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
INDEX_NAME = "index.html"
BACKUP_NAME = "index.html.realsteamonmac.original"
ASSET_DIRECTORY = "realsteamonmac"
ANCHOR = '<script defer="defer" src="/library.js"></script>'
BEGIN_MARKER = "<!-- RealSteamOnMac UI begin -->"
END_MARKER = "<!-- RealSteamOnMac UI end -->"
CONFIG_TAG = '<script defer="defer" src="/realsteamonmac/config.js"></script>'
UI_TAG = '<script defer="defer" src="/realsteamonmac/ui.js"></script>'
CONFIG_PREFIX = "globalThis.__REALSTEAMONMAC_CONFIG__ = Object.freeze("


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


def config_bytes(appids):
    payload = json.dumps({"appids": appids}, separators=(",", ":"))
    return f"{CONFIG_PREFIX}{payload});\n".encode("utf-8")


def paths_for(steamui_root):
    root = Path(steamui_root)
    return {
        "root": root,
        "index": root / INDEX_NAME,
        "backup": root / BACKUP_NAME,
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
    if not paths["ui"].is_file() or paths["ui"].stat().st_size == 0:
        raise ValueError("Steam UI asset is missing")
    if not paths["config"].is_file():
        raise ValueError("Steam UI config asset is missing")

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
    return appids


def install_steamui(steamui_root, ui_source, allowlist):
    paths = paths_for(steamui_root)
    ui_source = Path(ui_source)
    if not paths["root"].is_dir():
        raise ValueError("Steam UI root is missing")
    if not paths["index"].is_file():
        raise ValueError("Steam UI index is missing")
    if not ui_source.is_file() or ui_source.stat().st_size == 0:
        raise ValueError("RealSteamOnMac UI source is missing")

    appids = parse_allowlist(allowlist)
    if not appids:
        raise ValueError("RealSteamOnMac allowlist is empty")

    current = paths["index"].read_bytes()
    current_text = current.decode("utf-8")
    if BEGIN_MARKER in current_text:
        original = validated_original(paths["backup"])
        expected = build_patched_index(original.decode("utf-8")).encode("utf-8")
        if current != expected:
            raise ValueError("existing Steam UI patch is inconsistent")
    else:
        if sha256_bytes(current) not in KNOWN_INDEX_SHA256:
            raise ValueError("unsupported Steam UI index hash")
        if paths["backup"].exists():
            original = validated_original(paths["backup"])
            if current != original:
                raise ValueError(
                    "Steam UI backup does not match the restored clean index"
                )
        else:
            atomic_write(paths["backup"], current)
        patched = build_patched_index(current_text).encode("utf-8")
        atomic_write(paths["index"], patched)

    atomic_write(paths["ui"], ui_source.read_bytes())
    atomic_write(paths["config"], config_bytes(appids))
    verify_steamui(paths["root"])
    return appids


def restore_steamui(steamui_root):
    paths = paths_for(steamui_root)
    original = validated_original(paths["backup"])
    if not paths["index"].is_file():
        raise ValueError("Steam UI index is missing")
    expected = build_patched_index(original.decode("utf-8")).encode("utf-8")
    if paths["index"].read_bytes() != expected:
        raise ValueError("Steam UI index is not the guarded project patch")

    os.replace(paths["backup"], paths["index"])
    if paths["assets"].exists():
        shutil.rmtree(paths["assets"])


def build_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install")
    install.add_argument("--steamui-root", required=True)
    install.add_argument("--ui-source", required=True)
    install.add_argument("--allowlist", required=True)

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
