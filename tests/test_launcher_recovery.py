import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "launcher_recovery.py"
SPEC = importlib.util.spec_from_file_location(
    "launcher_recovery", MODULE_PATH
)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


class LauncherRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.game = self.root / "steamapps" / "common" / "RDR2"
        self.game.mkdir(parents=True)
        self.game_file = self.game / "PlayRDR2.exe"
        self.game_file.write_bytes(b"MZgame")
        self.compat_data = (
            self.root / "steamapps" / "compatdata" / "1174180"
        )
        self.prefix = self.compat_data / "pfx"
        self.prefix.mkdir(parents=True)
        self.state = self.compat_data / "realsteamonmac"
        self.state.mkdir()
        self.system_reg = self.prefix / "system.reg"
        self.user_reg = self.prefix / "user.reg"
        self.userdef_reg = self.prefix / "userdef.reg"
        for path in (
            self.system_reg,
            self.user_reg,
            self.userdef_reg,
        ):
            path.write_text("WINE REGISTRY Version 2\n", encoding="utf-8")
        self.user_data = (
            self.prefix
            / "drive_c"
            / "users"
            / "fixture"
            / "Documents"
            / "Rockstar Games"
            / "Red Dead Redemption 2"
            / "Profiles"
            / "profile.dat"
        )
        self.user_data.parent.mkdir(parents=True)
        self.user_data.write_bytes(b"user-save")
        redistributables = self.game / "Redistributables"
        redistributables.mkdir()
        self.social_installer = (
            redistributables / "Social-Club-Setup.exe"
        )
        self.launcher_installer = (
            redistributables / "Rockstar-Games-Launcher.exe"
        )
        self.social_installer.write_bytes(b"MZsocial-installer")
        self.launcher_installer.write_bytes(b"MZlauncher-installer")
        self.recipe = {
            "id": "rdr2-rockstar",
            "appid": 1174180,
            "snapshot_paths": [
                "system.reg",
                "user.reg",
                "userdef.reg",
                "drive_c/Program Files/Rockstar Games",
                "drive_c/ProgramData/Rockstar Games",
                "drive_c/users/fixture/Documents/Rockstar Games",
            ],
            "steps": [
                self.step(
                    "social-club",
                    "Redistributables/Social-Club-Setup.exe",
                    self.social_installer,
                    ["/silent"],
                    "drive_c/Program Files/Rockstar Games/"
                    "Social Club/SocialClubHelper.exe",
                    r"Software\Wow6432Node\Rockstar Games"
                    r"\Rockstar Games Social Club",
                ),
                self.step(
                    "rockstar-launcher",
                    "Redistributables/Rockstar-Games-Launcher.exe",
                    self.launcher_installer,
                    ["/s", "/t"],
                    "drive_c/Program Files/Rockstar Games/"
                    "Launcher/Launcher.exe",
                    r"Software\Wow6432Node\Rockstar Games\Launcher",
                ),
            ],
        }

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def step(
        self,
        step_id,
        relative_installer,
        installer,
        arguments,
        pe_path,
        registry_key,
    ):
        return {
            "id": step_id,
            "installer": relative_installer,
            "size": installer.stat().st_size,
            "sha256": self.digest(installer),
            "arguments": arguments,
            "success_codes": [0],
            "postconditions": [
                {"type": "pe", "path": pe_path},
                {
                    "type": "registry_key",
                    "file": "system.reg",
                    "key": registry_key,
                },
            ],
        }

    def context(self):
        return {
            "appid": 1174180,
            "install_path": self.game,
            "compat_data": self.compat_data,
            "prefix": self.prefix,
            "state": self.state,
        }

    def append_registry_key(self, key):
        encoded = key.replace("\\", "\\\\")
        with self.system_reg.open("a", encoding="utf-8") as stream:
            stream.write(f"\n[{encoded}] 123\n")

    def satisfy_step(self, index):
        step = self.recipe["steps"][index]
        pe = self.prefix / step["postconditions"][0]["path"]
        pe.parent.mkdir(parents=True, exist_ok=True)
        pe.write_bytes(b"MZinstalled")
        self.append_registry_key(step["postconditions"][1]["key"])

    def test_partial_launcher_state_reruns_from_first_missing_step(self):
        self.satisfy_step(1)

        plan = recovery.plan_launcher_recovery(
            self.context(),
            self.recipe,
            timestamp="20260611T111700Z",
        )

        self.assertEqual(plan["state"], "recoverable")
        self.assertEqual(
            [step["id"] for step in plan["steps"]],
            ["social-club", "rockstar-launcher"],
        )
        self.assertEqual(plan["preserve"], [str(self.game), str(self.prefix)])
        self.assertTrue(Path(plan["snapshot_path"]).is_dir())
        self.assertEqual(self.user_data.read_bytes(), b"user-save")
        self.assertNotIn("delete", json.dumps(plan).lower())

    def test_complete_state_is_a_noop_without_a_snapshot(self):
        self.satisfy_step(0)
        self.satisfy_step(1)

        plan = recovery.plan_launcher_recovery(
            self.context(),
            self.recipe,
            timestamp="20260611T111701Z",
        )

        self.assertEqual(plan["state"], "complete")
        self.assertEqual(plan["steps"], [])
        self.assertEqual(plan["snapshot_path"], "")
        self.assertFalse((self.state / "recovery").exists())

    def test_tampered_depot_installer_fails_closed_with_snapshot(self):
        self.social_installer.write_bytes(b"MZtampered")

        with self.assertRaisesRegex(
            recovery.LauncherRecoveryError,
            "snapshot:",
        ) as raised:
            recovery.plan_launcher_recovery(
                self.context(),
                self.recipe,
                timestamp="20260611T111702Z",
            )

        snapshot = Path(raised.exception.snapshot_path)
        self.assertTrue(snapshot.is_dir())
        self.assertTrue((snapshot / "manifest.json").is_file())
        self.assertEqual(self.game_file.read_bytes(), b"MZgame")
        self.assertEqual(self.user_data.read_bytes(), b"user-save")

    def test_non_pe_installed_target_fails_closed_with_snapshot(self):
        social = (
            self.prefix
            / self.recipe["steps"][0]["postconditions"][0]["path"]
        )
        social.parent.mkdir(parents=True)
        social.write_bytes(b"not-a-pe")

        with self.assertRaisesRegex(
            recovery.LauncherRecoveryError,
            "installed target is not PE",
        ) as raised:
            recovery.plan_launcher_recovery(
                self.context(),
                self.recipe,
                timestamp="20260611T111703Z",
            )

        self.assertTrue(Path(raised.exception.snapshot_path).is_dir())

    def test_snapshot_manifest_records_registry_and_user_data_hashes(self):
        plan = recovery.plan_launcher_recovery(
            self.context(),
            self.recipe,
            timestamp="20260611T111704Z",
        )

        snapshot = Path(plan["snapshot_path"])
        manifest = json.loads(
            (snapshot / "manifest.json").read_text(encoding="utf-8")
        )
        records = {record["source"]: record for record in manifest["files"]}
        self.assertEqual(
            records[str(self.system_reg)]["sha256"],
            self.digest(self.system_reg),
        )
        self.assertEqual(
            records[str(self.user_data)]["sha256"],
            self.digest(self.user_data),
        )
        self.assertFalse(
            any(
                str(self.game_file) == record["source"]
                for record in manifest["files"]
            )
        )

    def test_execute_runs_only_pinned_installers_and_writes_report(self):
        commands = []

        def runner(command, **kwargs):
            commands.append([str(part) for part in command])
            index = len(commands) - 1
            self.satisfy_step(index)
            return mock.Mock(returncode=0)

        result = recovery.execute_launcher_recovery(
            self.context(),
            self.recipe,
            Path("/fixture/wine64"),
            {"WINEPREFIX": str(self.prefix)},
            runner=runner,
            timestamp="20260611T111705Z",
        )

        self.assertEqual(
            commands,
            [
                [
                    "/fixture/wine64",
                    str(self.social_installer.resolve()),
                    "/silent",
                ],
                [
                    "/fixture/wine64",
                    str(self.launcher_installer.resolve()),
                    "/s",
                    "/t",
                ],
            ],
        )
        self.assertEqual(result["state"], "recovered")
        report = Path(result["report_path"])
        self.assertEqual(report.stat().st_mode & 0o777, 0o600)
        report_value = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(
            [step["exit_code"] for step in report_value["steps"]],
            [0, 0],
        )
        self.assertEqual(self.game_file.read_bytes(), b"MZgame")
        self.assertEqual(self.user_data.read_bytes(), b"user-save")

    def test_repository_catalog_pins_rdr2_depot_prerequisites(self):
        catalog = recovery.load_launcher_recovery_catalog(
            ROOT / "config" / "dependencies.json"
        )

        recipe = catalog[1174180]
        self.assertEqual(recipe["id"], "rdr2-rockstar")
        self.assertEqual(
            [
                (
                    step["id"],
                    step["installer"],
                    step["arguments"],
                    step["size"],
                    step["sha256"],
                )
                for step in recipe["steps"]
            ],
            [
                (
                    "social-club",
                    "Redistributables/Social-Club-Setup.exe",
                    ["/silent"],
                    127419512,
                    "8c057d4199ded0bd70e2f769548dd97bec9e0e89a27109d"
                    "61026b286d79c7cb5",
                ),
                (
                    "rockstar-launcher",
                    "Redistributables/Rockstar-Games-Launcher.exe",
                    ["/s", "/t"],
                    112102008,
                    "51afae4b364112286fda8abeeda64867830792d6134ab6cf"
                    "2d54bfbb8d21ece7",
                ),
            ],
        )
        postconditions = json.dumps(recipe["steps"])
        self.assertIn("SocialClubHelper.exe", postconditions)
        self.assertIn("Launcher.exe", postconditions)
        self.assertIn("registry_key", postconditions)


if __name__ == "__main__":
    unittest.main()
