# Normal campaign verifier source reconstruction

Status: `SOURCE_RECONSTRUCTED_OFFLINE`. The reviewer-supplied
`s8_verifier_source_recovery.zip` reconstructs readable Python; it is not the
original lost source and does not create a new campaign-acceptance result.

## Runtime and protected reference

- `tools/verify/game_s8_normal_campaign.py` imports the readable base at
  `tools/verify/_game_s8_normal_campaign_base.py`. The runtime no longer
  requires `SourcelessFileLoader`, a `.pyc`, marshal loading, or code-object
  rewriting.
- The package targeted wrapper blob
  `0a1e927d406a81e572e027e75167567e8245dd9a` (173,164 bytes); the local
  pre-patch file matched it. The known wrapper corrections are expressed as
  source.
- Active and protected reference bytecode remain 160,137 bytes each, both
  SHA-256
  `4b8596c4b6b2081ef3c4acf68306af00068fec06cbd786d5a76915f62c92522`.
  They were verified before and after validation and not modified.

## Offline results

Native CPython 3.10 comparisons against the preserved bytecode passed:

- 13,869 helper/Lua cases, zero mismatches.
- 108 nested-helper cases, all matched.
- 18 stubbed control-flow scenarios, all matched, including mock natural and
  skip routes over 16 entries and a three-entry Easy route.
- Cache-free import and `--help` passed using only the two runtime source
  files in an isolated directory. No `.pyc`/`__pycache__` was present and the
  test's external-process guard observed zero launches.

Focused repository tests passed: all 39 tests in
`test_actor_s8_normal_projection.py` and five selected traversal-contract
tests in `test_game_s8_spawn_traversal.py`. They used tiny in-memory metadata
stubs and did not read game media. The source migration replaced an obsolete
code-object patch-count assertion with AST checks for the same zero-edge,
discarded-diagnostic, and camera-button behavior. A traversal assertion also
exposed a reconstructed accelerator control-flow mismatch; the source now
preserves the reference's early returns and keeps terminal camera writes after
the traversal observer branch.

The full `test_game_s8_spawn_traversal.py` module was attempted but cannot
initialize without `Beats of Rage Original [v.3.0 Build 4086].pak`; importing
`build_rom` derives source queues from that PAK. No PAK was copied or
substituted. Consequently the following remain unproved: real PAK-backed
spawn-queue equivalence, the full real traversal path, emulator I/O, and
end-to-end campaign equivalence. No ROM build, Mesen session, or campaign run
was performed. Existing receipts remain tied to their recorded ROM/MSU hashes.
