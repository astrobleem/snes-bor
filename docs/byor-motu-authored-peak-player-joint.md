# Authored peak effect and player: joint source demand

The nominal source pose pairs He_ManB freespecial4 frame 6 at (80,220,0) with
HBreath idle frame 11 at (98,220,93). The
[source parent timeline](byor-motu-authored-breath-parent-pose-timing.md) derives
their intersection at nominal ticks 114–120. Successful allocation, startup at
birth, fixed positions and an uninterrupted animation remain assumptions;
runtime weapon selection and gameplay reachability are not certified.

The new generic literal-demand builder includes every final visible actor pixel,
including opaque RGB555 zero. It derives banked row palettes and fixed-bank
eight-pixel masks, retains source metadata, and independently decodes the
indices against the palette trace. All 57,344 source output pixels replay;
5,513 foreground pixels remain after source occlusion. No actor palettes are
reserved or omitted. The source output hash is
079de2d8ffbbe72c9779904f3a0ef2fe6d0283331dd49838a79ed2cc7e889f45.

There are 635 distinct foreground RGB555 output colors and a 75-color peak
scanline. He_ManB contributes 2,762 visible pixels, 31 output colors and a
10-color peak line. HBreath contributes 2,751 visible pixels, 606 output colors
and a 65-color peak line. These are final source-context colors after exact
RGB8 SCREEN compositing, distinct from HBreath's original 204-color source
frame and 54-color raw-source peak line. No color reduction or alpha adaptation
is applied.

The literal input is deliberately not a hardware admission: it has 264 OAM
entries and 49 sprites/slivers at peak. That construction fails those limits.
Its row reindexing is not optimized liveness and supplies no minimum bandwidth
bound. A separate source-pixel-exact aligned 8/16 geometry cover uses 39 objects,
9 sprites and 17 slivers; bank assignment and operand encoding remain open.

The joint geometry/bank/mode/window/cache search uses that cover and both actors'
actual visible demand, rather than a player geometry reservation. At the
353-clock ideal bank-partition gate it returns UNKNOWN after 122.524 seconds:
606,815 variables, 1,103,105 constraints and 44,104 direct mode/window coverage
clauses. Its complete cover examines all 32,768 operands against 7,776 tagged
contexts and retains 1,642 coverage identities, including 49 input seeds. This
is no integer witness and no infeasibility certificate. Physical slots, native
timing, live composition and full Demo admission remain unproven.

The bounded receipt reopens the actual source archive, rebuilds the demand,
replays every source row-context hash and independently checks geometry cover
ownership. Ninety-five focused tests pass. Production static presentation and
bank-zero code remain unchanged; all 17 protected tracked fingerprints match.
No PCM copies. [Joint source receipt](receipts/byor-motu-authored-peak-player-joint.json).
