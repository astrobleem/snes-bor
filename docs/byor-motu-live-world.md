# Private MOTU live-world bootstrap checkpoint

**Status: required constructor audio remains pending; no complete world tick.**
The opt-in builder now joins a guarded native foreground owner to the real
source constructor. Native execution drains the original DMA queue, acquires
its private workspace, completes a nested source VM callback, and reaches
He-Man's authored SELECT sound. The inherited constructor test fixture had
acknowledged that sound without delivering it. This integration replaces that
stub with an explicit pending continuation.

The fresh full build and the iterative build are byte-identical:
`f8d7d4d64629e76c6d6f797dd41cdb6ee733d2da61117f509b5f56e2e9a2e702`.
The accepted renderer input remains
`2ae50b27ac69986a07925e37fd99f5f5506044dec6195662ea54524a8ac4166f`;
its entire publisher bank is unchanged. Production build selection is unchanged.

## Implemented scope

`tools/verify/m4_live_world_native.py` regenerates and relocates the existing
source player library into checked empty ROM banks. It preserves the existing
script-table prefix and rehosts full 128-slot pending-jump, hit-identity and
movement-contact storage away from the renderer's maps/references/queues.
Those arrays, a separate callback work block, and snapshot storage fit within
the private retired scene-video WRAM lease at `$7E6200..$7E80FF`.

The owner first checks scene and water lifetime guards, then permits the
original NMI to drain actual DMA while original buffers remain valid. Only
after draining does it disable original visual producers and install private
state. The owned foreground never returns to the retired game loop. A separate
foreign-work predicate preserves generation, frame-busy, HDMA and all eight
DMA-slot checks; it does not claim another display mode's lease. Nested VM
callbacks execute the real VM gate with its displaced prologue, rather than
re-entering the outer fixture's return path.

The emitted code beyond the constructor connects the real physical-field
clock, input history, world Begin/Poll/Commit owner, twelve-phase dispatcher,
existing player and animation owners, and bounded grounded post-update and
fresh-birth health helpers. The dispatcher only acknowledges a provider's
actual completion. The new health helper is restricted to the derived fresh
He-Man profile, and airborne/contact/DOT services remain unadmitted. These
post-constructor joins have unit/static evidence; native execution has not
reached them. Their presence is not a completed live-loop result.

## Native evidence and exact stopping point

`out/byor-motu-live-world-v1/native-v8/` captures 70 physical fields. The fresh
full-build capture `native-v9/` captures another 30 and adds read-only frame
and effect-cursor snapshots. Both used the ordinary shared emulator gate,
private portable settings/SRAM, and a contained Windows Job Object. Both
leases were released with zero child processes remaining. The gate is usable;
the historical PermissionError is not a current access blocker.

The diagnostic retains one immutable-input bootstrap callback and sets up the
old fixture's activation/producer state before acquisition. After activation
it makes no debugger writes to actors, source time, input, poses or phases;
physical input is held neutral. This remains a private fixture bootstrap, not
proof of an ordinary production game-loop handoff.

The captured B4FE table is byte-identical to the table regenerated from the
private source PAK. Its retained ticket identifies slot 0, animation handle 5,
SELECT frame 0, sound namespace index 0:
`data/chars/he-man/entry/entry.wav`. The frame owner remains state 1/pending 2;
the effect owner remains state 1/service 9/acknowledged 0, at cursor 1 of 3.
Both full captured control blocks remain identical across 21 consecutive
observations, fields 514 through 534. The source asset exists; the missing
capability is its joined runtime audio backend.

Both diagnostics record zero completed ticks, sealed snapshots, visible live
presentation fields, or protected-renderer write faults. They generate no new
RGB555 presentation certification. The existing renderer's exact-frame and
10,000-clock batch/map requirements remain in force; this diagnostic does not
exercise their joined live path.

The source-ticket audit, native leases, full-build identity, tests and
independent review are pinned in
[`receipts/byor-motu-live-world.json`](receipts/byor-motu-live-world.json).
All 552 focused unittest checks pass: the existing 505-test renderer regression
set and 47 provider/layout checks. The separate player-controls pytest module
also runs its assembly check with configured tools. The five default native emitter outputs remain
byte-identical to HEAD. Independent review covers source ownership and the raw
pending-ticket evidence; it does not convert that pending result into a tick.

The opt-in builder requires `POPPY_DLL` and either `DOTNET` or `dotnet` on PATH.
Native capture requires `MESEN_EXE` and `MESEN_PYTHON_PATH` for the matching
frame-exact MCP build, plus the existing shared lease and contained-job wrapper.
Evidence paths in the public receipt are relative to the repository; private
raw captures remain local and are identified by hashes.

## Remaining work

Bind the retained source sound ticket to actual sound admission and delivery
under a proved graphics/audio memory and scheduling owner, then acknowledge
that same captured ticket exactly once. Existing isolated sound-admission,
PCM/BRR and SPC proofs are useful components; their production memory lease
and this frame-ticket join remain open.

After the real constructor completes, measure the entire clock/input/world
tick through actual provider completions and Commit. Resolve newly reached
pending capabilities, then join immutable natural snapshots to lossless
presentation while later ticks proceed. The current latest-snapshot/pinned
snapshot split is emitted but unmeasured. Artwork admission still covers only
the earlier SELECT/IDLE/WALK frame-zero fixture. The broader computation and
transfer limits in [`byor-motu-current-budget.md`](byor-motu-current-budget.md)
remain unresolved. This checkpoint certifies neither playable cadence, 200 Hz,
30 FPS, production concurrency, audio, combat, HUD nor game completion.
