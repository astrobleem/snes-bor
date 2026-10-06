import unittest
from source_clock_4086 import Clock,credits,FIELD_CLOCKS,SHORT_CLOCKS,GAME_SPEED,MASTER_HZ,cap_interval


class SourceClock(unittest.TestCase):
    def test_every_binary_credit_is_exact_integer_division(self):
        for bit,(q,r) in enumerate(credits()):
            self.assertEqual(q*MASTER_HZ+r,FIELD_CLOCKS*GAME_SPEED*(1<<bit))
            self.assertLess(r,MASTER_HZ)

    def test_partitioned_observation_does_not_accumulate_rounding_drift(self):
        for step in (1,2,7,14):
            c=Clock()
            for field in range(step,9000,step):
                c.observe(field,field//2)
                while c.due:c.commit()
                self.assertEqual(c.time,(field*FIELD_CLOCKS-(field//2)*SHORT_CLOCKS)*GAME_SPEED//MASTER_HZ)

    def test_source_backlog_pause_and_pending_tick_policy(self):
        self.assertEqual([cap_interval(n) for n in (0,1,50,51,200,201,10000)],[0,1,50,50,50,1,1])
        c=Clock();self.assertEqual(c.observe(20,10),50)
        with self.assertRaisesRegex(ValueError,'PENDING'):c.observe(21,10)
        while c.due:c.commit()
        self.assertEqual(c.observe(81,40),1)
        c.commit();self.assertEqual(c.time,51)
        self.assertEqual(c.observe(141,70,False),0)
        self.assertEqual(c.time,51)
        self.assertIn(c.observe(142,71),(3,4))

    def test_unsigned_field_and_logical_time_wrap(self):
        c=Clock(fields=0xfffffffe,shorts=0xffffffff,time=0xffffffff)
        c.observe(1,0);self.assertEqual(c.commit(),0)
        with self.assertRaisesRegex(ValueError,'DOMAIN'):Clock().observe(32768,0)
        with self.assertRaisesRegex(ValueError,'DOMAIN'):Clock().observe(1,2)


if __name__=='__main__':unittest.main()
