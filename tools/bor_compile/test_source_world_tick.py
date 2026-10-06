import unittest
from source_world_tick import World,Entity,Service


class WorldTickContract(unittest.TestCase):
    def test_suspended_and_abandoned_handler_cannot_commit(self):
        w=World([Entity(True,47)], [0],1,48)
        run=w.tick();self.assertEqual(next(run),(Service.RESET_MARK,0))
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):w.commit()
        run.close()
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):w.commit()
        self.assertEqual(w.time,48)

    def test_complete_tick_commits_once_and_wraps(self):
        w=World([Entity(False)], [0],1,0xffffffff)
        self.assertEqual(list(w.tick()),[]);w.commit()
        self.assertEqual(w.time,0)
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):w.commit()
        # Pinned arrange_ents retains ent_max when ent_count is zero.
        self.assertEqual(w.maximum,1)

    def test_invalid_order_and_live_tail_are_admission_faults(self):
        for order,maximum in (([0,0],2),([0,1],1)):
            w=World([Entity(False),Entity(True,47)],order,maximum,48)
            with self.assertRaisesRegex(ValueError,'ORDER_OR_LIVE_PREFIX'):list(w.tick())

    def test_mutated_epoch_faults_before_completion(self):
        w=World([Entity(True,47)],[0],1,48)
        run=w.tick();next(run);w.time=49
        with self.assertRaisesRegex(ValueError,'TIME_CHANGED'):list(run)
        self.assertFalse(w.completed)


if __name__=='__main__':unittest.main()
