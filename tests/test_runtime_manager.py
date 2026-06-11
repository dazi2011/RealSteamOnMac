import importlib.util
import hashlib
import io
import json
import os
import struct
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
                "REALSTEAMONMAC_COMPAT_TOOLS_ROOT": str(
                    self.root / "compatibilitytools.d"
                ),
                "REALSTEAMONMAC_DEPENDENCY_CATALOG": str(
                    self.root / "dependencies.json"
                ),
                "REALSTEAMONMAC_DEPENDENCY_CACHE": str(
                    self.root / "dependency-cache"
                ),
                "REALSTEAMONMAC_APPINFO_PATH": str(
                    self.root / "appinfo.vdf"
                ),
            },
        )
        self.environment.start()
        self.steamapps = self.root / "steamapps"
        self.game = self.steamapps / "common" / "Fixture Game"
        self.game.mkdir(parents=True)
        self.executable = self.game / "Fixture.exe"
        self.executable.write_bytes(b"MZfixture")
        self.write_appinfo(
            {
                "0": {
                    "executable": "Fixture.exe",
                    "type": "default",
                    "config": {"oslist": "windows"},
                }
            }
        )
        (self.steamapps / "appmanifest_1118200.acf").write_text(
            '"AppState"\n{\n'
            '\t"appid"\t\t"1118200"\n'
            '\t"StateFlags"\t\t"4"\n'
            '\t"installdir"\t\t"Fixture Game"\n'
            '\t"SizeOnDisk"\t\t"9"\n'
            '\t"UpdateResult"\t\t"0"\n'
            '\t"InstalledDepots"\n'
            "\t{\n"
            '\t\t"1118201"\n'
            "\t\t{\n"
            '\t\t\t"manifest"\t\t"12345"\n'
            '\t\t\t"size"\t\t"9"\n'
            "\t\t}\n"
            "\t}\n"
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
        dxmt_windows = (
            package
            / "wine"
            / "dxmt"
            / "lib"
            / "wine"
            / "x86_64-windows"
        )
        dxmt_windows.mkdir(parents=True, exist_ok=True)
        (dxmt_windows / "nvapi64.dll").write_bytes(b"MZdxmt-nvapi")
        (dxmt_windows / "nvngx.dll").write_bytes(b"MZdxmt-nvngx")
        gptk_windows = (
            package
            / "wine"
            / "gptk"
            / "lib"
            / "wine"
            / "x86_64-windows"
        )
        gptk_windows.mkdir(parents=True, exist_ok=True)
        (gptk_windows / "nvapi64.dll").write_bytes(b"MZgptk-nvapi")
        (gptk_windows / "nvngx-on-metalfx.dll").write_bytes(
            b"MZgptk-nvngx"
        )
        (gptk_windows / "nvngx.dll").write_bytes(
            b"MZgptk-legacy-nvngx"
        )
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
        self.compat_tools = self.root / "compatibilitytools.d"
        self.write_compat_tool(
            "fixture-dxmt",
            renderer="dxmt",
            runtime_package="fixture",
            metalfx=True,
        )

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def context(self):
        return runtime.resolve_context(self.executable, "1118200")

    def write_appinfo(self, launch):
        value = {
            "appinfo": {
                "config": {
                    "installdir": "Fixture Game",
                    "launch": launch,
                }
            }
        }
        keys = []
        seen = set()

        def collect(node):
            for key, child in node.items():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
                if isinstance(child, dict):
                    collect(child)

        collect(value)
        indices = {key: index for index, key in enumerate(keys)}

        def encode(node):
            payload = bytearray()
            for key, child in node.items():
                if isinstance(child, dict):
                    payload.append(0)
                    payload.extend(struct.pack("<i", indices[key]))
                    payload.extend(encode(child))
                elif isinstance(child, str):
                    payload.append(1)
                    payload.extend(struct.pack("<i", indices[key]))
                    payload.extend(child.encode("utf-8") + b"\x00")
                elif isinstance(child, int):
                    payload.append(2)
                    payload.extend(struct.pack("<ii", indices[key], child))
                else:
                    raise TypeError(f"unsupported appinfo fixture: {child!r}")
            payload.append(8)
            return payload

        binary_vdf = encode(value)
        metadata = (
            struct.pack("<IIQ", 2, 1_700_000_000, 0)
            + (b"\x11" * 20)
            + struct.pack("<I", 123)
            + hashlib.sha1(binary_vdf).digest()
        )
        entry = (
            struct.pack("<II", 1118200, len(metadata) + len(binary_vdf))
            + metadata
            + binary_vdf
            + struct.pack("<I", 0)
        )
        table_offset = 16 + len(entry)
        table = bytearray(struct.pack("<I", len(keys)))
        for key in keys:
            table.extend(key.encode("utf-8") + b"\x00")
        (self.root / "appinfo.vdf").write_bytes(
            struct.pack("<IIq", 0x07564429, 1, table_offset)
            + entry
            + table
        )

    def write_compat_tool(
        self,
        tool,
        *,
        renderer,
        runtime_package,
        metalfx=False,
    ):
        directory = self.compat_tools / tool
        directory.mkdir(parents=True, exist_ok=True)
        run = directory / "run"
        run.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        run.chmod(0o755)
        (directory / "toolmanifest.vdf").write_text(
            '"manifest"\n{\n'
            '  "version" "2"\n'
            '  "commandline" "/run %verb%"\n'
            "}\n",
            encoding="utf-8",
        )
        display_name = f"{renderer.upper()} Fixture"
        (directory / "compatibilitytool.vdf").write_text(
            '"compatibilitytools"\n{\n'
            '  "compat_tools"\n  {\n'
            f'    "{tool}"\n    {{\n'
            '      "install_path" "."\n'
            f'      "display_name" "{display_name}"\n'
            '      "from_oslist" "windows"\n'
            '      "to_oslist" "macos"\n'
            "    }\n  }\n}\n",
            encoding="utf-8",
        )
        (directory / "realsteamonmac.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "tool": tool,
                    "display_name": display_name,
                    "renderer": renderer,
                    "version": "fixture",
                    "runtime_package": runtime_package,
                    "capabilities": {
                        "msync": True,
                        "retina": True,
                        "metal_hud": True,
                        "metalfx": metalfx,
                        "dxr": False,
                        "avx": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        return directory

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
        self.assertEqual(context["working_directory"], self.game.resolve())
        self.assertEqual(context["launch_entry_id"], "0")
        self.assertEqual(context["launch_arguments"], "")
        self.assertEqual(
            context["compat_data"],
            self.steamapps.resolve() / "compatdata" / "1118200",
        )

    def test_rejects_staged_only_installation_context(self):
        self.executable.unlink()
        (self.steamapps / "appmanifest_1118200.acf").write_text(
            '"AppState"\n{\n'
            '\t"appid"\t\t"1118200"\n'
            '\t"StateFlags"\t\t"1026"\n'
            '\t"installdir"\t\t"Fixture Game"\n'
            '\t"SizeOnDisk"\t\t"0"\n'
            '\t"UpdateResult"\t\t"6"\n'
            '\t"InstalledDepots"\n'
            "\t{\n"
            "\t}\n"
            '\t"StagedDepots"\n'
            "\t{\n"
            '\t\t"1118201"\n'
            "\t\t{\n"
            '\t\t\t"manifest"\t\t"12345"\n'
            '\t\t\t"size"\t\t"149800000000"\n'
            "\t\t}\n"
            "\t}\n"
            "}\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext,
            "download-incomplete.*install or repair",
        ):
            runtime.resolve_app_context("1118200")

    def test_new_prefix_defaults_to_windows_10(self):
        context = self.context()
        wine64 = (
            self.package / "wine" / "dxmt" / "bin" / "wine64"
        )

        def record_setup(_context, command, _environment, _description):
            if command[1:3] == ["wineboot", "--init"]:
                (context["prefix"] / "dosdevices").mkdir(
                    parents=True,
                    exist_ok=True,
                )

        with mock.patch.object(
            runtime,
            "run_logged",
            side_effect=record_setup,
        ) as run:
            runtime.initialize_prefix(
                context,
                wine64,
                {"WINEPREFIX": str(context["prefix"])},
            )

        self.assertEqual(
            [call.args[1] for call in run.call_args_list],
            [
                [wine64, "wineboot", "--init"],
                [wine64, "winecfg", "-v", "win10"],
            ],
        )

    def test_resolved_app_context_keeps_the_full_install_root(self):
        nested = self.game / "bin" / "Fixture.exe"
        nested.parent.mkdir()
        self.executable.unlink()
        nested.write_bytes(b"MZnested-fixture")
        self.write_appinfo(
            {
                "0": {
                    "executable": "bin/Fixture.exe",
                    "workingdir": "bin",
                    "type": "default",
                    "config": {"oslist": "windows"},
                }
            }
        )

        context = runtime.resolve_app_context("1118200")

        self.assertEqual(context["executable"], nested.resolve())
        self.assertEqual(context["install_path"], self.game.resolve())
        self.assertEqual(
            context["working_directory"], nested.parent.resolve()
        )
        sibling = self.game / "Redist.exe"
        sibling.write_bytes(b"MZredist")
        self.assertEqual(
            runtime.resolve_command_target(context, "Redist.exe"),
            sibling.resolve(),
        )

    def test_stale_steam_target_falls_back_to_verified_default(self):
        self.write_appinfo(
            {
                "0": {
                    "executable": "Missing-Test.exe",
                    "arguments": "-development",
                    "type": "option1",
                    "config": {"oslist": "windows"},
                },
                "1": {
                    "executable": "Fixture.exe",
                    "arguments": "-release",
                    "type": "default",
                    "config": {"oslist": "windows"},
                },
            }
        )

        context = runtime.resolve_app_context(
            "1118200",
            requested_target=self.game / "Missing-Test.exe",
        )

        self.assertEqual(context["executable"], self.executable.resolve())
        self.assertEqual(context["launch_entry_id"], "1")
        self.assertEqual(context["launch_arguments"], "-release")

    def test_app_context_does_not_guess_an_unrelated_executable(self):
        self.write_appinfo(
            {
                "0": {
                    "executable": "Missing.exe",
                    "type": "default",
                    "config": {"oslist": "windows"},
                }
            }
        )

        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext,
            "no valid Windows launch entry",
        ):
            runtime.resolve_app_context("1118200")

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
        self.assertEqual(
            runtime.parse_action_payload(
                "action=container&operation=open-c-drive"
            ),
            {
                "action": "container",
                "operation": "open-c-drive",
            },
        )
        self.assertEqual(
            runtime.parse_action_payload("action=choose-file"),
            {"action": "choose-file"},
        )
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext, "duplicate"
        ):
            runtime.parse_action_payload(
                "action=install-dependency&dependency=one&dependency=two"
            )

    def test_container_actions_use_fixed_argv_and_recoverable_delete(self):
        context = self.context()
        wine64 = (
            self.package / "wine" / "dxmt" / "bin" / "wine64"
        ).resolve()
        wine_root = wine64.parent.parent
        context["prefix"].mkdir(parents=True)
        with mock.patch.object(
            runtime,
            "prepare",
            return_value=(
                self.package,
                {"package_id": "fixture"},
                wine_root,
                wine64,
                {"WINEPREFIX": str(context["prefix"])},
            ),
        ), mock.patch.object(
            runtime,
            "run_job_process",
            return_value=mock.Mock(returncode=0),
        ) as run:
            exit_code, result = runtime.execute_container_action(
                context,
                self.runtime_root,
                {"operation": "task-manager"},
                self.root / "container.log",
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            run.call_args.args[1],
            [wine64, "taskmgr"],
        )
        self.assertEqual(result["operation"], "task-manager")

        with mock.patch.object(
            runtime,
            "prepare",
            return_value=(
                self.package,
                {"package_id": "fixture"},
                wine_root,
                wine64,
                {"WINEPREFIX": str(context["prefix"])},
            ),
        ), mock.patch.object(
            runtime,
            "run_job_process",
            return_value=mock.Mock(returncode=0),
        ):
            exit_code, result = runtime.execute_container_action(
                context,
                self.runtime_root,
                {"operation": "delete-container"},
                self.root / "delete.log",
            )

        self.assertEqual(exit_code, 0)
        self.assertFalse(context["prefix"].exists())
        self.assertTrue(Path(result["recovery_path"]).is_dir())

    def test_open_c_drive_scrubs_wine_environment(self):
        context = self.context()
        wine64 = (
            self.package / "wine" / "dxmt" / "bin" / "wine64"
        ).resolve()
        wine_root = wine64.parent.parent
        context["prefix"].mkdir(parents=True)
        (context["prefix"] / "drive_c").mkdir()
        prepared_environment = {
            "HOME": str(self.root),
            "PATH": "/usr/bin:/bin",
            "WINEPREFIX": str(context["prefix"]),
            "WINEMSYNC": "1",
            "STEAM_COMPAT_APP_ID": "1118200",
            "DYLD_INSERT_LIBRARIES": "/tmp/x86_64-shim.dylib",
            "REALSTEAMONMAC_RENDERER": "dxmt",
        }

        with mock.patch.object(
            runtime,
            "prepare",
            return_value=(
                self.package,
                {"package_id": "fixture"},
                wine_root,
                wine64,
                prepared_environment,
            ),
        ), mock.patch.object(
            runtime,
            "run_job_process",
            return_value=mock.Mock(returncode=0),
        ) as run:
            exit_code, _ = runtime.execute_container_action(
                context,
                self.runtime_root,
                {"operation": "open-c-drive"},
                self.root / "open-c-drive.log",
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            run.call_args.args[1],
            ["/usr/bin/open", context["prefix"] / "drive_c"],
        )
        native_environment = run.call_args.args[2]
        self.assertEqual(native_environment["HOME"], str(self.root))
        self.assertEqual(native_environment["PATH"], "/usr/bin:/bin")
        for name in (
            "WINEPREFIX",
            "WINEMSYNC",
            "STEAM_COMPAT_APP_ID",
            "DYLD_INSERT_LIBRARIES",
            "REALSTEAMONMAC_RENDERER",
        ):
            with self.subTest(name=name):
                self.assertNotIn(name, native_environment)

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

    def test_container_nonzero_exit_fails_job(self):
        arguments = SimpleNamespace(
            appid="1118200",
            job_id="abcdef0123456789abcdef0123456789",
            payload="action=container&operation=open-c-drive",
            runtime_root=str(self.runtime_root),
        )
        context = self.context()
        with mock.patch.object(
            runtime,
            "resolve_app_context",
            return_value=context,
        ), mock.patch.object(
            runtime,
            "execute_container_action",
            return_value=(
                -6,
                {
                    "operation": "open-c-drive",
                    "renderer": "dxmt",
                },
            ),
        ):
            self.assertEqual(runtime.action_job(arguments), 1)

        status_path = runtime.job_paths(
            1118200, arguments.job_id
        )["status"]
        status = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["exit_code"], 1)
        self.assertIn("container operation exited with -6", status["message"])

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

    def test_metalfx_requires_a_capability_aware_tool_selection(self):
        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext, "capability-aware"
        ):
            runtime.normalize_config(
                {
                    **runtime.DEFAULT_CONFIG,
                    "renderer": "dxmt",
                    "metalfx": True,
                }
            )

        config = runtime.normalize_config(
            {
                **runtime.DEFAULT_CONFIG,
                "compat_tool": "fixture-dxmt",
                "renderer": "dxmt",
                "metalfx": True,
            }
        )
        package, manifest, _, _, tool = runtime.load_selected_package(
            self.runtime_root, config
        )
        self.assertEqual(package, self.package.resolve())
        self.assertEqual(manifest["package_id"], "fixture")
        self.assertEqual(tool["strToolName"], "fixture-dxmt")

    def test_environment_maps_controls(self):
        context = self.context()
        package, _, wine_root, _ = runtime.load_package(
            self.runtime_root, "gptk"
        )
        self.assertTrue(package.is_dir())
        config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "gptk",
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

    def test_dxmt_metalfx_uses_nvext_and_dxmt_vendor_dlls(self):
        context = self.context()
        _, _, wine_root, _ = runtime.load_package(
            self.runtime_root, "dxmt"
        )
        config = {
            **runtime.DEFAULT_CONFIG,
            "compat_tool": "fixture-dxmt",
            "renderer": "dxmt",
            "metalfx": True,
        }

        environment = runtime.build_environment(
            context, config, wine_root
        )
        runtime.install_metalfx_files(
            context,
            self.package,
            wine_root,
            "dxmt",
            True,
        )

        self.assertEqual(environment["DXMT_ENABLE_NVEXT"], "1")
        self.assertNotIn("D3DM_ENABLE_METALFX", environment)
        system32 = (
            context["prefix"]
            / "drive_c"
            / "windows"
            / "system32"
        )
        self.assertEqual(
            (system32 / "nvapi64.dll").read_bytes(),
            b"MZdxmt-nvapi",
        )
        self.assertEqual(
            (system32 / "nvngx.dll").read_bytes(),
            b"MZdxmt-nvngx",
        )

    def test_metalfx_files_switch_between_managed_tools_and_cleanly_disable(
        self,
    ):
        context = self.context()
        _, _, gptk_root, _ = runtime.load_package(
            self.runtime_root, "gptk"
        )
        _, _, dxmt_root, _ = runtime.load_package(
            self.runtime_root, "dxmt"
        )
        system32 = (
            context["prefix"]
            / "drive_c"
            / "windows"
            / "system32"
        )

        runtime.install_metalfx_files(
            context,
            self.package,
            gptk_root,
            "gptk",
            True,
        )
        self.assertEqual(
            (system32 / "nvngx.dll").read_bytes(),
            b"MZgptk-nvngx",
        )

        runtime.install_metalfx_files(
            context,
            self.package,
            dxmt_root,
            "dxmt",
            True,
        )
        self.assertEqual(
            (system32 / "nvngx.dll").read_bytes(),
            b"MZdxmt-nvngx",
        )

        runtime.install_metalfx_files(
            context,
            self.package,
            dxmt_root,
            "dxmt",
            False,
        )
        self.assertFalse((system32 / "nvngx.dll").exists())
        self.assertFalse((system32 / "nvapi64.dll").exists())

    def test_metalfx_adopts_known_legacy_files_without_a_ledger(self):
        context = self.context()
        _, _, dxmt_root, _ = runtime.load_package(
            self.runtime_root, "dxmt"
        )
        system32 = (
            context["prefix"]
            / "drive_c"
            / "windows"
            / "system32"
        )
        system32.mkdir(parents=True)
        (system32 / "nvngx.dll").write_bytes(
            b"MZgptk-legacy-nvngx"
        )
        (system32 / "nvapi64.dll").write_bytes(b"MZgptk-nvapi")

        runtime.install_metalfx_files(
            context,
            self.package,
            dxmt_root,
            "dxmt",
            True,
        )

        self.assertEqual(
            (system32 / "nvngx.dll").read_bytes(),
            b"MZdxmt-nvngx",
        )
        self.assertEqual(
            (system32 / "nvapi64.dll").read_bytes(),
            b"MZdxmt-nvapi",
        )
        ledger = json.loads(
            (context["state"] / "metalfx-files.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(ledger["renderer"], "dxmt")

    def test_metalfx_removes_known_legacy_files_without_a_ledger(self):
        context = self.context()
        _, _, gptk_root, _ = runtime.load_package(
            self.runtime_root, "gptk"
        )
        system32 = (
            context["prefix"]
            / "drive_c"
            / "windows"
            / "system32"
        )
        system32.mkdir(parents=True)
        (system32 / "nvngx.dll").write_bytes(
            b"MZgptk-legacy-nvngx"
        )
        (system32 / "nvapi64.dll").write_bytes(b"MZgptk-nvapi")

        runtime.install_metalfx_files(
            context,
            self.package,
            gptk_root,
            "gptk",
            False,
        )

        self.assertFalse((system32 / "nvngx.dll").exists())
        self.assertFalse((system32 / "nvapi64.dll").exists())

    def test_metalfx_still_refuses_unknown_files_without_a_ledger(self):
        context = self.context()
        _, _, dxmt_root, _ = runtime.load_package(
            self.runtime_root, "dxmt"
        )
        system32 = (
            context["prefix"]
            / "drive_c"
            / "windows"
            / "system32"
        )
        system32.mkdir(parents=True)
        destination = system32 / "nvngx.dll"
        destination.write_bytes(b"MZunmanaged")

        with self.assertRaisesRegex(
            runtime.RuntimeErrorWithContext,
            "refusing to replace an unmanaged MetalFX file",
        ):
            runtime.install_metalfx_files(
                context,
                self.package,
                dxmt_root,
                "dxmt",
                True,
            )

        self.assertEqual(destination.read_bytes(), b"MZunmanaged")

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

    def test_steamworks_bridge_is_removed_for_gptk_and_restored(self):
        steam_client = self.add_steamworks_bridge()
        context = self.context()
        dxmt_config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxmt",
        }
        gptk_config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "gptk",
        }
        steam_directory = (
            context["prefix"]
            / "drive_c"
            / "Program Files (x86)"
            / "Steam"
        )
        marker = context["state"] / "steamworks-bridge.json"
        with mock.patch.dict(
            os.environ,
            {
                "REALSTEAMONMAC_STEAM_CLIENT_INSTALL": str(
                    steam_client
                )
            },
            clear=False,
        ), mock.patch.object(runtime, "run_logged"):
            runtime.prepare(context, self.runtime_root, dxmt_config)
            runtime.prepare(context, self.runtime_root, gptk_config)
            self.assertFalse(
                (steam_directory / "lsteamclient.dll").exists()
            )
            self.assertFalse(
                (steam_directory / "steamclient64.dll").exists()
            )
            self.assertFalse(
                json.loads(marker.read_text(encoding="utf-8"))[
                    "active"
                ]
            )

            runtime.prepare(context, self.runtime_root, dxmt_config)

        self.assertEqual(
            (steam_directory / "lsteamclient.dll").read_bytes(),
            b"MZsteamworks-fixture",
        )
        self.assertEqual(
            (steam_directory / "steamclient64.dll").read_bytes(),
            b"MZsteamworks-fixture",
        )
        self.assertTrue(
            json.loads(marker.read_text(encoding="utf-8"))["active"]
        )

    def test_gptk_refuses_to_remove_a_modified_managed_bridge(self):
        steam_client = self.add_steamworks_bridge()
        context = self.context()
        dxmt_config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "dxmt",
        }
        gptk_config = {
            **runtime.DEFAULT_CONFIG,
            "renderer": "gptk",
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
            runtime.prepare(context, self.runtime_root, dxmt_config)
            destination = (
                context["prefix"]
                / "drive_c"
                / "Program Files (x86)"
                / "Steam"
                / "steamclient64.dll"
            )
            destination.write_bytes(b"user-modified")
            with self.assertRaisesRegex(
                runtime.RuntimeErrorWithContext,
                "modified managed Steamworks file",
            ):
                runtime.prepare(
                    context, self.runtime_root, gptk_config
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

    def test_launch_dry_run_uses_verified_descriptor_arguments(self):
        working_directory = self.game / "bin"
        working_directory.mkdir()
        self.write_appinfo(
            {
                "0": {
                    "executable": "Fixture.exe",
                    "workingdir": "bin",
                    "arguments": '-release "two words"',
                    "type": "default",
                    "config": {"oslist": "windows"},
                }
            }
        )
        arguments = SimpleNamespace(
            appid="1118200",
            compat_data=None,
            runtime_root=str(self.runtime_root),
            executable=str(self.game / "Missing-Test.exe"),
            dry_run=True,
            arguments=[],
        )
        output = io.StringIO()

        with mock.patch("sys.stdout", output):
            self.assertEqual(runtime.launch(arguments), 0)

        value = json.loads(output.getvalue())
        self.assertEqual(value["executable"], str(self.executable.resolve()))
        self.assertEqual(
            value["working_directory"],
            str(working_directory.resolve()),
        )
        self.assertEqual(value["arguments"], ["-release", "two words"])

    def test_people_playground_cleans_prefix_after_game_exit(self):
        context = self.context()
        working_directory = self.game / "bin"
        working_directory.mkdir()
        context["working_directory"] = working_directory
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
            run.call_args_list[0].kwargs["cwd"],
            str(working_directory),
        )
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
