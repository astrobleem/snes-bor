#!/usr/bin/env python3
"""plan_game.md Phase G9 gate: a real boss fight, from real TMNT data.

game_g9_boss_bar.py and game_g9_wait_group_boss.py already prove the boss
health bar and record_kind==4 plumbing work, but only against a
hand-authored SYNTHETIC record -- BOR's own two shipped stages have zero
`boss` lines (see core/hud_boss.pasm's header). This gate is the real-content
equivalent: stage index 2 (out/bg_stage2boss / out/spawn_stage2boss) is
converted straight from `Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak`,
`data\\LEVELS\\BEBOP.TXT` -- verified directly against the extracted pak text
(not assumed) to contain exactly one real `boss 1` line, on a `spawn Bebop`
record, plus a decorative `spawn Hydrany` (`type obstacle`, converts to
RECORD_KIND_PROP) and a closing `wait`.

**UPDATED (roster-growth slice, same session)**: the paragraph that used to
live here documented Bebop's boss rendering as a reskin (whichever roster
character already occupied the AI slot) as a deliberate, load-bearing scope
cut. That was overturned for real, not just re-labeled: Bebop was converted
fresh from the TMNT pak and added as roster slot 8, and this stage's real
spawn record now carries RECORD_KIND_BOSS_IDENTIFIED with roster_idx=8, so
Spawn_Play actually re-streams the AI slot with Bebop's own real converted
character (see core/spawn.pasm's Spawn_DoRosterReassign and
game_spawn_roster_reassign.py, which proves the same mechanism end-to-end
for Rock/Leather). Stage 1A's own `angel` spawn still reskins -- ordinary
(non-boss) enemies never got individual roster slots, so there is nothing
real to identify them against; that part of the old scope cut still stands,
just no longer for Bebop specifically.

Checks:
  1. The real spawn table's boss record decodes to RECORD_KIND_BOSS_IDENTIFIED
     with roster_idx==8 (Bebop's real roster slot) at the pipeline level
     (byte-level, ground truth off the committed
     out/spawn_stage2boss/spawn_table.bin, not an engine self-report) --
     proves build_spawn_table.py's real roster-lookup path fired for this
     stage now that Bebop is a real roster member, not the plain
     no-identity RECORD_KIND_BOSS the other two G9 gates still use for
     their hand-authored synthetic record (predates any roster membership
     for that record's fictional character).
  2. Driving the real win condition twice (stage 0->1, proven mechanism
     already covered by game_g4_transition.py; then 1->2, the untested
     direction into the new boss stage) lands on Game_StageIndex==2,
     Game_State back in PLAYING.
  3. Stage 2's CGRAM matches out/bg_stage2boss's own converter output
     (ground truth the engine did not produce, same standing rule as
     phase6.py/game_g4_transition.py).
  4. StreamScrollFp_Enabled reads 0 -- stage 2 (like stage 1B) has no
     frontpanel; proves the has-FP -> no-FP direction (the OTHER untested
     transition direction versus game_g4_transition.py's no-FP -> has-FP).
  5. Once the real, converted level's own `boss 1` record is consumed by
     Spawn_Play, SOME entity's own EntityN_IsBoss flag reads 1 -- the real
     end-to-end proof this gate exists for (not a synthetic WRAM poke).
  6. The HUD boss bar (core/hud_boss.pasm) actually renders for that real
     entity: BG3 tilemap ground truth (same decode as game_g9_boss_bar.py),
     a real filled bar at nonzero HP, not blank/sentinel.

Usage: python tools/verify/game_g9_tmnt_boss.py
"""
import os
import struct
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

# core/screen.pasm `.enum $7E1600` struct field, not a plain NAME = value
# constant -- same carve-out phase8.py/game_g4_transition.py already use.
SCREEN_POS_X = 0x7E1601

SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT_ADDR = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
Entity1_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity1_IsBoss')
Entity2_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity2_IsBoss')
Entity3_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity3_IsBoss')

STREAM_SCROLL_FP_ENABLED = pasm_constant('StreamScrollFp_Enabled')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')

HUD_ROW_BOSS = pasm_constant('HUD_ROW_BOSS')
HudBossCachedHp = pasm_constant('HudBossCachedHp')
BG3_TILEMAP_WORD = pasm_constant('BG3_TILEMAP_VRAM_WORD')

PLAYER_BASE = 0x7E0A00
ENTITY_BASES = [PLAYER_BASE, PLAYER_BASE + CHAR_ZP_LEN, PLAYER_BASE + 2 * CHAR_ZP_LEN,
                PLAYER_BASE + 3 * CHAR_ZP_LEN]
ENTITY_ISBOSS = [None, Entity1_IsBoss, Entity2_IsBoss, Entity3_IsBoss]

sys.path.insert(0, os.path.join(ROOT, 'tools', 'bg_converter'))
from build_spawn_table import RECORD_SIZE, RECORD_KIND_BOSS_IDENTIFIED  # noqa: E402
BEBOP_ROSTER_IDX = build_rom.ROSTER_PREFIXES.index('out/bebop')

_bg2_dir, _hud_dir = build_rom.BG_SCREENS[2]
BG2_DIR = os.path.join(ROOT, _bg2_dir)
HUD_DIR = os.path.join(ROOT, _hud_dir)
assert build_rom.FP_SCREENS[2] is None, 'gate assumption: stage 2 has no frontpanel'


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def byte_at(m, addr):
    return read_block(m, addr, 32)[0]


def word_at(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def row_words(m, row, count=32):
    raw = read_block(m, (BG3_TILEMAP_WORD + row * 32) * 2, max(32, count * 2),
                      mem_type='snesVideoRam')
    return [raw[i * 2] | (raw[i * 2 + 1] << 8) for i in range(count)]


def force_win_and_wait(m, r, from_stage, label, walk=False):
    """Forces the win condition (same "force the exact moment, don't wait
    on combat RNG" pattern game_g4_transition.py/game_g3_death.py already
    use for spawn_index/HP), then reaches the camera-clamp edge check
    (core/game_state.pasm's `lda Screen_PosX / cmp.l Stage_TrueMaxX`).

    walk=True holds Right and lets the player actually traverse the
    distance (fine for stage 1B, which is short -- this is what
    game_g4_transition.py itself does for the 0->1 direction). walk=False
    instead writes Screen_PosX := Stage_TrueMaxX directly once Stage_
    Cleared is set: stage 1A (the 1->2 direction this gate also needs) is
    408 tiles wide, real converted data, and a real held-Right walk across
    it would need far more real frames than a quick gate should spend --
    this is a direct, deliberate use of the same "safe to write directly"
    precedent already applied to Spawn_Index/CHAR_HP just above, applied to
    the other side of the exact same edge check instead of walking to it."""
    spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
    m.write_u8(SPAWN_INDEX, spawn_count)
    for base in ENTITY_BASES[1:]:
        m.write_u8(base + CHAR_HP, 0)
    m.run_frames(5)
    m.pause()
    cleared = byte_at(m, STAGE_CLEARED)
    r.check(f'{label}: win condition fired (Stage_Cleared set)', cleared == 1)

    if walk:
        for _ in range(20):
            m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
            m.set_input(m.BTN_RIGHT, 60)
            m.pause()
            if word_at(m, GAME_STAGE_INDEX) != from_stage:
                break
    else:
        true_max = word_at(m, STAGE_TRUE_MAX_X)
        m.write_u16(SCREEN_POS_X, true_max)
        m.run_frames(10)
        m.pause()

    for _ in range(20):
        if word_at(m, GAME_STATE) == GAME_STATE_PLAYING:
            break
        m.run_frames(30)
        m.pause()


def main():
    r = Reporter('G9-TMNT-BOSS', kind='GATE')

    # --- 1. Real converted level data, byte-level, before touching Mesen. ---
    with open(os.path.join(ROOT, 'out', 'spawn_stage2boss', 'spawn_table.bin'), 'rb') as f:
        spawn_bytes = f.read()
    record_count = len(spawn_bytes) // RECORD_SIZE
    boss_records = []
    for i in range(record_count):
        rec = spawn_bytes[i * RECORD_SIZE:(i + 1) * RECORD_SIZE]
        # claude_close_g7_g8_before_g10.md Part 2/3: record grew 9->10
        # bytes -- +9 object_roster_idx is the spawned character's own
        # identity (same meaning the old +8 had for this record shape).
        _trig, _sx, _sy, _facing, kind, _hp, _item_roster_idx, roster_idx = \
            struct.unpack('<HHBBBBBB', rec[:10])
        if (kind & 0x07) == RECORD_KIND_BOSS_IDENTIFIED:
            boss_records.append((i, roster_idx))
    r.check(f'out/spawn_stage2boss/spawn_table.bin has exactly one real '
            f'RECORD_KIND_BOSS_IDENTIFIED record with roster_idx={BEBOP_ROSTER_IDX} '
            f'(found {boss_records})',
            boss_records == [(0, BEBOP_ROSTER_IDX)])

    expected_palette = bytearray(_read(os.path.join(BG2_DIR, 'palette.bin')))
    expected_palette[:32] = _read(os.path.join(HUD_DIR, 'hud_palette.bin'))
    expected_palette = bytes(expected_palette)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'boots on stage 0 ({boot_stage})', boot_stage == 0)

        # --- 2a. Stage 0 -> 1 (already proven direction, needed as a real
        # stepping stone to reach stage 2 -- there is no direct-load path). ---
        force_win_and_wait(m, r, from_stage=0, label='0->1', walk=True)
        mid_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'Game_StageIndex advances 0 -> 1 ({mid_stage})', mid_stage == 1)

        # --- 2b. Stage 1 -> 2: the real boss stage, untested direction.
        # Stage 1A is 408 tiles wide (real converted data) -- direct-write
        # the camera-clamp edge instead of holding Right for the real
        # walking time that would take (see force_win_and_wait's header). ---
        force_win_and_wait(m, r, from_stage=1, label='1->2', walk=False)
        new_stage = word_at(m, GAME_STAGE_INDEX)
        state = word_at(m, GAME_STATE)
        print(f'after second forced win: stage={new_stage} state={state}')
        r.check(f'Game_StageIndex advances 1 -> 2 ({new_stage})', new_stage == 2)
        r.check(f'Game_State returns to PLAYING ({state})', state == GAME_STATE_PLAYING)

        # --- 3. Stage 2's CGRAM matches its own converter output. ---
        got_palette = bytes(read_block(m, 0x000, 256, mem_type='snesCgRam'))
        r.check("stage 2's CGRAM (BG1 backdrop + merged HUD sub-palette) "
                "matches out/bg_stage2boss's own converter output",
                got_palette == expected_palette)

        # --- 4. has-FP (stage 1) -> no-FP (stage 2): the OTHER untested
        # transition direction versus game_g4_transition.py's no-FP -> has-FP. ---
        fp_enabled = byte_at(m, STREAM_SCROLL_FP_ENABLED)
        r.check(f'StreamScrollFp_Enabled is 0 (stage 2 has no frontpanel, '
                f'got {fp_enabled})', fp_enabled == 0)

        # --- 5. The real level's own boss record actually sets SOME
        # entity's EntityN_IsBoss, from real data, not a synthetic poke.
        # Spawn_Play arms on Screen_PosX (the CAMERA), not player position
        # (core/spawn.pasm: `lda Screen_PosX / cmp.l SpawnTable_Wram,x`) --
        # stage 2 just reloaded with a fresh Screen_PosX near 0, and nothing
        # has moved the camera yet. Bebop's real trigger_x is small (~160
        # world px after SCALE), so a short real held-Right (genuine
        # gameplay, not a direct write -- this check specifically wants to
        # prove the real trigger fires under real advancement) easily
        # clears it. ---
        for _ in range(8):
            m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
            m.set_input(m.BTN_RIGHT, 20)
            m.pause()
            if any(byte_at(m, ENTITY_ISBOSS[slot]) == 1 for slot in (1, 2, 3)):
                break

        boss_slot = None
        for _ in range(20):
            for slot in (1, 2, 3):
                if byte_at(m, ENTITY_ISBOSS[slot]) == 1:
                    boss_slot = slot
                    break
            if boss_slot is not None:
                break
            m.run_frames(10)
            m.pause()
        print(f'real boss record landed on entity slot: {boss_slot}')
        r.check('the real converted boss record set SOME entity\'s '
                f'EntityN_IsBoss (slot={boss_slot})', boss_slot is not None)

        # --- 6. The HUD boss bar actually renders for it: BG3 tilemap
        # ground truth, a real nonzero bar, not the $FF/blank sentinel. ---
        m.run_frames(10)
        m.pause()
        cached = byte_at(m, HudBossCachedHp)
        words = row_words(m, HUD_ROW_BOSS)
        nonblank = any(w != 0 for w in words)
        print(f'boss row words[:3]={words[:3]} HudBossCachedHp={cached}')
        r.check('HudBossCachedHp reads a real HP value, not the $FF sentinel',
                cached != 0xFF)
        r.check('the boss health bar row is non-blank for the real boss entity',
                nonblank)

        # --- Not hung after two heavy, blocking reloads. ---
        fc0 = word_at(m, 0x7E5023)
        m.run_frames(60)
        m.pause()
        fc1 = word_at(m, 0x7E5023)
        r.check(f'Nmi_FrameCounter still advancing after both reloads ({fc0} -> {fc1})',
                fc1 > fc0)

    r.finish()


if __name__ == '__main__':
    main()
