"""Keep stream-cache mode flags out of live scroll state."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


def symbol_address(path: Path, name: str) -> int:
    source = path.read_text()
    match = re.search(rf"^{re.escape(name)}\s*=\s*\$([0-9A-Fa-f]+)", source, re.M)
    if not match:
        raise AssertionError(f"missing {name} in {path}")
    return int(match.group(1), 16)


class StreamCacheWramTests(unittest.TestCase):
    def test_mode_flags_use_gap_after_stream_scroll_and_before_fp_cache(self):
        cache = ROOT / "src/core/stream_cache.pasm"
        main = ROOT / "src/main.pasm"
        fetch_buf_sel = symbol_address(main, "StreamScroll_FetchBufSel")
        fp_cache_start = symbol_address(
            ROOT / "src/core/stream_cache_fp.pasm", "StreamCacheFp_CurrentStamp"
        )
        flags = [
            symbol_address(cache, "StreamCache_NormalLayout"),
            symbol_address(cache, "StreamCache_BG2Capacity"),
            symbol_address(cache, "StreamCache_LegacyFpActive"),
        ]

        self.assertEqual(flags, [0x7E259A, 0x7E259B, 0x7E259C])
        self.assertEqual(fetch_buf_sel, 0x7E2599)
        self.assertEqual(fp_cache_start, 0x7E25A0)
        self.assertTrue(all(fetch_buf_sel < address < fp_cache_start for address in flags))

    def test_reservation_helper_bytes_match_its_dedicated_bank_symbol(self):
        symbol_line = next(
            line for line in (ROOT / "src/main.sym").read_text().splitlines()
            if line.endswith(" Core_StreamCache_IsReserved")
        )
        bank_text, address_text = symbol_line.split()[0].split(":")
        bank, address = int(bank_text, 16), int(address_text, 16)
        self.assertEqual((bank, address), (0x1B, 0x8000))

        # main.bin is bank ordered; $8000 is the first byte of each LoROM
        # bank's 32-KiB physical window. Assert emitted code, not just the
        # symbol, so an overlapping later .org is caught.
        offset = bank * 0x8000 + (address & 0x7FFF)
        image = (ROOT / "src/main.bin").read_bytes()
        self.assertGreaterEqual(len(image), offset + 2)
        self.assertEqual(image[offset:offset + 2], bytes((0xC2, 0x30)))

    def test_streaming_initial_column_setup_clears_reserved_bg1_blank(self):
        symbol_line = next(
            line for line in (ROOT / "src/main.sym").read_text().splitlines()
            if line.endswith(" Core_StreamCache_InitialColumnSetup")
        )
        bank_text, address_text = symbol_line.split()[0].split(":")
        bank, address = int(bank_text, 16), int(address_text, 16)
        self.assertEqual((bank, address), (0x1B, 0x8080))

        image = (ROOT / "src/main.bin").read_bytes()
        offset = bank * 0x8000 + (address & 0x7FFF)
        code = image[offset:offset + 64]
        self.assertTrue(code.startswith(bytes((
            0xE2, 0x20,             # SEP #$20
            0xA9, 0x80,             # LDA #$80
            0x8F, 0x15, 0x21, 0x00, # STA.l $002115
        ))))
        self.assertIn(bytes((0x22, 0x84, 0x82, 0x09, 0x6B)), code)
        self.assertIn("jsl Core_StreamCache_InitialColumnSetup",
                      (ROOT / "src/main.pasm").read_text())

    def test_mode_flags_do_not_overlap_scroll_window_state(self):
        cache = ROOT / "src/core/stream_cache.pasm"
        main = ROOT / "src/main.pasm"
        scroll = [
            symbol_address(main, "StreamScroll_Enabled"),
            symbol_address(main, "StreamScroll_StagedLo"),
        ]
        flags = [
            symbol_address(cache, "StreamCache_NormalLayout"),
            symbol_address(cache, "StreamCache_BG2Capacity"),
            symbol_address(cache, "StreamCache_LegacyFpActive"),
        ]
        self.assertTrue(set(flags).isdisjoint(scroll))
        self.assertEqual(scroll, [0x7E2521, 0x7E2522])


if __name__ == "__main__":
    unittest.main()
