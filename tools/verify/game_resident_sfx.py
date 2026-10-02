#!/usr/bin/env python3
"""Run one real gameplay fixture for a resident global SFX.

The fixture setup follows the existing focused gameplay gates.  Only the
physical capture environment and the requested fixture vary; the SFX request
must still come from production gameplay code and the normal TAD queue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "verify"))

from _harness import open_session, pasm_constant, read_block  # noqa: E402
import audio_semantic_diesound as semantic  # noqa: E402
import game_g11_sfx as g11  # noqa: E402
import game_g5_pause as pause  # noqa: E402
import game_g8_get_leo as get  # noqa: E402
import game_g8_pickup as pickup  # noqa: E402

REQ_COUNT = pasm_constant("AudioSemantic_RequestCount")
CURRENT_ID = pasm_constant("AudioSemantic_CurrentId")
QUEUE_SFX = 0x7E0020
QUEUE_PAN = 0x7E0021

SPECS = {
    # LEO's real GET move emits global GET on the resident voice and its
    # authored PIZZA1 frame sound on stream voice 0.  PUNCH is suppressed
    # for GET_MOVE_VARIANT, so this two-event window is source-specific.
    "get": ("GET", 3, 0x09, 2, 0x18),
    # Assert at the pickup's immediate production event boundary.  Later
    # animation follow-through can emit PUNCH and must not be counted as a
    # duplicate pickup request.
    "money": ("MONEY", 4, 0x0A, 1, 0x0A),
    "punch": ("PUNCH", 5, 0x0B, 1, 0x0B),
    "oneup": ("1UP", 6, 0x0C, 1, 0x0C),
    "beep": ("BEEP", 7, 0x0D, 1, 0x0D),
    "beep2": ("BEEP2", 8, 0x0E, 1, 0x0E),
    "pause": ("PAUSE", 8, 0x0F, 1, 0x0F),
}


def u8(m, address):
    return read_block(m, address, 32)[0]


def run_frames(m, count):
    for _ in range(count):
        m.run_frames(1)
        m.pause()


def boot(m):
    # Keep the established gameplay fixture warmup.  Some fixtures depend on
    # the real stage spawns, so this is intentionally not semantic.boot(),
    # which neutralizes entities for the diesound tests.
    m.reset_emulator()
    run_frames(m, 300)


def run_get(m):
    get.load_char_onto_player(m, 12)  # LEO has the source-defined ANI_GET.
    get.neutralize_ai(m)
    get.arm_apple_item(m, player_hp=10)
    get.overlap_entity2_with_player(m)


def prepare_pickup(m, pickup_type):
    m.write_u8(pickup.Entity1 + pickup.CHAR_HP, 0)
    m.write_u8(pickup.Entity3 + pickup.CHAR_HP, 0)
    pickup.reset_combat_state(m)
    m.write_u8(pickup.Entity2 + pickup.CHAR_INPUT_DRIVEN, pickup.CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(pickup.Entity2 + pickup.CHAR_HP, pickup.CHAR_HP_PER_HIT)
    m.write_u8(pickup.Entity2 + pickup.CHAR_PICKUP_TYPE, pickup_type)
    m.write_u8(pickup.Entity2_ItemRosterIdx, 0)
    pickup.overlap_entity2_with_player(m)


def run_pickup_event(m):
    # Ground items are production touch-collects.  Advancing the overlap with
    # neutral input isolates the pickup edge from the later PUNCH animation.
    m.set_input(0, 1)
    pickup.poll_until(m, lambda: pickup.read_u8(m, pickup.Entity2 + pickup.CHAR_HP) == 0, max_frames=30)
    run_frames(m, 2)


def prepare_punch(m):
    # A real attack edge with the target outside hit range.  This exercises
    # Anim_Play__attack without also creating a HIT semantic event.
    for base in semantic.ENTITY_BASES[1:]:
        m.write_u8(base + semantic.CHAR_HP, 0)
    g11.write_u16(m, g11.Entity1 + g11.CHAR_POS_X, 60000)
    g11.write_u8(m, g11.PlayerEntity + g11.CHAR_HIT_STUN, 0)
    g11.write_u8(m, g11.PlayerEntity + g11.CHAR_HIT_APPLIED, 0)


def prepare_menu(m):
    # Keep the menu semantic window isolated from resumed AI attacks.  The
    # confirmation sound returns to PLAYING, so live enemies would otherwise
    # add unrelated PUNCH requests before the final observation.
    for base in semantic.ENTITY_BASES[1:]:
        m.write_u8(base + semantic.CHAR_HP, 0)


def run_punch_event(m):
    g11.exact_input_edge(m, m.BTN_Y, 10)
    g11.poll_frames(m, 60, lambda: None)


def run_pause_menu(m, kind):
    run_frames(m, 120)
    if kind == "pause":
        g11.exact_input_edge(m, m.BTN_START, 1)
        run_frames(m, 20)
        return
    # Enter pause first.  The capture is armed before this input, but the
    # selected effect is identified by the semantic ID at the end of the
    # requested transition, not by a mixed waveform.
    g11.exact_input_edge(m, m.BTN_START, 1)
    run_frames(m, 20)
    if kind == "beep":
        g11.exact_input_edge(m, m.BTN_DOWN, 1)
        run_frames(m, 20)
    else:
        # BEEP2: confirm the default CONTINUE selection.
        g11.exact_input_edge(m, m.BTN_START, 1)
        run_frames(m, 40)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", choices=sorted(SPECS))
    parser.add_argument("--voice", type=int, default=int(os.environ.get("MESEN_VOICE_CAPTURE_VOICE", "6"), 0))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not 0 <= args.voice <= 7:
        raise SystemExit("physical voice must be in 0..7")

    name, local_id, semantic_id, expected_event_delta, expected_current_id = SPECS[args.fixture]
    capture = Path(args.output).resolve()
    arm = Path(str(capture) + ".arm")
    stderr = Path(str(capture) + ".stderr.log")
    capture.parent.mkdir(parents=True, exist_ok=True)
    for stale in (capture, Path(str(capture) + ".json"), Path(str(capture) + ".report.json"), arm):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass
    env = {
        "MESEN_VOICE_CAPTURE_PATH": str(capture),
        "MESEN_VOICE_CAPTURE_VOICE": str(args.voice),
        "MESEN_VOICE_CAPTURE_ARM_FILE": str(arm),
    }

    current_id = None
    with open_session(__file__, env=env, stderr_log=str(stderr)) as m:
        boot(m)
        if args.fixture == "get":
            run_get(m)
        elif args.fixture == "money":
            prepare_pickup(m, pickup.PICKUP_TYPE_MONEY)
        elif args.fixture == "oneup":
            prepare_pickup(m, pickup.PICKUP_TYPE_ONEUP)
        elif args.fixture == "punch":
            prepare_punch(m)
        else:
            prepare_menu(m)
            run_frames(m, 120)
            if args.fixture in ("beep", "beep2"):
                # Entering pause is setup for the selector/confirmation
                # controls and may emit the separate PAUSE semantic event.
                g11.exact_input_edge(m, m.BTN_START, 1)
                run_frames(m, 20)
        semantic.clear_observation(m)
        before = u8(m, REQ_COUNT)
        arm.touch()
        if args.fixture == "get":
            run_frames(m, 12)
        elif args.fixture in ("money", "oneup"):
            run_pickup_event(m)
        elif args.fixture == "punch":
            run_punch_event(m)
        elif args.fixture == "pause":
                g11.exact_input_edge(m, m.BTN_START, 1)
                run_frames(m, 20)
        elif args.fixture == "beep":
            g11.exact_input_edge(m, m.BTN_DOWN, 1)
            run_frames(m, 20)
        else:
            g11.exact_input_edge(m, m.BTN_START, 1)
            run_frames(m, 40)
        event_after = u8(m, REQ_COUNT)
        event_current_id = u8(m, CURRENT_ID)
        # Keep the session alive past the source-specific one-shot so the
        # capture can prove natural ENDX rather than a truncated prefix.
        run_frames(m, 180)
        after = u8(m, REQ_COUNT)
        current_id = u8(m, CURRENT_ID)
        queue_after = u8(m, QUEUE_SFX)
        queue_pan_after = u8(m, QUEUE_PAN)
        semantic_rows = semantic.trace(m)
        state = m.get_audio_state()

    raw = capture.read_bytes() if capture.exists() else b""
    sidecar_path = Path(str(capture) + ".json")
    sidecar = {}
    if sidecar_path.exists():
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8").splitlines()[0])
    report = {
        **sidecar,
        "fixture": args.fixture,
        "expected_name": name,
        "semantic_id": semantic_id,
        "expected_event_delta": expected_event_delta,
        "event_request_delta": (event_after - before) & 0xFF,
        "event_current_id": event_current_id,
        "expected_event_current_id": expected_current_id,
        "semantic_request_delta": (after - before) & 0xFF,
        "semantic_current_id": current_id,
        "semantic_trace": semantic_rows,
        "queue_after": queue_after,
        "queue_pan_after": queue_pan_after,
        "local_id": local_id,
        "voice": args.voice,
        "rom_sha256": hashlib.sha256((ROOT / "distribution" / "bor.sfc").read_bytes()).hexdigest(),
        "capture_sha256": hashlib.sha256(raw).hexdigest(),
        "capture_bytes": len(raw),
        "audio_state": state,
        "capture_path": str(capture),
    }
    Path(str(capture) + ".report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if (
        report["event_request_delta"] == expected_event_delta
        and (expected_current_id is None or report["event_current_id"] == expected_current_id)
        and raw
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
