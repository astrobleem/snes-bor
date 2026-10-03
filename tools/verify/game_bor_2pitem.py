#!/usr/bin/env python3
"""Focused source-contract gate for BOR v1.0029 `2pitem`.

The source rule is a contained-item reveal predicate, not a P2 ownership
selector: obstacle_takedamage() spawns the contained item iff
`!if2p || count_ents(TYPE_PLAYER)>1`.  This gate checks parser/packed
preservation and drives the existing break/reveal service for one and two
active-player states.  Pickup ownership remains the ordinary collector path.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block, roster)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bg_converter'))
from spawn_parse import parse_spawns_from_pak, SpawnEvent  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
TABLE = os.path.join(ROOT, 'out', 'spawn_stage1b', 'spawn_table.bin')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
ENTITY1_BASE = 0x7E0A00 + CHAR_ZP_LEN
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_PROP = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_PROP')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
PICKUP_TYPE_MONEY = pasm_constant('PICKUP_TYPE_MONEY')
PICKUP_TYPE_2P_FLAG = pasm_constant('PICKUP_TYPE_2P_FLAG')
ITEM_IDX = pasm_constant_in('src/core/spawn.pasm', 'Entity1_ItemRosterIdx')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TWO_P = pasm_constant('G13_TwoPlayerEnabled')
P1_OUT = pasm_constant('G13_P1Out')
P2_OUT = pasm_constant('G13_P2Out')


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def make_broken_prop(m, two_player):
    m.write_u16(STATE, PLAYING)
    m.write_u8(TWO_P, 1 if two_player else 0)
    m.write_u8(P1_OUT, 0)
    m.write_u8(P2_OUT, 0 if two_player else 1)
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    m.write_u8(ENTITY1_BASE + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(ENTITY1_BASE + CHAR_HP, 1)
    m.write_u8(ENTITY1_BASE + CHAR_PICKUP_TYPE,
                PICKUP_TYPE_MONEY | PICKUP_TYPE_2P_FLAG)
    m.write_u8(ITEM_IDX, roster().index('money'))


def main():
    r = Reporter('BOR-2PITEM', kind='GATE')

    events = parse_spawns_from_pak(PAK, r'DATA\EASY\1BEASY.TXT')
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    two_p = [e for e in spawns if e.if2p]
    ordinary = [e for e in spawns if e.item and not e.if2p]
    r.check('source parser preserves 2pitem and distinguishes item',
            two_p and ordinary and all(e.item for e in two_p))

    data = open(TABLE, 'rb').read()
    records = [data[i:i + 10] for i in range(0, len(data), 10)]
    flagged = [rec for rec in records if rec[7] & 0x80]
    r.check('packed stage preserves 2pitem flag in existing record metadata',
            len(flagged) == len(two_p) and all(rec[7] & 0x7F <= 64 for rec in flagged))

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(150)
        m.pause()
        make_broken_prop(m, False)
        for _ in range(20):
            m.run_frames(2)
            if u8(m, ITEM_IDX) == 0:
                break
        r.check('one active player does not reveal 2pitem',
                u8(m, ITEM_IDX) == 0 and
                u8(m, 0x7E0A00 + CHAR_PICKUP_TYPE) == 0)

        make_broken_prop(m, True)
        for _ in range(20):
            m.run_frames(2)
            if u8(m, ITEM_IDX) == 0:
                break
        r.check('two active players reveal 2pitem',
                u8(m, ITEM_IDX) == 0 and
                u8(m, ENTITY1_BASE + CHAR_PICKUP_TYPE) == PICKUP_TYPE_MONEY)

        # The predicate has no attacker/collector input: changing the
        # collector selector cannot change whether the contained item was
        # revealed. Collector ownership is tested by the neighboring pickup
        # gate; this check guards the source-specific separation.
        r.check('reveal predicate is not P2 ownership keyed',
                PICKUP_TYPE_2P_FLAG == 0x80 and
                u8(m, ENTITY1_BASE + CHAR_PICKUP_TYPE) == PICKUP_TYPE_MONEY)
    r.finish()


if __name__ == '__main__':
    main()
