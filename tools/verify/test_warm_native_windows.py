"""Synthetic timing-contract tests for warm-native presentation windows."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warm_native_windows as windows


def point(name: str, clock: int, frame: int = 10) -> str:
    # The real observer appends CPU/owner state after the three timing fields.
    return "WARMPOINT|" + "|".join([name, str(clock), str(frame)] + ["0"] * 29)


def ppu(kind: str, clock: int, frame: int) -> str:
    return f"WARMPPU|{kind}|{clock}|{frame}"


def sample(*, margin: int = 12000, partial_edges: bool = False) -> str:
    start, end = 1000, 60000
    batch_start, batch_end = 5000, end - margin
    map_start, map_end = 26000, 30000
    rows = []
    if partial_edges:
        rows.append(ppu("VBLANK_END", 500, 10))
    rows.append(ppu("VBLANK_START", start, 10))
    rows += [point("WarmRenderer_NbQueueHasPending", batch_start),
             point("WarmRenderer_NbPairBegin", batch_start + 100),
             point("WarmRenderer_NbPairComplete", batch_start + 1000),
             point("WarmRenderer_NbQueueDrainDone", batch_end),
             point("WarmRenderer_NbMapCommit", map_start),
             point("WarmRenderer_NbMapsComplete", map_end)]
    rows.append(ppu("VBLANK_END", end, 11))
    if partial_edges:
        rows.append(ppu("VBLANK_START", 61000, 11))
    return "\n".join(rows)


class WarmNativeWindowsTests(unittest.TestCase):
    def test_accepts_complete_batch_and_maps_inside_measured_blank(self):
        result = windows.analyze(sample())
        self.assertTrue(result["accepted"], result["errors"])
        self.assertEqual(result["batches"][0]["dma_pairs"], 1)
        self.assertEqual(result["batches"][0]["margin_clocks"], 12000)
        self.assertEqual(result["maps"][0]["margin_clocks"], 30000)

    def test_allows_only_edge_partial_vblank_boundaries(self):
        result = windows.analyze(sample(partial_edges=True))
        self.assertTrue(result["accepted"], result["errors"])
        self.assertEqual(result["leading_or_trailing_partial_boundaries"], 2)

    def test_queue_staging_may_precede_vblank_but_dma_must_fit(self):
        raw = sample().replace(ppu("VBLANK_START", 1000, 10) + "\n" +
                               point("WarmRenderer_NbQueueHasPending", 5000),
                               point("WarmRenderer_NbQueueHasPending", 500) + "\n" +
                               ppu("VBLANK_START", 1000, 10))
        result = windows.analyze(raw)
        self.assertTrue(result["accepted"], result["errors"])
        self.assertEqual(result["batches"][0]["queued_clock"], 500)

    def test_empty_or_missing_timing_evidence_never_accepts(self):
        for raw in ("", ppu("VBLANK_START", 1, 1) + "\n" + ppu("VBLANK_END", 2, 2)):
            with self.subTest(raw=raw):
                result = windows.analyze(raw)
                self.assertFalse(result["accepted"])
                self.assertTrue(result["errors"])

    def test_rejects_active_or_unmatched_dma(self):
        raw = sample().replace(point("WarmRenderer_NbPairComplete", 6000) + "\n", "")
        result = windows.analyze(raw)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("active DMA" in e or "completion" in e for e in result["errors"]))

    def test_rejects_completion_outside_full_vblank_even_with_partial_edge(self):
        raw = sample(partial_edges=True).replace(
            point("WarmRenderer_NbQueueDrainDone", 48000),
            point("WarmRenderer_NbQueueDrainDone", 550))
        result = windows.analyze(raw)
        self.assertFalse(result["accepted"])

    def test_rejects_insufficient_end_margin(self):
        result = windows.analyze(sample(margin=9999))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("10000-clock" in e for e in result["errors"]))

    def test_rejects_ppu_frame_mismatch(self):
        raw = sample().replace(point("WarmRenderer_NbMapsComplete", 30000),
                               point("WarmRenderer_NbMapsComplete", 30000, frame=12))
        result = windows.analyze(raw)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("frame mismatch" in e for e in result["errors"]))

    def test_rejects_pair_completion_clock_outside_batch(self):
        raw = sample().replace(point("WarmRenderer_NbPairComplete", 6000),
                               point("WarmRenderer_NbPairComplete", 49000))
        result = windows.analyze(raw)
        self.assertFalse(result["accepted"])

    def test_rejects_cross_vblank_batch(self):
        raw = "\n".join([
            ppu("VBLANK_START", 1000, 10),
            point("WarmRenderer_NbQueueHasPending", 2000),
            point("WarmRenderer_NbPairBegin", 3000),
            point("WarmRenderer_NbPairComplete", 4000),
            ppu("VBLANK_END", 20000, 11),
            ppu("VBLANK_START", 21000, 11),
            point("WarmRenderer_NbQueueDrainDone", 22000),
            point("WarmRenderer_NbMapCommit", 23000),
            point("WarmRenderer_NbMapsComplete", 24000),
            ppu("VBLANK_END", 50000, 12),
        ])
        result = windows.analyze(raw)
        self.assertFalse(result["accepted"])

    def test_rejects_missing_map_pair_and_duplicate_boundary(self):
        no_map = "\n".join(line for line in sample().splitlines()
                             if "NbMap" not in line and "NbMaps" not in line)
        self.assertFalse(windows.analyze(no_map)["accepted"])
        duplicate = sample().replace(ppu("VBLANK_END", 60000, 11),
                                     ppu("VBLANK_END", 60000, 11) + "\n" +
                                     ppu("VBLANK_END", 60001, 11))
        self.assertFalse(windows.analyze(duplicate)["accepted"])

    def test_rejects_reordered_boundaries_instead_of_sorting_them(self):
        raw = sample() + "\n" + ppu("VBLANK_START", 100, 1)
        self.assertFalse(windows.analyze(raw)["accepted"])

    def test_missing_end_and_following_start_cannot_create_a_long_false_vblank(self):
        raw = sample().replace(ppu("VBLANK_END", 60000, 11),
                               ppu("VBLANK_END", 400000, 12))
        self.assertFalse(windows.analyze(raw)["accepted"])


if __name__ == "__main__":
    unittest.main()
