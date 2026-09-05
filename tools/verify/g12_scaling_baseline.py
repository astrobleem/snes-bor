#!/usr/bin/env python3
"""G12 kickoff baseline: measure the live character scheduler.

This is intentionally a measurement gate, not a residency implementation.  It
uses the real stage-clear transition to reach stage 1A, then samples every real
frame.  The bounded actor count is read from the source and no synthetic slots
are invented.
"""
import json
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact)

CHAR_ZP_LEN = pasm_constant("CHAR_ZP_LEN")
CHAR_FRAME_INDEX = pasm_constant("CHAR_FRAME_INDEX")
CHAR_TICK_COUNTER = pasm_constant("CHAR_TICK_COUNTER")
CHAR_SELECTED = pasm_constant("CHAR_SELECTED")
CHAR_ATTACK_VARIANT = pasm_constant("CHAR_ATTACK_VARIANT")
CHAR_INPUT_DRIVEN = pasm_constant("CHAR_INPUT_DRIVEN")
CHAR_ROSTER_INDEX = pasm_constant("CHAR_ROSTER_INDEX")
CHAR_HP = pasm_constant("CHAR_HP")
CHAR_HP_MAX = pasm_constant("CHAR_HP_MAX")
CHAR_IDLE_BASE_LO = pasm_constant("CHAR_IDLE_BASE_LO")
CHAR_IDLE_BASE_HI = pasm_constant("CHAR_IDLE_BASE_HI")
CHAR_IDLE_FCOUNT = pasm_constant("CHAR_IDLE_FCOUNT")
CHAR_WALK_BASE_LO = pasm_constant("CHAR_WALK_BASE_LO")
CHAR_WALK_BASE_HI = pasm_constant("CHAR_WALK_BASE_HI")
CHAR_ATTACK_BASE_LO = pasm_constant("CHAR_ATTACK_BASE_LO")
CHAR_ATTACK_BASE_HI = pasm_constant("CHAR_ATTACK_BASE_HI")
CHAR_ATTACK2_BASE_LO = pasm_constant("CHAR_ATTACK2_BASE_LO")
CHAR_ATTACK2_BASE_HI = pasm_constant("CHAR_ATTACK2_BASE_HI")
CHAR_FALL_BASE_LO = pasm_constant("CHAR_FALL_BASE_LO")
CHAR_FALL_BASE_HI = pasm_constant("CHAR_FALL_BASE_HI")
CHAR_RISE_BASE_LO = pasm_constant("CHAR_RISE_BASE_LO")
CHAR_RISE_BASE_HI = pasm_constant("CHAR_RISE_BASE_HI")
CHAR_SELECTED_FALL = pasm_constant("CHAR_SELECTED_FALL")
CHAR_SELECTED_RISE = pasm_constant("CHAR_SELECTED_RISE")
CHAR_SELECTED_JUMP = pasm_constant("CHAR_SELECTED_JUMP")
CHAR_SELECTED_THROWN = pasm_constant("CHAR_SELECTED_THROWN")
ACTOR_COUNT = pasm_constant("CHARACTER_ACTOR_COUNT")
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(ACTOR_COUNT)]
GAME_STATE = pasm_constant_in("src/core/game_state.pasm", "Game_State")
GAME_STATE_PLAYING = pasm_constant_in("src/core/game_state.pasm", "GAME_STATE_PLAYING")
GAME_STAGE_INDEX = pasm_constant_in("src/core/game_state.pasm", "Game_StageIndex")
STAGE_CLEARED = pasm_constant_in("src/core/game_state.pasm", "Stage_Cleared")
SPAWN_INDEX = pasm_constant_in("src/core/spawn.pasm", "Spawn_Index")
SPAWN_COUNT = pasm_constant_in("src/core/spawn.pasm", "Spawn_Count")
MSU_BUSY = pasm_constant("Msu1_StreamBusy")
NMI_COUNTER = pasm_constant_in("src/core/nmi.pasm", "Nmi_FrameCounter")
NMI_OVER = pasm_constant_in("src/core/nmi.pasm", "Nmi_FrameOver")
DMA_CUR = pasm_constant_in("src/core/dma.pasm", "DmaQueue_CurrentSlot")
DMA_BUDGET = pasm_constant_in("src/core/dma.pasm", "DmaQueue_BudgetTotal")
DMA_QUEUE = pasm_constant_in("src/core/dma.pasm", "DmaQueue")
ANIM_TRACE_INDEX = pasm_constant("G12_AnimTrace_Index")
ANIM_TRACE_OVERFLOW = pasm_constant("G12_AnimTrace_Overflow")
ANIM_TRACE_RING = pasm_constant("G12_AnimTrace_Ring")
ANIM_TRACE_LAST_DP = pasm_constant("G12_AnimTrace_LastDp")
ANIM_TRACE_LAST_EVENT = pasm_constant("G12_AnimTrace_LastEvent")
ANIM_TRACE_LAST_VALUE = pasm_constant("G12_AnimTrace_LastValue")


def block(m, addr, length=32, mem_type="snesMemory"):
    return read_block(m, addr, length, mem_type=mem_type)


def u8(m, addr):
    return block(m, addr)[0]


def u16(m, addr):
    b = block(m, addr)
    return b[0] | (b[1] << 8)


def source_identity(entity, frame, selected, variant):
    """Return the exact source address Msu1_LoadFrame would use when known."""
    bases = {
        0: (CHAR_IDLE_BASE_LO, CHAR_IDLE_BASE_HI, "idle"),
        1: (CHAR_WALK_BASE_LO, CHAR_WALK_BASE_HI, "walk"),
        2: (CHAR_ATTACK_BASE_LO, CHAR_ATTACK_BASE_HI, "attack"),
        CHAR_SELECTED_FALL: (CHAR_FALL_BASE_LO, CHAR_FALL_BASE_HI, "fall"),
        CHAR_SELECTED_RISE: (CHAR_RISE_BASE_LO, CHAR_RISE_BASE_HI, "rise"),
    }
    if selected == 2 and variant == 1:
        bases[2] = (CHAR_ATTACK2_BASE_LO, CHAR_ATTACK2_BASE_HI, "attack2")
    if selected not in bases or frame == 0xFF:
        return None, "non-streaming"
    lo_off, hi_off, state_name = bases[selected]
    lo = entity[lo_off] | (entity[lo_off + 1] << 8)
    hi = entity[hi_off]
    return ((hi << 16) | lo) + frame * 768, state_name


def snapshot(m):
    entities = []
    for base in ENTITY_BASES:
        b = block(m, base, 64)
        frame = b[CHAR_FRAME_INDEX]
        selected = b[CHAR_SELECTED]
        variant = b[CHAR_ATTACK_VARIANT]
        source, state_name = source_identity(b, frame, selected, variant)
        # $FF is the pre-frame sentinel.  With tick==1 it is an outstanding
        # initial/transition request, not proof of a legitimate non-streaming
        # action.  Keep true non-streaming states separate for later review.
        if frame == 0xFF and b[CHAR_TICK_COUNTER] == 1:
            state_name = "pending_initial_frame"
        entities.append({
            "frame": frame,
            "tick": b[CHAR_TICK_COUNTER],
            "selected": selected,
            "variant": variant,
            "state": state_name,
            "source_identity": source,
            "role": b[CHAR_INPUT_DRIVEN],
            "roster": b[CHAR_ROSTER_INDEX],
            "hp": b[CHAR_HP],
            "idle_frame_count": b[CHAR_IDLE_FCOUNT],
            "idle_base_lo": b[CHAR_IDLE_BASE_LO],
            "idle_base_hi": b[CHAR_IDLE_BASE_HI],
        })
    q = block(m, DMA_QUEUE, 64)
    active = sum(1 for i in range(8) if q[i * 8 + 4] & 0x40)
    ring = block(m, ANIM_TRACE_RING, 32) + block(m, ANIM_TRACE_RING + 32, 32)
    return {
        "entities": entities,
        "msu_busy": u8(m, MSU_BUSY),
        "nmi": u16(m, NMI_COUNTER),
        "nmi_over": u8(m, NMI_OVER),
        "dma_active": active,
        "dma_current": u16(m, DMA_CUR),
        "dma_budget": u16(m, DMA_BUDGET),
        "stage": u16(m, GAME_STAGE_INDEX),
        "state": u16(m, GAME_STATE),
        "anim_trace_index": u8(m, ANIM_TRACE_INDEX),
        "anim_trace_overflow": u8(m, ANIM_TRACE_OVERFLOW),
        "anim_trace_last": {
            "dp": u16(m, ANIM_TRACE_LAST_DP),
            "event": u8(m, ANIM_TRACE_LAST_EVENT),
            "value": u8(m, ANIM_TRACE_LAST_VALUE),
        },
        "anim_trace_records": [
            {"dp": ring[i] | (ring[i + 1] << 8), "event": ring[i + 2],
             "value": ring[i + 3], "selected": ring[i + 4],
             "frame": ring[i + 5], "tick": ring[i + 6], "grab": ring[i + 7]}
            for i in range(0, 64, 8)
        ],
    }


def move_to_stage_1a(m):
    m.run_frames(60)
    count = u8(m, SPAWN_COUNT)
    m.write_u8(SPAWN_INDEX, count)
    for base in ENTITY_BASES[1:]:
        m.write_u8(base + CHAR_HP, 0)
    m.run_frames(5)
    for _ in range(20):
        m.set_input(m.BTN_RIGHT, 60)
        if u16(m, GAME_STAGE_INDEX) != 0:
            break
    for _ in range(20):
        if u16(m, GAME_STATE) == GAME_STATE_PLAYING and u16(m, GAME_STAGE_INDEX) == 1:
            return
        m.run_frames(30)
    raise RuntimeError(f"stage 1A transition did not settle: {snapshot(m)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=240)
    parser.add_argument("--trace-out")
    parser.add_argument("--production-six", action="store_true",
                        help="spawn the bounded six-actor production fixture")
    parser.add_argument("--actor-liveness", action="store_true",
                        help="short production fixture isolating actor 2 with actor 1 control")
    args = parser.parse_args()
    with open_session(__file__) as m:
        m.reset_emulator()
        # Reset the bounded diagnostic ring explicitly; production leaves
        # this debug-only scratch uninitialized at boot.
        m.write_u8(ANIM_TRACE_INDEX, 0)
        m.write_u8(ANIM_TRACE_OVERFLOW, 0)
        m.write_memory("snesMemory", ANIM_TRACE_RING, "00" * 32)
        m.write_memory("snesMemory", ANIM_TRACE_RING + 32, "00" * 32)
        if args.production_six:
            # Reuse the production verifier's actual SpawnTable_Wram records
            # and Spawn_Play path.  This is a fresh measurement fixture, not
            # the destructive lifecycle/visual fixture from that gate.
            from game_g12_six_actor_production import install_fixture_queue, wait_for_six
            run_frames_exact(m, 180)
            for base in ENTITY_BASES[1:]:
                m.write_u8(base + CHAR_HP, 0)
            install_fixture_queue(m)
            if wait_for_six(m, 600) is None:
                raise RuntimeError(f"six production actors did not spawn: {snapshot(m)}")
            m.pause()
            m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
            # One-time fixture conditioning keeps all five production-spawned
            # fighters alive for the observation window; roles and update
            # paths remain the ordinary AI mode (2), never static mode 0.
            for base in ENTITY_BASES[1:]:
                m.write_u8(base + CHAR_HP, 255)
            if args.actor_liveness:
                # Preserve production initialization for the two observed
                # actors, but remove later callers so the last-event latch is
                # actor-specific during this bounded causal reproducer.
                for base in ENTITY_BASES[3:]:
                    m.write_u8(base + CHAR_HP, 0)
        else:
            move_to_stage_1a(m)
            # Stage 1A's real spawn queue is trigger-position driven. Walk through
            # the first production wave so the measurement covers live fighters,
            # not merely the freshly-reset empty slots at the stage's left edge.
            m.set_input(m.BTN_RIGHT, 300)
            run_frames_exact(m, 30)
        m.pause()
        before = snapshot(m)
        samples = []
        frame_changes = [0] * ACTOR_COUNT
        previous = [e["frame"] for e in before["entities"]]
        completed = 0
        while completed < args.frames:
            chunk = min(100, args.frames - completed)
            for _ in range(chunk):
                run_frames_exact(m, 1)
                m.pause()
                current = snapshot(m)
                samples.append(current)
                for i, e in enumerate(current["entities"]):
                    if e["frame"] != previous[i]:
                        frame_changes[i] += 1
                previous = [e["frame"] for e in current["entities"]]
            completed += chunk
            active_now = sum(1 for e in samples[-1]["entities"][1:]
                             if e["hp"] > 0 and e["role"] == 2)
            print(f"measurement chunk {completed}/{args.frames}: "
                  f"active_nonplayer_combat={active_now} "
                  f"nmi={samples[-1]['nmi']} dma={samples[-1]['dma_active']}/"
                  f"{samples[-1]['dma_budget']}", flush=True)

        visible = block(m, 0, 32, mem_type="snesSpriteRam")
        result = {
            "sample_frames": len(samples),
            "before": before,
            "frame_changes": frame_changes,
            "frame_advances_per_real_frame": [x / len(samples) for x in frame_changes],
            "max_dma_active_at_sample_boundary": max(s["dma_active"] for s in samples),
            "max_dma_budget_at_sample_boundary": max(s["dma_budget"] for s in samples),
            "max_msu_busy_at_sample_boundary": max(s["msu_busy"] for s in samples),
            "nmi_over_samples": sum(1 for s in samples if s["nmi_over"]),
            "nmi_delta": samples[-1]["nmi"] - before["nmi"],
            "final_entities": samples[-1]["entities"],
            "oam_first_six": [list(visible[i:i + 4]) for i in range(0, 24, 4)],
            "production_entity_limit": ACTOR_COUNT,
            "measurement_fixture": "production-six" if args.production_six else "stage-1a-control",
            "active_combat_actors_observed": [sum(1 for e in s["entities"][1:] if e["hp"] > 0 and e["role"] == 2) for s in samples],
        }
        # A request is created only on the first tick==1 observation of a
        # pending countdown. Later tick==1 observations are retry attempts,
        # not new work. State changes can supersede or cancel a pending timed
        # request, so those outcomes remain explicit in the ledger.
        timed_requests = [0] * ACTOR_COUNT
        timed_streams = [0] * ACTOR_COUNT
        retries = [0] * ACTOR_COUNT
        forced_loads = [0] * ACTOR_COUNT
        superseded = [0] * ACTOR_COUNT
        cancelled = [0] * ACTOR_COUNT
        waits = [[] for _ in range(ACTOR_COUNT)]
        pending = [None] * ACTOR_COUNT
        observations = [before] + samples
        for previous, sample in zip(observations, observations[1:]):
            for i, entity in enumerate(sample["entities"]):
                old = previous["entities"][i]
                due_state = old["state"] in {"idle", "walk", "attack", "attack2", "fall", "rise", "pending_initial_frame"}
                changed = (old["frame"], old["source_identity"], old["selected"], old["variant"]) != (entity["frame"], entity["source_identity"], entity["selected"], entity["variant"])
                target_stream = entity["source_identity"] is not None
                if due_state and old["tick"] == 1 and pending[i] is None:
                    timed_requests[i] += 1
                    pending[i] = {"wait": 0, "state": old["state"]}
                if pending[i] is not None:
                    pending[i]["wait"] += 1
                if changed:
                    if pending[i] is not None:
                        same_state_stream = target_stream and due_state and (
                            entity["state"] == pending[i]["state"] or
                            pending[i]["state"] == "pending_initial_frame")
                        wait = max(0, pending[i]["wait"] - 1)
                        if same_state_stream:
                            timed_streams[i] += 1
                            waits[i].append(wait)
                        elif target_stream:
                            forced_loads[i] += 1
                            superseded[i] += 1
                        else:
                            cancelled[i] += 1
                        pending[i] = None
                    elif target_stream:
                        forced_loads[i] += 1
                elif due_state and old["tick"] == 1:
                    retries[i] += 1
        for i in range(ACTOR_COUNT):
            if pending[i] is not None:
                waits[i].append(pending[i]["wait"])
        result["timed_due_requests"] = timed_requests
        result["successful_timed_streams"] = timed_streams
        # The recorder observes individual busy decisions, but this observer
        # does not retain a lossless per-event sequence across all entities.
        # Keep this aggregate null rather than manufacturing a count from the
        # circular snapshot ring; the per-sample records remain evidence.
        result["inferred_nonprogress_while_due"] = retries
        result["confirmed_busy_denials"] = None
        result["confirmed_busy_denials_status"] = "unmeasured: actual decisions are retained in the bounded event ring, but aggregate per-actor counts are not losslessly reconstructible from sampled ring snapshots"
        result["forced_frame_loads"] = forced_loads
        result["timed_requests_superseded_by_forced_load"] = superseded
        result["timed_requests_cancelled_by_nonstreaming_transition"] = cancelled
        result["outstanding_timed_requests"] = [int(x is not None) for x in pending]
        result["request_accounting"] = [{
            "created": timed_requests[i],
            "serviced_stream": timed_streams[i],
            "cache_serviced": 0,
            "superseded": superseded[i],
            "cancelled": cancelled[i],
            "outstanding": int(pending[i] is not None),
            "invariant": timed_streams[i] + superseded[i] + cancelled[i] + int(pending[i] is not None) == timed_requests[i],
        } for i in range(ACTOR_COUNT)]
        result["actual_frame_advances"] = frame_changes
        result["wait_frames_after_due"] = waits
        result["max_wait_after_due"] = [max(w, default=0) for w in waits]
        result["average_wait_after_due"] = [sum(w) / len(w) if w else 0 for w in waits]
        if args.trace_out:
            with open(args.trace_out, "w", encoding="utf-8") as trace_file:
                json.dump({"before": before, "samples": samples, "summary": result}, trace_file, indent=2, sort_keys=True)
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
