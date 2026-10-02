import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "audio"))

from production_source_publication import (build_catalog, pack_runtime_catalog,
                                           runtime_role_key)  # noqa: E402
from shipped_content import ROSTER_CONFIGS  # noqa: E402


class ProductionSourcePublicationTests(unittest.TestCase):
    def test_bor_catalog_is_source_sized_and_fail_closed(self):
        catalog = build_catalog(ROSTER_CONFIGS)
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
        catalog = build_catalog(ROSTER_CONFIGS)
        for entry in catalog["entries"]:
            self.assertNotEqual(entry["dimensions"], [32, 48])
            self.assertEqual(entry["tile_bytes"], entry["sheet_bytes"])
            self.assertEqual(entry["sheet_bytes"] % 512, 0)

    def test_runtime_catalog_is_deterministic_and_content_addressed(self):
        catalog = build_catalog(ROSTER_CONFIGS)
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
        self.assertEqual(runtime_role_key("unknown-role"), 255)


if __name__ == "__main__":
    unittest.main()
