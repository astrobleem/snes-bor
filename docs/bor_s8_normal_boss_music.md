# Normal ordinary-biker boss-music receipt

Source/predicate checks PASS; no native or audible acceptance claimed.

- Normal `2.TXT` (physical stage 25) has stage track 11 (`SAVIOUR.BOR`)
  and authored boss track 1 (`1BOSS.BOR`). Source queue indices
  22, 23, 51, 52, 53, 54, 55, 56 are ordinary Biker-K' (`boss=false`).
  They must not issue the boss cue. Heavy is the actual authored boss at
  queue index 64, source scroll position 3200; its cue remains enabled.
- Normal `4A.TXT` (physical stage 29), Biker indices 39/40, has no authored
  bossmusic and generated boss track zero: the old calls were audio no-ops.
- All 14 Normal stages' generated boss-track IDs match their source directives.

The focused test evaluates the actual narrow branch predicate for 112
campaign/kind/subtype combinations against pinned S7
`c8cbd71b200cab869d3f953bdd07352c172577ed`. Exactly one combination changes:
Normal campaign 3, identified kind 5, Biker subtype 1, cue true -> false.
Easy/foreign policy, ordinary identified-enemy exclusion, and real-boss cues
remain unchanged. This is bounded source-code evaluation, not SNES execution.

```powershell
python -B -m unittest tools.audio.test_normal_boss_music -v
python -B tools/audio/normal_boss_music.py
```

Three tests pass. The second command prints the full required-behavior receipt
without writing files. `verify_runtime_audio.py` now incorporates this receipt
under `normal_required_behaviors` on its next normal verification run, failing
closed on branch-policy or source boss-track drift. No old report is silently
promoted or rewritten here. Queue artifacts can still predate Kuhn's current
Normal model-binding edits; the receipt explicitly does not certify them.
