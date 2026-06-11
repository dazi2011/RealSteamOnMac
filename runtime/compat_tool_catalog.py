#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import plistlib
import re
import stat
import sys
import unicodedata
from pathlib import Path


IDENTIFIER_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,63}")
RUNTIME_PACKAGE_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9._-]{1,159}"
)
RENDERERS = frozenset(("gptk", "dxmt", "dxvk", "wined3d"))
CAPABILITY_NAMES = (
    "msync",
    "retina",
    "metal_hud",
    "metalfx",
    "dxr",
    "avx",
)
METADATA_KEYS = frozenset(
    (
        "schema",
        "tool",
        "display_name",
        "renderer",
        "version",
        "runtime_package",
        "capabilities",
    )
)
MAX_METADATA_BYTES = 64 * 1024
MAX_PLIST_BYTES = 64 * 1024
MAX_VDF_BYTES = 256 * 1024
MAX_VDF_TOKENS = 4096
MAX_VDF_DEPTH = 32


class CatalogError(ValueError):
    pass


def _read_bounded_text(path, limit, label):
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CatalogError(f"cannot read {label}: {path}") from exc
    if len(data) > limit:
        raise CatalogError(f"{label} is too large: {path}")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CatalogError(f"{label} is not valid UTF-8: {path}") from exc


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError(f"metadata contains duplicate key: {key}")
        result[key] = value
    return result


def _load_metadata(path):
    text = _read_bounded_text(
        path, MAX_METADATA_BYTES, "realsteamonmac.json"
    )
    try:
        metadata = json.loads(
            text, object_pairs_hook=_reject_duplicate_json_keys
        )
    except CatalogError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise CatalogError(f"metadata is invalid JSON: {path}") from exc
    if not isinstance(metadata, dict):
        raise CatalogError(f"metadata must be an object: {path}")
    if set(metadata) != METADATA_KEYS:
        raise CatalogError(f"metadata fields are invalid: {path}")
    if type(metadata["schema"]) is not int or metadata["schema"] != 1:
        raise CatalogError(f"metadata schema is unsupported: {path}")

    tool = metadata["tool"]
    if not isinstance(tool, str) or not IDENTIFIER_PATTERN.fullmatch(tool):
        raise CatalogError(f"metadata tool identifier is invalid: {path}")

    display_name = metadata["display_name"]
    if (
        not isinstance(display_name, str)
        or not display_name.strip()
        or len(display_name) > 160
        or any(
            unicodedata.category(character) == "Cc"
            for character in display_name
        )
    ):
        raise CatalogError(f"metadata display name is invalid: {path}")

    renderer = metadata["renderer"]
    if not isinstance(renderer, str) or renderer not in RENDERERS:
        raise CatalogError(f"metadata renderer is unsupported: {path}")

    version = metadata["version"]
    if (
        not isinstance(version, str)
        or not version
        or len(version) > 64
    ):
        raise CatalogError(f"metadata version is invalid: {path}")

    runtime_package = metadata["runtime_package"]
    if (
        not isinstance(runtime_package, str)
        or not RUNTIME_PACKAGE_PATTERN.fullmatch(runtime_package)
    ):
        raise CatalogError(
            f"metadata runtime package identifier is invalid: {path}"
        )

    capabilities = metadata["capabilities"]
    if (
        not isinstance(capabilities, dict)
        or set(capabilities) != set(CAPABILITY_NAMES)
        or any(
            type(capabilities[name]) is not bool
            for name in CAPABILITY_NAMES
        )
    ):
        raise CatalogError(f"metadata capabilities are invalid: {path}")

    return {
        "tool": tool,
        "display_name": display_name,
        "renderer": renderer,
        "version": version,
        "runtime_package": runtime_package,
        "capabilities": {
            name: capabilities[name] for name in CAPABILITY_NAMES
        },
    }


def _tokenize_vdf(text, path):
    tokens = []
    position = 0
    length = len(text)
    while position < length:
        character = text[position]
        if character.isspace():
            position += 1
            continue
        if text.startswith("//", position):
            newline = text.find("\n", position + 2)
            position = length if newline < 0 else newline + 1
            continue
        if character == "{":
            tokens.append(("open", character))
            position += 1
        elif character == "}":
            tokens.append(("close", character))
            position += 1
        elif character == '"':
            position += 1
            value = []
            while position < length:
                character = text[position]
                if character == '"':
                    position += 1
                    break
                if character == "\\":
                    position += 1
                    if position >= length:
                        raise CatalogError(
                            f"unterminated VDF escape: {path}"
                        )
                    escaped = text[position]
                    replacements = {
                        '"': '"',
                        "\\": "\\",
                        "n": "\n",
                        "r": "\r",
                        "t": "\t",
                    }
                    if escaped in replacements:
                        value.append(replacements[escaped])
                    else:
                        value.extend(("\\", escaped))
                    position += 1
                    continue
                value.append(character)
                position += 1
            else:
                raise CatalogError(f"unterminated VDF string: {path}")
            tokens.append(("string", "".join(value)))
        else:
            start = position
            while (
                position < length
                and not text[position].isspace()
                and text[position] not in '{}"'
            ):
                if text.startswith("//", position):
                    break
                position += 1
            if start == position:
                raise CatalogError(f"invalid VDF token: {path}")
            tokens.append(("string", text[start:position]))
        if len(tokens) > MAX_VDF_TOKENS:
            raise CatalogError(f"VDF contains too many tokens: {path}")
    return tokens


def _parse_vdf_object(tokens, path, position=0, depth=0, nested=False):
    if depth > MAX_VDF_DEPTH:
        raise CatalogError(f"VDF nesting is too deep: {path}")
    result = {}
    while position < len(tokens):
        kind, value = tokens[position]
        if kind == "close":
            if not nested:
                raise CatalogError(f"unexpected VDF closing brace: {path}")
            return result, position + 1
        if kind != "string":
            raise CatalogError(f"VDF key is invalid: {path}")
        key = value
        if key in result:
            raise CatalogError(f"VDF contains duplicate key {key}: {path}")
        position += 1
        if position >= len(tokens):
            raise CatalogError(f"VDF value is missing for {key}: {path}")
        kind, value = tokens[position]
        if kind == "open":
            value, position = _parse_vdf_object(
                tokens,
                path,
                position + 1,
                depth + 1,
                nested=True,
            )
        elif kind == "string":
            position += 1
        else:
            raise CatalogError(f"VDF value is invalid for {key}: {path}")
        result[key] = value
    if nested:
        raise CatalogError(f"VDF object is missing a closing brace: {path}")
    return result, position


def parse_vdf_document(path, max_bytes=MAX_VDF_BYTES, label="VDF"):
    path = Path(path)
    text = _read_bounded_text(path, max_bytes, label)
    tokens = _tokenize_vdf(text, path)
    parsed, position = _parse_vdf_object(tokens, path)
    if position != len(tokens):
        raise CatalogError(f"VDF contains trailing content: {path}")
    return parsed


def _load_vdf_tool(path):
    parsed = parse_vdf_document(
        path, MAX_VDF_BYTES, "compatibilitytool.vdf"
    )
    compatibility_tools = parsed.get("compatibilitytools")
    if not isinstance(compatibility_tools, dict):
        raise CatalogError(
            f"VDF compatibilitytools object is missing: {path}"
        )
    compat_tools = compatibility_tools.get("compat_tools")
    if not isinstance(compat_tools, dict) or len(compat_tools) != 1:
        raise CatalogError(
            f"VDF must contain exactly one compatibility tool: {path}"
        )
    tool, values = next(iter(compat_tools.items()))
    if not isinstance(values, dict):
        raise CatalogError(f"VDF compatibility tool is invalid: {path}")
    required = ("display_name", "from_oslist", "to_oslist")
    if any(not isinstance(values.get(name), str) for name in required):
        raise CatalogError(f"VDF compatibility tool fields are invalid: {path}")
    return {
        "tool": tool,
        "display_name": values["display_name"],
        "from_oslist": values["from_oslist"],
        "to_oslist": values["to_oslist"],
    }


def _require_regular_file(path, label, executable=False):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise CatalogError(f"{label} is missing: {path}") from exc
    except OSError as exc:
        raise CatalogError(f"cannot inspect {label}: {path}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise CatalogError(f"{label} must be a regular file: {path}")
    if executable and not os.access(path, os.X_OK):
        raise CatalogError(f"{label} must be executable: {path}")


def _resolve_internal_path(path, root, label, *, directory=False):
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise CatalogError(f"{label} is missing: {path}") from exc
    except OSError as exc:
        raise CatalogError(f"cannot resolve {label}: {path}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise CatalogError(f"{label} escapes its tool directory: {path}") from exc
    try:
        mode = resolved.stat().st_mode
    except OSError as exc:
        raise CatalogError(f"cannot inspect {label}: {path}") from exc
    expected = stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)
    if not expected:
        kind = "directory" if directory else "regular file"
        raise CatalogError(f"{label} must resolve to a {kind}: {path}")
    return resolved


def _require_internal_file(path, root, label, *, executable=False):
    resolved = _resolve_internal_path(path, root, label)
    if executable and not os.access(resolved, os.X_OK):
        raise CatalogError(f"{label} must be executable: {path}")
    return resolved


def _internal_file_exists(path, root, label):
    if not path.exists() and not path.is_symlink():
        return False
    _require_internal_file(path, root, label)
    return True


def _validate_raw_display_name(name, directory):
    if (
        not name
        or len(name) > 128
        or any(unicodedata.category(character) == "Cc" for character in name)
    ):
        raise CatalogError(
            f"raw compatibility tool directory name is invalid: {directory}"
        )


def _raw_identifier(kind, directory_name):
    normalized = unicodedata.normalize("NFKD", directory_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", ascii_name).strip("._-")
    if not slug:
        slug = hashlib.sha256(directory_name.encode("utf-8")).hexdigest()[:12]
    prefix = f"realsteamonmac-user-{kind}-"
    identifier = prefix + slug
    if len(identifier) > 64:
        digest = hashlib.sha256(
            directory_name.encode("utf-8")
        ).hexdigest()[:10]
        slug = slug[: 64 - len(prefix) - len(digest) - 1].rstrip("._-")
        identifier = f"{prefix}{slug}-{digest}"
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise CatalogError(
            f"cannot derive a safe tool identifier from: {directory_name}"
        )
    return identifier


def _version_from_name(name, label, directory):
    matches = re.findall(r"(?<![0-9])([0-9]+(?:\.[0-9]+)+)", name)
    if not matches:
        raise CatalogError(f"{label} version is missing from: {directory}")
    return matches[-1]


def _raw_capabilities(**updates):
    capabilities = {
        "msync": True,
        "retina": True,
        "metal_hud": True,
        "metalfx": False,
        "dxr": False,
        "avx": True,
    }
    capabilities.update(updates)
    return capabilities


def _raw_tool_record(
    directory,
    *,
    kind,
    label,
    renderer,
    version,
    capabilities,
):
    _validate_raw_display_name(directory.name, directory)
    resolved = directory.resolve(strict=True)
    return {
        "strToolName": _raw_identifier(kind, directory.name),
        "strDisplayName": f"{label} {version} - {directory.name}",
        "renderer": renderer,
        "version": version,
        "runtimePackage": "current",
        "capabilities": capabilities,
        "installPath": str(resolved),
        "sourceKind": kind,
        "componentPath": str(resolved),
    }


def _load_gptk_version(directory):
    framework = directory / "external" / "D3DMetal.framework"
    candidates = (
        framework / "Versions" / "Current" / "Resources" / "Info.plist",
        framework / "Versions" / "A" / "Resources" / "Info.plist",
        framework / "Resources" / "Info.plist",
    )
    plist_path = next(
        (
            path
            for path in candidates
            if path.exists() or path.is_symlink()
        ),
        None,
    )
    if plist_path is None:
        raise CatalogError(f"GPTK D3DMetal Info.plist is missing: {directory}")
    resolved = _require_internal_file(
        plist_path,
        directory,
        "GPTK D3DMetal Info.plist",
    )
    try:
        data = resolved.read_bytes()
    except OSError as exc:
        raise CatalogError(
            f"cannot read GPTK D3DMetal Info.plist: {plist_path}"
        ) from exc
    if len(data) > MAX_PLIST_BYTES:
        raise CatalogError(
            f"GPTK D3DMetal Info.plist is too large: {plist_path}"
        )
    try:
        values = plistlib.loads(data)
    except plistlib.InvalidFileException as exc:
        raise CatalogError(
            f"GPTK D3DMetal Info.plist is invalid: {plist_path}"
        ) from exc
    if (
        not isinstance(values, dict)
        or values.get("CFBundleIdentifier") != "com.apple.D3DMetal"
    ):
        raise CatalogError(
            f"GPTK D3DMetal bundle identifier is invalid: {plist_path}"
        )
    version = values.get("CFBundleShortVersionString")
    if (
        not isinstance(version, str)
        or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", version)
    ):
        raise CatalogError(
            f"GPTK D3DMetal version is invalid: {plist_path}"
        )
    return version


def _scan_raw_gptk(directory):
    marker_paths = (
        directory / "external" / "D3DMetal.framework",
        directory / "external" / "libd3dshared.dylib",
        directory / "wine" / "x86_64-unix",
    )
    if not any(path.exists() or path.is_symlink() for path in marker_paths):
        if not directory.name.lower().startswith("gptk"):
            return None
    version = _load_gptk_version(directory)
    required = (
        ("external/libd3dshared.dylib", "GPTK shared D3D library"),
        ("wine/x86_64-unix/d3d11.so", "GPTK Unix D3D11 module"),
        ("wine/x86_64-unix/dxgi.so", "GPTK Unix DXGI module"),
        ("wine/x86_64-windows/d3d11.dll", "GPTK Windows D3D11 module"),
        ("wine/x86_64-windows/dxgi.dll", "GPTK Windows DXGI module"),
    )
    try:
        for relative, label in required:
            _require_internal_file(directory / relative, directory, label)
    except CatalogError as exc:
        raise CatalogError(
            f"GPTK payload is incomplete: {directory}: {exc}"
        ) from exc
    windows = directory / "wine" / "x86_64-windows"
    unix = directory / "wine" / "x86_64-unix"
    has_dxr = _internal_file_exists(
        windows / "d3d12.dll", directory, "GPTK Windows D3D12 module"
    ) and _internal_file_exists(
        unix / "d3d12.so", directory, "GPTK Unix D3D12 module"
    )
    has_metalfx = _internal_file_exists(
        windows / "nvapi64.dll", directory, "GPTK NVAPI module"
    ) and any(
        _internal_file_exists(windows / name, directory, f"GPTK {name} module")
        for name in ("nvngx-on-metalfx.dll", "nvngx.dll")
    )
    return _raw_tool_record(
        directory,
        kind="gptk",
        label="GPTK",
        renderer="gptk",
        version=version,
        capabilities=_raw_capabilities(
            metalfx=has_metalfx,
            dxr=has_dxr,
        ),
    )


def _scan_raw_dxmt(directory):
    unix = directory / "x86_64-unix"
    windows = directory / "x86_64-windows"
    markers = (
        unix / "winemetal.so",
        windows / "nvngx.dll",
        windows / "nvngx-on-metalfx.dll",
    )
    if not directory.name.lower().startswith("dxmt") and not any(
        path.exists() or path.is_symlink() for path in markers
    ):
        return None
    required = (
        (unix / "winemetal.so", "DXMT Wine Metal module"),
        (windows / "d3d11.dll", "DXMT D3D11 module"),
        (windows / "dxgi.dll", "DXMT DXGI module"),
    )
    try:
        for path, label in required:
            _require_internal_file(path, directory, label)
    except CatalogError as exc:
        raise CatalogError(
            f"DXMT payload is incomplete: {directory}: {exc}"
        ) from exc
    version = _version_from_name(directory.name, "DXMT", directory)
    has_metalfx = _internal_file_exists(
        windows / "nvapi64.dll", directory, "DXMT NVAPI module"
    ) and any(
        _internal_file_exists(windows / name, directory, f"DXMT {name} module")
        for name in ("nvngx.dll", "nvngx-on-metalfx.dll")
    )
    return _raw_tool_record(
        directory,
        kind="dxmt",
        label="DXMT",
        renderer="dxmt",
        version=version,
        capabilities=_raw_capabilities(metalfx=has_metalfx),
    )


def _scan_raw_dxvk(directory):
    windows = directory / "x86_64-windows"
    markers = (
        windows / "d3d9.dll",
        windows / "d3d10.dll",
        windows / "d3d10_1.dll",
        windows / "d3d10core.dll",
    )
    if not directory.name.lower().startswith("dxvk") and not any(
        path.exists() or path.is_symlink() for path in markers
    ):
        return None
    try:
        _require_internal_file(
            windows / "d3d9.dll", directory, "DXVK D3D9 module"
        )
        _require_internal_file(
            windows / "d3d11.dll", directory, "DXVK D3D11 module"
        )
    except CatalogError as exc:
        raise CatalogError(
            f"DXVK payload is incomplete: {directory}: {exc}"
        ) from exc
    version = _version_from_name(directory.name, "DXVK", directory)
    return _raw_tool_record(
        directory,
        kind="dxvk",
        label="DXVK",
        renderer="dxvk",
        version=version,
        capabilities=_raw_capabilities(),
    )


def _scan_raw_wine(directory):
    bin_directory = directory / "bin"
    wine_candidates = (bin_directory / "wine64", bin_directory / "wine")
    markers = (*wine_candidates, bin_directory / "wineserver")
    if not directory.name.lower().startswith("wine") and not any(
        path.exists() or path.is_symlink() for path in markers
    ):
        return None
    wine = next(
        (
            path
            for path in wine_candidates
            if path.exists() or path.is_symlink()
        ),
        None,
    )
    if wine is None:
        raise CatalogError(f"Wine payload is incomplete: {directory}: wine is missing")
    required = (
        (wine, "Wine launcher", True),
        (bin_directory / "wineserver", "Wine server", True),
        (
            directory / "lib" / "wine" / "x86_64-unix" / "ntdll.so",
            "Wine Unix NTDLL module",
            False,
        ),
        (
            directory / "lib" / "wine" / "x86_64-windows" / "ntdll.dll",
            "Wine Windows NTDLL module",
            False,
        ),
    )
    try:
        for path, label, executable in required:
            _require_internal_file(
                path,
                directory,
                label,
                executable=executable,
            )
    except CatalogError as exc:
        raise CatalogError(
            f"Wine payload is incomplete: {directory}: {exc}"
        ) from exc
    version = _version_from_name(directory.name, "Wine", directory)
    return _raw_tool_record(
        directory,
        kind="wine",
        label="Wine",
        renderer="wined3d",
        version=version,
        capabilities=_raw_capabilities(
            msync=False,
            retina=False,
            metal_hud=False,
        ),
    )


def _scan_raw_tool(directory):
    for scanner in (
        _scan_raw_gptk,
        _scan_raw_dxmt,
        _scan_raw_dxvk,
        _scan_raw_wine,
    ):
        tool = scanner(directory)
        if tool is not None:
            return tool
    return None


def _validate_root(root):
    path = Path(root).expanduser()
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise CatalogError(
            f"compatibility tools root does not exist: {path}"
        ) from exc
    except OSError as exc:
        raise CatalogError(
            f"cannot inspect compatibility tools root: {path}"
        ) from exc
    if stat.S_ISLNK(mode):
        raise CatalogError(
            f"compatibility tools root cannot be a symbolic link: {path}"
        )
    if not stat.S_ISDIR(mode):
        raise CatalogError(
            f"compatibility tools root is not a directory: {path}"
        )
    try:
        return path.resolve(strict=True)
    except OSError as exc:
        raise CatalogError(
            f"cannot resolve compatibility tools root: {path}"
        ) from exc


def scan_compat_tools(root):
    root_path = _validate_root(root)
    tools = []
    seen = set()
    try:
        children = sorted(root_path.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        raise CatalogError(
            f"cannot scan compatibility tools root: {root_path}"
        ) from exc

    for directory in children:
        try:
            mode = directory.lstat().st_mode
        except OSError as exc:
            raise CatalogError(
                f"cannot inspect compatibility tool child: {directory}"
            ) from exc
        if stat.S_ISLNK(mode):
            raise CatalogError(
                "compatibility tool child cannot be a symbolic link: "
                f"{directory}"
            )
        if not stat.S_ISDIR(mode):
            continue
        resolved_directory = directory.resolve(strict=True)
        if resolved_directory.parent != root_path:
            raise CatalogError(
                f"compatibility tool directory escapes root: {directory}"
            )

        run = directory / "run"
        vdf = directory / "compatibilitytool.vdf"
        manifest = directory / "toolmanifest.vdf"
        metadata_path = directory / "realsteamonmac.json"
        candidate_files = (run, vdf, manifest, metadata_path)
        if not any(path.exists() for path in candidate_files):
            tool = _scan_raw_tool(resolved_directory)
            if tool is None:
                continue
            if tool["strToolName"] in seen:
                raise CatalogError(
                    "duplicate compatibility tool identifier: "
                    f"{tool['strToolName']}"
                )
            seen.add(tool["strToolName"])
            tools.append(tool)
            continue
        _require_regular_file(run, "run", executable=True)
        _require_regular_file(vdf, "compatibilitytool.vdf")
        _require_regular_file(manifest, "toolmanifest.vdf")
        _require_regular_file(metadata_path, "realsteamonmac.json")

        metadata = _load_metadata(metadata_path)
        vdf_tool = _load_vdf_tool(vdf)
        if vdf_tool["tool"] != metadata["tool"]:
            raise CatalogError(
                f"VDF tool identifier does not match metadata: {directory}"
            )
        if vdf_tool["display_name"] != metadata["display_name"]:
            raise CatalogError(
                f"VDF display name does not match metadata: {directory}"
            )
        if vdf_tool["from_oslist"] != "windows":
            raise CatalogError(
                f"VDF source platform must be windows: {directory}"
            )
        if vdf_tool["to_oslist"] != "macos":
            raise CatalogError(
                f"VDF target platform must be macos: {directory}"
            )
        if metadata["tool"] in seen:
            raise CatalogError(
                f"duplicate compatibility tool identifier: {metadata['tool']}"
            )
        seen.add(metadata["tool"])
        tools.append(
            {
                "strToolName": metadata["tool"],
                "strDisplayName": metadata["display_name"],
                "renderer": metadata["renderer"],
                "version": metadata["version"],
                "runtimePackage": metadata["runtime_package"],
                "capabilities": metadata["capabilities"],
                "installPath": str(resolved_directory),
            }
        )

    tools.sort(
        key=lambda tool: (tool["strDisplayName"], tool["strToolName"])
    )
    return tools


scan_compat_tool_catalog = scan_compat_tools
load_compat_tool_catalog = scan_compat_tools


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate and print a Steam compatibility-tool catalog."
    )
    parser.add_argument("root", help="compatibilitytools.d directory")
    arguments = parser.parse_args(argv)
    try:
        tools = scan_compat_tools(arguments.root)
    except CatalogError as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
    json.dump(tools, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
