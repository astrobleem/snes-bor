import copy,unittest
import numpy as np
from raster_physical_write_shift import shift
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
import test_raster_slot_layout as fixtures


class PhysicalWriteShiftTests(unittest.TestCase):
    def test_unused_slot_preloads_without_changing_indices_or_referenced_colors(self):
        source=fixtures.SlotLayoutTests().schedule()
        source['physical_slot_layout']=dict(all_packet_cgram_identities_verified=True)
        source['prepared_dma_packets']=[dict(scanline=y,packets=[],prepared_commit_span=0)for y in range(16)]
        source['prepared_dma_packets'][1]['packets']=[dict(cgram_word_address=129,word_count=1,data_hex='e003')]
        source['prepared_dma_packets'][2]=dict(scanline=2,packets=[dict(cgram_word_address=129,word_count=1,data_hex='1f00'),dict(cgram_word_address=147,word_count=1,data_hex='0000')],prepared_commit_span=40)
        before=copy.deepcopy(source)
        result=shift(source,lookahead=0,target_window=1)
        self.assertEqual(source,before)
        self.assertEqual(source['pieces'],result['pieces'])
        self.assertEqual(source['piece_pixel_masks'],result['piece_pixel_masks'])
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertEqual(result['physical_slot_layout']['peak_prepared_commit_span'],0)
        self.assertTrue(any(m['to_scanline']==0 and m['color']==0 for m in result['physical_slot_layout']['moves']))
        self.assertEqual([(e['color'],row['scanline'])for row in result['trace']for e in row['updates']if e['bank']==0],[(31,0),(992,1),(31,2)])
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])

    def test_invalid_liveness_domain_rejected(self):
        with self.assertRaisesRegex(ValueError,'WRITE_SHIFT_DOMAIN'):shift({},lookahead=-1)

    def test_prefetch_can_move_later_without_crossing_first_required_pixel(self):
        source=fixtures.SlotLayoutTests().schedule()
        source['trace'][0]['updates'].append(dict(bank=1,slot=3,old=None,color=0))
        for y in range(1,16):source['trace'][y]['resident_before'][1][2]=0 if y<=2 else 1024
        source['trace'][2]['updates'][1].update(old=0,color=1024)
        image=np.zeros((8,8),dtype=np.uint8);image[[0,1,5],0]=3;flat=image.flatten()
        source['piece_pixel_masks'][1]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        source['physical_slot_layout']=dict(all_packet_cgram_identities_verified=True)
        source['prepared_dma_packets']=[dict(scanline=y,packets=[],prepared_commit_span=0)for y in range(16)]
        source['prepared_dma_packets'][1]['packets']=[dict(cgram_word_address=129,word_count=1,data_hex='e003')]
        source['prepared_dma_packets'][2]=dict(scanline=2,packets=[dict(cgram_word_address=129,word_count=1,data_hex='1f00'),dict(cgram_word_address=147,word_count=1,data_hex='0004')],prepared_commit_span=40)
        result=shift(source,lookahead=3,target_window=1)
        self.assertTrue(any(m['from_scanline']==2 and 2<m['to_scanline']<=5 for m in result['physical_slot_layout']['moves']))
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)


if __name__=='__main__':unittest.main()
