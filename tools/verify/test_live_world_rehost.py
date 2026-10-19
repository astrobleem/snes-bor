"""Check the full-pool private storage plan and reject aliased callback work."""
import unittest
from pathlib import Path
import sys

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'bor_compile')]
from source_pending_jump_layout import rehost as jumps
from source_hit_state_layout import rehost as hits
from source_move_contact_layout import rehost as moves
from source_check_move_callback_native import emit


class LiveWorldRehostTests(unittest.TestCase):
    def test_full_pool_rows_fit_retired_video_and_exclude_renderer(self):
        jp,hp,mp=jumps(),hits(),moves()
        ranges=[(jp['base'],jp['end']),(hp['base'],hp['end']),
                (hp['controls'],hp['controls']+64),(0x7e7680,0x7e7700),
                (0x7e7700,0x7e7780),(0x7e7800,0x7e7892),
                (0x7e7a00,0x7e7c00),(mp['base'],mp['end']),
                (mp['controls'],mp['controls']+64),(0x7e8080,0x7e80e0)]
        for begin,end in ranges:
            self.assertTrue(0x7e6200<=begin<end<=0x7e8100)
            self.assertFalse(begin<0x42d800 and 0x42c000<end)
        ordered=sorted(ranges)
        for left,right in zip(ordered,ordered[1:]):
            self.assertLessEqual(left[1],right[0])
        for p,stride in ((jp,24),(hp,16),(mp,8)):
            self.assertEqual(p['entities'],128)
            self.assertEqual(p['end']-p['base'],128*stride)
            self.assertFalse(p['production_memory_lease'])
            self.assertEqual(p['conversion_descriptors'],[])
            self.assertIsNone(p['chr_workspace'])

    def test_bad_geometry_cannot_lease_other_memory(self):
        for make in (jumps,hits,moves):
            for base in (0x42c000,0x7e6100,0x7e6201,0x7e9a60):
                with self.assertRaises(ValueError):make(base=base)
            for count in (0,129):
                with self.assertRaises(ValueError):make(entities=count)

    def test_rehosted_callback_cannot_reuse_identity_or_movement_rows(self):
        # Work-alias rejection precedes any symbol/source emission. Actual
        # wrapper must use its separately reserved, full 96-byte work block.
        hp,mp=hits(),moves()
        for base in (hp['base'],hp['controls'],mp['base'],mp['controls'],
                     hp['base']-94,mp['controls']+62):
            with self.assertRaisesRegex(ValueError,'WORK_OVERLAP'):
                emit({},mp,dict(SOURCE_FOREIGN_WORK_BASE=0x7fa000,
                     SOURCE_FOREIGN_WORK_BYTES=6400),flat_work=base,include_identities=False)


if __name__=='__main__':unittest.main()
