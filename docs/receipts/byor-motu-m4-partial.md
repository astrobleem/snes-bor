# BYOR M4: foreign-source inspection and presentation decision

Classification: **PRODUCT_DECISION_REQUIRED**. Milestone 4 remains partial.

Branch: `feat/byor-motu`, based on canonical master
`ceb00643f32bb88db5dd56b6b54d200b5225c794`. No merge is authorized.

The implementation now inspects foreign sources, derives source set names,
routes and loaded player declarations, retains unknown directives and script
blocks, inventories assets, decodes source model palettes/alternate palettes,
and diagnoses compilation requirements without invoking the original-game
builder for another PAK. It does not yet compile or run MOTU.

Source PAK SHA-256:
`2a35ebb9beea7388a6823205dad21e1a718da4b5f747ea09792c0a0e719aa2e0`.
The archive contains 1,052 entries, including 99 text files, 836 images,
25 BOR music files, 72 WAV files and five C script files. Build 4086 appears
in the external filename; no authenticated engine build was discovered.
The actual source exercises `know`, indexed PNG palettes, `alternatepal`,
`animationscript`, `@cmd`, inline `@script` and `colourdepth 32bit`.

## Source-derived target

| Set ID | Name | ifcomplete | Typed entries | Campaign scenes |
| --- | --- | --- | --- | --- |
| 0 | Demo | 0 (default; not explicitly authored) | 2 stages | 0 |

Authored route: `DATA/LEVELS/GUILE2.TXT`, then `DATA/LEVELS/HOLES.TXT`.
Only the second entry has `next`. The syntactic queues contain 33 and one
complete records respectively, with 21 and one spawns. Maximum complete
syntactic queue length is 33. GUILE2 also has a stray `at 1800` at physical
source line 244. Its dialect semantics remain unresolved; **34 is not a
certified packed-record total**. No source queue or control directive is
discarded from inspection.

The one loaded source player is `He_Man`, registry ordinal 3. `He_ManB` is a
`type none` weapon form, not another selectable player. Source enemy models
are `Knightbot` and `Skeletor`; neither declares a subtype. The full registry
in source order is Shock, Slash, Spark, He_Man, He_ManB, HBreath, HWWind,
ShWave, Skeletor, GeyserN, SkFBall, SkGeyser, SkGeyserT, SkTorn, Knightbot,
ShockBall. Source weapon/projectile/effect dependencies remain distinct
identities, and their script behavior is not implemented by inspection.

## Measured presentation decision

`HE-MANB.TXT:227` uses `@cmd spawn01 "HBreath" 18 93 0` in `freespecial4`.
HBreath's first frame supplies its source model palette. All its nonempty
frames match that palette. `HBREATH.TXT:26` references `BR12.PNG`, a 110×90
image with 2,751 nontransparent pixels. After collapsing RGB8 palette aliases
to RGB555, that frame still needs **204 distinct opaque colors**, or at least
**14 static OBJ palette banks**. The current SNES OBJ architecture has
**eight banks × 15 opaque colors = 120**. The deficit is 84 colors even if
the effect owns every OBJ palette and leaves none for actors. The whole
HBreath animation uses 213 RGB555 colors. Fifteen of its source frames exceed
the static limit.

The hardware basis is independently checked against
[Mesen2's SNES PPU implementation](https://github.com/SourMesen/Mesen2/blob/master/Core/SNES/SnesPpu.cpp):
three palette selection bits, four pixel color bits, transparent index zero,
and OBJ CGRAM starting at entry 128. The local implementation's hash is
recorded in the capacity JSON. Model palette authority follows the documented
[OpenBOR palette semantics](https://chronocrash.com/obor/wiki/palette/).

This proves a limit of the current static OBJ renderer. It does **not** prove
that every SNES rendering strategy fails. HBreath also declares `alpha 1`;
blend semantics and native transparency fidelity remain a separate capability.

| Alternative | Measured fidelity cost | Resource/performance consequence |
| --- | --- | --- |
| Explicit 120-color source reduction | Example changes 7.17% of animation pixels; channel RMSE 0.167 in 5-bit units | Uses all eight OBJ banks, leaving none for independent actor palettes; not an admitted gameplay solution |
| Explicit 90-color source reduction | Example changes 12.03%; RMSE 0.230 | Six OBJ banks, two remain; concurrent actors still need admission proof |
| Explicit 60-color source reduction | Example changes 19.10%; RMSE 0.336 | Four OBJ banks, four remain; geometry stays source-sized, but colors are adapted |
| Raster palette reuse | Could preserve RGB555 colors; feasibility unproven | Peak frame has at most 54 colors on a line and at most 32 newly required colors between adjacent lines; needs CGRAM scheduling, OAM index/bank proof and HDMA contention measurement |
| BG effect renderer/compositing | Could preserve RGB555 colors; feasibility unproven | Requires new BG/VRAM/transfer allocation beside background, foreground and HUD; changes the layer/presentation architecture |

Reduction figures come from a deterministic weighted greedy sample over all
animation frames, with source colors only. They are neither an optimal
quantizer nor visual acceptance, and do not include duration weighting.
**No source color reduction has been applied.** A new presentation policy
must be chosen before producing a candidate that could silently compromise
the authored effect. All ordinary parser, script, media and runtime gaps
remain engineering work after that decision.

## Capability accounting

These counts describe source uses, not unique features or native support:

| Classification | Count |
| --- | --- |
| SUPPORTED | 20 |
| SUPPORTED_ACCEPTED_COMPAT | 646 |
| BINDING_REQUIRED | 883 |
| GENERIC_CAPABILITY_MISSING | 81 |
| SOURCE_DIALECT_VARIANT | 33 |
| RESOURCE_LIMIT | 15 |
| UNKNOWN_SEMANTICS | 163 |
| NOT_USED | 1,611 |

`NOT_USED` denotes files outside the explicit campaign/registry inspection
scope, not proof that implicit engine hooks or dynamic scripts never reference
them. Keyword recognition is not a runtime certificate. The matrix records
locations, values, nearest existing capability, proposed resolution and
compilation blocking for every retained directive, plus schema/resource gaps.

| Addition | Classification | Scope |
| --- | --- | --- |
| `source_profile.py` and CLI discovery/diagnostics | GENERIC_BYOR_CAPABILITY | Read-only inspection, source structures, explicit failure |
| `source_palette.py` | GENERIC_BYOR_CAPABILITY | Source PNG/ACT model palette and alternate map decoding |
| `source_color_capacity.py` | GENERIC_BYOR_CAPABILITY | Reproducible color demand and sample alternative costs |
| `source_profiles.json` | GENERIC_BYOR_CAPABILITY | Immutable identity and policy catalog; original adapter only |
| Survey, routes, registry, palette data and asset identities | MOTU_SOURCE_DERIVED | Generated from the supplied PAK |
| RGB8-high-bits to RGB555 color conversion | ACCEPTED_COMPAT | Explicit hardware conversion, no additional reduction |
| Explicit MOTU production bindings | MOTU_BINDING | None yet |

No hand-authored MOTU campaign, spawn queue, model list or runtime identity
alias was added. No runtime capability code was added. No TMNT work began.

## Commands and evidence

```powershell
py -3.10 byor.py inspect --source "Masters of the Universe [v.3.0 Build 4086].pak" --output out/byor-motu-survey.json
py -3.10 byor.py inventory --source "Masters of the Universe [v.3.0 Build 4086].pak" --set Demo --output out/byor-motu-inventory.json
py -3.10 byor.py build --source "Masters of the Universe [v.3.0 Build 4086].pak" --set Demo --output build/byor-motu
py -3.10 tools/bor_compile/source_color_capacity.py --source "Masters of the Universe [v.3.0 Build 4086].pak" --model HBreath --role idle --output out/byor-motu-color-capacity.json
```

Inspect exits 0. Foreign inventory writes its report and exits 2. Build exits
2 with specific capabilities, including the 204/120 color requirement, and
creates no ROM/MSU candidate. The original adapter is selected by immutable
source identity, and no foreign-source build is delegated to it.

Local reproducible evidence:

- `out/byor-motu-survey.json`, `out/byor-motu-survey-capabilities.json`, `out/byor-motu-survey.md`
- `out/byor-motu-inventory.json` and neighboring matrix/summary (hardlinked to identical survey bytes)
- `out/byor-motu-color-capacity.json`
- `out/byor-motu-original-regression.json`
- `out/byor-motu-layout-results.json` and width/layout/label-drift logs
- `out/byor-motu-preservation/protected-before.json`, exact protected-file backups and status snapshot
- `docs/receipts/byor-motu-m4-partial.json` (compact result/hashes/footprint)

## Validation and nonclaims

Focused source-profile, palette, original Hard, Easy and Bonus tests pass.
The original Easy/Normal/Hard/Bonus inventories all report complete structural
coverage. Changed Python files pass `py_compile`; the focused diff passes
`git diff --check`. Native selectors were not rerun because runtime/assembly
code did not change.

The label drift guard passes (1,152 code labels, zero drift). The width guard
fails on **132 inherited violations**, and `audit_all.py` fails because it
includes that guard. Every tracked `src` and `tools/rom_audit` file was compared
to canonical HEAD and found identical. These failures are not reported as PASS
and need resolution before a future runtime candidate is certified.

The unchanged canonical symbols place `scpu_bank0_runtime_end` at `$FF9E` and
`nmi_handler` at `$FFA0`: exactly **two bytes free**. New capability code
consumes **zero bank-0 bytes**.

All 17 protected dirty tracked files retain identical sizes and SHA-256 hashes.
Nothing unrelated is staged. No PCM was converted or copied; no candidate
exists, so ROM/MSU hashes, candidate footprint and PCM companions are not
applicable. Evidence files remain bounded; duplicate survey/inventory payloads
share hardlinks. Historical evidence is retained.

Native boot/selector, full traversal, scenes, terminal completion, combat,
prop/pickup and resource admission are all **NOT_RUN**. There are no naturally
authored stage props/pickups in the discovered two-stage route; comments do
not count as source spawns. MOTU's final counter/return behavior has not been
certified. This receipt is not `BYOR_MOTU_COMPLETE`, arbitrary BOR/OpenBOR
support, universal Build 4086 compatibility, or a universal hardware limit proof.
