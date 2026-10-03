# S7 shared compositor and accepted OBJ leases

This correction supersedes the earlier teardown implementation in `fbfc338`.
It does not certify strict source/display latency or six-actor execution.

## Correctness changes

The old teardown forced `Oam_HighWaterSlot=512`, cleared the entire shared
picture, and stopped publication while the source epoch was closed. That
inflated subsequent packet preparation and could suppress accepted actors.

Capture now records the publication phase outside the OAM shadow. A close
request received after rendering cannot retire that already-rendered source
picture. The next coherent source-excluded picture is submitted through the
same immutable packet/fence machinery. Accepted pieces remain in that picture.
Closed/reloading epochs continue shared publication. Reopen waits for actual
packet completion rather than rejecting a still-pending shared picture.

Source generation is compiler-owned in
`tools/bor_compile/source_publication_native.py`; verification modules invoke
it. Moving the generator did not change the mixed-test ROM bytes.

The allocator accepts explicit reserved 256-byte OBJ footprints. Mixed-policy
entry transfers cover only placed source bytes, not the entire 8-KiB window.
Accepted slot1 owns SMALL footprints 2,3,10,11 (its unchanged LARGE tile4
rectangle). Those 1,024 bytes are excluded from source placement and every
source transfer, leaving 7,168 bytes. Equal-sized footprints have zero external
fragmentation; unavailable capacity produces the actual reserved-space bound.
This is a fixed admitted layout lease, not permission to introduce an arbitrary
new compatibility allocation during an active epoch.

## Native evidence

```powershell
python tools/verify/actor_s7_multi_publisher.py --output out/repro_shared_epoch --case epoch-reuse --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_mixed_epoch --case mixed-epoch --live
```

`out/s7_epoch_shared_02`: 148 source pixel proofs, all Crab8/Gold6 frames,
162 queued packets, 16 completed tile transfers, zero resource/admission faults
and zero live-reference overwrites. Preparation-to-next-field misses decreased
from the old run's 30 to 1. Strict snapshot latency remains NOT_CERTIFIED.
The optional palette staging cache produced 5 misses on this corrected path;
it remains an experiment, not the selected default.

`out/s7_mixed_epoch_final`: actual Crab source frames0..7 and accepted Mary
rendering coexist; Mary survives close/reload, then Crab resumes. There are
45 source pixel proofs, 65 complete queued pictures and 24 entry/reload tile
transfers. Source transfers do not touch Mary's reserved bytes. Accepted tile
DMA bytes and immutable OAM consumption are compared at the actual hardware
completion boundary. Source pixels have zero mismatches. Five preparation
misses remain failed, not removed from the report.

The mixed control is explicitly animation-only publication isolation. Mary
retains accepted updates and has no independently simulated source context.
Cross-policy combat/target/AI semantics are **not** certified by this control.
The original source-world host continues to reject unbound live actors outside
this explicit verification configuration.

ROM SHA-256:
`872c0ee0f92f87bdf785ede39e15fec74821b93d6bd41e0273c4eb4dbdca0ba4`

MSU SHA-256:
`ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`

Artifacts include `multi-proof.json`, `publisher-multi.json`, `epoch-reuse.json`,
`teardown.json`, `mesen.log`, generated `world.pasm`, and
`compat-while-source-closed.png` (actual emulator screenshot).

Validation: 15 allocation/source-key tests, two palette-linker tests, native
template test, 500 generated labels with no S7 width violations, changed Python
compilation and diff hygiene. Default production ROM/MSU are not replaced.
