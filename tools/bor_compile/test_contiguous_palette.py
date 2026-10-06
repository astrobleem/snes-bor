import unittest
from contiguous_palette import attempt


class ContiguousPaletteTests(unittest.TestCase):
    def test_residency_preload_and_opaque_black(self):
        r=attempt([{0},{1},{2},{0,2}],3,1)
        self.assertEqual(r['status'],'CONTIGUOUS_BURST_SCHEDULE_PROVEN')
        self.assertEqual(r['peak_cgram_data_bytes'],2)
        self.assertEqual(sum(len(t['values']) for t in r['trace'][1:]),0)
        self.assertTrue(all(set(line)<=set(state) for line,state in zip([{0},{1},{2},{0,2}],r['states'])))

    def test_no_single_burst_across_reserved_range(self):
        r=attempt([{1,2},{3,4}],4,3,breaks=(2,))
        self.assertEqual(r['status'],'CONTIGUOUS_HEURISTIC_LIMIT')
        self.assertEqual(r['reason'],'NO_SAFE_SINGLE_BURST_WINDOW')

    def test_invalid_palette_size_rejected(self):
        with self.assertRaises(ValueError):attempt([{0}],256,2)

    def test_previous_frame_slots_retain_identity_and_vblank_admits_line_zero(self):
        lines=[{3},{1,3},{1,2}]
        r=attempt(lines,3,1,initial_slots=[1,2,99])
        self.assertEqual(r['status'],'CONTIGUOUS_BURST_SCHEDULE_PROVEN')
        self.assertEqual(r['states'][0],[1,2,3])
        self.assertEqual(sum(t['data_bytes'] for t in r['trace'][1:]),0)
        r=attempt(lines,3,1,initial_slots=[1,2,4])
        self.assertTrue(all(set(line)<=set(state) for line,state in zip(lines,r['states'])))

    def test_duplicate_initial_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_IDENTITY'):
            attempt([{1},{2}],3,1,initial_slots=[1,1,2])


if __name__=='__main__':unittest.main()
