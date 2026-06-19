#!/usr/bin/env python3

import sys
from pathlib import Path
from types import MappingProxyType

RUNTIME_MODULE_DIRECTORY = Path(__file__).resolve().parent
if str(RUNTIME_MODULE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULE_DIRECTORY))

from compat_tool_catalog import CatalogError, parse_vdf_document


MAX_APP_MANIFEST_BYTES = 2 * 1024 * 1024
FULLY_INSTALLED = 4
KNOWN_STATE_FLAGS = {
    1: "uninstalled",
    2: "update-required",
    4: "fully-installed",
    8: "encrypted",
    16: "locked",
    32: "files-missing",
    64: "app-running",
    128: "files-corrupt",
    256: "update-running",
    512: "update-paused",
    1024: "update-started",
    2048: "uninstalling",
    4096: "backup-running",
    65536: "reconfiguring",
    131072: "validating",
    262144: "adding-files",
    524288: "preallocating",
    1048576: "downloading",
    2097152: "staging",
    4194304: "committing",
    8388608: "update-stopping",
}
NONBLOCKING_STATE_FLAGS = frozenset((FULLY_INSTALLED, 64))
BLOCKING_STATE_FLAGS = tuple(
    flag
    for flag in KNOWN_STATE_FLAGS
    if flag not in NONBLOCKING_STATE_FLAGS
)
KNOWN_STATE_MASK = sum(KNOWN_STATE_FLAGS)


class SteamAppStateError(ValueError):
    pass


def _parse_nonnegative_integer(value, field, path):
    try:
        parsed = int(value, 10)
    except (TypeError, ValueError) as error:
        raise SteamAppStateError(
            f"Steam app manifest has invalid {field}: {path}"
        ) from error
    if parsed < 0:
        raise SteamAppStateError(
            f"Steam app manifest has invalid {field}: {path}"
        )
    return parsed


def _load_app_state(path, expected_appid):
    path = Path(path)
    try:
        document = parse_vdf_document(
            path, MAX_APP_MANIFEST_BYTES, "Steam app manifest"
        )
    except CatalogError as error:
        raise SteamAppStateError(str(error)) from error
    app_state = document.get("AppState")
    if not isinstance(app_state, dict):
        raise SteamAppStateError(
            f"Steam app manifest is missing AppState: {path}"
        )
    appid = _parse_nonnegative_integer(
        app_state.get("appid"), "appid", path
    )
    if appid != expected_appid:
        raise SteamAppStateError(
            f"Steam app manifest AppID does not match {expected_appid}: {path}"
        )
    return app_state


def manifest_install_directory(path, expected_appid):
    app_state = _load_app_state(path, expected_appid)
    installdir = app_state.get("installdir")
    if (
        not isinstance(installdir, str)
        or not installdir
        or Path(installdir).name != installdir
        or installdir in (".", "..")
    ):
        raise SteamAppStateError(
            f"Steam app manifest has an unsafe installdir: {path}"
        )
    return installdir


def _summarize_depots(app_state, section_name, path):
    section = app_state.get(section_name)
    if section is None:
        return 0, 0
    if not isinstance(section, dict):
        raise SteamAppStateError(
            f"Steam app manifest has invalid {section_name}: {path}"
        )
    count = 0
    total_bytes = 0
    for depot_id, depot in section.items():
        if not isinstance(depot_id, str) or not depot_id.isdecimal():
            raise SteamAppStateError(
                f"Steam app manifest has invalid depot ID: {path}"
            )
        if not isinstance(depot, dict):
            raise SteamAppStateError(
                f"Steam app manifest has invalid depot {depot_id}: {path}"
            )
        manifest = depot.get("manifest")
        if (
            not isinstance(manifest, str)
            or not manifest.isdecimal()
            or int(manifest, 10) <= 0
        ):
            raise SteamAppStateError(
                f"Steam app manifest has invalid depot manifest: {path}"
            )
        size = _parse_nonnegative_integer(
            depot.get("size"), f"depot {depot_id} size", path
        )
        count += 1
        total_bytes += size
    return count, total_bytes


def _directory_has_content(path):
    if not path.is_dir():
        return False
    try:
        next(path.iterdir())
    except StopIteration:
        return False
    except OSError as error:
        raise SteamAppStateError(
            f"could not inspect Steam install directory: {path}"
        ) from error
    return True


def _diagnostic(
    state_flags,
    blocking_states,
    size_on_disk,
    installed_depot_count,
    installed_depot_bytes,
    staged_depot_count,
    install_path_nonempty,
    bytes_to_download,
    bytes_downloaded,
    bytes_to_stage,
    bytes_staged,
):
    if (
        staged_depot_count > 0
        or state_flags & (2 | 256 | 512 | 1024 | 1048576 | 2097152)
        or bytes_to_download > bytes_downloaded
        or bytes_to_stage > bytes_staged
    ):
        return "download-incomplete"
    if "files-missing" in blocking_states or "files-corrupt" in blocking_states:
        return "repair-required"
    if size_on_disk == 0 or not install_path_nonempty:
        return "content-missing"
    if installed_depot_count == 0 or installed_depot_bytes == 0:
        return "installed-depots-missing"
    if not state_flags & FULLY_INSTALLED:
        return "not-installed"
    if blocking_states:
        return "state-blocked"
    return "ready"


def inspect_app_manifest(path, expected_appid, install_path):
    path = Path(path)
    install_path = Path(install_path)
    app_state = _load_app_state(path, expected_appid)
    state_flags = _parse_nonnegative_integer(
        app_state.get("StateFlags"), "StateFlags", path
    )
    size_on_disk = _parse_nonnegative_integer(
        app_state.get("SizeOnDisk"), "SizeOnDisk", path
    )
    update_result = _parse_nonnegative_integer(
        app_state.get("UpdateResult", "0"), "UpdateResult", path
    )
    bytes_to_download = _parse_nonnegative_integer(
        app_state.get("BytesToDownload", "0"), "BytesToDownload", path
    )
    bytes_downloaded = _parse_nonnegative_integer(
        app_state.get("BytesDownloaded", "0"), "BytesDownloaded", path
    )
    bytes_to_stage = _parse_nonnegative_integer(
        app_state.get("BytesToStage", "0"), "BytesToStage", path
    )
    bytes_staged = _parse_nonnegative_integer(
        app_state.get("BytesStaged", "0"), "BytesStaged", path
    )
    installed_count, installed_bytes = _summarize_depots(
        app_state, "InstalledDepots", path
    )
    staged_count, staged_bytes = _summarize_depots(
        app_state, "StagedDepots", path
    )
    blocking_states = [
        KNOWN_STATE_FLAGS[flag]
        for flag in BLOCKING_STATE_FLAGS
        if state_flags & flag
    ]
    unknown_flags = state_flags & ~KNOWN_STATE_MASK
    if unknown_flags:
        blocking_states.append(f"unknown-state-flags:{unknown_flags}")
    install_path_nonempty = _directory_has_content(install_path)
    diagnostic = _diagnostic(
        state_flags,
        blocking_states,
        size_on_disk,
        installed_count,
        installed_bytes,
        staged_count,
        install_path_nonempty,
        bytes_to_download,
        bytes_downloaded,
        bytes_to_stage,
        bytes_staged,
    )
    return MappingProxyType(
        {
            "appid": expected_appid,
            "state_flags": state_flags,
            "size_on_disk": size_on_disk,
            "build_id": app_state.get("buildid", ""),
            "update_result": update_result,
            "bytes_to_download": bytes_to_download,
            "bytes_downloaded": bytes_downloaded,
            "bytes_to_stage": bytes_to_stage,
            "bytes_staged": bytes_staged,
            "installed_depot_count": installed_count,
            "installed_depot_bytes": installed_bytes,
            "staged_depot_count": staged_count,
            "staged_depot_bytes": staged_bytes,
            "install_path_exists": install_path.is_dir(),
            "install_path_nonempty": install_path_nonempty,
            "blocking_states": tuple(blocking_states),
            "diagnostic": diagnostic,
            "launchable": diagnostic == "ready",
        }
    )
