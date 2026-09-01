#!/usr/bin/env python3
"""Check the source-level voice-0 reservation invariants."""
from pathlib import Path
import re

SOURCE = Path(r"E:\gh\terrific-audio-driver\audio-driver\src\audio-driver.asm")

def between(text, start, end):
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]

def main():
    text = SOURCE.read_text(encoding="utf-8")
    init = between(text, "; Reset bit-masks", "; Pop ESA from the stack")
    assert "mov A, #$ff" in init
    assert "mov echoDirty, A" in init
    assert "and A, #STREAM_VOICE_MASK" not in init
    assert "mov A, #$ff\n    mov sfx_oneChannelSfxId+0, A" in init
    def final_writes(register):
        starts = [m.start() for m in re.finditer(r"mov A, #" + register + r"\b", text)]
        assert starts, f"no production setup for {register}"
        for start in starts:
            previous = text.rfind("movw DSPADDR, YA", 0, start)
            tail = text[previous + len("movw DSPADDR, YA"):]
            write = tail.find("movw DSPADDR, YA")
            assert write >= 0, f"{register} setup has no DSP write"
            block = tail[:write]
            mask_text = "and A, #STREAM_VOICE_MASK"
            if mask_text not in block:
                safe_constant = "mov Y, #STREAM_VOICE_MASK" in block or "mov Y, #0" in block
                safe_variable = register == "DSP_KOFF" and "and A, musicSfxChannelMask" in block
                assert safe_constant or safe_variable, f"{register} final value is not reserved-safe"
                continue
            mask = block.rfind(mask_text)
            assert block.find("mov Y, A", mask) >= 0, f"{register} mask not transferred to Y"
    for label in ("DSP_KON", "DSP_KOFF", "DSP_NON", "DSP_PMON", "DSP_EON"):
        final_writes(label)
    pmon = between(text, "; Write pmonShadow to PMON", "mov A, noiseLock")
    assert pmon.index("and A, #STREAM_VOICE_MASK") < pmon.index("mov A, #DSP_PMON")
    assert pmon.index("mov A, #DSP_PMON") < pmon.index("movw DSPADDR, YA")
    assert "hardware-write firewall" in text
    assert "musicSfxChannelMask" in text
    print("TAD VOICE-0 RESERVATION STATIC: PASS")

if __name__ == "__main__":
    main()
