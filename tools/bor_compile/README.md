# BOR compiler: S0 shadow front end

This is a source-preserving compiler front end with the accepted queue backend,
a shadow identity/asset linker, and a full original-PAK compatibility report.
It does not replace production generation. It does not yet emit a complete
source-faithful ROM/MSU link. Normal 5B and all other unshipped entries are
dry-run output only.

## Reproduce

From the repository root:

```powershell
python tools/bor_compile/compiler.py 'Beats of Rage Original [v.3.0 Build 4086].pak' --out out/bor_compile_s0_final --golden-msu distribution/bor.msu --golden-sha256 E7FE744AF2928939F926A1C9121F6AC9E7F1D378533B95366E4AFEFD6BFE90AF --scope 1:10
python -m unittest discover -s tools/bor_compile -p test_compiler.py -v
```

The CLI also accepts an extracted source directory. The resolver owns case,
slash normalization, discovered spelling, collision rejection, traversal
rejection, and the implicit GIF suffix used by BOR's image loader. It does not
guess extensions for music, model declarations or progression paths.

Output:

- `compatibility.json`: complete typed source IR, unmodified source values,
  all frame delays, per-entry diagnostics, deterministic IDs, asset hashes,
  presentation groups, coverage and golden results.
- `compatibility.md`: readable set/entry matrix and explicit blockers.
- `queues/`: **legacy backend candidates**, including blocked entries for
  comparison. Their existence is not permission to publish them. Unknown or
  malformed stage directives prevent even candidate lowering.

Exit zero means the golden queue comparison passed, not that every source entry
is production-ready. `fully_compilable` is false until final media/model and
runtime bindings are owned and validated. `backend_lowerable` and
`registry_clear` are separate facts. Do not use CLI exit status as a content
availability flag.

## Ownership and golden evidence

The front end owns typed project/set/entry/stage/queue/scene descriptions;
source `next`, `ifcomplete`, scene repeat/order/timing; independent source and
packed counts; strict structural validation; source model lookup; deterministic
append-only shadow identities; content-hash asset groups; development prefixes.

The accepted adapter pins existing physical/model/scene IDs from Git revision
`0ef9a82bbd754aa979359df43d23821e48724ad8`. Its input is committed configuration,
not the dirty worktree. These are ABI pins, not guessed source identities.
Selectable-player policy stays separate. New source models get reserved shadow
IDs but cannot borrow another actor's art or behavior.

All 24 golden stage queues match the hash-pinned accepted production MSU byte
for byte. They also match the accepted converter using the old parser; the
new typed parser independently reproduces all queue fields understood by that
backend. Extra source altitude is retained separately. Scroll modes, Normal
boundary flags and generated scene ID/repeat/count contracts are checked.

Seven **committed input queue files** are stale relative to the accepted MSU:
Easy 3A, 3B, 3C, 4A, 4B, 5A, 5B. The report preserves their hashes and failed
comparison separately. These were already dirty before S0 and are not edited
or included in the compiler commit. This is why the MSU hash is required for
production golden reproduction. Do not claim all Git input blobs matched.

No production table changed ownership in S0. `STAGE_CONFIGS`, runtime constants,
music allocation, specialized video encoding, background conversion, and
final MSU/VM layout remain with the existing build. In particular S0 does not
yet centrally emit `STAGE_COUNT`, `MAX_BGS` or `VM_MSU_OFFSET`. It also does not
claim an independent byte reproduction of the complete ROM or video payloads.
The source-equivalence boundary has passed for queues and the listed metadata;
the remaining final-link work is explicit rather than silently asserted.

## Full original-PAK dry run

Source set order and thresholds: Easy (0), Normal (0), Hard (0), Bonus (1).
There are 50 logical entries: 43 stages and 7 scene references. All 43 stages
parse; 41 produce deterministic legacy queue candidates with no stage-name
branching. Hard 5A and EXTRA are blocked from queue emission by unbound source
models; a candidate may not silently borrow an actor identity for new content.
The queue output totals 22,080 bytes. Fifteen presentation signatures cover
the 43 stages; 134 unique content hashes cover directly referenced stage/scene
presentation, music and animation assets. This does not count transitive
model art/audio or predict a final MSU size.

Normal remainder: 5B, 6A, 6B and 6C lower mechanically. Rugal and Ending parse
through the same scene IR. Normal 5B needs no bespoke converter code, but its
aliases, maps above 3 and third coordinate expose legacy backend limitations.
Normal 6A additionally needs its environment/mirror binding verified. Normal
6B has no extra registered source blocker; final linking is still pending.

Thirteen Hard stages lower to queue candidates; Hard 5A requires explicit
Time/Ramon bindings before emission. All 14 introduce no new
stage directive names relative to Easy. Their encounter records remain
independent; shared presentation signatures are discovered by content.
This is not proof that every Hard encounter is faithfully implemented by the
current runtime. Alias/map/altitude and environment restrictions still apply.

There are zero entries certified for a complete compiler-owned ROM/MSU build;
all 50 remain blocked at that boundary. Forty also have explicit source/backend
diagnostics. Ten are clear of those narrower diagnostics. This distinction
prevents a successful legacy conversion from hiding fidelity losses.

## Bonus evidence

`DATA\EXTRA.TXT` is Shrine, right-scroll, ten panel declarations, order
`abcdefghij` repeated six times, background `data/bgs/shrine/back.gif`, no
frontpanel, stage music `data/music/fsol.bor`, boss music `data/music/1boss.bor`.
There are 184 authored records and a proposed packed count of 184: 166 spawns,
11 groups, 7 waits, no hole controls. Binary emission is blocked by unbound
models. No active rock/water/hole/endhole/blocked
directive is authored. Source order is retained even when `at` decreases.

Case-insensitive counts: Crab **50**, Lobster **27**. Crab is
`DATA\CHARS\CRAB\CRAB.TXT`, `type none`, speed 9, idle/walk only. Lobster is
`DATA\CHARS\LOBSTER\LOBSTER.TXT`, `type enemy`, idle/pain/fall/walk/rise/
attack1/attack2. Both need new identities and media. Crab's `type none`
movement/activation must be audited before assigning a runtime driver;
Lobster's authored attack/fall behavior also needs validation. No new AI
implementation is inferred from names or appearance.

The boss is Lobster alias `King_Crab`, map 5, health 400, boss 1, at 2900.
There are five Drum-contained items: Apple once, Meat three times, and one
`2pitem Apple`. All referenced identities, including case variants, are in
the JSON inventory. Normalized list: Angel, Biker-K', Billy, Crab, Drum, Eiji,
Heavy, Joe, K', K9999, Lobster, Robert, Shermie, Yamazaki, Yashiro.

`DATA\SCENES\SEWER.TXT`: TIME, repeat 1, SEWER.GIF (two frames, 20,000 ms total),
then THANKS.GIF (one frame, 5,000 ms). Exact per-frame delays are in the report.
Source parsing succeeds; new SEWER media encoding/geometry/presentation remains
an explicit blocker. Bonus remains a set with threshold 1, never an automatic
postgame branch or a difficulty flag.

## Capability limits and next step

The registry covers every encountered stage/progression/scene directive name;
unknown directives fail closed. Model bodies are read through the existing
entity parser, which is not a general model capability validator. Every new
model therefore remains blocked for encoding and behavioral validation.
Newly discovered model declarations include Flash, Time, Ramon, Knife, Shot,
Star, Crab and Lobster; declared-only entries are not conflated with new stage
spawn requirements. Existing legacy special handling of Time/Ramon does not
constitute an independently linked actor identity.

Known backend restrictions are reported with source line/value: aliases have
no queue field, maps above 3 are clamped, third coordinates are omitted from
the queue format, and environment values need a verified separate runtime
binding. Unknown `remap` at stage scope is rejected; model remaps remain in
model source and are not assumed supported for new models.

S1 now reproduces the entire accepted layout, but strict source certification
still exposes accepted runtime representation gaps. Close the generic bindings
listed in `docs/bor_compile_s1.md` before production ownership changes. Once
those gates pass, target compiler-owned **complete Normal**, not another
one-stage-at-a-time import.

A second PAK needs a source reader/tree, this LEVELS/MODELS/stage/scene grammar,
and an explicit accepted runtime binding manifest instead of the stock Git
adapter. The parser and ID/dedup primitives are generic; the current CLI golden
adapter targets this repository's original BOR corpus. No generic OpenBOR
compatibility or complete future-PAK media compiler is claimed.

## S1 runtime certification

```powershell
python tools/bor_compile/certify.py 'Beats of Rage Original [v.3.0 Build 4086].pak' --out out/bor_compile_s1 --evidence docs/bor_compile_s1_evidence.json
python -m unittest discover -s tools/bor_compile -p 'test*.py' -v
```

The audit command writes reports only. Its zero exit status means the audit
completed, **not** that BLOCKED content is certified. Add `--require-golden`
for the migration gate: it currently exits **2**, correctly. S2's stricter
model checks block all 24 accepted stages (S1 blocked 21). No production
ownership change is allowed by a byte-identical queue/layout check alone.

`certify.py` hash-pins the source PAK and accepted MSU, recomputes the complete
layout using compiler queues and accepted encoded assets, validates generated
audio/scroll tables, derives reuse from content signatures, verifies scene
order/timing/payload bindings, and inspects model directives/frames. Candidate
layouts temporarily parameterize the legacy packer's capacity in-process and
restore it; no production constants or artifacts are written.

The source-model validator distinguishes a missing binding from a proven
unsupported encoding. New models are never emitted using borrowed identities.
Existing opaque model directives are diagnostic blockers, not newly claimed
runtime defects. Reports preserve exact source paths and decoded queue deltas.

## S2 model/environment and independent PAK analysis

```powershell
python tools/bor_compile/analyze.py 'Beats of Rage Original [v.3.0 Build 4086].pak' --dialect historical-bor --golden-baseline 0ef9a82bbd754aa979359df43d23821e48724ad8 --output out/bor_compile_s2/bor
python tools/bor_compile/analyze.py 'Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak' --output out/bor_compile_s2/tmnt
python tools/bor_compile/analyze.py 'Masters of the Universe [v.3.0 Build 4086].pak' --output out/bor_compile_s2/motu
python tools/bor_compile/regenerate_queues.py 'Beats of Rage Original [v.3.0 Build 4086].pak' --install
```

`analyze.py` accepts a PAK or extracted tree. It does not infer an engine
dialect from the filename, execute source scripts, emit dummy actors or
publish content. Every source model has a project-content-scoped identity.
ModelIR retains raw directives, sticky per-frame state, original assets,
geometry, attack types, remaps and dependencies before capability checking.
`LOWERABLE_WITH_ADAPTER` is a source capability candidate, NOT a certified
runtime model. `--evidence PATH` optionally emits compact reproducible JSON.

`regenerate_queues.py` is the deterministic owner for accepted derived queue
inputs. It lowers all 24 from source, verifies every byte against the pinned
accepted MSU, and only then installs them. It does not consume dirty queue
files. `--output DIR` instead writes an isolated tree. This closes queue-input
reproducibility, not a claim that every media asset can be rebuilt from an
otherwise empty checkout. See `docs/bor_compile_s2.md` for remaining blockers.
