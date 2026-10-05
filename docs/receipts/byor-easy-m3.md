# BYOR Milestone 3: Easy convergence

**BYOR_EASY_CONVERGED — Bring Your Own Rage.** Base master:
`5d9ef2df66b3c132f046db57dcc13e302c5c247d`. Branch:
`feat/byor-easy-convergence`. All four original BOR source sets now use the shared
compiler-owned source campaign family. No foreign PAK was started.

```powershell
py -3.10 byor.py inventory --set Easy --output out/byor-easy-source.json
py -3.10 byor.py build --set Easy --output build/byor-easy
```

## Source and baseline

Actual original BOR PAK and LEVELS.TXT establish Easy set 0, `ifcomplete 0`.
Thresholds are Easy/Normal/Hard 0, Bonus 1. Authored route:

`1AEASY → 1BEASY → 1CEASY → 2EASY → 3AEASY → 3BEASY → 3CEASY →
4AEASY → 4BEASY → 5AEASY → 5BEASY → 6AEASY → 6BEASY → RUGAL →
6CEASY → ENDING`.

Stage files are under `DATA/EASY/`; scenes under `DATA/SCENES/`.
Fourteen stages and two scenes retain physical stage IDs `0,1,2,11..21`.
Queues contain 667 packed records: 545 source spawns, 69 groups, 50 waits and
three hole prefixes. Maximum Easy queue is 92; linked Bonus maximum remains 184.
The ten-byte record/u8-count ABI is unchanged. Six authored `next` flags drive
showcomplete. BOR.C establishes one TimesCompleted increment at terminal return.

The accepted M2 candidate `build/byor-bonus` was reused without rebuilding.
Its native Easy selector reaches campaign 0, physical stage 0, host mode 0.
The compatibility path used SCPU actors and fixed 32×48 visuals. All 14 actual
baseline MSU queues match the frozen baseline; all 14 packed media dimensions
match the new candidate, including down-scroll padding.

Baseline ROM: `34dda36cba7ca71766b4879bb2c398b75b015932d43e31425c37706b4c3c64f0`.
Baseline MSU: `fce2a860bfdb406d230a30d9ff88dc737ebc28dce544c81d3fbe2339665c3dcf`.

## What changed

The [machine differential](byor-easy-m3-differential.json) compares 765 finite
source/encoding contracts: **512 LEGACY_EQUIVALENT, 249 SOURCE_CORRECTS_LEGACY,
4 ACCEPTED_COMPAT, 0 REGRESSION, 0 UNPROVEN**. These counts do not certify full
legacy/new gameplay or pixel equivalence.

| Domain | Old behavior | New behavior / source authority | Verdict |
| --- | --- | --- | --- |
| 238 spawn binding contracts | Slot/default compatibility encoding | Explicit authoritative model bindings: Yashiro 97, Ralf 98, Joe 22, Jhun 16, Time 1, Ramon 1, Yamazaki 2, Heavy 1 | SOURCE_CORRECTS_LEGACY |
| Nine extra completion presentations | 1A, 1B, 3A, 3B, 4A, 5A, 6A, 6B and Rugal presented completion | LEVELS.TXT `next` flags only | SOURCE_CORRECTS_LEGACY |
| First foreground | Scalar final F03/legacy encoding | All four authored ordered STREET/F00..F03 declarations through shared BG2 adapter | SOURCE_CORRECTS_LEGACY |
| Mirror | Fixed metasprite mirror formula | Authored mirror uses source-sized same pose, tiles and palettes; BOR.C foot formula through existing coordinate adapter | SOURCE_CORRECTS_LEGACY |
| Queues/media | Accepted geometry, maps, held items, aliases, route and raster/scroll contracts | Preserved contracts; all authored records retained | LEGACY_EQUIVALENT |
| Runtime/presentation | Compatibility combat world and fixed-size art | Shared source world/visual publisher and typed environment services | ACCEPTED_COMPAT |

Binding corrections identify encoded contract changes; they do not assert that
every old screen showed the wrong identity. Individual records and source
evidence are in the differential. Ramon and Time now have generic source bindings
for every original source set. Held items, aliases, HP metadata, music, boss music,
holes, water, rocks, steam, blocking, mirrors and scenery remain explicitly
inventoried; existing HP/coordinate/raster/depth adaptations remain documented.

## Native proof

Final candidate source host mode 1, persistent SA-1 owner 2, 200 Hz source world,
30 Hz presentation, sequenced event transport and 16 KiB OBJ residency.
The all-set selector regression passed. Easy/Normal/Hard select at count 0;
Bonus refuses at 0 and selects at 1. Each first-stage player source packet
published. No other full campaign traversal was rerun.

The accepted accelerated-native Easy run visited all 16 entries in authored order,
consumed **667/667 records**, and observed **545/545 spawns**. No queue-index,
campaign-ordinal or completion-counter injection occurred during the run.
Rugal presented 126 frames; Ending presented 1997 with four clip transitions.
Both completed naturally with skip 0. TimesCompleted **0 → 1 exactly once**,
stable through 180 TITLE dwell observations; selected source set remained 0.
Sampling counts controller observations; admissions have an independent native
journal. Allowed positive idle overshoot rejects short steps and all timeouts.

The real-input 600-field sample damaged two authored Shermie enemies, with
persistent SA-1 active and host error 0. A separate bounded unaccelerated
interaction window damaged Trash, observed its Money drop and consumed it.
The inherited bootstrap actor is excluded from authored enemy coverage.

The source catalog contains 4153 entries, zero legacy entries and zero blockers.
Representative VRAM checks matched 14 tile blocks and one CGRAM palette exactly.
The full-run publication observer checked **34,077 pieces**, with zero tile,
block, palette or OAM high-bit binding faults. It recorded 1,624 mirror pieces
at physical stage 19. The mirror journal key contains roster and animation role,
not map. All 14,182 admission diagnostics were pending code 39, no hard faults.
Deferred admissions can omit a pose in a snapshot; this proves resource identity,
not continuous presentation cadence or exhaustive pixel fidelity.

Measured shared defects were fixed generically: SA-1 producer scratch corruption
by SCPU unlink, byte OAM coordinate writes, pending-lease index clobber, palette
scratch overlap, viewport accumulator width, and stale palette-map reuse.
The [fix receipt](byor-easy-m3-shared-visual-fixes.json) and
[event race receipt](byor-easy-m3-event-relay-scratch-race.json) retain causes.

After all native gates, the obsolete Easy accepted-legacy queue/unbound escape
was removed. Every original BOR selector bypasses campaign 0. Its resolver,
host-mode-0 service and fixed-size renderer remain for internal/foreign/test
compatibility. The [path audit](byor-easy-m3-legacy-path-audit.json) records scope.
Post-retirement relinking produced identical certified ROM/MSU hashes.

## Artifacts and validation

ROM: `46d7e21f23b81653ba626610d0c2c462c1fea2a858af02423b625705cf8a8e2a`.
MSU: `eb781b14d4df082f574df8eb58cb90d5714969a5a91913fdcbd70902da77b1cf`.

Primary records: [full receipt](byor-easy-m3.json),
[source inventory](byor-easy-m3-source.json),
[baseline](byor-easy-m3-baseline.json),
[native summary](byor-easy-m3-native-summary.json),
[full native report](byor-easy-m3-traversal-release.json.gz),
[admissions](byor-easy-m3-admissions.txt),
[selector](byor-easy-m3-selector-release.json),
[combat/resources](byor-easy-m3-combat-release.json),
[focused validation](byor-easy-m3-validation.json).
Local diagnostics remain under `out/byor-easy-evidence`.

Focused compiler, binding, differential, environment, affected runtime, selector,
scene, source-visual and traversal contract checks passed. Final Easy tests: 11;
campaign tests: 6; traversal contracts: 57; changed Python py_compile: 25.
Bank0/text/score layout guards and git diff --check passed. Bank0 has two bytes
before the NMI boundary; no new capacity claim is made.

Candidate exclusive allocation is **50,499,848 bytes**; 26 PCM files are canonical
distribution hardlinks, with zero new exclusive PCM bytes. Candidate logical size
is 784,658,854 bytes. Deduplicated candidate, M3 receipts/evidence and referenced
compiler-private cache allocation is recorded in the JSON storage receipt; reused
compiler caches are included, the pre-existing baseline is excluded. Four exact
M3 reproducible stderr logs totaling 1,624,157,064 bytes were pruned after compact
authority was retained. No protected historical evidence was deleted.

All 17 original dirty tracked files retain exact sizes and SHA-256 hashes.
Only milestone-owned work was committed; all unrelated dirty tracked files
remain unstaged. No reset, clean, stash or foreign dirt
discard occurred. Untracked preservation uses compact presence checks and no
repository deletion; it is not a per-file content certification of 47k paths.

Nonclaims: arbitrary OpenBOR compatibility, SOURCE_EXACT promotion, exhaustive
pixels, console hardware, full unaccelerated campaign balance, complete legacy
gameplay equivalence, complete original player-controller behavior, exact airborne
mirror/depth fidelity or continuous pose cadence. Static inventory diagnostics
retain their original bounded scope; native proof does not turn every source
feature into SOURCE_EXACT. No timeout is recorded as PASS.
