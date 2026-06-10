import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "compat_tool_catalog.py"
SPEC = importlib.util.spec_from_file_location(
    "compat_tool_catalog", MODULE_PATH
)
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)

CAPABILITIES = {
    "msync": True,
    "retina": True,
    "metal_hud": True,
    "metalfx": False,
    "dxr": False,
    "avx": True,
}


class CompatToolCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "compatibilitytools.d"
        self.root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def write_tool(
        self,
        directory_name,
        *,
        tool,
        display_name,
        renderer="dxmt",
        version="0.80",
        runtime_package=None,
        capabilities=None,
        metadata_updates=None,
        vdf_tool=None,
        vdf_display_name=None,
        from_oslist="windows",
        to_oslist="macos",
        executable=True,
    ):
        directory = self.root / directory_name
        directory.mkdir()
        run = directory / "run"
        run.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        run.chmod(0o755 if executable else 0o644)
        (directory / "toolmanifest.vdf").write_text(
            '"manifest"\n'
            "{\n"
            '    "version" "2"\n'
            '    "commandline" "/run %verb%"\n'
            "}\n",
            encoding="utf-8",
        )
        (directory / "compatibilitytool.vdf").write_text(
            '"compatibilitytools"\n'
            "{\n"
            '    "compat_tools"\n'
            "    {\n"
            f'        "{vdf_tool or tool}"\n'
            "        {\n"
            '            "install_path" "."\n'
            f'            "display_name" '
            f'"{vdf_display_name or display_name}"\n'
            f'            "from_oslist" "{from_oslist}"\n'
            f'            "to_oslist" "{to_oslist}"\n'
            "        }\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        metadata = {
            "schema": 1,
            "tool": tool,
            "display_name": display_name,
            "renderer": renderer,
            "version": version,
            "runtime_package": runtime_package or f"{tool}.runtime",
            "capabilities": (
                dict(CAPABILITIES)
                if capabilities is None
                else capabilities
            ),
        }
        if metadata_updates:
            metadata.update(metadata_updates)
        (directory / "realsteamonmac.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )
        return directory

    def test_scans_two_side_by_side_dxmt_versions_in_display_name_order(self):
        second = self.write_tool(
            "dxmt-080",
            tool="dxmt-080",
            display_name="DXMT 0.80",
            version="0.80",
            runtime_package="dxmt-runtime-080",
            capabilities={**CAPABILITIES, "metalfx": True},
        )
        first = self.write_tool(
            "dxmt-070",
            tool="dxmt-070",
            display_name="DXMT 0.70",
            version="0.70",
            runtime_package="dxmt-runtime-070",
        )

        self.assertEqual(
            catalog.scan_compat_tools(self.root),
            [
                {
                    "strToolName": "dxmt-070",
                    "strDisplayName": "DXMT 0.70",
                    "renderer": "dxmt",
                    "version": "0.70",
                    "runtimePackage": "dxmt-runtime-070",
                    "capabilities": CAPABILITIES,
                    "installPath": str(first.resolve()),
                },
                {
                    "strToolName": "dxmt-080",
                    "strDisplayName": "DXMT 0.80",
                    "renderer": "dxmt",
                    "version": "0.80",
                    "runtimePackage": "dxmt-runtime-080",
                    "capabilities": {**CAPABILITIES, "metalfx": True},
                    "installPath": str(second.resolve()),
                },
            ],
        )

    def test_rejects_duplicate_tool_identifiers(self):
        self.write_tool(
            "first",
            tool="duplicate-tool",
            display_name="DXMT Stable",
        )
        self.write_tool(
            "second",
            tool="duplicate-tool",
            display_name="DXMT Preview",
        )

        with self.assertRaisesRegex(catalog.CatalogError, "duplicate"):
            catalog.scan_compat_tools(self.root)

    def test_ignores_unrelated_directories_without_tool_files(self):
        unrelated = self.root / "user-notes"
        unrelated.mkdir()
        (unrelated / "README.txt").write_text(
            "This directory is not a compatibility tool.\n",
            encoding="utf-8",
        )
        self.write_tool(
            "dxmt-080",
            tool="dxmt-080",
            display_name="DXMT 0.80",
        )

        tools = catalog.scan_compat_tools(self.root)

        self.assertEqual(
            [tool["strToolName"] for tool in tools],
            ["dxmt-080"],
        )

    def test_rejects_malformed_metadata(self):
        invalid_cases = {
            "unsupported-schema": {"schema": 2},
            "unsafe-tool": {"tool": "../escape"},
            "empty-display": {"display_name": ""},
            "control-display": {"display_name": "DXMT\nPreview"},
            "unsupported-renderer": {"renderer": "vulkan"},
            "empty-version": {"version": ""},
            "unsafe-runtime": {"runtime_package": "../../runtime"},
            "missing-capability": {
                "capabilities": {
                    key: value
                    for key, value in CAPABILITIES.items()
                    if key != "metalfx"
                }
            },
            "non-boolean-capability": {
                "capabilities": {**CAPABILITIES, "metalfx": 1}
            },
            "extra-capability": {
                "capabilities": {**CAPABILITIES, "future": False}
            },
            "extra-metadata-field": {"unexpected": True},
        }

        for index, (name, updates) in enumerate(invalid_cases.items()):
            with self.subTest(name=name):
                directory = self.write_tool(
                    f"invalid-{index}",
                    tool=f"invalid-{index}",
                    display_name=f"Invalid {index}",
                    metadata_updates=updates,
                )
                with self.assertRaises(catalog.CatalogError):
                    catalog.scan_compat_tools(self.root)
                for child in directory.iterdir():
                    child.unlink()
                directory.rmdir()

    def test_rejects_mismatched_or_wrong_platform_vdf(self):
        cases = {
            "identifier": {"vdf_tool": "different-tool"},
            "display": {"vdf_display_name": "Different Name"},
            "source": {"from_oslist": "linux"},
            "target": {"to_oslist": "linux"},
        }

        for index, (name, options) in enumerate(cases.items()):
            with self.subTest(name=name):
                directory = self.write_tool(
                    f"vdf-{index}",
                    tool=f"vdf-{index}",
                    display_name=f"VDF {index}",
                    **options,
                )
                with self.assertRaises(catalog.CatalogError):
                    catalog.scan_compat_tools(self.root)
                for child in directory.iterdir():
                    child.unlink()
                directory.rmdir()

    def test_rejects_symlink_tool_directory(self):
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (self.root / "linked-tool").symlink_to(
            outside, target_is_directory=True
        )

        with self.assertRaisesRegex(catalog.CatalogError, "symbolic link"):
            catalog.scan_compat_tools(self.root)

    def test_rejects_missing_executable_run(self):
        self.write_tool(
            "non-executable",
            tool="non-executable",
            display_name="Non Executable",
            executable=False,
        )

        with self.assertRaisesRegex(catalog.CatalogError, "executable"):
            catalog.scan_compat_tools(self.root)

    def test_cli_prints_catalog_json(self):
        self.write_tool(
            "cli-tool",
            tool="cli-tool",
            display_name="CLI Tool",
        )

        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH), str(self.root)],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            catalog.scan_compat_tools(self.root),
        )


if __name__ == "__main__":
    unittest.main()
