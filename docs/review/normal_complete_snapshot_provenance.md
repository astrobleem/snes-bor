# Normal campaign review snapshot provenance

This is a review-only Git snapshot export, not replacement development history and not a branch to merge into master.

## Source revisions

- Original review base: 6bf609890563aa93835266213632b81f4c0b3723
- Original final committed revision: f20073b4ece3c6a0a1ad895aca1f49f33ff2aff2
- Original commits in the reviewed range:
  - 26fd15081156e1417df109ce488dd60e4d7a7e75 — feat(game): integrate compiler-owned Normal campaign
  - cea4b91a199c60de1f52a5660ab99ca99d209eff — test(game): certify complete Normal campaign routes
  - fe0feb72c9c428d3bd8154922882e40f4a1f2d6a — fix(build): track source visual catalog generator
  - 0c87d74200da03635c0208cf1bb253cb5268b690 — fix(game): correct Normal projection and slot boundaries
  - f20073b4ece3c6a0a1ad895aca1f49f33ff2aff2 — docs(review): publish Normal code review handoff

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