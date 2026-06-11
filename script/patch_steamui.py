#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

MODULE_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_RUNTIME = MODULE_DIRECTORY.parent / "runtime"
if REPOSITORY_RUNTIME.is_dir():
    sys.path.insert(0, str(REPOSITORY_RUNTIME))

from compat_tool_catalog import CatalogError, scan_compat_tools


KNOWN_INDEX_SHA256 = {
    "55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282",
}
KNOWN_COMPAT_CHUNK_SHA256 = {
    "6d28c06fafb32f99c695f4bc4d1b8a8b8fb5bc1efc425f2a78abb8697af81349",
    "f77316131cbed91865a800103bbda855a43395eecfb2bc866bc58c33fdea4c69",
    "387e1b1aacdcbddd5b1fbf65b64c9f5222cfe60d917568999c2c7ddedfdf6b0a",
}
if os.environ.get("REALSTEAMONMAC_ALLOW_TEST_FIXTURES") == "1":
    KNOWN_COMPAT_CHUNK_SHA256.add(
        "8fb392221299eea6b5326f8e3ed351d4cf4456fa2c56a32e752e057fb34d49df"
    )
INDEX_NAME = "index.html"
BACKUP_NAME = "index.html.realsteamonmac.original"
COMPAT_CHUNK_NAME = "chunk~2dcc5aaf7.js"
COMPAT_CHUNK_BACKUP_NAME = (
    "chunk~2dcc5aaf7.js.realsteamonmac.original"
)
ASSET_DIRECTORY = "realsteamonmac"
ANCHOR = '<script defer="defer" src="/library.js"></script>'
BEGIN_MARKER = "<!-- RealSteamOnMac UI begin -->"
END_MARKER = "<!-- RealSteamOnMac UI end -->"
CONFIG_TAG = '<script defer="defer" src="/realsteamonmac/config.js"></script>'
UI_TAG = '<script defer="defer" src="/realsteamonmac/ui.js"></script>'
CONFIG_PREFIX = "globalThis.__REALSTEAMONMAC_CONFIG__ = Object.freeze("
DEFAULT_COMPAT_TOOL = "realsteamonmac-dxmt"
REGISTRY_ENDPOINT = "http://127.0.0.1:57344/registry"
CONTROL_ENDPOINT = "http://127.0.0.1:57344/config"
ACTION_ENDPOINT = "http://127.0.0.1:57344/action"
JOB_ENDPOINT = "http://127.0.0.1:57344/job"
PUBLIC_DEPENDENCY_KEYS = (
    "id",
    "name",
    "description",
    "publisher",
    "size",
)
COMPAT_PAGE_ANCHOR = (
    '(0,f.CI)()&&o.push({title:(0,A.we)'
    '("#AppProperties_CompatibilityPage")'
)
COMPAT_PAGE_DYNAMIC_GATE = (
    "((0,f.CI)()||globalThis.__REALSTEAMONMAC_IS_MANAGED_APP__"
    "?.(t))&&o.push({title:(0,A.we)"
    '("#AppProperties_CompatibilityPage")'
)
COMPAT_PAGE_ALLOWLIST_GATE = (
    "((0,f.CI)()||globalThis.__REALSTEAMONMAC_CONFIG__"
    "?.appids?.includes(t))&&o.push({title:(0,A.we)"
    '("#AppProperties_CompatibilityPage")'
)
COMPAT_ENABLE_ANCHOR = (
    "r=(0,s.q3)(()=>u.rV.settings.bCompatEnabled),"
    "a=vt(t.unAppID,r),o=r&&!!t.strCompatToolName"
    "&&t.nCompatToolPriority==h.JN"
)
COMPAT_ENABLE_DYNAMIC_GATE = (
    "r=(0,s.q3)(()=>u.rV.settings.bCompatEnabled)"
    "||globalThis.__REALSTEAMONMAC_IS_MANAGED_APP__?.(t.unAppID),"
    "a=vt(t.unAppID,r),o=r&&((!!t.strCompatToolName"
    "&&t.nCompatToolPriority==h.JN)"
    "||!!globalThis.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__"
    "?.(t.unAppID))"
)
COMPAT_ENABLE_PREVIOUS_DYNAMIC_GATE = (
    "r=(0,s.q3)(()=>u.rV.settings.bCompatEnabled)"
    "||globalThis.__REALSTEAMONMAC_IS_MANAGED_APP__?.(t.unAppID),"
    "a=vt(t.unAppID,r),o=r&&!!t.strCompatToolName"
    "&&t.nCompatToolPriority==h.JN"
)
COMPAT_SELECTED_OPTION_ANCHOR = (
    "selectedOption:t.strCompatToolName,onChange:"
)
COMPAT_SELECTED_OPTION_DYNAMIC_GATE = (
    "selectedOption:t.strCompatToolName"
    "||globalThis.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__"
    "?.(t.unAppID)||\"\",onChange:"
)
NATIVE_CONTROLS_ANCHOR = (
    '(0,i.jsx)(wt,{...e})]})});function vt'
)
NATIVE_CONTROLS_DYNAMIC_GATE = (
    '(0,i.jsx)(wt,{...e}),'
    'globalThis.__REALSTEAMONMAC_RENDER_NATIVE_COMPAT_CONTROLS__'
    '?.({details:t,React:n,jsx:i,components:c,styles:K()})'
    ']})});function vt'
)


def sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def parse_allowlist(path):
    appids = []
    seen = set()
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].replace(",", " ")
        for token in line.split():
            if not token.isdecimal():
                continue
            appid = int(token, 10)
            if appid <= 0 or appid > 0xFFFFFFFF or appid in seen:
                continue
            seen.add(appid)
            appids.append(appid)
    return appids


def build_patched_index(original):
    if original.count(ANCHOR) != 1:
        raise ValueError("Steam UI index does not contain one supported anchor")
    injection = "".join(
        (
            ANCHOR,
            BEGIN_MARKER,
            CONFIG_TAG,
            UI_TAG,
            END_MARKER,
        )
    )
    return original.replace(ANCHOR, injection, 1)


def build_patched_compat_chunk(original):
    if original.count(COMPAT_PAGE_ANCHOR) != 2:
        raise ValueError(
            "compatibility chunk does not contain two supported page gates"
        )
    if original.count(COMPAT_ENABLE_ANCHOR) != 1:
        raise ValueError(
            "compatibility chunk does not contain one supported control gate"
        )
    if original.count(COMPAT_SELECTED_OPTION_ANCHOR) != 1:
        raise ValueError(
            "compatibility chunk does not contain one supported selector gate"
        )
    if original.count(NATIVE_CONTROLS_ANCHOR) != 1:
        raise ValueError(
            "compatibility chunk does not contain one supported native controls "
            "anchor"
        )
    if (
        COMPAT_PAGE_DYNAMIC_GATE in original
        or COMPAT_PAGE_ALLOWLIST_GATE in original
        or COMPAT_ENABLE_DYNAMIC_GATE in original
        or COMPAT_ENABLE_PREVIOUS_DYNAMIC_GATE in original
        or COMPAT_SELECTED_OPTION_DYNAMIC_GATE in original
        or NATIVE_CONTROLS_DYNAMIC_GATE in original
    ):
        raise ValueError("compatibility chunk is already partially patched")
    patched = original.replace(
        COMPAT_PAGE_ANCHOR,
        COMPAT_PAGE_DYNAMIC_GATE,
    )
    patched = patched.replace(
        COMPAT_ENABLE_ANCHOR,
        COMPAT_ENABLE_DYNAMIC_GATE,
        1,
    )
    patched = patched.replace(
        COMPAT_SELECTED_OPTION_ANCHOR,
        COMPAT_SELECTED_OPTION_DYNAMIC_GATE,
        1,
    )
    return patched.replace(
        NATIVE_CONTROLS_ANCHOR,
        NATIVE_CONTROLS_DYNAMIC_GATE,
        1,
    )


def build_previous_dynamic_compat_chunk(original):
    if original.count(COMPAT_PAGE_ANCHOR) != 2:
        raise ValueError(
            "compatibility chunk does not contain two supported page gates"
        )
    return original.replace(
        COMPAT_PAGE_ANCHOR,
        COMPAT_PAGE_DYNAMIC_GATE,
    )


def build_previous_native_compat_chunk(original):
    patched = build_previous_dynamic_compat_chunk(original)
    if patched.count(COMPAT_ENABLE_ANCHOR) != 1:
        raise ValueError(
            "compatibility chunk does not contain one supported control gate"
        )
    return patched.replace(
        COMPAT_ENABLE_ANCHOR,
        COMPAT_ENABLE_PREVIOUS_DYNAMIC_GATE,
        1,
    )


def build_previous_selected_compat_chunk(original):
    patched = build_previous_native_compat_chunk(original)
    if patched.count(COMPAT_ENABLE_PREVIOUS_DYNAMIC_GATE) != 1:
        raise ValueError(
            "compatibility chunk does not contain one supported native control "
            "gate"
        )
    patched = patched.replace(
        COMPAT_ENABLE_PREVIOUS_DYNAMIC_GATE,
        COMPAT_ENABLE_DYNAMIC_GATE,
        1,
    )
    if patched.count(COMPAT_SELECTED_OPTION_ANCHOR) != 1:
        raise ValueError(
            "compatibility chunk does not contain one supported selector gate"
        )
    return patched.replace(
        COMPAT_SELECTED_OPTION_ANCHOR,
        COMPAT_SELECTED_OPTION_DYNAMIC_GATE,
        1,
    )


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            temporary.chmod(path.stat().st_mode & 0o777)
        else:
            temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_registry_token(path):
    token = Path(path).read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[0-9A-Fa-f]{32,64}", token) is None:
        raise ValueError("RealSteamOnMac registry token is invalid")
    return token


def load_public_dependencies(path):
    catalog_path = Path(path)
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"RealSteamOnMac dependency catalog is invalid: {catalog_path}"
        ) from error
    dependencies = catalog.get("dependencies")
    if catalog.get("schema") != 1 or not isinstance(dependencies, list):
        raise ValueError(
            "RealSteamOnMac dependency catalog schema is unsupported"
        )
    public = []
    seen = set()
    for dependency in dependencies:
        dependency_id = (
            dependency.get("id")
            if isinstance(dependency, dict)
            else None
        )
        if (
            not isinstance(dependency, dict)
            or not isinstance(dependency_id, str)
            or re.fullmatch(r"[a-z0-9][a-z0-9-]{1,31}", dependency_id)
            is None
            or dependency_id in seen
            or not isinstance(dependency.get("name"), str)
            or not dependency["name"]
            or len(dependency["name"]) > 160
            or not isinstance(dependency.get("description"), str)
            or len(dependency["description"]) > 500
            or not isinstance(dependency.get("publisher"), str)
            or len(dependency["publisher"]) > 160
            or not isinstance(dependency.get("size"), int)
            or dependency["size"] <= 0
            or dependency["size"] > 512 * 1024 * 1024
        ):
            raise ValueError(
                "RealSteamOnMac dependency catalog entry is invalid: "
                f"{dependency_id}"
            )
        for key in ("name", "description", "publisher"):
            if any(ord(character) < 32 for character in dependency[key]):
                raise ValueError(
                    "RealSteamOnMac dependency catalog text is invalid"
                )
        seen.add(dependency_id)
        public.append(
            {key: dependency[key] for key in PUBLIC_DEPENDENCY_KEYS}
        )
    if not public:
        raise ValueError("RealSteamOnMac dependency catalog is empty")
    return public


def config_bytes(appids, registry_token, dependencies, compat_tools):
    if not compat_tools:
        raise ValueError("Steam UI compatibility tool catalog is empty")
    tool_names = {
        tool["strToolName"] for tool in compat_tools
    }
    default_compat_tool = (
        DEFAULT_COMPAT_TOOL
        if DEFAULT_COMPAT_TOOL in tool_names
        else compat_tools[0]["strToolName"]
    )
    payload = json.dumps(
        {
            "appids": appids,
            "defaultCompatTool": default_compat_tool,
            "registryEndpoint": REGISTRY_ENDPOINT,
            "controlEndpoint": CONTROL_ENDPOINT,
            "actionEndpoint": ACTION_ENDPOINT,
            "jobEndpoint": JOB_ENDPOINT,
            "registryToken": registry_token,
            "compatTools": compat_tools,
            "dependencies": dependencies,
        },
        separators=(",", ":"),
    )
    return f"{CONFIG_PREFIX}{payload});\n".encode("utf-8")


def paths_for(steamui_root):
    root = Path(steamui_root)
    return {
        "root": root,
        "index": root / INDEX_NAME,
        "backup": root / BACKUP_NAME,
        "compat_chunk": root / COMPAT_CHUNK_NAME,
        "compat_backup": root / COMPAT_CHUNK_BACKUP_NAME,
        "assets": root / ASSET_DIRECTORY,
        "config": root / ASSET_DIRECTORY / "config.js",
        "ui": root / ASSET_DIRECTORY / "ui.js",
    }


def validated_original(backup):
    if not backup.is_file():
        raise ValueError("Steam UI backup is missing")
    content = backup.read_bytes()
    if sha256_bytes(content) not in KNOWN_INDEX_SHA256:
        raise ValueError("Steam UI backup has an unsupported index hash")
    return content


def validated_compat_original(backup):
    if not backup.is_file():
        raise ValueError("compatibility chunk backup is missing")
    content = backup.read_bytes()
    if sha256_bytes(content) not in KNOWN_COMPAT_CHUNK_SHA256:
        raise ValueError(
            "compatibility chunk backup has an unsupported hash"
        )
    return content


def prepare_index(paths):
    current = paths["index"].read_bytes()
    current_text = current.decode("utf-8")
    if BEGIN_MARKER in current_text:
        original = validated_original(paths["backup"])
        expected = build_patched_index(
            original.decode("utf-8")
        ).encode("utf-8")
        if current != expected:
            raise ValueError("existing Steam UI patch is inconsistent")
        return original, expected, False

    if sha256_bytes(current) not in KNOWN_INDEX_SHA256:
        raise ValueError("unsupported Steam UI index hash")
    if paths["backup"].exists():
        original = validated_original(paths["backup"])
        if current != original:
            raise ValueError(
                "Steam UI backup does not match the restored clean index"
            )
        return original, build_patched_index(
            current_text
        ).encode("utf-8"), False
    return current, build_patched_index(current_text).encode("utf-8"), True


def prepare_compat_chunk(paths):
    current = paths["compat_chunk"].read_bytes()
    current_text = current.decode("utf-8")
    if COMPAT_PAGE_DYNAMIC_GATE in current_text:
        original = validated_compat_original(paths["compat_backup"])
        expected = build_patched_compat_chunk(
            original.decode("utf-8")
        ).encode("utf-8")
        previous = build_previous_dynamic_compat_chunk(
            original.decode("utf-8")
        ).encode("utf-8")
        previous_native = build_previous_native_compat_chunk(
            original.decode("utf-8")
        ).encode("utf-8")
        previous_selected = build_previous_selected_compat_chunk(
            original.decode("utf-8")
        ).encode("utf-8")
        if current not in (
            expected,
            previous,
            previous_native,
            previous_selected,
        ):
            raise ValueError(
                "existing compatibility chunk patch is inconsistent"
            )
        return original, expected, False
    if COMPAT_PAGE_ALLOWLIST_GATE in current_text:
        original = validated_compat_original(paths["compat_backup"])
        return (
            original,
            build_patched_compat_chunk(
                original.decode("utf-8")
            ).encode("utf-8"),
            False,
        )

    if sha256_bytes(current) not in KNOWN_COMPAT_CHUNK_SHA256:
        raise ValueError("unsupported compatibility chunk hash")
    if paths["compat_backup"].exists():
        original = validated_compat_original(paths["compat_backup"])
        if current != original:
            return (
                current,
                build_patched_compat_chunk(current_text).encode("utf-8"),
                True,
            )
        return original, build_patched_compat_chunk(
            current_text
        ).encode("utf-8"), False
    return (
        current,
        build_patched_compat_chunk(current_text).encode("utf-8"),
        True,
    )


def verify_steamui(steamui_root):
    paths = paths_for(steamui_root)
    if not paths["index"].is_file():
        raise ValueError("Steam UI index is missing")
    original = validated_original(paths["backup"])
    expected = build_patched_index(original.decode("utf-8")).encode("utf-8")
    current = paths["index"].read_bytes()
    if current != expected:
        raise ValueError("Steam UI index does not match the guarded patch")
    if current.count(BEGIN_MARKER.encode("utf-8")) != 1:
        raise ValueError("Steam UI patch marker count is invalid")
    compat_original = validated_compat_original(paths["compat_backup"])
    expected_compat = build_patched_compat_chunk(
        compat_original.decode("utf-8")
    ).encode("utf-8")
    if not paths["compat_chunk"].is_file():
        raise ValueError("compatibility chunk is missing")
    current_compat = paths["compat_chunk"].read_bytes()
    if current_compat != expected_compat:
        raise ValueError(
            "compatibility chunk does not match the guarded patch"
        )
    if (
        current_compat.count(
            COMPAT_PAGE_DYNAMIC_GATE.encode("utf-8")
        )
        != 2
    ):
        raise ValueError("compatibility page gate count is invalid")
    if (
        current_compat.count(
            COMPAT_ENABLE_DYNAMIC_GATE.encode("utf-8")
        )
        != 1
    ):
        raise ValueError("compatibility control gate count is invalid")
    if (
        current_compat.count(
            COMPAT_SELECTED_OPTION_DYNAMIC_GATE.encode("utf-8")
        )
        != 1
    ):
        raise ValueError("compatibility selector gate count is invalid")
    if (
        current_compat.count(
            NATIVE_CONTROLS_DYNAMIC_GATE.encode("utf-8")
        )
        != 1
    ):
        raise ValueError("native compatibility controls gate count is invalid")
    if not paths["ui"].is_file() or paths["ui"].stat().st_size == 0:
        raise ValueError("Steam UI asset is missing")
    if not paths["config"].is_file():
        raise ValueError("Steam UI config asset is missing")
    if paths["config"].stat().st_mode & 0o077:
        raise ValueError("Steam UI config asset permissions are too broad")

    config = paths["config"].read_text(encoding="utf-8")
    if not config.startswith(CONFIG_PREFIX) or not config.endswith(");\n"):
        raise ValueError("Steam UI config format is invalid")
    payload = config[len(CONFIG_PREFIX) : -3]
    parsed = json.loads(payload)
    appids = parsed.get("appids")
    if (
        not isinstance(appids, list)
        or not appids
        or any(
            not isinstance(appid, int) or appid <= 0 or appid > 0xFFFFFFFF
            for appid in appids
        )
        or len(appids) != len(set(appids))
    ):
        raise ValueError("Steam UI config allowlist is invalid")
    compat_tools = parsed.get("compatTools")
    default_compat_tool = parsed.get("defaultCompatTool")
    registry_endpoint = parsed.get("registryEndpoint")
    control_endpoint = parsed.get("controlEndpoint")
    action_endpoint = parsed.get("actionEndpoint")
    job_endpoint = parsed.get("jobEndpoint")
    registry_token = parsed.get("registryToken")
    dependencies = parsed.get("dependencies")
    if (
        not isinstance(compat_tools, list)
        or not compat_tools
        or any(
            not isinstance(tool, dict)
            or not isinstance(tool.get("strToolName"), str)
            or not tool["strToolName"]
            or not isinstance(tool.get("strDisplayName"), str)
            or not tool["strDisplayName"]
            or tool.get("renderer")
            not in {"gptk", "dxmt", "dxvk", "wined3d"}
            or not isinstance(tool.get("version"), str)
            or not tool["version"]
            or not isinstance(tool.get("runtimePackage"), str)
            or re.fullmatch(
                r"[a-z0-9][a-z0-9._-]{1,159}",
                tool["runtimePackage"],
            )
            is None
            or not isinstance(tool.get("installPath"), str)
            or not tool["installPath"]
            or not isinstance(tool.get("capabilities"), dict)
            or set(tool["capabilities"])
            != {
                "msync",
                "retina",
                "metal_hud",
                "metalfx",
                "dxr",
                "avx",
            }
            or any(
                type(value) is not bool
                for value in tool["capabilities"].values()
            )
            for tool in compat_tools
        )
        or len({tool["strToolName"] for tool in compat_tools})
        != len(compat_tools)
        or not isinstance(default_compat_tool, str)
        or default_compat_tool
        not in {tool["strToolName"] for tool in compat_tools}
        or registry_endpoint != REGISTRY_ENDPOINT
        or control_endpoint != CONTROL_ENDPOINT
        or action_endpoint != ACTION_ENDPOINT
        or job_endpoint != JOB_ENDPOINT
        or not isinstance(registry_token, str)
        or re.fullmatch(r"[0-9A-Fa-f]{32,64}", registry_token) is None
        or not isinstance(dependencies, list)
        or not dependencies
        or any(
            not isinstance(dependency, dict)
            or tuple(dependency) != PUBLIC_DEPENDENCY_KEYS
            or not isinstance(dependency.get("id"), str)
            or not isinstance(dependency.get("name"), str)
            or not isinstance(dependency.get("description"), str)
            or not isinstance(dependency.get("publisher"), str)
            or not isinstance(dependency.get("size"), int)
            for dependency in dependencies
        )
        or len({dependency["id"] for dependency in dependencies})
        != len(dependencies)
    ):
        raise ValueError("Steam UI compatibility tool config is invalid")
    return appids


def install_steamui(
    steamui_root,
    ui_source,
    allowlist,
    dependency_catalog=None,
    compat_tools_root=None,
):
    paths = paths_for(steamui_root)
    ui_source = Path(ui_source)
    if not paths["root"].is_dir():
        raise ValueError("Steam UI root is missing")
    if not paths["index"].is_file():
        raise ValueError("Steam UI index is missing")
    if not paths["compat_chunk"].is_file():
        raise ValueError("compatibility chunk is missing")
    if not ui_source.is_file() or ui_source.stat().st_size == 0:
        raise ValueError("RealSteamOnMac UI source is missing")

    appids = parse_allowlist(allowlist)
    if not appids:
        raise ValueError("RealSteamOnMac allowlist is empty")
    registry_token = load_registry_token(
        Path(allowlist).with_name("registry-token")
    )
    dependencies = load_public_dependencies(
        dependency_catalog
        if dependency_catalog is not None
        else Path(allowlist).with_name("dependencies") / "catalog.json"
    )
    try:
        compat_tools = scan_compat_tools(
            compat_tools_root
            if compat_tools_root is not None
            else Path(allowlist).with_name("compatibilitytools.d")
        )
    except CatalogError as error:
        raise ValueError(
            f"Steam compatibility tool catalog is invalid: {error}"
        ) from error

    original, expected_index, backup_index = prepare_index(paths)
    compat_original, expected_compat, backup_compat = (
        prepare_compat_chunk(paths)
    )

    if backup_index:
        atomic_write(paths["backup"], original)
    if backup_compat:
        atomic_write(paths["compat_backup"], compat_original)
    if paths["index"].read_bytes() != expected_index:
        atomic_write(paths["index"], expected_index)
    if paths["compat_chunk"].read_bytes() != expected_compat:
        atomic_write(paths["compat_chunk"], expected_compat)

    atomic_write(paths["ui"], ui_source.read_bytes())
    atomic_write(
        paths["config"],
        config_bytes(
            appids,
            registry_token,
            dependencies,
            compat_tools,
        ),
    )
    paths["config"].chmod(0o600)
    verify_steamui(paths["root"])
    return appids


def restore_steamui(steamui_root):
    paths = paths_for(steamui_root)
    original = validated_original(paths["backup"])
    compat_original = validated_compat_original(paths["compat_backup"])
    if not paths["index"].is_file():
        raise ValueError("Steam UI index is missing")
    if not paths["compat_chunk"].is_file():
        raise ValueError("compatibility chunk is missing")
    expected = build_patched_index(original.decode("utf-8")).encode("utf-8")
    if paths["index"].read_bytes() != expected:
        raise ValueError("Steam UI index is not the guarded project patch")
    expected_compat = build_patched_compat_chunk(
        compat_original.decode("utf-8")
    ).encode("utf-8")
    if paths["compat_chunk"].read_bytes() != expected_compat:
        raise ValueError(
            "compatibility chunk is not the guarded project patch"
        )

    atomic_write(paths["index"], original)
    atomic_write(paths["compat_chunk"], compat_original)
    paths["backup"].unlink()
    paths["compat_backup"].unlink()
    if paths["assets"].exists():
        shutil.rmtree(paths["assets"])


def build_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install")
    install.add_argument("--steamui-root", required=True)
    install.add_argument("--ui-source", required=True)
    install.add_argument("--allowlist", required=True)
    install.add_argument("--dependencies", required=True)
    install.add_argument("--compat-tools-root", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--steamui-root", required=True)

    restore = subparsers.add_parser("restore")
    restore.add_argument("--steamui-root", required=True)
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    if arguments.command == "install":
        appids = install_steamui(
            arguments.steamui_root,
            arguments.ui_source,
            arguments.allowlist,
            arguments.dependencies,
            arguments.compat_tools_root,
        )
        print(f"steamui=installed appids={','.join(map(str, appids))}")
    elif arguments.command == "verify":
        appids = verify_steamui(arguments.steamui_root)
        print(f"steamui=verified appids={','.join(map(str, appids))}")
    else:
        restore_steamui(arguments.steamui_root)
        print("steamui=restored")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"patch_steamui.py: {error}", file=sys.stderr)
        raise SystemExit(1)
