import itertools
import unittest

import numpy as np

from raster_physical_event_delete import rebuild
import test_raster_slot_layout as fixtures
from verify_raster_event_delete import exact_partition, mandatory_certificate, physical_rows, slot_requirements


class IndependentDeleteTests(unittest.TestCase):
    def fixture(self):
        source = fixtures.SlotLayoutTests().schedule()
        keys = {(y, i) for y, row in enumerate(source['trace']) if y for i in range(len(row['updates']))}
        return rebuild(source, keys)

    def test_required_event_certificate_matches_intersection_of_all_valid_subsets(self):
        source = self.fixture()
        rows, _ = physical_rows(source)
        keys = {(y, i) for y, row in enumerate(source['trace']) if y for i in range(len(row['updates']))}
        intersection = keys.copy()
        for bits in itertools.product((False, True), repeat=len(keys)):
            selected = {key for key, bit in zip(sorted(keys), bits) if bit}
            try:
                rebuild(source, selected)
            except (AssertionError, ValueError):
                continue
            intersection &= selected
        certificate = mandatory_certificate(source, slot_requirements(source, rows))
        self.assertEqual({(e['scanline'], e['update_index']) for e in certificate['mandatory_events']}, intersection)
        self.assertEqual(certificate['independently_certified_peak_lower_bound'], 40)

    def test_cancelled_pair_is_optional_only_when_both_deletions_are_considered(self):
        source = self.fixture()
        image = np.zeros((8, 8), dtype=np.uint8)
        image[[0, 3], 0] = 1
        flat = image.flatten()
        source['piece_pixel_masks'][0]['pixels_hex'] = (flat[::2] | flat[1::2] << 4).tobytes().hex()
        rows, _ = physical_rows(source)
        certificate = mandatory_certificate(source, slot_requirements(source, rows))
        self.assertEqual({(e['scanline'], e['bank'], e['slot']) for e in certificate['optional_events']},
                         {(1, 0, 1), (2, 0, 1)})
        self.assertEqual(len(certificate['mandatory_events']), 1)

    def test_byte_latch_replay_rejects_changed_unused_resident_word(self):
        source = self.fixture()
        rows, _ = physical_rows(source)
        self.assertEqual(rows[2][147], 0)  # Opaque black stays a referenced word.
        source['prepared_dma_packets'][2]['packets'][-1]['data_hex'] = '0100'
        with self.assertRaisesRegex(ValueError, 'FULL_CGRAM_IDENTITY'):
            physical_rows(source)

    def test_exhaustive_partition_critical_row(self):
        points = [31, 40, 41, 61, 62, 63, 66, 67, 69, 71, 72, 76, 77, 81, 103, 104]
        self.assertEqual(exact_partition(points)[0], 472)
        self.assertEqual(exact_partition([]), (0, []))


if __name__ == '__main__':
    unittest.main()
