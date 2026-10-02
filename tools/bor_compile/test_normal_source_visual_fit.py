"""Normal's known over-16-KiB K9999 pose remains source-sized and lossless."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/bor_compile"), str(ROOT / "tools/audio")]

from production_source_publication import build_catalog  # noqa: E402
from shipped_content import ROSTER_CONFIGS  # noqa: E402


class NormalSourceVisualFitTests(unittest.TestCase):
    def test_k9999_65_piece_pose_fits_full_obj_without_resizing(self):
        config = next(row for row in ROSTER_CONFIGS
                      if row["source_character"].replace("\\", "/").upper().endswith("/K9999"))
        catalog = build_catalog([config])
        entry = next(row for row in catalog["entries"]
                     if row["identity"].upper() == "K9999"
                     and row["role"] == "special" and row["frame"] == 14
                     and row["map"] == 0)
        self.assertEqual(entry["dimensions"], [214, 198])
        self.assertEqual(entry["piece_count"], 65)
        self.assertEqual(entry["packed_solver_status"], "lossless_full_obj_overlap_16k")
        self.assertEqual(entry["sheet_bytes"], 16 * 1024)
        self.assertEqual(entry["tile_bytes"], entry["sheet_bytes"])
        self.assertFalse(catalog["blockers"])
        # Every piece points to its exact content-addressed 16x32 tile block;
        # no piece scale, source offset, or OAM-piece count is adapted.
        sheet = bytes.fromhex(entry["sheet_data"])
        for piece in entry["pieces"]:
            origin = piece["sheet_tile"]
            self.assertTrue(0 <= origin < 512)
            block = bytes.fromhex(entry["blocks"][piece["resource"]]["data"])
            self.assertEqual(len(block), 256)
            for tile in range(8):
                cell = (origin // 16 + tile // 2) * 16 + origin % 16 + tile % 2
                self.assertEqual(sheet[cell * 32:cell * 32 + 32],
                                 block[tile * 32:tile * 32 + 32])


if __name__ == "__main__":
    unittest.main()
