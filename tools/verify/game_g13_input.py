#!/usr/bin/env python3
"""Bounded G13 JOY1/JOY2 hardware edge-detector proof.

This is only the input boundary gate. It does not claim co-op gameplay.
Each port is driven independently through Mesen's existing set_input API;
the two six-byte state records are sampled after exact one-frame polls.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (exact_input_edge, open_session, pasm_constant_in,
                      read_block, run_frames_exact)  # noqa: E402

INPUT_SRC = 'src/core/input.pasm'
P1_PRESS = pasm_constant_in(INPUT_SRC, 'Input_press_Addr')
P2_PRESS = pasm_constant_in(INPUT_SRC, 'Input2_press_Addr')
P1_RAW = pasm_constant_in(INPUT_SRC, 'Input_last_raw_Addr')
P2_RAW = pasm_constant_in(INPUT_SRC, 'Input2_last_raw_Addr')


def word(data, off=0):
    return data[off] | (data[off + 1] << 8)


def state(m, base):
    raw = read_block(m, base, 32)
    return {"press": word(raw, 0), "trigger": word(raw, 2), "old": word(raw, 4)}


def main():
    with open_session(__file__) as m:
        run_frames_exact(m, 60)
        # Enter the same active character-selection/gameplay path used by
        # the accepted G7 controls; the title/demo shell does not poll the
        # controller state we are proving.
        m.set_input(m.BTN_SELECT, 10)
        run_frames_exact(m, 40)
        exact_input_edge(m, 0, 2, port=0)
        exact_input_edge(m, 0, 2, port=1)

        m.hold_input(m.BTN_X, port=0)
        run_frames_exact(m, 1)
        p1 = state(m, P1_PRESS)
        p2 = state(m, P2_PRESS)
        print(f"P1_X_EDGE raw1={word(read_block(m, P1_RAW, 32)):#06x} raw2={word(read_block(m, P2_RAW, 32)):#06x} p1={p1} p2={p2}")
        m.release_input(port=0)
        assert p1["press"] & 0x0040
        assert p1["trigger"] & 0x0040
        assert not (p2["press"] & 0x0040)
        assert not (p2["trigger"] & 0x0040)

        exact_input_edge(m, 0, 2, port=0)
        m.hold_input(m.BTN_A, port=1)
        run_frames_exact(m, 1)
        p1 = state(m, P1_PRESS)
        p2 = state(m, P2_PRESS)
        print(f"P2_A_EDGE raw1={word(read_block(m, P1_RAW, 32)):#06x} raw2={word(read_block(m, P2_RAW, 32)):#06x} p1={p1} p2={p2}")
        m.release_input(port=1)
        assert not (p1["press"] & 0x0080)
        assert not (p1["trigger"] & 0x0080)
        assert p2["press"] & 0x0080
        assert p2["trigger"] & 0x0080
        print("G13 JOY2 BOUNDARY: PASS")


if __name__ == "__main__":
    main()
