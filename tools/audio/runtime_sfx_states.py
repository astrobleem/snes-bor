"""Explore the finite audio-relevant state graph represented by packed spawns."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "audio")]
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402

RECORD_SIZE = 10
KIND_MASK = 7
KIND_PROP = 1
KIND_WAIT = 2
KIND_GROUP = 3
KIND_BOSS = 4
KIND_BOSS_IDENTIFIED = 5
PICKUP_SHIFT = 5
PICKUP_MASK = 7


def roster_identity(entry: dict) -> str:
    return entry["source_character"].split("\\CHARS\\", 1)[1].upper().strip("\\")


def explore_stage(stage: dict) -> list[dict]:
    data = (ROOT / stage["spawn"]).read_bytes()
    if len(data) % RECORD_SIZE:
        raise SystemExit(f"invalid packed spawn size: {stage['spawn']}")
    records = [data[i:i + RECORD_SIZE] for i in range(0, len(data), RECORD_SIZE)]
    natural = (1, 2, 3)
    start = (0, 0, 0, False, tuple((False, idx, False, 0, 0) for idx in natural))
    queue = deque([start])
    seen = {start}
    states = []
    while queue:
        queue_index, group_min, group_max, waiting, slots = queue.popleft()
        states.append({"queue_index": queue_index, "group_min": group_min, "group_max": group_max, "wait_state": "waiting" if waiting else "ready", "slots": [{"alive": s[0], "roster_index": s[1], "prop": s[2], "pickup_type": s[3], "contained_item_roster_index": s[4]} for s in slots]})

        def enqueue(next_state):
            if next_state not in seen:
                seen.add(next_state)
                queue.append(next_state)

        # A contained item is not active until the prop-break transition.
        for index, slot in enumerate(slots):
            alive, identity, prop, pickup_type, contained = slot
            if not alive:
                continue
            updated = list(slots)
            if prop and contained:
                updated[index] = (True, contained, False, pickup_type, 0)
            else:
                updated[index] = (False, identity, False, 0, 0)
            enqueue((queue_index, group_min, group_max, waiting, tuple(updated)))

        if queue_index >= len(records):
            continue
        record = records[queue_index]
        kind = record[6] & KIND_MASK
        if kind == KIND_GROUP:
            enqueue((queue_index + 1, record[2], record[3], waiting, slots))
            continue
        if kind == KIND_WAIT:
            if not any(s[0] and not s[2] and s[3] == 0 for s in slots):
                enqueue((queue_index + 1, group_min, group_max, False, slots))
            continue
        free = next((index for index, slot in enumerate(slots) if not slot[0]), None)
        if free is None:
            continue
        previous = slots[free]
        identity = previous[1]
        if kind in (KIND_BOSS_IDENTIFIED, KIND_PROP) and record[9]:
            identity = record[9]
        elif previous[2]:
            identity = natural[free]
        prop = kind == KIND_PROP
        contained = record[8] if prop and record[8] else 0
        pickup_type = ((record[6] >> PICKUP_SHIFT) & PICKUP_MASK) if prop and not contained else 0
        updated = list(slots)
        updated[free] = (True, identity, prop, pickup_type, contained)
        enqueue((queue_index + 1, group_min, group_max, False, tuple(updated)))
    if any(len(state["slots"]) != 3 for state in states):
        raise SystemExit("runtime state violated three-slot invariant")
    return states


def main() -> int:
    roster_by_index = {index: roster_identity(entry) for index, entry in enumerate(ROSTER_CONFIGS)}
    states_by_stage = {stage["family"] + ":" + stage["source_level"]: explore_stage(stage) for stage in STAGE_CONFIGS}
    output = {"schema_version": 2, "record_size": RECORD_SIZE, "max_non_player_slots": 3, "roster_by_index": {str(k): v for k, v in roster_by_index.items()}, "states_by_stage": states_by_stage}
    (ROOT / "tools/audio/runtime_sfx_states.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"runtime state explorer: {sum(len(v) for v in states_by_stage.values())} states; max non-player slots: 3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
