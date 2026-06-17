#!/usr/bin/python3

import argparse
import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
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
    FULLY_INSTALLED,
    SteamAppStateError,
    inspect_app_manifest,
    manifest_install_directory,
)


RENDERERS = ("gptk", "dxmt", "dxvk", "wined3d")
LEGACY_STEAMWORKS_RENDERERS = ("dxmt", "dxvk", "wined3d")
STEAMWORKS_UNIX_INSTALL_NAMES = frozenset(
    ("lsteamclient.so", "lsteamclient.dll.so")
)
# People Playground's .NET mod compiler mistakes its Wine PID for a macOS PID.
# It can therefore survive the game indefinitely and keep Steam's AppID active.
POST_EXIT_PREFIX_KILL_APPIDS = frozenset((1118200,))
ACTION_JOB_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
CONTROLLER_READABILITY_DPI = 192
WINE_DESKTOP_REGISTRY_KEY = r"HKCU\Control Panel\Desktop"
WINE_LOGPIXELS_VALUE = "LogPixels"
CONTAINER_OPERATIONS = frozenset(
    (
        "open-c-drive",
        "wine-configuration",
        "controllers",
        "restart",
        "task-manager",
        "quit-all",
        "delete-container",
    )
)
RECOVERABLE_REPAIR_STATES = frozenset(("files-missing",))
WINDOWS_RUN_BUILTINS = {
    "cmd": "cmd.exe",
    "cmd.exe": "cmd.exe",
    "control": "control.exe",
    "control.exe": "control.exe",
    "explorer": "explorer.exe",
    "explorer.exe": "explorer.exe",
    "notepad": "notepad.exe",
    "notepad.exe": "notepad.exe",
    "regedit": "regedit.exe",
    "regedit.exe": "regedit.exe",
    "taskmgr": "taskmgr.exe",
    "taskmgr.exe": "taskmgr.exe",
    "winecfg": "winecfg",
    "winecfg.exe": "winecfg",
}
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
        "us.download.nvidia.com",
    )
)
DEPENDENCY_INSTALLERS = frozenset(("exe", "msi", "directx-redist"))
DEPENDENCY_POSTCONDITIONS = frozenset(
    ("file", "file-any", "file-sha256", "registry-key")
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
RAW_COMPONENT_KINDS = frozenset(("gptk", "dxmt", "dxvk", "wine"))
RAW_COMPONENT_OVERLAYS = {
    "gptk": (
        ("external", "lib/external"),
        ("wine", "lib/wine"),
    ),
    "dxmt": (
        ("x86_64-unix", "lib/wine/x86_64-unix"),
        ("x86_64-windows", "lib/wine/x86_64-windows"),
        ("i386-windows", "lib/wine/i386-windows"),
    ),
    "dxvk": (
        ("x86_64-windows", "lib/wine/x86_64-windows"),
        ("i386-windows", "lib/wine/i386-windows"),
    ),
}
COMPOSITION_SCHEMA = 1
_CLONEFILE = None
_CLONEFILE_LOADED = False


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


def inspect_action_state(appid, steam_root=None):
    appid = parse_appid(appid)
    for library_root in steam_library_roots(steam_root):
        steamapps = library_root / "steamapps"
        manifest = steamapps / f"appmanifest_{appid}.acf"
        if not manifest.is_file():
            continue
        try:
            installdir = manifest_install_directory(manifest, appid)
            install_path = (steamapps / "common" / installdir).resolve()
        except SteamAppStateError as error:
            return {
                "installed": False,
                "container_exists": False,
                "manifest_diagnostic": "manifest-invalid",
                "manifest_message": str(error),
            }
        if not install_path.is_dir():
            return {
                "installed": False,
                "container_exists": False,
                "manifest_diagnostic": "install-directory-missing",
            }
        try:
            install_state = inspect_app_manifest(
                manifest, appid, install_path
            )
        except SteamAppStateError as error:
            return {
                "installed": False,
                "container_exists": False,
                "manifest_diagnostic": "manifest-invalid",
                "manifest_message": str(error),
            }
        installed = install_state["diagnostic"] in {
            "ready",
            "repair-required",
        }
        compat_data = steamapps / "compatdata" / str(appid)
        if not installed or compat_data.is_symlink():
            container_exists = False
        else:
            prefix = compat_data / "pfx"
            container_exists = prefix.is_dir() and not prefix.is_symlink()
        return {
            "installed": installed,
            "container_exists": container_exists,
            "manifest_diagnostic": install_state["diagnostic"],
            "state_flags": install_state["state_flags"],
            "size_on_disk": install_state["size_on_disk"],
            "installed_depot_count": install_state[
                "installed_depot_count"
            ],
            "staged_depot_count": install_state["staged_depot_count"],
            "install_path_nonempty": install_state["install_path_nonempty"],
        }
    return {
        "installed": False,
        "container_exists": False,
        "manifest_diagnostic": "manifest-missing",
    }


def resolve_existing_action_context(appid, steam_root=None):
    installation = find_app_installation(appid, steam_root)
    compat_data = (
        installation["steamapps"]
        / "compatdata"
        / str(installation["appid"])
    )
    if compat_data.is_symlink():
        raise RuntimeErrorWithContext(
            f"compatibility data path must not be a symlink: {compat_data}"
        )
    compat_data = compat_data.resolve()
    prefix = compat_data / "pfx"
    if prefix.is_symlink() or not prefix.is_dir():
        raise RuntimeErrorWithContext(
            f"container has not been created for AppID {installation['appid']}"
        )
    state = compat_data / "realsteamonmac"
    return {
        "appid": installation["appid"],
        "executable": None,
        "working_directory": installation["install_path"],
        "install_path": installation["install_path"],
        "steamapps": installation["steamapps"],
        "compat_data": compat_data,
        "prefix": prefix,
        "state": state,
        "config": state / "config.json",
        "global_config": (
            default_app_config_root()
            / f"{installation['appid']}.json"
        ),
        "logs": state / "logs",
    }


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


def install_state_error_message(appid, install_state):
    return (
        "Steam app installation is incomplete "
        f"({install_state['diagnostic']}): AppID {appid}; "
        "use Steam's install or repair action"
    )


def install_state_allows_verified_launch(install_state):
    if install_state["launchable"]:
        return True, None
    if install_state["diagnostic"] != "repair-required":
        return False, None
    blocking_states = set(install_state["blocking_states"])
    if not blocking_states or blocking_states - RECOVERABLE_REPAIR_STATES:
        return False, None
    if not install_state["state_flags"] & FULLY_INSTALLED:
        return False, None
    if install_state["size_on_disk"] <= 0:
        return False, None
    if install_state["installed_depot_count"] <= 0:
        return False, None
    if install_state["installed_depot_bytes"] <= 0:
        return False, None
    if install_state["staged_depot_count"] != 0:
        return False, None
    if install_state["staged_depot_bytes"] != 0:
        return False, None
    for key in (
        "bytes_to_download",
        "bytes_downloaded",
        "bytes_to_stage",
        "bytes_staged",
    ):
        if install_state.get(key, 0) != 0:
            return False, None
    if not install_state["install_path_nonempty"]:
        return False, None
    return (
        True,
        "Steam manifest reports files-missing, but the selected Windows "
        "executable exists and the depot has no pending download or staging "
        "bytes",
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
    if (
        not installation["install_state"]["launchable"]
        and installation["install_state"]["diagnostic"] != "repair-required"
    ):
        raise RuntimeErrorWithContext(
            install_state_error_message(
                installation["appid"], installation["install_state"]
            )
        )
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
    allowed, warning = install_state_allows_verified_launch(
        installation["install_state"]
    )
    if not allowed:
        raise RuntimeErrorWithContext(
            install_state_error_message(
                installation["appid"], installation["install_state"]
            )
        )
    context["install_path"] = installation["install_path"]
    context["install_state"] = installation["install_state"]
    if warning is not None:
        context["install_warning"] = warning
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


def _load_package_path(package, renderer, expected_package_id=None):
    package = Path(package).resolve()
    if not package.is_dir():
        raise RuntimeErrorWithContext(
            f"runtime package is unavailable: {package}"
        )
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
        expected_package_id
        and manifest["package_id"] != expected_package_id
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


def load_package(runtime_root, renderer, runtime_package=None):
    if runtime_package:
        package = runtime_root / "packages" / runtime_package
        expected_package_id = runtime_package
    else:
        current = runtime_root / "current"
        if not current.exists():
            raise RuntimeErrorWithContext(
                f"no active runtime package: {current}"
            )
        package = current
        expected_package_id = None
    return _load_package_path(package, renderer, expected_package_id)


def _safe_tree_entries(root):
    try:
        with os.scandir(root) as entries:
            return sorted(entries, key=lambda entry: entry.name)
    except OSError as error:
        raise RuntimeErrorWithContext(
            f"cannot scan runtime payload tree: {root}"
        ) from error


def _validate_internal_symlink(path, root):
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise RuntimeErrorWithContext(
            f"runtime payload symlink is invalid: {path}"
        ) from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeErrorWithContext(
            f"runtime payload symlink escapes its source tree: {path}"
        ) from error
    return resolved


def _mapped_symlink_target(
    source_path,
    source_root,
    destination_path,
    destination_root,
):
    resolved = _validate_internal_symlink(source_path, source_root)
    mapped = destination_root / resolved.relative_to(source_root)
    return os.path.relpath(mapped, start=destination_path.parent)


def _tree_fingerprint(root):
    root = Path(root).resolve(strict=True)
    digest = hashlib.sha256()

    def visit(directory):
        for entry in _safe_tree_entries(directory):
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            try:
                metadata = path.lstat()
            except OSError as error:
                raise RuntimeErrorWithContext(
                    f"cannot inspect runtime payload: {path}"
                ) from error
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(metadata.st_mode).encode("ascii"))
            digest.update(b"\0")
            if entry.is_symlink():
                _validate_internal_symlink(path, root)
                digest.update(b"link\0")
                digest.update(os.readlink(path).encode("utf-8"))
            elif entry.is_dir(follow_symlinks=False):
                digest.update(b"directory\0")
                visit(path)
            elif entry.is_file(follow_symlinks=False):
                digest.update(b"file\0")
                digest.update(str(metadata.st_size).encode("ascii"))
                digest.update(b"\0")
                digest.update(str(metadata.st_mtime_ns).encode("ascii"))
            else:
                raise RuntimeErrorWithContext(
                    f"runtime payload contains an unsupported entry: {path}"
                )
            digest.update(b"\0")

    visit(root)
    return digest.hexdigest()


def _make_directory(path, mode):
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode & 0o777)


def _remove_overlay_file(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.exists():
        raise RuntimeErrorWithContext(
            f"runtime payload directory conflicts with a file: {path}"
        )


def _hardlink_tree(source, destination):
    source = Path(source).resolve(strict=True)
    destination = Path(destination)
    _make_directory(destination, source.stat().st_mode)

    def visit(source_directory, destination_directory):
        for entry in _safe_tree_entries(source_directory):
            source_path = Path(entry.path)
            destination_path = destination_directory / entry.name
            if entry.is_symlink():
                _remove_overlay_file(destination_path)
                destination_path.symlink_to(
                    _mapped_symlink_target(
                        source_path,
                        source,
                        destination_path,
                        destination,
                    )
                )
            elif entry.is_dir(follow_symlinks=False):
                if destination_path.exists() and not destination_path.is_dir():
                    raise RuntimeErrorWithContext(
                        "runtime payload directory conflicts with a file: "
                        f"{destination_path}"
                    )
                _make_directory(
                    destination_path, source_path.stat().st_mode
                )
                visit(source_path, destination_path)
            elif entry.is_file(follow_symlinks=False):
                _remove_overlay_file(destination_path)
                try:
                    os.link(source_path, destination_path)
                except OSError as error:
                    raise RuntimeErrorWithContext(
                        "cannot hardlink immutable runtime payload: "
                        f"{source_path}"
                    ) from error
            else:
                raise RuntimeErrorWithContext(
                    "runtime payload contains an unsupported entry: "
                    f"{source_path}"
                )

    visit(source, destination)


def _load_clonefile():
    global _CLONEFILE, _CLONEFILE_LOADED
    if _CLONEFILE_LOADED:
        return _CLONEFILE
    _CLONEFILE_LOADED = True
    if sys.platform != "darwin":
        return None
    try:
        clonefile = ctypes.CDLL(None, use_errno=True).clonefile
    except (AttributeError, OSError):
        return None
    clonefile.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int)
    clonefile.restype = ctypes.c_int
    _CLONEFILE = clonefile
    return _CLONEFILE


def _clone_or_copy_file(source, destination):
    clonefile = _load_clonefile()
    if clonefile is not None:
        result = clonefile(
            os.fsencode(source), os.fsencode(destination), 0
        )
        if result == 0:
            return
        clone_error = ctypes.get_errno()
        if clone_error not in {
            errno.EINVAL,
            errno.ENOSYS,
            errno.ENOTSUP,
            errno.EPERM,
            errno.EXDEV,
        }:
            raise OSError(
                clone_error,
                os.strerror(clone_error),
                str(source),
            )
        if destination.is_symlink() or destination.exists():
            destination.unlink()
    shutil.copy2(source, destination)


def _copy_component_tree(
    source,
    destination,
    component_root,
    component_destination_root,
):
    source = Path(source)
    destination = Path(destination)
    component_root = Path(component_root).resolve(strict=True)
    component_destination_root = Path(component_destination_root)
    if not source.exists():
        return
    _make_directory(destination, source.stat().st_mode)

    def visit(source_directory, destination_directory):
        for entry in _safe_tree_entries(source_directory):
            source_path = Path(entry.path)
            destination_path = destination_directory / entry.name
            if entry.is_symlink():
                _remove_overlay_file(destination_path)
                destination_path.symlink_to(
                    _mapped_symlink_target(
                        source_path,
                        component_root,
                        destination_path,
                        component_destination_root,
                    )
                )
            elif entry.is_dir(follow_symlinks=False):
                if destination_path.exists() and not destination_path.is_dir():
                    raise RuntimeErrorWithContext(
                        "runtime component directory conflicts with a file: "
                        f"{destination_path}"
                    )
                _make_directory(
                    destination_path, source_path.stat().st_mode
                )
                visit(source_path, destination_path)
            elif entry.is_file(follow_symlinks=False):
                _remove_overlay_file(destination_path)
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    _clone_or_copy_file(source_path, destination_path)
                except OSError as error:
                    raise RuntimeErrorWithContext(
                        f"cannot copy runtime component: {source_path}"
                    ) from error
            else:
                raise RuntimeErrorWithContext(
                    "runtime component contains an unsupported entry: "
                    f"{source_path}"
                )

    visit(source, destination)


def _version_major(value):
    if not isinstance(value, str):
        return None
    match = re.search(r"(?<![0-9])([0-9]+)(?:\.[0-9]+)+", value)
    return int(match.group(1)) if match else None


def _selected_bridge_variant(manifest, renderer):
    bridge = manifest.get("steamworks_bridge")
    if not isinstance(bridge, dict):
        return None
    variants = bridge.get("variants")
    if isinstance(variants, dict):
        selected = variants.get(renderer)
        return selected if isinstance(selected, dict) else None
    renderers = bridge.get("renderers")
    if isinstance(renderers, list) and renderer in renderers:
        return bridge
    return None


def _raw_wine_supports_base_bridge(tool, manifest, renderer):
    renderers = manifest.get("renderers")
    if not isinstance(renderers, dict):
        return False
    renderer_metadata = renderers.get(renderer)
    if not isinstance(renderer_metadata, dict):
        return False
    return (
        _version_major(tool.get("version")) is not None
        and _version_major(tool.get("version"))
        == _version_major(renderer_metadata.get("wine"))
    )


def _limit_manifest_to_renderer(manifest, renderer, keep_bridge):
    result = json.loads(json.dumps(manifest))
    renderer_metadata = result.get("renderers", {}).get(renderer, {})
    result["renderers"] = {renderer: renderer_metadata}
    if renderer != "dxmt":
        result.pop("dxmt_winemac_compat", None)
    bridge = result.get("steamworks_bridge")
    if not keep_bridge or not isinstance(bridge, dict):
        result.pop("steamworks_bridge", None)
    elif isinstance(bridge.get("variants"), dict):
        selected = bridge["variants"].get(renderer)
        if isinstance(selected, dict):
            bridge["variants"] = {renderer: selected}
        else:
            result.pop("steamworks_bridge", None)
    elif isinstance(bridge.get("renderers"), list):
        if renderer in bridge["renderers"]:
            bridge["renderers"] = [renderer]
        else:
            result.pop("steamworks_bridge", None)
    return result


def _install_base_bridge_in_raw_wine(
    base_wine_root, destination_wine_root, manifest, renderer
):
    variant = _selected_bridge_variant(manifest, renderer)
    if variant is None:
        return
    unix_name = variant.get("unix_install_name", "lsteamclient.so")
    for relative in (
        Path("lib/wine/x86_64-windows/lsteamclient.dll"),
        Path("lib/wine/x86_64-unix") / unix_name,
    ):
        source = base_wine_root / relative
        destination = destination_wine_root / relative
        if not source.is_file():
            raise RuntimeErrorWithContext(
                f"base Steamworks bridge payload is missing: {source}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        _remove_overlay_file(destination)
        os.link(source, destination)


def _build_composed_package(
    staging,
    base_package,
    base_manifest,
    base_wine_root,
    tool,
    composition,
):
    renderer = tool["renderer"]
    source_kind = tool["sourceKind"]
    component = Path(tool["componentPath"]).resolve(strict=True)
    destination_wine_root = staging / "wine" / renderer
    keep_bridge = source_kind != "wine" or _raw_wine_supports_base_bridge(
        tool, base_manifest, renderer
    )

    if source_kind == "wine":
        _copy_component_tree(
            component,
            destination_wine_root,
            component,
            destination_wine_root,
        )
        wine64 = destination_wine_root / "bin" / "wine64"
        if not wine64.exists():
            wine = destination_wine_root / "bin" / "wine"
            if not wine.is_file() or not os.access(wine, os.X_OK):
                raise RuntimeErrorWithContext(
                    f"raw Wine launcher is unavailable: {wine}"
                )
            wine64.symlink_to("wine")
        if keep_bridge:
            _install_base_bridge_in_raw_wine(
                base_wine_root,
                destination_wine_root,
                base_manifest,
                renderer,
            )
    else:
        _hardlink_tree(base_wine_root, destination_wine_root)
        component_destination_root = (
            destination_wine_root / "lib"
            if source_kind == "gptk"
            else destination_wine_root / "lib" / "wine"
        )
        for source_relative, destination_relative in RAW_COMPONENT_OVERLAYS[
            source_kind
        ]:
            source = component / source_relative
            if source.exists():
                _copy_component_tree(
                    source,
                    destination_wine_root / destination_relative,
                    component,
                    component_destination_root,
                )

    steamworks = base_package / "steamworks"
    if keep_bridge and steamworks.is_dir():
        _hardlink_tree(steamworks, staging / "steamworks")

    manifest = _limit_manifest_to_renderer(
        base_manifest, renderer, keep_bridge
    )
    manifest["package_id"] = composition["package_id"]
    renderer_metadata = manifest["renderers"].setdefault(renderer, {})
    renderer_metadata["user_component"] = tool["strDisplayName"]
    if source_kind == "wine":
        renderer_metadata["wine"] = tool["strDisplayName"]
    else:
        renderer_metadata["graphics"] = tool["strDisplayName"]
    manifest["composition"] = composition
    atomic_write_json(staging / "manifest.json", manifest)
    atomic_write_json(
        staging / ".realsteamonmac-composition.json", composition
    )


def compose_raw_tool_package(runtime_root, tool):
    source_kind = tool.get("sourceKind")
    if source_kind not in RAW_COMPONENT_KINDS:
        raise RuntimeErrorWithContext(
            f"raw compatibility tool kind is unsupported: {source_kind}"
        )
    component = Path(tool.get("componentPath", "")).resolve(strict=True)
    base_package, base_manifest, base_wine_root, _ = load_package(
        runtime_root, tool["renderer"]
    )
    source_fingerprint = _tree_fingerprint(component)
    identity = {
        "schema": COMPOSITION_SCHEMA,
        "base_package_id": base_manifest["package_id"],
        "tool": tool["strToolName"],
        "renderer": tool["renderer"],
        "source_kind": source_kind,
        "component_path": str(component),
        "source_fingerprint": source_fingerprint,
    }
    digest = hashlib.sha256(
        json.dumps(
            identity, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    package_id = f"composed-{digest[:32]}"
    composition = {**identity, "package_id": package_id}
    composed_root = Path(runtime_root) / "composed"
    composed_root.mkdir(parents=True, exist_ok=True)
    composed_root.chmod(0o700)
    destination = composed_root / package_id
    lock_path = composed_root / ".compose.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        lock_path.chmod(0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if destination.exists():
            marker_path = (
                destination / ".realsteamonmac-composition.json"
            )
            try:
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeErrorWithContext(
                    f"composed runtime cache is invalid: {destination}"
                ) from error
            if marker != composition:
                raise RuntimeErrorWithContext(
                    f"composed runtime cache identity changed: {destination}"
                )
            return _load_package_path(
                destination, tool["renderer"], package_id
            )

        staging = Path(
            tempfile.mkdtemp(prefix=".compose-", dir=str(composed_root))
        )
        try:
            _build_composed_package(
                staging,
                base_package,
                base_manifest,
                base_wine_root,
                tool,
                composition,
            )
            if _tree_fingerprint(component) != source_fingerprint:
                raise RuntimeErrorWithContext(
                    "runtime component changed while composing: "
                    f"{component}"
                )
            _load_package_path(staging, tool["renderer"], package_id)
            os.replace(staging, destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return _load_package_path(destination, tool["renderer"], package_id)


def load_selected_package(runtime_root, config):
    tool = load_compat_tool(config["compat_tool"])
    validate_tool_capabilities(config, tool)
    if tool is not None and tool.get("sourceKind") is not None:
        package, manifest, wine_root, wine64 = compose_raw_tool_package(
            runtime_root, tool
        )
    else:
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


def resolve_runtime_payload(package, relative, description):
    if not isinstance(relative, str) or not relative:
        raise RuntimeErrorWithContext(
            f"runtime {description} path is invalid: {package}"
        )
    root = package.resolve()
    candidate = Path(relative)
    if candidate.is_absolute():
        raise RuntimeErrorWithContext(
            f"runtime {description} path is invalid: {package}"
        )
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise RuntimeErrorWithContext(
            f"runtime {description} path escapes package: {package}"
        )
    return resolved


def load_steamworks_bridge(package, manifest, wine_root, renderer):
    bridge = manifest.get("steamworks_bridge")
    if bridge is None:
        return None
    if not isinstance(bridge, dict):
        raise RuntimeErrorWithContext(
            f"runtime Steamworks bridge metadata is invalid: {package}"
        )
    variants = bridge.get("variants")
    if variants is None:
        renderers = bridge.get("renderers")
        if not isinstance(renderers, list) or renderer not in renderers:
            return None
        if renderer not in LEGACY_STEAMWORKS_RENDERERS:
            raise RuntimeErrorWithContext(
                f"Steamworks bridge is unsupported for renderer: {renderer}"
            )
        selected = bridge
        unix_install_name = "lsteamclient.so"
    else:
        if not isinstance(variants, dict):
            raise RuntimeErrorWithContext(
                f"runtime Steamworks bridge variants are invalid: {package}"
            )
        selected = variants.get(renderer)
        if selected is None:
            return None
        if not isinstance(selected, dict):
            raise RuntimeErrorWithContext(
                "runtime Steamworks bridge variant is invalid for "
                f"renderer {renderer}: {package}"
            )
        unix_install_name = selected.get("unix_install_name")
        if unix_install_name not in STEAMWORKS_UNIX_INSTALL_NAMES:
            raise RuntimeErrorWithContext(
                "runtime Steamworks bridge Unix install name is invalid "
                f"for renderer {renderer}: {package}"
            )

    windows_dll = resolve_runtime_payload(
        package,
        selected.get("windows_dll"),
        "Steamworks bridge Windows DLL",
    )
    unix_library = resolve_runtime_payload(
        package,
        selected.get("unix_library"),
        "Steamworks bridge Unix library",
    )
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
        / unix_install_name
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
        "metadata": {**bridge, **selected},
        "windows_dll": windows_dll,
        "unix_library": unix_library,
        "unix_install_name": unix_install_name,
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
        "inspect-state": {"action"},
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
        if candidate is None:
            raise RuntimeErrorWithContext(
                "run-command target is required"
            )
    elif re.match(r"^[A-Za-z]:[\\/]", raw):
        drive = raw[0].lower()
        relative = raw[3:].replace("\\", "/")
        if drive == "c":
            drive_root = context["prefix"] / "drive_c"
        else:
            drive_root = context["prefix"] / "dosdevices" / f"{drive}:"
            if not drive_root.exists() and not drive_root.is_symlink():
                return {"kind": "association", "target": raw}
        candidate = drive_root / relative
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

    if not candidate.exists():
        normalized = raw.casefold()
        builtin = WINDOWS_RUN_BUILTINS.get(normalized)
        if builtin is not None:
            return {"kind": "builtin", "target": builtin}
        if normalized.endswith(".cpl"):
            return {"kind": "control-panel", "target": raw}
        return {"kind": "association", "target": raw}

    resolved = candidate.resolve()
    if resolved.is_dir():
        return {"kind": "association", "target": resolved}
    if not resolved.is_file():
        raise RuntimeErrorWithContext(
            f"run-command target is not a file or directory: {resolved}"
        )
    suffix = resolved.suffix.casefold()
    if suffix == ".exe":
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
        return {"kind": "pe", "target": resolved}
    if suffix in {".bat", ".cmd"}:
        return {"kind": "batch", "target": resolved}
    if suffix == ".cpl":
        return {"kind": "control-panel", "target": resolved}
    return {"kind": "association", "target": resolved}


def parse_command_arguments(value):
    if len(value) > 8192:
        raise RuntimeErrorWithContext(
            "run-command arguments are too long"
        )
    arguments = []
    index = 0
    while index < len(value):
        while index < len(value) and value[index].isspace():
            index += 1
        if index >= len(value):
            break
        argument = []
        quoted = False
        while index < len(value):
            character = value[index]
            if character.isspace() and not quoted:
                break
            if character == "\\":
                slash_count = 0
                while index < len(value) and value[index] == "\\":
                    slash_count += 1
                    index += 1
                if index < len(value) and value[index] == '"':
                    argument.extend("\\" * (slash_count // 2))
                    if slash_count % 2:
                        argument.append('"')
                    else:
                        quoted = not quoted
                    index += 1
                else:
                    argument.extend("\\" * slash_count)
                continue
            if character == '"':
                if (
                    quoted
                    and index + 1 < len(value)
                    and value[index + 1] == '"'
                ):
                    argument.append('"')
                    index += 2
                    continue
                quoted = not quoted
                index += 1
                continue
            argument.append(character)
            index += 1
        if quoted:
            raise RuntimeErrorWithContext(
                "run-command arguments are malformed"
            )
        arguments.append("".join(argument))
        while index < len(value) and value[index].isspace():
            index += 1
    if len(arguments) > 128 or any(
        len(argument) > 4096 for argument in arguments
    ):
        raise RuntimeErrorWithContext(
            "run-command argument vector is too large"
        )
    return arguments


def wineconsole_for(wine64):
    candidate = Path(wine64).parent / "wineconsole"
    return candidate if candidate.is_file() else wine64


def build_run_command_plan(context, wine64, target, argument_text):
    arguments = parse_command_arguments(argument_text)
    resolved = resolve_command_target(context, target)
    if (
        resolved["kind"] == "association"
        and isinstance(resolved["target"], str)
        and not re.match(
            r"^[A-Za-z][A-Za-z0-9+.-]*:",
            resolved["target"],
        )
        and any(
            character.isspace() for character in resolved["target"]
        )
    ):
        inline = parse_command_arguments(resolved["target"])
        if len(inline) > 1:
            resolved = resolve_command_target(context, inline[0])
            arguments = [*inline[1:], *arguments]

    kind = resolved["kind"]
    command_target = resolved["target"]
    if kind == "builtin" and command_target == "cmd.exe":
        command = [wineconsole_for(wine64), command_target, *arguments]
    elif kind in {"pe", "builtin"}:
        command = [wine64, command_target, *arguments]
    elif kind == "control-panel":
        command = [wine64, "control.exe", command_target, *arguments]
    elif isinstance(command_target, Path):
        command = [
            wine64,
            "start.exe",
            "/unix",
            command_target,
            *arguments,
        ]
    else:
        command = [wine64, "start.exe", command_target, *arguments]
    return {
        "kind": kind,
        "target": str(command_target),
        "command": command,
    }


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


def start_job_process(context, command, environment, log_path, description):
    with open_private_log(log_path) as stream:
        stream.write(f"\n[{utc_timestamp()}] {description}\n")
        stream.write(f"$ {shlex.join(str(part) for part in command)}\n")
        stream.flush()
        return subprocess.Popen(
            [str(part) for part in command],
            cwd=str(context["install_path"]),
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def run_job_process_capture(
    context, command, environment, log_path, description
):
    with open_private_log(log_path) as stream:
        stream.write(f"\n[{utc_timestamp()}] {description}\n")
        stream.write(f"$ {shlex.join(str(part) for part in command)}\n")
        stream.flush()
        result = subprocess.run(
            [str(part) for part in command],
            cwd=str(context["install_path"]),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            check=False,
        )
        result.stdout = result.stdout or ""
        stream.write(result.stdout)
        stream.flush()
        return result


def query_wine_registry_dword(
    context, wine64, environment, key, name, log_path
):
    result = run_job_process_capture(
        context,
        [wine64, "reg", "query", key, "/v", name],
        environment,
        log_path,
        f"query Wine registry value {key}\\{name}",
    )
    match = re.search(
        rf"^\s*{re.escape(name)}\s+REG_DWORD\s+0x([0-9a-f]+)\s*$",
        result.stdout,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if result.returncode == 0 and match:
        return int(match.group(1), 16)
    if result.returncode != 0 and re.search(
        r"(unable to find|not found)",
        result.stdout,
        flags=re.IGNORECASE,
    ):
        return None
    raise RuntimeErrorWithContext(
        f"cannot read Wine registry value {key}\\{name}; "
        f"see {log_path}"
    )


def set_wine_registry_dword(
    context, wine64, environment, key, name, value, log_path
):
    result = run_job_process(
        context,
        [
            wine64,
            "reg",
            "add",
            key,
            "/v",
            name,
            "/t",
            "REG_DWORD",
            "/d",
            str(value),
            "/f",
        ],
        environment,
        log_path,
        f"set Wine registry value {key}\\{name}",
    )
    if result.returncode != 0:
        raise RuntimeErrorWithContext(
            f"cannot set Wine registry value {key}\\{name}; "
            f"see {log_path}"
        )


def delete_wine_registry_value(
    context, wine64, environment, key, name, log_path
):
    result = run_job_process(
        context,
        [wine64, "reg", "delete", key, "/v", name, "/f"],
        environment,
        log_path,
        f"delete Wine registry value {key}\\{name}",
    )
    if result.returncode != 0:
        raise RuntimeErrorWithContext(
            f"cannot restore absent Wine registry value {key}\\{name}; "
            f"see {log_path}"
        )


def run_wine_controller_panel(
    context, wine64, environment, log_path
):
    previous_dpi = query_wine_registry_dword(
        context,
        wine64,
        environment,
        WINE_DESKTOP_REGISTRY_KEY,
        WINE_LOGPIXELS_VALUE,
        log_path,
    )
    target_dpi = max(previous_dpi or 96, CONTROLLER_READABILITY_DPI)
    override_applied = previous_dpi != target_dpi
    if override_applied:
        set_wine_registry_dword(
            context,
            wine64,
            environment,
            WINE_DESKTOP_REGISTRY_KEY,
            WINE_LOGPIXELS_VALUE,
            target_dpi,
            log_path,
        )
    try:
        result = run_job_process(
            context,
            [wine64, "control.exe", "joy.cpl"],
            environment,
            log_path,
            "open readable Wine game controllers",
        )
    finally:
        if override_applied:
            if previous_dpi is None:
                delete_wine_registry_value(
                    context,
                    wine64,
                    environment,
                    WINE_DESKTOP_REGISTRY_KEY,
                    WINE_LOGPIXELS_VALUE,
                    log_path,
                )
            else:
                set_wine_registry_dword(
                    context,
                    wine64,
                    environment,
                    WINE_DESKTOP_REGISTRY_KEY,
                    WINE_LOGPIXELS_VALUE,
                    previous_dpi,
                    log_path,
                )
    return result, target_dpi


def build_native_helper_environment(environment):
    return {
        name: value
        for name, value in environment.items()
        if name in NATIVE_HELPER_ENVIRONMENT_NAMES
    }


def validate_dependency_prefix_path(value):
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or "\\" in value
    ):
        return False
    path = Path(value)
    return (
        not path.is_absolute()
        and path.parts
        and path.parts[0] == "drive_c"
        and all(part not in ("", ".", "..") for part in path.parts)
    )


def validate_dependency_postcondition(postcondition):
    if not isinstance(postcondition, dict):
        return False
    condition_type = postcondition.get("type")
    if condition_type not in DEPENDENCY_POSTCONDITIONS:
        return False
    if condition_type == "file":
        return (
            set(postcondition) == {"type", "path"}
            and validate_dependency_prefix_path(postcondition.get("path"))
        )
    if condition_type == "registry-key":
        key = postcondition.get("key")
        return (
            set(postcondition) == {"type", "key"}
            and isinstance(key, str)
            and len(key) <= 512
            and re.fullmatch(
                r"HK(?:LM|CU)\\[A-Za-z0-9 _().{}+\\/-]+", key
            )
            is not None
        )
    if condition_type == "file-sha256":
        digest = postcondition.get("sha256")
        return (
            set(postcondition) == {"type", "path", "sha256"}
            and validate_dependency_prefix_path(
                postcondition.get("path")
            )
            and isinstance(digest, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        )
    paths = postcondition.get("paths")
    return (
        set(postcondition) == {"type", "paths"}
        and isinstance(paths, list)
        and 1 <= len(paths) <= 16
        and len(set(paths)) == len(paths)
        and all(validate_dependency_prefix_path(path) for path in paths)
    )


def validate_dependency_graph(dependencies):
    for dependency_id, dependency in dependencies.items():
        for prerequisite in dependency["prerequisites"]:
            if prerequisite not in dependencies:
                raise RuntimeErrorWithContext(
                    "dependency catalog prerequisite is missing: "
                    f"{dependency_id} -> {prerequisite}"
                )

    visiting = set()
    visited = set()

    def visit(dependency_id):
        if dependency_id in visiting:
            raise RuntimeErrorWithContext(
                f"dependency catalog contains a cycle: {dependency_id}"
            )
        if dependency_id in visited:
            return
        visiting.add(dependency_id)
        for prerequisite in dependencies[dependency_id]["prerequisites"]:
            visit(prerequisite)
        visiting.remove(dependency_id)
        visited.add(dependency_id)

    for dependency_id in dependencies:
        visit(dependency_id)


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
        installer = dependency.get("installer", "exe")
        prerequisites = dependency.get("prerequisites", [])
        postconditions = dependency.get("postconditions", [])
        parsed_url = urllib.parse.urlparse(url or "")
        expected_suffix = ".msi" if installer == "msi" else ".exe"
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
            and filename.lower().endswith(expected_suffix)
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
            and installer in DEPENDENCY_INSTALLERS
            and isinstance(prerequisites, list)
            and len(prerequisites) <= 16
            and len(set(prerequisites)) == len(prerequisites)
            and all(
                isinstance(prerequisite, str)
                and re.fullmatch(
                    r"[a-z0-9][a-z0-9-]{1,31}", prerequisite
                )
                and prerequisite != dependency_id
                for prerequisite in prerequisites
            )
            and isinstance(postconditions, list)
            and len(postconditions) <= 16
            and all(
                validate_dependency_postcondition(postcondition)
                for postcondition in postconditions
            )
        )
        if not valid:
            raise RuntimeErrorWithContext(
                "dependency catalog entry or postcondition is invalid: "
                f"{dependency_id}"
            )
        normalized[dependency_id] = {
            **dependency,
            "installer": installer,
            "prerequisites": prerequisites,
            "postconditions": postconditions,
        }
    validate_dependency_graph(normalized)
    return normalized


def curl_dependency_download(dependency, destination):
    result = subprocess.run(
        [
            "/usr/bin/curl",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--proto",
            "=https",
            "--proto-redir",
            "=https",
            "--max-redirs",
            "5",
            "--connect-timeout",
            "30",
            "--max-time",
            "600",
            "--max-filesize",
            str(dependency["size"]),
            "--user-agent",
            "RealSteamOnMac/1",
            "--output",
            str(destination),
            "--write-out",
            "%{url_effective}",
            dependency["url"],
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=620,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "curl failed"
        raise RuntimeErrorWithContext(
            f"dependency download failed: {dependency['id']}: {detail}"
        )
    final_url = result.stdout.strip()
    if not final_url:
        raise RuntimeErrorWithContext(
            f"dependency download returned no final URL: {dependency['id']}"
        )
    return final_url


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
        os.close(descriptor)
        descriptor = -1
        final_url = curl_dependency_download(dependency, temporary)
        parsed_final_url = urllib.parse.urlparse(final_url)
        if (
            parsed_final_url.scheme != "https"
            or parsed_final_url.hostname
            not in DEPENDENCY_DOWNLOAD_HOSTS
        ):
            raise RuntimeErrorWithContext(
                "dependency download redirected to an untrusted host"
            )
        total = temporary.stat().st_size
        digest = file_sha256(temporary)
        if (
            total != dependency["size"]
            or digest != dependency["sha256"]
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


def wine_z_path(path):
    resolved = Path(path).expanduser().resolve()
    return "Z:" + str(resolved).replace("/", "\\")


def build_dependency_install_commands(
    dependency, wine64, installer, extract_root=None
):
    dependency_id = dependency["id"]
    installer_type = dependency["installer"]
    arguments = dependency["arguments"]
    if installer_type == "exe":
        return [
            (
                f"install dependency {dependency_id}",
                [wine64, installer, *arguments],
            )
        ]
    if installer_type == "msi":
        return [
            (
                f"install dependency {dependency_id}",
                [wine64, "msiexec", "/i", installer, *arguments],
            )
        ]
    if extract_root is None:
        raise RuntimeErrorWithContext(
            "DirectX dependency requires an extraction directory"
        )
    extract_root = Path(extract_root)
    return [
        (
            f"extract dependency {dependency_id}",
            [
                wine64,
                installer,
                "/Q",
                f"/T:{wine_z_path(extract_root)}",
            ],
        ),
        (
            f"install dependency {dependency_id}",
            [wine64, extract_root / "DXSETUP.exe", *arguments],
        ),
    ]


def dependency_postcondition_met(context, postcondition):
    prefix = context["prefix"].resolve()

    def exists(relative):
        candidate = (prefix / relative).resolve()
        return candidate.is_relative_to(prefix) and candidate.is_file()

    if postcondition["type"] == "file":
        return exists(postcondition["path"])
    if postcondition["type"] == "file-sha256":
        candidate = (prefix / postcondition["path"]).resolve()
        return (
            candidate.is_relative_to(prefix)
            and candidate.is_file()
            and file_sha256(candidate) == postcondition["sha256"]
        )
    return any(exists(path) for path in postcondition["paths"])


def verify_dependency_postconditions(
    context,
    dependency,
    wine64=None,
    environment=None,
    log_path=None,
    run_process=run_job_process,
):
    for postcondition in dependency["postconditions"]:
        if postcondition["type"] == "registry-key":
            if wine64 is None or environment is None or log_path is None:
                raise RuntimeErrorWithContext(
                    "registry postcondition requires Wine context"
                )
            result = run_process(
                context,
                [
                    wine64,
                    "reg",
                    "query",
                    postcondition["key"],
                ],
                environment,
                log_path,
                "verify dependency "
                f"{dependency['id']} registry key",
            )
            met = result.returncode == 0
        else:
            met = dependency_postcondition_met(
                context, postcondition
            )
        if not met:
            raise RuntimeErrorWithContext(
                "dependency postcondition failed: "
                f"{dependency['id']} ({postcondition['type']})"
            )


def execute_run_command_action(context, runtime_root, fields, log_path):
    config = load_config(context)
    _, _, _, wine64, environment = prepare(
        context, runtime_root, config
    )
    plan = build_run_command_plan(
        context,
        wine64,
        fields["target"],
        fields["arguments"],
    )
    environment.update(
        parse_command_environment(fields["environment"])
    )
    log_event(
        context,
        {
            "event": "run-command",
            "kind": plan["kind"],
            "target": plan["target"],
            "command": [
                str(part) for part in plan["command"][1:]
            ],
            "arguments_text": fields["arguments"],
        },
    )
    process = start_job_process(
        context,
        plan["command"],
        environment,
        log_path,
        "run command",
    )
    return 0, {
        "kind": plan["kind"],
        "target": plan["target"],
        "renderer": config["renderer"],
        "pid": process.pid,
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
    installed = []
    completed = set()
    receipts = {}
    exit_codes = {}

    def install(dependency_id):
        if dependency_id in completed:
            return
        current = catalog[dependency_id]
        for prerequisite in current["prerequisites"]:
            install(prerequisite)

        installer = download_dependency(current)
        temporary = None
        try:
            extract_root = None
            if current["installer"] == "directx-redist":
                context["state"].mkdir(parents=True, exist_ok=True)
                temporary = tempfile.TemporaryDirectory(
                    prefix=".directx-redist-",
                    dir=str(context["state"]),
                )
                extract_root = Path(temporary.name)
                extract_root.chmod(0o700)
            commands = build_dependency_install_commands(
                current,
                wine64,
                installer,
                extract_root,
            )
            result = None
            for index, (description, command) in enumerate(commands):
                if (
                    current["installer"] == "directx-redist"
                    and index == 1
                    and not Path(command[1]).is_file()
                ):
                    raise RuntimeErrorWithContext(
                        "DirectX dependency did not extract DXSETUP.exe"
                    )
                result = run_job_process(
                    context,
                    command,
                    environment,
                    log_path,
                    description,
                )
                if result.returncode not in current["success_codes"]:
                    raise RuntimeErrorWithContext(
                        "dependency installer exited with "
                        f"{result.returncode}: {dependency_id}"
                    )
        finally:
            if temporary is not None:
                temporary.cleanup()

        verify_dependency_postconditions(
            context,
            current,
            wine64,
            environment,
            log_path,
        )
        exit_code = result.returncode
        receipt = (
            context["state"]
            / "dependencies"
            / f"{dependency_id}.json"
        )
        atomic_write_json(
            receipt,
            {
                "schema": 1,
                "dependency": dependency_id,
                "name": current["name"],
                "sha256": current["sha256"],
                "package_id": manifest["package_id"],
                "renderer": config["renderer"],
                "installed_at": utc_timestamp(),
                "exit_code": exit_code,
            },
        )
        log_event(
            context,
            {
                "event": "dependency-install",
                "dependency": dependency_id,
                "exit_code": exit_code,
            },
        )
        completed.add(dependency_id)
        installed.append(dependency_id)
        receipts[dependency_id] = str(receipt)
        exit_codes[dependency_id] = exit_code

    install(dependency["id"])
    return exit_codes[dependency["id"]], {
        "dependency": dependency["id"],
        "receipt": receipts[dependency["id"]],
        "installed": installed,
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
        env=build_native_helper_environment(os.environ),
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
    return 0, {"target": str(selected)}


def execute_container_action(context, runtime_root, fields, log_path):
    operation = fields["operation"]
    if operation == "open-c-drive":
        config = load_config(context)
        drive_c = context["prefix"] / "drive_c"
        if drive_c.is_symlink():
            raise RuntimeErrorWithContext(
                f"container C drive is unavailable: {drive_c}"
            )
        environment = os.environ
        if not drive_c.is_dir():
            _, _, _, _, environment = prepare(
                context, runtime_root, config
            )
        if not drive_c.is_dir():
            raise RuntimeErrorWithContext(
                f"container C drive is unavailable: {drive_c}"
            )
        result = run_job_process(
            context,
            ["/usr/bin/open", drive_c],
            build_native_helper_environment(environment),
            log_path,
            f"container operation {operation}",
        )
        return result.returncode, {
            "operation": operation,
            "path": str(drive_c),
            "renderer": config["renderer"],
        }

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

    if operation == "quit-all":
        _, _, wine_root, _, _ = load_selected_package(
            runtime_root, config
        )
        environment = build_environment(
            context, config, wine_root
        )
        result = run_job_process(
            context,
            [wine_root / "bin" / "wineserver", "-k"],
            environment,
            log_path,
            f"container operation {operation}",
        )
        return result.returncode, {
            "operation": operation,
            "renderer": config["renderer"],
        }

    _, _, wine_root, wine64, environment = prepare(
        context, runtime_root, config
    )
    if operation == "wine-configuration":
        command = [wine64, "winecfg"]
    elif operation == "controllers":
        result, controller_dpi = run_wine_controller_panel(
            context,
            wine64,
            environment,
            log_path,
        )
        return result.returncode, {
            "operation": operation,
            "renderer": config["renderer"],
            "controller_dpi": controller_dpi,
        }
    elif operation == "restart":
        command = [wine64, "wineboot", "--restart"]
    elif operation == "task-manager":
        command = [wine64, "taskmgr"]
    else:
        command = [wine64, "wineboot", "--restart"]
    if operation in {"wine-configuration", "task-manager"}:
        process = start_job_process(
            context,
            command,
            environment,
            log_path,
            f"container operation {operation}",
        )
        return 0, {
            "operation": operation,
            "renderer": config["renderer"],
            "pid": process.pid,
        }
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
        if action in {"choose-file", "inspect-state"}:
            context = None
        else:
            context = resolve_existing_action_context(appid)
        runtime_root = Path(args.runtime_root).expanduser().resolve()
        if action == "choose-file":
            exit_code, result = execute_choose_file_action(context)
        elif action == "inspect-state":
            exit_code, result = 0, inspect_action_state(appid)
        elif (
            action == "container"
            and fields["operation"] == "quit-all"
        ):
            exit_code, result = execute_container_action(
                context, runtime_root, fields, paths["log"]
            )
            if exit_code != 0:
                raise RuntimeErrorWithContext(
                    f"container operation exited with {exit_code}"
                )
        else:
            context["state"].mkdir(parents=True, exist_ok=True)
            context["state"].chmod(0o700)
            action_lock_path = context["state"] / "action.lock"
            with action_lock_path.open(
                "a+", encoding="utf-8"
            ) as action_lock:
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
                            "dependency installation exited with "
                            f"{exit_code}"
                        )
                else:
                    exit_code, result = execute_container_action(
                        context, runtime_root, fields, paths["log"]
                    )
                    if exit_code != 0:
                        raise RuntimeErrorWithContext(
                            f"container operation exited with {exit_code}"
                        )
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
        "install_warning": context.get("install_warning"),
        "launch_entry_id": context.get("launch_entry_id"),
        "launch_arguments": context.get("launch_arguments", ""),
        "requested_target": (
            str(context["requested_target"])
            if context.get("requested_target") is not None
            else None
        ),
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
            "launch_entry_id": context.get("launch_entry_id"),
            "launch_arguments": context.get("launch_arguments", ""),
            "requested_target": (
                str(context["requested_target"])
                if context.get("requested_target") is not None
                else None
            ),
            "install_warning": context.get("install_warning"),
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
