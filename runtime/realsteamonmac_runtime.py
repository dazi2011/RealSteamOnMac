#!/usr/bin/python3

import argparse
import fcntl
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


RENDERERS = ("gptk", "dxmt", "dxvk", "wined3d")
STEAMWORKS_RENDERERS = ("dxmt", "dxvk", "wined3d")
# People Playground's .NET mod compiler mistakes its Wine PID for a macOS PID.
# It can therefore survive the game indefinitely and keep Steam's AppID active.
POST_EXIT_PREFIX_KILL_APPIDS = frozenset((1118200,))
DEFAULT_CONFIG = {
    "renderer": "gptk",
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


def atomic_write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
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
        "install_path": executable.parent,
        "steamapps": steamapps,
        "compat_data": compat_data,
        "prefix": compat_data / "pfx",
        "state": state,
        "config": state / "config.json",
        "logs": state / "logs",
    }


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
    for key in DEFAULT_CONFIG:
        if key == "renderer":
            continue
        if not isinstance(config[key], bool):
            raise RuntimeErrorWithContext(
                f"configuration value {key} must be boolean"
            )
    if config["metalfx"] and config["renderer"] != "gptk":
        raise RuntimeErrorWithContext(
            "MetalFX translation is available only with the GPTK renderer"
        )
    if config["dxr"] and config["renderer"] != "gptk":
        raise RuntimeErrorWithContext(
            "DXR is available only with the GPTK renderer"
        )
    return config


def load_config(context):
    path = context["config"]
    if not path.exists():
        return normalize_config(None)
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


def save_config(context, config):
    normalized = normalize_config(config)
    atomic_write_json(context["config"], normalized)
    return normalized


def load_package(runtime_root, renderer):
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
    wine_root = package / "wine" / renderer
    wine64 = wine_root / "bin" / "wine64"
    if not wine64.is_file() or not os.access(wine64, os.X_OK):
        raise RuntimeErrorWithContext(
            f"runtime is missing executable wine64: {wine64}"
        )
    return package, manifest, wine_root, wine64


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


def build_environment(
    context, config, wine_root, steamworks_bridge=None
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
        "ROSETTA_ADVERTISE_AVX",
        "MVK_CONFIG_RESUME_LOST_DEVICE",
        "WINEDLLOVERRIDES",
        "STEAM_COMPAT_CLIENT_INSTALL_PATH",
    ):
        environment.pop(key, None)

    if config["msync"]:
        environment["WINEMSYNC"] = "1"
        # D3DMetal checks WINEESYNC even when the server uses MSync.
        environment["WINEESYNC"] = "1"
    if config["metal_hud"]:
        environment["MTL_HUD_ENABLED"] = "1"
    if config["metalfx"]:
        environment["D3DM_ENABLE_METALFX"] = "1"
    if config["dxr"]:
        environment["D3DM_SUPPORT_DXR"] = "1"
    if config["avx"]:
        environment["ROSETTA_ADVERTISE_AVX"] = "1"
    if config["renderer"] == "dxvk":
        environment["MVK_CONFIG_RESUME_LOST_DEVICE"] = "1"
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


def install_metalfx_files(context, package, enabled):
    marker_path = context["state"] / "metalfx-files.json"
    system32 = context["prefix"] / "drive_c" / "windows" / "system32"
    names = ("nvngx.dll", "nvapi64.dll")
    if not enabled:
        return

    source_root = (
        package
        / "wine"
        / "gptk"
        / "lib"
        / "wine"
        / "x86_64-windows"
    )
    source_mapping = {
        "nvngx.dll": source_root / "nvngx-on-metalfx.dll",
        "nvapi64.dll": source_root / "nvapi64.dll",
    }
    system32.mkdir(parents=True, exist_ok=True)
    installed = {}
    for name in names:
        source = source_mapping[name]
        if not source.is_file():
            raise RuntimeErrorWithContext(
                f"GPTK MetalFX payload is missing: {source}"
            )
        destination = system32 / name
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if destination.exists():
            current = hashlib.sha256(destination.read_bytes()).hexdigest()
            if current != digest:
                raise RuntimeErrorWithContext(
                    "refusing to replace an unmanaged MetalFX file: "
                    f"{destination}"
                )
        else:
            destination.write_bytes(data)
        installed[name] = digest
    atomic_write_json(marker_path, installed)


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
    if bridge is None:
        return

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

    steam_directory = (
        context["prefix"]
        / "drive_c"
        / "Program Files (x86)"
        / "Steam"
    )
    source = bridge["windows_dll"]
    source_digest = file_sha256(source)
    installed = {}
    for name in ("lsteamclient.dll", "steamclient64.dll"):
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
    package, manifest, wine_root, wine64 = load_package(
        runtime_root, config["renderer"]
    )
    bridge = load_steamworks_bridge(
        package, manifest, wine_root, config["renderer"]
    )
    environment = build_environment(
        context, config, wine_root, bridge
    )
    initialize_prefix(context, wine64, environment)
    install_steamworks_files(context, manifest, bridge)
    configure_steam_registry(
        context, wine64, environment, bridge
    )
    apply_retina_mode(
        context, wine64, environment, config["retina"]
    )
    install_metalfx_files(context, package, config["metalfx"])
    return package, manifest, wine_root, wine64, environment


def plan(context, runtime_root, config, arguments):
    package, manifest, wine_root, wine64 = load_package(
        runtime_root, config["renderer"]
    )
    bridge = load_steamworks_bridge(
        package, manifest, wine_root, config["renderer"]
    )
    environment = build_environment(
        context, config, wine_root, bridge
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
        }
    }
    return {
        "appid": context["appid"],
        "executable": str(context["executable"]),
        "arguments": list(arguments),
        "steamapps": str(context["steamapps"]),
        "compat_data": str(context["compat_data"]),
        "prefix": str(context["prefix"]),
        "config_path": str(context["config"]),
        "runtime_root": str(runtime_root),
        "package": str(package),
        "package_id": manifest["package_id"],
        "renderer": config["renderer"],
        "steamworks_bridge": (
            bridge["metadata"].get("name", "lsteamclient")
            if bridge is not None
            else None
        ),
        "wine_root": str(wine_root),
        "wine64": str(wine64),
        "environment": interesting,
    }


def run_game_process(context, wine_root, command, environment):
    result = subprocess.run(
        [str(part) for part in command],
        cwd=str(context["install_path"]),
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
    context = resolve_context(
        Path(args.executable), args.appid, args.compat_data
    )
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    config = load_config(context)
    launch_plan = plan(context, runtime_root, config, args.arguments)
    if args.dry_run:
        print(json.dumps(launch_plan, indent=2, sort_keys=True))
        return 0

    _, _, wine_root, wine64, environment = prepare(
        context, runtime_root, config
    )
    command = [str(wine64), str(context["executable"])] + args.arguments
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
