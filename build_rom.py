#!/usr/bin/env python3
# Build SNES-BOR ROM — LoROM, SA-1 + CC-DMA + MSU-1 PoC
import os
import re
import subprocess
import sys
import shutil
import hashlib
import json
from pathlib import Path

ROM_SIZE = 0x400000
BANK0_SIZE = 0x8000

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'bor_converter'))
import pack_msu_roster
from queue_abi import packed_count, plan_build, write_contract, source_set_names, assert_layout
from bor_levels import parse_levels_from_pak
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'scene_video'))
import convert_rugal
import convert_ending
import scene_sequences
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'audio'))
from shipped_content import (CAMPAIGN_CONFIGS, PLAYABLE_ROSTER_COUNT,
                              ROSTER_CONFIGS, ROSTER_PREFIXES, STAGE_CONFIGS,
                              SCENE_CONFIGS, normal_player_entries)
import build_audio

# Fixed initial roster for runtime MSU-1 character selection (see the plan
# at temporal-swinging-hartmanis.md). Replaces the old single-string
# MSU_DATA placeholder now that Anim_LoadCharacter reads a real directory.
# Phase 12 (plan.md 2.12): added out/joe as roster slot 2, converted from
# the real BOR pak via convert_character.py -- CharSelect_RosterCount is
# read from the packed file header at runtime (main.pasm), so no engine
# code needed to change for a 3rd roster slot to become selectable.
# Phase 15 (plan.md 2.15): added out/yashiro as roster slot 3, converted
# the same way -- picked specifically because Yashiro is the most-spawned
# enemy in the shipped level's (stage 1B) own spawn table. Entity #3 now
# loads this slot instead of reusing JHUN a second time (see main.pasm's
# Entity #3 Core_Oop_Create call, init param changed $0301 -> $0303).
# Follow-up (TMNT campaign, same day as Rock/Leather): the packed file
# format's roster directory was a hard 1-8 slot format (pack_msu_roster.py's
# byte 0x09, roster_count). 4 slots already used; the real TMNT campaign
# levels (sewer0/streets/streets2/sewer) reference 5 distinct real `enemy`-
# type fighters not yet in any roster (MOUSER, FOOT01-04, all converted --
# see out/mouser_*, out/foot0{1,2,3,4}_*) -- one more than the 4 remaining
# slots. FOOT01-04 are mechanically identical clones in the source data
# (same anim set, same health=70) -- picked FOOT01 as the one added first.
#
# Roster-growth slice (same session, real user-requested follow-up -- see
# core/spawn.pasm's Spawn_DoRosterReassign): the per-spawn character-
# identity gap this comment used to describe as a hard architectural wall
# was real but not a wall -- main.pasm's Anim_LoadCharacter is a reusable,
# already-mid-game-callable routine (the player's own Select-button
# reselect already called it live), so Spawn_Play now re-runs it for a
# specific AI slot when that spawn's real character is in the roster (see
# spawn.pasm's SPAWN_KIND_BOSS_IDENTIFIED). That made the roster's OWN
# 8-slot cap the real remaining limiter -- grown to 15 (pack_msu_
# roster.py's MAX_CHARACTERS). STALE as of finish_g8_with_runtime_asset_
# swapping.md: main.pasm's directory-seek was ALREADY rewritten to a real
# 16-bit accumulate loop by this same slice (see Anim_LoadCharacter_
# SeekRecord's own comment) -- 15 was never a hardware ceiling after that
# rewrite, only a soft Python-side sanity cap this comment mis-described;
# see pack_msu_roster.py's MAX_CHARACTERS for the corrected story. Grown
# again to 17 in the asset-swapping slice for MONEY/MEAT/1UP. BEBOP
# converted fresh in this slice too (it was never
# actually converted before -- Bebop's own boss stage always rendered a
# reskin) plus FOOT02-04 added using the new headroom. Ordinary (non-boss)
# enemies still render as a reskin: only characters deliberately added to
# this roster have anything real to identify against, and most spawned
# names in these levels still aren't roster members -- that's a content
# decision (which characters are "real"), not a remaining code gap.
# Slot 12 (2026-08-24): LEO (TMNT), the one playable turtle this pak's own
# data/MODELS.TXT actually loads (`load leo ...`; `don`/`mike` are present
# as real character data but commented out by the pak's own author, and no
# Raphael file exists in this pak at all -- checked directly, not assumed).
# Leo's real .TXT declares 21 anims (waiting/idle/slide/walk/get/jump/
# jumpattack/jumpattack2/attack1-4/grab/throw/pain/fall/rise/special/
# freespecial/grabattack/land); convert_character.py converts all of them
# (real frame data, inert ordinals) but only idle/walk/attack1/attack2/
# pain/fall/rise resolve to a known engine role -- jump/slide/grab-throw/
# special are real OpenBOR mechanics this engine doesn't implement
# (plan_game.md's own long-standing gap), not something invented here.

# Phase 6/9: the BG1 backdrop + BG3 HUD screen, appended to bor.msu as the
# BG section. Each entry is (bg_converter output dir, make_hud_tiles output
# dir). Mode (static whole-level vs. streaming) is auto-detected by
# pack_msu_roster.py from the bg_dir's manifest.json "streaming" key -- see
# that file's header comment. Regenerate with:
#   python tools/bg_converter/convert_bg.py --level "DATA\EASY\1BEASY.TXT" -o out/bg_stage1b --streaming
#   python tools/bg_converter/make_hud_tiles.py -o out/hud
#
# Phase G4 (plan_game.md 4, 2026-08-21): a real second stage, so a stage
# CLEAR can transition into something. Index 0 (stage 1B, "The bar") is
# unchanged from Phase 14 -- still the level the player starts on. Index 1
# is stage 1A ("The street"), the level Phase 14 replaced as the shipped
# default; its own converted assets (out/bg_stage1a, out/fp_stage1a,
# out/spawn_stage1a) stayed committed and buildable the whole time
# specifically so this day could reuse them without reconverting anything.
# BG_SCREENS/FP_SCREENS/SPAWN_TABLES below are now genuinely parallel,
# same-length, same-order lists -- see core/game_state.pasm's STAGE_COUNT
# and Stage_Load for the runtime side (main.pasm reads bg_count off the
# packed file header at boot, same as it already did before this phase --
# nothing there changed; what changed is there are now 2 records instead
# of 1, and the engine reads a Game_StageIndex-selected one instead of
# always record 0). Regenerate 1A's BG (kept committed, no longer the sole
# shipped level) with:
#   python tools/bg_converter/convert_bg.py --level "DATA\EASY\1AEASY.TXT" -o out/bg_stage1a --streaming
# Follow-up (same day): the two remaining real standalone TMNT boss levels,
# data\levels\Rock.txt and data\levels\Leather.txt (Rocksteady, Leatherhead)
# -- same real `boss 1` flag/pipeline as stage 2 (Bebop). Regenerate with:
#   python tools/bg_converter/convert_bg.py --pak "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak" --level "data\levels\Rock.txt" -o out/bg_stage3rock --streaming
#   python tools/bg_converter/convert_bg.py --pak "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak" --level "data\levels\Leather.txt" -o out/bg_stage4leather --streaming
# Follow-up (same day): the real 4-level TMNT main campaign (data\LEVELS00.TXT's
# "Play_Demo" set), in its own real order -- sewer0 -> streets -> streets2 ->
# sewer -- appended AFTER the standalone boss stages (indices 5-8) rather than
# renumbered in front of them: the standalone bosses were already shipped/
# gated at indices 2-4 in earlier commits on this branch, and inserting the
# campaign ahead of them would silently break anything that hardcoded those
# indices (nothing currently does, but there's no upside to reordering
# already-shipped, already-gated content). Regenerate with:
#   python tools/bg_converter/convert_bg.py --pak "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak" --level "data\levels\sewer0.txt" -o out/bg_stage5sewer0 --streaming
#   python tools/bg_converter/convert_bg.py --pak "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak" --level "data\levels\streets.txt" -o out/bg_stage6streets --streaming
#   python tools/bg_converter/convert_bg.py --pak "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak" --level "data\levels\streets2.txt" -o out/bg_stage7streets2 --streaming
#   python tools/bg_converter/convert_bg.py --pak "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak" --level "data\levels\sewer.txt" -o out/bg_stage8sewer --streaming
#
# Follow-up (same day): data\levels\foot.txt, the last standalone TMNT
# level -- real content, but NOT a boss record despite its "Foot Soldier
# Test" framing: `spawn Foot3 / alias Foot_Soldier / health 500` has no
# `boss 1` line at all (verified by reading the extracted level text, same
# as every other stage here -- `alias` is cosmetic in this engine, already
# established when converting the health-override slice). It's a single
# reinforced-HP (500 vs the normal 70) Foot Soldier encounter, nothing
# more -- shipped as stage 9, not part of G9's boss coverage. Regenerate:
#   python tools/bg_converter/convert_bg.py --pak "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak" --level "data\levels\foot.txt" -o out/bg_stage9foot --streaming
BG_SCREENS = [(stage["bg"], "out/hud") for stage in STAGE_CONFIGS]

# Phase 10 (plan.md 2.10): the frontpanel foreground layer for each entry in
# BG_SCREENS, same length/order -- an out/ dir (tools/bg_converter/
# convert_frontpanel.py output) or None if that BG has no frontpanel packed.
# Stage 1B has no `frontpanel` keyword in its own level file, so this is
# genuinely None here (not just unconverted) -- see BG_SCREENS' own comment.
# Stage 1A DOES have one (out/fp_stage1a, converted back in Phase 10/14 and
# kept committed) -- shipping it here means the stage transition exercises
# a real "no FP -> has FP" case, not just two FP-less levels. Regenerate with:
#   python tools/bg_converter/convert_frontpanel.py --level "DATA\EASY\1AEASY.TXT" -o out/fp_stage1a --width-tiles 408
FP_SCREENS = [stage["frontpanel"] for stage in STAGE_CONFIGS]

# Phase G4 (plan_game.md 4): one spawn-table blob per BG_SCREENS entry, same
# length/order -- was a single hand-synced SPAWN_MSU_OFFSET/SPAWN_COUNT
# global through Phase 14 (see git history), now a real per-stage list
# packed by pack_msu_roster.pack_roster()'s `spawns` param and discovered by
# the engine at runtime off each stage's own bg record (see that function's
# docstring, and core/spawn.pasm). check_spawn_constants() is GONE along
# with the hand-synced constants it used to cross-check -- there is nothing
# left in main.pasm for it to check. Regenerate 1A's with:
#   python tools/bg_converter/build_spawn_table.py "Beats of Rage Original [v.3.0 Build 4086].pak" "DATA\EASY\1AEASY.TXT" out/spawn_stage1a/spawn_table.bin
SPAWN_TABLES = [stage["spawn"] for stage in STAGE_CONFIGS]

if not (len(BG_SCREENS) == len(FP_SCREENS) == len(SPAWN_TABLES)):
    raise SystemExit("BG_SCREENS, FP_SCREENS, and SPAWN_TABLES must stay parallel")

BOR_CAMPAIGN_PREFIX = ("DATA\\EASY\\1AEASY.TXT", "DATA\\EASY\\1BEASY.TXT",
                       "DATA\\EASY\\1CEASY.TXT")
if tuple(stage["source_level"].upper() for stage in STAGE_CONFIGS[:3]) != BOR_CAMPAIGN_PREFIX:
    raise SystemExit("first three STAGE_CONFIGS entries must be BOR 1A, 1B, 1C")


def resolve_campaigns():
    """Resolve authored typed campaign identities to physical/runtime values."""
    by_source = {}
    for index, stage in enumerate(STAGE_CONFIGS):
        key = stage["source_level"].replace('/', '\\').upper()
        if key in by_source:
            raise SystemExit(f"campaign guard: duplicate catalog source {key}")
        by_source[key] = (index, stage)
    scene_ids = {entry["scene_id"].upper(): entry["runtime_id"]
                 for entry in SCENE_CONFIGS}
    resolved = {}
    typed = {}
    for campaign_id, campaign in CAMPAIGN_CONFIGS.items():
        indices = []
        entries = []
        seen = set()
        authored = campaign.get("entries")
        if authored is None:
            authored = [{"kind": "stage", "source_level": source}
                        for source in campaign["source_levels"]]
        for entry in authored:
            kind = str(entry.get("kind", "")).lower()
            if kind not in ("stage", "scene"):
                raise SystemExit(f"campaign guard: unknown entry kind {kind!r} in {campaign_id}")
            if kind == "scene":
                name = str(entry.get("scene_id", "")).upper()
                if name not in scene_ids:
                    raise SystemExit(f"campaign guard: {campaign_id} scene is not registered: {name}")
                entries.append(("scene", scene_ids[name], name))
                continue
            source = entry.get("source_level")
            if not source:
                raise SystemExit(f"campaign guard: stage entry missing source in {campaign_id}")
            key = source.replace('/', '\\').upper()
            if key in seen:
                raise SystemExit(f"campaign guard: duplicate {key} in {campaign_id}")
            seen.add(key)
            if key not in by_source:
                raise SystemExit(f"campaign guard: {campaign_id} source is not packed: {key}")
            index, stage = by_source[key]
            if campaign["family"] != "standalone" and stage["family"] != campaign["family"]:
                raise SystemExit(f"campaign guard: family mismatch for {key}")
            indices.append(index)
            entries.append(("stage", index, key))
        resolved[campaign_id] = indices
        typed[campaign_id] = entries
    bor_prefix = [by_source[source.replace('/', '\\').upper()][0]
                  for source in BOR_CAMPAIGN_PREFIX]
    if resolved["BOR_ORIGINAL"][:3] != bor_prefix:
        raise SystemExit("campaign guard: BOR 1A/1B/1C order is not preserved")
    if set(resolved["TMNT"]) & set(resolved["STANDALONE_TEST_CONTENT"]):
        raise SystemExit("campaign guard: standalone content overlaps TMNT campaign")
    return resolved, typed


CAMPAIGN_STAGE_MAPS, CAMPAIGN_ENTRY_MAPS = resolve_campaigns()


def write_campaign_include(normal_candidate=False, hard_candidate=False, bonus_candidate=False):
    """Emit the small assembly lookup used by runtime stage progression."""
    labels = {
        "BOR_ORIGINAL": "Bor",
        "BOR_NORMAL_1A_INTERNAL": "BorNormalDev",
        "BOR_HARD": "BorHard",
        "BOR_BONUS": "BorBonus",
        "TMNT": "Tmnt",
        "STANDALONE_TEST_CONTENT": "Standalone",
    }
    bor_stage = next(stage for stage in STAGE_CONFIGS if stage["family"] == "bor-original")
    bor_sets = parse_levels_from_pak(bor_stage["pak"], "DATA\\LEVELS.TXT")
    if [s.name for s in bor_sets] != ["Easy", "Normal", "Hard", "Bonus"]:
        raise SystemExit("BOR set guard: unexpected source set order")
    # An isolated native candidate is not a production release decision.
    available = {"Easy": True, "Normal": bool(normal_candidate),
                 "Hard": bool(hard_candidate), "Bonus": bool(bonus_candidate)}
    campaign_symbols = {"Easy": "CAMPAIGN_BOR_ORIGINAL",
                        "Normal": "CAMPAIGN_BOR_NORMAL_DEV",
                        "Hard": "CAMPAIGN_BOR_NORMAL_DEV", "Bonus": "CAMPAIGN_BOR_NORMAL_DEV"}
    lines = [
        "; Generated by build_rom.py from shipped_content.CAMPAIGN_CONFIGS.",
        "; Physical indices are resolved from source identities; do not edit.",
        "CAMPAIGN_ENTRY_STAGE = 0",
        "CAMPAIGN_ENTRY_SCENE = 1",
        "CAMPAIGN_BOR_NORMAL_DEV = 3",
        "BOR_SET_UNMAPPED = $FF",
        f"BOR_SET_COUNT = {len(bor_sets)}",
        "BorSet_Ids:",
        "    .db " + ", ".join(str(s.set_id) for s in bor_sets),
        "BorSet_IfComplete:",
        "    .db " + ", ".join(str(s.ifcomplete) for s in bor_sets),
        "BorSet_ContentAvailable:",
        "    .db " + ", ".join("1" if available[s.name] else "0" for s in bor_sets),
        "BorSet_CampaignMap:",
        "    .db " + ", ".join(campaign_symbols[s.name] if available[s.name]
                               else "BOR_SET_UNMAPPED" for s in bor_sets),
        "BOR_SET_NAME_WIDTH = 8",
        "BorSet_Names:",
    ]
    for source_set in bor_sets:
        encoded = source_set.name.encode('ascii')
        if len(encoded) >= 8:
            raise SystemExit(f"BOR set name too long: {source_set.name}")
        lines.append("    .db " + ", ".join(str(b) for b in encoded + b"\0" + bytes(7 - len(encoded))))
    lines.append("")
    for campaign_id, label in labels.items():
        values = ", ".join(str(value) for value in CAMPAIGN_STAGE_MAPS[campaign_id])
        entries = CAMPAIGN_ENTRY_MAPS[campaign_id]
        kinds = ", ".join("CAMPAIGN_ENTRY_SCENE" if kind == "scene"
                          else "CAMPAIGN_ENTRY_STAGE" for kind, _, _ in entries)
        value_expr = ", ".join("SceneSequence_" + name.capitalize() if kind == "scene"
                               else str(value)
                               for kind, value, name in entries)
        lines += [
            f"Campaign_{label}_EntryCount = {len(entries)}",
            f"Campaign_{label}_EntryKinds:",
            f"    .db {kinds}",
            f"Campaign_{label}_EntryValues:",
            f"    .db {value_expr}",
            "",
            f"Campaign_{label}_StageCount = {len(CAMPAIGN_STAGE_MAPS[campaign_id])}",
            f"Campaign_{label}_StageMap:",
            f"    .db {values}",
            "",
        ]
        if campaign_id in ("BOR_ORIGINAL", "BOR_NORMAL_1A_INTERNAL", "BOR_HARD", "BOR_BONUS"):
            authored = CAMPAIGN_CONFIGS[campaign_id]["entries"]
            if len(authored) != len(entries):
                raise SystemExit(f"BOR source guard: {campaign_id} entry metadata drift")
            flags_by_file = []
            for entry in authored:
                flag = entry.get("next_after")
                if flag not in (False, True, 0, 1):
                    raise SystemExit(f"BOR source guard: {campaign_id} missing/invalid next_after")
                flags_by_file.append(int(flag))
            flags = ", ".join(str(value) for value in flags_by_file)
            completion = CAMPAIGN_CONFIGS[campaign_id]['completion_flags']
            if len(completion) != len(entries) or any(type(v) is not int or v not in (0, 1) for v in completion):
                raise SystemExit(f"BOR completion policy drift: {campaign_id}")
            lines += [
                f"Campaign_{label}_NextFlags:",
                f"    .db {flags}",
                f"Campaign_{label}_CompleteFlags:",
                "    .db " + ", ".join(map(str, completion)),
                "",
            ]
    # Campaign ABI 3 selects the shared source-world runtime family. The
    # independently selected source set indexes these compiler-owned tables;
    # Hard is never inferred from Normal or physical-stage adjacency.
    source_entries = []
    offsets, counts = [], []
    for source_set in bor_sets:
        cid = {"Normal": "BOR_NORMAL_1A_INTERNAL", "Hard": "BOR_HARD", "Bonus": "BOR_BONUS"}.get(source_set.name)
        offsets.append(len(source_entries) if cid else 0)
        rows = CAMPAIGN_ENTRY_MAPS[cid] if cid else []
        counts.append(len(rows))
        if cid:
            cfg = CAMPAIGN_CONFIGS[cid]
            from compiler import Source, project
            authoritative = next(s for s in project(Source(bor_stage['pak'])).sets
                                 if s.source_id == source_set.set_id)
            if cfg['source_set_id'] != source_set.set_id or len(rows) != len(authoritative.entries):
                raise SystemExit('SOURCE_SET_LINK_INCOMPLETE: ' + source_set.name)
            source_entries.extend(zip(rows, cfg['completion_flags']))
    if len(source_entries) > 255:
        raise SystemExit('SOURCE_CAMPAIGN_TABLE_CAPACITY')
    for name, values in (
        ('Offsets', offsets), ('Counts', counts),
        ('Kinds', [int(row[0] == 'scene') for row, flag in source_entries]),
        ('Values', ['SceneSequence_' + row[2].capitalize() if row[0] == 'scene'
                    else str(row[1]) for row, flag in source_entries]),
        ('CompleteFlags', [flag for row, flag in source_entries])):
        lines += ['Campaign_Source_' + name + ':',
                  '    .db ' + ', '.join(map(str, values)), '']
    with open("tools/audio/campaign_config.pasm", "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(lines))

def write_stage_scroll_include():
    """Emit the physical-stage scroll-direction table used by the runtime."""
    values = []
    max_triggers = []
    mirrors = []
    for stage in STAGE_CONFIGS:
        direction = str(stage.get("scroll_direction", "right")).lower()
        if direction not in ("right", "left", "down"):
            raise SystemExit(f"unsupported shipped scroll direction: {direction}")
        values.append({"right": "STAGE_SCROLL_RIGHT", "left": "STAGE_SCROLL_LEFT", "down": "STAGE_SCROLL_DOWN"}[direction])
        mirrors.append(1 if stage.get("source_mirror", False) else 0)
        spawn_path = stage.get("spawn")
        if direction == "down" and spawn_path and os.path.exists(spawn_path):
            with open(spawn_path, "rb") as f:
                blob = f.read()
            max_triggers.append(max(
                (int.from_bytes(blob[i:i + 2], "little")
                 for i in range(0, len(blob), 10)),
                default=0))
        else:
            max_triggers.append(0)
    lines = [
        "; Generated by build_rom.py from shipped_content.STAGE_CONFIGS.",
        "; One byte per physical BG catalog entry; do not edit.",
        "STAGE_SCROLL_RIGHT = 0",
        "STAGE_SCROLL_DOWN = 1",
        "STAGE_SCROLL_LEFT = 2",
        "Stage_ScrollDirectionMap:",
        "    .db " + ", ".join(values),
        "Stage_ScrollMaxTriggerMap:",
        "    .db " + ", ".join(str(value) for value in max_triggers),
        "Stage_MirrorMap:",
        "    .db " + ", ".join(str(value) for value in mirrors),
    ]
    with open("tools/audio/stage_scroll_config.pasm", "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

def write_bor_player_select_include():
    """Emit source-order BOR player ordinals mapped to physical MSU slots."""
    entries = normal_player_entries("bor-original")
    lines = [
        "; Generated by build_rom.py from SOURCE_PLAYER_SELECTION.",
        "; Source selection ordinals are not physical roster indices.",
        f"BOR_SELECT_COUNT = {len(entries)}",
        "BorSelect_RuntimeMap:",
        "    .db " + ", ".join(str(index) for index, _ in entries),
    ]
    with open("tools/audio/bor_player_select_config.pasm", "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

# Task #13 (2026-08-20): the real compiled openborscript module shipped
# through the normal MSU/Vm_Load boot path, replacing the Gate 0 test
# fixture (gate0_module.bin) that shipped here since Gate 0a. Compiled from
# tools/bor_converter/openbor_script/fixtures/boot_spawn_wave1.c -- a
# synthetic entry-point script (see that file's own header for why it's
# synthetic rather than a mod pak's SPAWN000.C directly: the compiler has no
# codegen yet for a real script-to-script CALL with arguments) that reuses
# the exact same 9 natives vm_gate6.py already proved correct on real
# hardware against Double Dragon Moto's SPAWN000.C. Effect: spawns one AI
# entity 40 world-X pixels ahead of the player, at the player's Y, the first
# frame after boot. Packed at the very end of bor.msu so it can never move
# an earlier section's offset. This is the same file tools/verify/
# vm_gate0a.py byte-compares the loaded WRAM region against, and the same
# file tools/verify/vm_gate0.py recompiles fresh and diffs real boot
# execution against (via oracle.py) -- deliberately one file, not a copy, so
# the packed bytes and the ground truth cannot drift apart.
VM_MODULE = "tools/verify/vm_fixtures/boot_spawn_wave1_module.bin"

DOTNET = os.environ.get('DOTNET', r'C:\Users\chad\.dotnet\dotnet.exe')
POPPY_DLL = os.environ.get(
    'POPPY_DLL',
    r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')

def assemble():
    # Runs Poppy to (re)produce src/main.bin from src/main.pasm. Previously
    # a separate manual step -- running this script alone silently repacked
    # a STALE main.bin whenever main.pasm had been edited but not
    # reassembled, which cost a full debugging cycle chasing "fixes" that
    # were never actually built. Making this automatic removes that failure
    # mode entirely.
    if not (os.path.exists(DOTNET) or shutil.which(DOTNET)):
        print(f".NET executable not found: {DOTNET}. Set DOTNET to a working dotnet executable.",
              file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(POPPY_DLL):
        print(f"Poppy CLI not found: {POPPY_DLL}. Set POPPY_DLL to the built poppy.dll.",
              file=sys.stderr)
        sys.exit(1)
    result = subprocess.run([
        DOTNET, POPPY_DLL, 'src/main.pasm',
        '-o', 'src/main.bin',
        '-s', 'src/main.sym',
    ])
    if result.returncode != 0:
        print(f"Poppy assembly failed (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)

def write_campaign_layout_include(roster_sidecar):
    """Emit runtime constants from the finalized pack, before assembly."""
    stage_count = roster_sidecar["bg_count"]
    vm_offset = roster_sidecar["vm_offset"]
    vm_size = roster_sidecar["vm_size"]
    if stage_count != len(STAGE_CONFIGS) or not 0 < stage_count <= 255:
        raise SystemExit("campaign layout guard: packed stage count/catalog mismatch")
    if not 0 <= vm_offset <= 0xFFFFFFFF or not 0 < vm_size <= 0xFFFF:
        raise SystemExit("campaign layout guard: VM offset/size exceeds runtime fields")
    os.makedirs("src/generated", exist_ok=True)
    with open("src/generated/campaign_layout.pasm", "w",
              encoding="ascii", newline="\n") as f:
        f.write(
            "; Generated by build_rom.py from finalized packed metadata; do not edit.\n"
            f"STAGE_COUNT = {stage_count}\n"
            f"VM_MSU_OFFSET = ${vm_offset:08X}\n"
            f"VM_MODULE_SIZE = {vm_size}\n")


def check_spawn_table_freshness():
    """Regenerate every shipped spawn table against the current roster map.

    Spawn records embed roster indices, so changing ROSTER_PREFIXES can make
    an otherwise same-sized old table point at a different prop/actor.
    Compare the complete converter output, not merely record counts.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'tools', 'bg_converter'))
    from build_spawn_table import build_from_pak
    from production_campaign import compile_queues
    compiler_queues = compile_queues(STAGE_CONFIGS, ROSTER_CONFIGS)
    roster_lookup = {prefix.rsplit('/', 1)[-1].lower(): i
                     for i, prefix in enumerate(ROSTER_PREFIXES)}
    # Resolve source spawn aliases as well as converted directory names. K'
    # is authored as DATA\\CHARS\\K\\K.TXT but its converted directory is
    # k_prime; source identity must survive the spawn-table boundary.
    for index, entry in enumerate(ROSTER_CONFIGS):
        source_name = entry['source_character'].replace('\\', '/').rsplit('/', 1)[-1].lower()
        roster_lookup.setdefault(source_name, index)
    for stage in STAGE_CONFIGS:
        pak = os.path.abspath(stage['pak'])
        table = os.path.abspath(stage['spawn'])
        if not os.path.exists(pak) or not os.path.exists(table):
            continue
        if stage['family'] == 'bor-original':
            expected = compiler_queues[stage['spawn']]
        else:
            _, expected = build_from_pak(pak, stage['source_level'], roster_lookup)
        with open(table, 'rb') as f:
            actual = f.read()
        if actual != expected:
            first = next((i for i, (a, b) in enumerate(zip(actual, expected))
                          if a != b), min(len(actual), len(expected)))
            raise SystemExit(
                f"spawn table stale: source={stage['source_level']} "
                f"table={stage['spawn']} first_diff_record={first // 10} "
                f"byte={first % 10} committed_len={len(actual)} "
                f"expected_len={len(expected)}")
    print('spawn-table freshness: PASS (all tables match current PAK/roster mapping)')


def _load_poppy_symbols(path):
    symbols = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            # Poppy prints ROM offsets as four hex digits but WRAM equates
            # as the complete 24-bit address after the bank prefix.
            match = re.match(r'^\s*([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4,6})\s+(\S+)', line)
            if match:
                bank, address, name = match.groups()
                symbols[name] = (int(bank, 16) << 16) | int(address, 16)
    return symbols


def validate_bank0_layout(poppy_data, symbol_path):
    """Reject executable output that collides with the LoROM tail tables."""
    symbols = _load_poppy_symbols(symbol_path)
    required = ('scpu_boot', 'scpu_bank0_runtime_end', 'nmi_handler',
                'nmi_handler_end', 'irq_handler', 'irq_handler_end')
    missing = [name for name in required if name not in symbols]
    if missing:
        raise SystemExit('bank0 layout guard: missing symbols: ' + ', '.join(missing))

    expected = {
        # The source startup dispatch consumed the final three bytes before
        # the fixed boot body; keep the boot body aligned immediately after
        # runtime code while preserving the header/NMI/IRQ reservations.
        'scpu_boot': 0x00FC03,
        'nmi_handler': 0x00FFA0,
        'irq_handler': 0x00FFB0,
    }
    for name, value in expected.items():
        if symbols[name] != value:
            raise SystemExit(f'bank0 layout guard: {name} is ${symbols[name]:06X}, '
                             f'expected ${value:06X}')

    runtime_end = symbols['scpu_bank0_runtime_end'] & 0xFFFF
    nmi = symbols['nmi_handler'] & 0xFFFF
    nmi_end = symbols['nmi_handler_end'] & 0xFFFF
    irq = symbols['irq_handler'] & 0xFFFF
    irq_end = symbols['irq_handler_end'] & 0xFFFF
    if runtime_end > 0xFFA0:
        raise SystemExit(f'bank0 layout guard: runtime ends at ${runtime_end:04X}, '
                         'which reaches the NMI boundary $FFA0')
    if nmi != 0xFFA0 or nmi_end > 0xFFB0:
        raise SystemExit('bank0 layout guard: NMI stub crosses its reserved boundary')
    if irq != 0xFFB0 or irq_end > 0xFFC0:
        raise SystemExit('bank0 layout guard: IRQ stub crosses its reserved boundary')

    reserved = poppy_data[0x7FC0:0x8000]
    if any(reserved):
        first = 0x7FC0 + next(i for i, byte in enumerate(reserved) if byte)
        raise SystemExit(f'bank0 layout guard: emitted byte ${first:04X} in '
                         'header/vector window $7FC0-$7FFF')

    print(f'bank0 layout guard: PASS (runtime_end=${runtime_end:04X}, '
          f'free_before_nmi={0xFFA0 - runtime_end} bytes, '
          f'header_window=${0x7FC0:04X}-${0x7FFF:04X} empty)')


def validate_text_bank_layout(symbol_path):
    """Keep the font-adjacent text data in its documented LoROM bank."""
    symbols = _load_poppy_symbols(symbol_path)
    required = ('Text_StringPool', 'Text_StringPool_End', 'CharSelect_NamePtrs')
    missing = [name for name in required if name not in symbols]
    if missing:
        raise SystemExit('text bank layout guard: missing symbols: ' + ', '.join(missing))

    expected_bank = 0x02
    pool = symbols['Text_StringPool']
    pool_end = symbols['Text_StringPool_End']
    name_ptrs = symbols['CharSelect_NamePtrs']
    for name, value in (('Text_StringPool', pool),
                        ('Text_StringPool_End', pool_end),
                        ('CharSelect_NamePtrs', name_ptrs)):
        if value >> 16 != expected_bank:
            raise SystemExit(f'text bank layout guard: {name} is ${value:06X}, '
                             f'expected bank ${expected_bank:02X}')
    if pool_end <= pool or ((pool_end - 1) >> 16) != expected_bank:
        raise SystemExit('text bank layout guard: string pool crosses a ROM bank')

    print(f'text bank layout guard: PASS (pool=${pool:06X}-${pool_end - 1:06X}, '
          f'name_ptrs=${name_ptrs:06X})')


def validate_score_layout(symbol_path):
    """Keep the S1A 32-bit score/cache block at its audited WRAM ownership."""
    symbols = _load_poppy_symbols(symbol_path)
    required = {
        'Game_Score32': 0x7E58D1,
        'G13_P2Score32': 0x7E58D5,
        'HudCachedScore32': 0x7E58D9,
        'HudCachedP2Score32': 0x7E58DD,
        'P1_Lives16': 0x7E58E1,
        'P2_Lives16': 0x7E58E3,
        'HudCachedLives16': 0x7E58E5,
        'HudCachedP2Lives16': 0x7E58E7,
        'G12_AnimTrace_LastInput': 0x7E58D0,
        'VmCode_Wram': 0x7E6000,
        'G1_NumberSnapshotOffset': 0x7E2852,
        'Text_ScoreValue32': 0x7E2854,
        'Text_ScorePlace32': 0x7E2858,
        'Text_ScoreMode': 0x7E285C,
        'TadPrivate_stream_frame': 0x7E28A0,
    }
    missing = [name for name in required if name not in symbols]
    if missing:
        raise SystemExit('score layout guard: missing symbols: ' + ', '.join(missing))

    fields = ('Game_Score32', 'G13_P2Score32', 'HudCachedScore32',
              'HudCachedP2Score32')
    life_fields = ('P1_Lives16', 'P2_Lives16', 'HudCachedLives16',
                   'HudCachedP2Lives16')
    scratch = ('Text_ScoreValue32', 'Text_ScorePlace32')
    for name, expected in required.items():
        if name in fields and symbols[name] != expected:
            raise SystemExit(f'score layout guard: {name} is ${symbols[name]:06X}, '
                             f'expected ${expected:06X}')

    intervals = []
    for name in fields + life_fields + scratch:
        start = symbols[name]
        end = start + (1 if name in life_fields else 3)
        intervals.append((start, end, name))
    for start, end, name in intervals:
        if name in fields and start <= symbols['G12_AnimTrace_LastInput']:
            raise SystemExit(f'score layout guard: {name} overlaps G12 trace state')
        if name in fields + life_fields and end >= symbols['VmCode_Wram']:
            raise SystemExit(f'score layout guard: {name} reaches VM WRAM')
        if name in scratch and (start <= symbols['G1_NumberSnapshotOffset'] or
                                end >= symbols['TadPrivate_stream_frame']):
            raise SystemExit(f'score layout guard: {name} overlaps text/audio state')
    if not (symbols['Text_ScoreMode'] > symbols['Text_ScorePlace32'] + 3 and
            symbols['Text_ScoreMode'] < symbols['TadPrivate_stream_frame']):
        raise SystemExit('score layout guard: Text_ScoreMode overlaps text/audio state')
    for index, (start, end, name) in enumerate(intervals):
        for other_start, other_end, other_name in intervals[index + 1:]:
            if start <= other_end and other_start <= end:
                raise SystemExit(f'score layout guard: {name} overlaps {other_name}')
    aliases = {
        'Game_Lives': 'P1_Lives16',
        'G13_P2Lives': 'P2_Lives16',
        'HudCachedLives': 'HudCachedLives16',
        'HudCachedP2Lives': 'HudCachedP2Lives16',
    }
    for alias, canonical in aliases.items():
        if symbols.get(alias) != symbols[canonical]:
            raise SystemExit(f'score layout guard: {alias} is not an alias of {canonical}')
    if symbols['P1_Lives16'] <= symbols['HudCachedP2Score32'] + 3:
        raise SystemExit('score layout guard: P1 life block does not follow score block')
    if symbols['HudCachedP2Lives16'] + 1 >= symbols['VmCode_Wram']:
        raise SystemExit('score layout guard: P2 life cache reaches VM WRAM')

    print('score layout guard: PASS '
          '(Game_Score32=$7E58D1-$7E58D4, '
          'G13_P2Score32=$7E58D5-$7E58D8, '
          'HudCachedScore32=$7E58D9-$7E58DC, '
          'HudCachedP2Score32=$7E58DD-$7E58E0, '
          'P1_Lives16=$7E58E1-$7E58E2, P2_Lives16=$7E58E3-$7E58E4, '
          'HudCachedLives16=$7E58E5-$7E58E6, '
          'HudCachedP2Lives16=$7E58E7-$7E58E8)')


def bank0_layout_guard_self_test():
    symbols = {
        'scpu_boot': 0x00FC00,
        'scpu_bank0_runtime_end': 0x00FFA0,
        'nmi_handler': 0x00FFA0,
        'nmi_handler_end': 0x00FFB0,
        'irq_handler': 0x00FFB0,
        'irq_handler_end': 0x00FFC0,
    }
    try:
        runtime_end = symbols['scpu_bank0_runtime_end']
        if runtime_end >= 0xFFA0:
            raise ValueError('runtime reaches NMI boundary')
    except ValueError:
        print('bank0 layout guard self-test: PASS (broken runtime rejected)')
    else:
        raise SystemExit('bank0 layout guard self-test: FAILED')


def prepare_campaign_queues():
    from production_campaign import compile_queues
    from pathlib import Path
    for path, data in compile_queues(STAGE_CONFIGS, ROSTER_CONFIGS).items():
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)


def prepare_stage_environment_assets(configs=None, roster_configs=None, *,
                                     output_root='out/compiler_campaign/stage_water',
                                     generated_dir='src/generated', bor_c=None):
    """Materialize Normal water/FP cycles and emit water/bounds/HUD before assembly.

    Return private physical bindings for this pack; accepted Easy media and
    the shared catalog stay unchanged. All three helpers share source objects,
    and water/bounds consume the same parsed Normal IR.
    """
    from pathlib import Path
    from stage_water import normal_stage_inputs, materialize_normal, emit_tables
    from stage_frontpanel_bg2 import materialize_normal as materialize_frontpanels
    from stage_frontpanel_bg2 import motion_tables as frontpanel_motion_tables
    from stage_frontpanel_wram import allocation_proof as frontpanel_allocation_proof
    from stage_bounds import from_ir, emit_pasm
    from generate_hud_names import family_sources, render as render_hud_names
    from compiler import Source
    configs = STAGE_CONFIGS if configs is None else configs
    roster_configs = ROSTER_CONFIGS if roster_configs is None else roster_configs
    bor_c = bor_c or Path(__file__).resolve().parent/'out/bor_compile_s6/BOR.C'
    frontpanel_wram = frontpanel_allocation_proof()
    sources, normal_ir = normal_stage_inputs(configs)
    bounds = [None]*len(configs)
    for physical, ir in normal_ir.items():
        bounds[physical] = from_ir(ir)
    bounds_text = emit_pasm(bounds, bank=15)
    family_cache = {family:sources[str(path.resolve())]
                    for family,path in family_sources(configs).items()}
    # Explicit roster PAKs use the same source cache as family-bound models.
    hud_roster = [dict(cfg) for cfg in roster_configs]
    for cfg in hud_roster:
        if cfg.get('pak'):
            origin = str(Path(cfg['pak']).resolve())
            if origin not in sources:
                sources[origin] = Source(origin)
            cfg['pak'] = sources[origin]
    hud_text, hud_rows = render_hud_names(hud_roster, family_cache)
    materialized, water_rows, water_media = materialize_normal(
        configs, sources, normal_ir, bor_c, output_root)
    materialized, frontpanel_media = materialize_frontpanels(
        materialized, sources, normal_ir, bor_c, Path(output_root).parent/'stage_frontpanel')
    frontpanel_motion_text, frontpanel_motion = frontpanel_motion_tables(materialized, normal_ir)
    outputs = {
        'stage_frontpanel_tables.pasm': frontpanel_motion_text,
        'stage_water_tables.pasm': emit_tables(water_rows),
        'stage_bounds_tables.pasm': bounds_text,
        'hud_opponent_names.pasm': hud_text,
        'stage_environment_materialization.json': json.dumps(dict(
            normal_physical_ids=list(normal_ir), water_media=water_media, frontpanel_media=frontpanel_media,
            frontpanel_motion=frontpanel_motion,
            frontpanel_wram=frontpanel_wram,
            bounds=[dict(physical=i, source_path=normal_ir[i].source_path,
                         source_width=bounds[i].source_width, blocked=bounds[i].blocked,
                         endhole=bounds[i].endhole) for i in normal_ir],
            hud_names=hud_rows), indent=2)+'\n',
    }
    target = Path(generated_dir)
    target.mkdir(parents=True, exist_ok=True)
    for name,text in outputs.items():
        path = target/name
        if not path.exists() or path.read_text(encoding='ascii') != text:
            path.write_text(text, encoding='ascii', newline='\n')
    print(f'environment metadata: {len(normal_ir)} Normal stages, '
          f'{len(water_media)} water/rock BGs, {len(frontpanel_media)} Normal FP bindings, {len(hud_rows)} HUD names')
    return materialized


def build_msu_assets(write_output=True, source_sized_visual=False):
    """Build MSU data and generated metadata before ROM assembly.

    Scene aliases in campaign_config.pasm are assembled from the generated
    scene-video include, so that include must describe the same finalized
    records before Poppy reads main.pasm.
    """
    os.makedirs('build', exist_ok=True)
    os.makedirs('distribution', exist_ok=True)
    environment_configs = prepare_stage_environment_assets()
    # Queues are derived outputs, never a manually maintained campaign input.
    prepare_campaign_queues()
    missing = [p for p in SPAWN_TABLES + [VM_MODULE] if not os.path.exists(p)]
    if missing:
        raise SystemExit("missing required generated input(s): " + ", ".join(missing))
    check_spawn_table_freshness()
    spawn_blobs = [open(p, 'rb').read() for p in SPAWN_TABLES]
    queue_rows=[]
    set_paths={}
    from pak_extract import extract
    for pak in {s['pak'] for s in STAGE_CONFIGS}:
        for path,name in source_set_names(extract(pak,'DATA\\LEVELS.TXT').decode('latin1')).items():
            set_paths[(pak,path)]=name
    for i,(stage,blob) in enumerate(zip(STAGE_CONFIGS,spawn_blobs)):
        context=dict(project=stage['pak'],set_name=set_paths.get((stage['pak'],stage['source_level'].replace('\\','/').lower()),'standalone'),
                     stage=i,source_path=stage['source_level'])
        count=packed_count(blob,**context)
        queue_rows.append(dict(project=context['project'],set=context['set_name'],stage=i,
                               source_path=context['source_path'],packed_records=count))
    queue_plan=plan_build(queue_rows)
    vm_blob = open(VM_MODULE, 'rb').read()
    rugal_payload, rugal_stats = convert_rugal.build_payload(STAGE_CONFIGS[0]['pak'])
    ending_payloads = convert_ending.build_payloads(STAGE_CONFIGS[0]['pak'])
    ending_payloads['SEWER'] = convert_ending.build_clip(STAGE_CONFIGS[0]['pak'], 'SEWER')
    scene_video_entries = [{
        'scene_id': 1,
        'flags': 0,
        'width': convert_rugal.WIDTH,
        'height': convert_rugal.HEIGHT,
        'fps_num': 25,
        'fps_den': 1,
        'frame_count': convert_rugal.SOURCE_FRAMES,
        'payload': rugal_payload,
    }] + [{
        'scene_id': convert_ending.CLIP_IDS[name],
        'flags': stats['flags'], 'width': stats['width'], 'height': stats['height'],
        'fps_num': stats['fps_num'], 'fps_den': stats['fps_den'],
        'frame_count': stats['frame_count'], 'payload': payload,
    } for name, (payload, stats) in ending_payloads.items()]
    # Directory reservation follows the actual physical catalog.
    pack_msu_roster.MAX_BGS = len(BG_SCREENS)
    msu_data, roster_sidecar = pack_msu_roster.pack_roster(
        ROSTER_PREFIXES,
        bgs=[(cfg['bg'], BG_SCREENS[i][1]) for i,cfg in enumerate(environment_configs)],
        fps=[cfg['frontpanel'] for cfg in environment_configs], spawns=spawn_blobs,
        vm_blob=vm_blob, playable_count=PLAYABLE_ROSTER_COUNT,
        scene_video_entries=scene_video_entries, extended_maps=True)
    if source_sized_visual:
        visual_blob = Path('src/generated/production_source_visual.bin').read_bytes()
        visual_catalog = json.loads(Path('src/generated/production_source_visual.json').read_text(encoding='utf-8'))
        visual_offset = len(msu_data)
        msu_data += visual_blob
        roster_sidecar['source_visual'] = {
            'format': 'SVIS1',
            'entry_count': visual_catalog['summary']['entry_count'],
            'data_offset': visual_offset,
            'data_size': len(visual_blob),
            'sha256': hashlib.sha256(visual_blob).hexdigest(),
        }
    # Layout audits flatten main's includes, so publish these finalized
    # pack-derived constants before auditing the queue's WRAM ownership.
    write_campaign_layout_include(roster_sidecar)
    from stage_environment_abi import write_model_map_counts
    write_model_map_counts(ROSTER_PREFIXES, 'src/generated/stage_environment_maps.pasm')
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools', 'bor_compile'))
    from generate_environment import generate as generate_environment
    generate_environment(STAGE_CONFIGS, 'src/generated/stage_environment_bases.pasm')
    if roster_sidecar['queue_abi']['capacity']!=queue_plan['capacity']:
        raise SystemExit('queue compiler/linker capacity mismatch')
    write_contract(queue_plan,'src/generated/queue_abi')
    print('queue ABI/layout:', assert_layout(os.path.dirname(os.path.abspath(__file__)),queue_plan))
    pack_msu_roster.write_scene_video_metadata(
        'src/generated/scene_video_meta.pasm', roster_sidecar['scene_video'])

    def generated_track(symbol):
        for line in open('tools/audio/audio_music_ids.pasm', encoding='ascii'):
            if line.startswith(symbol + ' ='):
                return int(line.split('=', 1)[1].strip())
        raise SystemExit('generated scene music track is missing: ' + symbol)

    from compiler import Source, key
    clip_ids = {key(convert_rugal.SOURCE_PATH): 1}
    clip_ids.update({key(f'DATA/SCENES/{name}.GIF'): value
                     for name, value in convert_ending.CLIP_IDS.items()})
    scene_sequences.write('src/generated/scene_sequence_meta.pasm',
        scene_sequences.source_sequences(Source(STAGE_CONFIGS[0]['pak']),
            SCENE_CONFIGS, generated_track, clip_ids))
    if write_output:
        with open('build/bor.msu', 'wb') as f:
            f.write(msu_data)
    # Do not replace the runnable distribution's MSU while its ROM still
    # describes an older catalog. Publish only after assembly/layout checks.
    return msu_data, roster_sidecar


def prepare_source_visual_catalog():
    """Generate compiler-owned source-sized visual metadata for an opt-in build."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'tools', 'bor_compile'))
    from production_source_publication import write_catalog
    return write_catalog(
        ROSTER_CONFIGS,
        'src/generated/production_source_visual.json',
        'src/generated/production_source_visual.pasm')


def write_source_visual_layout_include(sidecar, *, enabled=False):
    visual = sidecar.get('source_visual') or {}
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'tools', 'bor_compile'))
    from production_source_publication import emit_policy_include
    catalog = json.loads(Path('src/generated/production_source_visual.json').read_text(
        encoding='utf-8'))
    emit_policy_include(catalog, 'src/generated/production_source_visual.pasm',
                        enabled=enabled, msu_offset=visual.get('data_offset', 0),
                        msu_size=visual.get('data_size', 0),
                        key_path='src/generated/production_source_visual_keys.pasm')


def reuse_pinned_audio(ref):
    """Non-audio rebuild: unchanged source inputs and hash-pinned encoded assets.

    This does not regenerate or claim to repair historical explorer evidence.
    """
    def git(*args): return subprocess.check_output(['git',*args])
    paths=git('ls-tree','-r','--name-only',ref,'--','tools/audio','soundwork/tad').decode().splitlines()
    for path in paths:
        # Git's own per-path text filters distinguish CRLF checkout text
        # from binary assets; never normalize arbitrary binary bytes.
        accepted=git('rev-parse',f'{ref}:{path}').strip()
        current=git('hash-object','--path',path,path).strip()
        if current!=accepted:
            raise SystemExit('refuse pinned audio reuse: changed input '+path)
    music=json.loads(git('show',f'{ref}:tools/audio/music_catalog.json'))
    for track in music['tracks']:
        if hashlib.sha256(open(track['msu_pcm_path'],'rb').read()).hexdigest()!=track['msu_pcm_hash']:
            raise SystemExit('refuse pinned audio reuse: PCM hash mismatch')
    sfx=json.loads(git('show',f'{ref}:tools/audio/sfx_production_banks.json'))
    for bank in sfx['banks']:
        path=f"soundwork/tad/build/sfx_banks/bank_{bank['bank_id']:02d}/common-data.bin"
        if hashlib.sha256(open(path,'rb').read()).hexdigest()!=bank['common_data_sha256']:
            raise SystemExit('refuse pinned audio reuse: SFX hash mismatch')
    print(f"pinned audio reuse PASS: {len(paths)} unchanged inputs, {len(music['tracks'])} PCMs, {len(sfx['banks'])} banks; ref={ref}")


def write_build_outputs(rom, msu_data, normal_candidate=False, candidate_dir=None):
    """Publish only the selected target after assembly/layout checks succeed."""
    if normal_candidate:
        target = str(candidate_dir or 'build/s8_candidate')
        # MSU music is resolved beside the loaded ROM. Copy only catalog-owned,
        # hash-verified companions; never move or relink production artifacts.
        with open('tools/audio/music_catalog.json', encoding='utf-8') as f:
            catalog = json.load(f)
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'verify'))
        from pcm_runtime import link_immutable_pcm
        companions = []
        for track in catalog['tracks']:
            source = track['msu_pcm_path']
            with open(source, 'rb') as f:
                if hashlib.sha256(f.read()).hexdigest() != track['msu_pcm_hash']:
                    raise SystemExit('candidate PCM hash mismatch: ' + source)
            companions.append((source, f"{target}/bor-{int(track['track_id'])}.pcm"))
        os.makedirs(target, exist_ok=True)
        link_immutable_pcm(Path('distribution'), Path(target))
        if {Path(destination).name for _, destination in companions} != {
                p.name for p in Path(target).glob('bor-*.pcm')}:
            raise SystemExit('candidate PCM sidecar set mismatch')
        outputs = [(f'{target}/bor.sfc', rom), (f'{target}/bor.msu', msu_data)]
    else:
        os.makedirs('build', exist_ok=True)
        os.makedirs('distribution', exist_ok=True)
        outputs = [('build/bor.sfc', rom), ('distribution/bor.sfc', rom),
                   ('distribution/bor.msu', msu_data)]
    for path, data in outputs:
        with open(path, 'wb') as f:
            f.write(data)
        print('Wrote ' + path)


def link_rom():
    """Assemble, validate, and return ROM bytes without publishing ROM/MSU.

    Uses the existing generated includes and refreshes src/main.bin/main.sym
    through assemble(). Diagnostic callers must supply matching existing MSU
    data to write_build_outputs(); this does not regenerate or certify media.
    """
    assemble()
    with open('src/main.bin', 'rb') as f:
        poppy_data = bytearray(f.read())
    print(f"Poppy binary: {len(poppy_data)} bytes (0x{len(poppy_data):X})")
    validate_bank0_layout(poppy_data, 'src/main.sym')
    validate_text_bank_layout('src/main.sym')
    validate_score_layout('src/main.sym')

    rom = bytearray(ROM_SIZE)
    # Historically clamped to BANK0_SIZE (32KB) because main.pasm was
    # single-bank only -- that clamp would now silently drop any `.bank N`
    # (N != 0) content straight out of the shipped ROM with no error (see
    # CLAUDE.md's Architecture section: cross-bank jsl/label resolution is
    # fixed in the fork as of 2026-08-19, so main.pasm can now use more than
    # bank 0). Copy the whole assembled binary; ROM_SIZE (4MB) is already the
    # real ceiling.
    if len(poppy_data) > ROM_SIZE:
        raise SystemExit('ROM resource overflow: assembled banks exceed target capacity')
    copy_len = len(poppy_data)
    rom[0:copy_len] = poppy_data[0:copy_len]

    # SA-1's reset vector (CRV) is hardware-forced into bank $00 on every
    # SA-1 reset (only a 16-bit PC is programmable), and bank $00-$1F
    # $8000-$FFFF maps directly to ROM banks 0-31 unless CXB ($2220) is
    # written -- main.pasm never writes it. So the SA-1 boots into the SAME
    # physical ROM region as the S-CPU's own main.bin, at $8000: that's
    # sa1_main, a complete routine already assembled into main.bin by
    # Poppy above. src/sa1/sa1_boot.pasm's `.bank 1` code is unreachable
    # from a bare CRV write and is not part of the build.

    # Header at $7FC0 (LoROM)
    title = b"BEATS OF RAGE SNES   "
    rom[0x7FC0:0x7FC0+21] = title
    rom[0x7FD5] = 0x23   # LoROM + SA-1
    rom[0x7FD6] = 0x35   # ROM+SA-1+RAM+Battery
    rom[0x7FD7] = 0x0C   # ROM size
    rom[0x7FD8] = 0x08   # RAM size
    rom[0x7FD9] = 0x01   # USA
    rom[0x7FDA] = 0x33   # Licensee
    rom[0x7FDB] = 0x00   # Version

    # Vectors — fixed by .org directives in main.pasm
    RESET = 0xFC03   # scpu_boot
    NMI = 0xFFA0     # nmi_handler (fixed bank-0 tail contract)
    IRQ = 0xFFB0     # irq_handler (fixed bank-0 tail contract)

    # COP/BRK/ABORT never fire intentionally in this codebase, but leaving
    # their vectors unset means they point at ROM offset 0 (zero-filled
    # RAM/whatever WRAM garbage lives at $00:0000), since `rom = bytearray()`
    # starts fully zeroed and nothing else writes these bytes. Any stray
    # BRK/COP -- e.g. PC running off the end of code into a zero/padding
    # region, since opcode $00 IS brk -- then vectors into WRAM and executes
    # whatever garbage is there, which is unrecoverable and looks like a
    # random, nondeterministic crash. Point them at the same rti stub as IRQ
    # so a spurious interrupt is merely a no-op instead of a runaway trap.
    COP = IRQ
    ABORT = IRQ

    # Native vectors at $7FE4
    rom[0x7FE4] = COP & 0xFF;    rom[0x7FE5] = (COP >> 8) & 0xFF    # COP
    rom[0x7FE6] = IRQ & 0xFF;    rom[0x7FE7] = (IRQ >> 8) & 0xFF    # BRK
    rom[0x7FE8] = ABORT & 0xFF;  rom[0x7FE9] = (ABORT >> 8) & 0xFF  # ABORT
    rom[0x7FEA] = NMI & 0xFF;    rom[0x7FEB] = (NMI >> 8) & 0xFF   # NMI
    rom[0x7FEC] = IRQ & 0xFF;    rom[0x7FED] = (IRQ >> 8) & 0xFF   # IRQ

    # Emulation vectors at $7FF4
    rom[0x7FF4] = COP & 0xFF;    rom[0x7FF5] = (COP >> 8) & 0xFF    # COP
    rom[0x7FF8] = ABORT & 0xFF;  rom[0x7FF9] = (ABORT >> 8) & 0xFF  # ABORT
    rom[0x7FFA] = NMI & 0xFF;    rom[0x7FFB] = (NMI >> 8) & 0xFF   # NMI
    rom[0x7FFC] = RESET & 0xFF;  rom[0x7FFD] = (RESET >> 8) & 0xFF  # RESET
    rom[0x7FFE] = IRQ & 0xFF;    rom[0x7FFF] = (IRQ >> 8) & 0xFF   # IRQ (shared w/ BRK in emulation mode)

    # Checksum
    total = sum(rom) & 0xFFFF
    complement = (~total) & 0xFFFF
    rom[0x7FDC] = complement & 0xFF
    rom[0x7FDD] = (complement >> 8) & 0xFF
    rom[0x7FDE] = total & 0xFF
    rom[0x7FDF] = (total >> 8) & 0xFF

    return bytes(rom)


def main(reuse_audio_from=None, normal_candidate=False, source_sized_visual=False,
         candidate_dir=None, hard_candidate=False, bonus_candidate=False):
    if bonus_candidate and not (normal_candidate and hard_candidate and source_sized_visual):
        raise SystemExit('BONUS_REQUIRES_COMPLETE_SOURCE_SIZED_CANDIDATE')
    from production_campaign import materialize_actor_bindings
    materialize_actor_bindings(ROSTER_CONFIGS)
    from production_campaign import materialize_stage_bindings
    materialize_stage_bindings(STAGE_CONFIGS)
    from source_noncombat import write_tables as write_noncombat
    write_noncombat(STAGE_CONFIGS, ROSTER_CONFIGS)
    if source_sized_visual:
        catalog = prepare_source_visual_catalog()
        if catalog['blockers']:
            raise SystemExit('source-sized visual catalog has blockers: ' +
                             json.dumps(catalog['blockers'][:8], sort_keys=True))
    prepare_campaign_queues()
    bank0_layout_guard_self_test()
    if hard_candidate and not (normal_candidate and source_sized_visual):
        raise SystemExit('HARD_REQUIRES_SOURCE_SIZED_CANDIDATE')
    write_campaign_include(normal_candidate=normal_candidate, hard_candidate=hard_candidate, bonus_candidate=bonus_candidate)
    write_stage_scroll_include()
    write_bor_player_select_include()
    if reuse_audio_from: reuse_pinned_audio(reuse_audio_from)
    else: build_audio.main()
    # Shared compiler/packing paths stay unchanged; defer candidate MSU output
    # so neither ordinary build/bor.msu nor distribution is published here.
    if normal_candidate:
        msu_data, roster_sidecar = build_msu_assets(
            write_output=False, source_sized_visual=source_sized_visual)
    else:
        msu_data, roster_sidecar = build_msu_assets(
            source_sized_visual=source_sized_visual)
    write_source_visual_layout_include(roster_sidecar,
                                       enabled=source_sized_visual)
    rom = link_rom()
    write_build_outputs(rom, msu_data, normal_candidate=normal_candidate,
                        candidate_dir=candidate_dir)

    print(f"ROM: {len(rom)} bytes")
    print(f"MSU: {len(msu_data)} bytes (bor.msu), roster: {', '.join(ROSTER_PREFIXES)}")
    for c in roster_sidecar["characters"]:
        print(f"  slot {c['slot']}: {c['prefix']} @ offset {c['data_offset']} "
              f"(idle={c['idle_frame_count']} walk={c['walk_frame_count']} attack={c['attack_frame_count']})")
    for b in roster_sidecar["bgs"]:
        print(f"  bg {b['slot']}: {b['bg_dir']} @ offset {b['data_offset']} "
              f"({b['bg_tile_count']} tiles, {b['hud_tile_count']} hud tiles, "
              f"{b['level_entry']}, spawn_offset={b['spawn_offset']} "
              f"spawn_count={b['spawn_count']})")
        fp = b.get('fp')
        if fp:
            print(f"    fp: {fp['fp_dir']} @ offset {fp['data_offset']} "
                  f"({fp['tile_count']} tiles, width_tiles={fp['width_tiles']})")
    print(f"Reset: ${rom[0x7FFD]<<8|rom[0x7FFC]:04X}  NMI: ${rom[0x7FFB]<<8|rom[0x7FFA]:04X}  IRQ: ${rom[0x7FFF]<<8|rom[0x7FFE]:04X}")
    print(f"Map: ${rom[0x7FD5]:02X}  Cart: ${rom[0x7FD6]:02X}")
    return 0

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-audio-from',help='non-audio rebuild: verify/reuse encoded audio pinned to this Git ref')
    parser.add_argument('--normal-candidate', action='store_true',
                        help='enable Normal only in isolated build/s8_candidate/bor.* outputs; not a release')
    parser.add_argument('--source-sized-visual', action='store_true',
                        help='generate source-sized visual catalog for the opt-in migration build')
    parser.add_argument('--candidate-dir', type=Path,
                        help='write an isolated Normal candidate to this directory instead of build/s8_candidate')
    args = parser.parse_args()
    exit(main(args.reuse_audio_from, normal_candidate=args.normal_candidate,
              source_sized_visual=args.source_sized_visual,
              candidate_dir=args.candidate_dir))
