#!/usr/bin/env python3

import json
import re
import unicodedata
from pathlib import Path, PurePosixPath


MAX_DESCRIPTOR_BYTES = 256 * 1024
MAX_LAUNCH_ENTRIES = 64
MAX_ARGUMENT_LENGTH = 8192
MAX_PATH_LENGTH = 1024
ENTRY_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")
TOP_LEVEL_KEYS = frozenset(
    ("schema", "appid", "selected_entry_id", "entries")
)
ENTRY_KEYS = frozenset(
    (
        "id",
        "os",
        "executable",
        "working_directory",
        "arguments",
        "is_default",
    )
)
SUPPORTED_OS_NAMES = frozenset(("windows", "macos", "linux"))


class LaunchDescriptorError(ValueError):
    pass


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LaunchDescriptorError(
                f"launch descriptor contains duplicate key: {key}"
            )
        result[key] = value
    return result


def _read_descriptor(path):
    path = Path(path)
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise LaunchDescriptorError(
            f"could not read launch descriptor: {path}"
        ) from error
    if len(payload) > MAX_DESCRIPTOR_BYTES:
        raise LaunchDescriptorError(
            f"launch descriptor is too large: {path}"
        )
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise LaunchDescriptorError(
            f"launch descriptor is not valid UTF-8: {path}"
        ) from error
    try:
        value = json.loads(
            text, object_pairs_hook=_reject_duplicate_json_keys
        )
    except LaunchDescriptorError:
        raise
    except (json.JSONDecodeError, TypeError) as error:
        raise LaunchDescriptorError(
            f"launch descriptor is invalid JSON: {path}"
        ) from error
    if not isinstance(value, dict):
        raise LaunchDescriptorError(
            f"launch descriptor must be an object: {path}"
        )
    return value


def _validate_entry_id(value, label):
    if (
        not isinstance(value, str)
        or ENTRY_ID_PATTERN.fullmatch(value) is None
    ):
        raise LaunchDescriptorError(
            f"launch descriptor {label} is invalid"
        )
    return value


def _contains_control_characters(value):
    return any(
        unicodedata.category(character) == "Cc" for character in value
    )


def _normalize_relative_path(value, label, allow_dot=False):
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_PATH_LENGTH
        or "\x00" in value
        or _contains_control_characters(value)
    ):
        raise LaunchDescriptorError(
            f"launch descriptor {label} path is invalid"
        )
    normalized = value.replace("\\", "/")
    if (
        normalized.startswith("/")
        or normalized.startswith("//")
        or re.match(r"^[A-Za-z]:", normalized) is not None
    ):
        raise LaunchDescriptorError(
            f"launch descriptor {label} path is invalid"
        )
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or ".." in path.parts
        or (not allow_dot and path == PurePosixPath("."))
    ):
        raise LaunchDescriptorError(
            f"launch descriptor {label} path is invalid"
        )
    return Path(*path.parts)


def _validate_entry(value):
    if not isinstance(value, dict) or set(value) != ENTRY_KEYS:
        raise LaunchDescriptorError(
            "launch descriptor entry fields are invalid"
        )
    entry_id = _validate_entry_id(value["id"], "entry ID")
    os_name = value["os"]
    if not isinstance(os_name, str) or os_name not in SUPPORTED_OS_NAMES:
        raise LaunchDescriptorError(
            f"launch descriptor OS is invalid for entry {entry_id}"
        )
    executable = _normalize_relative_path(
        value["executable"], "executable"
    )
    working_directory = _normalize_relative_path(
        value["working_directory"],
        "working directory",
        allow_dot=True,
    )
    arguments = value["arguments"]
    if (
        not isinstance(arguments, str)
        or len(arguments) > MAX_ARGUMENT_LENGTH
        or "\x00" in arguments
        or any(
            character in "\r\n"
            for character in arguments
        )
    ):
        raise LaunchDescriptorError(
            f"launch descriptor arguments are invalid for entry {entry_id}"
        )
    if type(value["is_default"]) is not bool:
        raise LaunchDescriptorError(
            f"launch descriptor default flag is invalid for entry {entry_id}"
        )
    return {
        "id": entry_id,
        "os": os_name,
        "executable": executable,
        "working_directory": working_directory,
        "arguments": arguments,
        "is_default": value["is_default"],
    }


def load_launch_descriptor(path, expected_appid):
    value = _read_descriptor(path)
    if set(value) != TOP_LEVEL_KEYS:
        raise LaunchDescriptorError(
            "launch descriptor top-level fields are invalid"
        )
    if type(value["schema"]) is not int or value["schema"] != 1:
        raise LaunchDescriptorError(
            "launch descriptor schema is unsupported"
        )
    if (
        type(value["appid"]) is not int
        or type(expected_appid) is not int
        or value["appid"] != expected_appid
    ):
        raise LaunchDescriptorError(
            "launch descriptor AppID mismatch: "
            f"expected {expected_appid}, got {value['appid']}"
        )
    selected_entry_id = value["selected_entry_id"]
    if selected_entry_id is not None:
        selected_entry_id = _validate_entry_id(
            selected_entry_id, "selected entry ID"
        )
    entries_value = value["entries"]
    if (
        not isinstance(entries_value, list)
        or not entries_value
        or len(entries_value) > MAX_LAUNCH_ENTRIES
    ):
        raise LaunchDescriptorError(
            "launch descriptor entries are invalid"
        )
    entries = [_validate_entry(entry) for entry in entries_value]
    entry_ids = [entry["id"] for entry in entries]
    if len(entry_ids) != len(set(entry_ids)):
        raise LaunchDescriptorError(
            "launch descriptor contains duplicate entry IDs"
        )
    return {
        "appid": value["appid"],
        "selected_entry_id": selected_entry_id,
        "entries": entries,
    }


def _resolve_inside(install_path, relative_path, label):
    root = Path(install_path).expanduser().resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise LaunchDescriptorError(
            f"launch descriptor {label} escapes the installation directory"
        ) from error
    return candidate


def _resolve_entry(entry, install_path):
    if entry["os"] != "windows":
        return None, f"{entry['id']}: OS is {entry['os']}"
    executable = _resolve_inside(
        install_path, entry["executable"], "executable"
    )
    if not executable.is_file():
        return None, f"{entry['id']}: target is missing"
    try:
        with executable.open("rb") as stream:
            if stream.read(2) != b"MZ":
                return None, f"{entry['id']}: target is not PE"
    except OSError:
        return None, f"{entry['id']}: target is unreadable"
    working_directory = _resolve_inside(
        install_path,
        entry["working_directory"],
        "working directory",
    )
    if not working_directory.is_dir():
        return None, f"{entry['id']}: working directory is missing"
    return {
        "entry_id": entry["id"],
        "executable": executable,
        "working_directory": working_directory,
        "arguments": entry["arguments"],
    }, None


def resolve_launch_descriptor(path, expected_appid, install_path):
    value = load_launch_descriptor(path, expected_appid)
    selected_entry_id = value["selected_entry_id"]
    entries = value["entries"]
    candidates = []
    if selected_entry_id is not None:
        candidates.extend(
            entry for entry in entries
            if entry["id"] == selected_entry_id
        )
    candidates.extend(
        entry for entry in entries
        if entry["is_default"] and entry not in candidates
    )

    rejected = []
    for entry in candidates:
        resolved, reason = _resolve_entry(entry, install_path)
        if resolved is not None:
            return resolved
        rejected.append(reason)
    diagnostic = "; ".join(rejected) if rejected else "no selected/default entry"
    raise LaunchDescriptorError(
        "no valid Windows launch entry: " + diagnostic
    )
