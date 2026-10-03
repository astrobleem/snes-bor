#!/usr/bin/env python3
"""P1-S1B.6: bounded unsigned-16-bit BOR life state/cache proof.

This gate validates the relocated fields and the existing gameplay/HUD paths;
source scoring arithmetic remains deliberately out of scope for S1C.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact)
import game_bor_startup_select as startup
import game_g8_pickup as g8
import game_g1_text as text

GS = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
P2 = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
HC = pasm_constant('HudCachedLives16')
P2HC = pasm_constant('HudCachedP2Lives16')
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
START = pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START')
ROW_P1 = pasm_constant('HUD_ROW_LIVES')
ROW_P2 = pasm_constant('HUD_ROW_P2_LIVES')


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | (b[1] << 8)


def put16(m, address, value):
    m.write_u16(address, value)


def row_text(m, row):
    return ''.join(text.decode_char(word)[0]
                   for word in text.read_row_words(m, row, 32))


class _SetupOnly:
    def check(self, *args, **kwargs):
        pass


def main():
    r = Reporter('BOR-S1B6-LIFE16', kind='GATE')
    expected = {
        'P1_Lives16': (0x7E58E1, 0x7E58E2),
        'P2_Lives16': (0x7E58E3, 0x7E58E4),
        'HudCachedLives16': (0x7E58E5, 0x7E58E6),
        'HudCachedP2Lives16': (0x7E58E7, 0x7E58E8),
    }
    got = {'P1_Lives16': (GS, GS + 1), 'P2_Lives16': (P2, P2 + 1),
           'HudCachedLives16': (HC, HC + 1),
           'HudCachedP2Lives16': (P2HC, P2HC + 1)}
    for name, span in expected.items():
        r.check(f'{name} exact range', got[name] == span)
    r.check('source stock constant is 3', START == 3)
    r.check('life fields are distinct', len(set(got.values())) == 4)

    setup = _SetupOnly()
    with open_session(__file__) as m:
        m.reset_emulator()
        startup.cold_to_title(m, setup)
        startup.select_case(m, setup, 'KULA', 'MIGHTY')
        r.check('new run is PLAYING', u16(m, STATE) == PLAYING)
        r.check('P1 initial lives are 3', u16(m, GS) == 3)
        r.check('P2 initial lives are 3', u16(m, P2) == 3)

        # Full-width storage and ownership: the high byte must survive and
        # changing one player must not touch the other.
        put16(m, GS, 255)
        put16(m, P2, 511)
        r.check('values above 255 survive storage', u16(m, GS) == 255 and u16(m, P2) == 511)
        put16(m, GS, 256)
        r.check('P1 change leaves P2 unchanged', u16(m, GS) == 256 and u16(m, P2) == 511)
        put16(m, P2, 512)
        r.check('P2 change leaves P1 unchanged', u16(m, P2) == 512 and u16(m, GS) == 256)

        # Consume the one real trigger-0 setup pickup before deterministic
        # display fixtures; this is production behavior, not a fake award.
        run_frames_exact(m, 60)
        # The first 1A trigger legitimately contains a source 1UP, so let
        # that production pickup settle before testing the literal value 3.
        for value in (9, 99, 255, 256, 999, 20007, 65535):
            put16(m, GS, value)
            put16(m, HC, value ^ 0xFFFF)
            run_frames_exact(m, 20)
            print(f'P1 HUD {value}: {row_text(m, ROW_P1)!r} cache={u16(m, HC)}')
            r.check(f'P1 HUD renders {value}',
                    row_text(m, ROW_P1) == ('LIVES ' + str(value)).ljust(32))
            r.check(f'P1 cache stores full {value}', u16(m, HC) == value)

        put16(m, GS, 20007)
        put16(m, HC, 0)
        run_frames_exact(m, 20)
        put16(m, GS, 3)
        run_frames_exact(m, 20)
        r.check('digit shrink 20007 -> 3 clears trailing digits',
                row_text(m, ROW_P1) == ('LIVES 3').ljust(32))
        r.check('digit-shrink cache is complete', u16(m, HC) == 3)

        # Exercise the real 1UP pickup path at the high-byte boundary.
        put16(m, GS, 255)
        g8.land_hit_on_entity2(m, g8.PICKUP_TYPE_ONEUP)
        r.check('real 1UP increments 255 -> 256', u16(m, GS) == 256)
        put16(m, GS, 3)
        put16(m, HC, 0)
        run_frames_exact(m, 20)
        r.check('P1 HUD renders 3',
                row_text(m, ROW_P1) == ('LIVES 3').ljust(32))
        r.check('P1 cache stores 3', u16(m, HC) == 3)

    with open_session(__file__) as m:
        m.reset_emulator()
        startup.cold_to_title(m, setup)
        startup.select_case(m, setup, 'KULA', 'MIGHTY')
        put16(m, P2, 65535)
        put16(m, P2HC, 0)
        run_frames_exact(m, 20)
        print(f'P2 HUD: {row_text(m, ROW_P2)!r} p1={u16(m, GS)}/{u16(m, HC)} p2={u16(m, P2)}')
        r.check('P2 HUD renders 65535',
                row_text(m, ROW_P2) == ('P2LIFE65535').ljust(32))
        r.check('P2 cache stores complete 16-bit value', u16(m, P2HC) == 65535)
        r.check('P2 rendering leaves P1 life/cache independent',
                u16(m, GS) == u16(m, HC))

    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
