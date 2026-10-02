# Read-only Easy S7 data audit

Rerun after the final full build, from any working directory:

```powershell
python -B tools/verify/game_s8_easy_data.py --out out/s8_easy_data.json
```

The command above assumes repository-root invocation for locating the script.
All paths inside the tool resolve against the repository root. By default it
checks both `distribution/bor.msu` and `build/s8_candidate/bor.msu`. Select a
different explicit artifact with repeatable `--msu PATH` arguments. Omit
`--out` for JSON on stdout only. Exit status is zero only for a complete PASS;
missing files, invalid extents, or changed required data fail closed.

The only persistent write is the requested JSON report, confined to `out/`.
No encoded assets are copied; there is no build, assembly, media generation,
emulator use, or native benchmark. Run while final artifacts are stable; this
is not an atomic snapshot of a concurrent build.

## Exact scope

Pinned baseline: `c8cbd71b200cab869d3f953bdd07352c172577ed`.

- Recompile only 14 Easy queues in memory, compare against S7 raw Git blobs,
  current queue files, and stage-directory queue payloads in each named MSU.
- Compare Easy physical media bindings, 16 entry identities/order, generated
  entry kinds/values and stage map, scene configuration and sequence metadata.
- Compare the original 45 roster configurations and all S7-tracked files under
  their encoded-media prefixes; compare Easy background/frontpanel files.
  Raw-byte matches and CRLF/LF-only differences are counted separately.
  Raw Git blobs are batch-read directly, without archive export filters.
- Compare the music catalog structurally and every PCM against its pinned
  hash. Run the existing mechanically pinned S7 audio-adapter inventory.
- Inspect the real availability generator's default and candidate expressions
  without executing its file-writing generator. Report current shared
  availability separately; candidate availability does not publish a release.

Each queue and MSU has exact SHA-256 evidence. Media groups have compact
inventory hashes over ordered paths and both before/after hashes, with content
changes/missing paths listed. The report includes the audit tool's own hash.

## Required differences and nonclaims

`Campaign_Bor_NextFlags` did not exist in S7. Its current source-derived value
is checked against the linked source entries and explicitly reported as an
addition, **not unchanged completion/runtime behavior**.

Existing actors/audio remain `ACCEPTED_COMPAT` / `ADAPTER_EQUIVALENT`, not
`SOURCE_CERTIFIED`. Shared runtime changes, the expanded roster and TIMEOVER
audio blob mean this is not whole-ROM/MSU identity. New files outside the
S7-tracked media inventory, packed visual payloads, timing, gameplay and pixel
equivalence are not certified here.

Main's Easy Native3 route PASS in `out/s8_scene_edge_easy.json` is separate
evidence, not a pixel claim; this tool neither runs nor revalidates that route.
