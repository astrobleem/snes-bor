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
ROSTER_PREFIXES = ["out/ralf", "out/jhun", "out/joe", "out/yashiro"]

# Phase 6/9: the BG1 backdrop + BG3 HUD screen, appended to bor.msu as the
# BG section. Each entry is (bg_converter output dir, make_hud_tiles output
# dir). Mode (static whole-level vs. streaming) is auto-detected by
# pack_msu_roster.py from the bg_dir's manifest.json "streaming" key -- see
# that file's header comment. Regenerate with:
#   python tools/bg_converter/convert_bg.py --level "DATA\EASY\1BEASY.TXT" -o out/bg_stage1b --streaming
#   python tools/bg_converter/make_hud_tiles.py -o out/hud
#
# Phase 14 (plan.md 2.14, 2026-08-16): second real level, replacing stage 1A
# as the shipped default -- same pattern as when 1A replaced the old
# synthetic out/bg_boss_level. Stage 1B ("The bar") is a genuinely different
# shape of level than 1A: only 2 distinct panel images (order "aabaabaab...",
# 14 panels/1120 BOR px = 896 SNES px/140 tiles wide -- narrower than 1A's
# 408) and, unlike 1A, NO frontpanel layer at all (level.frontpanel is None
# -- confirmed via level_parse.py). 2347 unique 4bpp tiles, still well past
# the 1024-tile static-load budget, so streaming mode is still needed even
# at this narrower width. out/bg_stage1a's data (and out/bg_boss_level's)
# stays committed and buildable -- only this list changed.
BG_SCREENS = [("out/bg_stage1b", "out/hud")]

# Phase 10 (plan.md 2.10): the frontpanel foreground layer for each entry in
# BG_SCREENS, same length/order -- an out/ dir (tools/bg_converter/
# convert_frontpanel.py output) or None if that BG has no frontpanel packed.
# Stage 1B has no `frontpanel` keyword in its own level file, so this is
# genuinely None here (not just unconverted) -- see BG_SCREENS' own comment.
# Regenerate 1A's (kept committed, no longer shipped) with:
#   python tools/bg_converter/convert_frontpanel.py --level "DATA\EASY\1AEASY.TXT" -o out/fp_stage1a --width-tiles 408
FP_SCREENS = [None]

# Spawn-table phase (plan.md 2.13)/Phase 14 (plan.md 2.14): the single global
# spawn queue for BG_SCREENS[0]'s level, built by tools/bg_converter/
# build_spawn_table.py from the same level script. Regenerate 1B's with:
#   python tools/bg_converter/build_spawn_table.py "Beats of Rage Original [v.3.0 Build 4086].pak" "DATA\EASY\1BEASY.TXT" out/spawn_stage1b/spawn_table.bin
# 1A's spawn table (out/spawn_stage1a, kept committed) was regenerated the
# same way with "DATA\EASY\1AEASY.TXT" instead.
SPAWN_TABLE = "out/spawn_stage1b/spawn_table.bin"

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

def check_spawn_constants(roster_sidecar):
    """Cross-checks src/main.pasm's hand-synced SPAWN_MSU_OFFSET/SPAWN_COUNT
    constants (core/spawn.pasm) against what pack_msu_roster.py just
    actually computed. These can't be computed by main.pasm itself (the
    spawn blob's file offset depends on every character/BG/FP blob packed
    before it, all of which can change size independently) so they're baked
    by hand -- same accepted-risk pattern as this file's own RESET/NMI/IRQ
    vector constants. This check is the "caught at build time instead of
    silently reading garbage at runtime" insurance for that pattern.
    """
    import re
    text = open('src/core/spawn.pasm', encoding='utf-8').read()
    offset_m = re.search(r'SPAWN_MSU_OFFSET\s*=\s*\$([0-9A-Fa-f]+)', text)
    count_m = re.search(r'SPAWN_COUNT\s*=\s*(\d+)', text)
    if not offset_m or not count_m:
        print("check_spawn_constants: couldn't find SPAWN_MSU_OFFSET/SPAWN_COUNT "
              "in src/core/spawn.pasm", file=sys.stderr)
        sys.exit(1)
    pasm_offset = int(offset_m.group(1), 16)
    pasm_count = int(count_m.group(1))
    real_offset = roster_sidecar["spawn_offset"]
    real_count = roster_sidecar["spawn_count"]
    if pasm_offset != real_offset or pasm_count != real_count:
        print(f"check_spawn_constants: MISMATCH -- src/core/spawn.pasm has "
              f"SPAWN_MSU_OFFSET=${pasm_offset:06X} SPAWN_COUNT={pasm_count}, "
              f"but the just-packed bor.msu has spawn_offset=${real_offset:06X} "
              f"spawn_count={real_count}. Update src/core/spawn.pasm to match "
              f"and rebuild.", file=sys.stderr)
        sys.exit(1)
    print(f"check_spawn_constants: OK (offset=${real_offset:06X}, count={real_count})")


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
    NMI = 0xFF90     # nmi_handler (rti stub)
    IRQ = 0xFFA0     # irq_handler (rti stub)

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
    spawn_blob = open(SPAWN_TABLE, 'rb').read() if os.path.exists(SPAWN_TABLE) else b""
    vm_blob = open(VM_MODULE, 'rb').read() if os.path.exists(VM_MODULE) else b""
    msu_data, roster_sidecar = pack_msu_roster.pack_roster(
        ROSTER_PREFIXES, bgs=BG_SCREENS, fps=FP_SCREENS, spawn_blob=spawn_blob,
        vm_blob=vm_blob)
    check_spawn_constants(roster_sidecar)
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
              f"{b['level_entry']})")
        fp = b.get('fp')
        if fp:
            print(f"    fp: {fp['fp_dir']} @ offset {fp['data_offset']} "
                  f"({fp['tile_count']} tiles, width_tiles={fp['width_tiles']})")
    print(f"Reset: ${rom[0x7FFD]<<8|rom[0x7FFC]:04X}  NMI: ${rom[0x7FFB]<<8|rom[0x7FFA]:04X}  IRQ: ${rom[0x7FFF]<<8|rom[0x7FFE]:04X}")
    print(f"Map: ${rom[0x7FD5]:02X}  Cart: ${rom[0x7FD6]:02X}")
    return 0

if __name__ == '__main__':
    exit(main())
