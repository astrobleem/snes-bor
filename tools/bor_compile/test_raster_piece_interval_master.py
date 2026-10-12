import copy,unittest
import numpy as np
from raster_piece_interval_master import search
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


def fixture():
    source=source_schedule()
    for p in source['pieces']:p['actor']=0
    return source


class IntervalMasterTests(unittest.TestCase):
    def test_complete_aggregate_hint_is_independently_validated(self):
        result=search(fixture(),time_limit=3,window=100,write_budget=2,hint_input_schedule=True,minimize_span=True)
        report=result['piece_interval_master']
        self.assertTrue(report['complete_input_aggregate_hint_model_verified'])
        self.assertTrue(report['aggregate_peak_cost_objective'])
        self.assertFalse(report['full_frame_schedule_proven'])
        rejected=search(fixture(),time_limit=3,window=100,write_budget=0,hint_input_schedule=True)
        self.assertGreater(rejected['complete_hint_violation_count'],0)
        self.assertFalse(rejected['complete_input_aggregate_hint_model_verified'])

    def test_fractional_loads_are_labeled_and_never_admit_a_schedule(self):
        result=search(fixture(),time_limit=3,window=100,write_budget=2,solver_backend='highspy',fractional_loads=True)
        report=result['piece_interval_master']
        self.assertTrue(report['fractional_aggregate_loads'])
        self.assertTrue(report['independent_source_rows_and_interval_inequalities_replayed'])
        self.assertFalse(report['independent_row_interval_and_partition_replay'])
        self.assertFalse(report['full_frame_schedule_proven'])
        with self.assertRaisesRegex(ValueError,'FRACTIONAL_BACKEND'):search(fixture(),fractional_loads=True)

    def test_independent_backend_replays_aggregate_assignment(self):
        source=fixture();result=search(source,time_limit=3,window=100,write_budget=2,solver_backend='highspy')
        report=result['piece_interval_master']
        self.assertTrue(report['independent_row_interval_and_partition_replay'])
        self.assertLessEqual(report['maximum_integer_constraint_violation'],1e-6)
        self.assertFalse(report['full_frame_schedule_proven'])

    def test_zero_loads_reject_sixteen_word_piece_lifetime(self):
        result=search(fixture(),time_limit=3,write_budget=0)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])

    def test_assignment_replays_aliases_without_cache_admission(self):
        source=fixture();result=search(source,time_limit=3,window=100,write_budget=2)
        report=result['piece_interval_master']
        self.assertTrue(report['independent_row_interval_and_partition_replay'])
        self.assertTrue(report['palette_cache_continuity_relaxed'])
        self.assertFalse(report['full_frame_schedule_proven'])
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)

    def test_concurrent_fixed_geometry_overflow_is_explicit(self):
        source=fixture();height=len(source['trace'])
        source['geometry_reservation']=dict(oam_entries=127,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
        result=search(source,time_limit=3)
        self.assertEqual(result['status'],'FIXED_INPUT_GEOMETRY_OVERFLOW')
        self.assertEqual(result['combined_reserved_geometry']['oam_entries'],129)
        self.assertFalse(result['universal_raster_rejected'])

    def test_input_not_mutated_and_invalid_domain_rejected(self):
        source=fixture();before=copy.deepcopy(source);search(source,time_limit=3)
        self.assertEqual(source,before)
        with self.assertRaisesRegex(ValueError,'MASTER_DOMAIN'):search(source,write_budget=True)


if __name__=='__main__':unittest.main()
