"""Explore packed Spawn_Play audio-relevant runtime states."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "audio"))
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402

RECORD_SIZE = 10
KIND_PROP, KIND_WAIT, KIND_GROUP = 1, 2, 3
KIND_BOSS_IDENTIFIED = 5
PICKUP_SHIFT, PICKUP_MASK = 5, 7


def roster_identity(entry: dict) -> str:
    return entry["source_character"].split("\\CHARS\\", 1)[1].upper().strip("\\")


def explore_stage(stage: dict, max_states: int = 500000) -> list[dict]:
    data = (ROOT / stage["spawn"]).read_bytes()
    if len(data) % RECORD_SIZE:
        raise SystemExit(f"invalid packed spawn size: {stage['spawn']}")
    records = [data[i:i + RECORD_SIZE] for i in range(0, len(data), RECORD_SIZE)]
    trigger_positions = sorted({record[0] | (record[1] << 8) for record in records})
    natural = (1, 2, 3)
    # queue, group_min, group_max, waiting, camera_x, slots
    # slot = alive, loaded_roster_index, input_driven_prop, pickup_type, pending_item_index
    start = (0, 100, 100, False, 0, tuple((False, idx, False, 0, 0) for idx in natural))
    queue = deque([start])
    seen = {start}
    states = []
    while queue:
        if len(seen) > max_states:
            raise SystemExit(f"runtime state exploration exceeded {max_states}: {stage['source_level']}")
        queue_index, group_min, group_max, waiting, camera_x, slots = queue.popleft()
        states.append({"queue_index": queue_index, "group_min": group_min, "group_max": group_max, "wait_state": "waiting" if waiting else "ready", "camera_trigger_x": camera_x, "slots": [{"alive": s[0], "roster_index": s[1], "prop": s[2], "pickup_type": s[3], "contained_item_roster_index": s[4]} for s in slots]})

        def enqueue(next_state):
            if next_state not in seen:
                seen.add(next_state)
                queue.append(next_state)

        # Death/free, collection/free, and prop break/reveal are player-driven
        # transitions. A revealed item retains CHAR_INPUT_DRIVEN_PROP exactly
        # as Spawn_RevealPendingItems does; this is needed for later restore.
        for index, slot in enumerate(slots):
            alive, identity, prop, pickup_type, contained = slot
            if not alive:
                continue
            updated = list(slots)
            if prop and contained:
                updated[index] = (True, contained, True, pickup_type, 0)
            else:
                updated[index] = (False, identity, prop, 0, 0)
            enqueue((queue_index, group_min, group_max, waiting, camera_x, tuple(updated)))

        if queue_index >= len(records):
            continue

        record = records[queue_index]
        trigger_x = record[0] | (record[1] << 8)
        kind = record[6] & 7

        # Spawn_Play releases a wait first when no non-prop enemy remains.
        if waiting and not any(s[0] and not s[2] and s[3] == 0 for s in slots):
            enqueue((queue_index, group_min, group_max, False, camera_x, slots))
            continue

        # Screen_PosX is monotonic. GROUP does not clamp it, so the player can
        # pass several future trigger positions while the queue is blocked.
        # WAIT clamps at the current Screen_PosX. Enumerating the finite set of
        # packed trigger positions preserves that distinction without a pixel
        # movement simulator.
        if trigger_x > camera_x:
            if waiting:
                continue
            for next_camera in trigger_positions:
                if next_camera > camera_x:
                    enqueue((queue_index, group_min, group_max, waiting, next_camera, slots))
            continue

        enemy_count = sum(1 for s in slots if s[0] and not s[2] and s[3] == 0)
        if enemy_count >= group_min or enemy_count >= group_max:
            continue

        if kind == KIND_WAIT:
            enqueue((queue_index + 1, group_min, group_max, True, trigger_x, slots))
            continue
        if kind == KIND_GROUP:
            enqueue((queue_index + 1, record[2], record[3], waiting, camera_x, slots))
            continue

        free = next((index for index, slot in enumerate(slots) if not slot[0]), None)
        if free is None:
            continue
        previous = slots[free]
        identity = previous[1]
        object_index = record[9]
        if (kind == KIND_BOSS_IDENTIFIED or kind == KIND_PROP) and object_index:
            identity = object_index
        elif previous[2]:
            identity = natural[free]
        prop = kind == KIND_PROP
        contained = record[8] if prop and record[8] else 0
        pickup_type = ((record[6] >> PICKUP_SHIFT) & PICKUP_MASK) if prop else 0
        updated = list(slots)
        updated[free] = (True, identity, prop, pickup_type, contained)
        enqueue((queue_index + 1, group_min, group_max, False, camera_x, tuple(updated)))
    return states


def main() -> int:
    roster_by_index = {index: roster_identity(entry) for index, entry in enumerate(ROSTER_CONFIGS)}
    states_by_stage = {stage["family"] + ":" + stage["source_level"]: explore_stage(stage) for stage in STAGE_CONFIGS}
    summary = {"schema_version": 3, "record_size": RECORD_SIZE, "max_non_player_slots": 3, "roster_by_index": {str(k): v for k, v in roster_by_index.items()}, "state_count_by_stage": {k: len(v) for k, v in states_by_stage.items()}, "total_state_count": sum(len(v) for v in states_by_stage.values()), "input_spawn_hashes": {stage["family"] + ":" + stage["source_level"]: __import__("hashlib").sha256((ROOT / stage["spawn"]).read_bytes()).hexdigest() for stage in STAGE_CONFIGS}}
    (ROOT / "tools/audio/runtime_sfx_states.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"runtime state explorer: {summary['total_state_count']} states; max non-player slots: 3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
