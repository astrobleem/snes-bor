import copy
import itertools
import unittest

import numpy as np
from raster_physical_event_delete import optimize, rebuild
from raster_slot_refine import verify_packets
import test_raster_slot_layout as fixtures


class EventDeleteTests(unittest.TestCase):
    def fixture(self):
        source = fixtures.SlotLayoutTests().schedule()
        selected = {(y, i) for y, row in enumerate(source['trace']) if y
                    for i in range(len(row['updates']))}
        return rebuild(source, selected)

    def test_required_reload_and_opaque_black_cannot_be_deleted(self):
        source = self.fixture()
        before = copy.deepcopy(source)
        result = optimize(source, 3)
        self.assertEqual(source, before)
        self.assertEqual(result['physical_event_delete']['solver_status'], 'OPTIMAL')
        self.assertEqual(result['physical_event_delete']['removed_events'], [])
        self.assertEqual(result['physical_event_delete']['peak_prepared_commit_span'], 40)
        self.assertEqual(result['physical_event_delete']['restricted_peak_commit_span_lower_bound'], 40)
        self.assertFalse(result['physical_event_delete']['physical_witness'])

    def test_cancelled_excursion_deleted_as_a_pair_and_matches_exhaustive_subsets(self):
        source = self.fixture()
        # Slot 1 is read only before and after a green -> red excursion.
        image = np.zeros((8, 8), dtype=np.uint8)
        image[[0, 3], 0] = 1
        flat = image.flatten()
        source['piece_pixel_masks'][0]['pixels_hex'] = (flat[::2] | flat[1::2] << 4).tobytes().hex()
        keys = [(y, i) for y, row in enumerate(source['trace']) if y for i in range(len(row['updates']))]
        exhaustive = []
        for bits in itertools.product((False, True), repeat=len(keys)):
            chosen = {key for key, bit in zip(keys, bits) if bit}
            try:
                candidate = rebuild(source, chosen)
            except (AssertionError, ValueError):
                continue
            exhaustive.append((max(r['prepared_commit_span'] for r in candidate['prepared_dma_packets']), len(chosen)))
        result = optimize(source, 3)
        report = result['physical_event_delete']
        self.assertEqual((report['peak_prepared_commit_span'], report['retained_noninitial_events']), min(exhaustive))
        self.assertEqual(len(report['removed_events']), 2)
        self.assertEqual(result['pieces'], source['pieces'])
        self.assertEqual(result['piece_pixel_masks'], source['piece_pixel_masks'])
        verify_packets(result)

    def test_dead_tail_load_deleted_but_packet_corruption_rejected(self):
        source = self.fixture()
        source['trace'][4]['updates'].append(dict(bank=0, slot=1, old=31, color=1024))
        for row in source['trace'][5:]:
            row['resident_before'][0][0] = 1024
        keys = {(y, i) for y, row in enumerate(source['trace']) if y for i in range(len(row['updates']))}
        source = rebuild(source, keys)
        result = optimize(source, 3)
        self.assertEqual([e['scanline'] for e in result['physical_event_delete']['removed_events']], [4])
        result['prepared_dma_packets'][1]['packets'][0]['data_hex'] = '0000'
        with self.assertRaisesRegex(ValueError, 'PACKET_IDENTITY'):
            verify_packets(result)

    def test_time_cap_enforced(self):
        with self.assertRaisesRegex(ValueError, 'TIME_LIMIT'):
            optimize({}, 121)


if __name__ == '__main__':
    unittest.main()
