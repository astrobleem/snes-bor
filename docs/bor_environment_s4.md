# S4 stage environment ABI

This is a capability increment, not complete source certification or content
publication. Normal/Hard/Bonus and the two foreign PAKs remain unpublished.
Full source diagnostics are in `bor_environment_s4_inventory.json`; exact
paths, line numbers and operands are retained, including foreign dialect errors.

## Source authority

Pinned [BOR.C](https://raw.githubusercontent.com/Plombo/beatsofrage/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C),
SHA-256 `68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41`.
`environment_semantics.py` records the source rules separately from target
adapters. In particular, source meaning is not inferred from runtime state IDs.

## Map representation

Before: StageIR retains an integer, but the accepted queue adapter clamps it
to 0..3 in byte 6 bits 3..4. The palette packer retained only three alternate
palettes. The entity map field was already a byte; palette address arithmetic
was already 16-bit `(index-1)*32`. These were two independent lossy boundaries.

Environment ABI v1 leaves the queue record at ten bytes:

| Field | Encoding |
|---|---|
| byte 5 bit 0 | facing, unchanged |
| byte 5 bits 1..6 | map bits 2..7 |
| byte 5 bit 7 | reserved, rejected by decoder |
| byte 6 bits 3..4 | map bits 0..1, unchanged |
| remaining fields | unchanged |

All 0..3 record bytes are identical. Six golden queue files change only these
selector bits. Runtime selection is a byte; a generated per-model count prevents
reading past available palettes. Undefined model maps select the base palette,
not the last alternate and not neighboring asset bytes. Valid existing maps
retain their palette addressing. The pinned historical source accepts 0..7;
negative/out-of-domain requests become base through its unsigned argument rule.
The target has 255 alternate-map capacity; an unknown dialect's normalization
rule remains blocked even if its numeric values fit.

`pack_character_blob(..., extended_maps=False)` is explicitly the historical
binary oracle, not the production emitter. Production uses `extended_maps=True`.
The source-driven v1 queue command first proves legacy reproduction, then
extends selectors; it never edits source IR or truncates records.

| Project/set | Maximum authored selector | Maximum declared alternate maps |
|---|---:|---:|
| BOR Easy | 5 | 6 (Eiji) |
| BOR Normal | 6 | 6 (Eiji) |
| BOR Hard | 6 | 6 (Eiji) |
| BOR Bonus | 6 | 6 (Eiji) |
| TMNT Play_Demo | 3 | 2 (foot01/02/03/05) |
| He-Man Demo | 1 | unresolved `palette` dialect, not zero-map certification |

Lobster declares five remaps: all five produce 160 palette bytes in the isolated
actor conversion, versus 96 in legacy mode. This closes its map representation
blocker only. Its fall-role attack remains a model/runtime blocker. No Lobster
identity or AI is installed. Original BOR declares 47 alternate maps total;
TMNT declares nine. He-Man's Skeletor, SkGeyserT and Knightbot use `palette`
constructs, not historical `remap` pairs. Their meaning is not guessed.

## Altitude and state ownership

The third `coords x z a` operand is a signed C integer in source pixels, default
zero. `z` is ground depth, while `a` is altitude. Spawn first assigns `a`;
smartspawn then applies type-specific rules. Ordinary enemy drop can override
authored altitude with randomized height. Player reentry can replace it with
an explicit jump. Nonzero altitude alone never identifies a jump or throw.

For `type steamer`, source smartspawn sets `base=a`. Its Steam child inherits
that base; Steam's thinker raises base and altitude together. This is fixed
elevation plus explicit rise, not gravity toward zero. The target uses a signed
Q16.16 parallel base, scaled by 4/5. Existing Q8.8 throw/jump displacement and
CHAR_SELECTED ownership remain separate. OAM subtracts base, then applies the
existing state-owned relative-Z offset. Steam rise uses Q16.16 `$00015555` per
60 Hz tick (source 100 ticks/sec at 4/5 spatial scale); quantization is explicit.

All original non-default stage uses are Steamer:

| Source files | Authored altitude | Target base |
|---|---:|---:|
| DATA\EASY\3CEASY.TXT; DATA\NORMAL\3C.TXT; DATA\HARD\3CHARD.TXT | +49 | +39.2 px, Q16.16 2569011 |
| DATA\EASY\5BEASY.TXT; DATA\NORMAL\5B.TXT; DATA\HARD\5BHARD.TXT | -5, three records each | -4 px, Q16.16 -262144 |

Only the five bindings in currently shipped physical records are emitted.
Other altitude drivers and unrepresentable signed target values fail closed.
There is no landing-to-ground assertion for a fixed-base emitter: source does
not give it one.

The focused probe also exposed tightly coupled pre-existing child/spawn issues:
the child must tail-enter the shared spawn exit's PHP/RTL contract, and slots
4/5 must distinguish PROP emitters from transient ENEMY children. The latter
path must call the spawn reset with an actual 16-bit accumulator. These fixes
are record-kind/driver based, not actor-name branches.

Two defects in the new implementation were caught and corrected before
acceptance: palette streaming requires DBR=0 for MMIO, and Poppy loses bank
metadata on label-plus-offset operands. Long table fields now include the
explicit data bank; the emitted-opcode test guards against recurrence.

## Alias and other environment verdicts

Aliases are per-spawn display names (20 source bytes), not source model names,
actor IDs, graphics identities or item effects. The generator binds 155 current
spawn instances to 89 distinct names. Runtime stores an independent alias ID.
The current HUD lacks the source general-opponent name display/tracking path:
**alias presentation remains blocked**, rather than being certified merely
because the string is preserved.

| Feature | Binding / verdict |
|---|---|
| ordinary hole | scaled queue control -> Spawn_CheckHole perspective predicate; accepted adapter, at most two positions; larger shapes fail closed |
| right / left / down | source axis transforms -> existing scroll metadata/camera machinery; no new scroll path |
| geometry/presentation | source image identity, dimensions, panel order -> accepted crop/scale/catalog adapter |
| water | bitmap/mode preserved; source texture-wave renderer has no complete runtime binding |
| blocked | preserved flag; source depth-dependent exit-X clamp is not implemented by a generic end-X clamp |
| endhole | preserved flag; source depth-dependent exit-pit predicate is not a stage-end sentinel |
| rock | time-driven visual rocking remains unbound |
| alias HUD | name metadata bound; general opponent presentation missing |

These remaining environment issues are real runtime gaps, not merely missing
certifier annotations. They are not relabeled MODEL to improve the headline
count. The scope does not rewrite working scroll/campaign behavior or introduce
an unreviewed replacement renderer.

## Resource contract

S3 queue ABI is unchanged: base `$7F9200`, ten-byte records, production capacity
92, maximum supported count 255. Production uses 920 bytes; complete Normal
needs 940; EXTRA needs 1840 for all 184 records. All fit the 3584-byte arena in
appropriately sized builds. TMNT/He-Man exact packed maxima remain unknown due
to their retained dialect/queue-shape diagnostics; recognized records are not
claimed as a full packing result.

Environment metadata reuses retired queue space without moving any actor or
following state: six 133-byte parallel rows at `$7E550F..$7E582C`, child scratch
`$7E5830..$7E5833`, next existing state `$7E5893`. This reserves 802 bytes over
an 805-byte extent, with 95 bytes before following state. Only six bytes per
actor are meaningful; the sparse stride intentionally preserves the actor ABI.
Generated environment tables have a 16 KiB budget and fail closed above it.

Production alternate palettes add 192 MSU bytes (Angel +2, Billy +1, Eiji +3).
VM offset: committed S3 `$585C50` -> final environment layout `$585D10`.
MSU size: 28,722,026 -> 28,722,218 bytes. No PCM content changes.
The ROM remains 4 MiB; additional metadata/code occupies previously unused
bank-13 space, not the nearly full bank-0 runtime region.

## Reproduction commands

Retain the hash-pinned S3 MSU as `out/bor_compile_s4/accepted_s3.msu` for legacy
oracle tests. It is an explicit input, not a committed binary or hidden dirty
queue dependency. The corpus unit test can instead regenerate legacy queues
and compare them with their committed S3 bytes.

```powershell
python tools/bor_compile/regenerate_queues.py 'Beats of Rage Original [v.3.0 Build 4086].pak' --msu out/bor_compile_s4/accepted_s3.msu --environment-v1 --install
python build_rom.py --reuse-audio-from c474617ee150b28b5b23677d89a9010b087dfa78
python -m unittest discover -s tools/bor_compile -p test_environment.py
python tools/verify/game_g15_s4_environment.py --output out/bor_compile_s4/runtime_final.json
```

Audio reuse verifies 121 unchanged source inputs, 25 PCMs and eight banks;
this does not claim a fresh rerun of the unrelated audio compiler pipeline.
No whole-campaign, SRAM restart, actor-AI or foreign-PAK production tests run.

## Final evidence and certification

`bor_environment_s4_runtime.json` contains 22 passing checks bound to the final
ROM/MSU hashes and the full trace hash. Each altitude case samples 180 frames.
Pre-existing NPCs are neutralized before each direct load; no new subject's
map, base, Z, selected state or queue index is injected. Organic Steamer OAM Y:
193 -> 154 for +49 source altitude, and 124 -> 128 for -5. Organic Angel map 4
in slot 4 matches all 32 CGRAM bytes. Children inherit/rise with zero throw Z
and no JUMP/THROWN classification. Negative-case failures from retained actors
in an earlier diagnostic fixture are preserved in `out/bor_compile_s4`, not
treated as accepted runtime evidence.

The 15 focused environment tests pass, including all 256 map selectors,
0..3 byte identity, full Lobster palette emission, source altitude/alias rules,
generated table reproduction and emitted ROM bank operands. Twelve focused
model/certification contract tests pass. Width audit: 0 new findings, 187
unchanged baseline findings. `py_compile`, diff whitespace checks and the
production ROM/MSU build pass. Campaign, scroll/music tables, roster and queue
ABI remain unchanged apart from the explicitly documented environment data.

Strict golden certification remains **0/24 stages before and after**, not a
weakened PASS. Rugal/Ending retain certified media bindings and byte-identical
payloads. Normal and Hard each remain 14 blocked stages plus two certified
scenes; Bonus remains 0/2. EXTRA still has 184 packed records, 166 spawns,
50 Crab, 27 Lobster, seven waits and eleven groups. SEWER still needs media
encoding/linking. Complete Normal is **not** blocked only by actor binding:
the alias HUD and actual environment gaps above also remain.

Compared with the saved S2 analysis, BOR loses 167 diagnostic occurrences:
75 stage map selectors, 80 repeated model-remap findings, and 12 nonzero
altitude findings. This is an occurrence count, not 167 distinct features.
TMNT and He-Man remove no blockers; they remain 0/6 and 0/2 fully certified
entries. Their map dialect assumptions are now explicit diagnostics (34 and
five occurrences) instead of the old unsupported implicit <=3 waiver.

Remaining groups:

- MODEL: fall/idle/walk-role attack dispatch; blast/burn/event contracts;
  Time timer-reset effect; unencoded Ramon binding; Crab noncombat drift;
  Lobster fall attacks. No new actor identities are installed.
- MEDIA: general alias/opponent-name HUD, SEWER encoding/linking, new actor
  assets/bindings. Existing Rugal/Ending media is unchanged.
- DIALECT: foreign PAK controls, palette declarations, map defaults, extended
  audio parameters and other retained unknown directives.
- RESOURCE/LINK: >255 maps, >255 queue records, >2 hole positions, signed
  base overflow, >16 KiB environment tables; incomplete foreign queue shapes
  prevent honest final size estimates. Unpublished full-entry links remain
  unissued rather than pretending to be production-ready.
- ENVIRONMENT (not disguised as MODEL): water texture waves, rocking,
  depth-dependent blocked/endhole predicates and complete alias presentation.

Final ROM SHA-256:
`35034ed9d838c0db9b078bb6fd71c5fe8039515fc42991cbfa99a62ebb97cbe3`

Final MSU SHA-256:
`b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`
