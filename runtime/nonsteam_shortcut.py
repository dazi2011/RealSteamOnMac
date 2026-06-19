"""Resolve filesystem context for a non-Steam Windows shortcut."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Any


UINT32_MAX = (1 << 32) - 1
_DECIMAL_ID = re.compile(r"[0-9]+\Z")


def _parse_shortcut_id(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("shortcut id must be a positive uint32")

    if isinstance(value, str):
        if _DECIMAL_ID.fullmatch(value) is None:
            raise ValueError("shortcut id must be a decimal integer")
        try:
            parsed = int(value, 10)
        except ValueError as exc:
            raise ValueError(
                "shortcut id must be a decimal integer"
            ) from exc
    elif isinstance(value, int):
        parsed = value
    else:
        raise ValueError("shortcut id must be a positive uint32")

    if not 1 <= parsed <= UINT32_MAX:
        raise ValueError("shortcut id must be a positive uint32")
    return parsed


def _path(value: Any, label: str) -> Path:
    try:
        return Path(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a valid path") from exc


def _reject_symlink_components(path: Path, label: str) -> None:
    normalized = Path(os.path.normpath(os.fspath(path)))
    candidates = (path,) if normalized == path else (path, normalized)

    for candidate in candidates:
        current = Path(candidate.anchor)
        components = candidate.parts[1:]

        for component in (None, *components):
            if component is not None:
                current /= component
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as exc:
                raise ValueError(
                    f"{label} path could not be inspected"
                ) from exc
            if stat.S_ISLNK(mode):
                raise ValueError(f"{label} path contains a symlink")


def _reject_named_symlink(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label} could not be inspected") from exc
    if stat.S_ISLNK(mode):
        raise ValueError(f"{label} must not be a symlink")


def resolve_shortcut_context(
    shortcut_id: Any,
    target: Any,
    steam_root: Any,
    *,
    config_root: Any,
    explicit_compat_data: Any | None = None,
) -> dict[str, Any]:
    """Validate inputs and return the paths used by a non-Steam shortcut."""

    parsed_id = _parse_shortcut_id(shortcut_id)

    target_path = _path(target, "target")
    if not target_path.is_absolute():
        raise ValueError("target must be absolute")
    _reject_symlink_components(target_path, "target")

    try:
        executable = target_path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ValueError("target must exist") from exc
    except OSError as exc:
        raise ValueError("target could not be resolved") from exc

    try:
        mode = executable.stat().st_mode
    except OSError as exc:
        raise ValueError("target must exist") from exc
    if not stat.S_ISREG(mode):
        raise ValueError("target must be a regular file")
    if executable.suffix.lower() != ".exe":
        raise ValueError("target must have a .exe extension")

    try:
        with executable.open("rb") as stream:
            magic = stream.read(2)
    except OSError as exc:
        raise ValueError("target file could not be read") from exc
    if magic != b"MZ":
        raise ValueError("target must begin with MZ")

    steam_root_path = _path(steam_root, "steam_root")
    if not steam_root_path.is_absolute():
        raise ValueError("steam_root must be absolute")
    _reject_symlink_components(steam_root_path, "steam_root")
    try:
        steam_root_path = steam_root_path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ValueError("steam_root could not be canonicalized") from exc

    steamapps = steam_root_path / "steamapps"
    compatdata_root = steamapps / "compatdata"
    _reject_named_symlink(steamapps, "steamapps")
    _reject_named_symlink(compatdata_root, "compatdata")

    compat_data = compatdata_root / f"nonsteam-{parsed_id}"
    prefix = compat_data / "pfx"
    state = compat_data / "realsteamonmac"
    config = state / "config.json"
    logs = state / "logs"
    _reject_named_symlink(compat_data, "compatdata")
    _reject_named_symlink(prefix, "prefix")
    _reject_named_symlink(state, "state")
    _reject_named_symlink(config, "config")
    _reject_named_symlink(logs, "logs")

    if explicit_compat_data is not None:
        explicit_path = _path(explicit_compat_data, "explicit compat data")
        if not explicit_path.is_absolute():
            raise ValueError("explicit compat data must be absolute")
        _reject_symlink_components(explicit_path, "explicit compat data")
        try:
            canonical_explicit = explicit_path.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise ValueError(
                "explicit compat data could not be canonicalized"
            ) from exc
        if explicit_path != canonical_explicit:
            raise ValueError("explicit compat data must be canonical")
        if canonical_explicit != compat_data:
            raise ValueError(
                "explicit compat data must exactly match shortcut compatdata"
            )

    config_root_path = _path(config_root, "config_root")
    if not config_root_path.is_absolute():
        raise ValueError("config_root must be absolute")
    _reject_symlink_components(config_root_path, "config_root")
    try:
        config_root_path = config_root_path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ValueError("config_root could not be canonicalized") from exc

    global_config = config_root_path / f"shortcut-{parsed_id}.json"
    _reject_named_symlink(global_config, "global config")

    return {
        "identity_kind": "nonsteam-pe",
        "shortcut_id": parsed_id,
        "appid": parsed_id,
        "executable": executable,
        "working_directory": executable.parent,
        "install_path": executable.parent,
        "steam_root": steam_root_path,
        "steamapps": steamapps,
        "compat_data": compat_data,
        "prefix": prefix,
        "state": state,
        "config": config,
        "logs": logs,
        "global_config": global_config,
    }
