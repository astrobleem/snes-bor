#!/usr/bin/env python3
"""Focused regression for authored frame-SFX duplicate scope.

The dispatcher may be reached more than once while one NMI is current, but a
record key must only suppress that one NMI.  The source-bound model covers the
same-frame branch; the gameplay controls prove that the same authored DASH and
PIZZA1 records re-emit through their real production triggers on later frames.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "verify"))

from _harness import open_session, pasm_constant, poll_until, read_block
import audio_semantic_diesound as semantic
import game_g8_pickup as pickup
from game_g8_get_leo import load_char_onto_player
from game_g7_jump import CHAR_SELECTED, ENTITY_BASES

FRAME_REQUESTS = pasm_constant("AudioSemantic_FrameSoundRequestCount")
SEMANTIC_REQUESTS = pasm_constant("AudioSemantic_RequestCount")
CURRENT_ID = pasm_constant("AudioSemantic_CurrentId")
STREAM_SOURCE = pasm_constant("AudioStream_SourceId")

LEO = 12
AUDIO_SEMANTIC_DASH = 0x12
AUDIO_SEMANTIC_PIZZA1 = 0x18
AUDIO_STREAM_PIZZA1 = 12


def u8(m, address: int) -> int:
    return read_block(m, address, 32)[0]


def u16(m, address: int) -> int:
    data = read_block(m, address, 32)
    return data[0] | (data[1] << 8)


def run_frames(m, count: int) -> None:
    for _ in range(count):
        m.run_frames(1)
        m.pause()


def assert_same_frame_model() -> None:
    source = (ROOT / "src/core/vm/vm_native_engine.pasm").read_text(encoding="utf-8")
    required = re.compile(
        r"sta\.l AudioSemantic_FrameSoundLastFrame\s+"
        r"; LastKey is scoped to LastFrame\.  A matching record must be eligible\s+"
        r"; again as soon as a later NMI begins\.\s+"
        r"sep #\$20\s+\.a8\s+lda #\$FF\s+"
        r"sta\.l AudioSemantic_FrameSoundLastKey\s+"
        r"rep #\$20\s+\.a16\s+"
        r"Audio_FrameSoundDispatch__same_frame:",
        re.MULTILINE,
    )
    if not required.search(source):
        raise AssertionError("LastKey is not invalidated on the new-NMI-frame path")

    last_frame, last_key = 0x1234, 0xFF

    def dispatch(frame: int, key: int) -> bool:
        nonlocal last_frame, last_key
        if frame != last_frame:
            last_frame = frame
            last_key = 0xFF
        if key == last_key:
            return False
        last_key = key
        return True

    if (not dispatch(0x1235, 7) or dispatch(0x1235, 7)
            or not dispatch(0x1236, 7)):
        raise AssertionError("same-frame suppression/later-frame re-arm model failed")
    print("same-NMI duplicate suppression and later-NMI re-arm: PASS")


def prepare_leo(m) -> None:
    semantic.boot(m)
    load_char_onto_player(m, LEO)
    for base in semantic.ENTITY_BASES[1:]:
        semantic.w8(m, base + semantic.CHAR_HP, 0)
    run_frames(m, 30)


def start_dash(m) -> None:
    # This is the normal grounded slide trigger.  The selected-state write is
    # fixture re-arm only; the DOWN+A production input accepts the action.
    m.set_input(m.BTN_DOWN, 1)
    run_frames(m, 1)
    m.write_u8(ENTITY_BASES[0] + CHAR_SELECTED, 0)
    m.set_input(m.BTN_DOWN | m.BTN_A, 1)
    run_frames(m, 1)
    m.set_input(0, 1)


def wait_slide_legal(m) -> None:
    if not poll_until(m, lambda _m: u8(m, ENTITY_BASES[0] + CHAR_SELECTED) == 0, 180):
        raise AssertionError("LEO slide did not return to a legal grounded state")


def prepare_pizza_pickup(m) -> None:
    pickup.reset_combat_state(m)
    m.write_u8(pickup.Entity1 + pickup.CHAR_HP, 0)
    m.write_u8(pickup.Entity3 + pickup.CHAR_HP, 0)
    m.write_u8(pickup.Entity2 + pickup.CHAR_INPUT_DRIVEN, pickup.CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(pickup.Entity2 + pickup.CHAR_HP, pickup.CHAR_HP_PER_HIT)
    m.write_u8(pickup.Entity2 + pickup.CHAR_PICKUP_TYPE, pickup.PICKUP_TYPE_APPLE)
    m.write_u8(pickup.Entity2_ItemRosterIdx, 0)
    pickup.overlap_entity2_with_player(m)


def collect_pizza(m) -> None:
    m.set_input(0, 1)
    if not poll_until(m, lambda _m: u8(m, pickup.Entity2 + pickup.CHAR_HP) == 0, 30):
        raise AssertionError("real LEO pickup did not collect")
    run_frames(m, 2)


def main() -> int:
    assert_same_frame_model()
    with open_session(__file__) as m:
        prepare_leo(m)
        semantic.clear_observation(m)
        dash_before = u16(m, FRAME_REQUESTS)
        start_dash(m)
        if not poll_until(m, lambda _m: u16(m, FRAME_REQUESTS) == dash_before + 1, 60):
            raise AssertionError("first real LEO DASH did not emit its authored frame sound")
        wait_slide_legal(m)
        start_dash(m)
        if not poll_until(m, lambda _m: u16(m, FRAME_REQUESTS) == dash_before + 2, 60):
            raise AssertionError("second real LEO DASH was suppressed across NMI frames")
        if u8(m, CURRENT_ID) != AUDIO_SEMANTIC_DASH:
            raise AssertionError("second DASH did not retain the DASH semantic identity")
        print("real repeated LEO DASH: two authored frame-sound requests: PASS")

        # Reuse the now-idle, already-neutralized LEO session. The two
        # PIZZA pickups must be in one production session, and a second boot
        # only adds wall-clock cost without changing their dispatch context.
        semantic.clear_observation(m)
        pizza_before = u16(m, FRAME_REQUESTS)
        semantic_before = u16(m, SEMANTIC_REQUESTS)
        prepare_pizza_pickup(m)
        collect_pizza(m)
        if not poll_until(m, lambda _m: u16(m, FRAME_REQUESTS) == pizza_before + 1, 60):
            raise AssertionError("first real PIZZA1 pickup did not emit its authored frame sound")
        first_source = u8(m, STREAM_SOURCE)
        run_frames(m, 90)
        prepare_pizza_pickup(m)
        collect_pizza(m)
        if not poll_until(m, lambda _m: u16(m, FRAME_REQUESTS) == pizza_before + 2, 60):
            raise AssertionError("second real PIZZA1 pickup was suppressed across NMI frames")
        second_source = u8(m, STREAM_SOURCE)
        if u16(m, SEMANTIC_REQUESTS) != semantic_before + 4:
            raise AssertionError("two real GET/PIZZA1 pickups did not emit both authored PIZZA1 semantics")
        if (u8(m, CURRENT_ID) != AUDIO_SEMANTIC_PIZZA1
                or first_source != AUDIO_STREAM_PIZZA1
                or second_source != AUDIO_STREAM_PIZZA1):
            raise AssertionError("second PIZZA1 did not retain source-12 semantic identity")
        print("real repeated PIZZA1: two authored source-12 dispatches: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
