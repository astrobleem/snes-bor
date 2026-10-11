import unittest
from raster_word_cache_repair import repair
from raster_slot_greedy import demand


class WordCacheRepairTests(unittest.TestCase):
    def fixture(self):
        from test_raster_word_bank_balance import WordBankBalanceTests
        return WordBankBalanceTests().fixture()

    def test_bank_repair_admits_static_words_and_rejects_overfull_bank(self):
        source,initial=self.fixture();forced={c:[0]for c in range(16)}
        rejected=repair(source,initial,forced,time_limit=5,write_budget=0,window=1)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        self.assertFalse(rejected['universal_raster_rejected'])
        forced[15]=[1]
        result=repair(source,initial,forced,time_limit=5,write_budget=0,window=1)
        self.assertEqual(result['joint_word_cache_repair']['status'],'JOINT_WORD_BANK_CACHE_AND_OPERAND_IDENTITIES_PROVEN')
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertEqual(result['geometry']['oam_entries'],4)
        self.assertFalse(result['joint_word_cache_repair']['physical_transfer_admitted'])
        self.assertFalse(result['joint_word_cache_repair']['native_timing_admitted'])
        def pixels(s):return{(p['actor'],p['y']+y,p['x']+x):int(c)for p,image in zip(s['pieces'],demand(s)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(result))

    def test_reload_schedule_replays_fixed_oam_and_zero_lookahead(self):
        source,initial=self.fixture()
        result=repair(source,initial,{c:[0]for c in range(16)},time_limit=5,write_budget=1,window=1,lookahead=0,maximum_oam=2)
        self.assertEqual(result['peak_scheduled_writes'],1)
        self.assertEqual(result['maximum_noninitial_prefetch_latency_lines'],0)
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertTrue(all(p['bank']==0 for p in result['pieces']))
        self.assertTrue(result['joint_word_cache_repair']['independent_cache_and_partition_replay'])
        demand(result)

    def test_illegal_alternatives_and_resource_bounds_reject(self):
        source,initial=self.fixture()
        for alternatives in({0:[4]},{0:[]},{99:[0]}):
            with self.assertRaisesRegex(ValueError,'ALTERNATIVES'):repair(source,initial,alternatives)
        with self.assertRaisesRegex(ValueError,'DOMAIN'):repair(source,initial,{},maximum_oam=129)

    def test_serialized_hint_replays_and_wrong_pixel_hint_rejects(self):
        import copy,json
        from raster_global_bank_classes import rebuild_schedule
        source,initial=self.fixture();hint=json.loads(json.dumps(rebuild_schedule(source,initial)))
        result=repair(source,initial,{15:[1]},time_limit=5,write_budget=1,window=33,residency_hint=hint)
        self.assertTrue(result['joint_word_cache_repair']['independent_cache_and_partition_replay'])
        bad=copy.deepcopy(hint);bad['piece_pixel_masks'][0]['pixels_hex']='00'+bad['piece_pixel_masks'][0]['pixels_hex'][2:]
        with self.assertRaisesRegex(ValueError,'HINT_IDENTITY'):repair(source,initial,{},residency_hint=bad)


if __name__=='__main__':unittest.main()
