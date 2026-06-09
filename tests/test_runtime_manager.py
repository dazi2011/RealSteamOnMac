import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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
        self.environment = mock.patch.dict(
            os.environ,
            {
                "REALSTEAMONMAC_APP_CONFIG_ROOT": str(
                    self.root / "app-configs"
                ),
                "REALSTEAMONMAC_STEAM_ROOT": str(self.root),
                "REALSTEAMONMAC_JOB_ROOT": str(self.root / "jobs"),
                "REALSTEAMONMAC_DEPENDENCY_CATALOG": str(
                    self.root / "dependencies.json"
                ),
                "REALSTEAMONMAC_DEPENDENCY_CACHE": str(
                    self.root / "dependency-cache"
                ),
            },
        )
        self.environment.start()
        self.steamapps = self.root / "steamapps"
        self.game = self.steamapps / "common" / "Fixture Game"
        self.game.mkdir(parents=True)
        self.executable = self.game / "Fixture.exe"
        self.executable.write_bytes(b"MZfixture")
        (self.steamapps / "appmanifest_1118200.acf").write_text(
            '"AppState"\n{\n'
            '\t"appid"\t\t"1118200"\n'
            '\t"installdir"\t\t"Fixture Game"\n'
            "}\n",
            encoding="utf-8",
        )
        self.dependency_bytes = b"MZdependency-fixture"
        self.dependency_digest = runtime.hashlib.sha256(
            self.dependency_bytes
        ).hexdigest()
        (self.root / "dependencies.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "dependencies": [
                        {
                            "id": "fixture-redist",
                            "name": "Fixture Redistributable",
                            "description": "Fixture dependency",
                            "publisher": "Microsoft",
                            "filename": "fixture.exe",
                            "url": "https://aka.ms/fixture.exe",
                            "sha256": self.dependency_digest,
                            "size": len(self.dependency_bytes),
                            "arguments": ["/quiet"],
                            "success_codes": [0],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.runtime_root = self.root / "runtimes"
        package = self.runtime_root / "packages" / "fixture"
        for renderer in runtime.RENDERERS:
            wine64 = package / "wine" / renderer / "bin" / "wine64"
            wine64.parent.mkdir(parents=True)
            wine64.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            wine64.chmod(0o755)
        dxmt_driver = (
            package
            / "wine"
            / "dxmt"
            / "lib"
            / "wine"
            / "x86_64-unix"
            / "winemac.so"
        )
        dxmt_shim = (
            package
            / "wine"
            / "dxmt"
            / "lib"
            / "librealsteamonmac_dxmt_macdrv_shim.dylib"
        )
        dxmt_driver.parent.mkdir(parents=True, exist_ok=True)
        dxmt_shim.parent.mkdir(parents=True, exist_ok=True)
        dxmt_driver.write_bytes(b"Mach-O winemac fixture")
        dxmt_shim.write_bytes(b"Mach-O shim fixture")
        (package / "manifest.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "package_id": "fixture",
                    "renderers": {},
                    "dxmt_winemac_compat": {
                        "name": "fixture DXMT macdrv compatibility",
                        "winemac_driver": (
                            "wine/dxmt/lib/wine/"
                            "x86_64-unix/winemac.so"
                        ),
                        "visibility_shim": (
                            "wine/dxmt/lib/"
                            "librealsteamonmac_dxmt_macdrv_shim.dylib"
                        ),
                    },
                }
            ),
            encoding="utf-8",
        )
        self.runtime_root.mkdir(exist_ok=True)
        (self.runtime_root / "current").symlink_to("packages/fixture")
        self.package = package

    def tearDown(self):
        self.environment.stop()
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

    def test_resolves_installed_app_from_steam_manifest(self):
        context = runtime.resolve_app_context("1118200")
        self.assertEqual(context["executable"], self.executable.resolve())
        self.assertEqual(context["install_path"], self.game.resolve())
        self.assertEqual(
            context["compat_data"],
            self.steamapps.resolve() / "compatdata" / "1118200",
        )

    def test_resolved_app_context_keeps_the_full_install_root(self):
        nested = self.game / "bin" / "Fixture.exe"
        nested.parent.mkdir()
        self.executable.unlink()
        nested.write_bytes(b"MZnested-fixture")

        context = runtime.resolve_app_context("1118200")

        self.assertEqual(context["executable"], nested.resolve())
        self.assertEqual(context["install_path"], self.game.resolve())
        sibling = self.game / "Redist.exe"
        sibling.write_bytes(b"MZredist")
        self.assertEqual(
            runtime.resolve_command_target(context, "Redist.exe"),
            sibling.resolve(),
        )

    def test_action_payload_is_fixed_and_rejects_duplicates(self):
        self.assertEqual(
            runtime.parse_action_payload(
                "action=run-command&target=Fixture.exe&"
                "arguments=-windowed&environment=DXVK_HUD%3D1"
            ),
            {
                "action": "run-command",
                "target": "Fixture.exe",
                "arguments": "-windowed",
                "environment": "DXVK_HUD=1",
            },
        )
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext, "duplicate"
        ):
            runtime.parse_action_payload(
                "action=install-dependency&dependency=one&dependency=two"
            )

    def test_run_command_target_cannot_escape_game_or_prefix(self):
        context = self.context()
        self.assertEqual(
            runtime.resolve_command_target(context, "Fixture.exe"),
            self.executable.resolve(),
        )
        outside = self.root / "outside.exe"
        outside.write_bytes(b"MZoutside")
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext, "must stay inside"
        ):
            runtime.resolve_command_target(context, str(outside))

    def test_run_command_environment_rejects_reserved_variables(self):
        self.assertEqual(
            runtime.parse_command_environment(
                "DXVK_HUD=fps\nCUSTOM_FLAG=value"
            ),
            {"DXVK_HUD": "fps", "CUSTOM_FLAG": "value"},
        )
        for value in (
            "WINEPREFIX=/tmp/escape",
            "DYLD_INSERT_LIBRARIES=/tmp/payload.dylib",
            "STEAM_COMPAT_APP_ID=42",
            "REALSTEAMONMAC_RENDERER=gptk",
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    runtime.RuntimeErrorWithContext,
                    "reserved variable",
                ):
                    runtime.parse_command_environment(value)

    def test_dependency_download_requires_manifest_hash_and_size(self):
        dependency = runtime.load_dependency_catalog()[
            "fixture-redist"
        ]
        with mock.patch.object(
            runtime.urllib.request,
            "urlopen",
            return_value=io.BytesIO(self.dependency_bytes),
        ):
            downloaded = runtime.download_dependency(dependency)
        self.assertEqual(
            downloaded.read_bytes(), self.dependency_bytes
        )
        self.assertEqual(downloaded.stat().st_mode & 0o777, 0o600)

        downloaded.unlink()
        with mock.patch.object(
            runtime.urllib.request,
            "urlopen",
            return_value=io.BytesIO(b"MZwrong"),
        ):
            with self.assertRaisesRegex(
                runtime.RuntimeErrorWithContext,
                "did not match",
            ):
                runtime.download_dependency(dependency)

    def test_dependency_download_rejects_an_untrusted_redirect(self):
        dependency = runtime.load_dependency_catalog()[
            "fixture-redist"
        ]
        response = io.BytesIO(self.dependency_bytes)
        response.geturl = lambda: "https://example.invalid/fixture.exe"
        with mock.patch.object(
            runtime.urllib.request,
            "urlopen",
            return_value=response,
        ):
            with self.assertRaisesRegex(
                runtime.RuntimeErrorWithContext,
                "untrusted host",
            ):
                runtime.download_dependency(dependency)

    def test_action_job_writes_private_completed_status(self):
        arguments = SimpleNamespace(
            appid="1118200",
            job_id="0123456789abcdef0123456789abcdef",
            payload=(
                "action=run-command&target=Fixture.exe&"
                "arguments=&environment="
            ),
            runtime_root=str(self.runtime_root),
        )
        with mock.patch.object(
            runtime,
            "execute_run_command_action",
            return_value=(0, {"target": str(self.executable)}),
        ):
            self.assertEqual(runtime.action_job(arguments), 0)
        status_path = runtime.job_paths(
            1118200, arguments.job_id
        )["status"]
        status = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual(status["state"], "completed")
        self.assertEqual(status["action"], "run-command")
        self.assertEqual(status_path.stat().st_mode & 0o777, 0o600)
        action_lock = (
            self.steamapps
            / "compatdata"
            / "1118200"
            / "realsteamonmac"
            / "action.lock"
        )
        self.assertEqual(action_lock.stat().st_mode & 0o777, 0o600)

    def test_run_command_executes_an_argv_vector_without_a_shell(self):
        context = self.context()
        wine64 = (
            self.package / "wine" / "dxmt" / "bin" / "wine64"
        ).resolve()
        with mock.patch.object(
            runtime,
            "prepare",
            return_value=(
                self.package,
                {"package_id": "fixture"},
                wine64.parent.parent,
                wine64,
                {"WINEPREFIX": str(context["prefix"])},
            ),
        ), mock.patch.object(
            runtime,
            "run_job_process",
            return_value=mock.Mock(returncode=0),
        ) as run:
            exit_code, result = runtime.execute_run_command_action(
                context,
                self.runtime_root,
                {
                    "target": "Fixture.exe",
                    "arguments": "--flag;touch 'two words'",
                    "environment": "CUSTOM_FLAG=value",
                },
                self.root / "run-command.log",
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["renderer"], "dxmt")
        self.assertEqual(
            run.call_args.args[1],
            [
                wine64,
                self.executable.resolve(),
                "--flag;touch",
                "two words",
            ],
        )
        self.assertEqual(
            run.call_args.args[2]["CUSTOM_FLAG"],
            "value",
        )

    def test_dependency_action_writes_a_private_prefix_receipt(self):
        context = self.context()
        wine64 = (
            self.package / "wine" / "dxmt" / "bin" / "wine64"
        ).resolve()
        installer = self.root / "vc_redist.x64.exe"
        installer.write_bytes(self.dependency_bytes)
        with mock.patch.object(
            runtime,
            "prepare",
            return_value=(
                self.package,
                {"package_id": "fixture"},
                wine64.parent.parent,
                wine64,
                {"WINEPREFIX": str(context["prefix"])},
            ),
        ), mock.patch.object(
            runtime,
            "download_dependency",
            return_value=installer,
        ), mock.patch.object(
            runtime,
            "run_job_process",
            return_value=mock.Mock(returncode=0),
        ):
            exit_code, result = runtime.execute_dependency_action(
                context,
                self.runtime_root,
                {"dependency": "fixture-redist"},
                self.root / "dependency.log",
            )

        self.assertEqual(exit_code, 0)
        receipt = Path(result["receipt"])
        value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(value["dependency"], "fixture-redist")
        self.assertEqual(value["package_id"], "fixture")
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)

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
        self.assertEqual(
            context["global_config"].stat().st_mode & 0o777,
            0o600,
        )
        self.assertEqual(
            json.loads(context["global_config"].read_text(encoding="utf-8")),
            saved,
        )
        self.assertEqual(runtime.load_config(context), saved)

    def test_global_config_precedes_legacy_prefix_config(self):
        context = self.context()
        runtime.atomic_write_json(
            context["config"],
            {
                **runtime.DEFAULT_CONFIG,
                "renderer": "wined3d",
            },
        )
        runtime.atomic_write_json(
            context["global_config"],
            {
                **runtime.DEFAULT_CONFIG,
                "renderer": "dxvk",
            },
        )
        self.assertEqual(runtime.load_config(context)["renderer"], "dxvk")

    def test_legacy_prefix_config_remains_a_migration_fallback(self):
        context = self.context()
        runtime.atomic_write_json(
            context["config"],
            {
                **runtime.DEFAULT_CONFIG,
                "renderer": "wined3d",
            },
        )
        self.assertEqual(
            runtime.load_config(context)["renderer"],
            "wined3d",
        )

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
                "DYLD_INSERT_LIBRARIES": "stale",
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
        self.assertNotIn("DYLD_INSERT_LIBRARIES", environment)

    def test_dxmt_injects_only_managed_visibility_shim(self):
        context = self.context()
        config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxmt",
        }
        with mock.patch.dict(
            os.environ,
            {"DYLD_INSERT_LIBRARIES": "/tmp/unmanaged.dylib"},
            clear=False,
        ):
            result = runtime.plan(
                context, self.runtime_root, config, []
            )
        expected = (
            self.package.resolve()
            / "wine"
            / "dxmt"
            / "lib"
            / "librealsteamonmac_dxmt_macdrv_shim.dylib"
        )
        self.assertEqual(
            result["environment"]["DYLD_INSERT_LIBRARIES"],
            str(expected),
        )
        self.assertEqual(
            result["dxmt_winemac_compat"],
            "fixture DXMT macdrv compatibility",
        )

    def test_dxmt_refuses_missing_visibility_shim(self):
        context = self.context()
        shim = (
            self.package
            / "wine"
            / "dxmt"
            / "lib"
            / "librealsteamonmac_dxmt_macdrv_shim.dylib"
        )
        shim.unlink()
        config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxmt",
        }
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext,
            "compatibility payload is missing",
        ):
            runtime.plan(context, self.runtime_root, config, [])

    def test_dxmt_refuses_visibility_shim_outside_renderer_root(self):
        context = self.context()
        outside = self.package / "outside-shim.dylib"
        outside.write_bytes(b"Mach-O outside fixture")
        manifest_path = self.package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["dxmt_winemac_compat"][
            "visibility_shim"
        ] = "outside-shim.dylib"
        manifest_path.write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxmt",
        }
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext,
            "visibility shim path is invalid",
        ):
            runtime.plan(context, self.runtime_root, config, [])

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
        ), mock.patch.object(runtime, "run_logged"):
            package, manifest, wine_root, wine64, environment = runtime.prepare(
                context, self.runtime_root, config
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
        ), mock.patch.object(runtime, "run_logged"):
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
        self.assertEqual(result["renderer"], "dxmt")
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
