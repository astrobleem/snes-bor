# Automatic DMA cursors and preserved interrupt context

An isolated native component now publishes changing palette payloads together
with five-byte positive-window descriptors while preserving the interrupted
CPU state. Prepared IRQ DMA owns channels 1..3 for two palette ranges and their
address change, then channels 6..7 for bounds and math mode. Channel 0 retains
the 73-row dummy APU HDMA stress. NMI resets the four automatic data cursors.
Palette transfers start at row 75; window transfers run on all visible rows.

Every palette row changes the payload. Each of the 149 admitted rows writes
19 RGB555 words / 38 CGRAM data bytes plus one CGRAM address byte. Window DMA
adds five data bytes: the combined packet is 44 transferred bytes over five
channels. Cursor maintenance uses DMA address registers, leaving the caller's
X register available. IRQ saves A, changes widths and clears decimal mode,
and relies on hardware-stacked P for exact return. X, Y, DBR and direct page
are untouched. New fixture code lives in bank 1; bank-zero production code is
not changed.

At timer 81, three complete observed fields contain 447 palette packets and
8,493 high-byte commits with zero unsafe commits. The maximum high-commit span
is 320 master clocks within the measured 356-clock CGRAM window. All 57,344
RGB555 pixels, OAM bytes and final CGRAM words match independent expectations.
Window modes affecting visible objects finish by H=132. The measured IRQ
entry-to-RTI span peaks at 1,104 clocks; hardware entry, vector gateway and RTI
execution are excluded from that span. There are 786 exact register-return
observations in the baseline case.

Three additional bounded fixtures test interrupted accumulator/index widths
8/16, 16/8 and 8/8 with decimal mode set. Each preserves the full accumulator
including its hidden high byte, the appropriate X/Y values, nonzero DBR and
direct page, stack position and final status flags. Each also matches all
pixels, palette words and OAM bytes with zero unsafe commits.

The earlier CPU-window handler with explicit register preservation and a WRAM
cursor fails: its service interval overruns successive IRQ periods and palette
commits drift through active display. Timer 126's long-IO version retains 405
packets, 6,244 unsafe commits and 44,990 pixel mismatches. Those failures reject
that fixture handler, not raster presentation. The DMA-cursor route removes
the required cursor load/store and X save/restore from each IRQ.

This remains synthetic geometry and a restricted positive-window family,
rather than HBreath source SCREEN alpha or a valid source bank/slot schedule.
The native interrupted CPU is a controlled loop. Production instruction
latency, NMI/audio leases, live source upload contention, variable transfer
lengths, CGRAM destinations and authored concurrency still need admission.
No color reduction or production presentation change has been applied.

[Bounded native reports and hashes](receipts/byor-motu-dma-window-context-component.json).

## Full window controls and per-word observer

The follow-up general-mask fixture uses all seven descriptor bytes, including
selection and logic for inverted masks. Channels 4 and 5 publish those two
additional registers after the palette transfers. The combined packet now has
46 data bytes over seven DMA channels, with channel 0 retained for audio HDMA.
At timer 60 it still matches every pixel, palette word and OAM byte, with 8,493
safe high commits and a 320-clock high-commit span. Descriptors over visible
objects finish by H=168. IRQ entry-to-RTI peaks at 1,218 clocks, excluding
hardware entry, vector gateway and RTI; actual production latency remains open.

The new palette ranges begin at opaque slots 1, rather than including unused
transparent words. All 19 words are opaque slots and transparent slots stay
zero. An independent observer records and checks the exact destination and
RGB555 value of every word in all 447 packets. The 8/8 decimal-context variant
also passes. Status verification reads hardware-stacked P immediately before
RTI; a final paused CPU snapshot can be inside a handler and is retained only
as diagnostic state. Earlier positive-window receipts describe their historical
fixtures, which included two unused transparent words among 19 data words.

[General-mask and word-identity receipt](receipts/byor-motu-general-dma-window-word-identity.json).
