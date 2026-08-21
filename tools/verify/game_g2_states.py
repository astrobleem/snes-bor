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
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
CHAR_FRAME_INDEX = 9
LIVING_AI_ENTITY = 2  # JOE, entity 2 -- see phase11_damage.py/phase15's own choice


def frame_counter(m):
    b = read_block(m, NMI_FRAME_COUNTER, 32)
    return b[0] | (b[1] << 8)


def entity0_oam_y(m):
    block = read_block(m, 0, 32, mem_type='snesSpriteRam')
    return block[ENTITY0_OAM_SLOT * 4 + 1]


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
        # write phase11_damage.py uses for its own alive controls.
        m.write_memory('snesMemory', ENTITY_BASES[LIVING_AI_ENTITY] + CHAR_HP, f'{CHAR_HP_MAX:02X}')
        m.run_frames(5)
        m.pause()

        # --- Boot state is PLAYING, and gameplay is visibly running. ---
        boot_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'boot Game_State == GAME_STATE_PLAYING ({boot_state})',
                boot_state == GAME_STATE_PLAYING)
        r.check('entity 0 OAM visible (not hidden) while PLAYING',
                entity0_oam_y(m) != OAM_DEFAULT_Y)

        assert_frame_counter_advances(r, m, 'PLAYING')

        # --- PLAYING -> TITLE: one-shot OAM hide on the transition edge. ---
        set_game_state(m, GAME_STATE_TITLE)
        m.run_frames(30)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Game_State reads back as GAME_STATE_TITLE ({got_state})',
                got_state == GAME_STATE_TITLE)
        r.check('entity 0 OAM hidden (Y=$F0) after PLAYING -> TITLE transition',
                entity0_oam_y(m) == OAM_DEFAULT_Y)
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
                entity0_oam_y(m) == OAM_DEFAULT_Y)
        r.check('DMA queue has a free slot in PAUSED (not saturated)',
                dma_queue_has_free_slot(m))

        assert_frame_counter_advances(r, m, 'PAUSED')

        # --- PAUSED -> PLAYING: gameplay resumes, Core_Oam_Play uploads
        # real sprite positions again. ---
        set_game_state(m, GAME_STATE_PLAYING)
        m.run_frames(30)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Game_State reads back as GAME_STATE_PLAYING ({got_state})',
                got_state == GAME_STATE_PLAYING)
        r.check('entity 0 OAM visible again after PAUSED -> PLAYING transition',
                entity0_oam_y(m) != OAM_DEFAULT_Y)

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
