# Authored peak effect and player: joint source demand

An alternative source-only geometry family contains eighteen 32-pixel parents
with legal 8-pixel children, using one global 8/32 OBJ size pair for both actors.
The exact shared-mode/window frame-word search returns FEASIBLE after 90.591
seconds: 113 objects, 19 sprites and 34 tile slivers. This includes the player's
palette and layer demand. Compilation independently replays all 57,344 source
viewport pixels and binds OBJ size mode 1 to the new geometry; schedule hash
4e5dcfbde4c9bcd2487bfa66ef84e79d681ff20308b7fbdfe0e81ab3b6e56c6c.
Greedy liveness needs 52 writes. The checked class-pooled lower bound is 42
writes with zero primal and dual residuals, requiring at least 656 clocks
between high-byte commits before setup. This rejects this selected encoding
even after relaxing bank assignment and geometry. It does not reject alternate
exact encodings or the 8/32 geometry family. No native timing or reachability
admission is inferred.

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

That first search permits cross-actor rectangle ownership where bounds overlap;
it is a necessary relaxation, not preservation of per-actor mask identity. The
source-bound CLI now verifies each input pixel's actor against the reopened
source and limits candidate ownership to the same actor. Explicit fused inputs
must reproduce their source owner-provenance proof. Compilation independently
rejects actor changes even when the final colors match. The actor-preserving
joint trial remains UNKNOWN after 122.313 seconds, with 603,703 variables and
1,089,101 constraints. No source identity shortcut or native admission is used.

Ignoring cache and transfer constraints produces an actor-preserving bank/mode/
window geometry witness after 30.461 seconds: 80 objects, 17 sprites and 34
slivers. The generic compiler replays every source output pixel, retains actor
identity and emits palette schedule hash
a0985f5f682b77c690302482cb866cbd5216393c3b3a5ff255747bdd6eef1b96.
Greedy residency reaches 53 writes; its independently validated fractional
fixed-bank/fixed-word cache lower bound is 45.625 with zero primal violation
and dual residual. This particular encoding therefore needs at least 46 writes,
or 720 clocks between high-byte commits before range overhead. It fails the
measured window. Other exact encodings and bank assignments remain open; the
geometry witness is not full concurrent native admission.

The bounded receipt reopens the actual source archive, rebuilds the demand,
replays every source row-context hash and independently checks geometry cover
ownership. Ninety-seven focused tests pass. Production static presentation and
bank-zero code remain unchanged; all 17 protected tracked fingerprints match.
No PCM copies. [Joint source receipt](receipts/byor-motu-authored-peak-player-joint.json).
