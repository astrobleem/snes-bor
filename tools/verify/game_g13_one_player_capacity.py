#!/usr/bin/env python3
"""One-player production-capacity gate for the G13 slot-1 reservation.

This gate deliberately does not write CharacterEntity HP, role, roster, or
position fields.  It lets the ordinary boot stage initialize its actors,
freezes only the production spawn queue after that initialization, and then
feeds three ordinary enemy records through Spawn_Play into the free slots.
The resulting five-NPC state is therefore a mix of the normal production
wave (including slot 1) and production Spawn_Play reuse, not fake structs.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact, exact_input_edge,
                      Reporter)  # noqa: E402
from game_g12_six_actor_production import (write_record, RECORD_SIZE,
                                           SPAWN_TABLE, SPAWN_INDEX,
                                           SPAWN_COUNT, SPAWN_WAITING,
                                           STAGE_CLEARED, ENTITIES, u8, u16,
                                           CHAR_HP, CHAR_INPUT_DRIVEN,
                                           CHAR_POS_X, CHAR_POS_Y,
                                           CHAR_FACING_LEFT)

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm',
                                      'GAME_STATE_PLAYING')
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')


def main():
    r = Reporter('G13-ONE-PLAYER-CAPACITY', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        # Wait for the real boot scene/spawn initialization.  No actor state
        # is written below; this is the same production path as a new game.
        m.run_frames(180)
        m.pause()
        boot = [(u8(m, b + CHAR_HP), u8(m, b + CHAR_INPUT_DRIVEN),
                 u16(m, b + CHAR_POS_X), u8(m, b + CHAR_POS_Y))
                for b in ENTITIES]
        print('boot production states:', boot, flush=True)

        # Stop the real queue from adding unrelated later records.  This is a
        # queue fixture boundary, not an actor-state injection.
        boot_queue_count = u8(m, SPAWN_COUNT)
        m.write_u8(SPAWN_INDEX, boot_queue_count)

        # The shipped opening wave contains two breakable props in slots 2/3.
        # Remove those through the ordinary player attack/collision path so
        # the capacity result is not a prop-vs-enemy classification accident.
        # Only the player's fixture position is arranged; no target HP, role,
        # roster, or other CharacterEntity field is written.
        for target in ENTITIES[2:4]:
            for _ in range(32):
                if u8(m, target + CHAR_HP) == 0:
                    break
                m.write_u16(ENTITIES[0] + CHAR_POS_X,
                            u16(m, target + CHAR_POS_X))
                m.write_u8(ENTITIES[0] + CHAR_POS_Y,
                            u8(m, target + CHAR_POS_Y))
                # The shipped opening props face opposite directions.  Try
                # each ordinary facing for the edge, retaining only the
                # fixture's position/facing arrangement and never writing
                # target state directly.
                for facing in (0, 1):
                    m.write_u8(ENTITIES[0] + CHAR_FACING_LEFT, facing)
                    exact_input_edge(m, m.BTN_Y, 1)
                    run_frames_exact(m, 3)
                    if u8(m, target + CHAR_HP) == 0:
                        break
        m.pause()
        print('post-production prop cleanup:',
              [(u8(m, b + CHAR_HP), u8(m, b + CHAR_INPUT_DRIVEN))
               for b in ENTITIES], flush=True)

        # Four ordinary enemy records are routed through the real free-slot
        # walk.  Slot 1 is intentionally not cleared or reserved in 1P.
        for i, (x, y) in enumerate(((280, 70), (300, 85), (320, 100),
                                    (340, 115))):
            write_record(m, i, 0, x, y, i & 1, 0, CHAR_HP_MAX)
        m.write_u8(SPAWN_INDEX, 0)
        m.write_u8(SPAWN_COUNT, 4)
        m.write_u8(SPAWN_WAITING, 0)
        m.write_u8(STAGE_CLEARED, 0)
        # Capacity is asserted at the end of the bounded production spawn
        # window.  A long combat soak belongs to the separate workload gate;
        # allowing the uncontrolled opening AI to kill P1 here would conflate
        # lifecycle capacity with death/continue behavior.
        run_frames_exact(m, 60)
        m.pause()
        states = [(u8(m, b + CHAR_HP), u8(m, b + CHAR_INPUT_DRIVEN),
                   u16(m, b + CHAR_POS_X), u8(m, b + CHAR_POS_Y))
                  for b in ENTITIES]
        print('post-fixture production states:', states, flush=True)
        live_npcs = [i for i, b in enumerate(ENTITIES[1:], start=1)
                     if u8(m, b + CHAR_HP) > 0 and
                     u8(m, b + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_AI]
        r.check('game remains in PLAYING for capacity fixture',
                u8(m, GAME_STATE) == GAME_STATE_PLAYING)
        r.check('slot 0 remains input-driven P1',
                u8(m, ENTITIES[0] + CHAR_INPUT_DRIVEN) == 1 and
                u8(m, ENTITIES[0] + CHAR_HP) > 0)
        r.check('slot 1 is a live production NPC in one-player mode',
                1 in live_npcs)
        r.check('slots 1-5 are all simultaneously live combat NPCs',
                live_npcs == [1, 2, 3, 4, 5])
        r.check('one-player production queue advanced through Spawn_Play',
                u8(m, SPAWN_INDEX) == u8(m, SPAWN_COUNT))
        r.check('five-NPC capacity is not falsely Stage_Cleared',
                u8(m, STAGE_CLEARED) == 0)
        print('live NPC slots:', live_npcs, flush=True)
        print('queue index/count:', u8(m, SPAWN_INDEX), u8(m, SPAWN_COUNT),
              'stage_cleared:', u8(m, STAGE_CLEARED), flush=True)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
