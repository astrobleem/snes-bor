# CGRAM split-packet native budget

The isolated HIRQ fixture now supports two data ranges using DMA channels 5 and
7, with channel 6 writing one CGRAM destination byte between them. The first
range starts at word 128, the second at word 192. Each descriptor is prepared
before transfer; IRQ code restores all three transfer counts and sets the first
address. The intermediate address channel uses fixed-source mode. Production
code and bank zero are untouched. The fixture main loop still does not require
full production CPU register preservation.

With the existing 73-row dummy mode-4 APU HDMA pattern and timer 155, the late
rows 75–223 produce 447 complete packets across three fields. A 38-byte split
(24+14 data bytes plus one address byte) has zero unsafe data writes. All 447
observed address/data-range sequences match the compiled destinations and sizes.
At 40 bytes (24+16 plus one address byte), 318 data writes fall outside the safe
window over 447 complete packets. Both first 100-write samples show zero unsafe
writes. Full-packet observation is decisive; the bounded sample is insufficient.
Earlier timer-166 and timer-149 40-byte trials also fail, but they do not prove
that every possible IRQ timer or handler must fail.

The previously tested contiguous 42-byte burst and this safe split 38-byte
burst are different mechanisms and costs. A 20-color pooled candidate cannot
be admitted from its color count alone: bank/slot placement, padded destination
spans, setup and destination switches must all fit. No universal maximum or
raster rejection is claimed. These isolated probes do not certify production
TAD audio protocol, NMI contention, source pixels, or actual source OAM rendering.

No PCM copies or giant logs. All 17 protected tracked hashes match.
[Native split-packet receipt](receipts/byor-motu-cgram-split-packet-native.json).
