#!/usr/bin/env python3
"""plan_game.md Phase G3 gate: player death, lives, continues, game over
(core/game_state.pasm).

Forces PlayerEntity_Hp to 0 directly via WRAM write (same "safe to write
directly, nothing else races this cell at the moment of the write" pattern
tools/verify/phase11_damage.py already uses for AI entities) rather than
waiting for organic combat to do it -- forcing the exact moment is both
faster and, per this project's memory phase_g3_player_death, avoids the
organic version's own confound: natural AI combat during a long test run
can exhaust all lives and reach GAME_STATE_GAMEOVER on its own, which
would freeze gameplay mid-test in a way unrelated to whatever this gate
is trying to isolate.

Checked, all against real Mesen2 hardware state (WRAM + hardware OAM/PPU,
not engine self-consistency -- CLAUDE.md's standing rule):
  1. A death with lives remaining: Game_Lives decrements by exactly 1,
     Game_State stays GAME_STATE_PLAYING (auto-respawn, no menu needed),
     CHAR_HP is back at CHAR_HP_MAX, hit-stun/facing/animation-selection
     are all reset (not just HP -- plan_game.md 3's own "watch out" list),
     and Player_InvulnFrames is armed nonzero.
  2. Exhausting every remaining life (GAME_LIVES_START + 1 forced deaths
     total) reaches GAME_STATE_GAMEOVER, with GameOver_ContinueTimer armed.
  3. A continue (Start press, simulated via set_input) restores
     GAME_STATE_PLAYING, fresh Game_Lives, and full player HP.
  4. Animation actually resumed post-continue -- sampled at a PRIME frame
     stride (37, not 40) per memory phase15_fourth_character (a "round"
     stride can alias a character's own animation cycle period and read as
     frozen when it isn't); same pattern game_g2_states.py already uses.

Usage: python tools/verify/game_g3_death.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_GAMEOVER = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_GAMEOVER')
GAME_LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
GAME_LIVES_START = pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START')
GAMEOVER_CONTINUE_TIMER = pasm_constant_in('src/core/game_state.pasm', 'GameOver_ContinueTimer')
PLAYER_INVULN_FRAMES = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')

CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_FACING_LEFT = pasm_constant('CHAR_FACING_LEFT')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')

PLAYER_BASE = 0x7E0A00
PlayerEntity_Hp = PLAYER_BASE + CHAR_HP
PlayerEntity_HitStun = PLAYER_BASE + CHAR_HIT_STUN
PlayerEntity_FacingLeft = PLAYER_BASE + CHAR_FACING_LEFT
PlayerEntity_Selected = PLAYER_BASE + CHAR_SELECTED


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
    r = Reporter('G3', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        boot_lives = byte_at(m, GAME_LIVES)
        r.check(f'boot Game_Lives == GAME_LIVES_START ({boot_lives})',
                boot_lives == GAME_LIVES_START)

        # --- 1. A single death with lives remaining: auto-respawn. ---
        force_player_death(m)
        lives_after_1 = byte_at(m, GAME_LIVES)
        state_after_1 = word_at(m, GAME_STATE)
        hp_after_1 = byte_at(m, PlayerEntity_Hp)
        stun_after_1 = byte_at(m, PlayerEntity_HitStun)
        facing_after_1 = byte_at(m, PlayerEntity_FacingLeft)
        selected_after_1 = byte_at(m, PlayerEntity_Selected)
        invuln_after_1 = byte_at(m, PLAYER_INVULN_FRAMES)
        print(f'after 1st forced death: lives={lives_after_1} state={state_after_1} '
              f'hp={hp_after_1} stun={stun_after_1} facing={facing_after_1} '
              f'selected={selected_after_1} invuln={invuln_after_1}')
        r.check(f'Game_Lives decremented by 1 ({boot_lives} -> {lives_after_1})',
                lives_after_1 == boot_lives - 1)
        r.check('Game_State stays PLAYING (auto-respawn, no menu needed)',
                state_after_1 == GAME_STATE_PLAYING)
        r.check(f'player respawned at CHAR_HP_MAX ({hp_after_1})', hp_after_1 == CHAR_HP_MAX)
        r.check('respawn reset hit-stun to 0', stun_after_1 == 0)
        r.check('respawn reset facing to 0 (right)', facing_after_1 == 0)
        r.check('respawn reset animation-selection to 0 (idle)', selected_after_1 == 0)
        r.check('respawn armed post-respawn invulnerability', invuln_after_1 > 0)

        # --- 2. Exhaust every remaining life -> GAME OVER. Boot lives is
        # GAME_LIVES_START; one death already consumed above, so
        # GAME_LIVES_START more forced deaths exhausts the rest and tips
        # into GAME_STATE_GAMEOVER on the death that finds Game_Lives==0. ---
        for _ in range(GAME_LIVES_START):
            force_player_death(m)
        final_lives = byte_at(m, GAME_LIVES)
        final_state = word_at(m, GAME_STATE)
        continue_timer = word_at(m, GAMEOVER_CONTINUE_TIMER)
        print(f'after exhausting all lives: lives={final_lives} state={final_state} '
              f'continue_timer={continue_timer}')
        r.check(f'Game_State reaches GAME_STATE_GAMEOVER after the last life ({final_state})',
                final_state == GAME_STATE_GAMEOVER)
        r.check('continue countdown armed (GameOver_ContinueTimer > 0)', continue_timer > 0)

        # --- 3. Continue: Start press restores a playable state. ---
        m.set_input(m.BTN_START, 10)
        m.run_frames(10)
        m.pause()
        continued_state = word_at(m, GAME_STATE)
        continued_lives = byte_at(m, GAME_LIVES)
        continued_hp = byte_at(m, PlayerEntity_Hp)
        print(f'after Start (continue): state={continued_state} lives={continued_lives} '
              f'hp={continued_hp}')
        r.check('continue restores GAME_STATE_PLAYING', continued_state == GAME_STATE_PLAYING)
        r.check(f'continue restores fresh Game_Lives ({continued_lives})',
                continued_lives == GAME_LIVES_START)
        r.check(f'continue restores full player HP ({continued_hp})', continued_hp == CHAR_HP_MAX)

        # --- 4. Gameplay actually resumed post-continue, not just "some
        # state variable says PLAYING" -- sample the player's own
        # CHAR_FRAME_INDEX at a prime (37) stride, same anti-aliasing
        # reasoning as game_g2_states.py / phase11_damage.py. ---
        frame_samples = []
        for _ in range(6):
            m.run_frames(37)
            m.pause()
            frame_samples.append(byte_at(m, PLAYER_BASE + CHAR_FRAME_INDEX))
        print(f'player CHAR_FRAME_INDEX samples after continue: {frame_samples}')
        r.check('animation actually resumed after continue (frame index varies)',
                len(set(frame_samples)) > 1)

        fc_before = word_at(m, 0x7E5023)
        m.run_frames(60)
        m.pause()
        fc_after = word_at(m, 0x7E5023)
        r.check(f'Nmi_FrameCounter still advancing ({fc_before} -> {fc_after})',
                fc_after > fc_before)

    r.finish()


if __name__ == '__main__':
    main()
