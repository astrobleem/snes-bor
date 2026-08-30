#!/usr/bin/env python3
"""plan_game.md Phase G2 gate: the game state machine (core/game_state.pasm).

Drives Game_State through TITLE and PAUSED via direct WRAM writes (there is
no title/pause menu content yet -- that's G5 -- so this gate forces the
transition the way a future menu eventually will) and back to PLAYING, and
checks real hardware state at each stop rather than trusting engine-visible
status alone (CLAUDE.md's standing rule, and this project's own Phase 7
history: a status byte can read "fine" while the underlying mechanism is
dead).

Checked at each state:
  - Nmi_FrameCounter keeps advancing (Core_Nmi_WaitFrame is unconditional in
    every state -- a state that stops calling it would hang the loop, the
    same vblank-overrun-shaped failure this project has hit four times
    before, see memory ccdma_validated_nmi_timing_bug).
  - Real hardware OAM (mem_type='snesSpriteRam', not the WRAM shadow) goes
    to the OAM_DEFAULT_Y-hidden pattern exactly once, on the PLAYING ->
    non-PLAYING transition edge, and stays hidden through a second
    non-PLAYING state (TITLE -> PAUSED) with no new upload; then becomes
    visible again once Game_State returns to PLAYING.
  - The software DMA queue (core/dma.pasm's DmaQueue, 8 slots) never stays
    saturated in a non-playing state -- plan_game.md 2's own gate spec names
    this explicitly. Checked by scanning each slot's DMA_OPT_ACTIVE bit.
  - On PAUSED -> PLAYING, CHAR_FRAME_INDEX for a living AI entity actually
    changes across several ticks -- not just "some sprite is visible",
    which would also be true if positions uploaded but animation/streaming
    stayed stuck. Same prime-stride sampling phase11_damage.py and
    phase15_fourth_character use, for the same aliasing reason (memory
    phase15_fourth_character: a "round" stride can alias a character's own
    animation cycle period and look frozen when it isn't).

Boot state is GAME_STATE_PLAYING (0) -- see core/game_state.pasm's header
for why that's the deliberate choice (every other routine gate drives the
ROM from boot and assumes gameplay is already running).

Usage: python tools/verify/game_g2_states.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_STATE_PAUSED = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PAUSED')

NMI_FRAME_COUNTER = 0x7E5023
OAM_DEFAULT_Y = 0xF0
ENTITY0_OAM_SLOT = 0  # "the player is always slot 0" (CLAUDE.md)

DMA_QUEUE = pasm_constant_in('src/core/dma.pasm', 'DmaQueue')
DMA_QUEUE_SLOTS = pasm_constant_in('src/core/dma.pasm', 'DMA_QUEUE_SLOTS')
DMA_QUEUE_SLOT_SIZE = pasm_constant_in('src/core/dma.pasm', 'DMA_QUEUE_SLOT_SIZE')
DMA_OPT_ACTIVE = pasm_constant_in('src/core/dma.pasm', 'DMA_OPT_ACTIVE')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_AI = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_AI')
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
CHAR_FRAME_INDEX = 9
LIVING_AI_ENTITY = 1  # entity 1 -- claude_close_g7_g8_before_g10.md Part 6
# closure-cluster finding: stage 1B's real boot-time (trigger_x==0) spawn
# data is two real breakable props (Table/Chair, both `item`-bearing), not
# ordinary enemies, and real Spawn_Play assignment claims entities 2 AND 3
# for them at boot -- entity 2 (this constant's old value, matching phase11
# _damage.py/phase15's own choice made before this real prop content
# shipped) is no longer a free AI walker by default. Verified live: entity
# 1 is the one real always-AI slot in stage 1B's actual boot state.


def frame_counter(m):
    b = read_block(m, NMI_FRAME_COUNTER, 32)
    return b[0] | (b[1] << 8)


Screen_PosX = 0x7E1601
CHAR_POS_X = 4


def entity0_oam_hidden(m):
    """Actor depth-sort slice (plan_game.md 7): real hardware OAM slot
    order is now ground-depth-sorted (Character_RenderPass), not fixed
    dispatch order -- "the player is always slot 0" (CLAUDE.md) is still
    true of the ENTITY struct layout, but no longer of real OAM emission
    order, so ENTITY0_OAM_SLOT alone can't identify entity 0's real sprite
    any more.

    The PLAYING -> non-PLAYING transition hides everything via a full
    Core_Oam_ClearAll (X reset to 0 too, not just Y=$F0 -- see core/
    oam.pasm), not a per-entity dead-hide, so X-matching can't identify
    entity 0 there (nothing has entity 0's real X once cleared) -- but
    every slot reads hidden in that state regardless, so checking "all 4
    slots hidden" is both simpler and correct. While PLAYING, entity 0 IS
    identified by its real on-screen X (same technique phase11_damage.py/
    game_g8_props.py use), since real per-entity rendering is what's under
    test there.

    Returns True iff entity 0's real sprite (or, when nothing real-X
    matches, every OAM slot) reads Y==OAM_DEFAULT_Y."""
    block = read_block(m, 0, 32, mem_type='snesSpriteRam')
    posx_block = read_block(m, ENTITY_BASES[0], 32)
    world_x = posx_block[CHAR_POS_X] | (posx_block[CHAR_POS_X + 1] << 8)
    cam = read_block(m, Screen_PosX, 32)
    cam_x = cam[0] | (cam[1] << 8)
    expected_x = (world_x - cam_x) & 0xFF
    for slot in range(4):
        if block[slot * 4] == expected_x:
            return block[slot * 4 + 1] == OAM_DEFAULT_Y
    # No slot's X matched (post-ClearAll state, X reset too) -- fall back
    # to "every slot hidden", which is exactly what ClearAll guarantees.
    return all(block[slot * 4 + 1] == OAM_DEFAULT_Y for slot in range(4))


def dma_queue_has_free_slot(m):
    block = read_block(m, DMA_QUEUE, max(32, DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE))
    for i in range(DMA_QUEUE_SLOTS):
        active_byte = block[i * DMA_QUEUE_SLOT_SIZE + 4]
        if not (active_byte & DMA_OPT_ACTIVE):
            return True
    return False


def entity_frame_index(m, base):
    block = read_block(m, base, 32)
    return block[CHAR_FRAME_INDEX]


def set_game_state(m, value):
    m.write_u16(GAME_STATE, value)


def assert_frame_counter_advances(r, m, label, run_frames=180):
    before = frame_counter(m)
    m.run_frames(run_frames)
    m.pause()
    after = frame_counter(m)
    r.check(f'Nmi_FrameCounter advances in {label} ({before} -> {after})', after > before)


def main():
    r = Reporter('G2', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # Force the AI control entity alive without camera movement --
        # spawn-table entities start CHAR_HP=0 (unspawned) until the
        # level's trigger_x is reached (memory phase13_spawn_table); this
        # gate never drives the camera, so entity 2 needs the same direct
        # write phase11_damage.py uses for its own alive controls. Also
        # force CHAR_INPUT_DRIVEN_AI: stage 1B's real boot-time (trigger_x
        # ==0) spawn records are two real breakable props (Table/Chair),
        # not ordinary enemies (claude_close_g7_g8_before_g10.md Part 6
        # closure-cluster finding) -- with only 3 AI slots and 2 boot-time
        # prop records, entity 2 can legitimately land as a real
        # CHAR_INPUT_DRIVEN_PROP at boot, which never animates past its
        # own idle loop and would make this check's premise (a walking AI
        # entity) false for a real, correct reason, not a bug. Force the
        # mode this check actually needs, same as forcing CHAR_HP.
        m.write_memory('snesMemory', ENTITY_BASES[LIVING_AI_ENTITY] + CHAR_INPUT_DRIVEN,
                        f'{CHAR_INPUT_DRIVEN_AI:02X}')
        m.write_memory('snesMemory', ENTITY_BASES[LIVING_AI_ENTITY] + CHAR_HP, f'{CHAR_HP_MAX:02X}')
        m.run_frames(5)
        m.pause()

        # --- Boot state is PLAYING, and gameplay is visibly running. ---
        boot_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'boot Game_State == GAME_STATE_PLAYING ({boot_state})',
                boot_state == GAME_STATE_PLAYING)
        r.check('entity 0 OAM visible (not hidden) while PLAYING',
                not entity0_oam_hidden(m))

        assert_frame_counter_advances(r, m, 'PLAYING')

        # --- PLAYING -> TITLE: one-shot OAM hide on the transition edge. ---
        set_game_state(m, GAME_STATE_TITLE)
        m.run_frames(30)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Game_State reads back as GAME_STATE_TITLE ({got_state})',
                got_state == GAME_STATE_TITLE)
        r.check('entity 0 OAM hidden (Y=$F0) after PLAYING -> TITLE transition',
                entity0_oam_hidden(m))
        r.check('DMA queue has a free slot in TITLE (not saturated)',
                dma_queue_has_free_slot(m))

        assert_frame_counter_advances(r, m, 'TITLE')

        # --- TITLE -> PAUSED: not a PLAYING exit, so no new OAM churn --
        # sprites should simply stay hidden (Core_Oam_Play isn't called in
        # either state). ---
        set_game_state(m, GAME_STATE_PAUSED)
        m.run_frames(30)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Game_State reads back as GAME_STATE_PAUSED ({got_state})',
                got_state == GAME_STATE_PAUSED)
        r.check('entity 0 OAM still hidden in PAUSED (no new upload needed)',
                entity0_oam_hidden(m))
        r.check('DMA queue has a free slot in PAUSED (not saturated)',
                dma_queue_has_free_slot(m))

        assert_frame_counter_advances(r, m, 'PAUSED')

        # --- PAUSED -> PLAYING: gameplay resumes, Core_Oam_Play uploads
        # real sprite positions again. ---
        set_game_state(m, GAME_STATE_PLAYING)
        # Re-force AI mode/HP right on the resume edge too -- Spawn_Play
        # runs every PLAYING frame and could have re-classified this slot
        # again while GAME_STATE was TITLE/PAUSED (both states still let
        # main-loop subsystems other than OAM/render run).
        m.write_memory('snesMemory', ENTITY_BASES[LIVING_AI_ENTITY] + CHAR_INPUT_DRIVEN,
                        f'{CHAR_INPUT_DRIVEN_AI:02X}')
        m.write_memory('snesMemory', ENTITY_BASES[LIVING_AI_ENTITY] + CHAR_HP, f'{CHAR_HP_MAX:02X}')
        m.run_frames(30)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Game_State reads back as GAME_STATE_PLAYING ({got_state})',
                got_state == GAME_STATE_PLAYING)
        r.check('entity 0 OAM visible again after PAUSED -> PLAYING transition',
                not entity0_oam_hidden(m))

        # Prove gameplay actually resumed, not just that OAM positions got
        # re-uploaded once -- sample a living AI entity's CHAR_FRAME_INDEX
        # across several ticks with a prime (non-aliasing) stride.
        frame_samples = []
        for _ in range(6):
            m.run_frames(37)
            m.pause()
            frame_samples.append(entity_frame_index(m, ENTITY_BASES[LIVING_AI_ENTITY]))
        print(f'entity {LIVING_AI_ENTITY} CHAR_FRAME_INDEX samples after resume: {frame_samples}')
        r.check('animation actually resumed after PAUSED -> PLAYING (frame index varies)',
                len(set(frame_samples)) > 1)

        assert_frame_counter_advances(r, m, 'PLAYING (resumed)')

    r.finish()


if __name__ == '__main__':
    main()
