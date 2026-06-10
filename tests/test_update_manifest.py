import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "script" / "check_for_updates.py"
SPEC = importlib.util.spec_from_file_location(
    "check_for_updates", MODULE_PATH
)
updates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updates)


def valid_manifest():
    return {
        "schema": 1,
        "version": "0.1.1",
        "tag": "v0.1.1",
        "repository": "dazi2011/RealSteamOnMac",
        "published_utc": "2026-06-10T03:00:00Z",
        "supported_steam_builds": ["1780705203", "1780965181"],
        "minimum_macos": "14.0",
        "architecture": "arm64",
        "installer": {
            "name": "RealSteamOnMac-Install.pkg",
            "sha256": "a" * 64,
            "size": 1024,
            "url": (
                "https://github.com/dazi2011/RealSteamOnMac/"
                "releases/download/v0.1.1/RealSteamOnMac-Install.pkg"
            ),
        },
        "uninstaller": {
            "name": "RealSteamOnMac-Uninstall.pkg",
            "sha256": "b" * 64,
            "size": 1024,
            "url": (
                "https://github.com/dazi2011/RealSteamOnMac/"
                "releases/download/v0.1.1/RealSteamOnMac-Uninstall.pkg"
            ),
        },
    }


class UpdateManifestTests(unittest.TestCase):
    def test_accepts_strict_manifest(self):
        value = valid_manifest()
        self.assertIs(
            updates.validate_manifest(
                value, "dazi2011/RealSteamOnMac"
            ),
            value,
        )

    def test_rejects_unknown_field(self):
        value = valid_manifest()
        value["extra"] = True
        with self.assertRaises(updates.UpdateError):
            updates.validate_manifest(
                value, "dazi2011/RealSteamOnMac"
            )

    def test_rejects_cross_repository_url(self):
        value = valid_manifest()
        value["installer"]["url"] = (
            "https://github.com/attacker/project/releases/download/"
            "v0.1.1/RealSteamOnMac-Install.pkg"
        )
        with self.assertRaises(updates.UpdateError):
            updates.validate_manifest(
                value, "dazi2011/RealSteamOnMac"
            )

    def test_rejects_unsupported_architecture(self):
        value = valid_manifest()
        value["architecture"] = "x86_64"
        with self.assertRaises(updates.UpdateError):
            updates.validate_manifest(
                value, "dazi2011/RealSteamOnMac"
            )

    def test_swift_verifier_accepts_signature_and_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private_key = root / "private.pem"
            public_key = root / "public.hex"
            payload = root / "manifest.json"
            signature = root / "manifest.sig"
            verifier = root / "verify"
            subprocess.run(
                [
                    "/opt/homebrew/bin/openssl",
                    "genpkey",
                    "-algorithm",
                    "ED25519",
                    "-out",
                    private_key,
                ],
                check=True,
            )
            subprocess.run(
                [
                    "/usr/bin/swiftc",
                    "-O",
                    ROOT / "script/verify_release_signature.swift",
                    "-o",
                    verifier,
                ],
                check=True,
            )
            payload.write_text(
                json.dumps(valid_manifest(), sort_keys=True),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "/opt/homebrew/bin/openssl",
                    "pkeyutl",
                    "-sign",
                    "-rawin",
                    "-inkey",
                    private_key,
                    "-in",
                    payload,
                    "-out",
                    signature,
                ],
                check=True,
            )
            script = (
                "from cryptography.hazmat.primitives import "
                "serialization\n"
                "from pathlib import Path\n"
                f"p=Path({str(private_key)!r})\n"
                "k=serialization.load_pem_private_key("
                "p.read_bytes(),password=None).public_key()\n"
                "print(k.public_bytes(serialization.Encoding.Raw,"
                "serialization.PublicFormat.Raw).hex())\n"
            )
            key_hex = subprocess.check_output(
                ["/usr/bin/python3", "-c", script], text=True
            ).strip()
            public_key.write_text(key_hex, encoding="ascii")
            subprocess.run(
                [
                    verifier,
                    key_hex,
                    payload,
                    signature,
                ],
                check=True,
            )
            payload.write_text("tampered", encoding="utf-8")
            result = subprocess.run(
                [verifier, key_hex, payload, signature],
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
