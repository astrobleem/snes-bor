# Normal campaign review handoff

Date: 2026-10-03

## Published review export

The review-only snapshot branch is `review/normal-complete-snapshot` at
`52238f6ed3b310d0343f2b294967938d313ca384` before this evidence-reconciliation
update. Its parentless review base is
`654eb122be7eeba6f6411dc03262a917ec5c8822`. The export omits only
`src/generated/production_source_visual.json`; original development commits
were not pushed as ancestors. The prior GH001 rejection described below is
historical; the snapshot branch was subsequently published by ordinary push.

The original development review range begins at
`6bf609890563aa93835266213632b81f4c0b3723` and includes:

- `26fd15081156e1417df109ce488dd60e4d7a7e75` — compiler-owned Normal / persistent SA-1 integration
- `cea4b91a199c60de1f52a5660ab99ca99d209eff` — campaign evidence and verifier tooling
- `fe0feb72c9c428d3bd8154922882e40f4a1f2d6a` — tracked source-visual generator
- `0c87d74200da03635c0208cf1bb253cb5268b690` — projection and slot-boundary corrections
- `f20073b4ece3c6a0a1ad895aca1f49f33ff2aff2` — original review handoff

These original commits remain local. This task creates a separate local
evidence-reconciliation commit without moving master or the current checkout.
Its full ID is recorded in the review-export provenance and export commit
message; the exported branch tip is verified separately.

### Historical failed push

An ordinary push of original `HEAD` to `review/normal-complete-repairs` was
rejected by GitHub with `GH001` because historical
`src/generated/production_source_visual.json` blobs exceed the 100-MiB limit.
No force push, merge, or history rewrite was performed. That failed attempt
does not describe the later snapshot publication.

## Accepted runtime repairs

The follow-up review accepted all three runtime repairs and the tracked
generator. The repaired paths are:

- `src/core/actor_source_bridge.pasm` — projection high-bit preservation.
- `src/core/stage_timer_host.pasm` — pending-Time actor-offset derivation.
- `src/core/actor_s8_normal_sa1_runtime.pasm` — full-width SA-1 metadata-tail copy.
- `tools/verify/test_normal_correctness_repairs.py` — focused regression tests.

The prior repair session recorded 27 passing timer/repair tests, 20 passing
source-visual generator tests, and production-main assembly (`main_repair.bin`,
884,906 bytes). No campaign run was performed for these repairs. The focused
tests and assembly are not new campaign or manual visual acceptance.

## Receipt reconciliation

The final `NORMAL_COMPLETE` closure is supported by the
`s8_normal_full_*_candidate` receipts. All identify the closure candidate ROM
SHA-256
`05edd46023b3173f8432087f8cfcbf182726c35ecfb918b5c996ec23e414ba1f` and MSU
SHA-256 `8eb71123e3baa3e2bb3f696775ca3d0dad42a5fa2d64ea7373b1dfd6f50bf3c6`.
The natural, skip, and bounded Easy receipt SHA-256 values are respectively:

- `out/s8_normal_full_natural_candidate_luna29.json` — `f2cda573cde1426296a7e5eaa925b5e150baaca9c235dc088a18308a5978e14c`.
- `out/s8_normal_full_skip_candidate_luna27.json` — `1681c4e860703f5e1fc232a0d20e92d70e17724b191322b2277087af830695ce`.
- `out/s8_normal_full_easy_candidate_luna25.json` — `8ecda866604a4d5324004a18f60b2579478801b5d155bee560441e58ac0ce579`.

The natural receipt passes 83 checks across the 16-entry authored route;
all 735/735 expected spawn records completed, including 614 model-bearing
records. Natural Ending changes `TimesCompleted` exactly once, 7 → 8. The
skip receipt passes 68 checks across the same route and records legitimate
skip input at Rugal and Ending; completion changes exactly once, 6 → 7. The
Easy receipt passes 25 checks for only its first three legal entries and
leaves the counter unchanged, 6 → 6; it is not a full Easy completion claim.

The previous handoff cited these valid but historical `luna01` receipts:

- `out/s8_normal_sa1_full_natural_luna11.json` — `2abcd737638a3ed1d73d44b648b5015301e990a767a561ba929b501220bd3812`.
- `out/s8_normal_sa1_full_skip_luna01.json` — `b7327d95618f33b811c3adbe33b91970a2b83de8faace91a77b0310d1c531941`.
- `out/s8_normal_sa1_full_easy_luna01.json` — `ba1e4de74ee6b9ab15c4792c93d43abeeb9000b30f787eafa5dde2566e0322f9`.

Those receipts all record a different ROM SHA-256,
`7ef9d232e688c77d8aa54c01c45d44d3868dbc21ef5a67a3750fccd2bb9186dd`, with
the same MSU but older symbols. They also report passing routes and 735/735
spawn traversal in their natural run. Their Easy run is likewise limited to
three entries. They remain useful historical evidence only for their recorded
`luna01` candidate and are not erased or edited. The earlier handoff conflated
historical evidence with final-candidate acceptance; the receipt JSONs remain
unchanged. The machine-readable manifest
`docs/review/normal_complete_receipt_manifest.json` contains all six full
receipt hashes, embedded artifact hashes, directly extracted route, spawn,
counter, check, scope, and nonclaim fields.

Both receipt generations scope their traversal as accelerated native
progression with real input-driven initial-actor/prop interactions, not full
combat balance or manual visual acceptance. The final natural receipt reports
the specific source-visual/resource observations documented in
`docs/bor_s8_normal.md`. All-stage manual visual acceptance remains open.

## Verifier source recovery

Status for this evidence update: `SOURCE_RECOVERY_UNRESOLVED`.
The runtime wrapper still loads
`tools/verify/__pycache__/game_s8_normal_campaign.cpython-310.pyc` and applies
code-object modifications. The original 160,137-byte bytecode and its protected
copy have SHA-256
`4b8596c4b6b2081ef3c4acf68306af00068fec06cbd786d5a76915f62c92522`.
The untracked decompiler candidate
`out/normal_review_repair/game_s8_normal_campaign.py` is not accepted source:
AST parsing fails at line 283 on a leading-zero integer; its emitted main/error
path is also malformed. The 89-byte root-level decompiler stub is not source.
Neither recovery copy was modified.

The targeted local session record confirms that the original untracked source
was truncated by a failed disk-full patch on 2026-09-26. It contains no intact
original source body. The retained depyo candidate fails Python AST parsing at
line 283 on a leading-zero integer. The prior pycrefine attempt is also
unparsable. One bounded pycdc attempt against the CPython 3.10 copy emitted
unsupported-opcode/stack warnings and invalid Python at line 114. None of
these outputs is adopted.

The wrapper contains readable source-level replacements for
traversal_actor_coordinates, traversal_blocking_props,
traversal_combat_target_blocks, traversal_combat_engagement_needed,
traversal_chase_axis, traversal_terminal_clamp, traversal_camera_wait,
traversal_prop_chase_action, traversal_pickup_needed, traversal_pickup_action,
traversal_combat_attack_opportunity, observer_spawn_watchdog_due,
traversal_script, and validate_admission. Those do not supply a complete
standalone verifier because the following active base bodies remain opaque:
observer_stale_fields, bridge_owns_source_actor, traversal_signed16,
traversal_biker_approaches, traversal_biker_attack_window,
traversal_biker_action, traversal_target_key, traversal_slots_full,
traversal_group_gate_blocks_spawn, traversal_terminal_prop_clear_required,
traversal_biker_attack_mask, traversal_prop_bypass_complete,
traversal_prop_bypass_action, traversal_lifecycle_input, traversal_attack_held,
traversal_jump_held, traversal_session, traversal_plan, read_traversal, and
main. The run body is also still bytecode-backed, with code-object rewrites
applied in memory. CLI modes, route/control behavior, admission validation,
completion assertions, and receipt generation therefore remain dependent on
the retained bytecode. No source-only import/CLI pass or full behavioral
equivalence is claimed.

## Scope and checks

This evidence update read and SHA-256 hashed the six named receipt JSON files,
validated the machine-readable manifest against all six receipts (routes,
check booleans, counters, spawn counts, and ROM/MSU hashes matched), and
compared those fields with the final closure. It verified both original and
protected bytecode copies against the expected SHA-256 after the bounded
decompiler attempt. It inspected the targeted local session record; no
recoverable original source was found. No receipt was edited; no source-visual
catalog was regenerated. No ROM build, Mesen session, or campaign traversal
was run.
