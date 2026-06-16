import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script"
RUNTIME = ROOT / "runtime"
for directory in (SCRIPT, RUNTIME):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import run_game_acceptance as acceptance


def write_manifest(
    path,
    appid,
    installdir,
    *,
    state_flags="4",
    size_on_disk="1024",
    installed=True,
    staged=False,
):
    installed_section = ""
    if installed:
        installed_section = '''
    "InstalledDepots"
    {
        "100"
        {
            "manifest" "200"
            "size" "1024"
        }
    }
'''
    staged_section = ""
    if staged:
        staged_section = '''
    "StagedDepots"
    {
        "100"
        {
            "manifest" "201"
            "size" "1024"
        }
    }
'''
    path.write_text(
        f'''"AppState"
{{
    "appid" "{appid}"
    "name" "Fixture"
    "StateFlags" "{state_flags}"
    "installdir" "{installdir}"
    "SizeOnDisk" "{size_on_disk}"
    "buildid" "300"
    "UpdateResult" "0"
{installed_section}{staged_section}}}
''',
        encoding="utf-8",
    )


def descriptor(appid, selected_entry_id, entries):
    return {
        "schema": 1,
        "appid": appid,
        "selected_entry_id": selected_entry_id,
        "entries": entries,
    }


def entry(
    entry_id,
    os_name,
    executable,
    *,
    working_directory=".",
    arguments="",
    is_default=True,
):
    return {
        "id": entry_id,
        "os": os_name,
        "executable": executable,
        "working_directory": working_directory,
        "arguments": arguments,
        "is_default": is_default,
    }


class GameAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.steamapps = self.root / "steamapps"
        self.common = self.steamapps / "common"
        self.compatdata = self.steamapps / "compatdata"
        self.config_root = self.root / "apps"
        self.evidence_root = self.root / "evidence"
        for directory in (
            self.common,
            self.compatdata,
            self.config_root,
            self.evidence_root,
        ):
            directory.mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def inspect(self, appid, installdir, launch_descriptor):
        manifest = self.steamapps / f"appmanifest_{appid}.acf"
        install_path = self.common / installdir
        return acceptance.inspect_game_record(
            appid=appid,
            manifest_path=manifest,
            install_path=install_path,
            launch_descriptor=launch_descriptor,
            config_path=self.config_root / f"{appid}.json",
            compat_data_path=self.compatdata / str(appid),
            evidence_root=self.evidence_root / str(appid),
        )

    def test_aimlabs_falls_back_from_macos_entry_to_windows_pe(self):
        self.assertTrue(hasattr(acceptance, "inspect_game_record"))
        appid = 714010
        installdir = "Aim Lab"
        install_path = self.common / installdir
        install_path.mkdir()
        (install_path / "AimLab_tb.exe").write_bytes(b"MZfixture")
        write_manifest(
            self.steamapps / f"appmanifest_{appid}.acf",
            appid,
            installdir,
        )
        value = descriptor(
            appid,
            "1",
            [
                entry("0", "windows", "AimLab_tb.exe"),
                entry("1", "macos", "AimLab.app"),
            ],
        )

        result = self.inspect(appid, installdir, value)

        self.assertEqual(result["state"]["diagnostic"], "ready")
        self.assertEqual(result["launch"]["entry_id"], "0")
        self.assertEqual(result["launch"]["executable"], "AimLab_tb.exe")
        self.assertFalse(result["container"]["exists"])
        self.assertFalse((self.compatdata / str(appid)).exists())

    def test_hogwarts_falls_back_from_missing_test_target(self):
        appid = 990080
        installdir = "Hogwarts Legacy"
        install_path = self.common / installdir
        install_path.mkdir()
        (install_path / "HogwartsLegacy.exe").write_bytes(b"MZfixture")
        write_manifest(
            self.steamapps / f"appmanifest_{appid}.acf",
            appid,
            installdir,
        )
        value = descriptor(
            appid,
            "0",
            [
                entry(
                    "0",
                    "windows",
                    "Phoenix/Binaries/Win64/Phoenix-Win64-Test.exe",
                    is_default=False,
                ),
                entry("13", "windows", "HogwartsLegacy.exe"),
            ],
        )

        result = self.inspect(appid, installdir, value)

        self.assertEqual(result["launch"]["entry_id"], "13")
        self.assertEqual(
            result["launch"]["executable"], "HogwartsLegacy.exe"
        )

    def test_incomplete_download_is_reported_without_creating_container(self):
        appid = 2358720
        installdir = "Black Myth Wukong"
        install_path = self.common / installdir
        install_path.mkdir()
        write_manifest(
            self.steamapps / f"appmanifest_{appid}.acf",
            appid,
            installdir,
            state_flags="1026",
            size_on_disk="0",
            installed=False,
            staged=True,
        )
        value = descriptor(
            appid,
            "0",
            [entry("0", "windows", "b1.exe")],
        )

        result = self.inspect(appid, installdir, value)

        self.assertEqual(
            result["state"]["diagnostic"], "download-incomplete"
        )
        self.assertFalse(result["state"]["launchable"])
        self.assertIsNone(result["launch"])
        self.assertIn("target is missing", result["launch_error"])
        self.assertFalse((self.compatdata / str(appid)).exists())

    def test_existing_config_and_evidence_are_bounded_and_recorded(self):
        appid = 1118200
        installdir = "People Playground"
        install_path = self.common / installdir
        install_path.mkdir()
        (install_path / "People Playground.exe").write_bytes(b"MZfixture")
        write_manifest(
            self.steamapps / f"appmanifest_{appid}.acf",
            appid,
            installdir,
        )
        config = {"renderer": "dxmt", "msync": False}
        (self.config_root / f"{appid}.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        evidence = self.evidence_root / str(appid)
        evidence.mkdir()
        (evidence / "renderer.log").write_text(
            "DXMT ready\n", encoding="utf-8"
        )
        (evidence / "frame-times.json").write_text(
            "[16.7, 16.4]\n", encoding="utf-8"
        )
        value = descriptor(
            appid,
            "0",
            [entry("0", "windows", "People Playground.exe")],
        )

        result = self.inspect(appid, installdir, value)

        self.assertEqual(result["config"], config)
        self.assertEqual(
            [item["name"] for item in result["evidence"]],
            ["frame-times.json", "renderer.log"],
        )

    def test_bounded_probe_records_success_and_timeout(self):
        self.assertTrue(hasattr(acceptance, "run_bounded_probe"))
        success = acceptance.run_bounded_probe(
            ["/bin/sh", "-c", "printf probe-ok"],
            timeout_seconds=1,
        )
        started = time.monotonic()
        timed_out = acceptance.run_bounded_probe(
            ["/bin/sh", "-c", "sleep 2"],
            timeout_seconds=0.05,
        )

        self.assertEqual(success["exit_code"], 0)
        self.assertEqual(success["stdout"], "probe-ok")
        self.assertFalse(success["timed_out"])
        self.assertTrue(timed_out["timed_out"])
        self.assertLess(time.monotonic() - started, 1)

    def test_report_discovers_game_in_external_steam_library(self):
        self.assertTrue(
            hasattr(acceptance, "build_acceptance_report")
        )
        steam_root = self.root / "Steam"
        external = self.root / "External Library"
        (steam_root / "steamapps").mkdir(parents=True)
        external_steamapps = external / "steamapps"
        install_path = external_steamapps / "common" / "Red Dead Redemption 2"
        install_path.mkdir(parents=True)
        (install_path / "PlayRDR2.exe").write_bytes(b"MZfixture")
        appid = 1174180
        write_manifest(
            external_steamapps / f"appmanifest_{appid}.acf",
            appid,
            "Red Dead Redemption 2",
        )
        (steam_root / "steamapps" / "libraryfolders.vdf").write_text(
            f'''"libraryfolders"
{{
    "0"
    {{
        "path" "{steam_root}"
    }}
    "1"
    {{
        "path" "{external}"
    }}
}}
''',
            encoding="utf-8",
        )
        value = descriptor(
            appid,
            "0",
            [entry("0", "windows", "PlayRDR2.exe")],
        )

        report = acceptance.build_acceptance_report(
            steam_root=steam_root,
            appids=[appid],
            descriptor_loader=lambda requested_appid, _: value,
            config_root=self.config_root,
            evidence_root=self.evidence_root,
        )

        self.assertEqual(report["summary"]["requested"], 1)
        self.assertEqual(report["summary"]["ready"], 1)
        self.assertEqual(report["games"][0]["appid"], appid)
        self.assertIn("name", report["games"][0])
        self.assertEqual(report["games"][0]["name"], "Fixture")
        self.assertEqual(
            Path(report["games"][0]["manifest"]).parent,
            external_steamapps.resolve(),
        )
        self.assertEqual(
            report["games"][0]["launch"]["executable"],
            "PlayRDR2.exe",
        )

    def test_cli_writes_replayable_json_report(self):
        self.assertTrue(hasattr(acceptance, "main"))
        steam_root = self.root / "Steam"
        steamapps = steam_root / "steamapps"
        install_path = steamapps / "common" / "People Playground"
        install_path.mkdir(parents=True)
        (install_path / "People Playground.exe").write_bytes(b"MZfixture")
        appid = 1118200
        write_manifest(
            steamapps / f"appmanifest_{appid}.acf",
            appid,
            "People Playground",
        )
        descriptor_root = self.root / "descriptors"
        descriptor_root.mkdir()
        (descriptor_root / f"{appid}.json").write_text(
            json.dumps(
                descriptor(
                    appid,
                    "0",
                    [
                        entry(
                            "0",
                            "windows",
                            "People Playground.exe",
                        )
                    ],
                )
            ),
            encoding="utf-8",
        )
        output = self.root / "report.json"

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "script/run_game_acceptance.py"),
                "--steam-root",
                str(steam_root),
                "--descriptor-root",
                str(descriptor_root),
                "--config-root",
                str(self.config_root),
                "--evidence-root",
                str(self.evidence_root),
                "--appid",
                str(appid),
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["summary"]["ready"], 1)
        self.assertEqual(report["games"][0]["appid"], appid)

    def test_report_preserves_manifest_state_when_descriptor_fails(self):
        steam_root = self.root / "Steam"
        steamapps = steam_root / "steamapps"
        install_path = steamapps / "common" / "Titanfall2"
        install_path.mkdir(parents=True)
        (install_path / "content.bin").write_bytes(b"fixture")
        appid = 1237970
        write_manifest(
            steamapps / f"appmanifest_{appid}.acf",
            appid,
            "Titanfall2",
        )

        def reject_descriptor(_appid, _install_path):
            raise ValueError("protocol-only launch record")

        report = acceptance.build_acceptance_report(
            steam_root=steam_root,
            appids=[appid],
            descriptor_loader=reject_descriptor,
            config_root=self.config_root,
            evidence_root=self.evidence_root,
        )

        game = report["games"][0]
        self.assertNotIn("error", game)
        self.assertEqual(game["state"]["diagnostic"], "ready")
        self.assertIsNone(game["launch"])
        self.assertEqual(
            game["launch_error"], "protocol-only launch record"
        )
        self.assertEqual(report["summary"]["blocked"], 1)

    def test_report_records_installed_runtime_fingerprint_mismatch(self):
        self.assertTrue(
            hasattr(acceptance, "collect_runtime_fingerprints")
        )
        steam_root = self.root / "Steam"
        steamapps = steam_root / "steamapps"
        install_path = steamapps / "common" / "Aim Lab"
        install_path.mkdir(parents=True)
        (install_path / "AimLab_tb.exe").write_bytes(b"MZfixture")
        appid = 714010
        write_manifest(
            steamapps / f"appmanifest_{appid}.acf",
            appid,
            "Aim Lab",
        )
        runtime_bin = self.root / "installed-runtime"
        runtime_bin.mkdir()
        (runtime_bin / "realsteamonmac-runtime").write_text(
            "old runtime\n", encoding="utf-8"
        )
        (runtime_bin / "steam_launch_descriptor.py").write_text(
            "old descriptor\n", encoding="utf-8"
        )

        report = acceptance.build_acceptance_report(
            steam_root=steam_root,
            appids=[appid],
            descriptor_loader=lambda _appid, _install_path: descriptor(
                appid,
                "0",
                [
                    entry("0", "windows", "aimlab_tb.exe"),
                    entry("1", "macos", "AimLab.app"),
                ],
            ),
            config_root=self.config_root,
            evidence_root=self.evidence_root,
            installed_runtime_bin=runtime_bin,
        )

        self.assertFalse(report["runtime"]["matches_source"])
        self.assertFalse(
            report["runtime"]["files"]["steam_launch_descriptor.py"][
                "matches_source"
            ]
        )
        self.assertEqual(
            report["games"][0]["launch"]["executable"],
            "AimLab_tb.exe",
        )


if __name__ == "__main__":
    unittest.main()
