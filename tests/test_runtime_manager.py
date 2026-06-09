import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "realsteamonmac_runtime.py"
SPEC = importlib.util.spec_from_file_location("realsteamonmac_runtime", MODULE_PATH)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimeManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.steamapps = self.root / "steamapps"
        self.game = self.steamapps / "common" / "Fixture Game"
        self.game.mkdir(parents=True)
        self.executable = self.game / "Fixture.exe"
        self.executable.write_bytes(b"MZfixture")
        self.runtime_root = self.root / "runtimes"
        package = self.runtime_root / "packages" / "fixture"
        for renderer in runtime.RENDERERS:
            wine64 = package / "wine" / renderer / "bin" / "wine64"
            wine64.parent.mkdir(parents=True)
            wine64.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            wine64.chmod(0o755)
        (package / "manifest.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "package_id": "fixture",
                    "renderers": {},
                }
            ),
            encoding="utf-8",
        )
        self.runtime_root.mkdir(exist_ok=True)
        (self.runtime_root / "current").symlink_to("packages/fixture")
        self.package = package

    def tearDown(self):
        self.temporary.cleanup()

    def context(self):
        return runtime.resolve_context(self.executable, "1118200")

    def test_resolves_exact_proton_prefix(self):
        context = self.context()
        self.assertEqual(context["appid"], 1118200)
        self.assertEqual(
            context["prefix"],
            self.steamapps.resolve()
            / "compatdata"
            / "1118200"
            / "pfx",
        )

    def test_rejects_non_pe_target(self):
        target = self.game / "not-pe"
        target.write_text("plain", encoding="utf-8")
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext, "not a PE"
        ):
            runtime.resolve_context(target, "1118200")

    def test_rejects_non_proton_compat_path(self):
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext, "Proton layout"
        ):
            runtime.resolve_context(
                self.executable,
                "1118200",
                str(self.root / "wrong-prefix"),
            )

    def test_config_is_atomic_and_private(self):
        context = self.context()
        saved = runtime.save_config(
            context,
            {
                **runtime.DEFAULT_CONFIG,
                "renderer": "dxmt",
                "retina": True,
            },
        )
        self.assertEqual(saved["renderer"], "dxmt")
        self.assertTrue(saved["retina"])
        self.assertEqual(context["config"].stat().st_mode & 0o777, 0o600)
        self.assertEqual(runtime.load_config(context), saved)

    def test_metalfx_is_gptk_only(self):
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext, "only with the GPTK"
        ):
            runtime.normalize_config(
                {
                    **runtime.DEFAULT_CONFIG,
                    "renderer": "dxmt",
                    "metalfx": True,
                }
            )

    def test_environment_maps_controls(self):
        context = self.context()
        package, _, wine_root, _ = runtime.load_package(
            self.runtime_root, "gptk"
        )
        self.assertTrue(package.is_dir())
        config = {
            **runtime.DEFAULT_CONFIG,
            "msync": True,
            "metal_hud": True,
            "metalfx": True,
            "dxr": True,
            "avx": True,
        }
        with mock.patch.dict(
            os.environ,
            {
                "WINEMSYNC": "stale",
                "D3DM_ENABLE_METALFX": "stale",
            },
            clear=False,
        ):
            environment = runtime.build_environment(
                context, config, wine_root
            )
        self.assertEqual(environment["WINEMSYNC"], "1")
        self.assertEqual(environment["WINEESYNC"], "1")
        self.assertEqual(environment["MTL_HUD_ENABLED"], "1")
        self.assertEqual(environment["D3DM_ENABLE_METALFX"], "1")
        self.assertEqual(environment["D3DM_SUPPORT_DXR"], "1")
        self.assertEqual(environment["ROSETTA_ADVERTISE_AVX"], "1")
        self.assertEqual(
            environment["WINEPREFIX"], str(context["prefix"])
        )
        self.assertEqual(environment["SteamAppId"], str(context["appid"]))
        self.assertEqual(environment["SteamGameId"], str(context["appid"]))
        self.assertEqual(
            environment["STEAM_COMPAT_APP_ID"], str(context["appid"])
        )
        self.assertEqual(
            environment["STEAM_COMPAT_DATA_PATH"],
            str(context["compat_data"]),
        )
        self.assertEqual(
            environment["WINEDLLOVERRIDES"],
            "winemenubuilder.exe=d",
        )

    def test_dxvk_uses_macos_moltenvk_recovery_setting(self):
        context = self.context()
        _, _, wine_root, _ = runtime.load_package(
            self.runtime_root, "dxvk"
        )
        config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxvk",
            "msync": False,
        }
        environment = runtime.build_environment(
            context, config, wine_root
        )
        self.assertEqual(
            environment["MVK_CONFIG_RESUME_LOST_DEVICE"], "1"
        )
        self.assertNotIn("WINEMSYNC", environment)

    def add_steamworks_bridge(self):
        windows = (
            self.package
            / "steamworks"
            / "x86_64-windows"
            / "lsteamclient.dll"
        )
        unix = (
            self.package
            / "steamworks"
            / "x86_64-unix"
            / "lsteamclient.so"
        )
        windows.parent.mkdir(parents=True)
        unix.parent.mkdir(parents=True)
        windows.write_bytes(b"MZsteamworks-fixture")
        unix.write_bytes(b"Mach-O fixture")
        for relative in (
            "lib/wine/x86_64-windows/lsteamclient.dll",
            "lib/wine/x86_64-unix/lsteamclient.so",
        ):
            destination = self.package / "wine" / "dxmt" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(
                windows.read_bytes()
                if destination.suffix == ".dll"
                else unix.read_bytes()
            )
        manifest_path = self.package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["steamworks_bridge"] = {
            "name": "fixture lsteamclient",
            "renderers": ["dxmt"],
            "windows_dll": (
                "steamworks/x86_64-windows/lsteamclient.dll"
            ),
            "unix_library": "steamworks/x86_64-unix/lsteamclient.so",
        }
        manifest_path.write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        steam_client = self.root / "native-steam"
        steam_client.mkdir()
        (steam_client / "steamclient.dylib").write_bytes(b"fixture")
        return steam_client

    def test_steamworks_bridge_maps_environment_and_prefix_files(self):
        steam_client = self.add_steamworks_bridge()
        context = self.context()
        config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxmt",
        }
        with mock.patch.dict(
            os.environ,
            {
                "REALSTEAMONMAC_STEAM_CLIENT_INSTALL": str(
                    steam_client
                )
            },
            clear=False,
        ):
            package, manifest, wine_root, wine64, environment = (
                runtime.prepare(
                    context, self.runtime_root, config
                )
            )
        self.assertEqual(package, self.package.resolve())
        self.assertEqual(
            environment["STEAM_COMPAT_CLIENT_INSTALL_PATH"],
            str(steam_client.resolve()),
        )
        self.assertIn(
            "steamclient64=n,b", environment["WINEDLLOVERRIDES"]
        )
        self.assertIn(
            "winemenubuilder.exe=d",
            environment["WINEDLLOVERRIDES"],
        )
        steam_directory = (
            context["prefix"]
            / "drive_c"
            / "Program Files (x86)"
            / "Steam"
        )
        self.assertEqual(
            (steam_directory / "steamclient64.dll").read_bytes(),
            b"MZsteamworks-fixture",
        )
        self.assertEqual(
            (steam_directory / "lsteamclient.dll").read_bytes(),
            b"MZsteamworks-fixture",
        )
        ledger = json.loads(
            (
                context["state"] / "steamworks-bridge.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(ledger["package_id"], manifest["package_id"])
        self.assertEqual(wine64.name, "wine64")

    def test_steamworks_bridge_refuses_unmanaged_dll(self):
        steam_client = self.add_steamworks_bridge()
        context = self.context()
        destination = (
            context["prefix"]
            / "drive_c"
            / "Program Files (x86)"
            / "Steam"
            / "steamclient64.dll"
        )
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"unmanaged")
        config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxmt",
        }
        with mock.patch.dict(
            os.environ,
            {
                "REALSTEAMONMAC_STEAM_CLIENT_INSTALL": str(
                    steam_client
                )
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                runtime.RuntimeErrorWithContext,
                "unmanaged Steamworks file",
            ):
                runtime.prepare(
                    context, self.runtime_root, config
                )

    def test_dry_run_plan_does_not_create_prefix(self):
        context = self.context()
        config = runtime.normalize_config(None)
        result = runtime.plan(
            context, self.runtime_root, config, ["-fixture"]
        )
        self.assertEqual(result["appid"], 1118200)
        self.assertEqual(result["renderer"], "gptk")
        self.assertEqual(result["arguments"], ["-fixture"])
        self.assertFalse(context["prefix"].exists())

    def test_people_playground_cleans_prefix_after_game_exit(self):
        context = self.context()
        _, _, wine_root, wine64 = runtime.load_package(
            self.runtime_root, "dxvk"
        )
        environment = {"WINEPREFIX": str(context["prefix"])}
        game_result = mock.Mock(returncode=0)
        cleanup_result = mock.Mock(returncode=0)
        with mock.patch.object(
            runtime.subprocess,
            "run",
            side_effect=(game_result, cleanup_result),
        ) as run:
            result = runtime.run_game_process(
                context,
                wine_root,
                [wine64, context["executable"]],
                environment,
            )
        self.assertEqual(result, 0)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(
            run.call_args_list[1].args[0],
            [str(wine_root / "bin" / "wineserver"), "-k"],
        )
        cleanup_event = json.loads(
            (
                context["logs"] / "runtime.jsonl"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            cleanup_event["event"], "post-exit-prefix-cleanup"
        )

    def test_other_games_do_not_force_prefix_cleanup(self):
        other = self.steamapps / "common" / "Other Game" / "Other.exe"
        other.parent.mkdir(parents=True)
        other.write_bytes(b"MZfixture")
        context = runtime.resolve_context(other, "4000")
        _, _, wine_root, wine64 = runtime.load_package(
            self.runtime_root, "dxvk"
        )
        with mock.patch.object(
            runtime.subprocess,
            "run",
            return_value=mock.Mock(returncode=7),
        ) as run:
            result = runtime.run_game_process(
                context,
                wine_root,
                [wine64, context["executable"]],
                {"WINEPREFIX": str(context["prefix"])},
            )
        self.assertEqual(result, 7)
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
