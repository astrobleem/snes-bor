import unittest
from source_hit_state_layout import layout
from source_pending_jump_layout import layout as jumps


class HitStateLayoutTests(unittest.TestCase):
    def test_every_capacity_retains_every_conversion_tile(self):
        for entities in range(1,129):
            p=layout(entities);j=jumps(entities)
            self.assertEqual(p['base']+entities*16,j['base'])
            self.assertEqual(p['controls']+64,p['base'])
            self.assertEqual(p['chr_capacity']+p['persistent_bytes'],j['chr_capacity'])
            for job,count in ((0,896),(1,512)):
                ds=[d for d in p['conversion_descriptors']if d['job']==job]
                self.assertEqual(sum(d['tile_count']for d in ds),count)
                self.assertEqual([d['tile_offset']for d in ds],[sum(x['tile_count']for x in ds[:i])for i in range(len(ds))])
                for d in ds:self.assertLessEqual(d['source']+d['bytes'],p['controls'])
            self.assertFalse(p['production_memory_lease'])

    def test_full_pool_boundaries(self):
        p=layout();self.assertEqual((p['controls'],p['base'],p['end']),(0x42c3c0,0x42c400,0x42cc00))
        self.assertEqual(p['chr_capacity'],50112)
        self.assertEqual(p['persistent_bytes'],2112)

    def test_invalid_pool_sizes_reject(self):
        for n in (0,129,-1):
            with self.assertRaises(ValueError):layout(n)


if __name__=='__main__':unittest.main()
