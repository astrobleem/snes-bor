"""SOURCE_EXACT axis position offsets must stay actor-D-relative on 65816/SA-1."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SourceAxisAddressingTests(unittest.TestCase):
    def test_axis_helper_uses_supported_direct_page_x_indexing(self):
        source = (ROOT / 'src/core/actor_source_ai.pasm').read_text()
        helper = source.split('S6_EnemyApplyAxis:', 1)[1].split(
            'S6_EnemyApplyAxis__done:', 1)[0]
        self.assertNotIn('$14,y', helper)
        self.assertIn('ldx $92\n    lda $AE', helper)
        self.assertIn('adc $14,x\n    sta $14,x', helper)
        self.assertIn('lda $14,x\n    dec a\n    sta $14,x', helper)
        self.assertIn('lda $14,x\n    inc a\n    sta $14,x', helper)


if __name__ == '__main__':
    unittest.main()
