import unittest
from pathlib import Path
from source_world_clock import AbsoluteSourceClock, timer_interval, verify_timer, visible_boundary
from source_actor_numeric import verify_source


class SourceWorldClockTests(unittest.TestCase):
    def test_pinned_source_clock_and_render_order(self):
        root=Path(__file__).resolve().parents[2]
        verify_source(root/'out/bor_compile_s6/BOR.C')
        verify_timer(root/'out/bor_compile_s7/TIMER.ASM')
        text=(root/'out/bor_compile_s6/BOR.C').read_text()
        body=text.split('void update(int ingame, int usevwait){',1)[1].split('void ',1)[0]
        self.assertLess(body.index('display_ents();'),body.index('timer_getinterval(GAME_SPEED)'))
        self.assertLess(body.index('update_ents();'),body.index('++time;'))
        self.assertIn('delay * GAME_SPEED / 100',text)
        self.assertIn('while(time < newtime)',body)

    def test_real_timer_block_not_nominal_200hz(self):
        self.assertEqual(timer_interval(5783,0),(0,0))
        self.assertEqual(timer_interval(5784,0),(1,5965))
        self.assertEqual(timer_interval(5784,5965),(0,5965))

    def test_poll_partition_has_no_cumulative_drift(self):
        for step in (1,17,100,5965,11931):
            last=total=0
            for now in range(0,120000,step):
                count,last=timer_interval(now,last)
                total+=count
                self.assertEqual(total,(now+181)//5965)

    def test_absolute_deadlines_ignore_previous_completion(self):
        clock=AbsoluteSourceClock(12345)
        for tick in range(1,10001):
            deadline=clock.deadline(tick)
            self.assertEqual(clock.due(deadline),tick)
            self.assertEqual(clock.due(deadline-1),tick-1)
            # A later observer may see a backlog, never move this deadline.
            clock.due(deadline+1000000)
            self.assertEqual(clock.deadline(tick),deadline)

    def test_frequency_changes_preserve_source_interval_state(self):
        count,last=timer_interval(10000,0,200)
        self.assertEqual((count,last),(1,5965))
        self.assertEqual(timer_interval(20000,last,100),(1,17896))

    def test_pause_consumes_timer_sample_before_suppressing_updates(self):
        _,last=timer_interval(50000,0)
        count,_=timer_interval(51000,last)
        self.assertEqual(count,0)

    def test_field_quantization_does_not_grant_hidden_extra_field(self):
        self.assertEqual(visible_boundary(100,[50,100,150]),100)
        self.assertEqual(visible_boundary(101,[50,100,150]),150)
        self.assertIsNone(visible_boundary(151,[50,100,150]))


if __name__=='__main__':unittest.main()
