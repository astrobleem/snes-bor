# Optimized authored control transport

The private native compiler now skips zero-count DMA channels, groups equal
count values under one load, writes zero controls with STZ and shares the
eight-bit accumulator interval between next-line count preparation and
control-byte writes. Word controls still precede byte controls. Palette packet
contents, destinations and register-event order remain independently observed.
These changes address the measured full-handler overrun, not just packet cost.

With the exact authored BR12 window/mode traffic, the seven-bank black-matte
physical packets and a 2,814-byte production NMI test queue, native execution
passes five complete fields. There are zero unsafe high commits, zero pixel
mismatches, exact CGRAM/CHR/OAM identity and zero IRQ context faults. Peak
packet span is 344 clocks; first highs lie at H=1096..1104. The complete handler
phase trace is retained compressed. The earlier failing pipeline receipt is
retained separately; it has not been relabeled.

This establishes a 344-clock transport witness for this delta-control traffic.
Color-math layer selection is disabled: exact authored alpha rendering, other
frame control patterns, concurrent gameplay, live VRAM leases and audio
contention are not admitted. Four focused native compiler tests and the
9,825-label width audit pass. All seventeen protected hashes match.
No code is added to bank zero. NO color reduction or alpha adaptation is used.
