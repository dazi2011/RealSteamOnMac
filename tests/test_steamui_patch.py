import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCHER_PATH = ROOT / "script" / "patch_steamui.py"
CURRENT_INDEX = (
    '<!doctype html><html style="width: 100%; height: 100%"><head>'
    '<title>SharedJSContext</title><meta charset="utf-8">'
    '<script defer="defer" src="/libraries/libraries~00299a408.js"></script>'
    '<script defer="defer" src="/library.js"></script>'
    '<link href="/css/library.css" rel="stylesheet"></head>'
    '<body style="width: 100%; height: 100%; margin: 0; overflow: hidden;">'
    '<div id="root" style="height:100%; width: 100%"></div>'
    '<div style="display:none"></div></body></html>'
)
COMPAT_PAGE_ANCHOR = (
    '(0,f.CI)()&&o.push({title:(0,A.we)'
    '("#AppProperties_CompatibilityPage")'
)
CURRENT_COMPAT_CHUNK = (
    f"before{COMPAT_PAGE_ANCHOR}middle{COMPAT_PAGE_ANCHOR}after"
)


def load_patcher():
    spec = importlib.util.spec_from_file_location("patch_steamui", PATCHER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SteamUIPatchTests(unittest.TestCase):
    def setUp(self):
        self.patcher = load_patcher()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.steamui = self.root / "steamui"
        self.steamui.mkdir()
        self.index = self.steamui / "index.html"
        self.index.write_text(CURRENT_INDEX, encoding="utf-8")
        self.compat_chunk = self.steamui / "chunk~2dcc5aaf7.js"
        self.compat_chunk.write_text(CURRENT_COMPAT_CHUNK, encoding="utf-8")
        self.patcher.KNOWN_COMPAT_CHUNK_SHA256.add(
            self.patcher.sha256_bytes(CURRENT_COMPAT_CHUNK.encode("utf-8"))
        )
        self.ui_source = self.root / "realsteamonmac_ui.js"
        self.ui_source.write_text("globalThis.realSteamOnMacLoaded = true;\n")
        self.allowlist = self.root / "allowlist.txt"
        self.allowlist.write_text("1118200\n", encoding="utf-8")
        self.registry_token = self.root / "registry-token"
        self.registry_token.write_text(
            "0123456789abcdef0123456789abcdef\n",
            encoding="utf-8",
        )
        dependency_directory = self.root / "dependencies"
        dependency_directory.mkdir()
        self.dependency_catalog = dependency_directory / "catalog.json"
        self.dependency_catalog.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "dependencies": [
                        {
                            "id": "vcrun2022",
                            "name": "Microsoft Visual C++ 2015-2022 x64",
                            "description": "Installs the current runtime.",
                            "publisher": "Microsoft",
                            "filename": "vc_redist.x64.exe",
                            "url": (
                                "https://aka.ms/vs/17/release/"
                                "vc_redist.x64.exe"
                            ),
                            "sha256": "0" * 64,
                            "size": 25635768,
                            "arguments": ["/quiet"],
                            "success_codes": [0],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_install_is_idempotent_and_restore_recovers_original(self):
        original = self.index.read_bytes()
        original_compat_chunk = self.compat_chunk.read_bytes()

        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )
        first = self.index.read_bytes()
        self.assertIn(b"/realsteamonmac/config.js", first)
        self.assertIn(b"/realsteamonmac/ui.js", first)
        self.assertTrue(
            (self.steamui / "index.html.realsteamonmac.original").is_file()
        )
        self.assertTrue(
            (
                self.steamui
                / "chunk~2dcc5aaf7.js.realsteamonmac.original"
            ).is_file()
        )
        patched_compat_chunk = self.compat_chunk.read_text(encoding="utf-8")
        self.assertEqual(
            patched_compat_chunk.count(
                self.patcher.COMPAT_PAGE_DYNAMIC_GATE
            ),
            2,
        )
        self.assertIn(
            "__REALSTEAMONMAC_IS_MANAGED_APP__",
            patched_compat_chunk,
        )
        self.assertNotIn(COMPAT_PAGE_ANCHOR, patched_compat_chunk)

        config_path = self.steamui / "realsteamonmac" / "config.js"
        config_text = config_path.read_text(encoding="utf-8")
        self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)
        payload = config_text.split("Object.freeze(", 1)[1].rsplit(");", 1)[0]
        self.assertEqual(
            json.loads(payload),
            {
                "appids": [1118200],
                "defaultCompatTool": "realsteamonmac-dxmt",
                "registryEndpoint": "http://127.0.0.1:57344/registry",
                "controlEndpoint": "http://127.0.0.1:57344/config",
                "actionEndpoint": "http://127.0.0.1:57344/action",
                "jobEndpoint": "http://127.0.0.1:57344/job",
                "registryToken": "0123456789abcdef0123456789abcdef",
                "compatTools": [
                    {
                        "strToolName": "realsteamonmac-gptk",
                        "strDisplayName": "RealSteamOnMac - GPTK 3",
                        "renderer": "gptk",
                    },
                    {
                        "strToolName": "realsteamonmac-dxmt",
                        "strDisplayName": "RealSteamOnMac - DXMT 0.80",
                        "renderer": "dxmt",
                    },
                    {
                        "strToolName": "realsteamonmac-dxvk",
                        "strDisplayName": (
                            "RealSteamOnMac - DXVK macOS 1.10.3"
                        ),
                        "renderer": "dxvk",
                    },
                    {
                        "strToolName": "realsteamonmac-wined3d",
                        "strDisplayName": (
                            "RealSteamOnMac - WineD3D 11.10"
                        ),
                        "renderer": "wined3d",
                    },
                ],
                "dependencies": [
                    {
                        "id": "vcrun2022",
                        "name": "Microsoft Visual C++ 2015-2022 x64",
                        "description": "Installs the current runtime.",
                        "publisher": "Microsoft",
                        "size": 25635768,
                    }
                ],
            },
        )

        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )
        self.assertEqual(self.index.read_bytes(), first)
        self.patcher.verify_steamui(self.steamui)

        self.patcher.restore_steamui(self.steamui)
        self.assertEqual(self.index.read_bytes(), original)
        self.assertEqual(
            self.compat_chunk.read_bytes(),
            original_compat_chunk,
        )
        self.assertFalse((self.steamui / "realsteamonmac").exists())
        self.assertFalse(
            (self.steamui / "index.html.realsteamonmac.original").exists()
        )
        self.assertFalse(
            (
                self.steamui
                / "chunk~2dcc5aaf7.js.realsteamonmac.original"
            ).exists()
        )

    def test_allowlist_parser_filters_invalid_and_duplicate_values(self):
        self.allowlist.write_text(
            "# selected games\n1118200, 1118200\n0\ninvalid\n4294967296\n42\n",
            encoding="utf-8",
        )

        self.assertEqual(
            self.patcher.parse_allowlist(self.allowlist),
            [1118200, 42],
        )

    def test_install_reapplies_when_steam_restores_the_supported_index(self):
        original = self.index.read_bytes()
        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )
        self.index.write_bytes(original)

        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )

        self.patcher.verify_steamui(self.steamui)
        self.assertIn(b"/realsteamonmac/ui.js", self.index.read_bytes())

    def test_install_migrates_the_previous_static_compatibility_gate(self):
        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )
        backup = (
            self.steamui
            / "chunk~2dcc5aaf7.js.realsteamonmac.original"
        ).read_text(encoding="utf-8")
        previous = backup.replace(
            self.patcher.COMPAT_PAGE_ANCHOR,
            self.patcher.COMPAT_PAGE_ALLOWLIST_GATE,
        )
        self.compat_chunk.write_text(previous, encoding="utf-8")

        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )

        current = self.compat_chunk.read_text(encoding="utf-8")
        self.assertEqual(
            current.count(self.patcher.COMPAT_PAGE_DYNAMIC_GATE),
            2,
        )
        self.assertNotIn(
            self.patcher.COMPAT_PAGE_ALLOWLIST_GATE,
            current,
        )
        self.patcher.verify_steamui(self.steamui)

    def test_unknown_clean_index_is_rejected_without_changes(self):
        self.index.write_text(
            CURRENT_INDEX.replace("SharedJSContext", "UnknownBuild"),
            encoding="utf-8",
        )
        original = self.index.read_bytes()

        with self.assertRaisesRegex(ValueError, "unsupported Steam UI index"):
            self.patcher.install_steamui(
                self.steamui,
                self.ui_source,
                self.allowlist,
            )

        self.assertEqual(self.index.read_bytes(), original)
        self.assertFalse(
            (self.steamui / "index.html.realsteamonmac.original").exists()
        )
        self.assertFalse((self.steamui / "realsteamonmac").exists())

    def test_unknown_compat_chunk_is_rejected_before_index_changes(self):
        original_index = self.index.read_bytes()
        original_chunk = b"unknown compatibility module"
        self.compat_chunk.write_bytes(original_chunk)

        with self.assertRaisesRegex(
            ValueError,
            "unsupported compatibility chunk hash",
        ):
            self.patcher.install_steamui(
                self.steamui,
                self.ui_source,
                self.allowlist,
            )

        self.assertEqual(self.index.read_bytes(), original_index)
        self.assertEqual(self.compat_chunk.read_bytes(), original_chunk)
        self.assertFalse(
            (self.steamui / "index.html.realsteamonmac.original").exists()
        )
        self.assertFalse((self.steamui / "realsteamonmac").exists())

    def test_verify_rejects_a_missing_installed_asset(self):
        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )
        (self.steamui / "realsteamonmac" / "ui.js").unlink()

        with self.assertRaisesRegex(ValueError, "UI asset is missing"):
            self.patcher.verify_steamui(self.steamui)

    def test_install_rejects_an_invalid_registry_token(self):
        self.registry_token.write_text("not-a-token\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "registry token is invalid"):
            self.patcher.install_steamui(
                self.steamui,
                self.ui_source,
                self.allowlist,
            )

    def test_install_rejects_an_invalid_dependency_catalog(self):
        self.dependency_catalog.write_text(
            '{"schema":1,"dependencies":[]}',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "catalog is empty"):
            self.patcher.install_steamui(
                self.steamui,
                self.ui_source,
                self.allowlist,
            )

    def test_verify_rejects_broad_config_permissions(self):
        self.patcher.install_steamui(
            self.steamui,
            self.ui_source,
            self.allowlist,
        )
        (self.steamui / "realsteamonmac" / "config.js").chmod(0o644)

        with self.assertRaisesRegex(ValueError, "permissions are too broad"):
            self.patcher.verify_steamui(self.steamui)

    def test_restore_rejects_a_missing_backup(self):
        with self.assertRaisesRegex(ValueError, "backup is missing"):
            self.patcher.restore_steamui(self.steamui)


if __name__ == "__main__":
    unittest.main()
