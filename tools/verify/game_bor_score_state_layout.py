#!/usr/bin/env python3
"""P1-S1A: prove the relocated 32-bit score/cache ownership only.

This gate deliberately tests the existing low-word score behavior.  It does
not test source addscore arithmetic, thresholds, or values above 16 bits.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact)
import game_g13_score_pickup as g13

GS32 = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
P2S32 = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score32')
HC32 = pasm_constant_in('src/core/game_state.pasm', 'HudCachedScore32')
P2HC32 = pasm_constant_in('src/core/game_state.pasm', 'HudCachedP2Score32')
G12_LAST = pasm_constant('G12_AnimTrace_LastInput')
VM_WRAM = pasm_constant_in('src/core/vm/vm_consts.pasm', 'VmCode_Wram')
OLD_GS = 0x7E2761
OLD_P2S = 0x7E2767


def u32(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24


def ranges():
    return {
        'Game_Score32': (GS32, GS32 + 3),
        'G13_P2Score32': (P2S32, P2S32 + 3),
        'HudCachedScore32': (HC32, HC32 + 3),
        'HudCachedP2Score32': (P2HC32, P2HC32 + 3),
    }


def main():
    r = Reporter('BOR-S1A-SCORE-STATE', kind='GATE')
    expected = {
        'Game_Score32': (0x7E58D1, 0x7E58D4),
        'G13_P2Score32': (0x7E58D5, 0x7E58D8),
        'HudCachedScore32': (0x7E58D9, 0x7E58DC),
        'HudCachedP2Score32': (0x7E58DD, 0x7E58E0),
    }
    got = ranges()
    for name, span in expected.items():
        r.check(f'{name} exact approved range', got[name] == span)
    r.check('score block follows G12 trace state', GS32 > G12_LAST)
    r.check('score block ends before VM WRAM', P2HC32 + 3 < VM_WRAM)
    all_spans = list(got.values())
    r.check('score/cache fields do not overlap', len(set(all_spans)) == 4 and
            all(a[1] < b[0] or b[1] < a[0]
                for i, a in enumerate(all_spans)
                for b in all_spans[i + 1:]))
    r.check('compatibility score names are relocated low-word aliases',
            g13.GS == GS32 and g13.P2S == P2S32)
    r.check('old P1 score address is retired', g13.GS != OLD_GS)
    r.check('old P2 score address is retired', g13.P2S != OLD_P2S)

    with open_session(__file__) as m:
        g13.setup(m)
        r.check('new session P1 score is zero', u32(m, GS32) == 0)
        r.check('new session P2 score is zero', u32(m, P2S32) == 0)
        r.check('new session score upper words are zero',
                (u32(m, GS32) >> 16) == 0 and (u32(m, P2S32) >> 16) == 0)
        r.check('new session HUD cache upper words are deterministic zero',
                (u32(m, HC32) >> 16) == 0 and (u32(m, P2HC32) >> 16) == 0)

        before_p1 = u32(m, GS32)
        before_p2 = u32(m, P2S32)
        g13.collect(m, 0, g13.PT_MONEY)
        after_p1 = u32(m, GS32)
        after_p2 = u32(m, P2S32)
        r.check('existing P1 award changes canonical low word',
                after_p1 == before_p1 + g13.SCORE_MONEY)
        r.check('P1 award leaves P2 canonical score unchanged', after_p2 == before_p2)
        r.check('P1 score upper word remains zero', (after_p1 >> 16) == 0)

        # P2's accepted production dispatch reaches the pickup pass on its
        # established three-frame service boundary; this remains the current
        # low-word behavior under test, not a new scoring fixture.
        g13.collect(m, 1, g13.PT_GOLD, service_frames=3)
        after_p1b = u32(m, GS32)
        after_p2b = u32(m, P2S32)
        r.check('existing P2 award changes canonical low word',
                after_p2b == after_p2 + g13.SCORE_GOLD)
        r.check('P2 award leaves P1 canonical score unchanged', after_p1b == after_p1)
        r.check('P2 score upper word remains zero', (after_p2b >> 16) == 0)

        run_frames_exact(m, 2)
        r.check('P1 HUD cache uses relocated four-byte field',
                (u32(m, HC32) & 0xFFFF) == after_p1b and (u32(m, HC32) >> 16) == 0)
        r.check('P2 HUD cache uses relocated four-byte field',
                (u32(m, P2HC32) & 0xFFFF) == after_p2b and (u32(m, P2HC32) >> 16) == 0)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
