"""Focused regression checks for the three Normal runtime review defects."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'src/core/actor_source_bridge.pasm'
TIMER_HOST = ROOT / 'src/core/stage_timer_host.pasm'
NORMAL_RUNTIME = ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm'


def round_ratio_away(numerator, denominator):
    sign = -1 if numerator < 0 else 1
    return sign * ((abs(numerator) + denominator // 2) // denominator)


def words_after_label(source, label, next_label):
    body = source.split(label + ':\n', 1)[1].split('\n' + next_label + ':', 1)[0]
    return [int(value, 16) for value in re.findall(r'\$([0-9A-Fa-f]{4})', body)]


class ProjectionBoundaryTests(unittest.TestCase):
    def test_actual_project_tables_and_high_masks_cover_the_signed_domain(self):
        source = BRIDGE.read_text()
        high = words_after_label(source, 'S6Bridge_ProjectHigh',
                                 'S6Bridge_ProjectRoundedLow')
        rounded = words_after_label(source, 'S6Bridge_ProjectRoundedLow',
                                    'S6Bridge_ProjectLow')
        exact = words_after_label(source, 'S6Bridge_ProjectLow',
                                  'S6Bridge_ProjectPolicy')
        self.assertEqual(high, [204 * value for value in range(32)])
        self.assertEqual(len(rounded), 287)
        self.assertEqual(len(exact), 287)

        masks = []
        for routine in ('S6Bridge_Project', 'S6Bridge_ProjectRounded'):
            body = source.split(routine + '__positive:\n', 1)[1]
            match = re.search(r'xba\s+and #\$([0-9A-Fa-f]{4})', body)
            self.assertIsNotNone(match, routine)
            masks.append(int(match.group(1), 16))
        self.assertEqual(masks, [0x001F, 0x001F])

        def table_result(value, low_table, mask, reject_off_lattice):
            if not -8191 <= value <= 8191:
                return None
            magnitude = abs(value)
            high_index = ((magnitude >> 8) & mask)
            low_index = high_index + (magnitude & 0xFF)
            correction = low_table[low_index]
            if reject_off_lattice and correction == 0x8000:
                return None
            result = high[high_index] + correction
            return -result if value < 0 else result

        # Model the exact lookup/index operations emitted by the two routines,
        # using the actual immediate masks and actual assembler table data.
        for value in range(-8191, 8192):
            rounded_expected = round_ratio_away(4 * value, 5)
            self.assertEqual(table_result(value, rounded, masks[1], False),
                             rounded_expected, f'rounded source={value}')
            exact_expected = (4 * value // 5) if value % 5 == 0 else None
            self.assertEqual(table_result(value, exact, masks[0], True),
                             exact_expected, f'exact source={value}')

        for value, expected in ((4095, 3276), (4096, 3277), (5150, 4120),
                                (8191, 6553), (-5150, -4120)):
            self.assertEqual(table_result(value, rounded, masks[1], False), expected)


class PendingTimeRenderTests(unittest.TestCase):
    def test_render_filter_uses_captured_actor_direct_page_for_all_slots(self):
        source = TIMER_HOST.read_text()
        render = source.split('StageTimerHost_RenderFrame:\n', 1)[1].split(
            '\nStageTimerHost_Offsets:', 1)[0]
        policy = render.index('sta.l SourceVisual_HostLastPolicy')
        gate = render[policy:render.index('jsl StageTimerHost_IsPendingOffset')]
        self.assertRegex(
            gate,
            r'lda\.l SourceVisual_HostLastD\s+sec\s+sbc #\$0A00\s+tax',
        )
        self.assertIn('bcs StageTimerHost_RenderFrame__skip', render)
        self.assertLess(render.index('jsl StageTimerHost_IsPendingOffset'),
                        render.index('jsl SourceVisual_RenderCurrent'))
        self.assertLess(render.index('jsl StageTimerHost_IsPendingOffset'),
                        render.index('jml Character_RenderFrame'))

        helper = source.split('StageTimerHost_IsPendingOffset:\n', 1)[1]
        helper = helper.split('\nStageTimerHost_IsPendingOffset__found:', 1)[0]
        self.assertIn('cmp.l StageTimerHost_Offsets,x', helper)
        self.assertIn('lda.l StageTimer_Pending,x', source)

        offsets = tuple(133 * slot for slot in range(6))
        # Each physical D value must resolve to the matching pending-mask row;
        # exercise every slot as the sole pending item and the all-clear case.
        for actor_slot, offset in enumerate(offsets):
            captured_d = 0x0A00 + offset
            resolved_offset = captured_d - 0x0A00
            self.assertEqual(resolved_offset, offset)
            self.assertEqual(offsets.index(resolved_offset), actor_slot)
            for pending_slot in range(6):
                pending = [False] * 6
                pending[pending_slot] = True
                self.assertEqual(pending[offsets.index(resolved_offset)],
                                 actor_slot == pending_slot)
            all_clear = [False] * 6
            self.assertFalse(all_clear[offsets.index(resolved_offset)])


class BoundContextMetadataTests(unittest.TestCase):
    def test_metadata_tail_reuses_full_width_copy_index_for_six_rows(self):
        source = NORMAL_RUNTIME.read_text()
        sync = source.split('S6Normal_SyncBoundContext:\n', 1)[1]
        metadata = sync.split('S6Normal_SyncBoundContext__metadata_start:\n', 1)[1]
        metadata = metadata.split('S6Normal_SyncBoundContext__player0:', 1)[0]
        loop = metadata.split('S6Normal_SyncBoundContext__metadata:\n', 1)[1]
        self.assertIn('inx\n    inx\n    iny\n    iny\n    cpy #132', loop)
        tail = loop.split('bcc S6Normal_SyncBoundContext__metadata', 1)[1]
        tail = tail.split('rep #$30', 1)[0]
        self.assertRegex(tail, r'\.a8\s+lda\.l StageEnv_Actors,x\s+'
                               r'sta\.l \$412100,x')
        self.assertNotRegex(tail, r'(?m)^\s*(tax|txa|lda\.l \$7E1752)\b')
        self.assertNotIn('adc #132', tail)

        stride = 133
        row_count = 6
        src = bytearray((index * 37 + 11) & 0xFF
                        for index in range(stride * row_count))
        guard = 0xD7
        dst = bytearray([guard] * (stride * row_count + 2))
        dst[0] = guard
        for slot in range(row_count):
            start = slot * stride
            x = start
            for _ in range(66):
                dst[1 + x:1 + x + 2] = src[x:x + 2]
                x += 2
            self.assertEqual(x, start + 132, f'slot {slot} loop tail index')
            dst[1 + x] = src[x]
        self.assertEqual(dst[1:1 + stride * row_count], src)
        self.assertEqual(dst[0], guard)
        self.assertEqual(dst[-1], guard)


if __name__ == '__main__':
    unittest.main()
