# MOTU source-world READY safe-point

**BYOR_MOTU_SOURCE_SAFEPOINT_PASS** against `6f2339ee45f5b3070eefcc9cd80ad61d3cfb78dc`.

One actual JOY1 RIGHT operation completes through the retained source movement implementation while the graphics transaction still owns its pending picture. The source advances from epoch 2 to 3 before the epoch-2 map commit. The old picture remains visible; the completed epoch-2 picture commits with its original key and epoch. A subsequent presentation consumes the sealed epoch 3 through the existing projected-position noop.

Candidate: `out/byor-motu-source-safepoint-candidate-v5/native/bor.sfc`.
SHA256: `7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b`.

## Ownership and native implementation

This is isolated behind `--source-safepoint`, requiring the accepted conditional-capacity backend and all its prerequisites. The flag-disabled build reproduces accepted ROM SHA256 `9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea` exactly. None of the inherited auditors was weakened.

`LiveGroundStart` in retained `out/byor-motu-online-v3/native/callback_fixture.pasm` cannot be called directly: its tail calls the publisher and enters the owner idle loop. The adapter in `tools/bor_compile/source_safepoint.py:movement_code` relocates its actual movement body into a returning subroutine. The candidate-specific binary auditor compares all 119 original instructions, correcting only local branch targets. Original external JSL service targets are unchanged. The constructor, controller bridge, history, run binding, ground/frame service, velocity, check_move and snapshot-seal implementations retain their original ROM bytes. There is no mock tick or host-written actor state.

The first source operation has completed its ground service before calling the renderer. The wrapper checks the actual `GroundServices_Begin` work-area status at `$7FB46A` is CLOSED (2). Source DP is zero; graphics DP is `$3400`. The wrapper saves P, A, X, Y, DBR and DP on the S-CPU stack, establishes source DP/DBR/16-bit widths, calls the returning adapter and restores those registers. Emulator callbacks check A/X/Y/DP/DBR/SP/P individually, including balanced stack restoration. The ordinary source owner has no further snapshot reads after the renderer returns. Only one queued request is permitted in this bounded experiment.

The legacy SA-1 returning worker is withdrawn by the retained isolated fixture; this proves S-CPU source execution, not SA-1 coexecution. Source services retain their established WRAM/BW-RAM authorities. Both-CPU write callbacks reject source-operation writes to renderer I-RAM `$3400..$37FF` and graphics BW-RAM `$42C000..$42D67F`; a before/after comparison also protects that BW-RAM region. No competing renderer, NMI, audio or DMA service runs during the source operation.

The READY hook is after all existing source-equality, mode, queue, slot and paired-DMA guards, and before the fresh commit VBlank. All CHR pairs have completed and the queue is empty. Existing pre-READY stale checks remain compiled and active. Failed or canceled transactions still reject; the READY rollback mode rejects before the hook executes. A completed valid picture may commit after the world advances. This does not globally bypass epoch checks.

The immutable latch is **20 bytes at `$42D60C..$42D61F`**, previously unused transaction-header padding. It is disjoint from restoration records, the six-pair I-RAM queue, metadata, spill records and committed key. It contains the nine source-derived words still needed for successful completion and the original pending epoch:

| Latch | Original authority |
|---|---|
| D60C | 7FBA50 |
| D60E | 7FBA54 |
| D610 | 7FBA56 |
| D612 | 7FBA1C |
| D614 | 7FBA36 |
| D616 | 7FBA3E |
| D618 | 433830 |
| D61A | 7FFAEC |
| D61C | 7FF742 |
| D61E | Pending epoch, 42D604 |

The latch is written only after READY and retained through map completion and successful-key publication. A callback checks it has not changed before commit. Completion reads these values from the latch, never the newer canonical snapshot. The remaining rectangle state in DP `$10/$12/$14/$16`, pending maps, refcounts and reservations remain graphics-owned and are protected during movement. No queue or restoration bytes are borrowed. New code occupies `$39B000..$39B263` (612 bytes), clear of existing A000 transaction and C000 compositor. The only source-owner ROM patch is 12 bytes in its idle command poll. All other ROM bytes, artwork, palettes, row/fused kernels and source services are equal to the accepted ROM.

Auto-JOY is normally disabled during production. The wrapper enables only auto-JOY (`$4200=1`, NMI still disabled), waits for a fresh sample and for active display to resume, then executes the real source bridge. It does not run movement inside a VBlank DMA interval. Commands request native work; the host never edits actor position, animation or snapshot bytes. A render-current command requests presentation of the already sealed snapshot without another movement.

## Native order and measured costs

Persistent actor pointer `$414000`; RIGHT changes canonical X **81 → 81.5**. The complete 146-byte source snapshots before and after match the accepted epoch-2 and epoch-3 controls byte-for-byte.

| Event | Master clock | Video field |
|---|---:|---:|
| Graphics start, epoch 2 | 200,481,846 | 561 |
| READY | 210,582,216 | 589 |
| Immutable latch | 210,583,332 | 589 |
| Source movement start | 210,846,036 | 590 |
| Source movement complete, epoch 3 | 211,244,426 | 591 |
| Map commit, epoch 2 | 211,510,398 | 592 |
| Both maps complete | 211,545,554 | 592 |
| Published/displayed epoch 2 | 212,114,416 | 593 |

Fields 589–592 display the exact old picture; field 593 first displays the exact pending picture. The movement takes **398,390 master clocks / 18.549378 ms**. READY-to-movement-start is 263,820 clocks, including controller sampling synchronization; movement-completion-to-map-commit is 265,972 clocks, including register restoration and the fresh commit VBlank. The movement crosses a video-field boundary, while the old image remains visible. There is no frame-rate deadline claim.

| Native publication interval (NbBegin → NbVisible) | Fields | Clocks | ms |
|---|---:|---:|---:|
| Accepted no-safe-point control | 30 | 10,917,854 | 508.344589 |
| RIGHT safe-point | 32 | 11,632,570 | 541.622376 |
| LEFT divergence safe-point | 32 | 11,632,614 | 541.624424 |

RIGHT adds **714,716 clocks / 33.277786 ms and two publication fields**. Preparation is not shortened or excluded from this interval. Minimum six-pair VBlank margin is **34,246 clocks**. RIGHT's complete paired-map commit takes 35,156 clocks with **15,118 clocks** remaining before active display. The LEFT case retains a 15,074-clock map margin. All warm DMA remains fenced inside measured VBlank windows.

## Independent verification and rejection controls

Five freshly executed native runs verify **419 visible fields / 24,027,136 RGB555 pixels**, with **zero mismatches**. The main proof accounts for 82 fields / 4,702,208 pixels and changes 4,260 pixels from the original scene. Normal brightness remains 15 after cold initialization. Each field has a screenshot and full 64-KiB physical VRAM capture. `m4_source_safepoint_evidence.py` independently recomposes both source snapshot oracles, reopens every PNG, decodes every physical VRAM capture and replays ordered DMA payloads. It checks all fields against the correct pre/post-commit source image.

| Run | Fields | Verified pixels | Result |
|---|---:|---:|---|
| RIGHT safe-point | 82 | 4,702,208 | Source advances before commit; original pending key/epoch retained |
| LEFT direction divergence | 90 | 5,160,960 | Different source direction cannot change pending key; newer unsupported picture rejects |
| Partial queue rejection | 81 | 4,644,864 | No READY/source step; prior display and ownership retained |
| Stale epoch rejection | 83 | 4,759,552 | No READY/source step; prior display and ownership retained |
| Flag-disabled control | 83 | 4,759,552 | Accepted ROM identical; ordinary source update occurs after graphics returns |

The LEFT divergence run deliberately executes an authentic LEFT at READY, advancing to epoch 3 / X80.5 / direction 0. The prepared RIGHT epoch-2 picture still commits with direction 1 / X81. Rendering unsupported newer state rejects while retaining epoch 2. An ordinary source-owned RIGHT recovers epoch 4 through the existing noop, proving the successful key was not replaced with the newer LEFT key. This supplements the main RIGHT proof, where the newer source projection is unchanged.

READY rollback, stale rejection, partial-queue failure, LEFT retention and projected noops pass. Rejected attempts leave committed maps/refcounts and brightness intact with no stale queued DMA. Source execution has no overlapping DMA packets. Complete physical replay and independent READY-residency reconstruction pass. Resource faults and unsafe PPU operations are **zero**. The accepted 18-epoch control, six inherited noops, capacity-rescue and previous renderer controls remain unchanged; this assignment does not rerun unrelated historical controls.

**153 focused tests pass. All 29 inherited dirty tracked files, including the protected 17, remain byte-identical.** Fingerprints are retained in `out/byor-motu-source-safepoint-v1/dirty-before.json` and `dirty-after.json`. No reset, stash, clean, media regeneration, PCM copy or master merge was used.

## Reproduction

Run from the repository root with the retained assets and Poppy/Mesen setup:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_opaque_component_native.py --output out/safepoint-RIGHT-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice --nonblank-batch-rescue --nonblank-restore-spill --early-capacity-admission --source-safepoint
# For LEFT, partial and stale: build a fresh private folder with the same flags plus --build-only.
python tools/verify/m4_source_safepoint_native.py --folder out/safepoint-LEFT-NEW --case left
python tools/verify/m4_source_safepoint_native.py --folder out/safepoint-PARTIAL-NEW --case partial
python tools/verify/m4_source_safepoint_native.py --folder out/safepoint-STALE-NEW --case stale
# Control: same build/run command without --source-safepoint, in a fresh folder.
python -m unittest test_m4_source_safepoint test_m4_conditional_capacity -q
# Re-certify the retained five runs and regenerate the machine-readable receipt:
python tools/verify/m4_source_safepoint_evidence.py
```

The receipt is `docs/receipts/byor-motu-source-safepoint.json`. It contains every verified field identity/hash/PPU state, native source events, per-transaction clocks, DMA fences and measured VBlank margins.

The subsequent epoch-3 presentation is deliberately an unchanged integer projection. It proves newer source consumption with zero graphics work; it does not prove a second changing picture can coexist in this allocator. This is one controlled S-CPU safe-point, not a continuous scheduler, 200-Hz world updates, SA-1 coexecution, general consecutive-frame capacity, 30 FPS, audio integration, breath, HUD, combat or full MOTU Demo. The existing isolated NMI/audio service configuration is retained. Stop at this bounded proof.
