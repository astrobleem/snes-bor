#!/usr/bin/env python3
"""Run the Gate 0 JSON through a tiny host reference VM and verify its result."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent

def i32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value

def main() -> int:
    fx = json.loads((ROOT / "gate0_program.json").read_text(encoding="utf-8"))
    slots = [dict(s) for s in fx["initial_slots"]]
    code = fx["instructions"]
    ip = 0
    status = "RUNNING"
    error = 0
    trace: list[list[int]] = []
    limit = 100

    while status == "RUNNING" and limit:
        limit -= 1
        if not 0 <= ip < len(code):
            status, error = "FAULT", 0x000D
            break
        ins = code[ip]
        op = ins["opcode"]
        trace.append([ip, op])

        if op in (0, 1, 2, 33, 34, 35, 39, 41, 42, 44, 45, 47):
            ip += 1
        elif op == 16:  # ADD; Gate 0 supports INTEGER only.
            left, right = slots[ins["b"]], slots[ins["c"]]
            if left["type"] != "VT_INTEGER" or right["type"] != "VT_INTEGER":
                status, error = "FAULT", 0x0005
                break
            slots[ins["a"]] = {"id": ins["a"], "type": "VT_INTEGER",
                               "value": i32(left["value"] + right["value"])}
            ip += 1
        elif op == 26:  # EQ; Gate 0 supports INTEGER only.
            left, right = slots[ins["b"]], slots[ins["c"]]
            value = int(left["type"] == right["type"] and left["value"] == right["value"])
            slots[ins["a"]] = {"id": ins["a"], "type": "VT_INTEGER", "value": value}
            ip += 1
        elif op == 36:  # Branch_FALSE
            cond = slots[ins["b"]]
            truth = cond["type"] == "VT_INTEGER" and cond["value"] != 0
            ip = ip + 1 if truth else ins["a"]
        elif op in (20, 21):
            ip = ins["a"]
        elif op == 15:
            status, error = "FAULT", 0x0003
        elif op == 43:
            status = "DONE"
        elif op == 7:
            status, error = "FAULT", 0x0002
        else:
            status, error = "FAULT", 0x0010

    if not limit and status == "RUNNING":
        status, error = "FAULT", 0x000F

    got = {"status": status, "error": error, "executed_trace": trace, "slots": slots}
    expected = fx["expected"]
    if got != expected:
        print("Gate 0 mismatch")
        print(json.dumps({"expected": expected, "got": got}, indent=2))
        return 1
    print("OK: Gate 0 reference result and complete IP/opcode trace match.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
