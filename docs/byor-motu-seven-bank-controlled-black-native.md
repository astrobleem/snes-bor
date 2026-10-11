# Seven-bank native peak proof on black

A generic bounded reservation search moves the three pieces using bank 3 to
other banks. It exhaustively checks 343 whole-piece assignments; 210 satisfy
every bank's fifteen-color scanline capacity. All 2,751 opaque source pixels
and 204 RGB555 identities remain exact. This preserves source SCREEN on black
only; authored underlays and alpha compatibility remain unresolved.

The admitted integer cache has sixteen peak writes, 231 total writes and
two-line prefetch. Independent physical packing admits four ranges and a
344-clock peak. A bounded joint bank/cache search returning UNKNOWN is also
retained without an infeasibility claim.

Native execution using the frame-exact Mesen build passes four complete fields,
zero pixel mismatches, zero unsafe high commits, exact CGRAM/CHR/OAM identity
and zero IRQ context faults. The existing production NMI services a 2,814-byte
test queue; this excludes live production VRAM leases and audio contention.
Code is injected outside bank zero.

Generic retiling keeps the exact pixel bank, slot and word identities while
reserving the player's 33 objects and full per-line geometry. The effect drops
from 107 to 40 objects. Combined reservation peaks are 73 objects, eighteen
sprites and 34 tile slivers. Its independently replayed palette packets remain
unchanged. A second native effect-only probe passes with this legal 8/16 size
pair. Reservation is geometry evidence, not concurrent palette/layer admission.

The compact receipt and gzip retain schedules and bounded native observer
traces; representative screenshots are adjacent. Three bank-reservation and
seven retiling tests pass. All seventeen protected tracked hashes match.
NO color reduction is applied. This is not authored peak or MOTU certification.
