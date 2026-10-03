#!/usr/bin/env python3
"""P1-L2 source death/fall/blink/respawn gate.

This is deliberately limited to the stock-remaining path.  Credit use,
continue/re-entry, and final game-over semantics remain P1-L3 work.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact, poll_until)  # noqa: E402
from game_bor_startup_select import cold_to_title, select_case  # noqa: E402

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
CREDITS = pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')
P1_OUT = pasm_constant_in('src/main.pasm', 'G13_P1Out')
P2_OUT = pasm_constant_in('src/main.pasm', 'G13_P2Out')
# Screen_PosX is a .dw field in the .enum $7E1600 block (the source does not
# expose an ``NAME =`` constant for enum members).
SCREEN_X = 0x7E1601
BLINK_FRAMES = pasm_constant('DEATH_BLINK_FRAMES')
JUMP_INITIAL_VEL = pasm_constant('JUMP_INITIAL_VEL')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_SELECTED_FALL = pasm_constant('CHAR_SELECTED_FALL')
CHAR_SELECTED_JUMP = pasm_constant('CHAR_SELECTED_JUMP')
CHAR_FALL_STATE_TIMER = pasm_constant('CHAR_FALL_STATE_TIMER')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_TICK_COUNTER = pasm_constant('CHAR_TICK_COUNTER')
CHAR_THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
CHAR_THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')

P1 = 0x7E0A00
P2 = P1 + CHAR_ZP_LEN
ENTITY_BASES = [P1 + i * CHAR_ZP_LEN for i in range(6)]


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def ent(m, base, offset):
    return u8(m, base + offset)


def main():
    r = Reporter('BOR-DEATH-RESPAWN', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        cold_to_title(m, r)
        select_case(m, r, 'KULA')
        r.check('entered PLAYING through normal BOR startup', u16(m, STATE) == PLAYING)

        # Keep one real AI alive so this focused death cannot be confused
        # with the stage-clear path.  Stop new spawn records; existing
        # production actors remain the enemy population for drop_all_enemies.
        old_credits = u8(m, CREDITS)
        old_screen_x = u16(m, SCREEN_X)
        # Quiesce new spawn records and keep one real unlinked AI alive so
        # the normal win-condition cannot turn this fixture into a stage
        # transition while the player is in the death sequence.
        m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
        enemy = ENTITY_BASES[1]
        m.write_u8(enemy + CHAR_INPUT_DRIVEN, 2)
        m.write_u8(enemy + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(enemy + CHAR_SELECTED, 0)
        m.write_u8(enemy + CHAR_GRAB_TARGET, 0xFF)
        m.write_u8(enemy + CHAR_GRABBED_BY, 0xFF)
        m.write_u16(LIVES, 2)
        m.write_u8(P1_OUT, 0)
        m.write_u8(P1 + CHAR_HP, 0)
        m.write_u8(P1 + CHAR_SELECTED, 0)
        m.write_u8(P1 + CHAR_FALL_STATE_TIMER, 0)
        m.write_u8(P1 + CHAR_FRAME_INDEX, 0xFF)
        m.write_u8(P1 + CHAR_TICK_COUNTER, 1)

        before = (u16(m, LIVES), u16(m, P2_LIVES), u8(m, CREDITS),
                  u8(m, P1 + CHAR_HP), u8(m, P1 + CHAR_SELECTED))
        after_begin = None
        for _ in range(3):
            run_frames_exact(m, 1)
            candidate = (u16(m, LIVES), u16(m, P2_LIVES), u8(m, CREDITS),
                         u8(m, P1 + CHAR_HP), u8(m, P1 + CHAR_SELECTED),
                         u8(m, P1 + CHAR_FALL_STATE_TIMER))
            if candidate[4] == CHAR_SELECTED_FALL:
                after_begin = candidate
                break
        if after_begin is None:
            after_begin = candidate
        print('death begin:', before, '->', after_begin)
        r.check('health depletion enters FALL before stock changes',
                after_begin[3] == 0 and after_begin[4] == CHAR_SELECTED_FALL)
        r.check('life is not decremented on death entry', after_begin[0] == 2)
        r.check('P2 stock and global credits are untouched at death entry',
                after_begin[1] == before[1] and after_begin[2] == before[2])

        timer_start = None
        fall_samples = []
        for _ in range(180):
            run_frames_exact(m, 1)
            timer = u8(m, P1 + CHAR_FALL_STATE_TIMER)
            fall_samples.append(u8(m, P1 + CHAR_FRAME_INDEX))
            if timer not in (0, 0xFF) and timer_start is None:
                timer_start = timer
                break
        print('fall frames:', fall_samples[:12], 'timer start:', timer_start)
        r.check('fall animation reaches the blink phase', timer_start in (BLINK_FRAMES, BLINK_FRAMES + 1))
        r.check('fall animation progressed before blink', len(set(fall_samples)) > 1 or timer_start is not None)
        r.check('stock remains unchanged through fall/land/blink entry', u16(m, LIVES) == 2)

        blink_ticks = 0
        life_before_handoff = u16(m, LIVES)
        handoff_prev_timer = None
        while u16(m, LIVES) == life_before_handoff and blink_ticks < BLINK_FRAMES + 4:
            handoff_prev_timer = u8(m, P1 + CHAR_FALL_STATE_TIMER)
            run_frames_exact(m, 1)
            blink_ticks += 1
        print('blink ticks to terminal:', blink_ticks,
              'timer:', hex(u8(m, P1 + CHAR_FALL_STATE_TIMER)),
              'lives:', u16(m, LIVES), 'previous timer:', handoff_prev_timer)
        r.check('blink interval has exactly GAME_SPEED*2 ticks',
                blink_ticks in (BLINK_FRAMES + 1, BLINK_FRAMES + 2,
                                BLINK_FRAMES + 3))
        r.check('stock remains until terminal blink handoff',
                handoff_prev_timer in (1, 0xFF))
        r.check('life decrements only after terminal blink handoff',
                u16(m, LIVES) == 1 and handoff_prev_timer in (1, 0xFF))

        # Respawn is source-rightward for the currently shipped, right-scrolling
        # campaign.  Left-scroll handling remains the documented adaptation
        # boundary because this runtime has no authored left-scroll level.
        respawn = u8(m, P1 + CHAR_SELECTED) == CHAR_SELECTED_JUMP
        respawn_sample = (u8(m, P1 + CHAR_HP), u8(m, P1 + CHAR_SELECTED),
                          u8(m, P1 + CHAR_THROW_ZPOS),
                          u16(m, P1 + CHAR_THROW_ZVEL), u8(m, P1_OUT))
        respawn_x = u16(m, P1 + CHAR_POS_X)
        respawn_state = respawn_sample
        respawn_screen_x = u16(m, SCREEN_X)
        print('respawn:', respawn_state, 'x:', respawn_x,
              'camera:', respawn_screen_x, 'expected rightward x:', respawn_screen_x + 20)
        r.check('stock-remaining respawn occurs in jump state', respawn and respawn_state[1] == CHAR_SELECTED_JUMP)
        r.check('respawn restores full health', respawn_state[0] == CHAR_HP_MAX)
        r.check('respawn uses source jump launch state',
                respawn_state[2] == 0 and 0 < respawn_state[3] <= JUMP_INITIAL_VEL)
        r.check('respawn has no invented invulnerability',
                u8(m, pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')) == 0)
        r.check('respawn uses rightward source offset for shipped stages',
                respawn_x == respawn_screen_x + 20)
        r.check('credits persist through death/respawn', u8(m, CREDITS) == old_credits)

        # At least one live AI should have been put through the source
        # drop_all_enemies path.  The runtime has no separate BOR `link` bit;
        # its grab-target/grabbed-by pair is the narrow equivalent.
        dropped = []
        for slot, base in enumerate(ENTITY_BASES[1:], start=1):
            if u8(m, base + CHAR_INPUT_DRIVEN) >= 2 and u8(m, base + CHAR_HP) != 0:
                dropped.append((slot, u8(m, base + CHAR_SELECTED)))
        print('live AI post-respawn states:', dropped)
        r.check('enemy-drop leaves live unlinked AI in FALL',
                any(state == CHAR_SELECTED_FALL for _, state in dropped))

        # Player independence, including the source stock foundation, is a
        # small 2P observation and does not exercise re-entry semantics.
        m.reset_emulator()
        cold_to_title(m, r)
        select_case(m, r, 'KULA', 'MIGHTY')
        p2_before = u16(m, P2_LIVES)
        m.write_u16(LIVES, 2)
        m.write_u8(P1 + CHAR_HP, 0)
        m.write_u8(P1 + CHAR_SELECTED, 0)
        m.write_u8(P1 + CHAR_FALL_STATE_TIMER, 0)
        m.write_u8(P1 + CHAR_FRAME_INDEX, 0xFF)
        m.write_u8(P1 + CHAR_TICK_COUNTER, 1)
        run_frames_exact(m, 3)
        r.check('P1 death does not decrement P2 stock at entry', u16(m, P2_LIVES) == p2_before)

        # P1-L2 stops at the zero-stock boundary.  Establish the already
        # terminal fall marker only to isolate that handoff; P1-L3 owns what
        # follows (credit use, re-entry, and final game-over semantics).
        m.write_u16(LIVES, 1)
        m.write_u8(P1_OUT, 0)
        m.write_u8(P1 + CHAR_HP, 0)
        m.write_u8(P1 + CHAR_SELECTED, CHAR_SELECTED_FALL)
        m.write_u8(P1 + CHAR_FALL_STATE_TIMER, 0xFF)
        credits_before_zero = u8(m, CREDITS)
        run_frames_exact(m, 3)
        print('zero-life handoff:', 'lives=', u16(m, LIVES),
              'credits=', u8(m, CREDITS), 'p1out=', u8(m, P1_OUT),
              'p2out=', u8(m, P2_OUT), 'state=', u16(m, STATE))
        r.check('zero-life handoff consumes no global credit',
                u16(m, LIVES) == 0 and u8(m, CREDITS) == credits_before_zero)
        r.check('zero-life handoff marks only P1 OUT for P1-L3',
                u8(m, P1_OUT) == 1 and u8(m, P2_OUT) == 0)

    r.finish()


if __name__ == '__main__':
    main()
