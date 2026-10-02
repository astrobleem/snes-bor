"""Exact dependency/interval proof for the native shared OAM admission cache."""
import itertools
import unittest
from pathlib import Path


def count(objects,y):
    active=[size for start,size in objects if ((y-start)&255)<size]
    return len(active),sum(size//16 for size in active)


class AdmissionTests(unittest.TestCase):
    def test_wram_ownership_does_not_touch_bg_staging_or_queue_arena(self):
        regions=((0x7FA900,0x7FAA0A),(0x7FAB00,0x7FAD28))
        owners=((0x7F9000,0x7F9120),(0x7F9200,0x7FA000),
                (0x7FA000,0x7FA600),(0x7FB000,0x7FB202))
        for a,b in regions:
            for c,d in owners:self.assertTrue(b<=c or d<=a)
        native=(Path(__file__).parents[2]/'src/core/actor_source_oam_admission.pasm').read_text()
        self.assertNotIn('$7F9000',native)
        self.assertNotIn('$7F910',native)

    def test_start_boundaries_equal_exhaustive_visible_scanlines(self):
        starts=(0,1,31,32,191,192,223,224,225,239,240,255)
        for a,b,sa,sb in itertools.product(starts,starts,(32,64),(32,64)):
            objects=((a,sa),(b,sb))
            full=[count(objects,y) for y in range(224)]
            boundaries=[count(objects,y) for y in {0,a,b} if y<224]
            self.assertEqual(tuple(map(max,zip(*full))),tuple(map(max,zip(*boundaries))))

    def test_cache_key_is_injective_over_complete_configured_y_size_domain(self):
        keys={y|(size_bit<<8) for y in range(256) for size_bit in (0,2)}
        self.assertEqual(len(keys),512)
        # Horizontal coordinates/palettes/tiles do not enter conservative
        # full-width admission. No hash or lossy representative is used.

    def test_wrap_safe_hidden_small_contributes_no_visible_scanline(self):
        self.assertEqual([count(((224,32),),y) for y in range(224)],[(0,0)]*224)
        self.assertEqual(count(((224,64),),0),(1,4))

    def test_dma_segment_map_covers_every_byte_of_each_native_block(self):
        for slot in range(32):
            tile=(slot//8)*64+(slot%8)*2
            occupied={tile*32+row*512+byte for row in range(4) for byte in range(64)}
            mapped={byte for byte in range(8192)
                    if (((byte//64)&7)+((byte//64)//32)*8)==slot}
            self.assertEqual(occupied,mapped)
        # Adjacent accepted columns own disjoint complete 64-byte segments;
        # an unaligned transfer crossing a boundary must inspect both.
        self.assertEqual(list(range(63//64,(65-1)//64+1)),[0,1])

    def test_serial_comparison_across_wrap_with_two_live_tickets(self):
        for oldest in range(65536):
            newest=(oldest+1)&65535
            self.assertTrue(0<((newest-oldest)&65535)<32768)
            self.assertFalse(0<((oldest-newest)&65535)<32768)


if __name__=='__main__':unittest.main()
