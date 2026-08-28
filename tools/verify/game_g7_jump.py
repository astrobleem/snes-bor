#!/usr/bin/env python3
"""plan_game.md 7 (jump slice, first of jump/special/grab-throw): real
player jump with Q8.8 gravity integration, jumpattack/jumpattack2, and a
visual-only OAM Y offset while airborne.

Sourced from real OpenBOR (DCurrent/openbor, engine/openbor.c), not
invented -- see src/core/jump.pasm's header for the full citation list:
tryjump()/dojump()/toss() (jumpheight IS the initial velocity), check_
gravity() (position += velocity, velocity += gravity, land when position<=0
AND velocity<=0 -- a two-part condition), and LEO's real char file (TMNT
pak, data\\CHARS\\LEO\\LEO.TXT: `jumpheight 5`, real jump/jumpattack/
jumpattack2 anims) as the only roster member with real jump data. AI jump
was never built (out of scope this slice -- real BOR.C AI think loops don't
autonomously jump either, so this is not a missing feature, just an
unbuilt one).

Player only (roster slot 0, entity 0). LEO is not slot 0 by default, so
every check here force-loads LEO onto the player entity via CharSelect_
Index + Anim_LoadCharacter, the same mechanism game_g5_menus.py's real
Select-cycle already exercises -- not a synthetic memory write of animation
data, a real character-select load.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_SELECTED_JUMP = pasm_constant('CHAR_SELECTED_JUMP')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')

Player_JumpZPos = pasm_constant('Player_JumpZPos')
Player_JumpZVel = pasm_constant('Player_JumpZVel')
Player_JumpFCount = pasm_constant('Player_JumpFCount')
Player_JumpAttackFCount = pasm_constant('Player_JumpAttackFCount')
Player_JumpAttack2FCount = pasm_constant('Player_JumpAttack2FCount')
Player_JumpAnimMode = pasm_constant('Player_JumpAnimMode')
JUMP_INITIAL_VEL = pasm_constant('JUMP_INITIAL_VEL')
JUMP_GRAVITY_RAW = pasm_constant('JUMP_GRAVITY')
JUMP_GRAVITY = JUMP_GRAVITY_RAW - 0x10000 if JUMP_GRAVITY_RAW & 0x8000 else JUMP_GRAVITY_RAW
Player_JumpBaseLo = pasm_constant('Player_JumpBaseLo')
Player_JumpAttackBaseLo = pasm_constant('Player_JumpAttackBaseLo')
CharSelect_Index = pasm_constant('CharSelect_Index')
CHAR_POS_X = pasm_constant('CHAR_POS_X')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Screen_PosX = 0x7E1601  # same literal every other depth-sort-safe gate uses


def read_byte(m, addr):
    return read_block(m, addr, 32)[0]


def read_i16(m, addr):
    b = read_block(m, addr, 32)
    v = b[0] | (b[1] << 8)
    return v - 0x10000 if v & 0x8000 else v


def simulate_ticks(n):
    """Reproduce Jump_PlayerTick__airborne's own integration exactly
    (position += velocity, velocity += gravity, every tick -- real BOR.C
    check_gravity()) starting from the real arm values, for n ticks."""
    zpos, zvel = 0, JUMP_INITIAL_VEL
    for _ in range(n):
        zpos = (zpos + zvel) & 0xFFFF
        if zpos & 0x8000:
            zpos -= 0x10000
        zvel = (zvel + JUMP_GRAVITY) & 0xFFFF
        if zvel & 0x8000:
            zvel -= 0x10000
    return zpos, zvel


def player_oam_y(m):
    """Actor depth-sort slice (plan_game.md 7): OamSetSprite_Y is a shared
    per-frame WRAM staging cell now written for all 4 entities in depth-
    sorted order each frame (Character_RenderPass) -- sampling it directly
    after a frame no longer reliably reflects the PLAYER's own value (same
    class of staleness bug already found/fixed for OamSetSprite_X in that
    slice's own gate, and for OamSetSprite_Hi in phase8.py). Read the
    player's real hardware OAM Y instead, identified by its real on-screen
    X, same technique phase11_damage.py/game_g8_props.py/game_g2_states.py
    already use."""
    posx = read_block(m, PlayerEntity + CHAR_POS_X, 32)
    world_x = posx[0] | (posx[1] << 8)
    cam = read_i16(m, Screen_PosX) & 0xFFFF
    expected_x = (world_x - cam) & 0xFF
    oam = read_block(m, 0, 32, mem_type='snesSpriteRam')
    for slot in range(4):
        if oam[slot * 4] == expected_x:
            return oam[slot * 4 + 1]
    raise AssertionError(f'player: no OAM sprite found at expected screen X={expected_x:#x} '
                          f'(real OAM X bytes present: {[oam[s * 4] for s in range(4)]})')


def player_state(m):
    zpos = read_i16(m, Player_JumpZPos)
    zvel = read_i16(m, Player_JumpZVel)
    selected = read_byte(m, PlayerEntity + CHAR_SELECTED)
    oam_y = player_oam_y(m)
    mode = read_byte(m, Player_JumpAnimMode)
    frame = read_byte(m, PlayerEntity + CHAR_FRAME_INDEX)
    return zpos, zvel, selected, oam_y, mode, frame


def neutralize_ai(m):
    for i in range(1, 4):
        m.write_u8(ENTITY_BASES[i] + CHAR_HP, 0)
    # Belt-and-suspenders: also clear any hit-stun already in flight against
    # the player -- Anim_Play__stunned_reset forces CHAR_SELECTED back to 0
    # unconditionally on the first stunned frame, which would look like a
    # broken jump landing to this gate but is really an unrelated AI hit
    # that was already committed before its attacker's HP hit 0 this frame.
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)


def press_select(m):
    # Select is edge-triggered (Input_trigger) -- a short press registers
    # one edge; same idiom phase12_roster.py's press_select() uses.
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(20)
    m.pause()


def load_leo_onto_player(m, leo_index, max_presses=20):
    """Real in-game character-select reselect (Select button cycling
    CharSelect_Index through Anim_LoadCharacter), the same live path
    phase12_roster.py/game_g5_menus.py already exercise -- not a synthetic
    write of animation data."""
    for _ in range(max_presses):
        idx = read_byte(m, CharSelect_Index)
        if idx == leo_index:
            return
        press_select(m)
    raise AssertionError(f'CharSelect_Index never reached {leo_index} after {max_presses} Select presses '
                          f'(stuck at {read_byte(m, CharSelect_Index)})')


def find_leo_slot():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src', 'main.pasm')
    # slot order is printed by build_rom.py at build time (roster: ... leo);
    # LEO was added as roster slot 12 -- confirm from the packed roster list
    # in main.pasm's own MSU directory comment / build log is fragile, so
    # instead just trust the documented, committed slot (see CLAUDE.md
    # memory phase15/leo commits: LEO added as roster slot 12).
    return 12


def main():
    r = Reporter('G7-JUMP', kind='GATE')
    leo_index = find_leo_slot()
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        load_leo_onto_player(m, leo_index)

        # Neutralize AI entities 1/2/3 -- same reasoning as game_g6_hud.py/
        # game_g7_invuln.py: real background AI combat is already underway by
        # frame 300, and a stray hit landing mid-flight would force
        # CHAR_SELECTED back to 0 via the unrelated hit-stun path
        # (Anim_Play__stunned_reset), which would look like an early/broken
        # landing to this gate but has nothing to do with the jump code.
        neutralize_ai(m)

        jump_fcount = read_byte(m, Player_JumpFCount)
        print(f'LEO (roster slot {leo_index}) Player_JumpFCount={jump_fcount}')
        r.check('LEO has real jump frame data loaded (Player_JumpFCount != 0)', jump_fcount != 0)

        # --- 1. Grounded, A press starts a real jump: CHAR_SELECTED becomes
        # JUMP and Player_JumpZVel is set to the real JUMP_INITIAL_VEL
        # (LEO's real jumpheight=5, Q8.8 -> $0500), not an arbitrary value. ---
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u16(Player_JumpZPos, 0)
        m.write_u16(Player_JumpZVel, 0)
        m.set_input(m.BTN_A, 1)
        m.pause()
        zpos1, zvel1, sel1, oamy1, mode1, frame1 = player_state(m)
        print(f'after A press: zpos={zpos1} zvel={zvel1} selected={sel1} mode={mode1}')
        r.check('A press while grounded enters CHAR_SELECTED_JUMP', sel1 == CHAR_SELECTED_JUMP)
        # set_input's own wall-clock sleep (mesen_set_input_wall_clock project
        # memory) advances a few real frames before this first read lands, so
        # the exact arm frame is unobservable -- instead simulate the real
        # integration (position += velocity, velocity += gravity every tick,
        # from the real JUMP_INITIAL_VEL/JUMP_GRAVITY constants) for a small
        # number of elapsed ticks and require an EXACT match at some small n.
        # This proves the arm value really was JUMP_INITIAL_VEL and gravity
        # really is JUMP_GRAVITY, without needing frame-1 precision.
        matched_n = None
        for n in range(0, 8):
            if simulate_ticks(n) == (zpos1, zvel1):
                matched_n = n
                break
        print(f'matched simulated tick count: {matched_n}')
        r.check('observed (zpos, zvel) after A press exactly matches the real-sourced '
                'integration from JUMP_INITIAL_VEL/JUMP_GRAVITY at some small elapsed tick count',
                matched_n is not None)

        # --- 2. Real gravity integration over several frames: height rises
        # then falls (not static, not monotonic in one direction only). ---
        heights = [zpos1]
        for _ in range(150):
            neutralize_ai(m)
            m.run_frames(1)
            m.pause()
            zpos, zvel, sel, oamy, mode, frame = player_state(m)
            heights.append(zpos)
            if sel != CHAR_SELECTED_JUMP:
                break
        peak = max(heights)
        peak_idx = heights.index(peak)
        print(f'height samples (first 12): {heights[:12]} ... peak={peak} at sample {peak_idx}, total samples={len(heights)}')
        r.check('height rose above 0 at some point (real upward velocity applied)', peak > 0)
        r.check('height came back down after the peak (gravity integrated, not static)',
                any(h < peak for h in heights[peak_idx:]))

        # --- 3. Lands within a bounded frame count, both Z cells back to 0,
        # CHAR_SELECTED back to idle/walk (not stuck airborne). ---
        landed = False
        for _ in range(120):
            zpos, zvel, sel, oamy, mode, frame = player_state(m)
            if sel != CHAR_SELECTED_JUMP:
                landed = True
                break
            neutralize_ai(m)
            m.run_frames(1)
            m.pause()
        zpos_f, zvel_f, sel_f, oamy_f, mode_f, frame_f = player_state(m)
        print(f'landed={landed} final: zpos={zpos_f} zvel={zvel_f} selected={sel_f}')
        r.check('lands within a bounded frame count', landed)
        r.check('Player_JumpZPos resets to 0 on landing', zpos_f == 0)
        r.check('Player_JumpZVel resets to 0 on landing', zvel_f == 0)
        r.check('CHAR_SELECTED returns to idle(0) or walk(1) on landing', sel_f in (0, 1))

        # --- 4. OAM Y offset: nonzero (sprite drawn higher) at/near the
        # peak, zero once landed -- proves the visual offset is real and
        # airborne-gated, not a permanent shift. ---
        neutralize_ai(m)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u16(Player_JumpZPos, 0)
        m.write_u16(Player_JumpZVel, 0)
        m.run_frames(1)
        m.pause()
        base_y = player_oam_y(m)
        m.set_input(m.BTN_A, 1)
        m.pause()
        oam_ys = []
        for _ in range(30):
            neutralize_ai(m)
            m.run_frames(1)
            m.pause()
            _, _, sel, oamy, _, _ = player_state(m)
            oam_ys.append((sel, oamy))
        airborne_ys = [oamy for sel, oamy in oam_ys if sel == CHAR_SELECTED_JUMP]
        print(f'base_y={base_y}, airborne oam_y samples={airborne_ys[:8]}')
        r.check('OAM Y while airborne differs from the grounded base Y (visual offset applied)',
                any(oamy != base_y for oamy in airborne_ys) if airborne_ys else False)

        for _ in range(120):
            _, _, sel, _, _, _ = player_state(m)
            if sel != CHAR_SELECTED_JUMP:
                break
            neutralize_ai(m)
            m.run_frames(1)
            m.pause()
        # One extra settle frame -- m.run_frames() is a wall-clock lower
        # bound, not an exact frame count (memory mesen_set_input_wall_
        # clock; same class of race the depth-sort gate's own crossover
        # test had to work around), and a bare post-break read here was
        # observed reading OAM Y a couple pixels off the true grounded
        # base immediately after the landing edge.
        neutralize_ai(m)
        m.run_frames(2)
        m.pause()
        oam_y_landed = player_oam_y(m)
        sel_landed = read_byte(m, PlayerEntity + CHAR_SELECTED)
        print(f'after landing: selected={sel_landed} oam_y={oam_y_landed} (base_y={base_y})')
        r.check('OAM Y offset is gone once landed (matches grounded base Y again)',
                sel_landed != CHAR_SELECTED_JUMP and oam_y_landed == base_y)

        # --- 5. jumpattack (Y) plays a genuinely different frame/base
        # sequence than the ground attack -- Player_JumpAnimMode becomes 1
        # and streams from Player_JumpAttackBaseLo, not Player_JumpBaseLo. ---
        jump_base = read_byte(m, Player_JumpBaseLo) | (read_byte(m, Player_JumpBaseLo + 1) << 8)
        jumpattack_base = read_byte(m, Player_JumpAttackBaseLo) | (read_byte(m, Player_JumpAttackBaseLo + 1) << 8)
        print(f'Player_JumpBaseLo={jump_base:#x} Player_JumpAttackBaseLo={jumpattack_base:#x}')
        r.check('jump and jumpattack stream from genuinely different MSU base offsets',
                jump_base != jumpattack_base)

        neutralize_ai(m)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u16(Player_JumpZPos, 0)
        m.write_u16(Player_JumpZVel, 0)
        m.set_input(m.BTN_A, 1)
        m.pause()
        neutralize_ai(m)
        m.set_input(m.BTN_Y, 1)
        m.pause()
        mode_after_y = read_byte(m, Player_JumpAnimMode)
        sel_after_y = read_byte(m, PlayerEntity + CHAR_SELECTED)
        print(f'after A then Y mid-air: selected={sel_after_y} mode={mode_after_y}')
        r.check('Y trigger mid-air (mode 0) enters jumpattack (Player_JumpAnimMode=1)', mode_after_y == 1)
        r.check('still CHAR_SELECTED_JUMP during jumpattack (not a separate state)', sel_after_y == CHAR_SELECTED_JUMP)

    r.finish()


if __name__ == '__main__':
    main()
