import unittest
from raster_cache_segments import construct
from raster_slot_greedy import demand


def pixels(frame):
    return {(p['actor'],p['y']+y,p['x']+x):int(c)for p,image in zip(frame['pieces'],demand(frame)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}


class CacheSegmentTests(unittest.TestCase):
    def fixture(self):
        from test_raster_piece_bank_cache import PieceBankCacheTests
        return PieceBankCacheTests().fixture()

    def test_class_transfer_lower_bound_never_exceeds_complete_partition(self):
        import itertools,math
        from raster_bank_residency import favorable_span
        for counts in itertools.product((0,1,15),repeat=8):
            minimum_banks=sum(math.ceil(sum(counts[a:a+4])/15)for a in (0,4))
            bound=max(0,16*sum(counts)+16*minimum_banks-32)
            events=[dict(bank=b)for b,n in enumerate(counts)for _ in range(n)]
            self.assertLessEqual(bound,favorable_span(events))

    def test_real_bank_assignment_retains_opaque_black_and_pixels(self):
        source=self.fixture();result=construct(source,time_limit=5,write_budget=0,window=1000,maximum_oam=4)
        self.assertEqual(pixels(source),pixels(result))
        self.assertIn(0,pixels(result).values())
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertEqual(result['combined_reserved_geometry']['oam_entries'],4)
        proof=result['cache_segment_construction']
        self.assertTrue(proof['fixed_bank_per_compiled_oam_entry'])
        self.assertTrue(proof['independent_cache_and_partition_replay'])
        self.assertFalse(proof['native_timing_admitted'])

    def test_class_pool_success_does_not_admit_impossible_bank_masks(self):
        result=construct(self.fixture(),time_limit=5,write_budget=0,window=1000,maximum_oam=2)
        self.assertEqual(result['class_cache_status'],'OPTIMAL')
        self.assertEqual(result['bank_status'],'INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])

    def test_actor_geometry_and_bank_eligibility_remain_required(self):
        source=self.fixture();height=len(source['trace'])
        source['geometry_reservation']=dict(oam_entries=125,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
        result=construct(source,time_limit=5,write_budget=0,window=1000)
        self.assertEqual(result['bank_status'],'INFEASIBLE')
        source.pop('geometry_reservation')
        for p in source['pieces']:p['allowed_banks']=[0]
        source['pieces'][1]['bank']=0
        # The original trace must still decode the same word identities.
        result=construct(source,time_limit=5,write_budget=0,window=1000)
        self.assertEqual(result['bank_status'],'INFEASIBLE')

    def test_invalid_resource_domains_reject(self):
        source=self.fixture()
        with self.assertRaisesRegex(ValueError,'DOMAIN'):construct(source,maximum_oam=129)
        source['geometry_reservation']=dict(oam_entries=True,sprites_per_line=[0]*16,tile_slivers_per_line=[0]*16)
        with self.assertRaisesRegex(ValueError,'RESERVATION'):construct(source,time_limit=5,write_budget=0)

    def test_cache_hint_is_replayed_before_soft_bank_search(self):
        import copy
        source=self.fixture();initial=construct(source,time_limit=5,write_budget=0,window=1000,maximum_oam=4)
        hint=initial['cache_segment_construction']
        result=construct(source,time_limit=5,write_budget=0,window=1000,maximum_oam=4,class_cache_hint=hint)
        self.assertTrue(result['cache_segment_construction']['validated_class_cache_hint_used'])
        self.assertEqual(pixels(source),pixels(result))
        bad=copy.deepcopy(hint);bad['class_cache_lifetimes']=[]
        with self.assertRaisesRegex(ValueError,'HINT_SOURCE_WORD'):construct(source,class_cache_hint=bad)
        blocked=construct(source,time_limit=5,write_budget=0,window=1000,maximum_oam=2,class_cache_hint=hint)
        self.assertEqual(blocked['bank_status'],'INFEASIBLE')
        fixed=construct(source,time_limit=5,write_budget=0,window=1000,maximum_oam=4,class_cache_hint=hint,fix_class_cache_hint=True)
        self.assertEqual(fixed['cache_segment_construction']['class_cache_lifetimes'],hint['class_cache_lifetimes'])
        self.assertFalse(fixed['cache_segment_construction']['class_cache_hints_are_soft'])
        self.assertEqual(pixels(source),pixels(fixed))
        with self.assertRaisesRegex(ValueError,'FIXED_HINT_DOMAIN'):construct(source,fix_class_cache_hint=True)
        diagnostic=construct(source,time_limit=5,write_budget=0,window=10000,maximum_oam=4,class_cache_hint=hint,fix_class_cache_hint=True)
        self.assertTrue(diagnostic['cache_segment_construction']['interchangeable_segment_bank_first_use_order'])
        self.assertTrue(diagnostic['cache_segment_construction']['complete_partition_constraints_provably_redundant'])
        self.assertEqual(pixels(source),pixels(diagnostic))

    def test_independent_integer_cache_backend_replays_source(self):
        source=self.fixture()
        result=construct(source,time_limit=5,write_budget=0,window=1000,maximum_oam=4,class_cache_backend='highspy')
        self.assertEqual(pixels(source),pixels(result))
        proof=result['cache_segment_construction']
        self.assertEqual(proof['class_cache_backend'],'highspy')
        self.assertLessEqual(proof['class_cache_backend_report']['maximum_integer_constraint_violation'],1e-6)


if __name__=='__main__':unittest.main()
