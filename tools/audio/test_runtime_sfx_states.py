"""Mini-fixtures for packed Spawn_Play state semantics."""
from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "audio"))
from runtime_sfx_states import explore_stage  # noqa: E402


def record(trigger=0, kind=0, group_min=0, group_max=0, item=0, obj=0):
    row = bytearray(10)
    row[0] = trigger & 0xff
    row[1] = trigger >> 8
    row[2] = group_min
    row[3] = group_max
    row[6] = kind | (3 << 5 if kind == 1 else 0)
    row[8] = item
    row[9] = obj
    return bytes(row)


def states(rows):
    with tempfile.TemporaryDirectory(prefix="bor-sfx-state-") as tmp:
        path = Path(tmp) / "spawn.bin"
        path.write_bytes(b"".join(rows))
        return explore_stage({"spawn": path})


def main() -> int:
    ordinary = record()
    a = states([ordinary, ordinary])
    assert any(s["queue_index"] == 2 for s in a)

    # Prop index 19 (Chair) remains provenance after free; ordinary reuse
    # restores natural slot 1 (JHUN), never the prop identity.
    b = states([record(kind=1, obj=19), ordinary])
    assert any(s["queue_index"] == 2 and s["slots"][0]["roster_index"] == 1 and s["slots"][0]["alive"] for s in b)

    # Table/Chair object and contained Money occupy one slot across reveal.
    c = states([record(kind=1, item=14, obj=19)])
    assert any(s["slots"][0]["alive"] and s["slots"][0]["roster_index"] == 14 and s["slots"][0]["prop"] and s["slots"][0]["pickup_type"] == 3 for s in c)

    # Group 1 blocks the second ordinary spawn while one enemy remains.
    d = states([record(kind=3, group_min=1, group_max=2), ordinary, ordinary])
    assert not any(s["queue_index"] == 3 and sum(slot["alive"] and not slot["prop"] for slot in s["slots"]) >= 2 for s in d)

    # Same-trigger records remain eligible under a wait; later trigger does not
    # advance until the waiting enemy is released.
    e = states([ordinary, record(trigger=0, kind=2), ordinary])
    assert any(s["queue_index"] == 3 for s in e)
    f = states([ordinary, record(trigger=0, kind=2), record(trigger=10)])
    assert any(s["queue_index"] == 2 and s["camera_trigger_x"] == 0 and s["wait_state"] == "waiting" for s in f)
    assert not any(s["queue_index"] == 3 and s["camera_trigger_x"] < 10 for s in f)

    # GROUP blocks queue advancement but does not clamp the camera. Once the
    # first enemy dies, an overdue WAIT is reached at the already-advanced
    # camera position and same/earlier records remain eligible.
    overshoot = states([
        record(kind=3, group_min=1, group_max=2),
        ordinary,
        record(trigger=10),
        record(trigger=20, kind=2),
        record(trigger=20),
        record(trigger=30),
    ])
    assert any(s["queue_index"] == 2 and s["camera_trigger_x"] >= 20 for s in overshoot)
    assert any(s["queue_index"] >= 4 and s["camera_trigger_x"] >= 20 and s["wait_state"] == "waiting" for s in overshoot)

    # Identified boss reassignment uses object_roster_idx.
    g = states([record(kind=5, obj=8)])
    assert any(s["slots"][0]["alive"] and s["slots"][0]["roster_index"] == 8 for s in g)
    print("runtime Spawn_Play mini-fixtures PASS")


if __name__ == "__main__":
    raise SystemExit(main())
