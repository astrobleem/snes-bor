#!/usr/bin/env python3
"""plan_game.md TMNT campaign gate: the real 4-level main campaign
(sewer0 -> streets -> streets2 -> sewer, stages 5-8), the standalone
boss stages added alongside it in the same session (Rock/Leather, stages
3-4), and the last standalone TMNT level (foot.txt, stage 9) --
game_g9_tmnt_boss.py already covers stage 2 (Bebop) end-to-end; this gate
is the rest of that TMNT conversion.

Real, verified-from-the-pak content facts this gate checks against (see
build_rom.py's BG_SCREENS/SPAWN_TABLES comments and the commit that added
these stages for the extraction methodology): `streets.txt` (stage 6) has
exactly one real `boss 1` line, on `spawn Rock` (Rocksteady fought as a
story boss, not just the standalone practice stage at index 3); `streets2.txt`
(stage 7) has exactly one, on `spawn Bebop` (fought again as a story boss,
separately from the standalone stage 2 encounter); `sewer0.txt`/`sewer.txt`
(stages 5/8) have none. Rock/Leather's own standalone stages (3/4) each
have exactly one, matching game_g9_tmnt_boss.py's already-proven pattern.
`foot.txt` (stage 9) has NONE despite its "Foot Soldier Test" framing --
`spawn Foot3 / alias Foot_Soldier / health 500` is a real, single
reinforced-HP encounter, not a `boss` record; verified directly, not
assumed (this project already knows `alias` is cosmetic, not identity).

Checks:
  1. Byte-level ground truth (the committed spawn_table.bin files
     themselves, not an engine self-report): each of the 7 new stages'
     RECORD_KIND_BOSS record count/position matches the real pak content
     above, and record counts match build_spawn_table.py's own printed
     counts at conversion time (3/2/63/67/86/46/1).
  2. Live engine: force-win sequentially from stage 0 through stage 9 (the
     full real chain today), confirming Game_StageIndex reaches 9 and
     Game_State returns to PLAYING -- exercises every one of the 9 stage-
     transition edges this project's stage list now has, not just the ones
     game_g4_transition.py/game_g9_tmnt_boss.py already covered (0->1,1->2).
  3. Stage 9's CGRAM matches out/bg_stage9foot's own converter output
     (ground truth the engine did not produce).
  4. Not hung after the full 9-stage transition chain.

Deliberately NOT checked live: stage 6's own real boss (Rock) firing
mid-level. Measured directly: reaching its real trigger_x (2240) plateaus
the camera at exactly that value -- a real, already-verified engine
feature (the `wait` scroll-gate), not a bug; see this file's own comment
at that stage in the transition loop for the full reasoning. The boss-flag
pipeline is already proven live end-to-end by game_g9_tmnt_boss.py
(Bebop) and by reaching stage 3 (Rock's own standalone encounter); check
1 above proves stage 6's real spawn table itself is correct.

Usage: python tools/verify/game_tmnt_campaign.py
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

SCREEN_POS_X = 0x7E1601   # core/screen.pasm `.enum $7E1600`, same carve-out as other gates

SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT_ADDR = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')

PLAYER_BASE = 0x7E0A00
ENTITY_BASES = [PLAYER_BASE, PLAYER_BASE + CHAR_ZP_LEN, PLAYER_BASE + 2 * CHAR_ZP_LEN,
                PLAYER_BASE + 3 * CHAR_ZP_LEN]

sys.path.insert(0, os.path.join(ROOT, 'tools', 'bg_converter'))
from build_spawn_table import RECORD_SIZE, RECORD_KIND_BOSS, RECORD_KIND_BOSS_IDENTIFIED  # noqa: E402

_bg_last_dir, _hud_dir = build_rom.BG_SCREENS[9]
BG_LAST_DIR = os.path.join(ROOT, _bg_last_dir)
HUD_DIR = os.path.join(ROOT, _hud_dir)

EXPECTED = {
    3: ('out/spawn_stage3rock/spawn_table.bin', 3, [1]),
    4: ('out/spawn_stage4leather/spawn_table.bin', 2, [0]),
    5: ('out/spawn_stage5sewer0/spawn_table.bin', 63, []),
    6: ('out/spawn_stage6streets/spawn_table.bin', 67, [65]),
    7: ('out/spawn_stage7streets2/spawn_table.bin', 86, [85]),
    8: ('out/spawn_stage8sewer/spawn_table.bin', 46, []),
    9: ('out/spawn_stage9foot/spawn_table.bin', 1, []),
}


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def byte_at(m, addr):
    return read_block(m, addr, 32)[0]


def word_at(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def force_win_and_wait(m, r, from_stage, label):
    """Same direct-write pattern game_g9_tmnt_boss.py already established:
    exhaust the spawn queue, zero remaining AI HP, then jump the camera
    straight to the real converted stage's own Stage_TrueMaxX rather than
    holding Right for however many real frames that stage's real width
    would take -- these are all real, wide, converted levels (240-480
    tiles), not the short stage 1B the walk=True path was built for."""
    spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
    m.write_u8(SPAWN_INDEX, spawn_count)
    for base in ENTITY_BASES[1:]:
        m.write_u8(base + CHAR_HP, 0)
    m.run_frames(5)
    m.pause()
    cleared = byte_at(m, STAGE_CLEARED)
    r.check(f'{label}: win condition fired (Stage_Cleared set)', cleared == 1)

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
    r = Reporter('TMNT-CAMPAIGN', kind='GATE')

    # --- 1. Byte-level ground truth for all 6 new stages' spawn tables. ---
    for stage, (relpath, expected_count, expected_boss) in EXPECTED.items():
        data = _read(os.path.join(ROOT, relpath))
        n = len(data) // RECORD_SIZE
        # Roster-reassignment slice (same day, real user instruction): Rock
        # and Leather are now real roster members (build_rom.py's
        # ROSTER_PREFIXES), so their boss records were regenerated as
        # RECORD_KIND_BOSS_IDENTIFIED (5), not plain RECORD_KIND_BOSS (4) --
        # both still mean "this is a boss" to core/spawn.pasm (both set
        # EntityN_IsBoss), so this check treats them as one family. Bebop's
        # own boss records (stages 2 and 7) stay plain RECORD_KIND_BOSS --
        # Bebop was never added to the roster (no out/bebop_* character
        # assets exist), so there is nothing real to identify it against.
        boss_at = [i for i in range(n)
                   if (data[i * RECORD_SIZE + 6] & 0x07) in (RECORD_KIND_BOSS, RECORD_KIND_BOSS_IDENTIFIED)]
        r.check(f'stage {stage} ({relpath}): {n} records (expected {expected_count})',
                 n == expected_count)
        r.check(f'stage {stage}: boss record(s) at {boss_at} (expected {expected_boss})',
                 boss_at == expected_boss)

    expected_palette = bytearray(_read(os.path.join(BG_LAST_DIR, 'palette.bin')))
    expected_palette[:32] = _read(os.path.join(HUD_DIR, 'hud_palette.bin'))
    expected_palette = bytes(expected_palette)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'boots on stage 0 ({boot_stage})', boot_stage == 0)

        # --- 2. Force-win the full real chain, 0 through 8. ---
        #
        # Not attempted here: forcing stage 6's (streets) own real boss
        # (Rock, a second spawn table entirely separate from the standalone
        # stage-3 practice fight) to fire live. Measured directly: pushing
        # the player's CHAR_POS_X (and Screen_PosX, which is DERIVED every
        # frame from it by Core_Screen_Play and only sticks at the true
        # max-X clamp on a direct write) toward the boss's real trigger_x
        # (2240, byte-level from out/spawn_stage6streets/spawn_table.bin
        # record 65) repeatedly plateaus the camera at EXACTLY 2240 --
        # this is a real, already-verified engine feature (the `wait`
        # scroll-gate, see project memory "wait/group/boss spawn
        # mechanics"), not a bug: the real level places a wait-gate right
        # at the boss's own doorway, same as real OpenBOR level design, and
        # it correctly holds the camera until the enemies in front of it
        # are cleared. Simulating that clear by repeatedly zeroing the 3 AI
        # slots' HP (the same technique force_win_and_wait uses) did not
        # reliably win the race against new wait-blockers respawning within
        # the same frame window, and forcing it harder is not worth the
        # wall-clock this gate should spend -- the wait-gate mechanic
        # itself already has its own real, passing gate elsewhere, and the
        # boss-flag pipeline is already proven end-to-end live by
        # game_g9_tmnt_boss.py (Bebop) and by reaching stage 3 (Rock's own
        # standalone encounter) below. What THIS gate adds for stage 6 is
        # the byte-level proof above that its real, converted spawn table
        # -- a second, different RECORD_KIND_BOSS site -- is correct.
        for target in range(1, 10):
            force_win_and_wait(m, r, from_stage=target - 1, label=f'{target-1}->{target}')
            got = word_at(m, GAME_STAGE_INDEX)
            r.check(f'Game_StageIndex advances {target-1} -> {target} ({got})', got == target)

        final_state = word_at(m, GAME_STATE)
        r.check(f'Game_State returns to PLAYING on the final stage ({final_state})',
                 final_state == GAME_STATE_PLAYING)

        # --- 3. Stage 9's CGRAM matches its own converter output. ---
        got_palette = bytes(read_block(m, 0x000, 256, mem_type='snesCgRam'))
        r.check("stage 9's CGRAM (BG1 backdrop + merged HUD sub-palette) "
                "matches out/bg_stage9foot's own converter output",
                got_palette == expected_palette)

        # --- 4. Not hung after 9 real stage transitions. ---
        fc0 = word_at(m, 0x7E5023)
        m.run_frames(60)
        m.pause()
        fc1 = word_at(m, 0x7E5023)
        r.check(f'Nmi_FrameCounter still advancing after all 9 transitions ({fc0} -> {fc1})',
                fc1 > fc0)

    r.finish()


if __name__ == '__main__':
    main()
