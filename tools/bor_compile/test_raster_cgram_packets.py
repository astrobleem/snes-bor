import unittest
from raster_cgram_packets import packetize_row,compile_packets,optimistic_dma_span


class CgramPacketTests(unittest.TestCase):
    def test_dma_span_bound_can_bridge_transparent_zero_between_banks(self):
        updates=[dict(bank=b)for b in (0,0,1,1)]
        r=optimistic_dma_span(updates)
        self.assertEqual(r['first_to_last_data_write_master_clocks'],72)
        self.assertEqual(r['best_partition_range_count'],1)
        self.assertEqual(r['ranges'][0]['data_words'],5)

    def test_dma_span_bound_separated_banks_need_destination_switch(self):
        r=optimistic_dma_span([dict(bank=0),dict(bank=7)])
        self.assertEqual(r['first_to_last_data_write_master_clocks'],48)
        self.assertEqual(r['best_partition_range_count'],2)
        self.assertEqual(r['best_partition_chain_dma_channels'],3)

    def row(self,slots,updates):
        before={b:[None]*15 for b in range(8)}
        for b,s,c in slots:before[b][s-1]=c
        return dict(scanline=100,resident_before=before,
                    updates=[dict(bank=b,slot=s,color=c,old=before[b][s-1])for b,s,c in updates])

    def test_contiguous_slots_are_little_endian_and_banks_stay_separate(self):
        row=self.row([],[(0,14,31),(0,15,992),(1,1,31744)])
        r=packetize_row(row)
        self.assertEqual([p['cgram_word_address']for p in r['packets']],[142,145])
        self.assertEqual(r['packets'][0]['data_hex'],'1f00e003')
        self.assertEqual(r['transfer_bytes'],8)
        self.assertTrue(r['slot_identity_verified'])

    def test_high_address_cost_can_bridge_known_unchanged_slots(self):
        row=self.row([(4,2,32767)],[(4,1,31),(4,3,0)])
        low=packetize_row(row,1);high=packetize_row(row,3)
        self.assertEqual(low['packet_count'],2)
        self.assertEqual(high['packet_count'],1)
        self.assertEqual(high['packets'][0]['data_hex'],'1f00ff7f0000')
        self.assertEqual(high['packets'][0]['bridged_unchanged_slots'],[2])

    def test_unknown_gap_cannot_be_written_even_with_high_address_cost(self):
        r=packetize_row(self.row([],[(7,1,0),(7,3,10)]),100)
        self.assertEqual(r['packet_count'],2)

    def test_stale_and_duplicate_updates_and_color_zero_slots_rejected(self):
        for field,value in [('old',3),('slot',0),('color',32768)]:
            row=self.row([],[(0,1,31)]);row['updates'][0][field]=value
            with self.assertRaises(ValueError):packetize_row(row)
        row=self.row([],[(0,1,31)]);row['updates']*=2
        with self.assertRaises(ValueError):packetize_row(row)

    def test_empty_row_needs_no_packet(self):
        self.assertEqual(packetize_row(self.row([],[]))['transfer_bytes'],0)

    def test_scanline_continuity_includes_unchanged_residents(self):
        first=self.row([],[(0,1,31)]);first['scanline']=0
        second=self.row([(0,1,31)],[]);second['scanline']=1
        schedule=dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',
                      compiled_pixel_identity_verified=True,no_color_reduction=True,
                      source_rgb555_sha256='0'*64,trace=[first,second])
        r=compile_packets(schedule)
        self.assertEqual(r['peak_transfer_bytes'],0)
        self.assertEqual(r['initial_vblank']['transfer_bytes'],3)
        self.assertFalse(r['native_timing_admitted'])
        second['resident_before'][0][0]=0
        with self.assertRaises(ValueError):compile_packets(schedule)

    def test_unvalidated_schedule_is_rejected(self):
        with self.assertRaises(ValueError):compile_packets(dict(status='BOUNDED_JOINT_SOLVER_NO_CANDIDATE'))


if __name__=='__main__':unittest.main()
