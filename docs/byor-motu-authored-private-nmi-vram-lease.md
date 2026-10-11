# Authored private viewport with production NMI

The isolated fixture can now bind an authored underlay while running the
production NMI service. A private allocator uses exact uploaded VRAM ranges;
it does not lease the live runtime's background streaming resources. For
GUILE2 the BG graphics use 38,144 bytes, the map occupies 45,056..47,104, and
OBJ graphics begin at 49,152. A 2,814-byte queue upload leases 38,144..40,958.
Queue destinations use byte addresses, as required by core/dma.pasm.

The fixture initializes the production shadows for BG mode, screen selection,
tilemap and vertical scroll. Source runtime code is unchanged. Every queue
upload is observed at its leased destination; the final VRAM snapshot also
matches the exact source payload. The existing per-NMI observer already
verified payload bytes at zero; this change moves that check with the lease.

The authored first HBreath frame passes three complete fields, with zero
pixel mismatches, complete BG/OBJ graphics, palette and OAM identity, 940 IRQ
checks with zero faults, and four NMI checks with zero faults. NMI completes
within VBlank; peak entry-to-RTI is 37,938 master clocks. Alpha is the exact
BOR4086 RGB8 SCREEN result projected to RGB555, using native subscreen ADD.
This frame has no noninitial palette transfers and is not the peak proof.

The prior raw peak black-underlay transport fixture also passes three fields
with source-authored window/mode traffic and production NMI: 344-clock peak,
first high commits at 1096..1104, zero unsafe commits, zero pixel errors and
705 IRQ checks with zero faults. The stronger final payload check passes.
Its math-layer selection remains disabled, so it does not prove authored
peak alpha. Six compiler tests pass. No code is added to bank zero.

The initial development failure used a word address in the byte-addressed
queue and corrupted BG data; the second failure preserved all pixels but
still observed the old queue destination. Both failures are recorded. The
corrected native result passes both payload and underlay checks.

Peak authored raster timing, concurrent actors, live leases, source VM/audio
contention and MOTU gameplay remain open. NO color reduction or alpha
adaptation is applied.
