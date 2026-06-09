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


if __name__ == "__main__":
    unittest.main()
