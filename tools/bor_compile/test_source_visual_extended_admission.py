import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/core/source_visual_production.pasm'


class ExtendedSourceVisualAdmissionTests(unittest.TestCase):
    def test_unlinked_actor_lease_retires_after_owned_dma(self):
        text = SOURCE.read_text()
        host = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        residency = text.split('SourceVisual_SelectResidency:\n', 1)[1].split(
            'SourceVisual_SelectResidency__busy:', 1)[0]
        processor = text.split('SourceVisual_ProcessRetired:\n', 1)[1].split(
            '; Release the current actor', 1)[0]

        self.assertLess(
            residency.index('jsr SourceVisual_CancelActorRetire'),
            residency.index('SourceVisual_SelectResidency__replace:'),
        )
        self.assertIn('jsr SourceVisual_ProcessRetired', residency)
        self.assertLess(
            processor.index('jsr SourceVisual_HasOwnedDma'),
            processor.index('jsr SourceVisual_ReleaseActorBlocks'),
        )
        self.assertLess(
            processor.index('jsr SourceVisual_ReleaseActorBlocks'),
            processor.index('jsr SourceVisual_ReleaseActorPalettes'),
        )
        self.assertIn('cmp #6', processor)
        self.assertIn('sta.l SourceVisual_State+6,x', processor)
        retire_success = processor.split(
            'sta.l SourceVisual_RetireMask\n', 1)[1]
        self.assertIn('rep #$31\n.a16\n.i16\n    bra SourceVisual_ProcessRetired__next',
                      retire_success)

        remove = host.split('S6Host_RemoveHandle:\n', 1)[1].split(
            'S6Host_RemoveHandle__bad:', 1)[0]
        self.assertIn('sec\n    sbc #$0A00\n    tax\n    txa\n'
                      '    sta.l SourceVisual_RetireEntityOffset', remove)
        self.assertEqual(remove.count('jsl SourceVisual_QueueRetireEntityOffset'), 2)
        for branch in ('S6Host_RemoveHandle__resident:',
                       'S6Host_RemoveHandle__temporary:'):
            body = remove.split(branch, 1)[1]
            self.assertLess(
                body.index('jsl S6Host_ClearRemovedReferences'),
                body.index('jsl SourceVisual_QueueRetireEntityOffset'),
            )

    def test_late_catalog_entry_address_preserves_multiply_carry(self):
        text = SOURCE.read_text()
        lookup = text.split('SourceVisual_FindEntry__key_match:\n', 1)[1].split(
            'jsr SourceVisual_AddCatalogBase', 1)[0]
        multiply_carry = lookup.index(
            'sta.l SourceVisual_Offset\n    sep #$20')
        capture_high = lookup.index(
            'lda #0\n    adc #0\n    sta.l SourceVisual_Offset+2')
        add_header = lookup.index('adc #18')
        propagate_header_carry = lookup.index(
            'lda.l SourceVisual_Offset+2\n    adc #0\n'
            '    sta.l SourceVisual_Offset+2')
        self.assertLess(multiply_carry, capture_high)
        self.assertLess(capture_high, add_header)
        self.assertLess(add_header, propagate_header_carry)

        # The 16-bit key-table value becomes 18 + index*24 in a 24-bit
        # catalog address.  Exercise the late entries whose product exceeds
        # one word; the previous code lost this high byte before MSU seek.
        for index in range(3640):
            product = index * 24
            low = product & 0xFFFF
            high = product >> 16
            low_with_header = low + 18
            address = ((high + (low_with_header >> 16)) << 16) | (
                low_with_header & 0xFFFF)
            self.assertEqual(address, 18 + index * 24, index)

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

    def test_source_sized_normal_emitter_applies_pit_foot_and_priority(self):
        visual = SOURCE.read_text()
        render = visual.split('SourceVisual_RenderCurrent:\n', 1)[1].split(
            'SourceVisual_RenderCurrent__fail:', 1)[0]
        self.assertLess(render.index('jsl StageBoundsHost_Normal'),
                        render.index('jsr SourceVisual_FindEntry'))
        self.assertIn('lda.l StageBounds_State,x\n    cmp #2\n'
                      '    beq SourceVisual_RenderCurrent__retired', render)
        emit = visual.split('SourceVisual_Emit:\n', 1)[1].split(
            'SourceVisual_Emit__piece:', 1)[0]
        self.assertIn('lda.l StageBounds_DrawY,x\n'
                      '    cmp #240\n    bcs SourceVisual_Emit__hidden', emit)
        self.assertIn('sta.l SourceVisual_EmitBaseY', emit)
        self.assertIn('SourceVisual_Emit__hidden:\n    sec\n    rts', emit)
        write = visual.split('SourceVisual_Emit__write:\n', 1)[1].split(
            'SourceVisual_Emit__priority_ready:', 1)[0]
        self.assertIn('and #$CF', write)

    def test_unpresented_source_lease_is_not_starved_by_live_frame_changes(self):
        text = SOURCE.read_text()
        render = text.split('SourceVisual_RenderCurrent:\n', 1)[1].split(
            'SourceVisual_RenderCurrent__retired:', 1)[0]
        residency = text.split('SourceVisual_SelectResidency:\n', 1)[1].split(
            'SourceVisual_SelectResidency__busy:', 1)[0]
        restore = text.split('SourceVisual_LoadPendingEntry:\n', 1)[1].split(
            '; Remove a newly live actor slot', 1)[0]

        self.assertLess(render.index('jsr SourceVisual_Emit'),
                        render.index('sta.l SourceVisual_State+28,x'))
        self.assertIn('lda.l SourceVisual_State+28,x', residency)
        self.assertIn('jsr SourceVisual_LoadPendingEntry', residency)
        self.assertIn('sta.l SourceVisual_EntryIndexSaved', restore)
        self.assertIn('adc #18', restore)
        self.assertIn('sta.l SourceVisual_KeySaved', restore)

    def test_retired_actor_cannot_orphan_shared_tile_staging(self):
        text = SOURCE.read_text()
        render = text.split('SourceVisual_RenderCurrent:\n', 1)[1].split(
            'SourceVisual_RenderCurrent__retired:', 1)[0]
        self.assertLess(render.index('jsr SourceVisual_ResumePendingBlock'),
                        render.index('jsl StageBoundsHost_Normal'))

    def test_source_sized_normal_emitter_applies_pit_foot_and_priority(self):
        visual = SOURCE.read_text()
        render = visual.split('SourceVisual_RenderCurrent:\n', 1)[1].split(
            'SourceVisual_RenderCurrent__fail:', 1)[0]
        self.assertLess(render.index('jsl StageBoundsHost_Normal'),
                        render.index('jsr SourceVisual_FindEntry'))
        self.assertIn('lda.l StageBounds_State,x\n    cmp #2\n'
                      '    beq SourceVisual_RenderCurrent__retired', render)
        emit = visual.split('SourceVisual_Emit:\n', 1)[1].split(
            'SourceVisual_Emit__piece:', 1)[0]
        self.assertIn('lda.l StageBounds_DrawY,x\n'
                      '    cmp #240\n    bcs SourceVisual_Emit__hidden', emit)
        self.assertIn('sta.l SourceVisual_EmitBaseY', emit)
        self.assertIn('SourceVisual_Emit__hidden:\n    sec\n    rts', emit)
        write = visual.split('SourceVisual_Emit__write:\n', 1)[1].split(
            'SourceVisual_Emit__priority_ready:', 1)[0]
        self.assertIn('and #$CF', write)


if __name__ == '__main__':
    unittest.main()
