import importlib.util
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "steam_launch_descriptor.py"
SPEC = importlib.util.spec_from_file_location(
    "steam_launch_descriptor", MODULE_PATH
)
descriptor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(descriptor)


class SteamLaunchDescriptorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.install_path = self.root / "Fixture Game"
        self.install_path.mkdir()
        self.descriptor_path = self.root / "990080.json"

    def tearDown(self):
        self.temporary.cleanup()

    def write_pe(self, relative_path):
        path = self.install_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"MZfixture")
        return path

    def write_descriptor(self, appid, selected_entry_id, entries):
        self.descriptor_path.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "appid": appid,
                    "selected_entry_id": selected_entry_id,
                    "entries": entries,
                }
            ),
            encoding="utf-8",
        )

    def write_appinfo(self, apps):
        keys = ["appinfo"]
        seen = {"appinfo"}

        def collect(value):
            for key, child in value.items():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
                if isinstance(child, dict):
                    collect(child)

        for value in apps.values():
            collect(value)
        indices = {key: index for index, key in enumerate(keys)}

        def encode_object(value):
            payload = bytearray()
            for key, child in value.items():
                if isinstance(child, dict):
                    payload.append(0)
                    payload.extend(struct.pack("<i", indices[key]))
                    payload.extend(encode_object(child))
                elif isinstance(child, str):
                    payload.append(1)
                    payload.extend(struct.pack("<i", indices[key]))
                    payload.extend(child.encode("utf-8"))
                    payload.append(0)
                elif isinstance(child, int):
                    payload.append(2)
                    payload.extend(struct.pack("<i", indices[key]))
                    payload.extend(struct.pack("<i", child))
                else:
                    raise TypeError(f"unsupported fixture value: {child!r}")
            payload.append(8)
            return payload

        entries = bytearray()
        for appid, value in apps.items():
            binary_vdf = encode_object({"appinfo": value})
            metadata = (
                struct.pack("<IIQ", 2, 1_700_000_000, 0)
                + (b"\x11" * 20)
                + struct.pack("<I", 123)
                + hashlib.sha1(binary_vdf).digest()
            )
            entries.extend(struct.pack("<II", appid, len(metadata) + len(binary_vdf)))
            entries.extend(metadata)
            entries.extend(binary_vdf)
        entries.extend(struct.pack("<I", 0))
        string_table_offset = 16 + len(entries)
        string_table = bytearray(struct.pack("<I", len(keys)))
        for key in keys:
            string_table.extend(key.encode("utf-8"))
            string_table.append(0)

        path = self.root / "appinfo.vdf"
        path.write_bytes(
            struct.pack("<IIq", 0x07564429, 1, string_table_offset)
            + entries
            + string_table
        )
        return path

    @staticmethod
    def entry(
        entry_id,
        executable,
        *,
        os_name="windows",
        is_default=False,
        working_directory=".",
        arguments="",
    ):
        return {
            "id": entry_id,
            "os": os_name,
            "executable": executable,
            "working_directory": working_directory,
            "arguments": arguments,
            "is_default": is_default,
        }

    def resolve(self, appid=990080):
        return descriptor.resolve_launch_descriptor(
            self.descriptor_path,
            expected_appid=appid,
            install_path=self.install_path,
        )

    def test_hogwarts_falls_back_from_stale_branch_to_release_default(self):
        expected = self.write_pe("HogwartsLegacy.exe")
        self.write_descriptor(
            990080,
            "development",
            [
                self.entry(
                    "development",
                    "Phoenix/Binaries/Win64/Phoenix-Win64-Test.exe",
                    arguments="-branch=development",
                ),
                self.entry(
                    "release",
                    "HogwartsLegacy.exe",
                    is_default=True,
                    arguments=(
                        '--SaveToUserDir -UserDir="Hogwarts Legacy"'
                    ),
                ),
            ],
        )

        selected = self.resolve()

        self.assertEqual(selected["entry_id"], "release")
        self.assertEqual(selected["executable"], expected.resolve())
        self.assertEqual(
            selected["arguments"],
            '--SaveToUserDir -UserDir="Hogwarts Legacy"',
        )

    def test_aimlabs_ignores_selected_macos_app_and_uses_windows_default(self):
        expected = self.write_pe("AimLab_tb.exe")
        self.write_descriptor(
            714010,
            "macos",
            [
                self.entry(
                    "windows",
                    "AimLab_tb.exe",
                    is_default=True,
                ),
                self.entry(
                    "macos",
                    "AimLab.app",
                    os_name="macos",
                    is_default=True,
                ),
            ],
        )

        selected = self.resolve(appid=714010)

        self.assertEqual(selected["entry_id"], "windows")
        self.assertEqual(selected["executable"], expected.resolve())

    def test_rdr2_preserves_explicit_launcher_role(self):
        expected = self.write_pe("PlayRDR2.exe")
        self.write_pe("RDR2.exe")
        self.write_descriptor(
            1174180,
            "default",
            [
                self.entry(
                    "default",
                    "PlayRDR2.exe",
                    is_default=True,
                    arguments="-steam",
                )
            ],
        )

        selected = self.resolve(appid=1174180)

        self.assertEqual(selected["executable"], expected.resolve())
        self.assertNotEqual(selected["executable"].name, "RDR2.exe")
        self.assertEqual(selected["arguments"], "-steam")

    def test_selected_windows_option_wins_over_another_default(self):
        selected_executable = self.write_pe("Game-DX11.exe")
        self.write_pe("Game-DX12.exe")
        self.write_descriptor(
            12345,
            "dx11",
            [
                self.entry(
                    "dx12",
                    "Game-DX12.exe",
                    is_default=True,
                    arguments="-dx12",
                ),
                self.entry(
                    "dx11",
                    "Game-DX11.exe",
                    arguments="-dx11",
                    working_directory="bin",
                ),
            ],
        )
        (self.install_path / "bin").mkdir()

        selected = self.resolve(appid=12345)

        self.assertEqual(selected["entry_id"], "dx11")
        self.assertEqual(
            selected["executable"], selected_executable.resolve()
        )
        self.assertEqual(
            selected["working_directory"],
            (self.install_path / "bin").resolve(),
        )
        self.assertEqual(selected["arguments"], "-dx11")

    def test_no_valid_windows_entry_fails_closed(self):
        self.write_pe("Unrelated.exe")
        self.write_descriptor(
            12345,
            "missing",
            [
                self.entry(
                    "missing",
                    "Missing.exe",
                    is_default=True,
                ),
                self.entry(
                    "macos",
                    "Fixture.app",
                    os_name="macos",
                    is_default=True,
                ),
            ],
        )

        with self.assertRaisesRegex(
            descriptor.LaunchDescriptorError,
            "no valid Windows launch entry",
        ):
            self.resolve(appid=12345)

    def test_descriptor_rejects_appid_mismatch_and_path_escape(self):
        self.write_descriptor(
            12345,
            "escape",
            [
                self.entry(
                    "escape",
                    "../Outside.exe",
                    is_default=True,
                )
            ],
        )

        with self.assertRaisesRegex(
            descriptor.LaunchDescriptorError, "AppID mismatch"
        ):
            self.resolve(appid=54321)
        with self.assertRaisesRegex(
            descriptor.LaunchDescriptorError, "executable path is invalid"
        ):
            self.resolve(appid=12345)

    def test_builds_verified_descriptor_from_v41_appinfo(self):
        expected = self.write_pe("HogwartsLegacy.exe")
        appinfo = self.write_appinfo(
            {
                990080: {
                    "config": {
                        "installdir": "Hogwarts Legacy",
                        "launch": {
                            "0": {
                                "executable": "Phoenix-Win64-Test.exe",
                                "arguments": "-development",
                                "type": "option1",
                                "config": {
                                    "oslist": "windows",
                                    "BetaKey": "development",
                                },
                            },
                            "13": {
                                "executable": "HogwartsLegacy.exe",
                                "arguments": (
                                    '-SaveToUserDir '
                                    '-UserDir="Hogwarts Legacy"'
                                ),
                                "type": "default",
                                "config": {"oslist": "windows"},
                            },
                        },
                    }
                }
            }
        )

        value = descriptor.build_launch_descriptor_from_appinfo(
            appinfo,
            expected_appid=990080,
            install_path=self.install_path,
            requested_target=self.install_path / "Phoenix-Win64-Test.exe",
        )
        selected = descriptor.resolve_launch_descriptor_value(
            value,
            expected_appid=990080,
            install_path=self.install_path,
        )

        self.assertEqual(value["selected_entry_id"], "0")
        self.assertEqual(selected["entry_id"], "13")
        self.assertEqual(selected["executable"], expected.resolve())

    def test_appinfo_target_match_is_windows_case_insensitive(self):
        expected = self.write_pe("AimLab_tb.exe")
        appinfo = self.write_appinfo(
            {
                714010: {
                    "config": {
                        "installdir": "Aim Lab",
                        "launch": {
                            "0": {
                                "executable": "aimlab_tb.exe",
                                "type": "default",
                                "config": {"oslist": "windows"},
                            },
                            "1": {
                                "executable": "AimLab.app",
                                "type": "default",
                                "config": {"oslist": "macos"},
                            },
                        },
                    }
                }
            }
        )

        value = descriptor.build_launch_descriptor_from_appinfo(
            appinfo,
            expected_appid=714010,
            install_path=self.install_path,
            requested_target=self.install_path / "aimlab.APP",
        )
        selected = descriptor.resolve_launch_descriptor_value(
            value,
            expected_appid=714010,
            install_path=self.install_path,
        )

        self.assertEqual(value["selected_entry_id"], "1")
        self.assertEqual(selected["entry_id"], "0")
        self.assertEqual(selected["executable"], expected.resolve())

    def test_appinfo_rejects_binary_vdf_hash_mismatch(self):
        appinfo = self.write_appinfo(
            {
                12345: {
                    "config": {
                        "launch": {
                            "0": {
                                "executable": "Game.exe",
                                "type": "default",
                                "config": {"oslist": "windows"},
                            }
                        }
                    }
                }
            }
        )
        payload = bytearray(appinfo.read_bytes())
        payload[76] ^= 0xFF
        appinfo.write_bytes(payload)

        with self.assertRaisesRegex(
            descriptor.LaunchDescriptorError,
            "binary VDF hash mismatch",
        ):
            descriptor.build_launch_descriptor_from_appinfo(
                appinfo,
                expected_appid=12345,
                install_path=self.install_path,
            )


if __name__ == "__main__":
    unittest.main()
