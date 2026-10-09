import unittest
from source_hit_contact_layout import layout
from source_hit_state_layout import layout as hits


class ContactLayoutTests(unittest.TestCase):
    def test_all_capacity_tiles_and_fixed_neighbors(self):
        for n in range(1,129):
            p=layout(n);h=hits(n)
            self.assertEqual(p['base']+n*8,h['controls'])
            self.assertEqual(p['controls']+64,p['base'])
            self.assertEqual(p['chr_capacity']+p['additional_persistent_bytes'],h['chr_capacity'])
            for job,count in ((0,896),(1,512)):
                ds=[d for d in p['conversion_descriptors']if d['job']==job]
                self.assertEqual(sum(d['tile_count']for d in ds),count)
                self.assertEqual([d['tile_offset']for d in ds],[sum(x['tile_count']for x in ds[:i])for i in range(len(ds))])
                for d in ds:self.assertLessEqual(d['source']+d['bytes'],p['controls'])
            self.assertFalse(p['production_memory_lease'])
    def test_full_pool_boundary(self):
        p=layout();self.assertEqual((p['controls'],p['base'],p['end']),(0x42bf80,0x42bfc0,0x42c3c0));self.assertEqual(p['chr_capacity'],49024)
    def test_invalid_counts_reject(self):
        for n in (0,129,-1):
            with self.assertRaises(ValueError):layout(n)
