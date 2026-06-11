import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
