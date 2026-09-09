#!/usr/bin/env python3
"""plan_game.md spawn-driven roster-reassignment gate (real user instruction,
same day as the TMNT campaign): closes the "deliberate scope cut" every
previous TMNT boss gate (game_g9_tmnt_boss.py, game_tmnt_campaign.py)
explicitly documented -- a boss used to render using whichever roster
character already happened to occupy its AI slot, never its own real
converted character.

Real mechanism (core/spawn.pasm's SPAWN_KIND_BOSS_IDENTIFIED +
Spawn_DoRosterReassign, tools/bg_converter/build_spawn_table.py's
RECORD_KIND_BOSS_IDENTIFIED): a boss spawn whose real character name IS in
the actual shipped roster (build_rom.py's ROSTER_PREFIXES) now carries that
roster index in the record's own spare bits, and Spawn_Play re-runs the
SAME Anim_LoadCharacter routine the player's own live Select-button reselect
already uses -- just DP-targeted at the AI slot the record lands on instead
of always the player. Rock (Rocksteady) and Leather (Leatherhead) were both
added as real roster members (indices 6/7) specifically to prove this: their
standalone boss stages (3/4) are the real, already-shipped, already-gated
content this reuses -- no synthetic record, no new level.

Ground truth is each character's own real converted moveset frame counts
(out/rock_moveset.json / out/leather_moveset.json's own numbers, not
invented) mirrored into the live entity's CHAR_IDLE_FCOUNT/WALK_FCOUNT/
ATTACK_FCOUNT fields (main.pasm's Anim_LoadCharacter writes these straight
from the roster record) -- never a screenshot, never an engine self-report.

Checks (per boss, Rock then Leather):
  1. The real spawn table's boss record decodes to RECORD_KIND_BOSS_IDENTIFIED
     with the correct real roster index (byte-level, off the committed
     out/spawn_stageN.../spawn_table.bin, not an engine self-report).
  2. Immediately after landing on the boss's own standalone stage (before
     its spawn record has triggered), no AI slot's (idle,walk,attack) frame
     triple already happens to equal the boss's real triple -- rules out
     "it was already right by coincidence of whatever the slot booted with."
  3. After the real trigger fires (real held-Right, not a direct WRAM
     poke) and Spawn_Play consumes the record, SOME entity's EntityN_IsBoss
     reads 1.
  4. That SAME entity's (idle,walk,attack) triple now matches the boss's own
     real converted moveset counts -- proves the reassignment actually
     re-streamed this slot's real character, not just set a flag.
  5. The engine is not hung after two blocking Anim_LoadCharacter reloads
     back to back (Rock's stage, then Leather's).

Usage: python tools/verify/game_spawn_roster_reassign.py
"""
import json
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

SCREEN_POS_X = 0x7E1601   # core/screen.pasm `.enum $7E1600`, same carve-out as other gates

SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT_ADDR = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
Entity1_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity1_IsBoss')
Entity2_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity2_IsBoss')
Entity3_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity3_IsBoss')

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_IDLE_FCOUNT = pasm_constant('CHAR_IDLE_FCOUNT')
CHAR_WALK_FCOUNT = pasm_constant('CHAR_WALK_FCOUNT')
CHAR_ATTACK_FCOUNT = pasm_constant('CHAR_ATTACK_FCOUNT')

# Regression coverage for a real fixed bug (animheaderstaging_shared_scratch_
# collision project memory, corrected 2026-08-29): Spawn_DoRosterReassign's
# jsl Anim_LoadCharacter_Long returns with A/X 16-bit (Anim_LoadCharacter's
# own documented exit convention), and the restore code right after the call
# used to run its CharSelect_Index save/restore pair still assuming 8-bit A,
# silently executing both as 16-bit loads/stores and zeroing the adjacent
# CharSelect_RosterCount byte. This gate already drives two real, live,
# back-to-back Spawn_DoRosterReassign calls (Rock then Leather) with other
# entities animating and the player actively moving/attacking -- exactly the
# overlap shape the bug needs -- so add direct before/after assertions on
# CharSelect_Index/CharSelect_RosterCount around each reassignment instead of
# a separate synthetic repro.
CharSelect_Index = 0x7E53B6
CharSelect_RosterCount = 0x7E53B7

PLAYER_BASE = 0x7E0A00
ENTITY_BASES = [PLAYER_BASE, PLAYER_BASE + CHAR_ZP_LEN, PLAYER_BASE + 2 * CHAR_ZP_LEN,
                PLAYER_BASE + 3 * CHAR_ZP_LEN]
ENTITY_ISBOSS = [None, Entity1_IsBoss, Entity2_IsBoss, Entity3_IsBoss]

sys.path.insert(0, os.path.join(ROOT, 'tools', 'bg_converter'))
from build_spawn_table import RECORD_SIZE, RECORD_KIND_BOSS_IDENTIFIED  # noqa: E402
# roster-growth slice: roster_idx moved from record_kind's spare bits (was
# ROSTER_SHIFT=5) to its own dedicated +8 byte once the roster cap (8) grew
# past what 3 spare bits could hold -- see build_spawn_table.py's RECORD_SIZE
# comment and core/spawn.pasm's record-layout comment for the real history.


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def byte_at(m, addr):
    return read_block(m, addr, 32)[0]


def word_at(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def entity_triple(m, base):
    return (byte_at(m, base + CHAR_IDLE_FCOUNT),
            byte_at(m, base + CHAR_WALK_FCOUNT),
            byte_at(m, base + CHAR_ATTACK_FCOUNT))


def force_win_and_wait(m, r, from_stage, label):
    spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
    m.write_u8(SPAWN_INDEX, spawn_count)
    for _ in range(240):
        for base in ENTITY_BASES[1:]:
            m.write_u8(base + CHAR_HP, 0)
        if byte_at(m, STAGE_CLEARED) == 1:
            break
        m.run_frames(1)
        m.pause()
    cleared = byte_at(m, STAGE_CLEARED)
    r.check(f'{label}: win condition fired (Stage_Cleared set)', cleared == 1)

    true_max = word_at(m, STAGE_TRUE_MAX_X)
    m.write_u16(SCREEN_POS_X, true_max)
    m.run_frames(10)
    m.pause()

    for _ in range(20):
        if (word_at(m, GAME_STAGE_INDEX) != from_stage
                and word_at(m, GAME_STATE) == GAME_STATE_PLAYING):
            break
        m.run_frames(30)
        m.pause()


def check_boss_stage(m, r, stage_index, spawn_relpath, roster_prefix, expected_roster_idx):
    """Runs checks 1-4 (module docstring) for the boss whose standalone
    stage is `stage_index` (already the CURRENT stage when this is called),
    real character `roster_prefix` (out/<roster_prefix>_moveset.json)."""
    moveset = json.load(open(os.path.join(ROOT, f'out/{roster_prefix}_moveset.json')))
    by_name = {a['name']: a['frames'] for a in moveset['animations']}
    expected_triple = (by_name['idle'], by_name['walk'], by_name['attack1'])

    # --- 1. Byte-level ground truth: the real spawn table's boss record. ---
    data = _read(os.path.join(ROOT, spawn_relpath))
    n = len(data) // RECORD_SIZE
    found = None
    for i in range(n):
        kind = data[i * RECORD_SIZE + 6]
        if (kind & 0x07) == RECORD_KIND_BOSS_IDENTIFIED:
            # +9 object_roster_idx -- the SPAWNED character's own real
            # roster index (a boss's own identity). +8 is item_roster_idx
            # (a contained/standalone item's identity), a different field
            # since the G8 item/pickup slice's record-size split; this was
            # still reading the old single +8 roster_idx offset, stale.
            found = (i, data[i * RECORD_SIZE + 9])
    r.check(f'{roster_prefix}: {spawn_relpath} has a RECORD_KIND_BOSS_IDENTIFIED '
             f'record with roster_idx={expected_roster_idx} (found {found})',
             found is not None and found[1] == expected_roster_idx)

    # --- 2. Before the trigger fires: no slot already coincidentally shows
    # the boss's real triple (rules out a false-positive from whatever the
    # slot happened to boot with). ---
    m.run_frames(10)
    m.pause()
    before = {slot: entity_triple(m, ENTITY_BASES[slot]) for slot in (1, 2, 3)}
    r.check(f'{roster_prefix}: no AI slot already shows the real triple '
             f'{expected_triple} before the spawn triggers (got {before})',
             expected_triple not in before.values())

    # --- 3. Real held-Right (genuine gameplay, not a direct poke) until
    # the real trigger fires and some slot's EntityN_IsBoss goes live. ---
    boss_slot = None
    for _ in range(10):
        m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
        m.set_input(m.BTN_RIGHT, 20)
        m.pause()
        for slot in (1, 2, 3):
            if byte_at(m, ENTITY_ISBOSS[slot]) == 1:
                boss_slot = slot
                break
        if boss_slot is not None:
            break
    r.check(f'{roster_prefix}: real trigger sets SOME entity\'s EntityN_IsBoss '
             f'(slot={boss_slot})', boss_slot is not None)

    # --- 4. That slot's triple now matches the boss's own real converted
    # moveset -- the actual proof the reassignment re-streamed a real
    # character, not just flipped a flag. ---
    if boss_slot is not None:
        after = entity_triple(m, ENTITY_BASES[boss_slot])
        for _ in range(24):
            if after == expected_triple:
                break
            m.run_frames(5)
            m.pause()
            after = entity_triple(m, ENTITY_BASES[boss_slot])
        print(f'{roster_prefix}: slot {boss_slot} triple before={before.get(boss_slot)} '
              f'after={after} expected={expected_triple}')
        r.check(f'{roster_prefix}: slot {boss_slot} now shows its OWN real '
                 f'(idle,walk,attack) triple {expected_triple} (got {after})',
                 after == expected_triple)
    else:
        r.check(f'{roster_prefix}: slot triple matches its own real moveset', False)


def main():
    r = Reporter('SPAWN-ROSTER-REASSIGN', kind='GATE')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'boots on stage 0 ({boot_stage})', boot_stage == 0)

        expected_roster_count = getattr(build_rom, 'PLAYABLE_ROSTER_COUNT', len(build_rom.ROSTER_PREFIXES))
        roster_count_before = byte_at(m, CharSelect_RosterCount)
        char_select_index_before = byte_at(m, CharSelect_Index)
        r.check(f'CharSelect_RosterCount sane before any reassignment ({roster_count_before} == '
                 f'{expected_roster_count})', roster_count_before == expected_roster_count)

        # --- Reach stage 4 (Rock's own standalone boss stage) via the real
        # chain, same force-win idiom as game_g9_tmnt_boss.py/
        # game_tmnt_campaign.py -- there is no direct-load path. ---
        for target in range(1, 5):
            force_win_and_wait(m, r, from_stage=target - 1, label=f'{target-1}->{target}')
            got = word_at(m, GAME_STAGE_INDEX)
            r.check(f'Game_StageIndex advances {target-1} -> {target} ({got})', got == target)

        check_boss_stage(m, r, 4, 'out/spawn_stage3rock/spawn_table.bin', 'rock', 6)

        # --- The actual regression check: Rock's own reassignment must not
        # have disturbed the player's persistent char-select state (the real
        # symptom of the bug this closes). ---
        r.check(f'CharSelect_RosterCount unchanged after Rock\'s reassignment '
                 f'({byte_at(m, CharSelect_RosterCount)} == {expected_roster_count})',
                 byte_at(m, CharSelect_RosterCount) == expected_roster_count)
        r.check(f'CharSelect_Index unchanged after Rock\'s reassignment '
                 f'({byte_at(m, CharSelect_Index)} == {char_select_index_before})',
                 byte_at(m, CharSelect_Index) == char_select_index_before)

        # --- Continue on to stage 5 (Leather's own standalone boss stage)
        # -- proves this isn't a one-off, and that back-to-back blocking
        # Anim_LoadCharacter reloads (Rock's reassignment, then Leather's)
        # don't corrupt anything. ---
        force_win_and_wait(m, r, from_stage=4, label='4->5')
        got = word_at(m, GAME_STAGE_INDEX)
        r.check(f'Game_StageIndex advances 4 -> 5 ({got})', got == 5)

        check_boss_stage(m, r, 5, 'out/spawn_stage4leather/spawn_table.bin', 'leather', 7)

        # --- Same regression check after the SECOND back-to-back
        # reassignment (a different roster identity, Leather not Rock) --
        # proves the fix holds across repeated reassignments, not just once. ---
        r.check(f'CharSelect_RosterCount unchanged after Leather\'s reassignment '
                 f'({byte_at(m, CharSelect_RosterCount)} == {expected_roster_count})',
                 byte_at(m, CharSelect_RosterCount) == expected_roster_count)
        r.check(f'CharSelect_Index unchanged after Leather\'s reassignment '
                 f'({byte_at(m, CharSelect_Index)} == {char_select_index_before})',
                 byte_at(m, CharSelect_Index) == char_select_index_before)

        # --- Not hung after two real, blocking, spawn-driven reloads. ---
        fc0 = word_at(m, 0x7E5023)
        m.run_frames(60)
        m.pause()
        fc1 = word_at(m, 0x7E5023)
        r.check(f'Nmi_FrameCounter still advancing after both reassignments ({fc0} -> {fc1})',
                fc1 > fc0)

    r.finish()


if __name__ == '__main__':
    main()
