import os
import tempfile
import unittest
from pathlib import Path

from runtime.nonsteam_shortcut import resolve_shortcut_context


UINT32_MAX = (1 << 32) - 1


class NonSteamShortcutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.steam_root = self.root / "Steam"
        self.steamapps = self.steam_root / "steamapps"
        self.steamapps.mkdir(parents=True)
        self.config_root = self.root / "config" / "apps"
        self.external = self.root / "External Games"
        self.external.mkdir()
        self.target = self.external / "Fixture Game.exe"
        self.target.write_bytes(b"MZfixture")

    def tearDown(self):
        self.temporary.cleanup()

    def resolve(
        self,
        shortcut_id=7,
        target=None,
        steam_root=None,
        config_root=None,
        **overrides,
    ):
        return resolve_shortcut_context(
            shortcut_id,
            self.target if target is None else target,
            self.steam_root if steam_root is None else steam_root,
            config_root=(
                self.config_root
                if config_root is None
                else config_root
            ),
            **overrides,
        )

    def snapshot(self):
        entries = {}
        for path in sorted(self.root.rglob("*")):
            relative = path.relative_to(self.root).as_posix()
            if path.is_symlink():
                entries[relative] = ("symlink", os.readlink(path))
            elif path.is_file():
                entries[relative] = ("file", path.read_bytes())
            else:
                entries[relative] = ("directory", None)
        return entries

    def assert_rejected(self, target, keyword):
        with self.assertRaisesRegex(ValueError, f"(?i){keyword}"):
            self.resolve(target=target)

    def test_resolves_external_pe_without_creating_state(self):
        before = self.snapshot()

        context = self.resolve()

        compat_data = (
            self.steamapps
            / "compatdata"
            / "nonsteam-7"
        )
        self.assertEqual(context["identity_kind"], "nonsteam-pe")
        self.assertEqual(context["shortcut_id"], 7)
        self.assertEqual(context["appid"], 7)
        self.assertEqual(context["executable"], self.target)
        self.assertEqual(context["working_directory"], self.external)
        self.assertEqual(context["install_path"], self.external)
        self.assertEqual(context["steam_root"], self.steam_root)
        self.assertEqual(context["steamapps"], self.steamapps)
        self.assertEqual(context["compat_data"], compat_data)
        self.assertEqual(context["prefix"], compat_data / "pfx")
        self.assertEqual(context["state"], compat_data / "realsteamonmac")
        self.assertEqual(
            context["config"],
            compat_data / "realsteamonmac" / "config.json",
        )
        self.assertEqual(
            context["logs"],
            compat_data / "realsteamonmac" / "logs",
        )
        self.assertEqual(
            context["global_config"],
            self.config_root / "shortcut-7.json",
        )
        self.assertEqual(self.snapshot(), before)

    def test_accepts_uint32_shortcut_id_bounds(self):
        for value, expected in ((1, 1), (str(UINT32_MAX), UINT32_MAX)):
            with self.subTest(value=value):
                context = self.resolve(shortcut_id=value)
                self.assertEqual(context["shortcut_id"], expected)
                self.assertEqual(
                    context["prefix"],
                    self.steamapps
                    / "compatdata"
                    / f"nonsteam-{expected}"
                    / "pfx",
                )

    def test_rejects_invalid_shortcut_ids(self):
        cases = (
            (True, "shortcut.*id"),
            (False, "shortcut.*id"),
            (0, "shortcut.*id"),
            (-1, "shortcut.*id"),
            (UINT32_MAX + 1, "shortcut.*id"),
            ("0x1", "decimal"),
        )
        for value, keyword in cases:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, f"(?i){keyword}"):
                    self.resolve(shortcut_id=value)

    def test_rejects_oversized_decimal_shortcut_id_stably(self):
        with self.assertRaisesRegex(
            ValueError,
            "(?i)(shortcut.*id|decimal)",
        ):
            self.resolve(shortcut_id="9" * 5000)

    def test_rejects_invalid_targets(self):
        missing = self.external / "Missing.exe"
        directory = self.external / "Directory.exe"
        directory.mkdir()
        app = self.external / "Fixture.app"
        app.write_bytes(b"MZfixture")
        not_pe = self.external / "Text.exe"
        not_pe.write_bytes(b"not PE")

        cases = (
            (Path("relative.exe"), "absolute"),
            (missing, "exist"),
            (directory, "file"),
            (app, r"\.exe"),
            (not_pe, "MZ"),
        )
        for target, keyword in cases:
            with self.subTest(target=target):
                self.assert_rejected(target, keyword)

    def test_rejects_target_and_parent_directory_symlinks(self):
        target_link = self.external / "Target Link.exe"
        target_link.symlink_to(self.target)

        real_parent = self.root / "Real Parent"
        real_parent.mkdir()
        parent_target = real_parent / "Parent Link.exe"
        parent_target.write_bytes(b"MZfixture")
        linked_parent = self.root / "Linked Parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)

        for target in (target_link, linked_parent / parent_target.name):
            with self.subTest(target=target):
                self.assert_rejected(target, "symlink")

    def test_rejects_wrong_explicit_compatdata(self):
        with self.assertRaisesRegex(ValueError, "(?i)compat"):
            self.resolve(
                explicit_compat_data=self.root / "wrong-compatdata"
            )

    def test_rejects_symlinked_steamapps_and_compatdata(self):
        self.steamapps.rmdir()
        real_steamapps = self.root / "real-steamapps"
        real_steamapps.mkdir()
        self.steamapps.symlink_to(real_steamapps, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "(?i)steamapps.*symlink"):
            self.resolve()

        self.steamapps.unlink()
        self.steamapps.mkdir()
        real_compatdata = self.root / "real-compatdata"
        real_compatdata.mkdir()
        (self.steamapps / "compatdata").symlink_to(
            real_compatdata, target_is_directory=True
        )
        with self.assertRaisesRegex(ValueError, "(?i)compat.*symlink"):
            self.resolve()

    def test_rejects_symlinked_compatdata_leaf_prefix_and_state(self):
        compatdata_root = self.steamapps / "compatdata"
        compatdata_root.mkdir()
        compat_data = compatdata_root / "nonsteam-7"
        real_directory = self.root / "real-state"
        real_directory.mkdir()

        compat_data.symlink_to(real_directory, target_is_directory=True)
        with self.assertRaisesRegex(
            ValueError,
            "(?i)compat.*symlink",
        ):
            self.resolve()

        compat_data.unlink()
        compat_data.mkdir()
        prefix = compat_data / "pfx"
        prefix.symlink_to(real_directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "(?i)prefix.*symlink"):
            self.resolve()

        prefix.unlink()
        state = compat_data / "realsteamonmac"
        state.symlink_to(real_directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "(?i)state.*symlink"):
            self.resolve()

    def test_rejects_symlinked_state_config_and_logs(self):
        state = (
            self.steamapps
            / "compatdata"
            / "nonsteam-7"
            / "realsteamonmac"
        )
        state.mkdir(parents=True)
        real_file = self.root / "real-config.json"
        real_file.write_text("{}")
        real_directory = self.root / "real-logs"
        real_directory.mkdir()

        config = state / "config.json"
        config.symlink_to(real_file)
        with self.assertRaisesRegex(
            ValueError,
            "(?i)config.*symlink",
        ):
            self.resolve()

        config.unlink()
        logs = state / "logs"
        logs.symlink_to(real_directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "(?i)logs.*symlink"):
            self.resolve()

    def test_rejects_relative_steam_root(self):
        with self.assertRaisesRegex(ValueError, "(?i)steam_root.*absolute"):
            self.resolve(steam_root=Path("Steam"))

    def test_rejects_steam_root_and_parent_directory_symlinks(self):
        linked_steam_root = self.root / "Linked Steam"
        linked_steam_root.symlink_to(
            self.steam_root,
            target_is_directory=True,
        )

        real_holder = self.root / "Real Holder"
        (real_holder / "Steam" / "steamapps").mkdir(parents=True)
        linked_holder = self.root / "Linked Holder"
        linked_holder.symlink_to(real_holder, target_is_directory=True)

        for steam_root in (
            linked_steam_root,
            linked_holder / "Steam",
        ):
            with self.subTest(steam_root=steam_root):
                with self.assertRaisesRegex(
                    ValueError,
                    "(?i)steam_root.*symlink",
                ):
                    self.resolve(steam_root=steam_root)

    def test_rejects_symlinks_hidden_by_missing_parent_collapse(self):
        linked_steam_root = self.root / "LinkedSteam"
        linked_steam_root.symlink_to(
            self.steam_root,
            target_is_directory=True,
        )
        aliased_steam_root = (
            self.root
            / "missing"
            / ".."
            / linked_steam_root.name
        )
        with self.assertRaisesRegex(
            ValueError,
            "(?i)steam_root.*symlink",
        ):
            self.resolve(steam_root=aliased_steam_root)

        linked_target = self.root / "LinkedTarget.exe"
        linked_target.symlink_to(self.target)
        aliased_target = (
            self.root
            / "missing"
            / ".."
            / linked_target.name
        )
        with self.assertRaisesRegex(ValueError, "(?i)target.*symlink"):
            self.resolve(target=aliased_target)

    def test_canonicalizes_steam_root_before_building_paths(self):
        holder = self.root / "holder"
        holder.mkdir()
        aliased_steam_root = holder / ".." / self.steam_root.name

        context = self.resolve(steam_root=aliased_steam_root)

        compat_data = self.steamapps / "compatdata" / "nonsteam-7"
        self.assertEqual(context["steam_root"], self.steam_root)
        self.assertEqual(context["steamapps"], self.steamapps)
        self.assertEqual(context["compat_data"], compat_data)

    def test_rejects_relative_config_root(self):
        with self.assertRaisesRegex(
            ValueError,
            "(?i)config_root.*absolute",
        ):
            self.resolve(config_root=Path("config/apps"))

    def test_rejects_config_root_parent_symlink_after_collapse(self):
        real_parent = self.root / "Real Config"
        (real_parent / "apps").mkdir(parents=True)
        linked_parent = self.root / "Linked Config"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        aliased_config_root = (
            self.root
            / "missing"
            / ".."
            / linked_parent.name
            / "apps"
        )

        with self.assertRaisesRegex(
            ValueError,
            "(?i)config_root.*symlink",
        ):
            self.resolve(config_root=aliased_config_root)

    def test_canonicalizes_config_root_and_global_config(self):
        holder = self.root / "config-holder"
        holder.mkdir()
        aliased_config_root = holder / ".." / "config" / "apps"

        context = self.resolve(config_root=aliased_config_root)

        self.assertEqual(
            context["global_config"],
            self.config_root / "shortcut-7.json",
        )

    def test_rejects_symlinked_global_config_leaf(self):
        self.config_root.mkdir(parents=True)
        real_config = self.root / "real-global-config.json"
        real_config.write_text("{}")
        global_config = self.config_root / "shortcut-7.json"
        global_config.symlink_to(real_config)

        with self.assertRaisesRegex(
            ValueError,
            "(?i)global.*config.*symlink",
        ):
            self.resolve()

    def test_accepts_canonical_exact_explicit_compatdata(self):
        compat_data = self.steamapps / "compatdata" / "nonsteam-7"

        context = self.resolve(explicit_compat_data=compat_data)

        self.assertEqual(context["compat_data"], compat_data)

    def test_rejects_noncanonical_explicit_compatdata_alias(self):
        compat_data = self.steamapps / "compatdata" / "nonsteam-7"
        aliased = compat_data.parent / "unused" / ".." / compat_data.name

        with self.assertRaisesRegex(ValueError, "(?i)compat.*canonical"):
            self.resolve(explicit_compat_data=aliased)

    def test_allows_target_inside_steam_root(self):
        target = self.steam_root / "Installed Game.exe"
        target.write_bytes(b"MZfixture")

        context = self.resolve(target=target)

        self.assertEqual(context["executable"], target)

    def test_rejects_nul_paths_with_stable_module_messages(self):
        compat_data = self.steamapps / "compatdata" / "nonsteam-7"
        cases = (
            (
                {"target": f"{self.target}\0"},
                "target",
            ),
            (
                {"steam_root": f"{self.steam_root}\0"},
                "steam_root",
            ),
            (
                {"explicit_compat_data": f"{compat_data}\0"},
                "explicit compat data",
            ),
        )

        for overrides, label in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    ValueError,
                    f"(?i){label}",
                ) as raised:
                    self.resolve(**overrides)
                self.assertNotIn(
                    "embedded null byte",
                    str(raised.exception).lower(),
                )


if __name__ == "__main__":
    unittest.main()
