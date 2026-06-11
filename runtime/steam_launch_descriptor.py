#!/usr/bin/env python3

import hashlib
import json
import re
import struct
import unicodedata
from pathlib import Path, PurePosixPath


MAX_DESCRIPTOR_BYTES = 256 * 1024
MAX_LAUNCH_ENTRIES = 64
MAX_ARGUMENT_LENGTH = 8192
MAX_PATH_LENGTH = 1024
MAX_APPINFO_BYTES = 128 * 1024 * 1024
MAX_APPINFO_ENTRY_BYTES = 16 * 1024 * 1024
MAX_STRING_TABLE_ENTRIES = 200_000
MAX_STRING_BYTES = 64 * 1024
MAX_KV_NODES = 200_000
MAX_KV_DEPTH = 64
MAX_DIRECTORY_ENTRIES = 10_000
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
APPINFO_MAGIC_BASE = 0x07564400
APPINFO_SUPPORTED_VERSIONS = frozenset((40, 41))


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
    if isinstance(value, PurePosixPath):
        value = value.as_posix()
    elif isinstance(value, Path):
        value = value.as_posix()
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
    return _validate_descriptor_value(value, expected_appid)


def _validate_descriptor_value(value, expected_appid):
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
        "schema": 1,
        "appid": value["appid"],
        "selected_entry_id": selected_entry_id,
        "entries": entries,
    }


class _BinaryReader:
    def __init__(self, payload, start=0, end=None):
        self.payload = payload
        self.position = start
        self.end = len(payload) if end is None else end

    def read(self, length, label):
        if length < 0 or self.position + length > self.end:
            raise LaunchDescriptorError(
                f"appinfo {label} is truncated"
            )
        start = self.position
        self.position += length
        return self.payload[start:self.position]

    def unpack(self, format_string, label):
        size = struct.calcsize(format_string)
        return struct.unpack(
            format_string, self.read(size, label)
        )[0]

    def read_cstring(self, label):
        terminator = self.payload.find(
            b"\x00",
            self.position,
            min(self.end, self.position + MAX_STRING_BYTES + 1),
        )
        if terminator < 0:
            raise LaunchDescriptorError(
                f"appinfo {label} is unterminated or too long"
            )
        raw = self.payload[self.position:terminator]
        self.position = terminator + 1
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise LaunchDescriptorError(
                f"appinfo {label} is not valid UTF-8"
            ) from error


def _read_appinfo_payload(path):
    path = Path(path)
    try:
        file_stat = path.lstat()
    except OSError as error:
        raise LaunchDescriptorError(
            f"could not inspect Steam appinfo: {path}"
        ) from error
    if path.is_symlink() or not path.is_file():
        raise LaunchDescriptorError(
            f"Steam appinfo must be a regular file: {path}"
        )
    if file_stat.st_size <= 0 or file_stat.st_size > MAX_APPINFO_BYTES:
        raise LaunchDescriptorError(
            f"Steam appinfo size is invalid: {path}"
        )
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise LaunchDescriptorError(
            f"could not read Steam appinfo: {path}"
        ) from error
    if len(payload) != file_stat.st_size:
        raise LaunchDescriptorError(
            f"Steam appinfo changed while it was being read: {path}"
        )
    return payload


def _read_appinfo_string_table(payload, offset):
    if offset < 16 or offset >= len(payload):
        raise LaunchDescriptorError(
            "Steam appinfo string-table offset is invalid"
        )
    reader = _BinaryReader(payload, offset)
    count = reader.unpack("<I", "string-table count")
    if count <= 0 or count > MAX_STRING_TABLE_ENTRIES:
        raise LaunchDescriptorError(
            "Steam appinfo string-table count is invalid"
        )
    values = []
    for _ in range(count):
        values.append(reader.read_cstring("string-table value"))
    return values


def _parse_binary_keyvalues(payload, start, end, string_table):
    reader = _BinaryReader(payload, start, end)
    node_count = [0]

    def read_key():
        if string_table is None:
            return reader.read_cstring("KeyValues key")
        index = reader.unpack("<i", "KeyValues string-table index")
        if index < 0 or index >= len(string_table):
            raise LaunchDescriptorError(
                "appinfo KeyValues string-table index is invalid"
            )
        return string_table[index]

    def read_object(depth):
        if depth > MAX_KV_DEPTH:
            raise LaunchDescriptorError(
                "appinfo KeyValues nesting is too deep"
            )
        value = {}
        while True:
            node_type = reader.unpack("<B", "KeyValues node type")
            if node_type == 8:
                return value
            node_count[0] += 1
            if node_count[0] > MAX_KV_NODES:
                raise LaunchDescriptorError(
                    "appinfo KeyValues contains too many nodes"
                )
            key = read_key()
            if key in value:
                raise LaunchDescriptorError(
                    f"appinfo KeyValues contains duplicate key: {key}"
                )
            if node_type == 0:
                child = read_object(depth + 1)
            elif node_type == 1:
                child = reader.read_cstring("KeyValues string")
            elif node_type in (2, 4, 6):
                child = reader.unpack("<i", "KeyValues int32")
            elif node_type == 3:
                child = reader.unpack("<f", "KeyValues float32")
            elif node_type == 7:
                child = reader.unpack("<Q", "KeyValues uint64")
            elif node_type == 10:
                child = reader.unpack("<q", "KeyValues int64")
            else:
                raise LaunchDescriptorError(
                    f"appinfo KeyValues node type is unsupported: {node_type}"
                )
            value[key] = child

    value = read_object(0)
    if reader.position != end:
        raise LaunchDescriptorError(
            "appinfo KeyValues record length is inconsistent"
        )
    return value


def _load_appinfo_record(path, expected_appid):
    payload = _read_appinfo_payload(path)
    reader = _BinaryReader(payload)
    magic = reader.unpack("<I", "magic")
    version = magic & 0xFF
    if (
        magic & 0xFFFFFF00 != APPINFO_MAGIC_BASE
        or version not in APPINFO_SUPPORTED_VERSIONS
    ):
        raise LaunchDescriptorError(
            f"Steam appinfo version is unsupported: {version}"
        )
    universe = reader.unpack("<I", "universe")
    if universe != 1:
        raise LaunchDescriptorError(
            f"Steam appinfo universe is unsupported: {universe}"
        )
    string_table = None
    entries_end = len(payload)
    if version >= 41:
        string_table_offset = reader.unpack(
            "<q", "string-table offset"
        )
        string_table = _read_appinfo_string_table(
            payload, string_table_offset
        )
        entries_end = string_table_offset

    found = None
    while reader.position + 4 <= entries_end:
        appid = reader.unpack("<I", "AppID")
        if appid == 0:
            break
        size = reader.unpack("<I", "record size")
        if size < 60 or size > MAX_APPINFO_ENTRY_BYTES:
            raise LaunchDescriptorError(
                f"Steam appinfo record size is invalid for AppID {appid}"
            )
        record_end = reader.position + size
        if record_end > entries_end:
            raise LaunchDescriptorError(
                f"Steam appinfo record is truncated for AppID {appid}"
            )
        reader.read(4, "info state")
        reader.read(4, "last-updated timestamp")
        reader.read(8, "PICS token")
        reader.read(20, "PICS hash")
        reader.read(4, "change number")
        binary_hash = reader.read(20, "binary VDF hash")
        binary_start = reader.position
        binary_payload = payload[binary_start:record_end]
        if hashlib.sha1(binary_payload).digest() != binary_hash:
            raise LaunchDescriptorError(
                f"Steam appinfo binary VDF hash mismatch for AppID {appid}"
            )
        if appid == expected_appid:
            if found is not None:
                raise LaunchDescriptorError(
                    f"Steam appinfo contains duplicate AppID {appid}"
                )
            found = _parse_binary_keyvalues(
                payload,
                binary_start,
                record_end,
                string_table,
            )
        reader.position = record_end
    if found is None:
        raise LaunchDescriptorError(
            f"Steam appinfo does not contain AppID {expected_appid}"
        )
    return found


def _launch_os_name(value):
    if not isinstance(value, str):
        return None
    names = {
        name.strip().lower()
        for name in re.split(r"[,;]", value)
        if name.strip()
    }
    if "windows" in names:
        return "windows"
    if names.intersection(("macos", "osx")):
        return "macos"
    if "linux" in names:
        return "linux"
    return None


def _relative_requested_target(requested_target, install_path):
    if requested_target is None:
        return None
    root = Path(install_path).expanduser().resolve()
    target = Path(requested_target).expanduser()
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    try:
        relative = target.relative_to(root)
    except ValueError:
        return None
    return relative.as_posix().casefold()


def build_launch_descriptor_from_appinfo(
    path,
    expected_appid,
    install_path,
    requested_target=None,
):
    root = _load_appinfo_record(path, expected_appid)
    appinfo = root.get("appinfo")
    config = appinfo.get("config") if isinstance(appinfo, dict) else None
    launch = config.get("launch") if isinstance(config, dict) else None
    if not isinstance(launch, dict) or not launch:
        raise LaunchDescriptorError(
            f"Steam appinfo has no launch records for AppID {expected_appid}"
        )
    if len(launch) > MAX_LAUNCH_ENTRIES:
        raise LaunchDescriptorError(
            f"Steam appinfo has too many launch records for AppID {expected_appid}"
        )

    entries = []
    for entry_id, raw_entry in launch.items():
        if not isinstance(entry_id, str) or not isinstance(raw_entry, dict):
            raise LaunchDescriptorError(
                "Steam appinfo launch record is invalid"
            )
        raw_config = raw_entry.get("config", {})
        if not isinstance(raw_config, dict):
            raise LaunchDescriptorError(
                f"Steam appinfo launch config is invalid for entry {entry_id}"
            )
        os_name = _launch_os_name(raw_config.get("oslist"))
        executable = raw_entry.get("executable")
        arguments = raw_entry.get("arguments", "")
        working_directory = raw_entry.get("workingdir", ".")
        launch_type = raw_entry.get("type", "")
        if (
            os_name is None
            or not isinstance(executable, str)
            or not isinstance(arguments, str)
            or not isinstance(working_directory, str)
            or not isinstance(launch_type, str)
        ):
            raise LaunchDescriptorError(
                f"Steam appinfo launch fields are invalid for entry {entry_id}"
            )
        entries.append(
            {
                "id": entry_id,
                "os": os_name,
                "executable": executable,
                "working_directory": working_directory or ".",
                "arguments": arguments,
                "is_default": launch_type.lower() in ("default", "none"),
            }
        )

    requested_relative = _relative_requested_target(
        requested_target, install_path
    )
    selected_entry_id = None
    if requested_relative is not None:
        for entry in entries:
            executable = entry["executable"].replace("\\", "/").casefold()
            if executable == requested_relative:
                selected_entry_id = entry["id"]
                break
    if selected_entry_id is None and requested_target is None:
        selected_entry_id = next(
            (
                entry["id"]
                for entry in entries
                if entry["os"] == "windows" and entry["is_default"]
            ),
            None,
        )
    return _validate_descriptor_value(
        {
            "schema": 1,
            "appid": expected_appid,
            "selected_entry_id": selected_entry_id,
            "entries": entries,
        },
        expected_appid,
    )


def _resolve_inside(install_path, relative_path, label):
    root = Path(install_path).expanduser().resolve()
    candidate = root
    for component in Path(relative_path).parts:
        requested = candidate / component
        if not candidate.is_dir():
            candidate = requested
            continue
        try:
            entries = []
            for entry in candidate.iterdir():
                entries.append(entry)
                if len(entries) > MAX_DIRECTORY_ENTRIES:
                    raise LaunchDescriptorError(
                        f"launch descriptor {label} directory is too large"
                    )
        except OSError as error:
            raise LaunchDescriptorError(
                f"launch descriptor {label} directory is unreadable"
            ) from error
        exact = [entry for entry in entries if entry.name == component]
        folded = [
            entry
            for entry in entries
            if entry.name.casefold() == component.casefold()
        ]
        if exact:
            candidate = exact[0]
        elif len(folded) == 1:
            candidate = folded[0]
        elif len(folded) > 1:
            raise LaunchDescriptorError(
                f"launch descriptor {label} path is case-ambiguous"
            )
        else:
            candidate = requested
    candidate = candidate.resolve()
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


def resolve_launch_descriptor_value(value, expected_appid, install_path):
    value = _validate_descriptor_value(value, expected_appid)
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


def resolve_launch_descriptor(path, expected_appid, install_path):
    value = load_launch_descriptor(path, expected_appid)
    return resolve_launch_descriptor_value(
        value, expected_appid, install_path
    )
