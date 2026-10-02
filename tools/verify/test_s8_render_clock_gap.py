import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RenderClockGapTests(unittest.TestCase):
    def test_word_sized_nmi_elapsed_time_is_replayed_fail_closed(self):
        fixture = (ROOT / 'src/core/actor_s6_world_fixture.pasm').read_text()
        nmi = (ROOT / 'src/core/nmi.pasm').read_text()
        self.assertRegex(nmi, r'Nmi_FrameCounter\s*=\s*\$7E5023\s*;\s*\.dw')

        start = fixture.index('S6Game_PlayRender__measure:')
        end = fixture.index('S6Game_PlayRender__field:', start)
        measure = fixture[start:end]
        self.assertIn('sbc.l S6Game_LastField', measure)
        self.assertNotRegex(measure, r'and\s+#\$00FF')
        self.assertIn('cmp #120', measure)
        self.assertIn('lda #16', measure)

        elapsed_start = fixture.index('S6Game_PlayRender__elapsed_field:')
        elapsed_end = fixture.index('S6Game_PlayRender__return:', elapsed_start)
        elapsed = fixture[elapsed_start:elapsed_end]
        self.assertIn('jsl S6Clock_ClockAdvance', elapsed)
        self.assertIn('jsl S7Resident_Flush', elapsed)

    def test_campaign_stage_transition_rebases_parked_source_clock_once(self):
        runtime = (ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        self.assertRegex(runtime, r'S6Normal_LastStage\s*=\s*\$7E1778')
        self.assertIn('lda #$FFFF\n    sta.l S6Normal_LastStage', runtime)
        hook_start = runtime.index('S6Normal_RenderHook__bind_live:')
        hook_end = runtime.index('S6Normal_RenderHook__ready:', hook_start)
        self.assertIn('jsl S6Normal_RebaseStageClock', runtime[hook_start:hook_end])

        rebase_start = runtime.index('S6Normal_RebaseStageClock:')
        rebase_end = runtime.index('S6Normal_RebaseStageClock__return:', rebase_start)
        rebase = runtime[rebase_start:rebase_end]
        self.assertIn('cmp.l S6Normal_LastStage', rebase)
        self.assertIn('sta.l S6Normal_LastStage', rebase)
        self.assertIn('sta.l S6Game_LastField', rebase)
        self.assertIn('sta.l S6Host_Error', rebase)


if __name__ == '__main__':
    unittest.main()
