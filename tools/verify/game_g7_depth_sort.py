#!/usr/bin/env python3
"""plan_game.md 7 (actor depth-sort slice, sixth slice, following jump/
jumpattack/jumpattack2): real BOR-style ground-depth render order over the
4 fixed entity slots.

Before this slice, OAM entries for the 4 fixed entities were emitted in
fixed dispatch order (player always slot 0, so always the lowest OAM index,
so always drawn in front of every AI actor regardless of actual on-screen
depth) -- core/jump.pasm's own header flagged this as a real gap ("no
depth-sort axis was built... no dynamic OAM draw-order/priority sort for
ANYTHING today"). This slice adds core/depth_sort.pasm's Depth_Sort_
ComputeOrder (ground-Y selection sort) + main.pasm's Character_RenderFrame/
Character_RenderPass split (movement vs. OAM emission, the latter now run
once per frame in depth-sorted order instead of inline per-entity).

Every check below inspects REAL hardware OAM (snesSpriteRam), not the new
Depth_RenderOrder WRAM array -- per this slice's own completion bar, the
gate must independently prove final OAM state matches expected depth order,
not just trust the internal sort result. Entities are identified in OAM by
their real on-screen X (computed from world CHAR_POS_X minus the live
Screen_PosX, matching Character_RenderFrame's own hi-bit X-high computation)
rather than by OAM slot number, since slot number is exactly the thing under
test.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_SELECTED_JUMP = pasm_constant('CHAR_SELECTED_JUMP')

Player_JumpZPos = pasm_constant('Player_JumpZPos')
Player_JumpFCount = pasm_constant('Player_JumpFCount')
CharSelect_Index = pasm_constant('CharSelect_Index')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Screen_PosX = 0x7E1601  # same literal phase8.py already uses (Screen_PosX_Lo offset)

# Distinct, well-separated world positions -- picked so post-camera screen X
# stays unique and unambiguous mod 256 (camera starts near world X=0 and
# nothing here ever presses dpad, so Screen_PosX stays put at whatever the
# boot-time camera settled on).
TEST_X = [40, 90, 140, 190]
# Distinct ground Y, deliberately NOT in entity-index order (entity 0 is
# neither frontmost nor backmost) -- this is the whole point: the OLD code
# would have drawn entity 0 in front regardless of this ordering.
TEST_Y = [70, 40, 90, 55]  # entity 0=70(2nd), 1=40(back), 2=90(front), 3=55(3rd)
EXPECTED_FRONT_TO_BACK = [2, 0, 3, 1]  # entity ids, descending Y: 90,70,55,40


def read_byte(m, addr):
    return read_block(m, addr, 32)[0]


def read_i16(m, addr):
    b = read_block(m, addr, 32)
    v = b[0] | (b[1] << 8)
    return v - 0x10000 if v & 0x8000 else v


def freeze_ai(m):
    """Stop entities 1-3 from moving/attacking without killing them (a dead
    AI's OAM Y is overridden to the $F0 hide sentinel, which would make it
    invisible in OAM and defeat this gate's whole premise -- see Character_
    RenderFrame's dead-hide block). CHAR_INPUT_DRIVEN=0 (static/idle) stops
    Character_PlayFrame's mode-2 (AI) movement/attack dispatch. CHAR_HP is
    also forced nonzero every time this is called -- AI entities boot with
    HP=0 (unspawned, see phase13_spawn_table project memory) until core/
    spawn.pasm's per-frame Spawn_Play trips a wave trigger, so a frame
    sampled before that would otherwise still hit the dead-hide branch
    (CHAR_INPUT_DRIVEN>=2 && HP==0) via whatever CHAR_INPUT_DRIVEN Spawn_
    Play itself reasserts, independent of this test's own write above."""
    for i in range(1, 4):
        m.write_u8(ENTITY_BASES[i] + CHAR_INPUT_DRIVEN, 0)
        m.write_u8(ENTITY_BASES[i] + CHAR_HIT_STUN, 0)
        m.write_u8(ENTITY_BASES[i] + CHAR_HP, CHAR_HP_MAX)
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)


def set_positions(m, xs, ys):
    for base, x, y in zip(ENTITY_BASES, xs, ys):
        m.write_u16(base + CHAR_POS_X, x)
        m.write_u8(base + CHAR_POS_Y, y)


def read_oam_by_entity_x(m, screen_x_by_entity):
    """Real hardware OAM (snesSpriteRam), first 4 low-table entries (4 bytes
    each: X, Y, tile, attr) -- same read shape phase5.py's own hardware-OAM
    check already uses. Returns {entity_id: (oam_slot, oam_y)}, matching
    each sprite to an entity purely by its expected on-screen X (mod 256,
    matching hardware's own 8-bit X field) -- independent of Depth_
    RenderOrder or any other internal state."""
    oam = read_block(m, 0, 128, mem_type='snesSpriteRam')
    slot_by_x = {}
    for slot in range(4):
        off = slot * 4
        ox, oy = oam[off], oam[off + 1]
        slot_by_x[ox] = (slot, oy)
    result = {}
    for entity_id, sx in screen_x_by_entity.items():
        key = sx & 0xFF
        assert key in slot_by_x, (
            f'entity {entity_id}: no OAM sprite found at expected screen X={key:#x} '
            f'(real OAM X bytes present: {sorted(slot_by_x.keys())})')
        result[entity_id] = slot_by_x[key]
    return result


def expected_screen_x(m):
    cam = read_i16(m, Screen_PosX) & 0xFFFF
    return {i: (TEST_X[i] - cam) & 0xFFFF for i in range(4)}


def find_leo_slot():
    # See game_g7_jump.py's identical helper/comment: LEO (roster slot 12,
    # TMNT pak) is the only roster member with real jump/jumpattack/
    # jumpattack2 frame data, committed as such (phase15/leo memory).
    return 12


def press_select(m):
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(20)
    m.pause()


def load_leo_onto_player(m, leo_index, max_presses=20):
    for _ in range(max_presses):
        idx = read_byte(m, CharSelect_Index)
        if idx == leo_index:
            return
        press_select(m)
    raise AssertionError(f'CharSelect_Index never reached {leo_index} after {max_presses} Select presses')


def main():
    r = Reporter('G7-DEPTH-SORT', kind='GATE')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(150)
        m.pause()

        freeze_ai(m)
        set_positions(m, TEST_X, TEST_Y)
        # Let Character_RenderPass run at least once against the new
        # positions before sampling -- one real frame is enough (it runs
        # unconditionally every Game_State_Play call in GAME_STATE_PLAYING).
        m.run_frames(2)
        m.pause()

        # --- ground truth: confirm what we actually wrote landed (CHAR_
        # POS_Y is the real depth key -- Character_PlayFrame's movement
        # pass, not something this gate invents). ---
        ground_y = [read_byte(m, b + CHAR_POS_Y) for b in ENTITY_BASES]
        print(f'CHAR_POS_Y per entity: {ground_y}')
        r.check('injected ground Y values held (not overwritten by AI/player movement)',
                ground_y == TEST_Y)

        # ====================================================================
        # 1. Static depth ordering: real OAM slot order must match TEST_Y's
        # descending order, independent of entity index / old fixed dispatch
        # order (entity 0 is deliberately mid-pack here, not front or back).
        # ====================================================================
        exp_x = expected_screen_x(m)
        by_entity = read_oam_by_entity_x(m, exp_x)
        oam_order = sorted(by_entity.items(), key=lambda kv: kv[1][0])  # sort by OAM slot
        actual_front_to_back = [entity_id for entity_id, _ in oam_order]
        print(f'expected screen X: {exp_x}')
        print(f'OAM (slot, y) by entity: {by_entity}')
        print(f'actual front-to-back entity order (by OAM slot): {actual_front_to_back}')
        print(f'expected front-to-back entity order (by ground Y): {EXPECTED_FRONT_TO_BACK}')
        r.check('real OAM slot order matches expected ground-depth order (front=lowest OAM index)',
                actual_front_to_back == EXPECTED_FRONT_TO_BACK)

        for entity_id, (slot, oam_y) in by_entity.items():
            r.check(f'entity {entity_id} real OAM Y ({oam_y}) matches its ground CHAR_POS_Y ({TEST_Y[entity_id]}) while grounded',
                    oam_y == TEST_Y[entity_id])

        baseline_by_entity = by_entity

        # ====================================================================
        # 2/3/4. Jump: altitude changes visual OAM Y but must NOT change the
        # depth-sort rank, and landing must restore both Y and rank exactly.
        # Reuses game_g7_jump.py's real LEO character-select load (not a
        # synthetic write of jump data) so this exercises the real trigger
        # path, same as that gate.
        # ====================================================================
        leo_index = find_leo_slot()
        load_leo_onto_player(m, leo_index)
        m.write_u8(PlayerEntity + CHAR_INPUT_DRIVEN, 1)  # player mode, unchanged by char-select
        freeze_ai(m)
        set_positions(m, TEST_X, TEST_Y)
        m.run_frames(2)
        m.pause()

        jump_fcount = read_byte(m, Player_JumpFCount)
        r.check('LEO has real jump frame data loaded (Player_JumpFCount != 0)', jump_fcount != 0)

        m.set_input(m.BTN_A, 1)
        m.run_frames(1)
        for _ in range(40):
            m.pause()
            selected = read_byte(m, PlayerEntity + CHAR_SELECTED)
            if selected == CHAR_SELECTED_JUMP:
                break
            m.run_frames(1)
        else:
            raise AssertionError('player never entered CHAR_SELECTED_JUMP after A press')

        # Re-pin ground Y every sampled frame -- jump must never touch
        # CHAR_POS_Y (Character_RenderFrame's jsl Jump_ApplyOamYOffset only
        # perturbs the WRAM-staging OamSetSprite_Y cell), but re-pin AI too
        # in case anything else nudges them, keeping this test isolated to
        # exactly the jump-vs-depth-sort interaction under test.
        max_zpos = 0
        airborne_orders = []
        airborne_player_ys = []
        for _ in range(30):
            freeze_ai(m)
            set_positions(m, TEST_X, TEST_Y)
            m.run_frames(1)
            m.pause()
            zpos = read_i16(m, Player_JumpZPos)
            max_zpos = max(max_zpos, zpos)
            ground_y_now = [read_byte(m, b + CHAR_POS_Y) for b in ENTITY_BASES]
            if ground_y_now != TEST_Y:
                raise AssertionError(f'CHAR_POS_Y perturbed while airborne: {ground_y_now} != {TEST_Y}')
            if zpos > 0:
                exp_x_now = expected_screen_x(m)
                by_entity_now = read_oam_by_entity_x(m, exp_x_now)
                order_now = [e for e, _ in sorted(by_entity_now.items(), key=lambda kv: kv[1][0])]
                airborne_orders.append(order_now)
                airborne_player_ys.append(by_entity_now[0][1])

        print(f'max Player_JumpZPos observed: {max_zpos:#x}')
        r.check('player actually left the ground during this test (Player_JumpZPos > 0 observed)',
                max_zpos > 0)
        r.check('CHAR_POS_Y (ground/depth key) never changed for anyone while airborne (checked every sampled frame)',
                True)  # the loop above raises on any violation -- reaching here means it held
        r.check('depth-sort OAM order unchanged for every airborne frame sampled (jump altitude does not affect rank)',
                len(airborne_orders) > 0 and all(o == EXPECTED_FRONT_TO_BACK for o in airborne_orders))
        r.check("player's real OAM Y actually moved while airborne (visual jump offset still applies)",
                len(airborne_player_ys) > 0 and any(y != TEST_Y[0] for y in airborne_player_ys))

        # --- landing: wait for Player_JumpZPos to return to 0 (real
        # check_gravity() landing condition, see core/jump.pasm), then
        # re-verify both Y and order are back to the exact grounded baseline. ---
        for _ in range(120):
            freeze_ai(m)
            set_positions(m, TEST_X, TEST_Y)
            m.run_frames(1)
            m.pause()
            if read_i16(m, Player_JumpZPos) == 0 and read_byte(m, PlayerEntity + CHAR_SELECTED) != CHAR_SELECTED_JUMP:
                break
        else:
            raise AssertionError('player never landed (Player_JumpZPos never returned to 0) within 120 frames')

        m.run_frames(2)
        m.pause()
        exp_x_landed = expected_screen_x(m)
        by_entity_landed = read_oam_by_entity_x(m, exp_x_landed)
        order_landed = [e for e, _ in sorted(by_entity_landed.items(), key=lambda kv: kv[1][0])]
        print(f'post-landing OAM (slot, y) by entity: {by_entity_landed}')
        r.check('post-landing real OAM Y matches grounded baseline exactly for every entity',
                all(by_entity_landed[e][1] == baseline_by_entity[e][1] for e in range(4)))
        r.check('post-landing depth-sort order matches grounded baseline exactly (landing does not reorder)',
                order_landed == EXPECTED_FRONT_TO_BACK)

    r.finish()


if __name__ == '__main__':
    main()
