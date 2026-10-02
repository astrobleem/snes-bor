#!/usr/bin/env python3
"""Focused semantic gate for the real grounded JUMP SFX edge."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402
from game_g7_jump import (  # noqa: E402
    CHAR_SELECTED,
    CHAR_SELECTED_JUMP,
    CHAR_THROW_ZPOS,
    CHAR_THROW_ZVEL,
    ENTITY_BASES,
    Player_JumpFCount,
    load_leo_onto_player,
    neutralize_ai,
)

Player_JumpRequestCount = pasm_constant("AudioSemantic_JumpRequestCount")
SemanticRequestCount = pasm_constant("AudioSemantic_RequestCount")
TraceWriteIndex = pasm_constant("AudioSemantic_TraceWriteIndex")
CharSelect_Index = pasm_constant("CharSelect_Index")
CHAR_HP = pasm_constant("CHAR_HP")


def byte(m, address):
    return read_block(m, address, 32)[0]


def word(m, address):
    data = read_block(m, address, 32)
    return data[0] | (data[1] << 8)


def settle_jump(m):
    m.run_frames(1)
    m.pause()


def press_a(m):
    m.set_input(m.BTN_A, 1)
    m.pause()
    settle_jump(m)


def wait_for_land(m):
    for _ in range(160):
        if byte(m, ENTITY_BASES[0] + CHAR_SELECTED) != CHAR_SELECTED_JUMP:
            return True
        neutralize_ai(m)
        settle_jump(m)
    return False


def main():
    r = Reporter("JUMP-SFX", kind="GATE")
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()
        neutralize_ai(m)

        leo = 12
        load_leo_onto_player(m, leo)
        neutralize_ai(m)
        base = word(m, Player_JumpRequestCount)
        r.check("loaded player has real jump data", byte(m, Player_JumpFCount) != 0)

        m.write_u8(ENTITY_BASES[0] + CHAR_SELECTED, 0)
        m.write_u16(ENTITY_BASES[0] + CHAR_THROW_ZPOS, 0)
        m.write_u16(ENTITY_BASES[0] + CHAR_THROW_ZVEL, 0)
        press_a(m)
        first = word(m, Player_JumpRequestCount)
        print(f"jump request counter: base={base} first={first} total={word(m, SemanticRequestCount)} trace={byte(m, TraceWriteIndex)}")
        r.check("grounded A emits exactly one JUMP request", first - base == 1)
        r.check("grounded A enters jump state", byte(m, ENTITY_BASES[0] + CHAR_SELECTED) == CHAR_SELECTED_JUMP)

        m.set_input(m.BTN_A, 20)
        m.pause()
        settle_jump(m)
        held = word(m, Player_JumpRequestCount)
        r.check("held A while airborne emits no duplicate", held == first)
        r.check("jump lands through normal gravity path", wait_for_land(m))

        base = held
        press_a(m)
        second = word(m, Player_JumpRequestCount)
        print(f"second jump request counter: base={base} second={second}")
        r.check("second distinct ground jump emits one new request", second - base == 1)
        r.check("second jump reaches jump state", byte(m, ENTITY_BASES[0] + CHAR_SELECTED) == CHAR_SELECTED_JUMP)

        # Ralf is the first playable roster entry and has no jump frames in
        # the authoritative roster data. This uses the real character-select
        # loader, not a synthetic Player_JumpFCount mutation.
        for _ in range(20):
            if byte(m, CharSelect_Index) == 0:
                break
            m.set_input(m.BTN_SELECT, 10)
            m.run_frames(20)
            m.pause()
        neutralize_ai(m)
        no_data = word(m, Player_JumpRequestCount)
        m.write_u8(ENTITY_BASES[0] + CHAR_SELECTED, 0)
        m.set_input(m.BTN_A, 1)
        m.pause()
        settle_jump(m)
        r.check("no-jump-data character emits no JUMP request", word(m, Player_JumpRequestCount) == no_data)

    r.finish()


if __name__ == "__main__":
    main()
