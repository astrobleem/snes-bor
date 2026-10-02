"""Pure telemetry arithmetic checks, not gameplay arithmetic or new fixtures."""
import unittest
from actor_s7_continuous import EPOCH,HORIZON
from actor_s7_continuous_report import due_bounds


class ContinuousTests(unittest.TestCase):
    def test_predeclared_physical_horizon(self):
        self.assertEqual(HORIZON,149722066)
        self.assertEqual(HORIZON-EPOCH,128*357368-64*4)

    def test_pending_field_is_not_zero_simulation_debt(self):
        self.assertEqual(due_bounds(306,3490580,257),(309,309))

    def test_current_field_remainder_includes_unexecuted_ticks(self):
        self.assertEqual(due_bounds(3,7041790,166),(6,6))

    def test_both_measured_parity_histories_give_same_due_cursor(self):
        self.assertEqual(due_bounds(306,3490580,257),due_bounds(306,3492980,257))

    def test_matched_six_actor_replay_clock_origin(self):
        self.assertEqual(due_bounds(302,17962060,297,160),(455,455))
        self.assertEqual(due_bounds(306,3489780,253,160),(309,309))


if __name__=='__main__':unittest.main()
