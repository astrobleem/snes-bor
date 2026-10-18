"""Independent pixel-oracle tests for the exact coverage fast path."""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))

from exact_coverage import fast_coverage, transform


def _boolean_fixture():
    return [
        'NbMarkTest:', '.a16', '.i16', ' lda.l $42D674',
        ' beq NbUseSourcePresence', ' jsr OnlineCoverage',
        ' bra NbPresenceChecked', 'NbUseSourcePresence:', '.a16', '.i16',
        ' jsr WarmSourcePresence', 'NbPresenceChecked:', '.a16', '.i16',
        ' cmp #0', ' beq NbMarkNext', ' lda $18', 'NbMarkNext:',
        ' rts', 'OnlineCoverage:', ' rts',
    ]


def _projected_overlap(source, foreground, origin_x, origin_y):
    """Build eight row words by per-pixel world-coordinate comparison.

    Both images are 8x8. Their world origins can be offset by -7..7 on each
    axis, so every possible partial alignment is represented.
    """
    words = []
    for sy in range(8):
        word = 0
        for sx in range(8):
            if not source[sy][sx]:
                continue
            wx, wy = origin_x + sx, origin_y + sy
            if not (0 <= wx < 8 and 0 <= wy < 8):
                continue
            # Foreground 1-bits are opaque and occlude the projected source.
            if not foreground[wy][wx]:
                word |= 1 << sx
        words.append(word)
    return words


def _pixel_oracle(source, foreground, origin_x, origin_y):
    for sy in range(8):
        for sx in range(8):
            wx, wy = origin_x + sx, origin_y + sy
            if (source[sy][sx] and 0 <= wx < 8 and 0 <= wy < 8
                    and not foreground[wy][wx]):
                return True
    return False


class ExactCoverageTests(unittest.TestCase):
    def test_fast_coverage_matches_pixel_oracle_for_every_alignment(self):
        # Deterministic, non-periodic masks include transparent source pixels
        # and foreground holes while keeping this exhaustive alignment sweep
        # fast and reproducible.
        source = [[((x * 17 + y * 29 + x * y * 3) % 11) < 5
                   for x in range(8)] for y in range(8)]
        foreground = [[((x * 31 + y * 13 + x * y * 7) % 13) < 6
                       for x in range(8)] for y in range(8)]
        for oy in range(-7, 8):
            for ox in range(-7, 8):
                with self.subTest(origin=(ox, oy)):
                    words = _projected_overlap(source, foreground, ox, oy)
                    got, _ = fast_coverage(words)
                    self.assertEqual(got, _pixel_oracle(source, foreground, ox, oy))

    def test_opaque_and_transparent_and_occluded_pixels(self):
        # A visible corner, its fully transparent counterpart, and a pixel
        # hidden behind an opaque foreground pixel exercise the pixel source.
        source = [[False] * 8 for _ in range(8)]
        foreground = [[False] * 8 for _ in range(8)]
        source[0][0] = True
        foreground[0][0] = False
        self.assertTrue(fast_coverage(_projected_overlap(source, foreground, 0, 0))[0])
        source[0][0] = False
        self.assertFalse(fast_coverage(_projected_overlap(source, foreground, 0, 0))[0])
        source[7][7] = True
        foreground[7][7] = True
        self.assertFalse(fast_coverage(_projected_overlap(source, foreground, 0, 0))[0])

        # Entire source lies outside the 8x8 target for origins at or beyond
        # either edge, despite opaque source and clear foreground pixels.
        source = [[True] * 8 for _ in range(8)]
        foreground = [[False] * 8 for _ in range(8)]
        for ox, oy in ((-8, 0), (8, 0), (0, -8), (0, 8), (-12, 11)):
            with self.subTest(clipped_origin=(ox, oy)):
                words = _projected_overlap(source, foreground, ox, oy)
                self.assertEqual(words, [0] * 8)
                self.assertFalse(fast_coverage(words)[0])
                self.assertFalse(_pixel_oracle(source, foreground, ox, oy))

        # Opaque source pixels fully covered by an opaque foreground produce
        # no visible coverage, while a fully transparent source over a clear
        # foreground also produces no coverage.
        source = [[True] * 8 for _ in range(8)]
        foreground = [[True] * 8 for _ in range(8)]
        words = _projected_overlap(source, foreground, 0, 0)
        self.assertEqual(words, [0] * 8)
        self.assertFalse(fast_coverage(words)[0])
        self.assertFalse(_pixel_oracle(source, foreground, 0, 0))

        source = [[False] * 8 for _ in range(8)]
        foreground = [[False] * 8 for _ in range(8)]
        words = _projected_overlap(source, foreground, 0, 0)
        self.assertEqual(words, [0] * 8)
        self.assertFalse(fast_coverage(words)[0])
        self.assertFalse(_pixel_oracle(source, foreground, 0, 0))

    def test_first_and_last_row_short_circuit_counts(self):
        first = [0] * 8
        first[0] = 0x8000
        self.assertEqual(fast_coverage(first), (True, 1))
        last = [0] * 8
        last[7] = 1
        self.assertEqual(fast_coverage(last), (True, 8))
        self.assertEqual(fast_coverage([0] * 8), (False, 8))

    def test_fast_coverage_rejects_invalid_domains(self):
        invalid = (
            [], [0] * 7, [0] * 9,
            [0] * 7 + [-1], [0] * 7 + [0x10000],
            [0] * 7 + [True], [0] * 7 + [1.0],
        )
        for rows in invalid:
            with self.subTest(rows=rows):
                with self.assertRaises((TypeError, ValueError)):
                    fast_coverage(rows)

    def test_transform_changes_only_pinned_callsite_and_preserves_original_routine(self):
        fixture = [
            "NbMarkTest:",
            "  .a16",
            "  .i16",
            "  lda.l $42D674",
            "  beq NbUseSourcePresence",
            "  jsr OnlineCoverage",
            "  bra NbPresenceChecked",
            "NbUseSourcePresence:",
            "  .a16",
            "  .i16",
            "  jsr WarmSourcePresence",
            "NbPresenceChecked:",
            "  .a16",
            "  .i16",
            "  cmp #0",
            "  beq NbMarkNext",
            "OnlineCoverage:",
            "  ; legacy routine stays available to other callers",
            "  rts",
            "OtherCaller:",
            "  jsr OnlineCoverage",
            "  rts",
        ]
        rewritten = transform(fixture)
        call_index = fixture.index("  jsr OnlineCoverage")
        expected_prefix = fixture.copy()
        expected_prefix[call_index] = "  jsr EcCoverage"
        self.assertEqual(rewritten[:len(fixture)], expected_prefix)
        self.assertTrue(any("A700" in line.upper() for line in rewritten[len(fixture):]))
        self.assertEqual(transform(fixture, enabled=False), fixture)

    def test_transform_fails_closed_for_missing_ambiguous_or_rewritten_anchor(self):
        valid = [
            "NbMarkTest:", "  .a16", "  .i16", "  lda.l $42D674",
            "  beq NbUseSourcePresence", "  jsr OnlineCoverage",
            "  bra NbPresenceChecked", "NbUseSourcePresence:",
            "  .a16", "  .i16", "  jsr WarmSourcePresence",
            "NbPresenceChecked:", "  .a16", "  .i16", "  cmp #0", "  beq NbMarkNext",
        ]
        cases = (
            [line for line in valid if line != "  jsr OnlineCoverage"],
            valid + valid,
            ["NbMarkTest:", "  jsr EcCoverage", "  bra NbPresenceChecked"],
        )
        for fixture in cases:
            with self.subTest(fixture=fixture):
                with self.assertRaises((TypeError, ValueError, RuntimeError)):
                    transform(fixture)

    def test_transform_rejects_changed_branch_semantics(self):
        valid = _boolean_fixture()
        for branch in ('bne NbMarkNext', 'bmi NbMarkNext', 'bpl NbMarkNext',
                       'bvs NbMarkNext', 'beq OtherTarget'):
            altered = [" " + branch if line == ' beq NbMarkNext' else line for line in valid]
            with self.subTest(branch=branch), self.assertRaisesRegex(ValueError, 'EC_PINNED_BOOLEAN_CALLSITE'):
                transform(altered)

    def test_transform_rejects_missing_zero_branch(self):
        altered = [line for line in _boolean_fixture() if line != ' beq NbMarkNext']
        with self.assertRaisesRegex(ValueError, 'EC_PINNED_BOOLEAN_CALLSITE'):
            transform(altered)


if __name__ == "__main__":
    unittest.main()
