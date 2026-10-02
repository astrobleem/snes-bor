import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/core/source_visual_production.pasm'


class ExtendedSourceVisualAdmissionTests(unittest.TestCase):
    def test_normal_65_piece_frames_have_nonoverlapping_table_and_scratch(self):
        text = SOURCE.read_text()
        values = {name: 0x7E0000 + int(value, 16) for name, value in re.findall(
            r'^(SourceVisual_\w+)\s*=\s*\$7E([0-9A-Fa-f]{4})', text, re.M)}
        limit = int(re.search(r'^SOURCE_VISUAL_MAX_PIECES\s*=\s*(\d+)$', text, re.M).group(1))
        table_end = values['SourceVisual_PieceTable'] + limit * 16
        self.assertEqual(limit, 65)
        self.assertLessEqual(table_end, values['SourceVisual_EntryScratch'])
        self.assertEqual(table_end, 0x7E4410)
        self.assertLess(values['SourceVisual_ActorSlot'] + 2, 0x7E550F)

    def test_oam_capacity_is_reserved_before_any_piece_is_emitted(self):
        text = SOURCE.read_text()
        emit = text.split('SourceVisual_Emit:\n', 1)[1].split(
            'SourceVisual_Emit__piece:\n', 1)[0]
        self.assertIn('adc.l $7E53A0', emit)
        self.assertIn('cmp #513', emit)  # 128 entries * four OAM bytes + sentinel
        self.assertIn('lda #$A7', emit)
        self.assertLess(emit.index('SourceVisual_Emit__oam_capacity_ok:'),
                        text.index('SourceVisual_Emit__piece:'))
        self.assertIn('jsr SourceVisual_Emit\n    bcc SourceVisual_RenderCurrent__fail', text)


if __name__ == '__main__':
    unittest.main()
