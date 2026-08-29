#!/usr/bin/env python3
"""notjustfreespecial.txt G5 finding: real char-select portrait (ANI_SELECT/
`waiting`).

Background: the ledger used to say `waiting`/ANI_SELECT belonged to G5
"already implemented there as cosmetic" -- false. game_g5_menus.py only ever
proved text rows, character names, index changes and CGRAM palette reloads;
it never rendered a single sprite during CHARSELECT (confirmed by direct
source inspection: Game_State_Play only dispatches Core_Oop_Play/Character_
RenderPass/Core_Oam_Play from the GAME_STATE_PLAYING branch, never from
Game_State_Play__charselect -- core/charselect.pasm had no OAM-emitting code
at all before this slice).

Ground truth (a direct scan of every roster character's raw .TXT across both
shipped paks, not an assumption): ONLY LEO has real `waiting` data --
DATA\\CHARS\\LEO\\LEO.TXT: `anim waiting`, 1 frame (`select.gif`), `loop 1`,
`delay 130`, `offset 1 1`. Every other roster character's CHAR_WAITING_FCOUNT
is 0 by real (converted) content, not a simplification -- "advance the
portrait frame" is content-inapplicable for all 13 roster members (LEO's own
single frame never advances; nobody else has a `waiting` anim to advance at
all).

This gate proves, against real hardware-visible state (never a screenshot --
see memory: mesen_screenshot_stale_hud_layer):
1. CHAR_WAITING_FCOUNT/BASE ground truth for LEO vs. every other roster
   member (0 = correctly inapplicable).
2. Selecting LEO makes a real OAM sprite (slot 0) visible with the real
   converted portrait tile data in VRAM (byte-exact vs. pack_msu_roster.py's
   own bake_anim_bytes(out/leo_waiting) -- the same converter-output ground
   truth phase6.py/phase9.py already establish as authoritative for this
   project, not the engine's own claim).
3. Reselecting to a character with no real waiting data (RALF) hides the
   sprite again (OAM Y=$F0, this project's established "clean slot"
   sentinel).
4. Reselecting back to LEO makes it visible again with the SAME real tile
   data (round-trip, not a one-shot fluke).
5. Entering real gameplay (Start) tears the portrait down cleanly: no OAM
   slot anywhere in the low table (not just slot 0 -- depth-sort can move
   the player to a different OAM slot once PLAYING starts, see
   game_g7_depth_sort.py) carries the portrait's own signature (X=16,
   Y=24) or its VRAM tile content, i.e. the portrait sprite is genuinely
   gone, not merely relocated to another slot.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter, roster  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bor_converter'))
import pack_msu_roster  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_WAITING_FCOUNT = pasm_constant('CHAR_WAITING_FCOUNT')
CHAR_TILE_COLUMN = pasm_constant('CHAR_TILE_COLUMN')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')

CharSelect_Index = 0x7E53B6
CharSelect_PortraitPending = 0x7E27AD
Game_State = 0x7E2750
PlayerEntity = 0x7E0A00

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROSTER = roster()

# Msu1_LoadFrame's own row-DMA layout (main.pasm's own header comment,
# "row 0: word $4000 (tileRow0,col0)*2" etc.): 6 rows of 128 bytes, byte
# addresses $8000/$8200/$8400/$8600/$8800/$8A00 for tile column 0 (the
# player's own CHAR_TILE_COLUMN, always 0 -- CLAUDE.md's "player is always
# slot 0"). NOT a contiguous 768-byte run in VRAM (hardware tile-index
# layout jumps by 16 slots/row, not 4) -- read each row separately.
VRAM_ROW_BYTES = [0x8000, 0x8200, 0x8400, 0x8600, 0x8800, 0x8A00]


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def select_to(m, name):
    """CHARSELECT's own WAIT step (core/charselect.pasm) polls Left/Right,
    NOT the Select button -- Select is a separate, PLAYING-state-only live
    reselect path (Anim_Play's own check_reselect) that never runs
    CharSelect_PortraitUpdate. Must drive the real Right-press path to
    exercise the actual screen this gate is testing."""
    idx = read_u8(m, CharSelect_Index)
    target = ROSTER.index(name)
    steps = (target - idx) % len(ROSTER)
    for _ in range(steps):
        m.set_input(m.BTN_RIGHT, 10)
        m.run_frames(40)
        m.pause()
    return read_u8(m, CharSelect_Index)


def settle_portrait(m, frames=30):
    """CharSelect_PortraitUpdate defers the actual MSU stream one frame past
    a reselect (see its own header -- avoids stacking Msu1_LoadFrame's 6
    DMA-queue slots on top of Anim_LoadCharacter's palette DMA in the same
    frame). Poll until CharSelect_PortraitPending clears (streamed) rather
    than a fixed sleep."""
    for _ in range(frames):
        m.run_frames(1)
        m.pause()
        if read_u8(m, CharSelect_PortraitPending) == 0:
            break
    m.run_frames(3)
    m.pause()


def read_oam_slot0(m):
    b = read_block(m, 0, 32, mem_type='snesSpriteRam')
    return {'x': b[0], 'y': b[1], 'tile': b[2], 'attr': b[3]}


def read_oam_all(m, count=8):
    """Low OAM table: 4 bytes/sprite (x, y, tile, attr). Read `count` real
    entities' worth (this project's max live sprite count) rather than just
    slot 0 -- depth-sort can reassign which OAM slot the player occupies
    once PLAYING starts (see game_g7_depth_sort.py), so a teardown check
    that only looks at slot 0 can pass vacuously if the portrait's stale
    frame merely migrated to a different slot."""
    b = read_block(m, 0, count * 4, mem_type='snesSpriteRam')
    return [{'x': b[i * 4], 'y': b[i * 4 + 1], 'tile': b[i * 4 + 2],
             'attr': b[i * 4 + 3]} for i in range(count)]


def read_portrait_vram(m):
    chunks = []
    for addr in VRAM_ROW_BYTES:
        chunks.append(bytes(read_block(m, addr, 128, mem_type='snesVideoRam')))
    return b''.join(chunks)


def main():
    r = Reporter('G5-PORTRAIT', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # --- 1. Ground truth: only LEO has real waiting data. ---
        with open(os.path.join(ROOT, 'out', 'leo_moveset.json'), 'r', encoding='utf-8') as f:
            leo_moveset = json.load(f)
        r.check("LEO's real converted moveset has a `waiting` role (ordinal not None)",
                leo_moveset['roles'].get('waiting') is not None)
        for other in ROSTER:
            if other == 'leo':
                continue
            path = os.path.join(ROOT, 'out', f'{other}_moveset.json')
            if not os.path.isfile(path):
                continue
            with open(path, 'r', encoding='utf-8') as f:
                other_moveset = json.load(f)
            if other_moveset['roles'].get('waiting') is not None:
                r.check(f'{other}: no real `waiting` role (content-inapplicable)', False)

        expected_leo_waiting_bytes = pack_msu_roster.bake_anim_bytes(
            os.path.join(ROOT, 'out', 'leo_waiting'))
        r.check('real converted leo_waiting frame data is exactly 768 bytes '
                '(1 frame)', len(expected_leo_waiting_bytes) == 768)

        # --- Reach CHARSELECT the real way (game_g5_menus.py's own
        # established convention): force GAME_STATE_TITLE (Game_State boots
        # PLAYING by design -- plan_game.md G5's own declined-flip note --
        # so a forced write is how every G5 gate reaches TITLE at all),
        # settle the title drip, then a real Start press transitions
        # TITLE -> CHARSELECT, exactly like a real boot would. ---
        m.write_u16(Game_State, 1)  # GAME_STATE_TITLE
        m.run_frames(60)
        m.pause()
        m.set_input(m.BTN_START, 10)
        m.run_frames(40)
        m.pause()
        r.check('Start at title transitions to GAME_STATE_CHARSELECT',
                read_u8(m, Game_State) == 2)

        # --- 2. Select LEO: real OAM visible, real tile data in VRAM. ---
        idx = select_to(m, 'leo')
        r.check('roster selected to LEO', idx == ROSTER.index('leo'))
        waiting_fc = read_u8(m, PlayerEntity + CHAR_WAITING_FCOUNT)
        r.check('LEO CHAR_WAITING_FCOUNT matches real converted data (>0)',
                waiting_fc > 0)
        settle_portrait(m)

        oam = read_oam_slot0(m)
        print(f'LEO selected: OAM slot0 = {oam}')
        r.check('LEO portrait: OAM slot0 Y != $F0 (visible)', oam['y'] != 0xF0)

        vram = read_portrait_vram(m)
        r.check('LEO portrait: VRAM tile data byte-exact vs. real converted '
                'leo_waiting frame (pack_msu_roster.bake_anim_bytes)',
                vram == expected_leo_waiting_bytes)

        # --- 3. Reselect to RALF (no real waiting data): hidden again. ---
        idx = select_to(m, 'ralf')
        r.check('roster selected to RALF', idx == ROSTER.index('ralf'))
        ralf_waiting_fc = read_u8(m, PlayerEntity + CHAR_WAITING_FCOUNT)
        r.check('RALF CHAR_WAITING_FCOUNT == 0 (real data: no waiting anim)',
                ralf_waiting_fc == 0)
        settle_portrait(m)
        oam = read_oam_slot0(m)
        print(f'RALF selected: OAM slot0 = {oam}')
        r.check('RALF (no portrait data): OAM slot0 Y == $F0 (hidden, not a '
                'stale LEO frame)', oam['y'] == 0xF0)

        # --- 4. Reselect back to LEO: visible again, same real data
        #     (round-trip, not a one-shot fluke). ---
        idx = select_to(m, 'leo')
        r.check('roster reselected to LEO', idx == ROSTER.index('leo'))
        settle_portrait(m)
        oam = read_oam_slot0(m)
        vram = read_portrait_vram(m)
        r.check('LEO portrait round-trip: OAM slot0 Y != $F0 (visible again)',
                oam['y'] != 0xF0)
        r.check('LEO portrait round-trip: VRAM tile data still byte-exact',
                vram == expected_leo_waiting_bytes)

        # --- 5. Start -> real gameplay: portrait torn down cleanly, same
        #     OAM slot now holds the real player sprite. ---
        m.set_input(m.BTN_START, 10)
        m.run_frames(40)
        m.pause()
        # CHARSELECT's own multi-step clear/teardown sequence (draw/clear
        # header/name/instr rows) takes several real frames -- settle it.
        for _ in range(60):
            m.run_frames(1)
            m.pause()
            if read_u8(m, PlayerEntity + 0) != 0xFF:  # any real per-frame tick
                pass
        game_state = read_u8(m, Game_State)
        r.check('GAME_STATE_PLAYING reached after Start', game_state == 0)

        playing_oam_all = read_oam_all(m)
        playing_vram = read_portrait_vram(m)
        print(f'PLAYING reached: OAM low table = {playing_oam_all}, '
              f'CHAR_POS_Y={read_u8(m, PlayerEntity + CHAR_POS_Y)}')
        # The strong teardown claim: no OAM slot ANYWHERE carries the
        # portrait's own fixed signature (X=16, Y=24 -- set verbatim in
        # CharSelect_PortraitUpdate's __visible branch). Checking only
        # slot 0 would pass vacuously if depth-sort simply moved the stale
        # frame to a different slot instead of it being torn down.
        r.check('after Start: no OAM slot carries the portrait\'s fixed '
                'signature (X=16, Y=24) -- real teardown, not relocation',
                not any(s['x'] == 16 and s['y'] == 24 for s in playing_oam_all))
        r.check('after Start: VRAM tile data at the portrait\'s slot no '
                'longer matches the static waiting frame -- real gameplay '
                'animation streaming has overwritten it',
                playing_vram != expected_leo_waiting_bytes)

    r.finish()


if __name__ == '__main__':
    main()
