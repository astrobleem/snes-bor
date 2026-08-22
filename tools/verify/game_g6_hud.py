#!/usr/bin/env python3
"""plan_game.md Phase G6 gate: score, lives, and a real HUD.

Background (see this session's plan file / core/game_state.pasm's own G6
header): the HUD used to be 4 raw HP bars (a debug view) with no score, no
lives display, no stage number. This phase drops the 3 AI bars (no
"currently engaged enemy" concept exists without a boss -- see plan_game.md
G9) and adds SCORE/LIVES/STAGE text on the freed rows 1-3, plus a real
scoring system: Character_HitApply_VsEntity1/2/3 (the player-lands-a-hit
leaves) now jsr Game_Score_Award, which adds HIT_SCORE (+KILL_SCORE on a
kill) to Game_Score and awards +1 Game_Lives on crossing an
EXTEND_LIFE_SCORE multiple.

A REAL Y-button press (m.set_input, same mechanism phase8.py/phase12_roster.py
already use for real dpad/Select input) drives the actual attack, not a
forced CHAR_SELECTED write -- an early version of this gate tried forcing
CHAR_SELECTED=2 directly and found it gets silently overwritten within the
same frame: Anim_Play (which runs before Character_HitApply every frame,
per that routine's own header) recomputes CHAR_SELECTED from real button
state, clobbering a forced value before Character_HitApply ever sees it.
The player's own attack trigger (Anim_Play__player_input) has no proximity
check unlike the AI's own seek/attack range -- pressing Y always attacks,
so overlapping position + a real Y press reliably lands a hit on whichever
AI entity occupies that position.

Checked, all against real Mesen2 hardware state (WRAM + hardware VRAM, not
engine self-consistency -- CLAUDE.md's standing rule; screenshots
specifically excluded per mesen_screenshot_stale_hud_layer memory):
  1. A real player-attacks-Entity1 hit (position forced to overlap, same
     "direct WRAM force is safe" pattern every gate this session uses, but
     the ATTACK itself is real button input) scores exactly HIT_SCORE when
     it doesn't kill, and HIT_SCORE+KILL_SCORE when it does.
  2. Crossing EXTEND_LIFE_SCORE awards exactly +1 Game_Lives.
  3. After enough frames for Hud_Play__text's drip to catch up, BG3 tilemap
     rows 1/2/3 actually contain the SCORE/LIVES/STAGE labels (checked by
     decoding each row's first tile id back to its real glyph).
  4. Row 0 (the player's bar) is unaffected structurally by any of this.

Usage: python tools/verify/game_g6_hud.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
HIT_SCORE = pasm_constant('HIT_SCORE')
KILL_SCORE = pasm_constant('KILL_SCORE')
EXTEND_LIFE_SCORE = pasm_constant('EXTEND_LIFE_SCORE')
HUD_TILE_CAP_LEFT = pasm_constant('HUD_TILE_CAP_LEFT')
BG3_TILEMAP_WORD = pasm_constant('BG3_TILEMAP_VRAM_WORD')
# FONT_TILE_INDEX_BASE is itself a computed expression in text.pasm, not a
# plain literal pasm_constant_in can parse -- recompute from its two real
# literal operands instead of hardcoding the result a second time.
FONT_TILES_VRAM_WORD = pasm_constant_in('src/core/text.pasm', 'FONT_TILES_VRAM_WORD')
BG3_TILES_VRAM_WORD = pasm_constant('BG3_TILES_VRAM_WORD')
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) // 8
FONT_ASCII_FIRST = pasm_constant_in('src/core/text.pasm', 'FONT_ASCII_FIRST')

Game_Score = pasm_constant_in('src/core/game_state.pasm', 'Game_Score')
Game_Lives = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
CHAR_POS_X = 4
CHAR_POS_Y = 6
CHAR_HIT_STUN = 33
CHAR_HP = 35

PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]


def read_word(m, addr):
    block = read_block(m, addr, 32)
    return block[0] | (block[1] << 8)


def read_byte(m, addr):
    return read_block(m, addr, 32)[0]


def overlap_entity1_with_player(m):
    px = read_word(m, PlayerEntity + CHAR_POS_X)
    m.write_memory('snesMemory', Entity1 + CHAR_POS_X, f'{px & 0xFF:02X}{(px >> 8) & 0xFF:02X}')
    py = read_byte(m, PlayerEntity + CHAR_POS_Y)
    m.write_memory('snesMemory', Entity1 + CHAR_POS_Y, f'{py:02X}')


def force_player_attack(m, entity1_hp):
    """Position entity 1 on top of the player, force its HP, then press Y
    for real and let the attack animation fully play out.

    Also clears the player's own CHAR_HIT_STUN first: entity 1 (still a
    live mode-2 AI right up until this forces its HP) counter-attacks the
    player back at distance 0 just as readily as the player attacks it,
    and Anim_Play's stunned-player path ignores the attack-button trigger
    entirely while CHAR_HIT_STUN > 0 -- a real background hazard this gate
    hit directly (a first version intermittently failed to land any hit at
    all, traced to the player still being stunned from the PREVIOUS forced
    encounter). Entities 2/3 are neutralized once, in main(), rather than
    every call -- soft-killed (CHAR_HP==0) is sticky and they're never
    revived by anything this gate does.
    """
    m.write_memory('snesMemory', PlayerEntity + CHAR_HIT_STUN, '00')
    m.write_memory('snesMemory', Entity1 + CHAR_HP, f'{entity1_hp:02X}')
    overlap_entity1_with_player(m)
    m.set_input(m.BTN_Y, 10)
    m.run_frames(60)   # full attack animation + return to idle, so
    m.pause()          # CHAR_HIT_APPLIED is clear again for the next call


def tilemap_row_word(m, row, col):
    row_bytes = read_block(m, BG3_TILEMAP_WORD * 2 + row * 64, 64, mem_type='snesVideoRam')
    off = col * 2
    return row_bytes[off] | (row_bytes[off + 1] << 8)


def main():
    r = Reporter('G6', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # Neutralize entities 2/3 once -- real background AI combat is
        # already underway by frame 300, and a live entity 2/3 attacking
        # the player between force_player_attack calls would re-stun it
        # exactly like entity 1 does mid-call (see that function's own
        # comment). Soft-killed (CHAR_HP==0) is sticky -- see
        # phase11_damage_system_softkill memory -- so this holds for the
        # rest of the gate with no further action.
        m.write_memory('snesMemory', Entity2 + CHAR_HP, '00')
        m.write_memory('snesMemory', Entity3 + CHAR_HP, '00')

        score_before = read_word(m, Game_Score)
        force_player_attack(m, CHAR_HP_MAX)   # well above CHAR_HP_PER_HIT -- not a kill
        score_after = read_word(m, Game_Score)
        entity1_hp = read_byte(m, Entity1 + CHAR_HP)
        print(f'non-killing hit: score {score_before} -> {score_after}, entity1 hp={entity1_hp}')
        r.check('non-killing hit awards exactly HIT_SCORE',
                score_after == score_before + HIT_SCORE)

        score_before = score_after
        force_player_attack(m, CHAR_HP_PER_HIT)   # exactly one hit from 0 -- a kill
        score_after = read_word(m, Game_Score)
        entity1_hp = read_byte(m, Entity1 + CHAR_HP)
        print(f'killing hit: score {score_before} -> {score_after}, entity1 hp={entity1_hp}')
        r.check('killing hit brings entity 1 to exactly 0 HP', entity1_hp == 0)
        r.check('killing hit awards exactly HIT_SCORE+KILL_SCORE',
                score_after == score_before + HIT_SCORE + KILL_SCORE)

        # --- extend-life threshold: force score to just under the next
        # multiple, then land one more guaranteed-non-killing HIT_SCORE hit. ---
        lives_before = read_byte(m, Game_Lives)
        just_under = ((score_after // EXTEND_LIFE_SCORE) + 1) * EXTEND_LIFE_SCORE - HIT_SCORE
        m.write_memory('snesMemory', Game_Score, f'{just_under & 0xFF:02X}{(just_under >> 8) & 0xFF:02X}')
        force_player_attack(m, CHAR_HP_MAX)
        lives_after = read_byte(m, Game_Lives)
        score_final = read_word(m, Game_Score)
        print(f'extend-life: score {just_under} -> {score_final}, lives {lives_before} -> {lives_after}')
        r.check('crossing EXTEND_LIFE_SCORE awards exactly +1 life',
                lives_after == lives_before + 1)

        # --- HUD text rows actually redrawn (give the drip several frames) ---
        m.run_frames(20)
        m.pause()
        score_tile = tilemap_row_word(m, 1, 0) & 0x03FF
        expected_s_tile = FONT_TILE_INDEX_BASE + (ord('S') - FONT_ASCII_FIRST)
        print(f'row 1 col 0 tile id = {score_tile} (expected {expected_s_tile} for "S")')
        r.check('row 1 col 0 shows the "S" of SCORE', score_tile == expected_s_tile)

        lives_tile = tilemap_row_word(m, 2, 0) & 0x03FF
        expected_l_tile = FONT_TILE_INDEX_BASE + (ord('L') - FONT_ASCII_FIRST)
        print(f'row 2 col 0 tile id = {lives_tile} (expected {expected_l_tile} for "L")')
        r.check('row 2 col 0 shows the "L" of LIVES', lives_tile == expected_l_tile)

        stage_tile = tilemap_row_word(m, 3, 0) & 0x03FF
        expected_st_tile = FONT_TILE_INDEX_BASE + (ord('S') - FONT_ASCII_FIRST)
        print(f'row 3 col 0 tile id = {stage_tile} (expected {expected_st_tile} for "S" of STAGE)')
        r.check('row 3 col 0 shows the "S" of STAGE', stage_tile == expected_st_tile)

        # --- row 0 (player bar) structurally unaffected ---
        cap_left = tilemap_row_word(m, 0, 1) & 0x03FF
        print(f'row 0 col 1 tile id = {cap_left} (expected {HUD_TILE_CAP_LEFT}, the bar left cap)')
        r.check('row 0 still shows the player HP bar (left cap intact)',
                cap_left == HUD_TILE_CAP_LEFT)

    r.finish()


if __name__ == '__main__':
    main()
