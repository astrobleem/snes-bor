import copy,unittest
import numpy as np
from raster_physical_suffix_reindex import reindex
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_obj_compact import unpack
import test_raster_slot_layout as fixtures


class SuffixReindexTests(unittest.TestCase):
    def test_reindexed_bitplanes_keep_source_words_banks_and_geometry(self):
        source=fixtures.SlotLayoutTests().schedule()
        for row in source['trace']:
            values=row['resident_before'][0];values[13],values[0]=values[0],None
            values=row['resident_before'][1];values[0]=None if values[2]is None else 1024;values[2]=None
            for e in row['updates']:
                if e['bank']==0:e['slot']=14
                else:e['slot']=1;e['color']=1024
        for p,mask in zip(source['pieces'],source['piece_pixel_masks']):
            image=unpack(mask);image[image!=0]=14 if p['bank']==0 else 1;flat=image.flatten();mask['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        source['physical_slot_layout']=dict(all_packet_cgram_identities_verified=True)
        source['prepared_dma_packets']=[dict(scanline=y,packets=[],prepared_commit_span=0)for y in range(16)]
        source['prepared_dma_packets'][1]['packets']=[dict(cgram_word_address=142,word_count=1,data_hex='e003')]
        source['prepared_dma_packets'][2]=dict(scanline=2,packets=[dict(cgram_word_address=142,word_count=1,data_hex='1f00'),dict(cgram_word_address=145,word_count=1,data_hex='0004')],prepared_commit_span=40)
        before=copy.deepcopy(source);result=reindex(source,time_limit=5,target_window=33)
        self.assertEqual(source,before);self.assertEqual(source['pieces'],result['pieces'])
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertEqual(result['physical_slot_layout']['peak_prepared_commit_span'],32)
        self.assertNotEqual(source['piece_pixel_masks'],result['piece_pixel_masks'])
        self.assertTrue(result['physical_slot_layout']['all_live_slot_relocation_writes_charged'])
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])

    def test_invalid_search_limits_rejected(self):
        with self.assertRaisesRegex(ValueError,'SUFFIX_REINDEX_DOMAIN'):reindex({},radius=-1)

    def test_annealing_retains_only_best_complete_source_exact_state(self):
        import test_raster_physical_event_schedule as event_fixtures
        source=event_fixtures.PhysicalEventScheduleTests().schedule()
        source['trace'][2]['updates'][1]['color']=1024
        source['prepared_dma_packets'][2]['packets'][1]['data_hex']='0004'
        for row in source['trace'][3:]:row['resident_before'][1][2]=1024
        before=copy.deepcopy(source)
        result=reindex(source,time_limit=5,iterations=1,radius=4,target_window=1,anneal_steps=200,seed=630)
        self.assertEqual(source,before);self.assertEqual(source['pieces'],result['pieces'])
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        report=result['physical_slot_layout']
        self.assertGreater(report['anneal_proposals'],0)
        self.assertLessEqual(tuple(report['final_score']),tuple(report['initial_score']))
        self.assertFalse(report['native_timing_admitted'])


if __name__=='__main__':unittest.main()
