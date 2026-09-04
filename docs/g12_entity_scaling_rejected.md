# G12 entity scaling experiment — rejected

This experiment is preserved as forensic evidence only. It is not a
production claim and must not be revived as the six-entity implementation.

## Measured resource headroom

- Six `CHAR_ZP_LEN=133` windows use 798 bytes in the existing 3072-byte OOP
  RAM arena.
- Six four-column animation slices use 192 of the 256 available 8x8 OBJ
  tile columns in the existing lower OBJ band.
- Six actor palettes use six of the eight SNES OBJ palette slots.
- OAM capacity (128 entries) is not the limiting resource for the current
  one-entry-per-character render shape.

## Candidate result

The temporary candidate created six real OOP objects and, after 600 frames,
showed six live entity windows with independent positions, animation state,
palette slots 0..5, and tile columns 0..5. NMI continued to advance with no
observed overrun in the short probes.

It was rejected. The extra-slot spawn path was only a partial regular-enemy
landing path; player collision, complete prop/boss bookkeeping, stage-win
accounting, and slot-reuse semantics were not generalized for slots 4/5.
The candidate also failed the established phase5 regression during its boot
settling window. No production six-entity support is claimed.

The existing single-buffer animation transport was not changed. Residency and
grouped two-buffer transport remain rejected research and are not revived by
this note.
