#!/usr/bin/env python3

import argparse
import json
import os
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
