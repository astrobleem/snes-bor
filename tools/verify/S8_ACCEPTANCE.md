# S8 acceptance receipts

This checker does not enable Normal or certify all-stage visual release. The
bounded campaign-flow/runtime completion is recorded separately in
`docs/bor_s8_normal.md`; the outstanding manual visual and feature-specific
gates below remain independent. Run only after the combined candidate has
finished publication and new receipts are available. The natural traversal
receipt may satisfy both natural playback and admission validation; ordinary
index-skipping routes cannot satisfy admission validation.

```powershell
python tools/verify/game_s8_acceptance.py --rom build/s8_candidate/bor.sfc --skip out/s8_final_skip.json --natural out/s8_final_natural_traversal.json --easy out/s8_final_easy.json --traversal out/s8_final_natural_traversal.json --output out/s8_final_acceptance_01.json
```

Use those report names when main runs the native harness, or substitute the
actual new receipt paths. Missing files fail explicitly. Output is create-only;
choose a new suffix rather than replacing any earlier receipt. Exit code 1
means release is still blocked, even when scoped route/admission gates pass.

## Gate inventory

| Gate | Binding and acceptance scope |
| --- | --- |
| Candidate identity | Every route receipt must match the actual selected ROM, sibling MSU, current main.sym, and campaign include SHA256. Rebuilt candidates invalidate historical receipts. |
| Actual source route | Compiler-derived 16 typed entries / 14 stages, physical IDs and order, separate authored next and runtime completion policy. JSON includes each entry's required receipts. |
| Native selection | Required cold startup, difficulty Normal selection, native first-entry and player-selector checks; no availability override. |
| Normal completion routing | All source next/direct and showcomplete-once checks; 6B → Rugal → 6C → Ending. |
| Natural scenes | Rugal 126 frames; Ending 1997 frames / four clip transitions, completion=1, skip=0, clean transport. |
| Skip scenes | Real skip/cleanup gates, skip=1, completion=0; immediate-skip requires the exact strict fence set. |
| Campaign completion | Entry transitions and Times delta, completion/continuation-once gates and TITLE dwell check. Raw dwell counter snapshots are not yet persisted by the producer. |
| Easy control | First three native clears must follow accepted-S7 completion flags, not Easy authored next flags. It does not certify full Easy or extra completion after Rugal. |
| All-spawn integration | Separate natural traversal receipt; fresh compiler plan, 614 initialized source identities and every packed control record in order. Source model paths, physical slot incarnation and delayed HP-write provenance checked. No combat-kill claim. |
| Stage visual commit | Candidate-matched committed/unblanked output for all 14 actual stages; entry-boundary screenshots do not suffice. Missing native receipt. |
| Frontpanel | Actual authored uses, including four-panel Normal 1A sequence motion. Implementation/allocation reports are not native motion receipts. Missing bound native oracle. |
| Timer / Time | Source Time pickup, timer reset/decrement/timeout and once-only effects. Missing feature-specific receipt binding. |
| Opponent HUD | Native P1/P2 hit target, source name/HP and committed HUD pixels. Missing feature-specific receipt binding. |
| Bounds / holes / water | Actual required source cases, actor lifecycle and native outputs. Missing feature-specific receipt binding. |
| Ramon / actor / item behavior | Admission identity is not moves, damage, pickup semantics or lifecycle equivalence. Missing feature-specific receipts. |
| Media / audio / manual acceptance | Source-generated media correctness, audible behavior and manual visual acceptance remain distinct from transport and track selection. |

## Diagnostic feature receipt input

`--feature-receipt FEATURE=PATH` can retain receipt path/hash and reject explicit
failures or missing candidate bindings. It cannot turn an arbitrary PASS into
feature acceptance: even a matching generic receipt is `UNBOUND_FEATURE_SCHEMA`
until its dedicated expected-case/native-measurement oracle is implemented.
Accepted keys are the names in `game_s8_acceptance.PENDING`.

Inspected historical receipts: `s8_bounds_native_02.json` is FAIL (source actor
identity); `s8_opponent_hud_02.json` contains a P2 damage assertion failure;
`s8_timer_linked_03.json` is a wrapper manifest with old distribution hashes,
not direct measurements; `s8_frontpanel_wram_relocation.json` is allocation/
assembly metadata, not native motion proof. Preserve these records. None can
close a new candidate's native feature gate.

Static normal_coverage remains an inventory only. Further missing bindings are
explicit in aggregate JSON, including executing-harness/source hashes and raw
TITLE-dwell credit/continuation counters. No generic PASS/force override exists.
