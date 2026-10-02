import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "audio"))

from production_source_publication import (build_catalog, pack_runtime_catalog,
                                           emit_policy_include,
                                           runtime_catalog_role_key,
                                           runtime_catalog_role_aliases,
                                           runtime_role_key)  # noqa: E402
from shipped_content import ROSTER_CONFIGS  # noqa: E402


class ProductionSourcePublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The production catalog walk resolves thousands of PAK frames. Keep
        # these tests focused on assertions rather than rebuilding the same
        # deterministic catalog once per method.
        cls.catalog = build_catalog(ROSTER_CONFIGS)

    def test_bor_catalog_is_source_sized_and_fail_closed(self):
        catalog = self.catalog
        self.assertEqual(catalog["visual_policies"]["SOURCE_SIZED"], 1)
        self.assertGreater(catalog["summary"]["entry_count"], 0)
        self.assertEqual(catalog["summary"]["legacy_fixed_entries"], 0)
        kula = [e for e in catalog["entries"] if e["identity"].upper() == "KULA"
                and e["role"] == "attack1" and e["frame"] == 0]
        self.assertEqual({e["map"] for e in kula}, {0, 1})
        for entry in kula:
            self.assertEqual(entry["dimensions"], [98, 104])
            self.assertEqual(entry["visual_policy"], "SOURCE_SIZED")
            self.assertGreater(entry["piece_count"], 0)

    def test_catalog_never_marks_a_legacy_frame_as_source_sized(self):
        catalog = self.catalog
        for entry in catalog["entries"]:
            self.assertNotEqual(entry["dimensions"], [32, 48])
            self.assertEqual(entry["tile_bytes"], entry["sheet_bytes"])
            self.assertEqual(entry["sheet_bytes"] % 512, 0)

    def test_runtime_catalog_is_deterministic_and_content_addressed(self):
        catalog = self.catalog
        blob = pack_runtime_catalog(catalog)
        self.assertEqual(blob[:6], b"SVIS1\0")
        self.assertGreater(len(blob), 4096)
        self.assertEqual(blob, pack_runtime_catalog(catalog))
        self.assertEqual(len({p["resource"] for e in catalog["entries"]
                              for p in e["pieces"]}),
                         int.from_bytes(blob[10:12], "little"))

    def test_runtime_role_key_is_presentation_only(self):
        self.assertEqual(runtime_role_key("idle"), 0)
        self.assertEqual(runtime_role_key("attack1"), 2)
        self.assertEqual(runtime_role_key("attack2"), 3)
        self.assertEqual(runtime_role_key("fall"), 4)
        self.assertEqual(runtime_role_key("jump"), 7)
        self.assertEqual(runtime_role_key("pain"), 8)
        self.assertEqual(runtime_role_key("unknown-role"), 255)

    def test_authored_grab_is_attack2_only_without_a_separate_attack2(self):
        self.assertEqual(runtime_catalog_role_key("grab", {"grab"}), 3)
        self.assertEqual(
            runtime_catalog_role_key("grab", {"grab", "attack2"}), 255
        )
        self.assertEqual(
            runtime_catalog_role_key("attack2", {"grab", "attack2"}), 3
        )

    def test_joe_authored_grab_frames_resolve_as_runtime_attack2(self):
        joe_grab = [entry for entry in self.catalog["entries"]
                    if entry["roster"] == 2 and entry["identity"].upper() == "JOE"
                    and entry["role"].lower() == "grab"]
        self.assertTrue(joe_grab)
        self.assertEqual({entry["runtime_role"] for entry in joe_grab}, {3})

    def test_biker_motor_clip_has_native_fall_alias_without_losing_pain_key(self):
        self.assertEqual(runtime_catalog_role_aliases(
            "pain", {"idle", "pain"}, "BIKER-K"), (4,))
        self.assertEqual(runtime_catalog_role_aliases(
            "pain", {"idle", "pain"}, "OTHER"), ())
        biker_pain = [entry for entry in self.catalog["entries"]
                      if entry["roster"] == 28
                      and entry["identity"].upper() == "BIKER-K"
                      and entry["role"].lower() == "pain"]
        self.assertEqual(len(biker_pain), 2)
        self.assertEqual({entry["runtime_role"] for entry in biker_pain}, {8})
        self.assertEqual({tuple(entry["runtime_key_aliases"])
                          for entry in biker_pain}, {(4,)})

        with tempfile.TemporaryDirectory() as temp_dir:
            include = Path(temp_dir) / "policy.pasm"
            keys = Path(temp_dir) / "keys.pasm"
            emit_policy_include(self.catalog, include, key_path=keys)
            lines = keys.read_text(encoding="ascii").splitlines()
            bindings = {}
            for line_index, line in enumerate(lines[:-1]):
                if not line.startswith("    .db 28,"):
                    continue
                fields = tuple(int(value) for value in
                               line.removeprefix("    .db ").split(","))
                if fields[1] not in (4, 8) or fields[2:] != (0, 0):
                    continue
                bindings[fields[1]] = int(lines[line_index + 1].split()[-1])
            self.assertIn(4, bindings)
            self.assertIn(8, bindings)
            self.assertEqual(bindings[4], bindings[8])
            self.assertIn(
                "SOURCE_VISUAL_ENTRY_KEY_COUNT = "
                f"{len(self.catalog['entries']) + sum(len(entry.get('runtime_key_aliases', ())) for entry in self.catalog['entries'])}",
                include.read_text(encoding="ascii"),
            )

    def test_jhun_jumpattack_resolves_the_observed_attack2_visual_key(self):
        self.assertEqual(runtime_catalog_role_aliases(
            "jumpattack", {"attack1", "jumpattack"}, "JHUN"), (3,))
        self.assertEqual(runtime_catalog_role_aliases(
            "jumpattack", {"attack1", "attack2", "jumpattack"}, "JHUN"), ())
        self.assertEqual(runtime_catalog_role_aliases(
            "jumpattack", {"attack1", "jumpattack"}, "OTHER"), ())
        frames = [entry for entry in self.catalog["entries"]
                  if entry["identity"].upper() == "JHUN"
                  and entry["role"].lower() == "jumpattack"]
        self.assertEqual({entry["frame"] for entry in frames}, set(range(5)))
        self.assertEqual({tuple(entry["runtime_key_aliases"])
                          for entry in frames}, {(3,)})

    def test_ralf_upper_resolves_the_observed_attack2_visual_key(self):
        self.assertEqual(runtime_catalog_role_aliases(
            "upper", {"attack1", "upper"}, "RALF"), (3,))
        self.assertEqual(runtime_catalog_role_aliases(
            "upper", {"attack1", "attack2", "upper"}, "RALF"), ())
        self.assertEqual(runtime_catalog_role_aliases(
            "upper", {"attack1", "upper"}, "OTHER"), ())
        frames = [entry for entry in self.catalog["entries"]
                  if entry["identity"].upper() == "RALF"
                  and entry["role"].lower() == "upper"]
        self.assertEqual({entry["frame"] for entry in frames}, set(range(4)))
        self.assertEqual({tuple(entry["runtime_key_aliases"])
                          for entry in frames}, {(3,)})

    def test_native_key_rows_use_canonical_runtime_key_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            include = Path(temp_dir) / "policy.pasm"
            keys = Path(temp_dir) / "keys.pasm"
            emit_policy_include(self.catalog, include, key_path=keys)
            lines = keys.read_text(encoding="ascii").splitlines()

        rows = []
        for line_index, line in enumerate(lines[:-1]):
            if not line.startswith("    .db "):
                continue
            key = tuple(int(value) for value in
                        line.removeprefix("    .db ").split(","))
            entry_index = int(lines[line_index + 1].removeprefix("    .dw "))
            rows.append((key, entry_index))

        keys_in_order = [key for key, _entry_index in rows]
        self.assertEqual(keys_in_order, sorted(keys_in_order))
        for (roster, role, _frame, _map_index), entry_index in rows:
            entry = self.catalog["entries"][entry_index]
            self.assertEqual(roster, entry["roster"])
            self.assertIn(role, {entry["runtime_role"],
                                 *entry.get("runtime_key_aliases", ())})

    def test_transparent_steamer_source_entry_is_kept_empty(self):
        steamer = [entry for entry in self.catalog["entries"]
                   if entry["roster"] == 35
                   and entry["identity"].upper() == "MISC/STEAMER"]
        self.assertEqual(len(steamer), 1)
        self.assertEqual(steamer[0]["piece_count"], 0)
        self.assertEqual(steamer[0]["pieces"], [])


if __name__ == "__main__":
    unittest.main()
