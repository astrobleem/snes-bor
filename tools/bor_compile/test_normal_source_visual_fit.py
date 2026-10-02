"""Normal's known over-16-KiB K9999 pose remains source-sized and lossless."""
import sys
import io
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/bor_compile"), str(ROOT / "tools/audio")]

from production_source_publication import build_catalog  # noqa: E402
from shipped_content import ROSTER_CONFIGS  # noqa: E402
from compiler import Source  # noqa: E402


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

    def test_furnace_animation_fits_obj_and_roundtrips_hardware_colors(self):
        config = next(row for row in ROSTER_CONFIGS
                      if row["source_character"].replace("\\", "/").upper()
                      .endswith("/MISC/FURNACE"))
        catalog = build_catalog([config])
        entries = sorted((row for row in catalog["entries"]
                          if row["identity"].upper() == "MISC/FURNACE"
                          and row["role"].lower() in ("idle", "waiting")
                          and row["map"] == 0), key=lambda row: row["frame"])
        self.assertEqual(len(entries), 8, catalog["blockers"])
        self.assertFalse(catalog["blockers"])
        self.assertEqual(entries[0]["dimensions"], [320, 62])
        source_path = Path(config.get("pak") or
                           "Beats of Rage Original [v.3.0 Build 4086].pak")
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        source = Source(source_path)
        cluster = entries[0]["palette_cluster"]
        self.assertEqual(cluster["palette_count"], 3)
        self.assertEqual(cluster["source_colors"], 25)
        self.assertGreater(cluster["cgram_aliases"], 0)
        self.assertEqual(len(cluster["frame_piece_counts"]), len(entries))

        for frame_index, entry in enumerate(entries):
            self.assertLessEqual(entry["piece_count"], 128)
            self.assertEqual(cluster["frame_piece_counts"][frame_index],
                             entry["piece_count"])
            self.assertTrue(all(piece.get("obj_size", [16, 32]) == [16, 32]
                                for piece in entry["pieces"]))
            self.assertEqual(entry["piece_count"], 40)
            self.assertEqual(entry["sheet_bytes"], 10 * 1024)
            self.assertEqual(entry["tile_bytes"], entry["sheet_bytes"])
            self.assertTrue(all(len(bytes.fromhex(block["data"])) == 256
                                for block in entry["blocks"].values()))
            source_image = Image.open(io.BytesIO(source.read(entry["source_path"])))
            source_image.load()
            width, height = source_image.size
            reconstructed = [[None] * width for _ in range(height)]
            sheet = bytes.fromhex(entry["sheet_data"])
            source_palette = source.read("data/pal.act")

            def cgram_color(index):
                rgb = source_palette[index * 3:index * 3 + 3]
                return ((rgb[0] >> 3) | ((rgb[1] >> 3) << 5)
                        | ((rgb[2] >> 3) << 10))

            for piece in entry["pieces"]:
                block = bytes.fromhex(entry["blocks"][piece["resource"]]["data"])
                piece_width, piece_height = piece["obj_size"]
                tiles_wide, tiles_high = piece_width // 8, piece_height // 8
                self.assertEqual(len(block), tiles_wide * tiles_high * 32)
                palette = entry["palettes"][piece["palette"]]["colors"]
                origin_tile = piece["sheet_tile"]
                self.assertTrue(0 <= origin_tile < 512)
                for tile_index in range(tiles_wide * tiles_high):
                    cell = ((origin_tile // 16 + tile_index // tiles_wide) * 16
                            + origin_tile % 16 + tile_index % tiles_wide)
                    self.assertEqual(
                        sheet[cell * 32:cell * 32 + 32],
                        block[tile_index * 32:tile_index * 32 + 32])

                source_x, source_y = piece["source_xy"]
                for tile_index in range(tiles_wide * tiles_high):
                    tile_x = (tile_index % tiles_wide) * 8
                    tile_y = (tile_index // tiles_wide) * 8
                    tile = block[tile_index * 32:(tile_index + 1) * 32]
                    for y in range(8):
                        p0, p1 = tile[y * 2], tile[y * 2 + 1]
                        p2, p3 = tile[16 + y * 2], tile[17 + y * 2]
                        for x in range(8):
                            shift = 7 - x
                            color = (((p0 >> shift) & 1)
                                     | (((p1 >> shift) & 1) << 1)
                                     | (((p2 >> shift) & 1) << 2)
                                     | (((p3 >> shift) & 1) << 3))
                            if not color:
                                continue
                            px = source_x + tile_x + x
                            py = source_y + tile_y + y
                            if 0 <= px < width and 0 <= py < height:
                                value = cgram_color(palette[color])
                                old = reconstructed[py][px]
                                self.assertIn(old, (None, value))
                                reconstructed[py][px] = value

            self.assertEqual(
                [pixel for row in reconstructed for pixel in row],
                [None if pixel == 0 else cgram_color(pixel)
                 for pixel in source_image.getdata()],
                f"Furnace source-CGRAM mismatch in frame {frame_index}")


if __name__ == "__main__":
    unittest.main()
