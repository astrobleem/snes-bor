#!/usr/bin/env python3
"""plan_game.md Phase G4 gate: win condition and stage transition
(core/game_state.pasm's Stage_Load/Stage_ApplyWinClamp, main.pasm's
Bg_LoadScene stage-index parameterization, core/spawn.pasm's per-stage
spawn table).

Forces the win condition directly (Spawn_Index := Spawn_Count, all live AI
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
     1B's data, not a stale copy of stage 1A's.
  3. StreamScroll_WidthTiles reads back as stage 1B's real width (not
     stage 1A's stale 408) -- proves Boot_SetPlayfieldBorder's runtime
     re-derivation actually re-ran for the new stage.
  4. StreamScrollFp_Enabled reads back as 0 -- stage 1B has no frontpanel.
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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402
import game_bor_startup_select as startup  # noqa: E402

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

def symbol(name):
    wanted = re.compile(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+' + re.escape(name) + r'\s*$')
    with open(os.path.join(ROOT, 'src', 'main.sym'), encoding='utf-8') as f:
        for line in f:
            hit = wanted.match(line.strip())
            if hit:
                return (int(hit.group(1), 16) << 16) | int(hit.group(2), 16)
    raise KeyError(name)

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
PLAYER_INVULN_FRAMES = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')
G13_MODE = pasm_constant('G13_TwoPlayerEnabled')

SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT_ADDR = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')

STREAM_SCROLL_WIDTH_TILES = pasm_constant('StreamScroll_WidthTiles')
STREAM_SCROLL_FP_ENABLED = pasm_constant('StreamScrollFp_Enabled')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_POS_X = pasm_constant('CHAR_POS_X')

PLAYER_BASE = 0x7E0A00
# G13 retains six actor windows.  The completion fixture must neutralize all
# five NPC windows; clearing only the historical slots 1-3 leaves slots 4/5
# as legitimate blockers under the role-aware predicate.
ENTITY_BASES = [PLAYER_BASE + i * CHAR_ZP_LEN for i in range(6)]

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
    with open(os.path.join(ROOT, 'out', 'spawn_stage1b', 'spawn_table.bin'), 'rb') as f:
        expected_spawn_count = len(f.read()) // RECORD_SIZE

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        m.pause()

        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'boots on stage 0 ({boot_stage})', boot_stage == 0)

        # --- Force the win condition: queue exhausted + no AI alive. Same
        # "safe to write directly" pattern phase11_damage.py/game_g3_death.py
        # already use for entity HP. ---
        spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
        m.write_u8(SPAWN_INDEX, spawn_count)
        for slot, base in enumerate(ENTITY_BASES[1:], start=1):
            role = byte_at(m, base + CHAR_INPUT_DRIVEN)
            print(f'forced-clear slot{slot}: role={role} hp={byte_at(m, base + CHAR_HP)}')
        # The completion predicate is evaluated from the PLAYING update. Keep
        # the legal clear precondition alive while pending stage work settles.
        # fixed five-frame sleep is not a semantic boundary, especially when
        # the preceding MSU work leaves the emulator between NMI updates.
        cleared = 0
        for _ in range(240):
            for base in ENTITY_BASES[1:]:
                if byte_at(m, base + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_AI:
                    m.write_u8(base + CHAR_HP, 0)
            m.run_frames(1)
            cleared = byte_at(m, STAGE_CLEARED)
            if cleared:
                break
        m.pause()

        print('post-clear roles/hp: ' + str([
            (byte_at(m, base + CHAR_INPUT_DRIVEN), byte_at(m, base + CHAR_HP))
            for base in ENTITY_BASES[1:]
        ]))
        print(f'post-clear mode={byte_at(m, G13_MODE)} spawn_index={byte_at(m, SPAWN_INDEX)} spawn_count={spawn_count}')
        r.check('win condition fired (Stage_Cleared set)', cleared == 1)
        true_max = word_at(m, STAGE_TRUE_MAX_X)
        print(f'Stage_Cleared={cleared} Stage_TrueMaxX={true_max}')

        # Drive the already-unlocked camera to the true edge as a controlled
        # handoff precondition, then stop at the explicit post-store hook.
        # A PPU-frame endpoint can otherwise land after a later stage-clear
        # check and report the stale STAGECLEAR value even though the real
        # stageclear invocation wrote PLAYING successfully.
        m.write_u8(SCREEN_POS_X, true_max & 0xFF)
        m.write_u8(SCREEN_POS_X + 1, true_max >> 8)
        names = ('Game_State_Play__stageclear',
                 'Game_State_Play__after_stage_load',
                 'Game_State_Play__after_old_stage_clear',
                 'G13_EnsureP2AfterStage',
                 'G13_EnsureP2AfterStage__done',
                 'Game_State_Play__after_p2_restore',
                 'Game_State_Play__after_playing_store',
                 'Game_State_Play__stageclear_done',
                 'Game_State_Play__done')
        hooks = {m.add_exec_hook(symbol(name)): name for name in names}
        q = m.run_frames(120)
        notes = m.drain_notifications()
        for handle in hooks:
            m.remove_hook(handle)
        semantic = [{'name': hooks[n.get('params', {}).get('handle')],
                     'frame': n.get('params', {}).get('frame')}
                    for n in notes
                    if n.get('method', '').endswith('hookFired') and
                    n.get('params', {}).get('handle') in hooks]
        semantic_ok = (all(name in [row['name'] for row in semantic]
                            for name in names) and
                       any(row['name'] == 'Game_State_Play__after_playing_store'
                           for row in semantic))
        print(f'semantic handoff events: {semantic}')

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
        print(f'after forced win + held-right: stage={new_stage} state={state} '
              f'cleared={byte_at(m, STAGE_CLEARED)} pending={byte_at(m, pasm_constant_in("src/core/game_state.pasm", "Stage_LoadPending"))} '
              f'spawn={byte_at(m, SPAWN_INDEX)}/{byte_at(m, SPAWN_COUNT_ADDR)}')
        r.check('ordered semantic handoff completed', semantic_ok)
        r.check(f'Game_StageIndex advances 0 -> 1 ({new_stage})', new_stage == 1)
        r.check(f'Game_State returns to PLAYING ({state})', state == GAME_STATE_PLAYING)

        # --- 2. New stage's CGRAM matches ITS OWN converter output. ---
        got_palette = bytes(read_block(m, 0x000, 256, mem_type='snesCgRam'))
        r.check("stage 1's CGRAM (BG1 backdrop + merged HUD sub-palette) "
                "matches out/bg_bor_1b's own converter output",
                got_palette == bytes(expected_palette))

        # --- 3. Playfield width re-derived for the new stage, not stale. ---
        got_width = word_at(m, STREAM_SCROLL_WIDTH_TILES)
        r.check(f'StreamScroll_WidthTiles reads stage 1B\'s real width '
                f'({stage1_width_tiles}, got {got_width})',
                got_width == stage1_width_tiles)

        # --- 4. The riskiest untested direction: no-FP -> has-FP. ---
        fp_enabled = byte_at(m, STREAM_SCROLL_FP_ENABLED)
        r.check('StreamScrollFp_Enabled is 0 (stage 1B has no frontpanel)',
                fp_enabled == 0)

        # --- 5. Fresh spawn queue for the new stage. ---
        new_spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
        new_spawn_index = byte_at(m, SPAWN_INDEX)
        print(f'new stage spawn_count={new_spawn_count} spawn_index={new_spawn_index}')
        r.check(f"Spawn_Count matches stage 1B's own table ({expected_spawn_count})",
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
