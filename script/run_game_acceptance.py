#!/usr/bin/env python3

"""Read-only Windows game acceptance reporting."""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from compat_tool_catalog import CatalogError, parse_vdf_document
from steam_app_state import (
    inspect_app_manifest,
    manifest_install_directory,
)
from steam_launch_descriptor import (
    LaunchDescriptorError,
    build_launch_descriptor_from_appinfo,
    load_launch_descriptor,
    resolve_launch_descriptor_value,
)


MAX_CONFIG_BYTES = 1024 * 1024
MAX_EVIDENCE_FILES = 128
MAX_EVIDENCE_FILE_BYTES = 16 * 1024 * 1024
MAX_PROBE_ARGUMENTS = 64
MAX_PROBE_ARGUMENT_BYTES = 16 * 1024
MAX_PROBE_OUTPUT_BYTES = 1024 * 1024
RUNTIME_FINGERPRINT_FILES = (
    "realsteamonmac-runtime",
    "steam_launch_descriptor.py",
)


def _read_config(path):
    path = Path(path)
    if not path.exists():
        return {}
    stat = path.lstat()
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"game configuration must be a regular file: {path}")
    if stat.st_size > MAX_CONFIG_BYTES:
        raise ValueError(f"game configuration is too large: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"game configuration must be an object: {path}")
    return value


def _collect_evidence(path):
    path = Path(path)
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"evidence root must be a directory: {path}")
    entries = sorted(path.iterdir(), key=lambda item: item.name)
    if len(entries) > MAX_EVIDENCE_FILES:
        raise ValueError(f"evidence root contains too many entries: {path}")
    evidence = []
    for entry in entries:
        stat = entry.lstat()
        if entry.is_symlink() or not entry.is_file():
            continue
        if stat.st_size > MAX_EVIDENCE_FILE_BYTES:
            raise ValueError(f"evidence file is too large: {entry}")
        digest = hashlib.sha256(entry.read_bytes()).hexdigest()
        evidence.append(
            {
                "name": entry.name,
                "size": stat.st_size,
                "sha256": digest,
            }
        )
    return evidence


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_runtime_fingerprints(installed_runtime_bin):
    installed_runtime_bin = Path(installed_runtime_bin).expanduser()
    source_bin = ROOT / "runtime"
    files = {}
    for name in RUNTIME_FINGERPRINT_FILES:
        source_path = (
            source_bin / "realsteamonmac_runtime.py"
            if name == "realsteamonmac-runtime"
            else source_bin / name
        )
        installed_path = installed_runtime_bin / name
        item = {
            "source": str(source_path),
            "installed": str(installed_path),
            "source_sha256": (
                _sha256_file(source_path) if source_path.is_file() else None
            ),
            "installed_sha256": (
                _sha256_file(installed_path)
                if installed_path.is_file()
                and not installed_path.is_symlink()
                else None
            ),
        }
        item["matches_source"] = (
            item["source_sha256"] is not None
            and item["source_sha256"] == item["installed_sha256"]
        )
        files[name] = item
    return {
        "installed_runtime_bin": str(installed_runtime_bin),
        "files": files,
        "matches_source": all(
            item["matches_source"] for item in files.values()
        ),
    }


def _relative(path, root):
    path = Path(path).resolve()
    root = Path(root).resolve()
    relative = path.relative_to(root)
    return "." if relative == Path(".") else relative.as_posix()


def _validate_probe_command(command):
    if (
        not isinstance(command, (list, tuple))
        or not command
        or len(command) > MAX_PROBE_ARGUMENTS
    ):
        raise ValueError("probe command is invalid")
    normalized = []
    total_bytes = 0
    for argument in command:
        if not isinstance(argument, str) or "\x00" in argument:
            raise ValueError("probe command argument is invalid")
        total_bytes += len(argument.encode("utf-8"))
        normalized.append(argument)
    if total_bytes > MAX_PROBE_ARGUMENT_BYTES:
        raise ValueError("probe command is too large")
    executable = Path(normalized[0])
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError("probe executable must be an absolute file")
    return normalized


def _read_probe_output(stream):
    stream.seek(0)
    payload = stream.read(MAX_PROBE_OUTPUT_BYTES + 1)
    truncated = len(payload) > MAX_PROBE_OUTPUT_BYTES
    payload = payload[:MAX_PROBE_OUTPUT_BYTES]
    return payload.decode("utf-8", errors="replace"), truncated


def run_bounded_probe(command, *, timeout_seconds):
    command = _validate_probe_command(command)
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
        or timeout_seconds > 3600
    ):
        raise ValueError("probe timeout is invalid")
    started = time.monotonic()
    timed_out = False
    with (
        tempfile.TemporaryFile() as stdout_stream,
        tempfile.TemporaryFile() as stderr_stream,
    ):
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=stdout_stream,
            stderr=stderr_stream,
            start_new_session=True,
        )
        try:
            exit_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                exit_code = process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                exit_code = process.wait()
        stdout, stdout_truncated = _read_probe_output(stdout_stream)
        stderr, stderr_truncated = _read_probe_output(stderr_stream)
    return {
        "command": command,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 6),
        "stdout": stdout,
        "stderr": stderr,
        "output_truncated": stdout_truncated or stderr_truncated,
    }


def discover_library_roots(steam_root):
    steam_root = Path(steam_root).expanduser().resolve()
    roots = [steam_root]
    library_file = steam_root / "steamapps/libraryfolders.vdf"
    if not library_file.is_file():
        return roots
    try:
        document = parse_vdf_document(
            library_file,
            4 * 1024 * 1024,
            "Steam library folders",
        )
    except CatalogError as error:
        raise ValueError(str(error)) from error
    libraries = document.get("libraryfolders")
    if not isinstance(libraries, dict):
        raise ValueError(
            f"Steam library folders are invalid: {library_file}"
        )
    for value in libraries.values():
        if not isinstance(value, dict):
            continue
        path = value.get("path")
        if not isinstance(path, str) or not path:
            continue
        candidate = Path(path).expanduser().resolve()
        if candidate not in roots:
            roots.append(candidate)
    return roots


def _find_manifest(appid, library_roots):
    matches = []
    for library_root in library_roots:
        manifest = (
            Path(library_root)
            / "steamapps"
            / f"appmanifest_{appid}.acf"
        )
        if manifest.is_file():
            matches.append(manifest)
    if not matches:
        raise ValueError(f"Steam app manifest was not found for AppID {appid}")
    if len(matches) > 1:
        paths = ", ".join(str(path) for path in matches)
        raise ValueError(
            f"multiple Steam app manifests exist for AppID {appid}: {paths}"
        )
    return matches[0]


def _manifest_name(path):
    try:
        document = parse_vdf_document(
            path,
            2 * 1024 * 1024,
            "Steam app manifest",
        )
    except CatalogError as error:
        raise ValueError(str(error)) from error
    app_state = document.get("AppState")
    name = app_state.get("name") if isinstance(app_state, dict) else None
    if not isinstance(name, str) or not name:
        raise ValueError(f"Steam app manifest has no valid name: {path}")
    return name


def build_acceptance_report(
    *,
    steam_root,
    appids,
    descriptor_loader,
    config_root,
    evidence_root,
    installed_runtime_bin=None,
):
    if not callable(descriptor_loader):
        raise ValueError("descriptor loader must be callable")
    normalized_appids = []
    for appid in appids:
        if (
            isinstance(appid, bool)
            or not isinstance(appid, int)
            or appid <= 0
            or appid in normalized_appids
        ):
            raise ValueError("acceptance AppID list is invalid")
        normalized_appids.append(appid)
    library_roots = discover_library_roots(steam_root)
    config_root = Path(config_root).expanduser().resolve()
    evidence_root = Path(evidence_root).expanduser().resolve()
    games = []
    for appid in normalized_appids:
        try:
            manifest = _find_manifest(appid, library_roots)
            steamapps = manifest.parent
            installdir = manifest_install_directory(manifest, appid)
            install_path = steamapps / "common" / installdir
            name = _manifest_name(manifest)
            descriptor_error = None
            try:
                launch_descriptor = descriptor_loader(
                    appid, install_path
                )
            except (OSError, ValueError) as error:
                launch_descriptor = None
                descriptor_error = str(error)
            record = inspect_game_record(
                appid=appid,
                manifest_path=manifest,
                install_path=install_path,
                launch_descriptor=launch_descriptor,
                config_path=config_root / f"{appid}.json",
                compat_data_path=steamapps / "compatdata" / str(appid),
                evidence_root=evidence_root / str(appid),
                descriptor_error=descriptor_error,
            )
            record["name"] = name
        except (OSError, ValueError) as error:
            record = {"appid": appid, "error": str(error)}
        games.append(record)
    ready = sum(
        1
        for game in games
        if game.get("state", {}).get("diagnostic") == "ready"
        and game.get("launch") is not None
    )
    errors = sum(1 for game in games if "error" in game)
    return {
        "schema": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "steam_root": str(Path(steam_root).expanduser().resolve()),
        "library_roots": [str(path) for path in library_roots],
        "summary": {
            "requested": len(normalized_appids),
            "ready": ready,
            "blocked": len(games) - ready - errors,
            "errors": errors,
        },
        "runtime": collect_runtime_fingerprints(
            installed_runtime_bin
            or (
                Path.home()
                / "Library/Application Support/RealSteamOnMac/runtimes/bin"
            )
        ),
        "games": games,
    }


def _parse_requested_targets(values):
    targets = {}
    for value in values:
        appid_text, separator, target = value.partition("=")
        if (
            not separator
            or not appid_text.isdecimal()
            or int(appid_text, 10) <= 0
            or not target
        ):
            raise ValueError(
                "requested target must use APPID=PATH syntax"
            )
        appid = int(appid_text, 10)
        if appid in targets:
            raise ValueError(f"duplicate requested target for AppID {appid}")
        targets[appid] = target
    return targets


def _write_report(path, report):
    payload = (
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    )
    if path is None:
        sys.stdout.write(payload)
        return
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError(f"report output must not be a symlink: {path}")
    if not path.parent.is_dir():
        raise ValueError(
            f"report output directory does not exist: {path.parent}"
        )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Generate a non-destructive RealSteamOnMac game acceptance report"
        )
    )
    parser.add_argument(
        "--steam-root",
        type=Path,
        default=Path.home() / "Library/Application Support/Steam",
    )
    parser.add_argument("--appinfo", type=Path)
    parser.add_argument("--descriptor-root", type=Path)
    parser.add_argument("--config-root", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--runtime-bin", type=Path)
    parser.add_argument("--appid", action="append", required=True)
    parser.add_argument(
        "--requested-target",
        action="append",
        default=[],
        metavar="APPID=PATH",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)

    try:
        appids = []
        for value in arguments.appid:
            if not value.isdecimal() or int(value, 10) <= 0:
                raise ValueError(f"invalid AppID: {value}")
            appids.append(int(value, 10))
        requested_targets = _parse_requested_targets(
            arguments.requested_target
        )
        support_root = (
            Path.home() / "Library/Application Support/RealSteamOnMac"
        )
        config_root = arguments.config_root or support_root / "apps"
        evidence_root = (
            arguments.evidence_root
            or support_root / "game-acceptance-evidence"
        )
        if arguments.descriptor_root is not None:
            descriptor_root = (
                arguments.descriptor_root.expanduser().resolve()
            )
            if not descriptor_root.is_dir():
                raise ValueError(
                    f"descriptor root is missing: {descriptor_root}"
                )

            def descriptor_loader(appid, _install_path):
                return load_launch_descriptor(
                    descriptor_root / f"{appid}.json", appid
                )

        else:
            appinfo = arguments.appinfo or (
                arguments.steam_root / "appcache/appinfo.vdf"
            )
            appinfo = appinfo.expanduser().resolve()

            def descriptor_loader(appid, install_path):
                return build_launch_descriptor_from_appinfo(
                    appinfo,
                    appid,
                    install_path,
                    requested_targets.get(appid),
                )

        report = build_acceptance_report(
            steam_root=arguments.steam_root,
            appids=appids,
            descriptor_loader=descriptor_loader,
            config_root=config_root,
            evidence_root=evidence_root,
            installed_runtime_bin=arguments.runtime_bin,
        )
        _write_report(arguments.output, report)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0

def inspect_game_record(
    *,
    appid,
    manifest_path,
    install_path,
    launch_descriptor,
    config_path,
    compat_data_path,
    evidence_root,
    descriptor_error=None,
):
    manifest_path = Path(manifest_path)
    install_path = Path(install_path)
    compat_data_path = Path(compat_data_path)
    state = dict(
        inspect_app_manifest(manifest_path, appid, install_path)
    )
    state["blocking_states"] = list(state["blocking_states"])

    launch = None
    launch_error = descriptor_error
    if launch_descriptor is not None:
        try:
            resolved = resolve_launch_descriptor_value(
                launch_descriptor, appid, install_path
            )
            launch = {
                "entry_id": resolved["entry_id"],
                "executable": _relative(
                    resolved["executable"], install_path
                ),
                "working_directory": _relative(
                    resolved["working_directory"], install_path
                ),
                "arguments": resolved["arguments"],
            }
        except LaunchDescriptorError as error:
            launch_error = str(error)

    prefix = compat_data_path / "pfx"
    container_exists = (
        prefix.is_dir()
        and not prefix.is_symlink()
        and not compat_data_path.is_symlink()
    )
    return {
        "appid": appid,
        "manifest": str(manifest_path),
        "install_path": str(install_path),
        "state": state,
        "launch": launch,
        "launch_error": launch_error,
        "config": _read_config(config_path),
        "container": {
            "compat_data_path": str(compat_data_path),
            "exists": container_exists,
        },
        "evidence": _collect_evidence(evidence_root),
    }


if __name__ == "__main__":
    raise SystemExit(main())
