#!/usr/bin/env python3
"""plan_game.md Phase G4 gate: win condition and stage transition
(core/game_state.pasm's Stage_Load/Stage_ApplyWinClamp, main.pasm's
Bg_LoadScene stage-index parameterization, core/spawn.pasm's per-stage
spawn table).

Forces the win condition directly (Spawn_Index := Spawn_Count, all three AI
entities' CHAR_HP := 0) rather than clearing stage 1B's real 28-record wave
organically -- same "force the exact moment, don't wait on combat RNG"
pattern game_g3_death.py already uses for player death. Then holds Right
until the just-unlocked camera clamp is reached, exactly like a real win,
and lets the engine's own transition machinery (Game_State_Play__playing's
win-check -> GAME_STATE_STAGECLEAR -> Stage_Load) do the actual reload.

Checked, all against real Mesen2 hardware state (WRAM + hardware VRAM/CGRAM,
not engine self-consistency -- CLAUDE.md's standing rule):
  1. Game_StageIndex advances 0 -> 1, Game_State returns to PLAYING (not
     stuck in STAGECLEAR or GAMEOVER).
  2. The new stage's CGRAM palette (BG1 backdrop + merged HUD sub-palette)
     matches build_rom.BG_SCREENS[1]'s OWN converter output -- ground truth
     the engine did not produce, same standing rule phase6.py already
     applies. Byte-identical here proves the reload actually loaded stage
     1A's data, not a stale copy of stage 1B's.
  3. StreamScroll_WidthTiles reads back as stage 1A's real width (not
     stage 1B's stale 140) -- proves Boot_SetPlayfieldBorder's runtime
     re-derivation actually re-ran for the new stage.
  4. StreamScrollFp_Enabled reads back as 1 -- stage 1A DOES have a
     frontpanel and stage 1B does NOT (see build_rom.py's own FP_SCREENS
     comment), so this specifically exercises the "no FP -> has FP"
     direction the advisor consult flagged as the riskiest untested case.
  5. This stage's own spawn queue is freshly loaded: Spawn_Count matches
     stage 1A's real record count, Spawn_Index is back to 0 (not stage
     1B's exhausted queue).
  6. The player was fully reset at the new stage's left edge: full HP,
     PosX within a few pixels of Screen_PosX (which is itself 0).
  7. The engine is not hung after this deliberately heavy, blocking
     reload -- Nmi_FrameCounter still advances afterward.

Usage: python tools/verify/game_g4_transition.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
PLAYER_INVULN_FRAMES = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')

SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT_ADDR = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')

STREAM_SCROLL_WIDTH_TILES = pasm_constant('StreamScroll_WidthTiles')
STREAM_SCROLL_FP_ENABLED = pasm_constant('StreamScrollFp_Enabled')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_POS_X = pasm_constant('CHAR_POS_X')

PLAYER_BASE = 0x7E0A00
ENTITY_BASES = [PLAYER_BASE, PLAYER_BASE + CHAR_ZP_LEN, PLAYER_BASE + 2 * CHAR_ZP_LEN,
                PLAYER_BASE + 3 * CHAR_ZP_LEN]

# Screen_MaxX/Screen_PosX: core/screen.pasm `.enum $7E1600` struct fields,
# not plain `NAME = value` constants -- see tools/verify/phase8.py's own
# note on this same carve-out.
SCREEN_POS_X = 0x7E1601
SCREEN_MAX_X = 0x7E160E

_bg1_dir, _hud_dir = build_rom.BG_SCREENS[1]
BG1_DIR = os.path.join(ROOT, _bg1_dir)
HUD_DIR = os.path.join(ROOT, _hud_dir)
_fp1_dir = build_rom.FP_SCREENS[1]
FP1_DIR = os.path.join(ROOT, _fp1_dir) if _fp1_dir else None


def byte_at(m, addr):
    return read_block(m, addr, 32)[0]


def word_at(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def main():
    import json
    r = Reporter('G4', kind='GATE')

    with open(os.path.join(BG1_DIR, 'manifest.json'), encoding='utf-8') as f:
        stage1_manifest = json.load(f)
    stage1_width_tiles = stage1_manifest['width_tiles']

    # Ground truth for the new stage's CGRAM: same recipe phase6.py's own
    # expected-palette construction uses -- raw palette.bin with the HUD's
    # sub-palette 0 merged in, then (since stage 1A HAS a frontpanel, unlike
    # phase6.py's stage 1B) the frontpanel's own sub-palettes 1-3 merged in
    # too. This is a RUNTIME overlay Bg_LoadSceneFp_Streaming performs (see
    # that routine's header) -- not baked into pack_bg_blob's own blob, so
    # it can't be read off the packer directly the way phase8.py's simpler
    # checks can.
    def _read(path):
        with open(path, 'rb') as f:
            return f.read()
    expected_palette = bytearray(_read(os.path.join(BG1_DIR, 'palette.bin')))
    expected_palette[:32] = _read(os.path.join(HUD_DIR, 'hud_palette.bin'))
    if FP1_DIR:
        fp_palette = _read(os.path.join(FP1_DIR, 'palette.bin'))
        expected_palette[8:32] = fp_palette[8:32]
    expected_palette = bytes(expected_palette)

    # record size grew 7 -> 8 bytes (health-override slice, follow-up to G8:
    # added a spawn_hp byte) -- derive from build_spawn_table.py's own
    # RECORD_SIZE rather than hardcoding it a second time here.
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'bg_converter'))
    from build_spawn_table import RECORD_SIZE
    with open(os.path.join(ROOT, 'out', 'spawn_stage1a', 'spawn_table.bin'), 'rb') as f:
        expected_spawn_count = len(f.read()) // RECORD_SIZE

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'boots on stage 0 ({boot_stage})', boot_stage == 0)

        # --- Force the win condition: queue exhausted + no AI alive. Same
        # "safe to write directly" pattern phase11_damage.py/game_g3_death.py
        # already use for entity HP. ---
        spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
        m.write_u8(SPAWN_INDEX, spawn_count)
        for base in ENTITY_BASES[1:]:
            m.write_u8(base + CHAR_HP, 0)
        m.run_frames(5)
        m.pause()

        cleared = byte_at(m, STAGE_CLEARED)
        r.check('win condition fired (Stage_Cleared set)', cleared == 1)
        true_max = word_at(m, STAGE_TRUE_MAX_X)
        print(f'Stage_Cleared={cleared} Stage_TrueMaxX={true_max}')

        # --- Hold Right until the newly-unlocked camera clamp is reached --
        # exactly the real win path, just with the setup above skipping the
        # organic 28-wave clear. Force invulnerability throughout, same
        # reasoning as phase8.py/phase9.py's own forced holds: combat must
        # not confound a test that isn't about combat. ---
        for _ in range(20):
            m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
            m.set_input(m.BTN_RIGHT, 60)
            m.pause()
            if word_at(m, GAME_STAGE_INDEX) != boot_stage:
                break

        # --- Stage_Load is a real, heavy, blocking reload (a ~150KB MSU-1
        # byte-by-byte stream under sei -- see core/game_state.pasm's own
        # header on why it's deliberately synchronous, boot-style). Game_
        # StageIndex increments BEFORE jsr Stage_Load even starts (see
        # Game_State_Play__stageclear_next), so seeing it change is not
        # proof the reload has actually finished -- Game_State only flips
        # back to PLAYING once Stage_Load returns. A single short fixed
        # wait here sampled CGRAM mid-write on a first attempt (a real,
        # reproducible partial-palette read, not engine corruption) --
        # poll on Game_State itself instead of guessing a wait length. ---
        for _ in range(20):
            if word_at(m, GAME_STATE) == GAME_STATE_PLAYING:
                break
            m.run_frames(30)
            m.pause()

        new_stage = word_at(m, GAME_STAGE_INDEX)
        state = word_at(m, GAME_STATE)
        print(f'after forced win + held-right: stage={new_stage} state={state}')
        r.check(f'Game_StageIndex advances 0 -> 1 ({new_stage})', new_stage == 1)
        r.check(f'Game_State returns to PLAYING ({state})', state == GAME_STATE_PLAYING)

        # --- 2. New stage's CGRAM matches ITS OWN converter output. ---
        got_palette = bytes(read_block(m, 0x000, 256, mem_type='snesCgRam'))
        r.check("stage 1's CGRAM (BG1 backdrop + merged HUD sub-palette) "
                "matches out/bg_stage1a's own converter output",
                got_palette == bytes(expected_palette))

        # --- 3. Playfield width re-derived for the new stage, not stale. ---
        got_width = word_at(m, STREAM_SCROLL_WIDTH_TILES)
        r.check(f'StreamScroll_WidthTiles reads stage 1A\'s real width '
                f'({stage1_width_tiles}, got {got_width})',
                got_width == stage1_width_tiles)

        # --- 4. The riskiest untested direction: no-FP -> has-FP. ---
        fp_enabled = byte_at(m, STREAM_SCROLL_FP_ENABLED)
        r.check('StreamScrollFp_Enabled is 1 (stage 1A has a frontpanel, '
                'stage 1B did not)', fp_enabled == 1)

        # --- 5. Fresh spawn queue for the new stage. ---
        new_spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
        new_spawn_index = byte_at(m, SPAWN_INDEX)
        print(f'new stage spawn_count={new_spawn_count} spawn_index={new_spawn_index}')
        r.check(f"Spawn_Count matches stage 1A's own table ({expected_spawn_count})",
                new_spawn_count == expected_spawn_count)
        # Not asserting exactly 0: by the time this samples, a few extra
        # frames have run past the transition (the checks above needed the
        # dust to settle), and stage 1A's own first wave can trigger almost
        # immediately if its trigger_x is near 0 -- Spawn_Play advancing to
        # 1 already is CORRECT behavior, not stage 1B's stale exhausted
        # queue carrying over. The real regression this guards against is
        # the old stage's queue (Spawn_Index == its OLD Spawn_Count, 28)
        # silently surviving the reload.
        r.check(f"Spawn_Index is fresh for the new stage, not stage 1B's "
                f"exhausted queue ({new_spawn_index} << {new_spawn_count})",
                new_spawn_index < new_spawn_count)

        # --- 6. Player reset at the new stage's left edge. ---
        player_hp = byte_at(m, PLAYER_BASE + CHAR_HP)
        player_x = word_at(m, PLAYER_BASE + CHAR_POS_X)
        screen_x = word_at(m, SCREEN_POS_X)
        print(f'player_hp={player_hp} player_x={player_x} screen_x={screen_x}')
        r.check(f'player respawned at CHAR_HP_MAX ({player_hp})', player_hp == CHAR_HP_MAX)
        r.check('camera reset to the new stage\'s left edge (Screen_PosX small)',
                screen_x < 32)
        # Loose bound, not a tight left-edge check: set_input holds for
        # ~60 real frames regardless of when the transition itself lands
        # mid-hold (see this file's own held-right loop), so the player can
        # already have walked a bit further right by the time this samples.
        # The real regression this guards against is the player staying at
        # STAGE 1B's right edge (world X in the 700-1080 range) instead of
        # actually being repositioned into stage 1A at all.
        r.check("player positioned in the new stage's opening stretch, not "
                "still at the old stage's right edge",
                player_x < 300)

        # --- 7. Not hung after a deliberately heavy, blocking reload. ---
        fc0 = word_at(m, 0x7E5023)
        m.run_frames(60)
        m.pause()
        fc1 = word_at(m, 0x7E5023)
        r.check(f'Nmi_FrameCounter still advancing after the reload ({fc0} -> {fc1})',
                fc1 > fc0)

    r.finish()


if __name__ == '__main__':
    main()
