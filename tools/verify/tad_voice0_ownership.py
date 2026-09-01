#!/usr/bin/env python3
"""Targeted live proof for the build-time TAD voice-0 firewall.

The fixture writes distinctive values to voice 0 after TAD startup, then
drives the existing real G11 landed-hit path.  It samples the DSP state on
every frame and fails if normal TAD changes voice 0 or emits a final global
voice mask containing bit 0.  Voice 6/7 key-on observations are collected
from the same real SFX activity.
"""
import argparse
import sys

sys.path.insert(0, "tools/verify")
from _harness import open_session, exact_input_edge  # noqa: E402
from game_g11_sfx import (  # noqa: E402
    Entity1, PlayerEntity, CHAR_HIT_STUN, CHAR_HP, SFX_QUEUE_ADDR,
    SFX_HIT_ID, overlap,
    boot_and_warm, write_u8,
)


DSP_VOICE0 = list(range(8))
DSP_KON = 0x4C
DSP_KOFF = 0x5C
DSP_NON = 0x3D
DSP_PMON = 0x2D
DSP_EON = 0x4D
GLOBAL_MASKS = {
    "KON": DSP_KON,
    "KOFF": DSP_KOFF,
    "NON": DSP_NON,
    "PMON": DSP_PMON,
    "EON": DSP_EON,
}


def dsp_read(m, address):
    return m.read_memory("spcDspRegisters", address, 32)[0]


def dsp_write(m, address, value):
    m.write_memory("spcDspRegisters", address, f"{value & 0xff:02X}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-both-sfx-voices",
        action="store_true",
        help="require the fixture-only two-channel audio-project variant",
    )
    args = parser.parse_args()
    sentinel = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
    with open_session(__file__) as m:
        boot_and_warm(m)
        for address, value in zip(DSP_VOICE0, sentinel):
            dsp_write(m, address, value)

        # Start from a clean real landed-hit setup.  No SFX queue or DSP
        # register is faked; only the safe voice-0 sentinels are fixture state.
        write_u8(m, PlayerEntity + CHAR_HIT_STUN, 0)
        write_u8(m, Entity1 + CHAR_HP, 100)
        overlap(m, Entity1)

        seen_sfx_voices = set()
        key_on_history = []
        global_history = {name: [] for name in GLOBAL_MASKS}
        voice_history = []

        for frame in range(90):
            # The production project currently has one resident SFX asset.
            # Queue that real generated effect twice while its first copy is
            # active so both TAD physical SFX paths are exercised.  This is
            # fixture-only timing scaffolding, not a shipping policy change.
            if frame in (0, 1):
                write_u8(m, SFX_QUEUE_ADDR, SFX_HIT_ID)
            exact_input_edge(m, m.BTN_Y, 1)
            m.pause()
            state = m.get_audio_state()
            key_on = state["dsp"]["keyOn"]
            key_on_history.append(key_on)
            for voice in (6, 7):
                if key_on & (1 << voice):
                    seen_sfx_voices.add(voice)
            voice_history.append([dsp_read(m, address) for address in DSP_VOICE0])
            for name, address in GLOBAL_MASKS.items():
                global_history[name].append(dsp_read(m, address))
        m.release_input(0)

        bad_voice = [row for row in voice_history if row != sentinel]
        if bad_voice:
            raise SystemExit(f"FAIL: voice-0 sentinel changed: {bad_voice[:3]}")
        bad_masks = {
            name: [value for value in values if value & 1]
            for name, values in global_history.items()
        }
        bad_masks = {name: values for name, values in bad_masks.items() if values}
        if bad_masks:
            raise SystemExit(f"FAIL: normal TAD emitted voice-0 mask bits: {bad_masks}")
        if args.require_both_sfx_voices and seen_sfx_voices != {6, 7}:
            raise SystemExit(
                f"FAIL: observed TAD SFX voices {sorted(seen_sfx_voices)}; "
                f"keyOn={[hex(value) for value in key_on_history if value & 0xC0]}"
            )

        print("TAD VOICE-0 OWNERSHIP LIVE: PASS")
        print(f"voice0_sentinel_frames={len(voice_history)}")
        print(f"voice6_voice7_keyon={sorted(seen_sfx_voices)}")
        print("production_sfx_policy=one_channel" if seen_sfx_voices == {7}
              else "production_sfx_policy=two_channel_fixture")
        print("global_mask_bit0_history=KON:0 KOFF:0 NON:0 PMON:0 EON:0")


if __name__ == "__main__":
    main()
