#!/usr/bin/env python3
"""P1-S1B: ROM-level 32-bit score HUD/display gate.

Only the score display path is under test.  Score-producing game logic is not
used to reach values above the existing 16-bit range; the canonical score
fields are set as a bounded display fixture.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, open_session, pasm_constant,
                      pasm_constant_in, read_block, run_frames_exact)
import game_bor_startup_select as startup
import game_g1_text as text

GS = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
P2S = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score32')
HC = pasm_constant_in('src/core/game_state.pasm', 'HudCachedScore32')
P2HC = pasm_constant_in('src/core/game_state.pasm', 'HudCachedP2Score32')
ROW_P1 = pasm_constant('HUD_ROW_SCORE')
ROW_P2 = pasm_constant('HUD_ROW_P2_SCORE')
LABEL_P1 = 'SCORE '
LABEL_P2 = 'P2SCOR'
VALUES = (0, 65535, 65536, 100000, 999999999)


class _SetupOnly:
    """Keep this display gate independent of stale campaign assertions in
    the shared startup helper; the helper still drives real menu input."""
    def check(self, *args, **kwargs):
        pass


def u32(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24


def put32(m, address, value):
    for offset in range(4):
        m.write_u8(address + offset, (value >> (offset * 8)) & 0xFF)


def row_text(m, row):
    words = text.read_row_words(m, row, 32)
    return ''.join(text.decode_char(word)[0] for word in words)


def render_and_check(m, r, score_addr, cache_addr, row, label, value, tag):
    put32(m, score_addr, value)
    put32(m, cache_addr, value ^ 1)
    # P1 text owns the first text service slot; in 2P the existing scheduler
    # may defer the P2 row behind a changed P1/lives/stage row.  This bounded
    # settle window observes the normal eventual cache/DMA result.
    run_frames_exact(m, 20)
    rendered = row_text(m, row)
    expected = (label + str(value)).ljust(32)
    r.check(f'{tag} renders {value}', rendered == expected)
    r.check(f'{tag} cache stores complete 32-bit value',
            u32(m, cache_addr) == value)
    r.check(f'{tag} score remains complete 32-bit value',
            u32(m, score_addr) == value)
    return rendered


def main():
    r = Reporter('BOR-S1B-SCORE-HUD32', kind='GATE')
    setup_reporter = _SetupOnly()
    with open_session(__file__) as m:
        startup.cold_to_title(m, setup_reporter)
        startup.select_case(m, setup_reporter, 'KULA')
        for value in VALUES:
            render_and_check(m, r, GS, HC, ROW_P1, LABEL_P1, value, 'P1')

        # High-word-only change: the low word remains $FFFF, so a low-word
        # cache comparison would incorrectly skip this redraw.
        put32(m, GS, 0x0000FFFF)
        put32(m, HC, 0x0000FFFF)
        run_frames_exact(m, 20)
        put32(m, GS, 0x0001FFFF)
        run_frames_exact(m, 20)
        r.check('P1 high-word-only change triggers redraw',
                row_text(m, ROW_P1) == (LABEL_P1 + '131071').ljust(32))
        r.check('P1 high-word-only redraw updates full cache', u32(m, HC) == 0x0001FFFF)

        # Digit shrink must clear all trailing positions in the same row DMA.
        render_and_check(m, r, GS, HC, ROW_P1, LABEL_P1, 999999999, 'P1 shrink source')
        render_and_check(m, r, GS, HC, ROW_P1, LABEL_P1, 0, 'P1 shrink result')

    with open_session(__file__) as m:
        startup.cold_to_title(m, setup_reporter)
        startup.select_case(m, setup_reporter, 'KULA', 'MIGHTY')
        for value in VALUES:
            render_and_check(m, r, P2S, P2HC, ROW_P2, LABEL_P2, value, 'P2')
        p1_before = u32(m, GS)
        p1_cache_before = u32(m, HC)
        put32(m, P2S, 0x0001FFFF)
        put32(m, P2HC, 0x0000FFFF)
        run_frames_exact(m, 3)
        r.check('P2 high-word-only change triggers redraw',
                row_text(m, ROW_P2) == (LABEL_P2 + '131071').ljust(32))
        r.check('P2 high-word-only redraw updates full cache', u32(m, P2HC) == 0x0001FFFF)
        r.check('P2 rendering leaves P1 score/cache unchanged',
                u32(m, GS) == p1_before and u32(m, HC) == p1_cache_before)
        r.check('P1/P2 score rows stay within 32-column bounds',
                len(row_text(m, ROW_P1)) == 32 and len(row_text(m, ROW_P2)) == 32)

    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
