#!/usr/bin/env python3
"""plan_game.md Phase G5 gate: real SRAM-backed music-volume persistence
(core/options.pasm's Options_Init/VolumeUp/VolumeDown, reachable from the
pause menu's volume row -- core/pausemenu.pasm).

Real-OpenBOR-sourced scope (see core/options.pasm's own header): the ONE
real, buildable option this project ships is music volume
(savedata.musicvol in engine/openbor.c), applied via TAD's real
SET_GLOBAL_MUSIC_VOLUME command. Everything else real BOR's savedata
struct persists (control remap, gamma/brightness, SFX volume, difficulty)
has no real content behind it in this project -- see that file's header
for the full closure reasoning, same as plan_game.md 8a's settime/maxenemy.

Real hardware fact this gate proves, not just asserts (2026-08-23, from
Mesen2's own C++ core -- see core/options.pasm's header for the full
citation): SA-1's classic S-CPU $6000-$7FFF window is real battery-backed
cartridge save RAM, backed by a .srm file that Mesen2 only writes on a
clean process shutdown (BatteryManager::SaveBattery, called from the
emulator's power-off path) and only reads back on a fresh cartridge load
(BaseCartridge's own load path) -- NOT on m.reset_emulator(), which
touches neither. This is exactly the shape of bug this project's own
CLAUDE.md/memory warns about (phase7's TAD "PLAYING but silent" bug): a
gate that only calls reset_emulator() would falsely PASS even if nothing
ever reached the .srm and the SRAM code were a complete no-op. So this
gate does the real thing: session 1 changes the volume through actual
input (not a WRAM poke) and cleanly closes the Mesen process; the .srm
Mesen actually wrote is byte-checked directly off disk; THEN a second,
completely separate Mesen process is launched against the same ROM and
must load the persisted (non-default) value, not silently re-default.

Checks:
  1. A fresh cart boots with the default music volume (Options_Init's
     first-ever-boot path, magic mismatch on a blank .srm).
  2. Down x2 from the pause menu's default CONTINUE selection reaches the
     volume row (PAUSE_SELECTOR_VOLUME).
  3. Left x3 lowers the volume by real input, to a value distinct from the
     default, persisted to SRAM immediately (core/options.pasm's own
     "no separate save step" design, matching real BOR's own
     menu_options_sound()).
  4. Start on the volume row resumes GAME_STATE_PLAYING (nothing to commit
     -- see core/pausemenu.pasm's own header).
  5. The .srm file on disk (ground truth, not an engine self-report) has
     the real magic/version/volume bytes at the real physical BW-RAM
     offset ($6000-$6003 in the S-CPU window = offset 0-3 of the file).
  6. A SEPARATE, freshly-launched Mesen process against the same ROM loads
     the persisted (non-default) volume into WRAM, not the default --the
     actual proof of persistence across a "power cycle".
  7. The pause menu's volume row visibly redraws the persisted value too,
     not just WRAM -- BG3 tilemap ground truth, same convention as
     game_g5_pause.py (never a screenshot -- see
     mesen_screenshot_stale_hud_layer).

Usage: python tools/verify/game_g5_sram.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, Reporter, MESEN_EXE  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')

PAUSE_SELECTOR_VOLUME = pasm_constant_in('src/core/pausemenu.pasm', 'PAUSE_SELECTOR_VOLUME')
Pause_Selector = pasm_constant_in('src/core/pausemenu.pasm', 'Pause_Selector')
PAUSE_ROW_VOLUME = pasm_constant_in('src/core/pausemenu.pasm', 'PAUSE_ROW_VOLUME')

Options_MusicVolume = pasm_constant_in('src/core/options.pasm', 'Options_MusicVolume')
OPTIONS_MUSICVOL_DEFAULT = pasm_constant_in('src/core/options.pasm', 'OPTIONS_MUSICVOL_DEFAULT')
OPTIONS_MUSICVOL_STEP = pasm_constant_in('src/core/options.pasm', 'OPTIONS_MUSICVOL_STEP')
OPTIONS_MAGIC0_VALUE = pasm_constant_in('src/core/options.pasm', 'OPTIONS_MAGIC0_VALUE')
OPTIONS_MAGIC1_VALUE = pasm_constant_in('src/core/options.pasm', 'OPTIONS_MAGIC1_VALUE')
OPTIONS_VERSION_CURRENT = pasm_constant_in('src/core/options.pasm', 'OPTIONS_VERSION_CURRENT')

FONT_TILES_VRAM_WORD = pasm_constant_in('src/core/text.pasm', 'FONT_TILES_VRAM_WORD')
BG3_TILES_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILES_VRAM_WORD')
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) // 8
FONT_ASCII_FIRST = pasm_constant_in('src/core/text.pasm', 'FONT_ASCII_FIRST')
BG3_TILEMAP_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILEMAP_VRAM_WORD')

TEXT_ROW_ENTRIES = 32

# Mesen2 runs in portable mode here (a Saves/ folder already lives next to
# the .exe, confirmed 2026-08-23) -- battery saves land at
# <mesen exe dir>/Saves/<rom basename>.srm (BatteryManager::GetBasePath +
# FolderUtilities::GetSaveFolder). Derived from MESEN_EXE, not hardcoded,
# so this still works if the Mesen2 checkout ever moves.
SRM_PATH = os.path.join(os.path.dirname(MESEN_EXE), 'Saves', 'bor.srm')

EXPECTED_LOWERED = OPTIONS_MUSICVOL_DEFAULT - OPTIONS_MUSICVOL_STEP * 3
assert 0 <= EXPECTED_LOWERED < OPTIONS_MUSICVOL_DEFAULT, \
    'gate assumption: 3 Left-presses from the default must land in range, distinct from default'


def read_row_words(m, row, count=TEXT_ROW_ENTRIES):
    byte_off = (BG3_TILEMAP_VRAM_WORD + row * TEXT_ROW_ENTRIES) * 2
    length = max(32, count * 2)
    raw = read_block(m, byte_off, length=length, mem_type='snesVideoRam')
    words = []
    for i in range(count):
        lo, hi = raw[i * 2], raw[i * 2 + 1]
        words.append(lo | (hi << 8))
    return words


def decode_row(m, row):
    words = read_row_words(m, row)
    chars = []
    for w in words:
        tile_id = w & 0x03FF
        chars.append(chr(tile_id - FONT_TILE_INDEX_BASE + FONT_ASCII_FIRST))
    return ''.join(chars)


def enter_pause_and_select_volume(m, r, label):
    m.set_input(m.BTN_START, 10)
    m.run_frames(15)
    m.pause()
    m.set_input(m.BTN_DOWN, 10)
    m.run_frames(15)
    m.pause()
    m.set_input(m.BTN_DOWN, 10)
    m.run_frames(15)
    m.pause()
    selector = read_block(m, Pause_Selector, 32)[0]
    r.check(f'{label}: Down x2 from default selects the volume row ({selector})',
            selector == PAUSE_SELECTOR_VOLUME)


def main():
    r = Reporter('G5-SRAM', kind='GATE')

    # --- Session 1: real input lowers the volume; clean shutdown flushes it. ---
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        vol = read_block(m, Options_MusicVolume, 32)[0]
        r.check(f'fresh boot initializes the default music volume ({vol})',
                vol == OPTIONS_MUSICVOL_DEFAULT)

        enter_pause_and_select_volume(m, r, 'session 1')

        for _ in range(3):
            m.set_input(m.BTN_LEFT, 10)
            m.run_frames(10)
        m.pause()
        vol = read_block(m, Options_MusicVolume, 32)[0]
        r.check(f'Left x3 lowers the volume to a non-default value ({vol}, expected {EXPECTED_LOWERED})',
                vol == EXPECTED_LOWERED)

        m.set_input(m.BTN_START, 10)
        m.run_frames(40)
        m.pause()
        state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Start on the volume row resumes GAME_STATE_PLAYING ({state})',
                state == GAME_STATE_PLAYING)
    # `with` exit here calls McpSession's own clean "shutdown" RPC + process
    # wait -- the same path a real power-off takes, which is what actually
    # flushes BatteryManager's .srm (see this file's own header).

    # --- Ground truth: the .srm file Mesen actually wrote, not an engine
    # self-report (same discipline as phase7's TAD-silence bug). ---
    r.check(f'.srm file exists at {SRM_PATH}', os.path.isfile(SRM_PATH))
    with open(SRM_PATH, 'rb') as f:
        srm = f.read(4)
    r.check(f'.srm offset 0 = magic byte 0 ({srm[0]:#04x})', srm[0] == OPTIONS_MAGIC0_VALUE)
    r.check(f'.srm offset 1 = magic byte 1 ({srm[1]:#04x})', srm[1] == OPTIONS_MAGIC1_VALUE)
    r.check(f'.srm offset 2 = format version ({srm[2]})', srm[2] == OPTIONS_VERSION_CURRENT)
    r.check(f'.srm offset 3 = the lowered volume, not the default ({srm[3]})',
            srm[3] == EXPECTED_LOWERED)

    # --- Session 2: a COMPLETELY SEPARATE Mesen process, same ROM.
    # m.reset_emulator() alone would NOT prove this (it never touches the
    # .srm) -- only a fresh process load does, since BaseCartridge reads
    # the .srm back in its own load path. ---
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        vol = read_block(m, Options_MusicVolume, 32)[0]
        r.check(f'fresh Mesen process restores the persisted volume, not the default ({vol})',
                vol == EXPECTED_LOWERED)

        enter_pause_and_select_volume(m, r, 'session 2')
        got_volume_row = decode_row(m, PAUSE_ROW_VOLUME)
        expect_prefix = f'> V {EXPECTED_LOWERED}'
        r.check(f'volume row visibly shows the persisted value, selected ({got_volume_row!r})',
                got_volume_row.startswith(expect_prefix))

    r.finish()


if __name__ == '__main__':
    main()
