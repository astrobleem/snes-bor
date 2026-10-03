# Normal campaign review snapshot provenance

This is a review-only Git snapshot export, not replacement development history and not a branch to merge into master.

## Source revisions

- Original review base: 6bf609890563aa93835266213632b81f4c0b3723
- Original final committed revision: f20073b4ece3c6a0a1ad895aca1f49f33ff2aff2
- Original commits in the reviewed range:
  - 26fd15081156e1417df109ce488dd60e4d7a7e75 - feat(game): integrate compiler-owned Normal campaign
  - cea4b91a199c60de1f52a5660ab99ca99d209eff - test(game): certify complete Normal campaign routes
  - fe0feb72c9c428d3bd8154922882e40f4a1f2d6a - fix(build): track source visual catalog generator
  - 0c87d74200da03635c0208cf1bb253cb5268b690 - fix(game): correct Normal projection and slot boundaries
  - f20073b4ece3c6a0a1ad895aca1f49f33ff2aff2 - docs(review): publish Normal code review handoff

## Snapshot mapping and export omission

- New review-base snapshot commit: 654eb122be7eeba6f6411dc03262a917ec5c8822 (parentless; tree derived from 6bf609890563aa93835266213632b81f4c0b3723)
- New review-final snapshot commit: recorded by the review branch tip; its sole parent is the review-base snapshot above.
- Omitted from both exported trees only: src/generated/production_source_visual.json
- Original base catalog blob: 225f65e9e14c7e883d919ac9d01d5d4b12bf24ad, 112659267 bytes.
- Original final catalog blob: c8677f8617c61875090da45e3d50453bda2c00b3, 114194902 bytes.
- Existing generator comparison evidence: docs/review/normal_complete_generator_comparison.json
- No regeneration command is included because none was found documented in the existing review handoff/comparison material.

## Review status and limits

The campaign verifier's readable tracked-source restoration remains unresolved; this export does not include the protected bytecode recovery copy or claim to resolve that issue. No new runtime validation was performed for this snapshot task. Prior campaign receipts apply only to their recorded original candidate hashes; they are not new acceptance evidence for this export. Manual combat/visual acceptance remains outstanding.

This export is not a self-contained reproducible-build claim. Only the single catalog JSON path named above is omitted; other committed source, generators, evidence, and tracked inputs retain their original blob IDs and modes.
## Evidence reconciliation and source-recovery update

- Local development commit supplying this update: ae7afde76c8c26681c70360567aff950e8f18ebe (parent: f20073b4ece3c6a0a1ad895aca1f49f33ff2aff2).
- Review export is a snapshot-only child of the prior published review tip 52238f6ed3b310d0343f2b294967938d313ca384; its commit message records the same local development commit mapping. No original development commit is attached as a parent.
- Corrected acceptance evidence is listed in docs/review/normal_complete_receipt_manifest.json; final Normal acceptance is supported by the luna29, luna27, and luna25 receipts for candidate ROM 05edd46023b3173f8432087f8cfcbf182726c35ecfb918b5c996ec23e414ba1f. Earlier luna01 receipts are historical for ROM 7ef9d232e688c77d8aa54c01c45d44d3868dbc21ef5a67a3750fccd2bb9186dd.
- Verifier status remains SOURCE_RECOVERY_UNRESOLVED: current wrapper overrides and code-object rewrites depend on the preserved CPython 3.10 bytecode; the tracked readable implementation is incomplete. Protected and active bytecode copies were verified unchanged at SHA-256 4b8596c4b6b2081ef3c4acf68306af00068fec06cbd786d5a76915f62c92522.
- During this update: receipt contents and hashes were reconciled; the manifest was consistency-checked; documentation diff hygiene was checked. No source-only verifier import/CLI proof was possible without complete source. No ROM build, Mesen session, gameplay run, or campaign traversal was performed.
- Prior failed push status is historical. This export update is published only after the remote branch SHA is independently verified.
## Reconstructed verifier-source update

This section supersedes the earlier verifier-source-unresolved statements in the historical sections above; those accurately described prior snapshot states, but are no longer the current status. Current status is SOURCE_RECONSTRUCTED_OFFLINE, not full campaign-equivalence certification.


- Local development commit supplying this update: 61c48d45727e2bdb5fb6a3fa1e5b92ee353c9595 (its parent is the prior task-local evidence commit ae7afde76c8c26681c70360567aff950e8f18ebe).
- This review-only snapshot is a child of the previously published review tip e2ba02dd12d462c20573cee50530e63805dad47d; its commit message maps it to the local development commit. No original development commit is attached as a parent.
- Status: SOURCE_RECONSTRUCTED_OFFLINE. The readable verifier is reconstructed, not the original lost source. It has no runtime dependency on retained bytecode; the active and protected 160,137-byte CPython 3.10 copies remain unchanged at SHA-256 4b8596c4b6b2081ef3c4acf68306af00068fec06cbd786d5a76915f62c92522.
- Native CPython 3.10 offline results: 13,869 helper/Lua comparisons, 108 nested-helper comparisons, and 18 stubbed control-flow scenarios passed. Isolated repository-source import and --help passed without .pyc/__pycache__ or external process launch. Project checks: 39 Normal projection tests and five selected traversal-contract tests passed with in-memory build metadata stubs.
- The full source-queue traversal module remains unrun past import because its build_rom setup requires the absent Beats of Rage Original [v.3.0 Build 4086].pak. No PAK was copied or substituted. Real source-queue/spawn equivalence, emulator I/O, and end-to-end campaign equivalence are not established.
- Existing campaign receipts were not edited or rerun. No ROM build, Mesen session, gameplay run, or campaign traversal was performed. Manual visual acceptance remains outstanding.
