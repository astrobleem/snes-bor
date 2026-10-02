#!/usr/bin/env python3
"""Physical capture for the real grounded JUMP semantic edge."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (  # noqa: E402
    Reporter, open_session, pasm_constant, read_block, read_snes_bus_block,
)
from game_g7_jump import (  # noqa: E402
    CHAR_SELECTED,
    CHAR_SELECTED_JUMP,
    CHAR_THROW_ZPOS,
    CHAR_THROW_ZVEL,
    ENTITY_BASES,
    Player_JumpFCount,
    load_leo_onto_player,
    neutralize_ai,
)
import audio_semantic_diesound as semantic  # noqa: E402

JUMP_REQUEST_COUNT = pasm_constant("AudioSemantic_JumpRequestCount")
FRAME_SOUND_REQUEST_COUNT = pasm_constant("AudioSemantic_FrameSoundRequestCount")
CURRENT_SEMANTIC_ID = pasm_constant("AudioSemantic_CurrentId")
CHAR_ROSTER_INDEX = pasm_constant("CHAR_ROSTER_INDEX")
CHAR_ATTACK_VARIANT = pasm_constant("CHAR_ATTACK_VARIANT")
CHAR_FRAME_INDEX = pasm_constant("CHAR_FRAME_INDEX")
CHAR_TICK_COUNTER = pasm_constant("CHAR_TICK_COUNTER")
PLAYER_JUMP_ANIM_MODE = pasm_constant("Player_JumpAnimMode")
PLAYER_JUMP_FRAME_COUNT = pasm_constant("Player_JumpFCount")
PLAYER_JUMP_DELAY = pasm_constant("Player_JumpDelay")
FRAME_DISPATCH_PC = 0x0C8FD6
FRAME_MATCH_PC = 0x0C9047
FRAME_ENTITY_BASE = pasm_constant("AudioSemantic_FrameSoundEntityBase")
SEMANTIC_REQUEST_COUNT = pasm_constant("AudioSemantic_RequestCount")
TAD_SFX_QUEUE = 0x7E0000 + pasm_constant("Tad_sfxQueue_sfx")
TAD_STATE = pasm_constant("TadPrivate_state")
TAD_PREVIOUS_COMMAND = pasm_constant("TadPrivate_previousCommand")
TAD_NEXT_COMMAND = pasm_constant("TadPrivate_nextCommand_id")
APUIO0 = pasm_constant("APUIO0")
STREAM_PENDING = pasm_constant("TadPrivate_stream_pending")
STREAM_ACTIVE = pasm_constant("AudioSemantic_FootDieStreamActive")
PLAY_SFX_HANDLER_PC = 0x08C1
DIESOUND_PC = 0x0C8E2E
STREAM_START_PC = 0x0C9885
FRAME_STAGE_PCS = {
    "roster": 0x0C8FFD,
    "selected": 0x0C900A,
    "variant": 0x0C901D,
    "jump_mode": 0x0C9034,
    "frame": FRAME_MATCH_PC,
}


def read_u16(m, address: int) -> int:
    data = read_block(m, address, 32)
    return data[0] | (data[1] << 8)


def main() -> None:
    output = Path(os.environ.get("JUMP_CAPTURE_PATH", "out/jump-gameplay-v7.raw")).resolve()
    arm = Path(os.environ.get("JUMP_CAPTURE_ARM_FILE", str(output) + ".arm")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    for path in (output, Path(str(output) + ".json"), Path(str(output) + ".trace"), arm):
        path.unlink(missing_ok=True)

    voice = int(os.environ.get("JUMP_CAPTURE_VOICE", "7"), 0)
    env = {
        "MESEN_VOICE_CAPTURE_PATH": str(output),
        "MESEN_VOICE_CAPTURE_VOICE": str(voice),
        "MESEN_VOICE_CAPTURE_ARM_FILE": str(arm),
    }
    report = Reporter("JUMP-SFX-PHYSICAL", kind="GATE")
    with open_session(__file__, env=env) as m:
        semantic.boot(m)
        neutralize_ai(m)
        load_leo_onto_player(m, 12)
        neutralize_ai(m)
        # Character loading legitimately submits audio/stream lifecycle work.
        # Match the direct resident fixture: let that production command plane
        # settle before asserting the gameplay input edge under test.
        for _ in range(30):
            m.run_frames(1)
            m.pause()

        report.check("loaded player has real jump data", read_block(m, Player_JumpFCount, 32)[0] != 0)
        before = read_u16(m, JUMP_REQUEST_COUNT)
        frame_before = read_u16(m, FRAME_SOUND_REQUEST_COUNT)
        semantic_before = read_u16(m, SEMANTIC_REQUEST_COUNT)
        m.write_u8(ENTITY_BASES[0] + CHAR_SELECTED, 0)
        m.write_u16(ENTITY_BASES[0] + CHAR_THROW_ZPOS, 0)
        m.write_u16(ENTITY_BASES[0] + CHAR_THROW_ZVEL, 0)

        frame_dispatch_hook = m.add_exec_hook(FRAME_DISPATCH_PC, FRAME_DISPATCH_PC)
        frame_stage_hooks = {
            stage: m.add_exec_hook(pc, pc)
            for stage, pc in FRAME_STAGE_PCS.items()
        }
        spc_handler_hook = m.add_exec_hook(
            PLAY_SFX_HANDLER_PC, PLAY_SFX_HANDLER_PC, cpu_type="Spc"
        )
        provenance_hooks = {
            "diesound": m.add_exec_hook(DIESOUND_PC, DIESOUND_PC),
            "frame_stream": m.add_exec_hook(0x0C908A, 0x0C908A),
            "stream_start": m.add_exec_hook(STREAM_START_PC, STREAM_START_PC),
        }
        arm.touch()
        m.set_input(m.BTN_A, 1)
        m.pause()
        m.run_frames(1)
        m.pause()
        # The fixture is a single grounded A edge.  Clear it before any
        # subsequent airborne tick so it cannot become a held jumpattack2
        # request while the dispatcher/capture hooks are being armed.
        m.set_input(0, 1)
        frame_dispatch_pause = m.run_until(60, frame_dispatch_hook)
        frame_dispatch_cpu = (
            m.get_cpu_state("Snes")
            if frame_dispatch_pause.get("reason") == "hookFired"
            else None
        )
        after = read_u16(m, JUMP_REQUEST_COUNT)
        report.check("grounded A emits exactly one JUMP request", after - before == 1)
        report.check(
            "grounded A enters jump state",
            read_block(m, ENTITY_BASES[0] + CHAR_SELECTED, 32)[0] == CHAR_SELECTED_JUMP,
        )

        audio_snapshots = []
        queue_snapshots = []
        player_transitions = []
        previous_player = None
        for frame in range(40):
            state = m.get_audio_state()
            player = {
                "roster": read_block(m, ENTITY_BASES[0] + CHAR_ROSTER_INDEX, 32)[0],
                "selected": read_block(m, ENTITY_BASES[0] + CHAR_SELECTED, 32)[0],
                "variant": read_block(m, ENTITY_BASES[0] + CHAR_ATTACK_VARIANT, 32)[0],
                "frame": read_block(m, ENTITY_BASES[0] + CHAR_FRAME_INDEX, 32)[0],
                "tick": read_block(m, ENTITY_BASES[0] + CHAR_TICK_COUNTER, 32)[0],
                "jump_mode": read_block(m, PLAYER_JUMP_ANIM_MODE, 32)[0],
                "jump_frame_count": read_block(m, PLAYER_JUMP_FRAME_COUNT, 32)[0],
                "jump_delay": read_block(m, PLAYER_JUMP_DELAY, 32)[0],
            }
            if player != previous_player:
                player_transitions.append({"frame": frame, **player})
                previous_player = player
            if frame < 6:
                audio_snapshots.append({
                    "frame": frame,
                    "dsp_key_on": state["dsp"]["keyOn"],
                    "dsp_key_off": state["dsp"]["keyOff"],
                    "voices_ended": state["dsp"]["voicesEnded"],
                    "voice6": state["voices"][6],
                    "voice7": state["voices"][7],
                    "player": player,
                })
            if frame < 24:
                queue_snapshots.append({
                    "frame": frame,
                    "queued_sfx": read_block(m, TAD_SFX_QUEUE, 32)[0],
                    "state": read_block(m, TAD_STATE, 32)[0],
                    "previous_command": read_block(m, TAD_PREVIOUS_COMMAND, 32)[0],
                    "next_command": read_block(m, TAD_NEXT_COMMAND, 32)[0],
                    "apuio0": read_snes_bus_block(m, APUIO0, 32)[0],
                    "stream_pending": read_block(m, STREAM_PENDING, 32)[0],
                    "stream_active": read_block(m, STREAM_ACTIVE, 32)[0],
                })
            m.run_frames(1)
            m.pause()
        m.run_frames(140)
        m.pause()
        frame_dispatch_events = m.drain_notifications()
        m.remove_hook(frame_dispatch_hook)
        m.remove_hook(spc_handler_hook)
        for handle in frame_stage_hooks.values():
            m.remove_hook(handle)
        for handle in provenance_hooks.values():
            m.remove_hook(handle)
        frame_after = read_u16(m, FRAME_SOUND_REQUEST_COUNT)
        semantic_after = read_u16(m, SEMANTIC_REQUEST_COUNT)
        current_semantic_id = read_block(m, CURRENT_SEMANTIC_ID, 32)[0]
        frame_entity_base = read_u16(m, FRAME_ENTITY_BASE)

    raw = output.read_bytes() if output.exists() else b""
    payload = {
        "event": "JUMP_GAMEPLAY",
        "fixture": "grounded-a-jump",
        "local_sfx_id": 2,
        "voice": voice,
        "capture_bytes": len(raw),
        "capture_sha256": hashlib.sha256(raw).hexdigest(),
        "audio_snapshots": audio_snapshots,
        "frame_sound_request_delta": (frame_after - frame_before) & 0xFFFF,
        "semantic_request_delta": (semantic_after - semantic_before) & 0xFFFF,
        "queue_snapshots": queue_snapshots,
        "spc_play_sfx_handler_count": sum(
            1 for event in frame_dispatch_events
            if event.get("params", {}).get("handle") == spc_handler_hook
        ),
        "current_semantic_id": current_semantic_id,
        "player_transitions": player_transitions,
        "frame_dispatch_event_count": len(frame_dispatch_events),
        "frame_stage_event_counts": {
            stage: sum(
                1 for event in frame_dispatch_events
                if event.get("params", {}).get("handle") == handle
            )
            for stage, handle in frame_stage_hooks.items()
        },
        "frame_stage_event_addresses": {
            stage: sorted({
                event.get("params", {}).get("address")
                for event in frame_dispatch_events
                if event.get("params", {}).get("handle") == handle
            })
            for stage, handle in frame_stage_hooks.items()
        },
        "stream_provenance_counts": {
            name: sum(
                1 for event in frame_dispatch_events
                if event.get("params", {}).get("handle") == handle
            )
            for name, handle in provenance_hooks.items()
        },
        "frame_entity_base": frame_entity_base,
        "frame_dispatch_pause": frame_dispatch_pause,
        "frame_dispatch_cpu": frame_dispatch_cpu,
    }
    print(json.dumps(payload, sort_keys=True))
    report.check("capture file exists", output.exists())
    report.check("capture contains PCM", bool(raw))
    report.finish()


if __name__ == "__main__":
    main()
