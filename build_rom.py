#!/usr/bin/env python3
# Build SNES-BOR ROM — LoROM, SA-1 + CC-DMA + MSU-1 PoC
import os
import subprocess
import sys

ROM_SIZE = 0x400000
BANK0_SIZE = 0x8000

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'bor_converter'))
import pack_msu_roster

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
# roster.py's MAX_CHARACTERS; 15 is a real hardware-arithmetic ceiling of
# main.pasm's existing 8-bit directory-seek math, not an arbitrary number,
# see that constant's own comment), and BEBOP converted fresh (it was never
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
ROSTER_PREFIXES = ["out/ralf", "out/jhun", "out/joe", "out/yashiro", "out/mouser", "out/foot01",
                   "out/rock", "out/leather", "out/bebop", "out/foot02", "out/foot03", "out/foot04",
                   "out/leo",
                   # Real prop/pickup sprite art (notjustfreespecial.txt
                   # follow-up to G8's own "deliberately still not done"
                   # item): APPLE is a real MISC item entity (DATA\CHARS\
                   # MISC\APPLE.TXT), converted via tools/bor_converter/
                   # convert_prop.py (its own idle-only pipeline, NOT
                   # convert_character.py -- see that script's docstring for
                   # why). A representative single real converted prop, not
                   # every pickup type -- build_spawn_table.py's roster_
                   # lookup-by-item-name mechanism (same one bosses already
                   # use) picks this up automatically for any spawn whose
                   # real item name is "apple", with zero engine-side
                   # per-item-type code; other pickup types (money/meat/
                   # 1up) still render using a borrowed roster character
                   # until they get their own convert_prop.py pass too.
                   "out/apple"]

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
BG_SCREENS = [("out/bg_stage1b", "out/hud"), ("out/bg_stage1a", "out/hud"),
              ("out/bg_stage2boss", "out/hud"), ("out/bg_stage3rock", "out/hud"),
              ("out/bg_stage4leather", "out/hud"), ("out/bg_stage5sewer0", "out/hud"),
              ("out/bg_stage6streets", "out/hud"), ("out/bg_stage7streets2", "out/hud"),
              ("out/bg_stage8sewer", "out/hud"), ("out/bg_stage9foot", "out/hud")]

# Phase 10 (plan.md 2.10): the frontpanel foreground layer for each entry in
# BG_SCREENS, same length/order -- an out/ dir (tools/bg_converter/
# convert_frontpanel.py output) or None if that BG has no frontpanel packed.
# Stage 1B has no `frontpanel` keyword in its own level file, so this is
# genuinely None here (not just unconverted) -- see BG_SCREENS' own comment.
# Stage 1A DOES have one (out/fp_stage1a, converted back in Phase 10/14 and
# kept committed) -- shipping it here means the stage transition exercises
# a real "no FP -> has FP" case, not just two FP-less levels. Regenerate with:
#   python tools/bg_converter/convert_frontpanel.py --level "DATA\EASY\1AEASY.TXT" -o out/fp_stage1a --width-tiles 408
FP_SCREENS = [None, "out/fp_stage1a", None, None, None, None, None, None, None, None]

# Phase G4 (plan_game.md 4): one spawn-table blob per BG_SCREENS entry, same
# length/order -- was a single hand-synced SPAWN_MSU_OFFSET/SPAWN_COUNT
# global through Phase 14 (see git history), now a real per-stage list
# packed by pack_msu_roster.pack_roster()'s `spawns` param and discovered by
# the engine at runtime off each stage's own bg record (see that function's
# docstring, and core/spawn.pasm). check_spawn_constants() is GONE along
# with the hand-synced constants it used to cross-check -- there is nothing
# left in main.pasm for it to check. Regenerate 1A's with:
#   python tools/bg_converter/build_spawn_table.py "Beats of Rage Original [v.3.0 Build 4086].pak" "DATA\EASY\1AEASY.TXT" out/spawn_stage1a/spawn_table.bin
SPAWN_TABLES = ["out/spawn_stage1b/spawn_table.bin", "out/spawn_stage1a/spawn_table.bin",
                "out/spawn_stage2boss/spawn_table.bin", "out/spawn_stage3rock/spawn_table.bin",
                "out/spawn_stage4leather/spawn_table.bin", "out/spawn_stage5sewer0/spawn_table.bin",
                "out/spawn_stage6streets/spawn_table.bin", "out/spawn_stage7streets2/spawn_table.bin",
                "out/spawn_stage8sewer/spawn_table.bin", "out/spawn_stage9foot/spawn_table.bin"]

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

DOTNET = r'C:\Users\chad\.dotnet\dotnet.exe'
POPPY_DLL = r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'

def assemble():
    # Runs Poppy to (re)produce src/main.bin from src/main.pasm. Previously
    # a separate manual step -- running this script alone silently repacked
    # a STALE main.bin whenever main.pasm had been edited but not
    # reassembled, which cost a full debugging cycle chasing "fixes" that
    # were never actually built. Making this automatic removes that failure
    # mode entirely.
    result = subprocess.run([DOTNET, POPPY_DLL, 'src/main.pasm', '-s', 'src/main.sym'])
    if result.returncode != 0:
        print(f"Poppy assembly failed (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)

def check_stage_count(roster_sidecar):
    """Phase G4 (plan_game.md 4): cross-checks core/game_state.pasm's
    hand-synced STAGE_COUNT constant against the packed bor.msu's real
    bg_count. STAGE_COUNT can't be computed by the engine itself (it gates
    Game_State_Play__stageclear's "no more stages -> ENDING" check before
    any MSU read happens that frame) so it's hand-synced, same accepted-
    risk pattern as this file's other build-time cross-checks.
    """
    import re
    text = open('src/core/game_state.pasm', encoding='utf-8').read()
    m = re.search(r'STAGE_COUNT\s*=\s*(\d+)', text)
    if not m:
        print("check_stage_count: couldn't find STAGE_COUNT in "
              "src/core/game_state.pasm", file=sys.stderr)
        sys.exit(1)
    pasm_count = int(m.group(1))
    real_count = roster_sidecar["bg_count"]
    if pasm_count != real_count:
        print(f"check_stage_count: MISMATCH -- src/core/game_state.pasm has "
              f"STAGE_COUNT={pasm_count}, but the just-packed bor.msu has "
              f"bg_count={real_count} (BG_SCREENS has {len(BG_SCREENS)} "
              f"entries). Update src/core/game_state.pasm to match and "
              f"rebuild.", file=sys.stderr)
        sys.exit(1)
    print(f"check_stage_count: OK (STAGE_COUNT={pasm_count})")


def check_vm_constants(roster_sidecar):
    """The check_spawn_constants pattern, applied to the script VM's module
    (Gate 0a, plan_vm.md 1). src/core/vm/vm_load.pasm hand-syncs
    VM_MSU_OFFSET/VM_MODULE_SIZE because neither can be computed by main.pasm
    -- the module's file offset depends on every character/BG/FP/spawn blob
    packed before it. Without this check, any future asset that changes size
    shifts the module and the loader silently reads whatever bytes now sit
    there: a garbage module with a plausible-looking header.
    """
    import re
    text = open('src/core/vm/vm_load.pasm', encoding='utf-8').read()
    offset_m = re.search(r'VM_MSU_OFFSET\s*=\s*\$([0-9A-Fa-f]+)', text)
    size_m = re.search(r'VM_MODULE_SIZE\s*=\s*(\d+)', text)
    if not offset_m or not size_m:
        print("check_vm_constants: couldn't find VM_MSU_OFFSET/VM_MODULE_SIZE "
              "in src/core/vm/vm_load.pasm", file=sys.stderr)
        sys.exit(1)
    pasm_offset = int(offset_m.group(1), 16)
    pasm_size = int(size_m.group(1))
    real_offset = roster_sidecar["vm_offset"]
    real_size = roster_sidecar["vm_size"]
    if pasm_offset != real_offset or pasm_size != real_size:
        print(f"check_vm_constants: MISMATCH -- src/core/vm/vm_load.pasm has "
              f"VM_MSU_OFFSET=${pasm_offset:06X} VM_MODULE_SIZE={pasm_size}, "
              f"but the just-packed bor.msu has vm_offset=${real_offset:06X} "
              f"vm_size={real_size}. Update src/core/vm/vm_load.pasm to match "
              f"and rebuild.", file=sys.stderr)
        sys.exit(1)
    print(f"check_vm_constants: OK (offset=${real_offset:06X}, size={real_size})")


def main():
    assemble()
    poppy_data = bytearray(open('src/main.bin', 'rb').read())
    print(f"Poppy binary: {len(poppy_data)} bytes (0x{len(poppy_data):X})")

    rom = bytearray(ROM_SIZE)
    # Historically clamped to BANK0_SIZE (32KB) because main.pasm was
    # single-bank only -- that clamp would now silently drop any `.bank N`
    # (N != 0) content straight out of the shipped ROM with no error (see
    # CLAUDE.md's Architecture section: cross-bank jsl/label resolution is
    # fixed in the fork as of 2026-08-19, so main.pasm can now use more than
    # bank 0). Copy the whole assembled binary; ROM_SIZE (4MB) is already the
    # real ceiling.
    copy_len = min(len(poppy_data), ROM_SIZE)
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
    RESET = 0xFC00   # scpu_boot
    NMI = 0xFFA0     # nmi_handler (rti stub)
    IRQ = 0xFFB0     # irq_handler (rti stub)

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

    os.makedirs('build', exist_ok=True)
    os.makedirs('distribution', exist_ok=True)
    
    # Write ROMs
    with open('build/bor.sfc', 'wb') as f:
        f.write(rom)
    with open('distribution/bor.sfc', 'wb') as f:
        f.write(rom)

    # Write MSU-1 data files
    spawn_blobs = [open(p, 'rb').read() if os.path.exists(p) else b"" for p in SPAWN_TABLES]
    vm_blob = open(VM_MODULE, 'rb').read() if os.path.exists(VM_MODULE) else b""
    msu_data, roster_sidecar = pack_msu_roster.pack_roster(
        ROSTER_PREFIXES, bgs=BG_SCREENS, fps=FP_SCREENS, spawns=spawn_blobs,
        vm_blob=vm_blob)
    check_stage_count(roster_sidecar)
    check_vm_constants(roster_sidecar)
    with open('build/bor.msu', 'wb') as f:
        f.write(msu_data)
    with open('distribution/bor.msu', 'wb') as f:
        f.write(msu_data)

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
    exit(main())
