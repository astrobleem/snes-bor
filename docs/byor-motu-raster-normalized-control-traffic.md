# Source-exact window normalization and measured control traffic

The generic control normalizer derives gating constraints from visible upper
OBJ-bank pixels. It preserves their exact outputs against the source underlay,
keeps palette words, indices, dimensions and fixed OAM banks unchanged, and
checks the entire viewport against the source composite. Unobserved coordinates
and rows can retain controls. A failed normalization keeps the verified
original descriptor rather than changing pixels.

For the authored peak, fixed positive windows need the original inverted form
on row 153. Fixed negative windows fit every required row: two inverted windows
combined with AND keep WOBJSEL at `$F0` and WOBJLOG at `$04`. The complete output
hash remains `4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
No palette word or source color is reduced.

Native transport tests expose the required CPU cost. Writing every control
field each row misses deadlines at a 344-clock palette span. Changed-field
updates with positive-window normalization still miss some deadlines. Constant
negative-window selection sustains 328 clocks with ordinary absolute count
stores. An explicitly idle private executor using direct page `$4300` for DMA
count setup then sustains **344 clocks with control traffic included**.

Five complete fields (12--16) have zero viewport pixel mismatches, unsafe CGRAM
commits, packet/word identity faults, register-sequence faults, OBJ overflow or
IRQ/NMI context faults. The actual production NMI service completes its
2,814-byte queue transfer. First commits are 1096--1104, largest packet data is
44 bytes, peak IRQ entry-to-RTI cost is 1,186 clocks, and the latest observed
control write on the target visible line is at clock 444. All code remains in
nonzero ROM banks. DBR zero and direct page `$4300` are explicit private ABI
requirements; the default full-context path does not adopt them.

These native tests render the exact SCREEN result on black. OBJ math-layer
selection is explicitly disabled while the authored mode/window register
traffic is exercised. They prove sustained transfer and register traffic,
**not full authored raster alpha rendering**. Authored alpha arithmetic has
its separate static-row proof. Active audio, the source VM, SA-1 gameplay work,
streaming/frontpanel contention, concurrent actors and animated uploads remain
unadmitted.

The paired normalization/control-traffic receipts retain source and descriptor
hashes, the full normalized schedule and bounded successful/failed native
assembly and observers. Thirty-nine focused solver/control tests pass. The
width guard checks 9,825 labels with no violations or baseline entries. All
seventeen protected files retain their hashes. No PCM copies or color
reduction were applied.
