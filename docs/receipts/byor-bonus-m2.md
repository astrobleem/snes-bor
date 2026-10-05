# BYOR Milestone 2 — Original BOR Bonus

**BYOR_BONUS_COMPLETE** — BYOR means **Bring Your Own Rage**.

Branch: `feat/byor-bonus`, based on canonical master `50a82175a4834bdce87333c35db024567e492635`. This receipt certifies the candidate hashes below; commits and remote branch identity are returned in the final review handoff.

```powershell
py -3.10 byor.py inventory --set Bonus --output out/byor-bonus-source.json
py -3.10 byor.py build --set Bonus --output build/byor-bonus
```

Source and compiler ownership

- Actual source PAK/`DATA/LEVELS.TXT`: Bonus set ID 3, `ifcomplete 1`; Easy/Normal/Hard thresholds 0. Route `DATA/EXTRA.TXT` → `DATA/SCENES/SEWER.TXT`, no `next`, no `showcomplete`. The terminal scene returns to TITLE. BOR.C increments `TimesCompleted` after every completed set, including Bonus; [engine excerpts and hash](byor-bonus-m2-engine-authority.json) record the authority.
- EXTRA: 184 packed records = 166 source spawns + 11 groups + 7 waits; 0 hole prefixes. Compiler allocation: physical stage 50, typed route entry followed by scene sequence 3. Generated queue capacity is 184 records/1,840 bytes; u8 count/index ceiling 255, 16-bit copy count, guarded relocated arena. No truncation or route splitting.
- Source roster identities Crab (47, `type none`, 50 spawns) and Lobster (48, enemy, 27 spawns, maps 1–5 including map-5 King_Crab) use their own source definitions, animations and source-sized art. Five Drum held-item records include authored `2pitem`; Apple/Meat identity is preserved. Full directives, maps, names, queue records and source hashes are in [the source inventory](byor-bonus-m2-source.json).
- EXTRA's 60 authored shrine panels are compiled through the shared stage encoder; source width 14,400, encoded width 11,520. Generic ordered scene lowering binds the real two SEWER.GIF frames (10 seconds each), THANKS.GIF (5 seconds) and TIME.BOR repeat 1 through production scene transport.

Shared capabilities added

- Source-driven noncombat walking metadata and committed-source-clock catchup retain Crab heading, walking, drift and offscreen lifetime. This is explicit ACCEPTED_COMPAT fixed-point/byte-RNG scheduling, not a float/RNG equivalence claim.
- Long-stage source-coordinate projection expands the generic validated domain to source ±16,383/native ±13,106 while retaining rejection of unsupported off-lattice inputs.
- Source-image viewport admission, visible-piece pinning and actor-slot identity checks prevent offscreen resource exhaustion and stale model packets. Existing 16 KiB OBJ storage and presentation cadence remain unchanged.
- Compiler-declared lossless model-shared palette layout allows live/death poses to share identical source pixels. The measured Biker composition changes from a failing residency requirement to 53/64 tile blocks and 92/128 OAM pieces. The Biker poses share 41 blocks and two palettes; independent 4bpp decoding matches both source GIFs under the existing RGB555 adapter, including transparency and dimensions.
- Bonus follows the same BYOR/compiler pipeline. Complete availability and saved-counter unlock are separate decisions; incomplete candidate linkage is rejected. Optional same-candidate source-image resume/repack retains hardlinked PCM.

Native certification

- Real selector: all four sets PASS. Bonus is marked locked and confirmation is refused at saved count 0; count 1 permits selection and reaches compiler stage 50. Easy/Normal/Hard remain selectable at 0 and reach stages 0/22/36. Normal and Hard receive bounded source-world first-stage checks only.
- Full authored route: **184/184 queue records, 166/166 source spawns**, including control records. Accepted accelerated-native sequenced removals are disclosed in JSON; no queue-index, campaign-ordinal or completion-counter injection during the run. Save counter initialized to 1 before starting only. [Admission journal](byor-bonus-m2-admissions.txt), [complete compressed report](byor-bonus-m2-traversal.json.gz).
- Sewer: 3 presented frames, 1 authored clip transition, 1 completion, 0 skips, 0 late swaps, 0 retries; natural playback and score/lives/credits preservation PASS.
- Completion: **1 → 2**, exactly once; selected source set remains 3 and 180 TITLE observations produce no further increment or late scene transition.
- Bounded real interaction: 147 unaccelerated fields, controller input only, authored Drum damage, Apple drop and actual pickup-handler consumption; host error 0. Separate 600-field unaccelerated authored-enemy combat sample: 5 observed HP reductions, persistent SA-1 active, host error 0. [Screenshot](byor-bonus-m2-combat.png).
- Resource sample: 26 resident tile blocks and 4 palette records match exact catalog bytes, zero mismatches. Catalog: 4,153 source-sized entries, 0 legacy entries, 0 blockers. Full run admission trace: 3284 records, zero hard codes 0x21/22/23/24/26/2A; 0x27 pending transport is expected. [Admission trace](byor-bonus-m2-visual-admissions.txt.gz), [noncombat trace](byor-bonus-m2-noncombat.txt.gz).

Validation and preservation

Focused compiler/runtime checks: 114 passed, 49 subtests; final changed Bonus/visual checks: 29 passed; isolated traversal-contract checks: 55 passed, 14 subtests. Three historical queue/source-shape gates were deliberately outside this milestone's focused scope. Changed Python compiles; assembly queue/bank/text/score guards and `git diff --check` pass. Verifier fixture tests run in separate processes to avoid pre-existing module-wrapper leakage.

All 17 pre-existing dirty tracked files retain their exact original hashes (605,880-byte compact backup). They remain unstaged. No clean/reset, foreign generated-output staging, PCM copies or broad output deletion. One Mesen instance at a time; superseded candidate media replaced in place. Candidate exclusive retained storage: **50,598,358 bytes (48.25 MiB)**. All 26 PCM companions are canonical distribution hardlinks; 734,185,936 logical PCM bytes consume 0 new candidate PCM bytes. Detailed file-ID/link accounting and evidence paths are in [the certification JSON](byor-bonus-m2.json).

Artifacts

- ROM SHA256: `34dda36cba7ca71766b4879bb2c398b75b015932d43e31425c37706b4c3c64f0`
- MSU SHA256: `fce2a860bfdb406d230a30d9ff88dc737ebc28dce544c81d3fbe2339665c3dcf`
- Candidate: `build/byor-bonus`; source inventory: `out/byor-bonus-source.json`.
- Local focused logs, initial status, exact dirty-byte backup and diagnostics: `out/byor-bonus-evidence`.

Remaining nonclaims

No arbitrary OpenBOR compatibility, SOURCE_EXACT promotion, exhaustive pixel review, console-hardware certification or full unaccelerated Bonus balance/combat campaign claim. Existing coordinate/health/scenery/palette/scene adaptations and six-actor pool remain documented. No full Normal/Hard replay or historical broad gates; no foreign source game started. Production source world remains persistent SA-1 at configured 200 Hz simulation / 30 Hz presentation with sequenced event transport.

Measured retained candidate, milestone evidence, EXTRA background and receipts together: 66,401,957 exclusive bytes (63.33 MiB), excluding shared existing media. This names its scope explicitly; it is not a repository-wide storage claim.
