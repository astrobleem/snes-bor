# MOTU borrowed-home lookup experiment — rejected

Result: `BORROW_INVALIDATE_REJECTED`. The accepted checkpoint remains
`438b519ff32879298d97e050ca25a3f119a7401a` (reference rebuild). No candidate
commit, push, publication, or default build change was made.

The new 63-byte bank-local lookup passes **439 focused tests**, independent
instruction-model checks, all eight native correctness cases, **666
consecutive fields and 38,191,104 exact RGB555 pixels**.
Pixel, resource and unsafe-PPU faults are zero. All 84 preservation controls,
inherited edits, prompt deletion, older captures, private assets and the
unchanged 10,000-clock safety floors remain intact.

A fresh unchanged-ROM control pairs all 300 calls by full input hash and
return state. Epoch-3 full-function cost, including the actual RTS, falls
from **280,768 to 212,020 clocks (24.485696%)**.
Transactions 1 and 2 are unchanged. Original successful epochs 2/3 remain
22/31 fields, but other recorded intervals regress:

| Case | Transaction | Committed | Clock delta | Fields before / after |
|---|---:|---|---:|---:|
| valid | 4 | true | +96 | 22 / 22 |
| early | 3 | false | +76 | 25 / 25 |

These positive deltas violate the strict no-regression requirement. The
collector now pins the complete accepted native receipt and compares every
case and every committed/aborted transaction before writing a top-level PASS.
Recollection explicitly refuses a pre-existing PASS until that evidence is
retained separately. The tightened collector rejects this capture at valid
transaction 4; no top-level candidate PASS receipt exists.

Independent matched-event diagnosis locates the early +76 in abort/rollback.
Valid transaction 4 is a real +96-clock successful-publication regression at
the same 22 fields. Its 96 invalidation spans have identical aggregate cost
in both captures; the exact instruction-level source of the timing drift is
unresolved. The measured local CPU saving therefore does not qualify this
candidate as a supported end-to-end improvement. No padding, threshold
relaxation or changed observation boundary was used to accept it.

Seven cases completed before the original final RIGHT startup returned 9 of
10 requested frames at the unchanged MCP wall-time cap. That failed startup
is archived. A subsequent attempt encountered ordinary byte-gate contention
and started no emulator; the final fresh RIGHT run retained all exact-frame
assertions and original runtime inputs. The completed suite was sealed after
that run; the seven earlier raw case directories stayed byte-identical.

Minimum complete-batch margin is **27,318 clocks** and map margin
**14,640 clocks**. Two private runtimes match all 63 source binaries each,
change only six output paths, preserve global settings and the original SRAM
seed, and match final native save arrays. Both CPUs' leaf write-ownership
guards remain active; SA-1 stays reset in this fixture.

Code: `tools/bor_compile/borrow_invalidate.py` and four
`tools/verify/*borrow_invalidate*` source/test files. These remain isolated
experiment tools; the rejected ROM is confined to `out`. Receipt:
`docs/receipts/byor-motu-borrow-invalidate.json`. Sealed capture:
`out/byor-motu-borrow-invalidate-v1`; pinned control:
`out/byor-motu-borrow-invalidate-control-v1`; reviews, logs, failure archive,
source snapshots and preservation evidence:
`out/byor-motu-borrow-invalidate-integration-v1`.

The remaining implementation gap is publication/rollback phase timing under
the complete no-regression gate. This fixture supplies no complete-game,
30-FPS, audio, combat, HUD, live-200-Hz or production-concurrency proof.
