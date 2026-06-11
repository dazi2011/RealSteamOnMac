#!/usr/bin/python3

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_MODULE_DIRECTORY = Path(__file__).resolve().parent
if str(RUNTIME_MODULE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULE_DIRECTORY))

from compat_tool_catalog import CatalogError, scan_compat_tools
from launcher_recovery import (
    LauncherRecoveryError,
    execute_launcher_recovery,
    load_launcher_recovery_catalog,
)
from steam_launch_descriptor import (
    LaunchDescriptorError,
    build_launch_descriptor_from_appinfo,
    resolve_launch_descriptor_value,
)
from steam_app_state import (
    SteamAppStateError,
    inspect_app_manifest,
    manifest_install_directory,
)


RENDERERS = ("gptk", "dxmt", "dxvk", "wined3d")
STEAMWORKS_RENDERERS = ("dxmt", "dxvk", "wined3d")
# People Playground's .NET mod compiler mistakes its Wine PID for a macOS PID.
# It can therefore survive the game indefinitely and keep Steam's AppID active.
POST_EXIT_PREFIX_KILL_APPIDS = frozenset((1118200,))
ACTION_JOB_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
CONTAINER_OPERATIONS = frozenset(
    (
        "open-c-drive",
        "install-application",
        "wine-configuration",
        "controllers",
        "restart",
        "task-manager",
        "quit-all",
        "delete-container",
    )
)
ENVIRONMENT_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
COMPAT_TOOL_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,63}")
RESERVED_ENVIRONMENT_NAMES = frozenset(
    (
        "HOME",
        "PATH",
        "WINEPREFIX",
        "WINEDLLOVERRIDES",
        "SteamAppId",
        "SteamGameId",
        "STEAM_COMPAT_APP_ID",
        "STEAM_COMPAT_DATA_PATH",
        "STEAM_COMPAT_CLIENT_INSTALL_PATH",
    )
)
RESERVED_ENVIRONMENT_NAMES_UPPER = frozenset(
    name.upper() for name in RESERVED_ENVIRONMENT_NAMES
)
RESERVED_ENVIRONMENT_PREFIXES = (
    "DYLD_",
    "REALSTEAMONMAC_",
    "STEAM_",
)
NATIVE_HELPER_ENVIRONMENT_NAMES = frozenset(
    (
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "PATH",
        "SHELL",
        "TMPDIR",
        "USER",
        "__CF_USER_TEXT_ENCODING",
    )
)
DEPENDENCY_DOWNLOAD_HOSTS = frozenset(
    (
        "aka.ms",
        "download.microsoft.com",
        "download.visualstudio.microsoft.com",
        "go.microsoft.com",
    )
)
DEFAULT_CONFIG = {
    "compat_tool": "",
    "renderer": "dxmt",
    "msync": True,
    "retina": False,
    "metal_hud": False,
    "metalfx": False,
    "dxr": False,
    "avx": False,
}


class RuntimeErrorWithContext(RuntimeError):
    pass


def utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_runtime_root():
    configured = os.environ.get("REALSTEAMONMAC_RUNTIME_ROOT")
    if configured:
        return Path(configured).expanduser()
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "RealSteamOnMac"
        / "runtimes"
    )


def default_compat_tools_root():
    configured = os.environ.get("REALSTEAMONMAC_COMPAT_TOOLS_ROOT")
    if configured:
        return Path(configured).expanduser()
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "Steam"
        / "compatibilitytools.d"
    )


def default_app_config_root():
    configured = os.environ.get("REALSTEAMONMAC_APP_CONFIG_ROOT")
    if configured:
        return Path(configured).expanduser()
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "RealSteamOnMac"
        / "apps"
    )


def default_support_root():
    configured = os.environ.get("REALSTEAMONMAC_SUPPORT_ROOT")
    if configured:
        return Path(configured).expanduser()
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "RealSteamOnMac"
    )


def default_job_root():
    configured = os.environ.get("REALSTEAMONMAC_JOB_ROOT")
    if configured:
        return Path(configured).expanduser()
    return default_support_root() / "jobs"


def default_dependency_catalog():
    configured = os.environ.get("REALSTEAMONMAC_DEPENDENCY_CATALOG")
    if configured:
        return Path(configured).expanduser()
    return default_support_root() / "dependencies" / "catalog.json"


def default_dependency_cache():
    configured = os.environ.get("REALSTEAMONMAC_DEPENDENCY_CACHE")
    if configured:
        return Path(configured).expanduser()
    return default_support_root() / "dependencies" / "cache"


def default_steam_root():
    configured = os.environ.get("REALSTEAMONMAC_STEAM_ROOT")
    if configured:
        return Path(configured).expanduser()
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "Steam"
    )


def default_appinfo_path(steam_root=None):
    configured = os.environ.get("REALSTEAMONMAC_APPINFO_PATH")
    if configured:
        return Path(configured).expanduser()
    root = (
        Path(steam_root).expanduser()
        if steam_root is not None
        else default_steam_root()
    )
    return root / "appcache" / "appinfo.vdf"


def atomic_write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_appid(explicit=None):
    candidates = (
        explicit,
        os.environ.get("STEAM_COMPAT_APP_ID"),
        os.environ.get("SteamAppId"),
        os.environ.get("SteamGameId"),
    )
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            value = int(str(candidate), 10)
        except ValueError as error:
            raise RuntimeErrorWithContext(
                f"invalid Steam AppID: {candidate}"
            ) from error
        if value <= 0:
            raise RuntimeErrorWithContext(
                f"invalid Steam AppID: {candidate}"
            )
        return value
    raise RuntimeErrorWithContext("Steam AppID is unavailable")


def find_steamapps(executable):
    resolved = executable.expanduser().resolve()
    for parent in (resolved.parent,) + tuple(resolved.parents):
        if parent.name == "steamapps":
            return parent
    raise RuntimeErrorWithContext(
        f"executable is not inside a Steam library: {resolved}"
    )


def resolve_context(executable, explicit_appid=None, explicit_compat_data=None):
    executable = executable.expanduser().resolve()
    if not executable.is_file():
        raise RuntimeErrorWithContext(
            f"Windows executable does not exist: {executable}"
        )
    with executable.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise RuntimeErrorWithContext(
                f"target is not a PE executable: {executable}"
            )

    appid = parse_appid(explicit_appid)
    steamapps = find_steamapps(executable)
    if explicit_compat_data:
        compat_data = Path(explicit_compat_data).expanduser().resolve()
    elif os.environ.get("STEAM_COMPAT_DATA_PATH"):
        compat_data = Path(
            os.environ["STEAM_COMPAT_DATA_PATH"]
        ).expanduser().resolve()
    else:
        compat_data = steamapps / "compatdata" / str(appid)

    expected = steamapps / "compatdata" / str(appid)
    if compat_data != expected:
        raise RuntimeErrorWithContext(
            "compatibility data path must use the Proton layout: "
            f"expected {expected}, got {compat_data}"
        )

    state = compat_data / "realsteamonmac"
    return {
        "appid": appid,
        "executable": executable,
        "working_directory": executable.parent,
        "install_path": executable.parent,
        "steamapps": steamapps,
        "compat_data": compat_data,
        "prefix": compat_data / "pfx",
        "state": state,
        "config": state / "config.json",
        "global_config": default_app_config_root() / f"{appid}.json",
        "logs": state / "logs",
    }


def parse_vdf_string_pairs(path):
    pairs = []
    pattern = re.compile(
        r'^\s*"((?:\\.|[^"])*)"\s*"((?:\\.|[^"])*)"\s*$'
    )
    try:
        lines = path.read_text(
            encoding="utf-8", errors="strict"
        ).splitlines()
    except OSError as error:
        raise RuntimeErrorWithContext(
            f"could not read Steam VDF file: {path}"
        ) from error
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        key = match.group(1).replace(r"\"", '"').replace(r"\\", "\\")
        value = (
            match.group(2).replace(r"\"", '"').replace(r"\\", "\\")
        )
        pairs.append((key, value))
    return pairs


def steam_library_roots(steam_root=None):
    root = (
        Path(steam_root).expanduser().resolve()
        if steam_root is not None
        else default_steam_root().resolve()
    )
    roots = [root]
    library_file = root / "steamapps" / "libraryfolders.vdf"
    if library_file.is_file():
        for key, value in parse_vdf_string_pairs(library_file):
            if key != "path":
                continue
            candidate = Path(value).expanduser().resolve()
            if candidate not in roots:
                roots.append(candidate)
    return roots


def parse_app_manifest(path, expected_appid):
    try:
        return manifest_install_directory(path, expected_appid)
    except SteamAppStateError as error:
        raise RuntimeErrorWithContext(
            str(error)
        ) from error


def find_app_installation(appid, steam_root=None):
    appid = parse_appid(appid)
    for library_root in steam_library_roots(steam_root):
        steamapps = library_root / "steamapps"
        manifest = steamapps / f"appmanifest_{appid}.acf"
        if not manifest.is_file():
            continue
        installdir = parse_app_manifest(manifest, appid)
        install_path = (steamapps / "common" / installdir).resolve()
        if not install_path.is_dir():
            raise RuntimeErrorWithContext(
                f"Steam game install directory is missing: {install_path}"
            )
        try:
            install_state = inspect_app_manifest(
                manifest, appid, install_path
            )
        except SteamAppStateError as error:
            raise RuntimeErrorWithContext(str(error)) from error
        if not install_state["launchable"]:
            raise RuntimeErrorWithContext(
                "Steam app installation is incomplete "
                f"({install_state['diagnostic']}): AppID {appid}; "
                "use Steam's install or repair action"
            )
        return {
            "appid": appid,
            "steamapps": steamapps.resolve(),
            "manifest": manifest.resolve(),
            "install_path": install_path,
            "install_state": install_state,
            "compat_data": (
                steamapps / "compatdata" / str(appid)
            ).resolve(),
        }
    raise RuntimeErrorWithContext(
        f"Steam app manifest was not found for AppID {appid}"
    )


def discover_default_executable(installation):
    install_path = installation["install_path"]
    top_level = sorted(
        path for path in install_path.glob("*.exe") if path.is_file()
    )
    candidates = top_level
    if not candidates:
        candidates = []
        for path in install_path.rglob("*.exe"):
            if path.is_file():
                candidates.append(path)
            if len(candidates) >= 5000:
                break
        candidates.sort()
    if not candidates:
        raise RuntimeErrorWithContext(
            f"no Windows executable was found in {install_path}"
        )

    preferred_name = re.sub(
        r"[^a-z0-9]", "", install_path.name.lower()
    )
    rejected_stems = (
        "crashhandler",
        "unins",
        "uninstall",
        "setup",
        "installer",
    )

    def rank(path):
        stem = re.sub(r"[^a-z0-9]", "", path.stem.lower())
        rejected = any(token in stem for token in rejected_stems)
        exact = stem == preferred_name
        return (rejected, not exact, len(path.parts), str(path).lower())

    for candidate in sorted(candidates, key=rank):
        try:
            with candidate.open("rb") as stream:
                if stream.read(2) == b"MZ":
                    return candidate.resolve()
        except OSError:
            continue
    raise RuntimeErrorWithContext(
        f"no valid PE executable was found in {install_path}"
    )


def resolve_app_context(
    appid, steam_root=None, requested_target=None
):
    installation = find_app_installation(appid, steam_root)
    try:
        descriptor = build_launch_descriptor_from_appinfo(
            default_appinfo_path(steam_root),
            expected_appid=installation["appid"],
            install_path=installation["install_path"],
            requested_target=requested_target,
        )
        launch = resolve_launch_descriptor_value(
            descriptor,
            expected_appid=installation["appid"],
            install_path=installation["install_path"],
        )
    except LaunchDescriptorError as error:
        diagnostic = ""
        try:
            guessed = discover_default_executable(installation)
            diagnostic = (
                f"; diagnostic executable present but not selected by "
                f"Steam: {guessed}"
            )
        except RuntimeErrorWithContext:
            pass
        raise RuntimeErrorWithContext(
            f"{error}{diagnostic}"
        ) from error
    context = resolve_context(
        launch["executable"],
        str(installation["appid"]),
        str(installation["compat_data"]),
    )
    context["install_path"] = installation["install_path"]
    context["working_directory"] = launch["working_directory"]
    context["launch_entry_id"] = launch["entry_id"]
    context["launch_arguments"] = launch["arguments"]
    context["requested_target"] = (
        Path(requested_target).expanduser()
        if requested_target is not None
        else None
    )
    return context


def parse_launch_arguments(value):
    if not value:
        return []
    try:
        return shlex.split(value, posix=True)
    except ValueError as error:
        raise RuntimeErrorWithContext(
            f"Steam launch arguments are invalid: {error}"
        ) from error


def normalize_config(value):
    config = dict(DEFAULT_CONFIG)
    if value:
        unknown = sorted(set(value) - set(DEFAULT_CONFIG))
        if unknown:
            raise RuntimeErrorWithContext(
                f"unknown configuration keys: {', '.join(unknown)}"
            )
        config.update(value)
    if config["renderer"] not in RENDERERS:
        raise RuntimeErrorWithContext(
            f"unsupported renderer: {config['renderer']}"
        )
    if (
        not isinstance(config["compat_tool"], str)
        or (
            config["compat_tool"]
            and COMPAT_TOOL_PATTERN.fullmatch(config["compat_tool"]) is None
        )
    ):
        raise RuntimeErrorWithContext(
            "compatibility tool identifier is invalid"
        )
    for key in DEFAULT_CONFIG:
        if key in {"compat_tool", "renderer"}:
            continue
        if not isinstance(config[key], bool):
            raise RuntimeErrorWithContext(
                f"configuration value {key} must be boolean"
            )
    if (
        not config["compat_tool"]
        and config["metalfx"]
        and config["renderer"] != "gptk"
    ):
        raise RuntimeErrorWithContext(
            "MetalFX translation requires a capability-aware tool selection"
        )
    if (
        not config["compat_tool"]
        and config["dxr"]
        and config["renderer"] != "gptk"
    ):
        raise RuntimeErrorWithContext(
            "DXR requires a capability-aware tool selection"
        )
    return config


def load_config(context):
    for path in (context["global_config"], context["config"]):
        if not path.exists():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeErrorWithContext(
                f"could not read per-game configuration: {path}"
            ) from error
        if not isinstance(value, dict):
            raise RuntimeErrorWithContext(
                f"per-game configuration must be an object: {path}"
            )
        return normalize_config(value)
    return normalize_config(None)


def save_config(context, config):
    normalized = normalize_config(config)
    atomic_write_json(context["global_config"], normalized)
    atomic_write_json(context["config"], normalized)
    return normalized


def load_compat_tool(tool_name, root=None):
    if not tool_name:
        return None
    try:
        tools = scan_compat_tools(root or default_compat_tools_root())
    except CatalogError as error:
        raise RuntimeErrorWithContext(
            f"compatibility tool catalog is invalid: {error}"
        ) from error
    for tool in tools:
        if tool["strToolName"] == tool_name:
            return tool
    raise RuntimeErrorWithContext(
        f"compatibility tool is unavailable: {tool_name}"
    )


def validate_tool_capabilities(config, tool):
    if tool is None:
        return
    if tool["renderer"] != config["renderer"]:
        raise RuntimeErrorWithContext(
            "compatibility tool renderer does not match configuration"
        )
    for key in (
        "msync",
        "retina",
        "metal_hud",
        "metalfx",
        "dxr",
        "avx",
    ):
        if config[key] and not tool["capabilities"][key]:
            raise RuntimeErrorWithContext(
                f"{key} is unsupported by {tool['strDisplayName']}"
            )


def load_package(runtime_root, renderer, runtime_package=None):
    if runtime_package:
        package = runtime_root / "packages" / runtime_package
        if not package.is_dir():
            raise RuntimeErrorWithContext(
                f"runtime package is unavailable: {package}"
            )
        package = package.resolve()
    else:
        current = runtime_root / "current"
        if not current.exists():
            raise RuntimeErrorWithContext(
                f"no active runtime package: {current}"
            )
        package = current.resolve()
    manifest_path = package / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeErrorWithContext(
            f"runtime manifest is invalid: {manifest_path}"
        ) from error
    if manifest.get("schema") != 1 or not manifest.get("package_id"):
        raise RuntimeErrorWithContext(
            f"unsupported runtime manifest: {manifest_path}"
        )
    if (
        runtime_package
        and manifest["package_id"] != runtime_package
    ):
        raise RuntimeErrorWithContext(
            f"runtime package identity mismatch: {manifest_path}"
        )
    wine_root = package / "wine" / renderer
    wine64 = wine_root / "bin" / "wine64"
    if not wine64.is_file() or not os.access(wine64, os.X_OK):
        raise RuntimeErrorWithContext(
            f"runtime is missing executable wine64: {wine64}"
        )
    return package, manifest, wine_root, wine64


def load_selected_package(runtime_root, config):
    tool = load_compat_tool(config["compat_tool"])
    validate_tool_capabilities(config, tool)
    package, manifest, wine_root, wine64 = load_package(
        runtime_root,
        config["renderer"],
        tool["runtimePackage"] if tool is not None else None,
    )
    return package, manifest, wine_root, wine64, tool


def resolve_steam_client_install():
    configured = os.environ.get("REALSTEAMONMAC_STEAM_CLIENT_INSTALL")
    if configured:
        path = Path(configured).expanduser().resolve()
    else:
        path = (
            Path.home()
            / "Library"
            / "Application Support"
            / "Steam"
            / "Steam.AppBundle"
            / "Steam"
            / "Contents"
            / "MacOS"
        )
    steamclient = path / "steamclient.dylib"
    if not steamclient.is_file():
        raise RuntimeErrorWithContext(
            f"native Steam client library is unavailable: {steamclient}"
        )
    return path


def load_steamworks_bridge(package, manifest, wine_root, renderer):
    bridge = manifest.get("steamworks_bridge")
    if bridge is None:
        return None
    if not isinstance(bridge, dict):
        raise RuntimeErrorWithContext(
            f"runtime Steamworks bridge metadata is invalid: {package}"
        )
    renderers = bridge.get("renderers")
    if not isinstance(renderers, list) or renderer not in renderers:
        return None
    if renderer not in STEAMWORKS_RENDERERS:
        raise RuntimeErrorWithContext(
            f"Steamworks bridge is unsupported for renderer: {renderer}"
        )

    windows_relative = bridge.get("windows_dll")
    unix_relative = bridge.get("unix_library")
    if not isinstance(windows_relative, str) or not isinstance(
        unix_relative, str
    ):
        raise RuntimeErrorWithContext(
            f"runtime Steamworks bridge paths are invalid: {package}"
        )

    windows_dll = package / windows_relative
    unix_library = package / unix_relative
    installed_windows = (
        wine_root
        / "lib"
        / "wine"
        / "x86_64-windows"
        / "lsteamclient.dll"
    )
    installed_unix = (
        wine_root
        / "lib"
        / "wine"
        / "x86_64-unix"
        / "lsteamclient.so"
    )
    for path in (
        windows_dll,
        unix_library,
        installed_windows,
        installed_unix,
    ):
        if not path.is_file():
            raise RuntimeErrorWithContext(
                f"runtime Steamworks bridge payload is missing: {path}"
            )

    return {
        "metadata": bridge,
        "windows_dll": windows_dll,
        "unix_library": unix_library,
        "steam_client_install": resolve_steam_client_install(),
    }


def load_dxmt_winemac_compat(package, manifest, wine_root, renderer):
    if renderer != "dxmt":
        return None

    metadata = manifest.get("dxmt_winemac_compat")
    if not isinstance(metadata, dict):
        raise RuntimeErrorWithContext(
            f"runtime is missing DXMT Wine compatibility metadata: {package}"
        )
    driver_relative = metadata.get("winemac_driver")
    shim_relative = metadata.get("visibility_shim")
    if not isinstance(driver_relative, str) or not isinstance(
        shim_relative, str
    ):
        raise RuntimeErrorWithContext(
            f"runtime DXMT Wine compatibility paths are invalid: {package}"
        )

    driver = package / driver_relative
    expected_driver = (
        wine_root / "lib" / "wine" / "x86_64-unix" / "winemac.so"
    )
    shim = package / shim_relative
    expected_shim = (
        wine_root
        / "lib"
        / "librealsteamonmac_dxmt_macdrv_shim.dylib"
    )
    if driver.resolve() != expected_driver.resolve():
        raise RuntimeErrorWithContext(
            f"runtime DXMT winemac driver path is invalid: {driver}"
        )
    if shim.resolve() != expected_shim.resolve():
        raise RuntimeErrorWithContext(
            f"runtime DXMT visibility shim path is invalid: {shim}"
        )
    for path in (driver, shim):
        if not path.is_file():
            raise RuntimeErrorWithContext(
                f"runtime DXMT Wine compatibility payload is missing: {path}"
            )
    return {
        "metadata": metadata,
        "driver": driver,
        "visibility_shim": shim,
    }


def build_environment(
    context,
    config,
    wine_root,
    steamworks_bridge=None,
    dxmt_winemac_compat=None,
):
    environment = dict(os.environ)
    environment["WINEPREFIX"] = str(context["prefix"])
    environment["PATH"] = (
        f"{wine_root / 'bin'}:{environment.get('PATH', '')}"
    )
    environment["REALSTEAMONMAC_APP_ID"] = str(context["appid"])
    environment["REALSTEAMONMAC_RENDERER"] = config["renderer"]
    environment["SteamAppId"] = str(context["appid"])
    environment["SteamGameId"] = str(context["appid"])
    environment["STEAM_COMPAT_APP_ID"] = str(context["appid"])
    environment["STEAM_COMPAT_DATA_PATH"] = str(context["compat_data"])

    for key in (
        "WINEMSYNC",
        "WINEESYNC",
        "MTL_HUD_ENABLED",
        "D3DM_ENABLE_METALFX",
        "D3DM_SUPPORT_DXR",
        "DXMT_ENABLE_NVEXT",
        "ROSETTA_ADVERTISE_AVX",
        "MVK_CONFIG_RESUME_LOST_DEVICE",
        "WINEDLLOVERRIDES",
        "STEAM_COMPAT_CLIENT_INSTALL_PATH",
        "DYLD_INSERT_LIBRARIES",
    ):
        environment.pop(key, None)

    if config["msync"]:
        environment["WINEMSYNC"] = "1"
        # D3DMetal checks WINEESYNC even when the server uses MSync.
        environment["WINEESYNC"] = "1"
    if config["metal_hud"]:
        environment["MTL_HUD_ENABLED"] = "1"
    if config["metalfx"]:
        if config["renderer"] == "dxmt":
            environment["DXMT_ENABLE_NVEXT"] = "1"
        else:
            environment["D3DM_ENABLE_METALFX"] = "1"
    if config["dxr"]:
        environment["D3DM_SUPPORT_DXR"] = "1"
    if config["avx"]:
        environment["ROSETTA_ADVERTISE_AVX"] = "1"
    if config["renderer"] == "dxvk":
        environment["MVK_CONFIG_RESUME_LOST_DEVICE"] = "1"
    if dxmt_winemac_compat is not None:
        environment["DYLD_INSERT_LIBRARIES"] = str(
            dxmt_winemac_compat["visibility_shim"]
        )
    dll_overrides = ["winemenubuilder.exe=d"]
    if steamworks_bridge is not None:
        environment["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(
            steamworks_bridge["steam_client_install"]
        )
        dll_overrides.extend(
            ("steamclient64=n,b", "steamclient=n,b", "lsteamclient=n,b")
        )
    environment["WINEDLLOVERRIDES"] = ";".join(dll_overrides)

    return environment


def log_event(context, event):
    context["logs"].mkdir(parents=True, exist_ok=True)
    path = context["logs"] / "runtime.jsonl"
    record = {"timestamp": utc_timestamp(), **event}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True))
        stream.write("\n")


def run_logged(context, command, environment, description):
    context["logs"].mkdir(parents=True, exist_ok=True)
    log_path = context["logs"] / "wine-setup.log"
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n[{utc_timestamp()}] {description}\n")
        stream.write(f"$ {shlex.join(str(part) for part in command)}\n")
        stream.flush()
        result = subprocess.run(
            [str(part) for part in command],
            cwd=str(context["install_path"]),
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeErrorWithContext(
            f"{description} failed with exit code {result.returncode}; "
            f"see {log_path}"
        )


def initialize_prefix(context, wine64, environment):
    context["state"].mkdir(parents=True, exist_ok=True)
    lock_path = context["state"] / "prefix.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        prefix = context["prefix"]
        if not (prefix / "dosdevices").is_dir():
            prefix.mkdir(parents=True, exist_ok=True)
            run_logged(
                context,
                [wine64, "wineboot", "--init"],
                environment,
                "initialize Wine prefix",
            )
            run_logged(
                context,
                [wine64, "winecfg", "-v", "win10"],
                environment,
                "set Wine prefix to Windows 10",
            )


def apply_retina_mode(context, wine64, environment, enabled):
    value = "y" if enabled else "n"
    marker_path = context["state"] / "retina-mode"
    previous = (
        marker_path.read_text(encoding="utf-8").strip()
        if marker_path.exists()
        else None
    )
    if previous == value:
        return
    run_logged(
        context,
        [
            wine64,
            "reg",
            "add",
            r"HKCU\Software\Wine\Mac Driver",
            "/v",
            "RetinaMode",
            "/t",
            "REG_SZ",
            "/d",
            value,
            "/f",
        ],
        environment,
        "configure Retina mode",
    )
    marker_path.write_text(f"{value}\n", encoding="utf-8")
    os.chmod(marker_path, 0o600)


def known_metalfx_digests(package, name):
    windows_roots = (
        package / "wine" / "gptk" / "lib" / "wine" / "x86_64-windows",
        package / "wine" / "dxmt" / "lib" / "wine" / "x86_64-windows",
    )
    candidates = [root / name for root in windows_roots]
    if name == "nvngx.dll":
        candidates.append(windows_roots[0] / "nvngx-on-metalfx.dll")
    return {
        file_sha256(candidate)
        for candidate in candidates
        if candidate.is_file()
    }


def install_metalfx_files(
    context, package, wine_root, renderer, enabled
):
    marker_path = context["state"] / "metalfx-files.json"
    system32 = context["prefix"] / "drive_c" / "windows" / "system32"
    names = ("nvngx.dll", "nvapi64.dll")
    known_digests = {
        name: known_metalfx_digests(package, name) for name in names
    }
    previous = {}
    if marker_path.is_file():
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeErrorWithContext(
                f"MetalFX file ledger is invalid: {marker_path}"
            ) from error
        if (
            isinstance(marker, dict)
            and isinstance(marker.get("files"), dict)
        ):
            previous = marker["files"]
        elif (
            isinstance(marker, dict)
            and all(
                name in marker and isinstance(marker[name], str)
                for name in names
            )
        ):
            previous = marker
        else:
            raise RuntimeErrorWithContext(
                f"MetalFX file ledger is invalid: {marker_path}"
            )
    if not enabled:
        removable = []
        for name in names:
            destination = system32 / name
            if not destination.exists():
                continue
            current = file_sha256(destination)
            if (
                previous.get(name) != current
                and current not in known_digests[name]
            ):
                raise RuntimeErrorWithContext(
                    "refusing to remove an unmanaged MetalFX file: "
                    f"{destination}"
                )
            removable.append(destination)
        for destination in removable:
            destination.unlink()
        if marker_path.exists():
            marker_path.unlink()
        return

    source_root = wine_root / "lib" / "wine" / "x86_64-windows"
    source_mapping = (
        {
            "nvngx.dll": source_root / "nvngx.dll",
            "nvapi64.dll": source_root / "nvapi64.dll",
        }
        if renderer == "dxmt"
        else {
            "nvngx.dll": source_root / "nvngx-on-metalfx.dll",
            "nvapi64.dll": source_root / "nvapi64.dll",
        }
    )
    system32.mkdir(parents=True, exist_ok=True)
    installed = {}
    source_records = []
    for name in names:
        source = source_mapping[name]
        if not source.is_file():
            raise RuntimeErrorWithContext(
                f"{renderer.upper()} MetalFX payload is missing: {source}"
            )
        destination = system32 / name
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if destination.exists():
            current = hashlib.sha256(destination.read_bytes()).hexdigest()
            if current != digest:
                if (
                    previous.get(name) != current
                    and current not in known_digests[name]
                ):
                    raise RuntimeErrorWithContext(
                        "refusing to replace an unmanaged MetalFX file: "
                        f"{destination}"
                    )
        source_records.append((name, source, destination, digest))
    for name, source, destination, digest in source_records:
        if not destination.exists() or file_sha256(destination) != digest:
            atomic_copy_file(source, destination)
        installed[name] = digest
    atomic_write_json(
        marker_path,
        {
            "schema": 1,
            "package_id": package.name,
            "renderer": renderer,
            "files": installed,
        },
    )


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=str(destination.parent)
    )
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as input_stream:
            with os.fdopen(descriptor, "wb") as output_stream:
                for chunk in iter(
                    lambda: input_stream.read(1024 * 1024), b""
                ):
                    output_stream.write(chunk)
                output_stream.flush()
                os.fsync(output_stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def install_steamworks_files(context, manifest, bridge):
    marker_path = context["state"] / "steamworks-bridge.json"
    previous = {}
    if marker_path.exists():
        try:
            previous = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeErrorWithContext(
                f"Steamworks bridge ledger is invalid: {marker_path}"
            ) from error
    previous_files = previous.get("files", {})
    if not isinstance(previous_files, dict):
        raise RuntimeErrorWithContext(
            f"Steamworks bridge ledger is invalid: {marker_path}"
        )
    managed_names = ("lsteamclient.dll", "steamclient64.dll")
    if (
        not set(previous_files).issubset(managed_names)
        or any(
            not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for digest in previous_files.values()
        )
    ):
        raise RuntimeErrorWithContext(
            f"Steamworks bridge ledger is invalid: {marker_path}"
        )

    steam_directory = (
        context["prefix"]
        / "drive_c"
        / "Program Files (x86)"
        / "Steam"
    )
    if bridge is None:
        if not previous:
            return
        for name, managed_digest in previous_files.items():
            destination = steam_directory / name
            if not destination.exists():
                continue
            if file_sha256(destination) != managed_digest:
                raise RuntimeErrorWithContext(
                    "refusing to remove a modified managed Steamworks "
                    f"file: {destination}"
                )
            destination.unlink()
        atomic_write_json(
            marker_path,
            {
                **previous,
                "schema": 1,
                "active": False,
            },
        )
        return

    source = bridge["windows_dll"]
    source_digest = file_sha256(source)
    installed = {}
    for name in managed_names:
        destination = steam_directory / name
        if destination.exists():
            current_digest = file_sha256(destination)
            managed_digest = previous_files.get(name)
            if current_digest != source_digest and (
                not isinstance(managed_digest, str)
                or current_digest != managed_digest
            ):
                raise RuntimeErrorWithContext(
                    "refusing to replace an unmanaged Steamworks file: "
                    f"{destination}"
                )
        if not destination.exists() or file_sha256(
            destination
        ) != source_digest:
            atomic_copy_file(source, destination)
        installed[name] = source_digest

    atomic_write_json(
        marker_path,
        {
            "schema": 1,
            "package_id": manifest["package_id"],
            "bridge": bridge["metadata"].get("name", "lsteamclient"),
            "active": True,
            "files": installed,
        },
    )


def configure_steam_registry(context, wine64, environment, bridge):
    if bridge is None:
        return

    steam_path = r"C:\Program Files (x86)\Steam"
    registry_values = (
        (
            r"HKCU\Software\Valve\Steam",
            "SteamPath",
            "REG_SZ",
            steam_path,
        ),
        (
            r"HKCU\Software\Valve\Steam",
            "SteamExe",
            "REG_SZ",
            rf"{steam_path}\steam.exe",
        ),
        (
            r"HKCU\Software\Valve\Steam\ActiveProcess",
            "PID",
            "REG_DWORD",
            "65534",
        ),
        (
            r"HKCU\Software\Valve\Steam\ActiveProcess",
            "SteamClientDll",
            "REG_SZ",
            rf"{steam_path}\steamclient.dll",
        ),
        (
            r"HKCU\Software\Valve\Steam\ActiveProcess",
            "SteamClientDll64",
            "REG_SZ",
            rf"{steam_path}\steamclient64.dll",
        ),
        (
            r"HKCU\Software\Valve\Steam\ActiveProcess",
            "SteamPath",
            "REG_SZ",
            steam_path,
        ),
        (
            r"HKLM\Software\Wow6432Node\Valve\Steam",
            "InstallPath",
            "REG_SZ",
            steam_path,
        ),
    )
    for key, name, value_type, value in registry_values:
        run_logged(
            context,
            [
                wine64,
                "reg",
                "add",
                key,
                "/v",
                name,
                "/t",
                value_type,
                "/d",
                value,
                "/f",
            ],
            environment,
            f"configure Steam registry value {name}",
        )


def prepare(context, runtime_root, config):
    package, manifest, wine_root, wine64, _ = load_selected_package(
        runtime_root, config
    )
    bridge = load_steamworks_bridge(
        package, manifest, wine_root, config["renderer"]
    )
    dxmt_winemac_compat = load_dxmt_winemac_compat(
        package, manifest, wine_root, config["renderer"]
    )
    environment = build_environment(
        context,
        config,
        wine_root,
        bridge,
        dxmt_winemac_compat,
    )
    initialize_prefix(context, wine64, environment)
    install_steamworks_files(context, manifest, bridge)
    configure_steam_registry(
        context, wine64, environment, bridge
    )
    apply_retina_mode(
        context, wine64, environment, config["retina"]
    )
    install_metalfx_files(
        context,
        package,
        wine_root,
        config["renderer"],
        config["metalfx"],
    )
    return package, manifest, wine_root, wine64, environment


def parse_action_payload(payload):
    if not isinstance(payload, str) or len(payload.encode("utf-8")) > 8192:
        raise RuntimeErrorWithContext("action payload is invalid")
    try:
        parsed = urllib.parse.parse_qs(
            payload,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=8,
        )
    except ValueError as error:
        raise RuntimeErrorWithContext(
            "action payload is malformed"
        ) from error
    if any(len(values) != 1 for values in parsed.values()):
        raise RuntimeErrorWithContext(
            "action payload contains duplicate fields"
        )
    fields = {key: values[0] for key, values in parsed.items()}
    action = fields.get("action")
    allowed = {
        "run-command": {
            "action",
            "target",
            "arguments",
            "environment",
        },
        "install-dependency": {"action", "dependency"},
        "container": {"action", "operation"},
        "choose-file": {"action"},
    }
    if action not in allowed or set(fields) != allowed[action]:
        raise RuntimeErrorWithContext(
            "action payload contains unsupported fields"
        )
    if (
        action == "container"
        and fields["operation"] not in CONTAINER_OPERATIONS
    ):
        raise RuntimeErrorWithContext(
            "container operation is unsupported"
        )
    return fields


def resolve_command_target(context, target):
    raw = target.strip()
    if not raw:
        candidate = context["executable"]
    elif re.match(r"^[A-Za-z]:[\\/]", raw):
        if raw[0].lower() != "c":
            raise RuntimeErrorWithContext(
                "only the Wine C: drive is available"
            )
        relative = raw[3:].replace("\\", "/")
        candidate = context["prefix"] / "drive_c" / relative
    elif raw.startswith("prefix:"):
        candidate = context["prefix"] / raw[len("prefix:") :].lstrip(
            "/\\"
        )
    elif raw.startswith("install:"):
        candidate = context["install_path"] / raw[
            len("install:") :
        ].lstrip("/\\")
    else:
        raw_path = Path(raw).expanduser()
        candidate = (
            raw_path
            if raw_path.is_absolute()
            else context["install_path"] / raw_path
        )

    resolved = candidate.resolve()
    allowed_roots = (
        context["install_path"].resolve(),
        context["prefix"].resolve(),
    )
    if not any(
        resolved == root or resolved.is_relative_to(root)
        for root in allowed_roots
    ):
        raise RuntimeErrorWithContext(
            "run-command target must stay inside the game or its prefix"
        )
    if not resolved.is_file():
        raise RuntimeErrorWithContext(
            f"run-command target does not exist: {resolved}"
        )
    try:
        with resolved.open("rb") as stream:
            magic = stream.read(2)
    except OSError as error:
        raise RuntimeErrorWithContext(
            f"could not inspect run-command target: {resolved}"
        ) from error
    if magic != b"MZ":
        raise RuntimeErrorWithContext(
            f"run-command target is not a PE executable: {resolved}"
        )
    return resolved


def parse_command_arguments(value):
    if len(value) > 8192:
        raise RuntimeErrorWithContext(
            "run-command arguments are too long"
        )
    try:
        arguments = shlex.split(value, posix=True)
    except ValueError as error:
        raise RuntimeErrorWithContext(
            "run-command arguments are malformed"
        ) from error
    if len(arguments) > 128 or any(
        len(argument) > 4096 for argument in arguments
    ):
        raise RuntimeErrorWithContext(
            "run-command argument vector is too large"
        )
    return arguments


def parse_command_environment(value):
    if len(value) > 8192:
        raise RuntimeErrorWithContext(
            "run-command environment is too large"
        )
    result = {}
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if len(result) >= 32 or "=" not in line:
            raise RuntimeErrorWithContext(
                "run-command environment is malformed"
            )
        name, variable_value = line.split("=", 1)
        if (
            not ENVIRONMENT_NAME_PATTERN.fullmatch(name)
            or len(variable_value) > 2048
            or "\0" in variable_value
        ):
            raise RuntimeErrorWithContext(
                f"run-command environment variable is invalid: {name}"
            )
        upper_name = name.upper()
        if (
            upper_name in RESERVED_ENVIRONMENT_NAMES_UPPER
            or any(
                upper_name.startswith(prefix)
                for prefix in RESERVED_ENVIRONMENT_PREFIXES
            )
        ):
            raise RuntimeErrorWithContext(
                f"run-command cannot override reserved variable: {name}"
            )
        if name in result:
            raise RuntimeErrorWithContext(
                f"run-command environment variable is duplicated: {name}"
            )
        result[name] = variable_value
    return result


def job_paths(appid, job_id):
    appid = parse_appid(appid)
    if not ACTION_JOB_ID_PATTERN.fullmatch(job_id):
        raise RuntimeErrorWithContext("action job ID is invalid")
    directory = default_job_root() / str(appid)
    return {
        "status": directory / f"{job_id}.json",
        "log": directory / f"{job_id}.log",
    }


def write_job_status(path, appid, job_id, action, state, **values):
    atomic_write_json(
        path,
        {
            "schema": 1,
            "appid": appid,
            "job_id": job_id,
            "action": action,
            "state": state,
            **values,
        },
    )


def open_private_log(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    return os.fdopen(descriptor, "a", encoding="utf-8")


def run_job_process(context, command, environment, log_path, description):
    with open_private_log(log_path) as stream:
        stream.write(f"\n[{utc_timestamp()}] {description}\n")
        stream.write(f"$ {shlex.join(str(part) for part in command)}\n")
        stream.flush()
        return subprocess.run(
            [str(part) for part in command],
            cwd=str(context["install_path"]),
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )


def build_native_helper_environment(environment):
    return {
        name: value
        for name, value in environment.items()
        if name in NATIVE_HELPER_ENVIRONMENT_NAMES
    }


def load_dependency_catalog(path=None):
    catalog_path = (
        Path(path).expanduser()
        if path is not None
        else default_dependency_catalog()
    )
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeErrorWithContext(
            f"dependency catalog is invalid: {catalog_path}"
        ) from error
    dependencies = catalog.get("dependencies")
    if catalog.get("schema") != 1 or not isinstance(
        dependencies, list
    ):
        raise RuntimeErrorWithContext(
            f"dependency catalog schema is unsupported: {catalog_path}"
        )
    normalized = {}
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise RuntimeErrorWithContext(
                f"dependency catalog entry is invalid: {catalog_path}"
            )
        dependency_id = dependency.get("id")
        filename = dependency.get("filename")
        url = dependency.get("url")
        digest = dependency.get("sha256")
        size = dependency.get("size")
        arguments = dependency.get("arguments")
        success_codes = dependency.get("success_codes")
        parsed_url = urllib.parse.urlparse(url or "")
        valid = (
            isinstance(dependency_id, str)
            and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,31}", dependency_id)
            and dependency_id not in normalized
            and isinstance(dependency.get("name"), str)
            and bool(dependency["name"])
            and isinstance(dependency.get("description"), str)
            and isinstance(dependency.get("publisher"), str)
            and isinstance(filename, str)
            and Path(filename).name == filename
            and filename.lower().endswith(".exe")
            and parsed_url.scheme == "https"
            and parsed_url.hostname in DEPENDENCY_DOWNLOAD_HOSTS
            and isinstance(digest, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest)
            and isinstance(size, int)
            and 0 < size <= 512 * 1024 * 1024
            and isinstance(arguments, list)
            and all(
                isinstance(argument, str) and len(argument) <= 256
                for argument in arguments
            )
            and isinstance(success_codes, list)
            and bool(success_codes)
            and all(
                isinstance(code, int) and 0 <= code <= 65535
                for code in success_codes
            )
        )
        if not valid:
            raise RuntimeErrorWithContext(
                f"dependency catalog entry is invalid: {dependency_id}"
            )
        normalized[dependency_id] = dependency
    return normalized


def download_dependency(dependency, cache_root=None):
    cache = (
        Path(cache_root).expanduser()
        if cache_root is not None
        else default_dependency_cache()
    )
    cache.mkdir(parents=True, exist_ok=True)
    cache.chmod(0o700)
    destination = (
        cache
        / (
            f"{dependency['id']}-"
            f"{dependency['sha256'][:16]}-{dependency['filename']}"
        )
    )
    if destination.is_file():
        if (
            destination.stat().st_size == dependency["size"]
            and file_sha256(destination) == dependency["sha256"]
        ):
            return destination
        destination.unlink()

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{dependency['id']}.", dir=str(cache)
    )
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(
            dependency["url"],
            headers={"User-Agent": "RealSteamOnMac/1"},
        )
        total = 0
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = (
                response.geturl()
                if callable(getattr(response, "geturl", None))
                else dependency["url"]
            )
            parsed_final_url = urllib.parse.urlparse(final_url)
            if (
                parsed_final_url.scheme != "https"
                or parsed_final_url.hostname
                not in DEPENDENCY_DOWNLOAD_HOSTS
            ):
                raise RuntimeErrorWithContext(
                    "dependency download redirected to an untrusted host"
                )
            with os.fdopen(descriptor, "wb") as output:
                descriptor = -1
                for chunk in iter(
                    lambda: response.read(1024 * 1024), b""
                ):
                    total += len(chunk)
                    if total > dependency["size"]:
                        raise RuntimeErrorWithContext(
                            "dependency download exceeded its expected size"
                        )
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        if (
            total != dependency["size"]
            or digest.hexdigest() != dependency["sha256"]
        ):
            raise RuntimeErrorWithContext(
                "dependency download did not match its manifest"
            )
        temporary.chmod(0o600)
        os.replace(temporary, destination)
        return destination
    except OSError as error:
        raise RuntimeErrorWithContext(
            f"dependency download failed: {dependency['id']}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def execute_run_command_action(context, runtime_root, fields, log_path):
    config = load_config(context)
    _, _, _, wine64, environment = prepare(
        context, runtime_root, config
    )
    target = resolve_command_target(context, fields["target"])
    arguments = parse_command_arguments(fields["arguments"])
    environment.update(
        parse_command_environment(fields["environment"])
    )
    command = [wine64, target, *arguments]
    log_event(
        context,
        {
            "event": "run-command",
            "target": str(target),
            "arguments": arguments,
        },
    )
    result = run_job_process(
        context,
        command,
        environment,
        log_path,
        "run command",
    )
    return result.returncode, {
        "target": str(target),
        "renderer": config["renderer"],
    }


def execute_dependency_action(context, runtime_root, fields, log_path):
    catalog = load_dependency_catalog()
    dependency = catalog.get(fields["dependency"])
    if dependency is None:
        raise RuntimeErrorWithContext(
            f"dependency is not in the catalog: {fields['dependency']}"
        )
    config = load_config(context)
    _, manifest, _, wine64, environment = prepare(
        context, runtime_root, config
    )
    installer = download_dependency(dependency)
    command = [wine64, installer, *dependency["arguments"]]
    result = run_job_process(
        context,
        command,
        environment,
        log_path,
        f"install dependency {dependency['id']}",
    )
    if result.returncode not in dependency["success_codes"]:
        raise RuntimeErrorWithContext(
            f"dependency installer exited with {result.returncode}"
        )
    receipt = (
        context["state"]
        / "dependencies"
        / f"{dependency['id']}.json"
    )
    atomic_write_json(
        receipt,
        {
            "schema": 1,
            "dependency": dependency["id"],
            "name": dependency["name"],
            "sha256": dependency["sha256"],
            "package_id": manifest["package_id"],
            "renderer": config["renderer"],
            "installed_at": utc_timestamp(),
            "exit_code": result.returncode,
        },
    )
    log_event(
        context,
        {
            "event": "dependency-install",
            "dependency": dependency["id"],
            "exit_code": result.returncode,
        },
    )
    return result.returncode, {
        "dependency": dependency["id"],
        "receipt": str(receipt),
        "renderer": config["renderer"],
    }


def execute_configured_launcher_recovery(
    context, wine64, environment, catalog_path=None
):
    path = (
        Path(catalog_path).expanduser()
        if catalog_path is not None
        else default_dependency_catalog()
    )
    try:
        recipes = load_launcher_recovery_catalog(path)
        recipe = recipes.get(context["appid"])
        if recipe is None:
            return {
                "state": "not-configured",
                "snapshot_path": "",
                "report_path": "",
                "steps": [],
            }
        result = execute_launcher_recovery(
            context,
            recipe,
            wine64,
            environment,
        )
    except LauncherRecoveryError as error:
        raise RuntimeErrorWithContext(str(error)) from error
    log_event(
        context,
        {
            "event": "launcher-recovery",
            "state": result["state"],
            "snapshot_path": result["snapshot_path"],
            "report_path": result["report_path"],
            "steps": [
                step["id"] for step in result.get("steps", [])
            ],
        },
    )
    return result


def choose_executable_file():
    script = (
        'set chosenFile to choose file with prompt '
        '"Select a Windows executable or batch file"\n'
        "return POSIX path of chosenFile"
    )
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeErrorWithContext(
            "file selection was cancelled or failed"
        )
    raw_selected = Path(result.stdout.strip()).expanduser()
    if (
        raw_selected.is_symlink()
        or not raw_selected.is_file()
        or raw_selected.suffix.lower() not in {".exe", ".bat", ".cmd"}
    ):
        raise RuntimeErrorWithContext(
            "selected file is not a supported Windows executable"
        )
    selected = raw_selected.resolve()
    if selected.suffix.lower() == ".exe":
        with selected.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise RuntimeErrorWithContext(
                    "selected executable is not a PE file"
                )
    return selected


def execute_choose_file_action(context):
    selected = choose_executable_file()
    allowed_roots = (
        context["install_path"].resolve(),
        context["prefix"].resolve(),
    )
    if not any(
        selected == root or selected.is_relative_to(root)
        for root in allowed_roots
    ):
        raise RuntimeErrorWithContext(
            "run-command file selection must stay inside the game or prefix"
        )
    return 0, {"target": str(selected)}


def execute_container_action(context, runtime_root, fields, log_path):
    operation = fields["operation"]
    config = load_config(context)
    if operation == "delete-container":
        package, manifest, wine_root, wine64, _ = load_selected_package(
            runtime_root, config
        )
        environment = build_environment(
            context, config, wine_root
        )
        if context["prefix"].exists():
            run_job_process(
                context,
                [wine_root / "bin" / "wineserver", "-k"],
                environment,
                log_path,
                "stop container processes",
            )
            recovery_root = context["state"] / "recovery"
            recovery_root.mkdir(parents=True, exist_ok=True)
            recovery_root.chmod(0o700)
            destination = recovery_root / (
                "pfx-" + datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%S%fZ"
                )
            )
            os.replace(context["prefix"], destination)
            log_event(
                context,
                {
                    "event": "container-recovered",
                    "path": str(destination),
                    "package_id": manifest["package_id"],
                },
            )
            return 0, {
                "operation": operation,
                "recovery_path": str(destination),
            }
        return 0, {
            "operation": operation,
            "recovery_path": "",
        }

    _, _, wine_root, wine64, environment = prepare(
        context, runtime_root, config
    )
    if operation == "open-c-drive":
        command = ["/usr/bin/open", context["prefix"] / "drive_c"]
        environment = build_native_helper_environment(environment)
    elif operation == "install-application":
        selected = choose_executable_file()
        command = (
            [wine64, "cmd", "/c", selected]
            if selected.suffix.lower() in {".bat", ".cmd"}
            else [wine64, selected]
        )
    elif operation == "wine-configuration":
        command = [wine64, "winecfg"]
    elif operation == "controllers":
        command = [wine64, "control", "joy.cpl"]
    elif operation == "restart":
        command = [wine64, "wineboot", "--restart"]
    elif operation == "task-manager":
        command = [wine64, "taskmgr"]
    else:
        command = [wine_root / "bin" / "wineserver", "-k"]
    result = run_job_process(
        context,
        command,
        environment,
        log_path,
        f"container operation {operation}",
    )
    return result.returncode, {
        "operation": operation,
        "renderer": config["renderer"],
    }


def action_job(args):
    appid = parse_appid(args.appid)
    paths = job_paths(appid, args.job_id)
    action = "unknown"
    started_at = utc_timestamp()
    try:
        fields = parse_action_payload(args.payload)
        action = fields["action"]
        write_job_status(
            paths["status"],
            appid,
            args.job_id,
            action,
            "running",
            started_at=started_at,
            log_path=str(paths["log"]),
        )
        context = resolve_app_context(appid)
        runtime_root = Path(args.runtime_root).expanduser().resolve()
        context["state"].mkdir(parents=True, exist_ok=True)
        context["state"].chmod(0o700)
        action_lock_path = context["state"] / "action.lock"
        with action_lock_path.open("a+", encoding="utf-8") as action_lock:
            action_lock_path.chmod(0o600)
            fcntl.flock(action_lock.fileno(), fcntl.LOCK_EX)
            if action == "run-command":
                exit_code, result = execute_run_command_action(
                    context, runtime_root, fields, paths["log"]
                )
                if exit_code != 0:
                    raise RuntimeErrorWithContext(
                        f"run command exited with {exit_code}"
                    )
            elif action == "install-dependency":
                exit_code, result = execute_dependency_action(
                    context, runtime_root, fields, paths["log"]
                )
                if exit_code != 0:
                    raise RuntimeErrorWithContext(
                        f"dependency installation exited with {exit_code}"
                    )
            elif action == "container":
                exit_code, result = execute_container_action(
                    context, runtime_root, fields, paths["log"]
                )
                if exit_code != 0:
                    raise RuntimeErrorWithContext(
                        f"container operation exited with {exit_code}"
                    )
            else:
                exit_code, result = execute_choose_file_action(context)
        write_job_status(
            paths["status"],
            appid,
            args.job_id,
            action,
            "completed",
            started_at=started_at,
            finished_at=utc_timestamp(),
            exit_code=exit_code,
            log_path=str(paths["log"]),
            result=result,
        )
        return 0
    except Exception as error:
        message = (
            str(error)
            if isinstance(error, RuntimeErrorWithContext)
            else f"unexpected action failure: {error}"
        )
        write_job_status(
            paths["status"],
            appid,
            args.job_id,
            action,
            "failed",
            started_at=started_at,
            finished_at=utc_timestamp(),
            exit_code=1,
            log_path=str(paths["log"]),
            message=message,
        )
        with open_private_log(paths["log"]) as stream:
            stream.write(f"[{utc_timestamp()}] ERROR: {message}\n")
        print(f"error: {message}", file=sys.stderr)
        return 1


def list_dependencies(args):
    dependencies = load_dependency_catalog(args.catalog)
    public = [
        {
            key: dependency[key]
            for key in (
                "id",
                "name",
                "description",
                "publisher",
                "size",
            )
        }
        for dependency in dependencies.values()
    ]
    print(json.dumps(public, indent=2, sort_keys=True))
    return 0


def plan(context, runtime_root, config, arguments):
    package, manifest, wine_root, wine64, tool = load_selected_package(
        runtime_root, config
    )
    bridge = load_steamworks_bridge(
        package, manifest, wine_root, config["renderer"]
    )
    dxmt_winemac_compat = load_dxmt_winemac_compat(
        package, manifest, wine_root, config["renderer"]
    )
    environment = build_environment(
        context,
        config,
        wine_root,
        bridge,
        dxmt_winemac_compat,
    )
    interesting = {
        key: environment[key]
        for key in sorted(environment)
        if key.startswith(("WINE", "D3DM", "MTL_", "ROSETTA_", "MVK_"))
        or key.startswith("REALSTEAMONMAC_")
        or key
        in {
            "SteamAppId",
            "SteamGameId",
            "STEAM_COMPAT_APP_ID",
            "STEAM_COMPAT_DATA_PATH",
            "STEAM_COMPAT_CLIENT_INSTALL_PATH",
            "DYLD_INSERT_LIBRARIES",
        }
    }
    return {
        "appid": context["appid"],
        "executable": str(context["executable"]),
        "working_directory": str(
            context.get(
                "working_directory", context["install_path"]
            )
        ),
        "arguments": list(arguments),
        "steamapps": str(context["steamapps"]),
        "compat_data": str(context["compat_data"]),
        "prefix": str(context["prefix"]),
        "config_path": str(context["config"]),
        "runtime_root": str(runtime_root),
        "package": str(package),
        "package_id": manifest["package_id"],
        "renderer": config["renderer"],
        "compat_tool": (
            tool["strToolName"] if tool is not None else ""
        ),
        "steamworks_bridge": (
            bridge["metadata"].get("name", "lsteamclient")
            if bridge is not None
            else None
        ),
        "dxmt_winemac_compat": (
            dxmt_winemac_compat["metadata"].get(
                "name", "DXMT Wine macdrv compatibility"
            )
            if dxmt_winemac_compat is not None
            else None
        ),
        "wine_root": str(wine_root),
        "wine64": str(wine64),
        "environment": interesting,
    }


def run_game_process(context, wine_root, command, environment):
    result = subprocess.run(
        [str(part) for part in command],
        cwd=str(
            context.get(
                "working_directory", context["install_path"]
            )
        ),
        env=environment,
        check=False,
    )
    if context["appid"] not in POST_EXIT_PREFIX_KILL_APPIDS:
        return result.returncode

    wineserver = wine_root / "bin" / "wineserver"
    cleanup = subprocess.run(
        [str(wineserver), "-k"],
        cwd=str(context["install_path"]),
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    log_event(
        context,
        {
            "event": "post-exit-prefix-cleanup",
            "game_exit_code": result.returncode,
            "wineserver_exit_code": cleanup.returncode,
        },
    )
    if cleanup.returncode != 0:
        raise RuntimeErrorWithContext(
            "failed to terminate the per-game Wine session after exit"
        )
    return result.returncode


def launch(args):
    if args.appid:
        context = resolve_app_context(
            args.appid,
            requested_target=Path(args.executable),
        )
        if args.compat_data:
            requested_compat_data = (
                Path(args.compat_data).expanduser().resolve()
            )
            if requested_compat_data != context["compat_data"]:
                raise RuntimeErrorWithContext(
                    "compatibility data path must use the Proton layout: "
                    f"expected {context['compat_data']}, "
                    f"got {requested_compat_data}"
                )
    else:
        context = resolve_context(
            Path(args.executable), args.appid, args.compat_data
        )
    launch_arguments = (
        list(args.arguments)
        if args.arguments
        else parse_launch_arguments(
            context.get("launch_arguments", "")
        )
    )
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    config = load_config(context)
    launch_plan = plan(
        context, runtime_root, config, launch_arguments
    )
    if args.dry_run:
        print(json.dumps(launch_plan, indent=2, sort_keys=True))
        return 0

    _, _, wine_root, wine64, environment = prepare(
        context, runtime_root, config
    )
    execute_configured_launcher_recovery(
        context, wine64, environment
    )
    command = (
        [str(wine64), str(context["executable"])]
        + launch_arguments
    )
    log_event(
        context,
        {
            "event": "launch",
            "renderer": config["renderer"],
            "command": command,
            "prefix": str(context["prefix"]),
        },
    )
    return run_game_process(
        context, wine_root, command, environment
    )


def recover_launcher(args):
    context = resolve_app_context(
        args.appid,
        requested_target=Path(args.executable),
    )
    if args.compat_data:
        requested_compat_data = (
            Path(args.compat_data).expanduser().resolve()
        )
        if requested_compat_data != context["compat_data"]:
            raise RuntimeErrorWithContext(
                "compatibility data path must use the Proton layout: "
                f"expected {context['compat_data']}, "
                f"got {requested_compat_data}"
            )
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    config = load_config(context)
    _, _, _, wine64, environment = prepare(
        context, runtime_root, config
    )
    result = execute_configured_launcher_recovery(
        context, wine64, environment
    )
    if result["state"] == "not-configured":
        raise RuntimeErrorWithContext(
            f"no launcher recovery is configured for AppID "
            f"{context['appid']}"
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def prepare_prefix(args):
    context = resolve_context(
        Path(args.executable), args.appid, args.compat_data
    )
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    config = load_config(context)
    prepare(context, runtime_root, config)
    print(context["prefix"])
    return 0


def configure(args):
    context = resolve_context(
        Path(args.executable), args.appid, args.compat_data
    )
    config = load_config(context)
    if args.renderer is not None:
        config["renderer"] = args.renderer
    for key in ("msync", "retina", "metal_hud", "metalfx", "dxr", "avx"):
        value = getattr(args, key)
        if value is not None:
            config[key] = value == "on"
    saved = save_config(context, config)
    print(json.dumps(saved, indent=2, sort_keys=True))
    return 0


def show_config(args):
    context = resolve_context(
        Path(args.executable), args.appid, args.compat_data
    )
    print(json.dumps(load_config(context), indent=2, sort_keys=True))
    return 0


def add_context_arguments(parser):
    parser.add_argument("--appid")
    parser.add_argument("--compat-data")
    parser.add_argument(
        "--runtime-root", default=str(default_runtime_root())
    )
    parser.add_argument("executable")


def build_parser():
    parser = argparse.ArgumentParser(
        description="RealSteamOnMac independent Wine runtime"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch_parser = subparsers.add_parser("launch")
    add_context_arguments(launch_parser)
    launch_parser.add_argument("--dry-run", action="store_true")
    launch_parser.add_argument(
        "arguments", nargs=argparse.REMAINDER
    )
    launch_parser.set_defaults(handler=launch)

    recovery_parser = subparsers.add_parser("recover-launcher")
    add_context_arguments(recovery_parser)
    recovery_parser.set_defaults(handler=recover_launcher)

    prepare_parser = subparsers.add_parser("prepare-prefix")
    add_context_arguments(prepare_parser)
    prepare_parser.set_defaults(handler=prepare_prefix)

    configure_parser = subparsers.add_parser("configure")
    add_context_arguments(configure_parser)
    configure_parser.add_argument(
        "--renderer", choices=RENDERERS
    )
    for key in ("msync", "retina", "metal_hud", "metalfx", "dxr", "avx"):
        configure_parser.add_argument(
            f"--{key.replace('_', '-')}", choices=("on", "off")
        )
    configure_parser.set_defaults(handler=configure)

    show_parser = subparsers.add_parser("show-config")
    add_context_arguments(show_parser)
    show_parser.set_defaults(handler=show_config)

    action_parser = subparsers.add_parser("action")
    action_parser.add_argument("--appid", required=True)
    action_parser.add_argument("--job-id", required=True)
    action_parser.add_argument("--payload", required=True)
    action_parser.add_argument(
        "--runtime-root", default=str(default_runtime_root())
    )
    action_parser.set_defaults(handler=action_job)

    dependencies_parser = subparsers.add_parser(
        "list-dependencies"
    )
    dependencies_parser.add_argument(
        "--catalog", default=str(default_dependency_catalog())
    )
    dependencies_parser.set_defaults(handler=list_dependencies)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except RuntimeErrorWithContext as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
