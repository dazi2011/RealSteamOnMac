#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


KNOWN_INDEX_SHA256 = {
    "55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282",
}
KNOWN_COMPAT_CHUNK_SHA256 = {
    "6d28c06fafb32f99c695f4bc4d1b8a8b8fb5bc1efc425f2a78abb8697af81349",
}
if os.environ.get("REALSTEAMONMAC_ALLOW_TEST_FIXTURES") == "1":
    KNOWN_COMPAT_CHUNK_SHA256.add(
        "d1202ff58c2cb9c0e1c7e91885b6568ae88ccd9225bf029d6b1260a8906107f6"
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
DEFAULT_COMPAT_TOOL = "realsteamonmac-experimental"
CONFIG_MODE = "all-windows-only"
COMPAT_PAGE_ANCHOR = (
    '(0,f.CI)()&&o.push({title:(0,A.we)'
    '("#AppProperties_CompatibilityPage")'
)
# Generalized compatibility-page gate: the original Linux/SteamOS condition,
# OR a runtime predicate (installed by ui.js) that returns true for any
# Windows-only title in the library. Optional chaining keeps the gate
# fail-safe (no tab) if ui.js has not finished loading. This replaces the old
# allowlist-membership gate so EVERY Windows-only game exposes the native
# compatibility page, including titles bought after Steam started.
COMPAT_PAGE_TARGET_GATE = (
    "((0,f.CI)()||globalThis.__REALSTEAMONMAC_IS_TARGET__?.(t))"
    "&&o.push({title:(0,A.we)"
    '("#AppProperties_CompatibilityPage")'
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
    if COMPAT_PAGE_TARGET_GATE in original:
        raise ValueError("compatibility chunk is already partially patched")
    return original.replace(
        COMPAT_PAGE_ANCHOR,
        COMPAT_PAGE_TARGET_GATE,
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


def config_bytes(force_include_appids):
    # The runtime now targets every Windows-only title structurally, so the
    # config no longer carries an exclusive allowlist. It records the mode, a
    # single default compatibility tool applied to all targets, and an optional
    # force-include set (e.g. the People Playground fixture, or titles the user
    # wants treated regardless of metadata).
    payload = json.dumps(
        {
            "mode": CONFIG_MODE,
            "defaultCompatTool": DEFAULT_COMPAT_TOOL,
            "forceIncludeAppids": force_include_appids,
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
    if COMPAT_PAGE_TARGET_GATE in current_text:
        original = validated_compat_original(paths["compat_backup"])
        expected = build_patched_compat_chunk(
            original.decode("utf-8")
        ).encode("utf-8")
        if current != expected:
            raise ValueError(
                "existing compatibility chunk patch is inconsistent"
            )
        return original, expected, False

    if sha256_bytes(current) not in KNOWN_COMPAT_CHUNK_SHA256:
        raise ValueError("unsupported compatibility chunk hash")
    if paths["compat_backup"].exists():
        original = validated_compat_original(paths["compat_backup"])
        if current != original:
            raise ValueError(
                "compatibility chunk backup does not match the clean chunk"
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
            COMPAT_PAGE_TARGET_GATE.encode("utf-8")
        )
        != 2
    ):
        raise ValueError("compatibility page gate count is invalid")
    if not paths["ui"].is_file() or paths["ui"].stat().st_size == 0:
        raise ValueError("Steam UI asset is missing")
    if not paths["config"].is_file():
        raise ValueError("Steam UI config asset is missing")

    config = paths["config"].read_text(encoding="utf-8")
    if not config.startswith(CONFIG_PREFIX) or not config.endswith(");\n"):
        raise ValueError("Steam UI config format is invalid")
    payload = config[len(CONFIG_PREFIX) : -3]
    parsed = json.loads(payload)
    if parsed.get("mode") != CONFIG_MODE:
        raise ValueError("Steam UI config mode is invalid")
    default_tool = parsed.get("defaultCompatTool")
    if not isinstance(default_tool, str) or not default_tool:
        raise ValueError("Steam UI default compatibility tool is invalid")
    # The force-include set is optional: an empty list is valid because the
    # runtime targets every Windows-only title structurally, not from a list.
    force_include = parsed.get("forceIncludeAppids")
    if (
        not isinstance(force_include, list)
        or any(
            not isinstance(appid, int) or appid <= 0 or appid > 0xFFFFFFFF
            for appid in force_include
        )
        or len(force_include) != len(set(force_include))
    ):
        raise ValueError("Steam UI force-include set is invalid")
    return force_include


def install_steamui(steamui_root, ui_source, allowlist):
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

    # The allowlist is now an optional force-include set. An empty (or absent)
    # list is valid: the runtime targets every Windows-only title structurally.
    appids = parse_allowlist(allowlist) if allowlist else []

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
    atomic_write(paths["config"], config_bytes(appids))
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
    install.add_argument("--allowlist", required=False, default=None)

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
