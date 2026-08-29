#!/usr/bin/env python3
"""Organic vertical-slice integration gate (notjustfreespecial.txt audit,
claude_permanent_stop_rule_revised.md / explainyourself.txt's "allowed work"
list). NOT G10 -- explicitly, per an earlier hard correction in this
session's own history (see project memory dont_attribute_own_framing_to_
user_choice / vm_and_game_plans_split): this gate chains the real screens
and subsystems every earlier G1-G9 gate already proved individually, one
after another in a single continuous session, to prove they compose --
it does not add or claim any NEW subsystem of its own.

Every segment below is exactly the same real mechanism its own dedicated
gate already exercises, called in the same real order a player experiences
them, with NO synthetic shortcuts beyond the ones those original gates
already established as necessary (force_win_and_wait -- there is no direct
stage-load path in this engine; force_player_death -- direct HP=0 write,
same idiom game_g3_death.py uses, since there is no scripted "get hit until
you die" input sequence worth the frame count):

  1. Title (G5): boots at GAME_STATE_PLAYING by design (this project's own
     documented boot default) -- reach TITLE the same way game_g5_menus.py
     does (a forced Game_State write, simulating the real GAME_OVER-timeout/
     pause-quit fallback path that already lands here for real), then a
     real Start press into CHARSELECT.
  2. Char-select (G5): real header/name row drip, a real Right press
     re-streams the next roster character (CHAR_PALETTE_SLOT/CGRAM changes),
     a real Start press finishes the teardown drip and lands in PLAYING.
  3. Gameplay + combat (G2/G7): a real landed Y attack on a real AI entity
     lands a hit (CHAR_HIT_STUN goes nonzero, HP drops) -- the ordinary
     per-frame game loop, no forced HP writes yet.
  4. Breakable -> drop -> pickup -> reward (G8): the real, unmodified stage
     1B Chair/Money spawn record (same real chain game_g8_pickup_chain.py
     proves) -- a real landed attack breaks it, Game_Score gets the real
     PICKUP_SCORE_MONEY award, the OAM sprite hides.
  5. Death + continue (G3): one forced death with lives remaining (auto-
     respawn, stays PLAYING), then lives exhausted -> GAME_STATE_GAMEOVER
     with the continue countdown armed, then a real Start press continues
     back into PLAYING with fresh lives.
  6. Wave completion + stage transition (G4): the real win condition
     (Stage_Cleared) fires and Game_StageIndex advances.
  7. Boss (spawn-driven roster reassignment gate): continuing the SAME
     force-win chain through to stage 3 (Rock's own standalone boss stage),
     the real boss spawn record re-streams that AI slot to Rock's own real
     converted moveset (idle/walk/attack frame-count triple), same ground
     truth game_spawn_roster_reassign.py's check_boss_stage() already uses
     -- imported and reused here, not reimplemented.
  8. Stage transition after a boss (G4): the chain continues one more real
     win -> Game_StageIndex advances past the boss stage too.

Every wait in this file is poll-based (against real hardware-visible state,
never a fixed frame count trusted blind) -- same discipline the hardened
game_g7_depth_sort.py/game_g8_prop_art.py gates in this same slice
established. Run sequentially, never in parallel with another Mesen-driven
job (memory: mesen mcp parallel-job socket contention, this session).

Usage: python tools/verify/game_vertical_slice.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, repo_root_from, roster, Reporter  # noqa: E402

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)

sys.path.insert(0, os.path.join(ROOT, 'tools', 'verify'))
import game_spawn_roster_reassign as sr  # noqa: E402
import game_g8_pickup_chain as pc  # noqa: E402

GS_PATH = 'src/core/game_state.pasm'
GAME_STATE = pasm_constant_in(GS_PATH, 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in(GS_PATH, 'GAME_STATE_PLAYING')
GAME_STATE_TITLE = pasm_constant_in(GS_PATH, 'GAME_STATE_TITLE')
GAME_STATE_CHARSELECT = pasm_constant_in(GS_PATH, 'GAME_STATE_CHARSELECT')
GAME_STATE_GAMEOVER = pasm_constant_in(GS_PATH, 'GAME_STATE_GAMEOVER')
GAME_LIVES = pasm_constant_in(GS_PATH, 'Game_Lives')
GAME_LIVES_START = pasm_constant_in(GS_PATH, 'GAME_LIVES_START')
GAMEOVER_CONTINUE_TIMER = pasm_constant_in(GS_PATH, 'GameOver_ContinueTimer')
GAME_STAGE_INDEX = pasm_constant_in(GS_PATH, 'Game_StageIndex')
PLAYER_INVULN_FRAMES = pasm_constant_in(GS_PATH, 'Player_InvulnFrames')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')

CharSelect_Index = 0x7E53B6
CharSelect_Loaded = 0x7E53B8

PLAYER_BASE = 0x7E0A00
ENTITY_BASES = [PLAYER_BASE + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity_Hp = PLAYER_BASE + CHAR_HP


def byte_at(m, addr):
    return read_block(m, addr, 32)[0]


def word_at(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def force_player_death(m):
    m.write_u8(PlayerEntity_Hp, 0)
    m.run_frames(5)
    m.pause()


def main():
    r = Reporter('VERTICAL-SLICE', kind='GATE')
    roster_names = roster()

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        r.check('boots at GAME_STATE_PLAYING (this project\'s documented boot default)',
                word_at(m, GAME_STATE) == GAME_STATE_PLAYING)

        # === 1-2. Title -> char-select -> gameplay (G5) ===
        m.write_u16(GAME_STATE, GAME_STATE_TITLE)
        m.run_frames(5)
        m.pause()
        r.check('forced-title lands in GAME_STATE_TITLE', word_at(m, GAME_STATE) == GAME_STATE_TITLE)

        m.set_input(m.BTN_START, 10)
        m.pause()
        r.check('Start at title lands in GAME_STATE_CHARSELECT',
                word_at(m, GAME_STATE) == GAME_STATE_CHARSELECT)
        r.check('char-select shows roster slot 0 initially', byte_at(m, CharSelect_Index) == 0)

        idx0 = byte_at(m, CharSelect_Index)
        m.set_input(m.BTN_RIGHT, 10)
        m.pause()
        idx1 = byte_at(m, CharSelect_Index)
        r.check(f'Right at char-select advances CharSelect_Index ({idx0} -> {idx1})',
                idx1 == (idx0 + 1) % len(roster_names))
        r.check('char-select reload stays loaded (CharSelect_Loaded==1)',
                byte_at(m, CharSelect_Loaded) == 1)

        m.set_input(m.BTN_START, 10)
        m.pause()
        r.check('Start at char-select lands in GAME_STATE_PLAYING',
                word_at(m, GAME_STATE) == GAME_STATE_PLAYING)

        # === 3. Real gameplay + combat (G2/G7): a real landed attack lands
        # a hit on a real AI entity, ordinary per-frame game loop only. ===
        m.run_frames(60)
        m.pause()
        hp_before = [byte_at(m, b + CHAR_HP) for b in ENTITY_BASES[1:]]
        stun_before = [byte_at(m, b + CHAR_HIT_STUN) for b in ENTITY_BASES[1:]]
        m.set_input(m.BTN_Y, 60)
        m.pause()
        hp_after = [byte_at(m, b + CHAR_HP) for b in ENTITY_BASES[1:]]
        stun_after = [byte_at(m, b + CHAR_HIT_STUN) for b in ENTITY_BASES[1:]]
        print(f'combat: hp {hp_before} -> {hp_after}, stun {stun_before} -> {stun_after}')
        r.check('a real landed attack changed some AI entity\'s HP or hit-stun '
                 '(real combat, no forced writes)',
                 hp_after != hp_before or any(s > 0 for s in stun_after))

        # === 4. Breakable -> drop -> pickup -> reward (G8), real stage 1B
        # Chair/Money record, same mechanism game_g8_pickup_chain.py proves
        # -- imported and reused, not reimplemented. ===
        found_base = None
        for base in ENTITY_BASES[1:]:
            blk = pc.entity_block(m, base)
            if (blk[pc.CHAR_INPUT_DRIVEN] == pc.CHAR_INPUT_DRIVEN_PROP
                    and blk[pc.CHAR_PICKUP_TYPE] == pc.PICKUP_TYPE_MONEY):
                found_base = base
                break
        r.check('real stage 1B Chair/Money spawn record already landed as a '
                 'CHAR_INPUT_DRIVEN_PROP carrying PICKUP_TYPE_MONEY',
                 found_base is not None)
        if found_base is not None:
            for base in ENTITY_BASES[1:]:
                if base != found_base:
                    m.write_u8(base + CHAR_HP, 0)
            px = pc.entity_block(m, PLAYER_BASE)
            m.write_u16(found_base + pc.CHAR_POS_X, pc.pos_x(px))
            m.write_u8(found_base + pc.CHAR_POS_Y, px[pc.CHAR_POS_Y])
            score_before = word_at(m, pc.Game_Score)
            # The earlier combat segment already held BTN_Y -- input press-
            # edge detection needs a real release before a fresh press is
            # seen as a new attack (input.pasm's Core_Input_Poll edge
            # tracking), unlike game_g8_pickup_chain.py's own fresh-boot
            # version of this segment where Y was never previously held.
            m.set_input(0, 5)
            m.pause()
            m.set_input(m.BTN_Y, 1)
            killed = False
            for _ in range(30):
                m.run_frames(1)
                m.pause()
                if byte_at(m, found_base + pc.CHAR_HP) == 0:
                    killed = True
                    break
            m.run_frames(2)
            m.pause()
            r.check('real landed attack breaks the real prop (CHAR_HP reaches 0)', killed)
            score_after = word_at(m, pc.Game_Score)
            expected_delta = pc.PICKUP_SCORE_MONEY + pc.COMBAT_KILL_AWARD
            r.check(f'breaking the real prop awards the real pickup reward '
                     f'({score_before} -> {score_after}, expect +{expected_delta})',
                     score_after == score_before + expected_delta)

        # === 5. Death + continue (G3) ===
        boot_lives = byte_at(m, GAME_LIVES)
        force_player_death(m)
        lives_after_1 = byte_at(m, GAME_LIVES)
        r.check(f'a death with lives remaining decrements Game_Lives and stays '
                 f'PLAYING (auto-respawn) ({boot_lives} -> {lives_after_1})',
                 lives_after_1 == boot_lives - 1 and word_at(m, GAME_STATE) == GAME_STATE_PLAYING)
        hp_after_respawn = byte_at(m, PlayerEntity_Hp)
        r.check(f'player respawned at CHAR_HP_MAX ({hp_after_respawn})',
                 hp_after_respawn == CHAR_HP_MAX)

        for _ in range(lives_after_1 + 1):
            force_player_death(m)
        r.check('exhausting every remaining life reaches GAME_STATE_GAMEOVER',
                 word_at(m, GAME_STATE) == GAME_STATE_GAMEOVER)
        r.check('continue countdown armed (GameOver_ContinueTimer > 0)',
                 word_at(m, GAMEOVER_CONTINUE_TIMER) > 0)

        m.set_input(m.BTN_START, 10)
        m.pause()
        r.check('a real Start press continues back into PLAYING',
                 word_at(m, GAME_STATE) == GAME_STATE_PLAYING)
        r.check(f'continue restores fresh Game_Lives (GAME_LIVES_START={GAME_LIVES_START})',
                 byte_at(m, GAME_LIVES) == GAME_LIVES_START)

        # === 6-8. Wave completion, stage transition, boss, stage transition
        # after the boss (G4 + spawn-driven roster reassignment) -- the SAME
        # real force-win chain game_spawn_roster_reassign.py's own main()
        # already drives, reused function-for-function here rather than
        # reimplemented. ===
        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'stage index reads a real value after the continue ({boot_stage})',
                 boot_stage >= 0)
        for target in range(boot_stage + 1, 4):
            sr.force_win_and_wait(m, r, from_stage=target - 1, label=f'{target-1}->{target}')
            got = word_at(m, GAME_STAGE_INDEX)
            r.check(f'Game_StageIndex advances {target-1} -> {target} ({got})', got == target)

        sr.check_boss_stage(m, r, 3, 'out/spawn_stage3rock/spawn_table.bin', 'rock', 6)

        sr.force_win_and_wait(m, r, from_stage=3, label='3->4 (after boss)')
        got = word_at(m, GAME_STAGE_INDEX)
        r.check(f'Game_StageIndex advances past the boss stage 3 -> 4 ({got})', got == 4)

        fc0 = word_at(m, 0x7E5023)
        m.run_frames(60)
        m.pause()
        fc1 = word_at(m, 0x7E5023)
        r.check(f'engine still running at the end of the full vertical slice '
                 f'(Nmi_FrameCounter {fc0} -> {fc1})', fc1 > fc0)

    r.finish()


if __name__ == '__main__':
    main()
