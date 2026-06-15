#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


SEMVER = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")
STEAM_BUILD = re.compile(r"[0-9]{8,12}")
SHA256 = re.compile(r"[0-9a-f]{64}")
ALLOWED_DOWNLOAD_HOSTS = frozenset(
    (
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
    )
)
MANIFEST_NAME = "release-manifest.json"
SIGNATURE_NAME = "release-manifest.json.sig"
MAX_MANIFEST_BYTES = 128 * 1024
MAX_SIGNATURE_BYTES = 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024 * 1024


class UpdateError(RuntimeError):
    pass


def parse_version(value):
    match = SEMVER.fullmatch(value)
    if match is None:
        raise UpdateError(f"invalid semantic version: {value}")
    return tuple(int(part) for part in match.groups())


def validate_download_url(value, repository, filename):
    if not isinstance(value, str):
        raise UpdateError("release artifact URL must be a string")
    parsed = urllib.parse.urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise UpdateError("release artifact URL is not trusted")
    if filename not in urllib.parse.unquote(parsed.path):
        raise UpdateError("release artifact URL does not match its filename")
    owner, name = repository.split("/", 1)
    if parsed.hostname == "github.com":
        expected = f"/{owner}/{name}/releases/download/"
        if not parsed.path.startswith(expected):
            raise UpdateError("release artifact URL targets another repository")


def validate_artifact(value, repository, expected_name):
    if not isinstance(value, dict) or set(value) != {
        "name",
        "sha256",
        "size",
        "url",
    }:
        raise UpdateError(f"{expected_name} metadata is invalid")
    if value["name"] != expected_name:
        raise UpdateError(f"unexpected release artifact: {value['name']}")
    if (
        not isinstance(value["sha256"], str)
        or SHA256.fullmatch(value["sha256"]) is None
    ):
        raise UpdateError(f"{expected_name} checksum is invalid")
    if (
        type(value["size"]) is not int
        or value["size"] <= 0
        or value["size"] > MAX_PACKAGE_BYTES
    ):
        raise UpdateError(f"{expected_name} size is invalid")
    validate_download_url(value["url"], repository, expected_name)


def validate_manifest(value, repository):
    expected_keys = {
        "schema",
        "version",
        "tag",
        "repository",
        "published_utc",
        "supported_steam_builds",
        "minimum_macos",
        "architecture",
        "installer",
        "updater",
        "uninstaller",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise UpdateError("release manifest fields are invalid")
    if type(value["schema"]) is not int or value["schema"] != 1:
        raise UpdateError("release manifest schema is unsupported")
    parse_version(value["version"])
    if value["tag"] != f"v{value['version']}":
        raise UpdateError("release tag and version do not match")
    if value["repository"] != repository:
        raise UpdateError("release manifest targets another repository")
    if (
        not isinstance(value["published_utc"], str)
        or not value["published_utc"].endswith("Z")
    ):
        raise UpdateError("release publication time is invalid")
    builds = value["supported_steam_builds"]
    if (
        not isinstance(builds, list)
        or not builds
        or len(builds) != len(set(builds))
        or any(
            not isinstance(build, str)
            or STEAM_BUILD.fullmatch(build) is None
            for build in builds
        )
    ):
        raise UpdateError("supported Steam build list is invalid")
    if (
        not isinstance(value["minimum_macos"], str)
        or re.fullmatch(r"[0-9]+\.[0-9]+", value["minimum_macos"])
        is None
    ):
        raise UpdateError("minimum macOS version is invalid")
    if value["architecture"] != "arm64":
        raise UpdateError("release architecture is unsupported")
    validate_artifact(
        value["installer"], repository, "RealSteamOnMac-Install.pkg"
    )
    validate_artifact(
        value["updater"], repository, "RealSteamOnMac-Update.pkg"
    )
    validate_artifact(
        value["uninstaller"],
        repository,
        "RealSteamOnMac-Uninstall.pkg",
    )
    if value["updater"] == value["installer"]:
        raise UpdateError("update package must be distinct from installer")
    return value


def select_update_artifact(manifest):
    updater = manifest.get("updater")
    if not isinstance(updater, dict):
        raise UpdateError("release manifest has no update package")
    return updater


def fetch_bounded(url, destination, maximum):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "RealSteamOnMac-Updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > maximum:
            raise UpdateError("download exceeds its size limit")
        total = 0
        digest = hashlib.sha256()
        with open(destination, "wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum:
                    raise UpdateError("download exceeds its size limit")
                digest.update(chunk)
                stream.write(chunk)
    return total, digest.hexdigest()


def load_latest_release(repository, api_base):
    url = f"{api_base.rstrip('/')}/repos/{repository}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "RealSteamOnMac-Updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise UpdateError("GitHub release response is too large")
    value = json.loads(data)
    assets = value.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("GitHub release has no asset list")
    result = {}
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if isinstance(name, str) and isinstance(url, str):
            result[name] = url
    for required in (MANIFEST_NAME, SIGNATURE_NAME):
        if required not in result:
            raise UpdateError(f"GitHub release is missing {required}")
    return result


def verify_manifest(verifier, public_key_hex, manifest, signature):
    result = subprocess.run(
        [
            str(verifier),
            public_key_hex,
            str(manifest),
            str(signature),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "signature verification failed"
        raise UpdateError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-version", required=True)
    parser.add_argument("--steam-build", required=True)
    parser.add_argument(
        "--repository", default="dazi2011/RealSteamOnMac"
    )
    parser.add_argument(
        "--api-base", default="https://api.github.com"
    )
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--verifier", required=True, type=Path)
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path.home()
        / "Library/Caches/RealSteamOnMac/updates",
    )
    parser.add_argument("--install", action="store_true")
    arguments = parser.parse_args()

    current_version = parse_version(arguments.current_version)
    if STEAM_BUILD.fullmatch(arguments.steam_build) is None:
        raise UpdateError("current Steam build is invalid")
    public_key_hex = arguments.public_key.read_text(
        encoding="ascii"
    ).strip()
    if re.fullmatch(r"[0-9a-f]{64}", public_key_hex) is None:
        raise UpdateError("release public key is invalid")
    if not arguments.verifier.is_file() or not os.access(
        arguments.verifier, os.X_OK
    ):
        raise UpdateError("release signature verifier is unavailable")

    assets = load_latest_release(
        arguments.repository, arguments.api_base
    )
    arguments.download_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(
        prefix=".update.", dir=arguments.download_dir
    ) as temporary:
        temporary_path = Path(temporary)
        manifest_path = temporary_path / MANIFEST_NAME
        signature_path = temporary_path / SIGNATURE_NAME
        fetch_bounded(
            assets[MANIFEST_NAME],
            manifest_path,
            MAX_MANIFEST_BYTES,
        )
        fetch_bounded(
            assets[SIGNATURE_NAME],
            signature_path,
            MAX_SIGNATURE_BYTES,
        )
        verify_manifest(
            arguments.verifier,
            public_key_hex,
            manifest_path,
            signature_path,
        )
        manifest = validate_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            arguments.repository,
        )
        latest_version = parse_version(manifest["version"])
        if latest_version <= current_version:
            print(
                json.dumps(
                    {
                        "status": "current",
                        "version": arguments.current_version,
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.steam_build not in manifest[
            "supported_steam_builds"
        ]:
            raise UpdateError(
                "the latest release does not support this Steam build"
            )
        package = select_update_artifact(manifest)
        destination = arguments.download_dir / package["name"]
        size, digest = fetch_bounded(
            package["url"], destination, package["size"]
        )
        if size != package["size"] or digest != package["sha256"]:
            destination.unlink(missing_ok=True)
            raise UpdateError("update package verification failed")
        if arguments.install:
            if os.geteuid() == 0:
                subprocess.run(
                    [
                        "/usr/sbin/installer",
                        "-pkg",
                        str(destination),
                        "-target",
                        "/",
                    ],
                    check=True,
                )
            else:
                subprocess.run(
                    ["/usr/bin/open", str(destination)], check=True
                )
        print(
            json.dumps(
                {
                    "status": "update_available",
                    "version": manifest["version"],
                    "package": str(destination),
                    "install_started": arguments.install,
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        UpdateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        urllib.error.URLError,
        subprocess.SubprocessError,
    ) as error:
        print(f"update check failed: {error}", file=sys.stderr)
        raise SystemExit(1)
