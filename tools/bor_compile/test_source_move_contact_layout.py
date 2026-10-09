import unittest
from source_move_contact_layout import layout
from source_hit_contact_layout import layout as pain


class MoveContactLayoutTests(unittest.TestCase):
    def test_all_pool_extents_keep_existing_rows_and_full_conversion(self):
        for n in range(1,129):
            p=layout(n);neighbor=pain(n)
            self.assertEqual(p['end'],neighbor['controls'])
            self.assertEqual(p['base']+8*n,p['end'])
            self.assertEqual(p['controls']+64,p['base'])
            self.assertEqual(p['chr_capacity']+p['additional_persistent_bytes'],neighbor['chr_capacity'])
            for job,count in ((0,896),(1,512)):
                descriptors=[d for d in p['conversion_descriptors'] if d['job']==job]
                self.assertEqual(sum(d['tile_count'] for d in descriptors),count)
                for i,d in enumerate(descriptors):
                    self.assertEqual(d['tile_offset'],sum(x['tile_count'] for x in descriptors[:i]))
                    self.assertLessEqual(d['source']+d['bytes'],p['controls'])
            self.assertFalse(p['production_memory_lease'])

    def test_full_pool_boundary_and_source_field_types(self):
        p=layout()
        self.assertEqual((p['controls'],p['base'],p['end']),(0x42BB40,0x42BB80,0x42BF80))
        self.assertEqual(p['chr_capacity'],47936)
        self.assertEqual(p['field_types'],dict(pathblocked='uint32',grabwalking='int32'))

    def test_invalid_counts_reject(self):
        for n in (-1,0,129):
            with self.assertRaises(ValueError):layout(n)
