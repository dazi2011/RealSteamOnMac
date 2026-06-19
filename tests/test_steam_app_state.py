import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "steam_app_state.py"
SPEC = importlib.util.spec_from_file_location("steam_app_state", MODULE_PATH)
steam_app_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(steam_app_state)


class SteamAppStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.install_path = self.root / "steamapps" / "common" / "Fixture Game"
        self.install_path.mkdir(parents=True)
        self.manifest = self.root / "steamapps" / "appmanifest_1118200.acf"

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(
        self,
        *,
        state_flags,
        size_on_disk,
        installed_depots="",
        staged_depots="",
        update_result="0",
        bytes_to_download="0",
        bytes_downloaded="0",
        bytes_to_stage="0",
        bytes_staged="0",
    ):
        installed_section = (
            f'\t"InstalledDepots"\n\t{{\n{installed_depots}\t}}\n'
            if installed_depots is not None
            else ""
        )
        staged_section = (
            f'\t"StagedDepots"\n\t{{\n{staged_depots}\t}}\n'
            if staged_depots is not None
            else ""
        )
        self.manifest.write_text(
            '"AppState"\n'
            "{\n"
            '\t"appid"\t\t"1118200"\n'
            '\t"name"\t\t"Fixture Game"\n'
            f'\t"StateFlags"\t\t"{state_flags}"\n'
            '\t"installdir"\t\t"Fixture Game"\n'
            f'\t"SizeOnDisk"\t\t"{size_on_disk}"\n'
            '\t"buildid"\t\t"12345"\n'
            f'\t"UpdateResult"\t\t"{update_result}"\n'
            f'\t"BytesToDownload"\t\t"{bytes_to_download}"\n'
            f'\t"BytesDownloaded"\t\t"{bytes_downloaded}"\n'
            f'\t"BytesToStage"\t\t"{bytes_to_stage}"\n'
            f'\t"BytesStaged"\t\t"{bytes_staged}"\n'
            f"{installed_section}"
            f"{staged_section}"
            "}\n",
            encoding="utf-8",
        )

    def test_fully_installed_game_is_launchable(self):
        (self.install_path / "Fixture.exe").write_bytes(b"MZfixture")
        self.write_manifest(
            state_flags=4,
            size_on_disk=128281011495,
            installed_depots=(
                '\t\t"1174182"\n'
                "\t\t{\n"
                '\t\t\t"manifest"\t\t"2258488483491377476"\n'
                '\t\t\t"size"\t\t"128281011495"\n'
                "\t\t}\n"
            ),
            staged_depots=None,
        )

        state = steam_app_state.inspect_app_manifest(
            self.manifest, 1118200, self.install_path
        )

        self.assertTrue(state["launchable"])
        self.assertEqual(state["installed_depot_count"], 1)
        self.assertEqual(state["installed_depot_bytes"], 128281011495)
        self.assertEqual(state["bytes_to_download"], 0)
        self.assertEqual(state["bytes_to_stage"], 0)
        self.assertEqual(state["diagnostic"], "ready")

    def test_files_missing_state_requires_repair(self):
        (self.install_path / "Phoenix").mkdir()
        (self.install_path / "Phoenix" / "HogwartsLegacy.exe").write_bytes(
            b"MZfixture"
        )
        self.write_manifest(
            state_flags=36,
            size_on_disk=74056715310,
            installed_depots=(
                '\t\t"990081"\n'
                "\t\t{\n"
                '\t\t\t"manifest"\t\t"5198899101792588169"\n'
                '\t\t\t"size"\t\t"74056715310"\n'
                "\t\t}\n"
            ),
            staged_depots=None,
        )

        state = steam_app_state.inspect_app_manifest(
            self.manifest, 1118200, self.install_path
        )

        self.assertFalse(state["launchable"])
        self.assertIn("files-missing", state["blocking_states"])
        self.assertEqual(state["bytes_to_download"], 0)
        self.assertEqual(state["diagnostic"], "repair-required")

    def test_installed_update_with_pending_bytes_is_download_incomplete(self):
        (self.install_path / "AimLab_tb.exe").write_bytes(b"MZfixture")
        self.write_manifest(
            state_flags=38,
            size_on_disk=19731876148,
            bytes_to_download="47530849",
            installed_depots=(
                '\t\t"714011"\n'
                "\t\t{\n"
                '\t\t\t"manifest"\t\t"3280265244216468903"\n'
                '\t\t\t"size"\t\t"19731876148"\n'
                "\t\t}\n"
            ),
            staged_depots=None,
        )

        state = steam_app_state.inspect_app_manifest(
            self.manifest, 1118200, self.install_path
        )

        self.assertFalse(state["launchable"])
        self.assertIn("update-required", state["blocking_states"])
        self.assertIn("files-missing", state["blocking_states"])
        self.assertEqual(state["bytes_to_download"], 47530849)
        self.assertEqual(state["diagnostic"], "download-incomplete")

    def test_staged_only_download_is_not_installed(self):
        self.write_manifest(
            state_flags=1026,
            size_on_disk=0,
            installed_depots="",
            staged_depots=(
                '\t\t"2358721"\n'
                "\t\t{\n"
                '\t\t\t"manifest"\t\t"1111111111111111111"\n'
                '\t\t\t"size"\t\t"149800000000"\n'
                "\t\t}\n"
            ),
        )

        state = steam_app_state.inspect_app_manifest(
            self.manifest, 1118200, self.install_path
        )

        self.assertFalse(state["launchable"])
        self.assertEqual(state["installed_depot_count"], 0)
        self.assertEqual(state["staged_depot_count"], 1)
        self.assertEqual(state["diagnostic"], "download-incomplete")

    def test_empty_install_directory_is_not_launchable(self):
        self.write_manifest(
            state_flags=4,
            size_on_disk=4096,
            installed_depots=(
                '\t\t"1118201"\n'
                "\t\t{\n"
                '\t\t\t"manifest"\t\t"2222222222222222222"\n'
                '\t\t\t"size"\t\t"4096"\n'
                "\t\t}\n"
            ),
            staged_depots=None,
        )

        state = steam_app_state.inspect_app_manifest(
            self.manifest, 1118200, self.install_path
        )

        self.assertFalse(state["launchable"])
        self.assertFalse(state["install_path_nonempty"])
        self.assertEqual(state["diagnostic"], "content-missing")

    def test_manifest_without_installed_depots_is_not_launchable(self):
        (self.install_path / "Fixture.exe").write_bytes(b"MZfixture")
        self.write_manifest(
            state_flags=4,
            size_on_disk=4096,
            installed_depots=None,
            staged_depots=None,
        )

        state = steam_app_state.inspect_app_manifest(
            self.manifest, 1118200, self.install_path
        )

        self.assertFalse(state["launchable"])
        self.assertEqual(state["installed_depot_count"], 0)
        self.assertEqual(state["diagnostic"], "installed-depots-missing")


if __name__ == "__main__":
    unittest.main()
