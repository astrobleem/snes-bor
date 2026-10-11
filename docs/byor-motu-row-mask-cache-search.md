# Source-exact row masks with fixed OAM banks

The authored-background peak HBreath frame has an exact fixed-bank encoding
using 33 OAM entries, 10 sprites and 20 tile slivers. Its initial fixed-bank
cache LP lower bound is 24 writes. Bank balancing preserves every input pixel
and lowers the interval bound to 22.142857. Pooling banks within their legal
math classes gives 14.428571 for the same encoded words. These results reject
the particular fixed-bank encodings at 21 writes, and leave bank assignment open.

The generic cache solver can now split equal words on different source rows
into separate pixel masks. Each resulting OAM entry retains one bank for its
whole rectangle. No OAM bank changes between scanlines. The compiler replays
each source pixel, counts every mask as a complete legal rectangle, enforces
128 objects / 32 sprites / 34 slivers, and independently rebuilds slot indices.
Whole-piece and whole-word choices remain the default paths.

Row choices use shorter redundant interval cuts to reduce the auxiliary graph;
the exact per-bank residency, writes and 15-slot capacity constraints remain.
An enclosing full-palette range proves that the ideal transfer-flow graph is
redundant only when the requested window exceeds a conservative 2104-clock
bound. Logical trials explicitly request 9999 clocks and claim no physical
admission. Bank-label ordering is applied only in that relaxed case when every
object permits its entire eligibility class. Physical-window trials retain
the bank labels and transfer constraints.

The SAT strategy now requests the no-LP subsolver explicitly. A bounded
32-line solver observer measured 704,082 branches, 32,833 conflicts and zero
LP iterations in the 90-second logical trial. That result is UNKNOWN. The
earlier default portfolio used 36,381 LP iterations in its nominal SAT trial.
Both outcomes are retained; neither is a hardware failure. The three-mask
physical-window trial is also UNKNOWN. Pinning complete saved cache intervals
is INFEASIBLE for that restricted construction. The four-mask trial returned
UNKNOWN after 120 seconds, with 548,207 branches and 367,025 conflicts.

The receipt retains the exact encodings, validated bounds and bounded solver
results. Thirty-five focused cache/rebuild tests pass. The width audit reports
9825 labels with zero failures, and all 17 protected tracked-file hashes match.
No production runtime or bank-zero code is changed. No color reduction is
applied. Authored-peak native transfer admission and MOTU completion remain open.

An optional row-mask path now uses the compact load-interval solver as well.
Required word identities are ORed per bank and row, and optional resident
lifetimes share a cumulative 15-slot capacity. Noninitial starts count against
the palette-write limit and require a visible use within the lookahead. Each
compiled mask retains a fixed bank, and the model counts its full rectangle
against all three hardware geometry limits. The independent rebuild and cache
materialization remain mandatory. Default whole-piece selection is unchanged.

The two-load-per-word/bank trial reduced the model to 51,056 variables and
110,690 constraints, made 1,899,884 branches and returned UNKNOWN after 120
seconds. Its reload cap restricts this family. No physical slot or transfer
admission is claimed. Thirty-seven focused interval/cache/rebuild tests and
the width audit pass; protected tracked hashes match. The supplemental receipt
retains both final four-mask and interval results. A 24-write diagnostic is
being tried to obtain a construction outside the current transfer target.
