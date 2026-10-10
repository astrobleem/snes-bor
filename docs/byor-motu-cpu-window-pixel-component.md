# Palette DMA plus CPU windows: native pixel component

The isolated combined fixture preserves all 57,344 RGB555 viewport pixels.
It draws 16 source-sized test objects in the legal 8/32 OBJ mode, using lower
and upper palette classes against a BG1 subscreen operand. Four positive-window
masks alternate each row; addition and halved addition alternate every four
rows. Independent RGB555 replay, all 544 OAM bytes and final 512 CGRAM bytes
match. Initial OBJ words differ from the DMA payload, so omitting palette
publication would fail the pixel oracle.

Prepared split DMA publishes 19 palette words through channels 5..7. Dummy APU
HDMA occupies channel 0 for 73 rows; palette publication starts at row 75,
before objects at y=80. This explicit admission interval avoids unsafe writes
while the early audio transfer is active. The fixed-control CPU descriptor
publishes four window bounds and the math mode after DMA. Timer 156 accounts
for the added admission check. Across three complete observed fields, 447
packets produce 8,493 high-byte commits, zero unsafe commits and a maximum
320-master-clock high-commit span. Descriptors overlapping visible objects
finish by H=302. The rendered pixel comparison independently validates their
effect on this fixture. Peak geometry is four sprites and 16 tile slivers.

Lua observer overhead requires bounded retries of single-frame advances.
Zero-advance timeout responses are retained as retries; three actual frame
advances and all 149 palette packets in each observed field are required.

This is a component proof: repeated palette payload, synthetic geometry, no
source HBreath schedule, source SCREEN alpha, authored scene, live camera,
production CPU register preservation, NMI or presentation lease certification.
The mixed-mode source solver remains open; the strengthened dual-simplex
180-second trial also reached its limit without a candidate or certified bound.
No color reduction was applied.

[Retained report and artifact hashes](receipts/byor-motu-cpu-window-pixel-component.json).
