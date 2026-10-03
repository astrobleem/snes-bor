import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class StageClearEdgeTests(unittest.TestCase):
    def test_left_clear_accepts_the_clamped_minimum(self):
        source = (ROOT / 'src/core/game_state.pasm').read_text()
        left = source.split('Game_State_Play__stage_check_left_edge:\n', 1)[1]
        left = left.split('\nGame_State_Play__stage_check_vertical_edge:', 1)[0]
        self.assertIn('cmp.l Screen_MinX', left)
        self.assertIn('bcc Game_State_Play__stage_edge_ready', left)
        self.assertIn('beq Game_State_Play__stage_edge_ready', left)
        self.assertIn('bra Game_State_Play__stage_no_win', left)

        screen = (ROOT / 'src/core/screen.pasm').read_text()
        clamp = screen.split('Core_Screen__ClampToScreen:\n', 1)[1]
        clamp = clamp.split('\nCore_Screen__ClampToScreen__maxx_ok:', 1)[0]
        self.assertIn('cmp Screen_MinX', clamp)
        self.assertIn('sta Screen_PosX', clamp)


if __name__ == '__main__':
    unittest.main()
