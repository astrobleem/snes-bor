# Normal campaign review handoff

Date: 2026-10-02

## Review revision

Base: `6bf609890563aa93835266213632b81f4c0b3723`.

The intended review revision contains these commits, in order:

- `26fd15081156e1417df109ce488dd60e4d7a7e75` — `feat(game): integrate compiler-owned Normal campaign`
- `cea4b91a199c60de1f52a5660ab99ca99d209eff` — `test(game): certify complete Normal campaign routes`
- `fe0feb72c9c428d3bd8154922882e40f4a1f2d6a` — `fix(build): track source visual catalog generator`
- `0c87d74200da03635c0208cf1bb253cb5268b690` — `fix(game): correct Normal projection and slot boundaries`

All four resolve locally and are descendants of the review base. The requested origin was verified as `astrobleem/snes-bor`; credentials were not emitted. The review branch was absent before publication.

An ordinary push of `HEAD` to `review/normal-complete-repairs` was attempted. GitHub rejected it with `GH001`: historical `src/generated/production_source_visual.json` blobs are 108.90 MiB and 107.44 MiB, over GitHub's 100 MiB per-file limit. The remote review ref remained absent after that rejection. No force push, merge, or history rewrite was performed. The final review update is therefore local only unless the repository's large-file publication policy is addressed.

The outgoing change set had no detected credential patterns across 172 changed textual paths. The large outgoing blobs are the source-visual catalog JSON/BIN; no ROM, MSU, PCM, PAK, executable, or bytecode recovery blob is in the commits.

## Runtime repairs and prior verification

The reviewed runtime corrections are confined to:

- `src/core/actor_source_bridge.pasm` — preserve the fifth high-coordinate bit in exact and rounded source/native projections.
- `src/core/stage_timer_host.pasm` — derive the pending-slot offset from the captured direct-page value.
- `src/core/actor_s8_normal_sa1_runtime.pasm` — keep the full-width metadata-tail index from the preceding copy loop.

Focused tests are in `tools/verify/test_normal_correctness_repairs.py`. The earlier repair session recorded 27 passing timer/repair tests and 20 passing source-visual generator tests. It also recorded a successful production-main assembly (`main_repair.bin`, 884,906 bytes). These checks were not rerun in this task because their dependencies did not change. They are not new campaign or visual acceptance.

The generator comparison is published separately at `docs/review/normal_complete_generator_comparison.json`. With identical local PAK inputs and the recorded CPython/NumPy/SciPy/Pillow toolchain, the dirty generator reproduced the checked-in catalog JSON/BIN hashes; the previous committed generator did not. The comparison records both outputs and all input hashes.

Existing natural, skip, and Easy receipts are unchanged and refer to their original candidate artifacts; no Normal traversal was rerun for these repairs. The retained receipts are local under `out/` and are not copied into this handoff because they are verbose runtime traces (approximately 4.93 MiB, 1.49 MiB, and 86 KiB). Their receipt hashes are:

- `out/s8_normal_sa1_full_natural_luna11.json` — `2abcd737638a3ed1d73d44b648b5015301e990a767a561ba929b501220bd3812`
- `out/s8_normal_sa1_full_skip_luna01.json` — `b7327d95618f33b811c3adbe33b91970a2b83de8faace91a77b0310d1c531941`
- `out/s8_normal_sa1_full_easy_luna01.json` — `ba1e4de74ee6b9ab15c4792c93d43abee9000b30f787ea5ddeb2566e0322f9`

All three receipts record the same original candidate hashes: ROM `7ef9d232e688c77d8aa54c01c45d44d3868dbc21ef5a67a3750fccd2bb9186dd`, MSU `8eb71123e3baa3e2bb3f696775ca3d0dad42a5fa2d64ea7373b1dfd6f50bf3c6`, symbols `acffb1efc37f5a9521212cff70e9fa64e96acbdc11d416209fe97d2629141c35`, and audio config `e4492d18696db537d349e4d593bbd7bf8ddb75d030aa898d82bcf406424f3e0a`. The receipt JSONs themselves remain available only in Chad's worktree.

Manual combat and visual acceptance remains outstanding. Focused tests and assembly do not establish that acceptance.

## Verifier source gap — unresolved

`tools/verify/game_s8_normal_campaign.py` still loads the campaign implementation from `tools/verify/__pycache__/game_s8_normal_campaign.cpython-310.pyc` and rewrites code objects. The full original source was not found in local Git history, the findings archive, or retained same-name source files. The root-level `game_s8_normal_campaign.py` is only the 89-byte decompiler-error stub; it has been preserved byte-for-byte.

The original bytecode remains untouched at 160,137 bytes with SHA-256 `4b8596c4b6b2081ef3c4acf68306af00068fec06cbd786d5a76915f62c92522`. Its protected copy outside `__pycache__` has the same full hash. A local decompiler attempt emitted invalid Python (including an unparsable formatted-string expression); that output was not accepted as source, and no behavior was inferred from it.

A source-only probe copied just the bridge and the focused spawn-traversal test into an isolated directory containing zero `.pyc` files and no `__pycache__`. Both `--help` and test collection fail with `FileNotFoundError` for the absent `__pycache__/game_s8_normal_campaign.cpython-310.pyc`. This confirms the source gap is still open. No verifier-source restoration or cache-free passing test is claimed.

## Checks performed for this handoff

- Verified `HEAD`, branch, review-base ancestry, named commit hashes, staged state, and tracked dirty paths. Unrelated dirty work was left untouched.
- Verified the sanitized origin target and attempted an ordinary push; confirmed the GitHub large-file rejection above. No successful remote review branch SHA is available.
- Audited changed blob sizes/suffixes and scanned additions in 172 textual paths for common credential formats; no credential-pattern hits were found.
- Rechecked the original bytecode and protected-copy full SHA-256 values.
- Searched the requested source-recovery locations and ran the isolated cache-free negative import/CLI and test-collection probes.
- No ROM build, Mesen session, campaign traversal, runtime test suite, or broad regression sweep was run in this task.
