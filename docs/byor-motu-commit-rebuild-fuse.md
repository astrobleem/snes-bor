# MOTU copy/recount fusion alone: not accepted

The optional 825-byte publication helper fused the committed-map copy and
reference recount. Epoch-3 post-map time fell from 453,628 to 340,216 master
clocks (25.0011%). All eight cases captured 666 exact fields and 38,191,104
RGB555 pixels, with no ownership, resource or unsafe-PPU faults.

The unchanged strict timing gate rejected five aborted transactions: early
added 134 clocks, READY 38, partial 82, stale 46, and insufficient-capacity 4.
Their field counts did not change. The candidate was not promoted, and no
`commit-rebuild-fuse-receipt.json` pass receipt exists. The inherited REF
receipt is narrower correctness evidence and does not override this rejection.

The frozen negative result is
[`receipts/byor-motu-commit-rebuild-fuse.json`](receipts/byor-motu-commit-rebuild-fuse.json).
Raw eight-case inputs are sealed under `out/byor-motu-commit-rebuild-fuse-v1`.
The first incomplete 48-field capture, successful repeat pilot, host-frame
diagnostics, reviews, and unchanged baseline controls are retained under
`out/byor-motu-commit-rebuild-fuse-integration-v1`.

The repeat used an identical ROM and observer script with a candidate-only
host deadline. Exact remaining frame counts, response continuity, no overshoot,
paused completion, pixel checks and measured ROM timing gates remain strict.
The incomplete capture is not acceptance evidence. Global copy/recount write
interleaving changes are scoped to the fixture's exclusive publication owner;
this experiment makes no production-concurrency or complete-game claim.
