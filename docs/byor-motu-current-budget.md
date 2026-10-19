# Current MOTU movement and presentation budget

This reconciles the accepted `a5ecc1f` non-blank fixture, ROM
`2ae50b27ac69986a07925e37fd99f5f5506044dec6195662ea54524a8ac4166f`.
The earlier scalar online-render timings describe an older implementation;
they are not the current critical path. The current evidence remains a fixed
camera, opaque, single-player SELECT/IDLE/WALK frame-zero fixture. Source
movement is requested by the test driver, and unsupported capabilities reject.

The five consecutive native boundaries below are disjoint. Their sums equal
the original transaction totals exactly. Times use the existing declared
21,477,270-master-clock clock policy.

| Interval | Epoch 2 clocks | Epoch 3 clocks |
|---|---:|---:|
| Begin to preloading: planning | 1,459,214 | 5,339,990 |
| Preloading to READY | 5,212,730 | 5,308,380 |
| READY to `NbMapCommit` | 783,078 | 66,404 |
| `NbMapCommit` to maps complete | 35,156 | 35,124 |
| Maps complete to returned VISIBLE | 339,754 | 340,216 |
| **Total** | **7,829,932 / 364.568 ms** | **11,090,114 / 516.365 ms** |
| Native field count | **22** | **31** |

`NbMapCommit` marks the commit phase before DMA setup, not the exact bus start.
Composition, waits, DMA and named helper spans are diagnostic subsets of this
ledger, not additional terms. Epochs 2/3 contain 1,989,408/1,874,122 composition
clocks, 1,846,100/1,544,574 wait clocks and 116,444/112,176 DMA-fence clocks.
The epoch-3 planning interval includes a 559,096-clock conservative prediction,
1,749,038-clock exact mark, 470,932-clock restoration plan and 1,531,966-clock
borrow preparation. The 1,012,632-clock membership bitmap is *inside* borrow
preparation. These overlapping subsets must not be summed as independent costs.

The 113,412-clock publication-fusion saving is a supported improvement to its
specified interval. It is about 1.01% of the preceding 11,203,624-clock epoch-3
transaction, not a 25% end-to-end speedup.

## What prevents the next playable source-driven milestone

The next bounded milestone is a continuously owned, source-timed player
movement/animation loop on this fixed scene, publishing coherent lossless
pictures while retaining the previous picture during preparation. It needs
the real clock and input/world owner joined to animation callbacks and the
renderer. The fixture currently derives source time from requested operations
(`LiveGroundStart` uses the request epoch plus 49); it does not demonstrate the
200-Hz world loop. Only three frame-zero artwork capabilities are admitted.

Both computation and transfer scheduling are critical. At 30 presentations per
second the declared clock policy provides about 715,909 clocks per picture.
Current composition alone costs 87–93 ms, and planning costs 68–249 ms. Each
transition also uses 14 preloading windows and a separate map window. A faster
final reference rebuild cannot resolve those limits.

The accepted capture's closed source-ground operation spans 417,168 clocks
between `NB_SP_START` and `NB_SP_DONE`, about 19.424 ms. This is one operation's
elapsed interval, not a complete world tick or an exclusive CPU-cost estimate.
It already exceeds the approximately 107,386-clock / 5-ms budget of a 200-Hz
tick. Joining the clock and world owners must therefore measure and resolve
the complete tick's actual critical path; wiring them alone cannot establish
the required simulation cadence.

There is a transfer lower bound independent of CPU optimization. Epochs 2/3
send 8,640/8,400 CHR bytes and 4,096 map bytes: 12,736/12,496 bytes. At eight
master clocks per byte, even an ideal transfer needs 101,888/99,968 clocks,
before descriptor overhead. Even two of the larger observed 50,468-clock
VBlank intervals with the required 10,000-clock margin in each offer only
80,936 clocks. These payloads therefore
cannot fit the two-field target under the existing margins. Future admission
needs fewer changed bytes and/or a measured different scheduling architecture;
increasing the batch limit alone is insufficient.

The bounded capacity-scan experiment attacks a measured part of planning. Its
acceptance requires an exact native decision and state, at least 20% reduction
of the same prediction boundary, and all original transaction/field/pixel/
ownership gates. A supported result is a planning step, not completion of the
source-timed loop or a 30-FPS claim.

Its 179-byte native candidate demonstrates the distinction: the ordinary
pressured transaction improves from 31 to 30 fields, but valid-home recovery
takes 32 more master clocks with the same 22 fields. That is about 1.49 us.
All 198 fields / 11,354,112 RGB555 pixels across these two completed cases are
exact; their minimum batch/map margins are 27,316/14,664 clocks. The measured
regression does not breach a pixel, ownership, field-count or 10,000-clock
safety requirement. The inherited collector additionally forbids *any* whole
transaction clock increase. That stronger performance rule remains unchanged,
so the candidate has no full-suite acceptance. No numerical tolerance was
introduced to pass it.

The timing difference first appears at READY (+22 clocks), map completion adds
eight, and the final RAM interval adds two. This is consistent with scheduling
and bus alignment; this experiment has not independently proved the cause of
each added clock. Further instruction tuning is frozen. Completing the live
clock/input/world join advances the missing runtime capability more directly;
remaining renderer computation and transfer work still need measured admission.

The concrete first runtime join should use `SourceClock4086_Observe` and its
physical-field debt, capture the interval's input through the existing input
controller/history owner, and enter `SourceWorldTick4086_Begin/Poll`. The world
owner already requires a due tick and matching clock/world time. Each yielded
phase must reach its actual provider before acknowledgment; the existing
`WorldModelOwner_Run` supplies the timed-animation continuation at phase 7.
The current `LiveGroundStart` helper cannot stand in for this dispatcher: it
manually installs phase/time controls and bypasses the whole traversal.

The smallest defensible initial integration proof is one persistent player's
clock-driven source update with real input and real provider completions,
stopping with any unbound phase still pending and its clock tick uncommitted.
Then close those specific providers until a full tick commits. Unknown phases
must not receive fabricated acknowledgments. This directly removes a live
runtime gap without requiring a faster renderer or claiming playable cadence.
The resulting world snapshots can subsequently feed presentation: that join
also needs an immutable render snapshot while later world ticks proceed, since
the current fixture serializes preparation and permits movement only at READY.

The opt-in [live-world bootstrap](byor-motu-live-world.md) drains the old DMA
queue and acquires a private native owner. The bounded
[entry-sound join](byor-motu-live-audio.md) now executes real source admission,
completes the constructor and cold publication, delivers all prepared BRR
blocks through the DSP, and retires the voice. The same 900-field capture
commits 285 consecutive real ticks and seals 285 coherent snapshots. Its median
tick costs 976,804 master clocks / three fields, so 200-Hz source cadence remains
unmet. Full sample coverage/polyphony, other actions and the immutable warm
presentation join remain open. The bounded waveform proof supplies no
presentation-cadence or full audio claim.

The forced owner-zero abort probe covers a guarded copy branch. The untested
natural cold-preflight failure chain is separate from the measured warm
presentation critical path; it must be closed when admitting a live bootstrap
owner, but does not justify an open-ended harness detour here.

## Requirements still outside this fixture

Foreign MOTU milestone 4 remains partial. Full source-sized, lossless artwork
and supported blending, all required poses and models, authored stage geometry
and camera/underlays, multiple actors, combat, HUD, authored audio, progression
and Demo completion need their own joined runtime evidence. Existing original
BOR campaign/runtime results do not certify these foreign MOTU requirements.
No source simulation slowdown, colour reduction, smaller artwork, weakened
10,000-clock margin, or relaxed pixel check is admitted by this checkpoint.

The bounded arithmetic evidence and exact input hashes are recorded in
`out/byor-motu-milestone-budget-v1/luna-requirements-audit-v2.json`; the canonical
accepted capture remains `out/byor-motu-abort-copy-v1/success/`.
