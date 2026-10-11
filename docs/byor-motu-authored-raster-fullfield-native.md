# Full authored frame execution harness

The private raster harness now binds a source-derived static BG1 underlay and
an exact subscreen-additive OBJ schedule. It independently replays every source
output over that underlay before assembly. BG assets live in separate private
ROM banks, and all new code remains outside bank zero. The unchanged controlled
fixture compiles to identical ROM bytes against commit `8c2d8dd`:
`aa582edcd169f230e14805579d8c10413af84e4fb9be80c9eb9e532c75922198`.

Native execution observes actual CGRAM contents after each active palette IRQ,
including retained slots and the lower background palette. This is distinct
from observing intended `$2121` addresses and `$2122` data. The proof also checks
OAM identity, overflow flags, layer register writes, underlay VRAM and palette
identity, packet sequence and a complete viewport of rendered RGB555 pixels.

The authored first HBreath frame passes as a positive harness control. Its
palette is initialized during blanking, with no per-line palette traffic.
There are four complete observer fields and one full 57344-pixel comparison,
with zero mismatches and no OBJ overflow. The source RGB555 viewport hash is
`8cdaab5de7e9cbb1897468bff6174120f9183052911454c61bf9f70437b0652a`.
Alpha remains exact BOR4086 RGB8 SCREEN followed by RGB555 conversion. This
does not admit the peak frame's raster transfer or concurrent actor routing.

The peak-frame word-bank frontier has a complete logical cache schedule with
21 writes per line. Its requested write trace has a 440-clock optimistic bank
bound even after all 40320 eligible bank permutations. The strict 345-clock
fixed-assignment cache search reports INFEASIBLE with the same words and banks;
that result does not cover other bank assignments or geometries.

A bounded fixed-slot search emits an independently replayed physical schedule
with a 776-clock offline peak. Native execution rejects this construction:
816 observed transfer clocks, 1562 clocks of IRQ service against a 1364-clock
scanline, 2914 unsafe high commits, 20921 physical CGRAM byte mismatches across
195 checks, and 33166 rendered pixel mismatches. Register routing and OBJ
overflow checks still pass. The native data demonstrates a transport failure
of this complete construction, not a universal raster failure.

Two focused compile tests pass, the width audit has 9825 labels and zero
failures, and all 17 protected file fingerprints match. Source contexts that
do not reproduce every expected alpha pixel fail before assembly. Combining
the authored underlay with production NMI VRAM traffic currently fails
explicitly because that lease is not implemented; there is no production
runtime admission. No color reduction, BG fallback or MOTU completion claim
is made.

The reports, complete observer traces, assembly and offline schedules are
retained in `docs/receipts/byor-motu-authored-raster-fullfield-native.json.gz`.
The retained first-frame PNG is a positive control, not a peak-frame raster
certification image.
