# BYOR milestone 1: original BOR Hard

**BYOR_HARD_COMPLETE.** The complete authored Hard campaign is compiler-owned,
selectable, built and traversed on the production persistent SA-1 runtime.
[Machine summary](byor-hard-m1.json) contains the checks, hashes and bounded
claims; [native admission journal](byor-hard-m1-admissions.txt) retains all 879
queue observations for review.

## Product and source authority

BYOR means **Bring Your Own Rage**. [BYOR documentation](../BYOR.md) describes
the supported original BOR source profile, production architecture, explicit
capability diagnostics and build dependencies. From the repository root:

```powershell
py -3.10 byor.py inventory --set Hard --output out/byor-hard-source.json
py -3.10 byor.py build --set Hard --output build/byor-hard
```

The output directory must be new. The thin entry point invokes the existing
compiler and production builder. It does not duplicate the compiler or promise
arbitrary OpenBOR compatibility. Other source profiles are rejected explicitly.

[Source inventory](byor-hard-m1-source.json) records the authoritative PAK,
`DATA/LEVELS.TXT`, original `BOR.C` completion/lifecycle authority, source model
definitions, authored health/maps/directives and per-stage packed queue hashes.
It is source and in-memory linkage evidence; native evidence is reported below.

The verified thresholds are Easy 0, Normal 0, Hard 0 and Bonus 1. Hard is source
set 2. Its authored route is:

```text
1AHARD -> 1BHARD -> 1CHARD(next) -> 2HARD(next)
-> 3AHARD -> 3BHARD -> 3CHARD(next)
-> 4AHARD -> 4BHARD(next) -> 5AHARD -> 5BHARD(next)
-> 6AHARD -> 6BHARD -> RUGAL(scene) -> 6CHARD(next) -> ENDING(scene)
```

`next` requests source showcomplete after the preceding stage. Compiler typed
entries, rather than physical stage adjacency, select the next entry. Physical
Hard stages are 36 through 49. The terminal campaign latch guards the single
TimesCompleted increment before return to TITLE. Bonus remains unavailable.

| Stage | Physical ID | Packed records |
| --- | ---: | ---: |
| 1AHARD | 36 | 51 |
| 1BHARD | 37 | 41 |
| 1CHARD | 38 | 38 |
| 2HARD | 39 | 115 |
| 3AHARD | 40 | 55 |
| 3BHARD | 41 | 45 |
| 3CHARD | 42 | 31 |
| 4AHARD | 43 | 73 |
| 4BHARD | 44 | 76 |
| 5AHARD | 45 | 73 |
| 5BHARD | 46 | 104 |
| 6AHARD | 47 | 119 |
| 6BHARD | 48 | 24 |
| 6CHARD | 49 | 34 |

Total: 16 entries, 14 stages, 876 source queue records plus three generated
hole-prefix records, 879 packed records and 753 source spawns. There are 29
spawned identities, 33 including held pickups. Hard adds no spawned identity or
directive kind beyond Normal. Its new authored map selections are Billy 3 and
Eiji 5/6. All use the existing source catalog and explicit map compatibility
policy; no new identity aliases were introduced.

## Shared implementation

The compiler owns the complete Hard route, source parsing, physical stages,
queues, model bindings, environment directives, scene/media metadata and
source-next completion policy. Hard availability is emitted only after complete
successful linkage. ABI 3 identifies the common source-world runtime; selected
source-set IDs and generated offsets resolve Normal and Hard independently.

Hard uses persistent SA-1 canonical source-world ownership, configured 200 Hz
BOR simulation, 30 Hz presentation, source-sized publication, 16 KiB OBJ
residency and the existing sequenced event ring. No Hard-specific simulation,
actor-count reduction or performance-rate change was introduced.

The milestone exposed and fixed shared defects:

- Retire old native NPC/pickup state and flush/fence old events at stage-world
  reset, following the source `kill_all` lifecycle. Preserve player stock/health.
- Clear the hidden pickup lane's high Y byte before binding a reused spawn slot.
- Clip complete source OBJ packets to the signed viewport before reserving OAM;
  preserve visible source pieces and repair row offsets and negative X encoding.
- Derive palette DMA bank from relocated staging and update the staging fence.
- Reset the full player Y position and jump state on stage/stock/continue
  respawn. The shared body moved to bank 17 to retain bank 0 admission.
- Relocate immutable stage music metadata to bank 12 for the expanded physical
  stage table, with long runtime loads.

The traversal controller also reads canonical signed player depth rather than
wrapping it to a byte, and preserves the accepted jump-input sampling timing.
These fixture corrections do not write player coordinates.

## Native methodology and evidence

The full fixture boots a fresh Mesen process, uses the real difficulty/character
selector, and follows generated progression. A native Lua observer records each
queue advancement independently of the four-field gameplay controller sampling
and checks each packed record against source lowering, live source identity,
role, health, boss, map and pickup transport. Initial AI takes observed real
damage; bounded enemy retirement then uses the sequenced worker remove transport.
Props and pickups use real input interactions. No queue index, campaign ordinal
or completion-counter injection is used in the full run.

RUGAL and ENDING play naturally. The inherited 9,000-observation scene bound
expired during clean ENDING playback; a 40,000-observation bound permits the
1,997 encoded frames without changing scene timing or skip behavior. The rejected
bound receipt remains under `out/byor-hard-evidence/` as diagnostic evidence.

The final `out/byor-hard-evidence/traversal.json` verdict is PASS: all 16 entries
in order, all 879 packed records including 753 source spawns, and all 83 gate
checks passed. The controller made 27,186 observations. The run used 609
sequenced worker removals; the summary records the actual interaction counts.
Every stage consumed its complete packed queue before compiler progression.

RUGAL presented 126 encoded frames, and ENDING presented all 1,997 frames with
four clip transitions. Each completed once, with zero skips, late frames or
retries. TimesCompleted was 10 before the run and 11 afterward. The final state
was TITLE at ordinal 15; 180 further controller observations retained the single
increment and produced no late scene swaps. Host/worker errors and event-ring
overflow were zero. The full traversal's visual-admission fault log is empty;
ordinary resource-pending statuses are not classified as admission faults.

The separate unaccelerated 600-native-field first-entry combat observation
passed. Real attack inputs reduced enemy HP, including a sampled 32 -> 27 -> 22
-> 12 -> 0 sequence. Persistent SA-1 host mode was 1 and host error was zero.
All 20 sampled hardware STAT77 OBJ overflow flags were clear. At the capture,
57 pinned resident blocks and six loaded OBJ palettes matched immutable embedded
catalog bytes exactly. [Combat capture](byor-hard-m1-combat.png) is retained;
these checks do not constitute exhaustive pixel or cadence acceptance.

The real selector regression passed Easy -> physical stage 0, Normal -> stage
22 and Hard -> stage 36. Normal and Hard each used source-world host mode 1,
zero host error and progressing ticks. No long Normal or full Easy traversal
was repeated.

The admission journal is the unmodified native observer output. Each decimal
row contains campaign, physical stage, queue index, native slot offset,
Spawn_LastKind, live flag, compatibility HP, input mode, source roster, object
slot, object number, ten packed source-record bytes, idle frames, frame, load
result, NMI field and boss flag. Source queue identities and packed hashes are
cross-referenced in the inventory and full native report. Full report hashes
are recorded in the machine summary.

## Visual policy and remaining nonclaims

The candidate embeds the 3,640-frame source-sized catalog. No artwork shrinking,
legacy 32x48 fallback, global actor-count reduction or newly invented visual
alias is used. Viewport clipping excludes only offscreen pieces. The final native
fault trace and representative resident VRAM/CGRAM comparisons bound resource
claims to the observed traversal and combat sample.

Existing ACCEPTED_COMPAT policies remain adaptations. The source inventory lists
coordinate/health transport, encoded palettes/scenes, scenery flattening and
other capability limitations explicitly. Native admission is not exhaustive
pixel, pose, animation, remap, layer priority or source physics equivalence.
This milestone does not certify all two-player interactions, every oversized
catalog frame, arbitrary OpenBOR games, a manual full-game balance playthrough
or physical FXPAK hardware. It does not begin Bonus.

## Validation, artifacts and workspace safety

Focused compiler gates passed: 41 tests and 59 subtests. The combined BYOR,
traversal/candidate, source projection/environment and visual admission/render
hook gates passed: 127 tests and 23 subtests, with one pre-existing generic
distribution `BOR_TEST_ROM` test deselected because the candidate fixtures
explicitly select their ROM. No full historical suite was run. Changed Python
modules passed `py_compile`, and milestone-owned changes passed `git diff
--check`. Candidate assembly/link/layout guards passed.

```powershell
py -3.10 -m pytest -q tools/bor_compile/test_byor_hard.py tools/bor_compile/test_production_campaign.py tools/bor_compile/test_normal_coverage.py tools/bor_compile/test_normal_bindings.py tools/bor_compile/test_stage_environment_build.py
py -3.10 -m pytest -q tools/bor_compile/test_byor_hard.py tools/verify/test_game_s8_spawn_traversal.py tools/verify/test_s8_candidate_build.py tools/verify/test_actor_s8_normal_projection.py tools/verify/test_s8_normal_worker_environment.py tools/bor_compile/test_source_visual_extended_admission.py tools/bor_compile/test_source_publication_render_hook.py -k "not rom_override_default_relative_absolute_and_invalid"
```

The final candidate is `build/byor-hard`. ROM SHA256:

```text
cd43ae27c8ab36d4b8d43522cd3b796f703250d4c622be0614dde2d2e526b809
```

MSU SHA256:

```text
74f469d407199549f57086d6c7844bd551880b43208504e7eec62a701c744a1a
```

The embedded source-sized catalog SHA256 is
`3dca52015dc5be7e0b16b1efe7b9fb580e52800f7c6e698f0ca4b4c733c7ff46`;
it contains 3,640 frames in 11,369,220 bytes. The candidate's build/link and
production-runtime manifests are retained alongside ROM/MSU and worker symbols.

Full native reports and focused logs remain under `out/byor-hard-evidence/`:
`traversal.json`, `combat.json`, `selector.json`, `source-inventory.json`,
`focused-final-code-tests.log`, `compiler-final-tests.log`, `commands.txt`,
`pcm-hardlinks.json` and `footprint.json`. Rejected diagnostic receipts remain
there, with their failures identified rather than relabeled as successful runs.

Retained candidate storage is 49,400,209 new bytes (47.11 MiB), plus 672,922,568
bytes of shared PCM links. Owned reports/logs/debug tools occupy approximately
35.24 MB; the twelve referenced native journal directories occupy 2.29 MB.
Tracked review receipts total about 0.18 MB. Free disk at closure exceeds
123 GB. There is one coherent candidate and zero PCM copies.

Work started from canonical master
`8ca34a84669c0f033385e1af7a8589f24d31060a` on `feat/byor-hard`.
Git ref creation and ordinary GitHub push access were verified after the earlier
permission blocker. `out/byor_m1_access/` remains historical diagnostic evidence.
No merge to master is performed.

Unrelated tracked/untracked dirt remains unstaged. A build regenerated the twelve
pre-existing dirty `out/spawn_*/*.bin` tables before their original bytes were
backed up. The retained `prebuild-spawn-dirt` snapshots are after that regeneration;
they cannot recover or prove preservation of the original dirty bytes. Those
outputs are not staged, reset or discarded. The five unrelated `out/g13_*` JSON
files and other foreign outputs remain outside the milestone commits.

One coherent candidate is retained. Its 25 PCM companions are hardlinks to
canonical media, adding zero PCM storage. Canonical source PAKs and distribution
media were not deleted. Automatic approval review rejected removing the
reproducible 6.7 MB `debug-tools` directory, so it is retained and counted.
