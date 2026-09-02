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
    assert re.search(r"mov A, #\$ff\s+mov echoDirty, A", init)
    assert re.search(r"mov A, #\$ff\s+mov sfx_oneChannelSfxId\+0, A", init)
    assert re.search(r"mov sfx_oneChannelSfxId\+1, A", init)

    # Verify actual hardware write sites, not the nearest textual occurrence
    # of a DSP register constant. The normal firewall prepares Y and reloads
    # A with the register address immediately before movw DSPADDR, YA.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"mov A, #(DSP_(KON|KOFF|NON|PMON|EON))\b", line)
        if not m:
            continue
        register = m.group(1)
        window = lines[max(0, i - 14):i + 3]
        joined = "\n".join(window)
        assert "movw DSPADDR, YA" in "\n".join(lines[i:i + 3]), f"{register} is not a final DSP write"
        proc_start = max((j for j in range(i + 1) if re.match(r"\s*\.proc\s+", lines[j])), default=0)
        stream_owned = "stream_receive_frame" in lines[proc_start].lower()
        if stream_owned and register == "DSP_KON":
            continue
        mask = re.search(r"and A, #STREAM_VOICE_MASK", joined)
        safe_constant = re.search(r"mov Y, #STREAM_VOICE_MASK", joined) or re.search(r"mov Y, #0", joined)
        assert mask or safe_constant, f"{register} final value is not reservation-safe"
        if mask:
            assert re.search(r"and A, #STREAM_VOICE_MASK\s+mov Y, A", joined), \
                f"{register} masked value is not transferred to Y"

    pmon = between(text, "; Write pmonShadow to PMON", "mov A, noiseLock")
    assert re.search(r"and A, #STREAM_VOICE_MASK\s+mov Y, A\s+mov A, #DSP_PMON\s+movw DSPADDR, YA", pmon)
    assert "hardware-write firewall" in text
    assert "musicSfxChannelMask" in text
    print("TAD VOICE-0 RESERVATION STATIC: PASS")

if __name__ == "__main__":
    main()
