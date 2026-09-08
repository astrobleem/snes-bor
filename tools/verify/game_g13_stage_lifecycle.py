#!/usr/bin/env python3"""Bounded G13 lifecycle localization gate.This gate uses the established direct-WRAM death boundary used by G3 toisolate lifecycle ownership.  It does not claim organic combat death,continue UI, or the full stage-handoff campaign; those remain explicit gatesuntil the production combat fixture is wired for this slice."""import osimport syssys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))from _harness import (open_session, pasm_constant, pasm_constant_in,                      read_block, run_frames_exact, exact_input_edge, Reporter)from game_g13_camera_pause import setup, P1, P2, ZP_LENROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')GAMEOVER = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_GAMEOVER')LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')LIVES_START = pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START')P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')CONTINUE_TIMER = pasm_constant_in('src/core/game_state.pasm', 'GameOver_ContinueTimer')HP = pasm_constant('CHAR_HP')HP_MAX = pasm_constant('CHAR_HP_MAX')OUT1 = pasm_constant('G13_P1Out')OUT2 = pasm_constant('G13_P2Out')SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')def u8(m, a):    return read_block(m, a, 32)[0]def u16(m, a):    b = read_block(m, a, 32)    return b[0] | (b[1] << 8)def inert_npcs(m):    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))    for slot in range(2, 6):        b = P1 + slot * ZP_LEN        m.write_u8(b + HP, 0)def main():    r = Reporter('G13-STAGE-LIFECYCLE', kind='GATE')    with open_session(__file__) as m:        setup(m)        inert_npcs(m)        m.write_u8(LIVES, 1)        m.write_u8(P2_LIVES, 1)        m.write_u8(P1 + HP, HP_MAX)        m.write_u8(P2 + HP, 0)        run_frames_exact(m, 1)        p2_respawn = (u8(m, OUT2), u8(m, P2 + HP), u8(m, P2_LIVES), u16(m, GAME_STATE))        print('P2 death/respawn boundary:', p2_respawn, flush=True)        r.check('P2 respawns with remaining stock',                p2_respawn == (0, HP_MAX, 0, PLAYING))        m.write_u8(P2 + HP, 0)        run_frames_exact(m, 1)        p2_out = (u8(m, OUT2), u8(m, P2 + HP), u16(m, GAME_STATE))        print('P2 OUT boundary:', p2_out, flush=True)        r.check('P2 reaches OUT after stock exhaustion', p2_out == (1, 0, PLAYING))        exact_input_edge(m, m.BTN_START, 1, port=1)        p2_continue = (u8(m, OUT2), u8(m, P2 + HP), u8(m, P2_LIVES), u16(m, GAME_STATE))        print('P2 continue:', p2_continue, flush=True)        r.check('P2 continue restores only P2',                p2_continue == (0, HP_MAX, LIVES_START, PLAYING) and u8(m, LIVES) == 1)        # Both OUT must be the only 2P gameover condition.        exact_input_edge(m, 0, 2, port=0)        exact_input_edge(m, 0, 2, port=1)        m.write_u8(LIVES, 0)        m.write_u8(P2_LIVES, 0)        m.write_u8(P1 + HP, 0)        m.write_u8(P2 + HP, 0)        run_frames_exact(m, 1)        both = (u8(m, OUT1), u8(m, OUT2), u16(m, GAME_STATE), u16(m, CONTINUE_TIMER))        print('both OUT:', both, flush=True)        r.check('both OUT enters GAMEOVER', both[0:3] == (1, 1, GAMEOVER) and both[3] > 0)        # P2-only gameover continue must not resurrect P1.        exact_input_edge(m, m.BTN_START, 1, port=1)        cont = (u8(m, OUT1), u8(m, OUT2), u8(m, P1 + HP),                u8(m, P2 + HP), u16(m, GAME_STATE))        print('GAMEOVER P2 continue:', cont, flush=True)        r.check('GAMEOVER P2 continue is player-owned',                cont == (1, 0, 0, HP_MAX, PLAYING))    r.finish()if __name__ == '__main__':    main()
#!/usr/bin/env python3
"""Bounded G13 lifecycle localization gate.

Uses the established direct-WRAM death boundary to isolate lifecycle
ownership. It does not claim organic combat death or full stage handoff.
"""
import os
import sys
from contextlib import contextmanager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact, exact_input_edge, Reporter)
from game_g13_camera_pause import setup, P1, P2, ZP_LEN
from game_g13_combat_ai import (prepare_ai_fixture, NPC2, SELECTED,
                                ATTACK_VARIANT, HIT_APPLIED, P1_INVULN,
                                P2_INVULN, ACTOR_INVULN)

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAMEOVER = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_GAMEOVER')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
LIVES_START = pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
CONTINUE_TIMER = pasm_constant_in('src/core/game_state.pasm', 'GameOver_ContinueTimer')
HP = pasm_constant('CHAR_HP')
HP_MAX = pasm_constant('CHAR_HP_MAX')
OUT1 = pasm_constant('G13_P1Out')
OUT2 = pasm_constant('G13_P2Out')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')

def arm_legal_p2_hit(m, p2_hp, p2_lives):
    prepare_ai_fixture(m, 120, 220, 220, p1_hp=HP_MAX, p2_hp=p2_hp)
    m.write_u8(LIVES, LIVES_START)
    m.write_u8(P2_LIVES, p2_lives)
    m.write_u8(OUT1, 0)
    m.write_u8(OUT2, 0)
    m.write_u8(P1_INVULN, 255)
    m.write_u8(P2_INVULN, 0)
    m.write_u8(NPC2 + SELECTED, 2)
    m.write_u8(NPC2 + ATTACK_VARIANT, 0)
    m.write_u8(NPC2 + HIT_APPLIED, 0)
    m.write_u8(NPC2 + pasm_constant('CHAR_FRAME_INDEX'), 0xFF)
    m.write_u8(NPC2 + pasm_constant('CHAR_TICK_COUNTER'), 1)
    m.write_u8(ACTOR_INVULN + 2, 0)

def wait_p2_result(m, predicate, limit=12):
    for _ in range(limit):
        run_frames_exact(m, 1)
        if predicate():
            return True
    return False

def u8(m, a):
    return read_block(m, a, 32)[0]

def u16(m, a):
    b = read_block(m, a, 32)
    return b[0] | (b[1] << 8)

def inert_npcs(m):
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    for slot in range(2, 6):
        m.write_u8(P1 + slot * ZP_LEN + HP, 0)

def legacy_main():
    r = Reporter('G13-STAGE-LIFECYCLE', kind='GATE')
    @contextmanager
    def fresh():
        with open_session(__file__) as m:
            setup(m)
            inert_npcs(m)
            yield m

    with fresh() as m:
        m.write_u8(P1 + HP, HP_MAX)
        m.write_u8(P2 + HP, HP_MAX)
        m.write_u8(OUT1, 0); m.write_u8(OUT2, 0)
        m.write_u8(P2_LIVES, 1); m.write_u16(GAME_STATE, PLAYING)
        run_frames_exact(m, 4)
        stable = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u16(m, GAME_STATE))
        print('living P2 lives=1:', stable, flush=True)
        r.check('living P2 lives=1 is unchanged', stable == (HP_MAX, 0, 1, PLAYING))

    with fresh() as m:
        m.write_u8(P1 + HP, HP_MAX)
        m.write_u8(P2 + HP, HP_MAX)
        m.write_u8(OUT1, 0); m.write_u8(OUT2, 0)
        m.write_u8(P2_LIVES, 0); m.write_u16(GAME_STATE, PLAYING)
        run_frames_exact(m, 4)
        stable = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u16(m, GAME_STATE))
        print('living P2 lives=0:', stable, flush=True)
        r.check('living P2 lives=0 is unchanged', stable == (HP_MAX, 0, 0, PLAYING))

    with fresh() as m:
        arm_legal_p2_hit(m, 4, 1)
        pre = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u8(m, P2_INVULN))
        reached = wait_p2_result(m, lambda: u8(m, P2 + HP) == HP_MAX and u8(m, P2_LIVES) == 0)
        result = (u8(m, OUT2), u8(m, P2 + HP), u8(m, P2_LIVES), u16(m, GAME_STATE), u8(m, OUT1))
        print('legal P2 spare-life hit:', pre, result, flush=True)
        r.check('legal P2 spare-life attack fixture reached', pre == (4, 0, 1, 0))
        r.check('P2 spare-life death respawns', reached and result == (0, HP_MAX, 0, PLAYING, 0))

    with fresh() as m:
        arm_legal_p2_hit(m, 4, 0)
        pre = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u8(m, P2_INVULN))
        reached = wait_p2_result(m, lambda: u8(m, OUT2) == 1)
        result = (u8(m, OUT2), u8(m, P2 + HP), u8(m, P2_LIVES), u16(m, GAME_STATE), u8(m, OUT1), u8(m, P1 + HP))
        print('legal P2 zero-life hit:', pre, result, flush=True)
        r.check('legal P2 zero-life attack fixture reached', pre == (4, 0, 0, 0))
        r.check('P2 exhaustion leaves survivor active', reached and result == (1, 0, 0, PLAYING, 0, HP_MAX))

    with fresh() as m:
        arm_legal_p2_hit(m, 4, 1)
        m.write_u8(P2_INVULN, 255)
        before = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES))
        run_frames_exact(m, 8)
        after = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u16(m, GAME_STATE))
        print('no-hit invulnerability control:', before, after, flush=True)
        r.check('no-hit control has no lifecycle mutation', after == (64, 0, 1, PLAYING))
    r.finish()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True,
                        choices=('alive-lives1', 'alive-lives0',
                                 'lethal-lives1', 'lethal-lives0',
                                 'no-hit', 'p1-survivor'))
    case = parser.parse_args().case
    r = Reporter('G13-P2-DEATH-REGRESSION', kind='GATE')

    with open_session(__file__) as m:
        setup(m)
        inert_npcs(m)
        if case.startswith('alive'):
            lives = 1 if case == 'alive-lives1' else 0
            m.write_u8(P1 + HP, HP_MAX)
            m.write_u8(P2 + HP, HP_MAX)
            m.write_u8(OUT1, 0); m.write_u8(OUT2, 0)
            m.write_u8(P2_LIVES, lives)
            m.write_u16(GAME_STATE, PLAYING)
            run_frames_exact(m, 6)
            result = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u16(m, GAME_STATE))
            print(case, result, flush=True)
            r.check(case + ' unchanged', result == (HP_MAX, 0, lives, PLAYING))
        elif case.startswith('lethal'):
            lives = 1 if case == 'lethal-lives1' else 0
            arm_legal_p2_hit(m, 4, lives)
            pre = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u8(m, P2_INVULN))
            if lives:
                ok = wait_p2_result(m, lambda: u8(m, P2 + HP) == HP_MAX and u8(m, P2_LIVES) == 0)
                result = (u8(m, OUT2), u8(m, P2 + HP), u8(m, P2_LIVES), u16(m, GAME_STATE), u8(m, OUT1))
                expected = (0, HP_MAX, 0, PLAYING, 0)
            else:
                ok = wait_p2_result(m, lambda: u8(m, OUT2) == 1)
                result = (u8(m, OUT2), u8(m, P2 + HP), u8(m, P2_LIVES), u16(m, GAME_STATE), u8(m, OUT1), u8(m, P1 + HP))
                expected = (1, 0, 0, PLAYING, 0, HP_MAX)
            print(case, 'legal fixture', pre, 'result', result, flush=True)
            r.check(case + ' legal attack precondition', pre == (4, 0, lives, 0))
            r.check(case + ' lifecycle result', ok and result == expected)
        elif case == 'no-hit':
            arm_legal_p2_hit(m, 4, 1)
            m.write_u8(P2_INVULN, 255)
            before = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES))
            run_frames_exact(m, 8)
            result = (u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u16(m, GAME_STATE))
            print(case, before, result, flush=True)
            r.check('no-hit unchanged', result == (4, 0, 1, PLAYING))
        else:
            prepare_ai_fixture(m, 120, 220, 120, p1_hp=4, p2_hp=HP_MAX)
            m.write_u8(LIVES, 0); m.write_u8(P2_LIVES, 1)
            m.write_u8(OUT1, 0); m.write_u8(OUT2, 0)
            m.write_u8(P1_INVULN, 0); m.write_u8(P2_INVULN, 255)
            m.write_u8(NPC2 + SELECTED, 2)
            m.write_u8(NPC2 + ATTACK_VARIANT, 0)
            m.write_u8(NPC2 + HIT_APPLIED, 0)
            m.write_u8(NPC2 + pasm_constant('CHAR_FRAME_INDEX'), 0xFF)
            m.write_u8(NPC2 + pasm_constant('CHAR_TICK_COUNTER'), 1)
            m.write_u8(ACTOR_INVULN + 2, 0)
            ok = wait_p2_result(m, lambda: u8(m, OUT1) == 1)
            result = (u8(m, P1 + HP), u8(m, OUT1), u8(m, P2 + HP), u8(m, OUT2), u8(m, P2_LIVES), u16(m, GAME_STATE))
            print(case, result, flush=True)
            r.check('P1 survivor regression', ok and result == (0, 1, HP_MAX, 0, 1, PLAYING))
    r.finish()

if __name__ == '__main__':
    main()
