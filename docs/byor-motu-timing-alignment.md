# MOTU timing-alignment follow-up

**The borrowed-home lookup remains rejected.** Four fresh native captures
reproduced both elapsed-clock regressions exactly, with unchanged transaction
fields. The original negative receipt is unchanged, SHA-256
`6608f65c40df4c5dd5bbefa17ceb7bc82012c631c3fa32fc2321aaa258c423ae`.

The accepted reference rebuild was published. A fresh `git ls-remote origin
refs/heads/feat/byor-motu` returned
`438b519ff32879298d97e050ca25a3f119a7401a`. That is a remote branch identity
check; no CI result is implied. The accepted ROM remains
`41c505ad5f821bc7a6c458524cfd61f5212362f976d01a3f107a2d14381b9941`.

## Repeated measurements

The unchanged control and rejected candidate each ran the valid and early-abort
fixtures, using fresh private runtimes with identical observers. Two read-only
execution callbacks bracket the original `NbFreshVblank` polling body, from
entry through `NbWindowStart` before RTS. No callback was added inside the
polling loop. The 21 original bytes, callers and returned CPU state are audited.
The remaining interval includes every other master clock; it is not exclusive
CPU instruction time.

| Case / transaction | Control clocks | Candidate clocks | Total delta | Wait-body delta | Remaining delta | Fields |
|---|---:|---:|---:|---:|---:|---:|
| Valid / 2 | 7,943,412 | 7,943,412 | 0 | 0 | 0 | 22 / 22 |
| Valid / 3 | 11,203,622 | 11,203,584 | -38 | +68,728 | -68,766 | 31 / 31 |
| Valid / 4 | 7,814,280 | 7,814,376 | **+96** | +272 | -176 | 22 / 22 |
| Early / 2 | 7,943,412 | 7,943,412 | 0 | 0 | 0 | 22 / 22 |
| Early / 3, aborted | 9,055,908 | 9,055,984 | **+76** | +724 | -648 | 25 / 25 |

The extra clocks are repeatable measured boundary costs. The unchanged polling
loop absorbs almost all of the valid transaction-3 function saving. In valid
transaction 4, five calls account for a net +120 elapsed function clocks:
four +40 differences and one -40. All five have home indices at least 596 and
exit before the changed lookup dispatch. The executed admission and return
bytes are identical. The local Mesen implementation adds 40 master clocks at
DRAM refresh. Refresh phase is a strong source-supported explanation for these
function differences; individual refresh events were not logged, so exact
per-call attribution remains an inference. Neither observation permits ignoring
the required total-clock comparisons.

At the accepted rate of 21,477,272 master clocks/second, +96 is **0.004470 ms**
(0.001229% of that transaction) and +76 is **0.003539 ms** (0.000839%). The
candidate repeat's minimum complete-batch and map safety margins are 27,318
and 14,640 clocks, both above 10,000. A transaction delta is a different
boundary from a DMA margin and is not subtracted from that margin. Small scale
does not change acceptance: both total-clock regressions still fail.

## Evidence and scope

Offline re-certification passed **386 consecutive captured fields and
22,134,784 exact RGB555 pixels** across the four diagnostic cases. All 1,002
sealed raw inputs, 91 preservation controls, both private runtimes' 63 binary
files, six output-path-only setting changes, original SRAM seed and original
negative receipt were verified. The normal shared emulator byte gate was
acquired and released; no shared gate bytes, unrelated processes or global
emulator settings changed. The Windows packaging task received the next slot.
The final focused regression run passed **444 tests**, including the unchanged
439-test rejection suite and five new wait-accounting fault tests.

The supporting receipt is
[`receipts/byor-motu-timing-alignment.json`](receipts/byor-motu-timing-alignment.json).
Raw captures are retained under `out/byor-motu-timing-repeat-v1`; integration,
independent review, fault tests and revalidation are under
`out/byor-motu-timing-alignment-v1`. The original eight-case rejection and its
439-test record are retained separately. These four cases explain the bounded
timing question and do not promote a ROM or replace eight-case certification.

A separate scratch-to-staging copy pilot did not qualify: its provisional
epoch-3 copy saving was 3.75%, the recorded publication was ten clocks slower,
and inherited ownership monitors rejected its relocated store instructions.
Its failed logs remain retained; no candidate was promoted. Work proceeds with
a separate READY-scan experiment over the accepted reference rebuild, requiring
its own measurements, exact frames, safety margins, all-transaction
nonregression and independent review. No complete-game, 30 FPS, audio, combat,
HUD or production concurrency claim follows from these fixtures.
