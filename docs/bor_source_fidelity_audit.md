# BOR source-fidelity audit

## G15 Batch E status (2026-09-10)

Original BOR `DATA\\EASY\\3CEASY.TXT` is imported at physical catalog index 14
and extends logical Easy progression through `3CEASY -> TITLE`. The Boat3
level preserves one panel/order entry, 31 ordered queue records, 30 spawns,
one group, a direct 1UP, two Crate/Meat records including one `2pitem`, and
the Robert/Steven boss record with health 300. It has no hole, `endhole`, or
`blocked` records. Furnace 34, Steamer 35, Crate 36, Robert 37, and Steam 38
are appended runtime-only identities; the selectable roster remains 13 and
actor capacity six. The accepted generic item/2pitem and identified-boss
paths are reused. Source `TYPE_STEAMER` periodic Steam child spawning is
implemented through a generic dynamic child-spawn runtime using the existing
actor windows. Steam children use the imported finite animation and retire
when it ends; a full pool safely skips an emission without overwriting a live
actor.

## G15 Batch D status (2026-09-10)

Original BOR `DATA\\EASY\\3BEASY.TXT` is imported at physical catalog index 13
and extends logical Easy progression to `1A -> 1B -> 1C -> 2EASY -> 3AEASY ->
3BEASY -> TITLE`. Its Boat data preserves three panels, 24 ordered panel
entries, 38 ordered queue records, 31 spawns, two waits, five groups, and four
Box obstacle records. Box contains Meat on two records (one source `2pitem`)
and Apple on two records. There are no hole, `endhole`, `blocked`, or authored
boss records; the final three K' records and trailing wait complete through
queue exhaustion. Batch C identities Angel 29, Shermie 30, K' 31, and Box 33
are reused; no new runtime primitive or identity was required. The selectable
roster remains 13 and actor capacity remains six. The physical catalog remains
separate from logical progression, so completion returns to TITLE rather than
falling through to TMNT/test content.

Status: source audit at the campaign/catalog separation checkpoint. This is
not a claim that the current SNES runtime is a complete BOR port. Source
authority is the local `Beats of Rage Original [v.3.0 Build 4086].pak`
(`A2A55CDD5E5...AEA81D`), then the original source/data where available.
Current SNES files are cited as implementation evidence only.

## Campaign structure

The BOR PAK's `DATA\LEVELS.TXT` defines three difficulty sets (`Easy`,
`Normal`, `Hard`) and a separate `Bonus` set. Easy's authored order is
`1A, 1B, 1C -> 2 -> 3A, 3B, 3C -> 4A, 4B -> 5A, 5B -> 6A, 6B, 6C`,
with `rugal.txt` before 6C and `ending.txt` after the set. `Bonus` is gated
by `ifcomplete 1` and loads `extra.txt` after `sewer.txt`. The current port
ships only the first three Easy parts.

The TMNT PAK's `DATA\LEVELS00.TXT` `Play_Demo` set authors
`SEWER0 -> STREETS -> STREETS2 -> SEWER`, with its story and ending scenes.
The physical stage catalog also contains standalone Bebop, Rock, Leather and
Foot records; those are not silently campaign links.

| Behavior | Source evidence | Current implementation | Classification |
|---|---|---|---|
| BOR Easy part order | BOR PAK `DATA\LEVELS.TXT` | Generated `CAMPAIGN_CONFIGS["BOR_ORIGINAL"]` | SOURCE_MATCH |
| Normal/Hard sets | BOR PAK `DATA\LEVELS.TXT` | Not selectable/loaded | SOURCE_FEATURE_MISSING |
| Bonus and `ifcomplete` | BOR PAK `DATA\LEVELS.TXT` | Not implemented | SOURCE_FEATURE_MISSING |
| Physical catalog is campaign order | No source evidence; contradicted by separate sets and standalone records | Previous `Game_StageIndex+1` behavior | PROJECT_INVENTION — REPLACE_WITH_SOURCE |
| Logical BOR/TMNT progression | Both PAK `LEVELS.TXT` files | Generated identity maps and `Game_CampaignId/Ordinal` | SOURCE_ADAPTATION; faithful for shipped paths |
| Incomplete BOR end | No source final boundary; port has only 1A-1C | Return to TITLE at generated BOR end | TEMP_DEV_SCAFFOLD |
| TMNT main campaign excludes standalone tests | TMNT `DATA\LEVELS00.TXT` | Explicit TMNT map excludes Bebop/Rock/Leather/Foot | SOURCE_MATCH |

## Boot, menus, and roster

The original BOR `DATA\MODELS.TXT` identifies normal BOR players as Kula,
Maxima, Mary and Mighty (the model `type player` declarations). The current
runtime-loadable roster is broader and includes AI/boss/prop identities; it
must not be confused with the source player-selectable set. The current
runtime normally selects Ralf/Jhun/Joe/Yashiro and carries a fixed P2 Leo;
that is implementation history, not BOR authority.

| Behavior | Source evidence | Current implementation | Classification |
|---|---|---|---|
| Boot enters title/menu flow | BOR menu/model data and normal game flow; no source evidence for direct gameplay boot | `src/main.pasm` initializes `GAME_STATE_PLAYING` for the development harness | TEMP_DEV_SCAFFOLD |
| BOR normal selectable players | BOR PAK `DATA\MODELS.TXT`, model `type player` | Current selectable prefix does not match Kula/Maxima/Mary/Mighty | PROJECT_INVENTION — REPLACE_WITH_SOURCE (P1) |
| Runtime-loadable vs selectable identity | BOR level/model references distinguish enemy/prop/player roles | `ROSTER_CONFIGS` includes AI-only and prop entries, but legacy `playable` flags are broader | SOURCE_ADAPTATION; selection policy remains unresolved |
| P2 fixed Leo | BOR PAK `MODELS.TXT` does not authorize fixed Leo as a second player rule | `G13_EnsureP2AfterStage` restores roster index 12 | PROJECT_INVENTION — USER_DECISION_REQUIRED |
| Fixed pre-game 1P/2P choice | No exact equivalent established from BOR source data | Current title/session path | UNRESOLVED |
| No mid-game join | No authoritative BOR rule established in the local data | Current session restriction | UNRESOLVED |
| Shared camera/tether | BOR source level geometry implies one playfield; exact multiplayer camera rule not established | Shared camera and tether | SOURCE_ADAPTATION; visible result plausible, source proof incomplete |
| No friendly fire | Exact source rule not established in available PAK data | Collision ownership excludes friendly damage | UNRESOLVED |

## Lives, scoring, combat, and actors

The project comment in `src/core/game_state.pasm` records that original BOR
does not expose the current 20-life stock concept. The exact original
death/continue/game-over contract therefore needs original BOR source/code
review before it is replaced. Level files and converted character data are
the authority for spawn identities, `health`, `boss`, `item`, `map` and
`music` directives; `tools/bor_converter/build_spawn_table.py` is the current
conversion evidence.

| Behavior | Source evidence | Current implementation | Classification |
|---|---|---|---|
| 20-life stock | `src/core/game_state.pasm` explicitly calls `GAME_LIVES_START=20` arbitrary; BOR source has no established lives field | P1/P2 stock and continue system | PROJECT_INVENTION — REPLACE_WITH_SOURCE |
| Death/continue/game-over | Original contract not settled by PAK alone | `src/core/game_state.pasm`, `core/player2_context.pasm` | UNRESOLVED |
| Hit/kill/item score values | Level/item data plus original scoring source required for exact values | `Game_Score_Award` and pickup collector | SOURCE_ADAPTATION; exact source parity audit pending |
| 1UP and threshold lives | PAK item identities establish 1UP existence; threshold semantics not established here | score threshold and 1UP award | SOURCE_FEATURE_MISSING / UNRESOLVED |
| `2pitem` ownership | BOR level keyword occurrences are source evidence; exact two-player semantics need original code | current collector ownership model | SOURCE_ADAPTATION; fidelity not yet proven |
| Movement/depth/facing | Converted character and level geometry; exact timing needs original code | SNES movement/camera/collision | SOURCE_ADAPTATION |
| Jump/grab/throw/special | Character files declare these animations; runtime role support is partial | only supported role subset is wired | SOURCE_FEATURE_MISSING |
| Friendly-fire damage | No direct source rule established | friendly damage disabled | UNRESOLVED |
| Identified boss spawn | BOR/TMNT level `boss` records and source character identity | identified bosses can reassign to converted assets | SOURCE_ADAPTATION |
| Ordinary enemy identity | Level spawns identify source fighters, but not all are roster-resident | many ordinary enemies render as a deliberate reskin | SOURCE_FEATURE_MISSING |
| Six fixed actor windows | No BOR source requirement for this SNES storage limit | G13 six-slot model | SOURCE_ADAPTATION; SNES constraint, behavior preserved for supported content |

## Level semantics

Occurrences must be read through the level parser, not keyword names alone.
The Easy campaign inventory is in `docs/g15_bor_campaign_audit.md`; the
current parser/runtime is in `tools/bor_converter/` and `src/core/spawn.pasm`.

The `SNES-BOR` and `1024` strings are `TEMP_DEV_SCAFFOLD` probes from the
old G1 renderer gate, not original Beats of Rage presentation. The revised G1
gate validates their DrawString/DrawNumber producer transactions and queued
DMA parameters at the diagnostic boundary; it does not require row 5 to
retain `1024` after later startup screens legitimately own that row.

| Keyword/feature | Source meaning/evidence | Current status | Classification |
|---|---|---|---|
| `wait` | Source wave/scroll gating in level files | trigger hold and camera clamp | SOURCE_ADAPTATION |
| `group` | Source wave grouping | declarative spawn records/group handling | SOURCE_ADAPTATION |
| `boss` | Boss spawn record and completion gate | boss flag, identity reassignment, boss HUD | SOURCE_ADAPTATION |
| `map`/remap | Source spawn/map directives | converter map fields and runtime map path | SOURCE_ADAPTATION |
| `health` | Source per-spawn health override | spawn table HP override | SOURCE_MATCH for converted uses |
| `item` | Source contained item/pickup identity | converted prop/pickup tables | SOURCE_ADAPTATION |
| `2pitem` | Source multiplayer item behavior | partial ownership path | SOURCE_FEATURE_MISSING |
| `hole`/`endhole` | Source hazard/level-end semantics | not implemented as a general hazard | SOURCE_FEATURE_MISSING |
| `blocked` | Source movement/scroll blocking semantics | only the supported wait/edge model is present | SOURCE_FEATURE_MISSING |
| `water`/`rock`/`mirror`/`direction` | Source environment/spawn directives | only encountered supported subsets are converted | SOURCE_ADAPTATION / SOURCE_FEATURE_MISSING by occurrence |
| openborscript references | Source script references in later content | no generic VM claim for campaign completion | SOURCE_FEATURE_MISSING; not yet a demonstrated BOR blocker |

## Stage clear, camera, audio, and scenes

The source level files provide trigger order, waits, groups, bosses, music and
scene references. The current `Spawn_LastTriggerX`, `Stage_TrueMaxX`,
`Stage_Cleared` and actor-alive checks are a derived SNES completion model.
They are faithful for the converted gates but are not themselves BOR source
semantics.

| Behavior | Source evidence | Current implementation | Classification |
|---|---|---|---|
| Scroll blocking/waits | BOR level `wait` records | `Spawn_PreClearHoldX` and camera clamp | SOURCE_ADAPTATION |
| Queue exhausted + actors dead + edge | No source statement in this exact form | current win predicate | PROJECT_INVENTION — REPLACE_WITH_SOURCE where exact source behavior differs |
| Music/bossmusic metadata | source level directives and `tools/audio/audio_manifest.json` | physical-stage music tables | SOURCE_ADAPTATION; missing reachable tracks are SOURCE_FEATURE_MISSING |
| Rugal scene | BOR PAK `DATA\SCENES\RUGAL.TXT` | not fully presented | SOURCE_FEATURE_MISSING |
| Ending/credits | BOR `ENDING.TXT` and scene data | G10 text/static adaptation | SOURCE_ADAPTATION; omitted visuals/music are explicit |
| Bonus sewer | BOR `ifcomplete`/`extra.txt`/`sewer.txt` | not shipped | SOURCE_FEATURE_MISSING |
| Static SNES scene presentation | SNES tile/text/image constraints | G1/G10 machinery and bounded adaptation | SOURCE_ADAPTATION |

## Difficulty and scope

Easy, Normal and Hard are separate authored sets in BOR `DATA\LEVELS.TXT`,
not merely a promise that one topology will be parameterized. Bonus is a
separate conditional set. The current Easy-only scope is a port milestone
cut, not source behavior. Excluding Bonus is likewise a scope choice until
its source gate and content are ported.

## Correction queue

Priority order for later approval:

1. **P0** — campaign structure and source-authored set/difficulty selection;
   the catalog/progression separation is the only P0 fix authorized in this
   pass. The incomplete BOR TITLE boundary is a temporary scaffold.
2. **P1** — source player roster/character selection and the fixed-P2 policy;
   replace project roster assumptions with source-backed player rules.
3. **P1** — death/continue/game-over model and exact score/1UP/`2pitem`
   semantics from original source.
4. **P2** — source-level hazards (`hole`, `endhole`, `blocked`), missing
   character mechanics, ordinary enemy identity, full difficulty sets and
   remaining campaign content.
5. **P3** — scene/ending visual fidelity, audio reachability, and presentation
   polish.

The following are explicitly not authorized here: broad gameplay rewrites,
generic script VM work, animation transport redesign, arbitrary actor growth,
Double Dragon Moto, and speculative cache redesign.
## P1 update: Mighty

The earlier conclusion that Mighty blocked the normal BOR roster is withdrawn.
The authoritative `DATA\CHARS\MIGHTY\MIGHTY.TXT` has no attack1 animation by
design, and original `BOR.C` explicitly dispatches missing `ANI_ATTACK1` to
`dojump(1)` and missing `ANI_FREESPECIAL` to `dojump(2)`.  This is a
`SOURCE_MATCH` target, not missing content or a reason to remove Mighty from
selection.  The packer/runtime must represent absent attack data as a zero
frame count and use the generic animation-presence condition.

## P1 implementation status

The runtime roster now appends the four source-normal BOR players without
renumbering existing AI, boss, TMNT or prop identities.  The generated
selection map is source ordered: Kula, Max/Maxima, Mandy/Mary, Mighty.  This
mapping is distinct from runtime roster indices.

Mighty's packed record has `attack_frame_count=0`; the existing jump system is
the target for the normal attack fallback.  The separate freespecial fallback
is not claimed as implemented unless the current command path has a real
reachable source-equivalent trigger.

## P1 current correction status

The source-normal player mapping is explicit and appended without renumbering
existing AI, boss, TMNT or prop identities: Kula -> runtime 22,
Max/Maxima -> 23, Mandy/Mary -> 24, and Mighty -> 25. Normal selection no
longer derives from the historical contiguous `playable` prefix, and the
pre-game P2 path resolves its independent source-normal ordinal rather than
forcing Leo. The older table entries above remain historical evidence of the
pre-P1 state.

Mighty's missing `attack1` is represented by an honest packed attack count of
zero. The generic player attack path recognizes a zero real attack-frame count
and routes through the existing jump state, matching BOR.C's
animation-presence branch without fabricating attack data. The source
freespecial `dojump(2)` branch remains `SOURCE_FEATURE_MISSING` for the
current reachable SNES command path because Mighty has no freespecial data.

The startup implementation now enters INTRO, presents bounded static/text
adaptations of the source logo and intro scenes, then reaches TITLE and the
currently available Easy set before player selection. State/order semantics
are `SOURCE_MATCH`; omitted GIF artwork/audio are `SOURCE_ADAPTATION`.
Direct PLAYING and direct TITLE boot scaffolds are removed from normal reset.

## P1-S1A score storage foundation

The S1A structural slice is validated separately from source scoring. Canonical
P1/P2 score state and the two HUD cache fields are now four-byte little-endian
fields in the audited WRAM block `$7E58D1-$7E58E0`. Their compatibility names
still address only the low words, so existing 16-bit runtime arithmetic and
HUD behavior remain intentionally unchanged. Reset paths clear all four bytes;
the upper words remain zero until the later source-scoring/HUD slices. The
build-time score-layout guard rejects address drift, overlap, and crossing the
adjacent G12/VM ownership boundaries. Source scoring semantics are not
implemented by S1A.

## P1-S1B 32-bit score display

S1B adds a bounded score-specific HUD renderer for unsigned values from 0
through 999999999. It compares and copies all four bytes of each canonical
score/cache field and leaves the existing generic 16-bit number path unchanged
for lives, stage, pause, and other callers. The score conversion uses audited
temporary scratch between the G1 telemetry and audio-stream regions, then
flushes through the existing shared text/DMA path. Score arithmetic and source
scoring call sites remain intentionally unimplemented until S1C; current
gameplay awards retain their old behavior.
## G15 Batch B status (2026-09-09)

Original BOR `DATA\\EASY\\2EASY.TXT` is now imported as the fourth logical BOR
Easy stage. Its 38-panel bridge scene, ordered 77-record spawn queue (including
three non-actor hole records), waits,
groups, Fence contained items, and Heavy boss record are packed at physical
catalog index 11. Campaign resolution is source-identity based:
`1A -> 1B -> 1C -> 2EASY -> TITLE`; TMNT and standalone records remain outside
the BOR campaign.

Heavy is an appended runtime-only identity (source type `enemy`, level boss
health 250, source model health 300, real idle/walk/fall/rise/attack1 data).
Fence is an appended runtime-only breakable identity with its source idle/fall
Biker-K' now has an appended runtime-only subtype identity. Its sparse source
idle/pain model drives the generic bounded biker movement state, and its five
authored records carry the source subtype bit without entering player select.
The three source `hole` directives are packed as non-actor records and use a
generic grounded pit-fall predicate with the source perspective bounds.

The current SNES representation is a documented source adaptation: fixed-point
coordinates and the existing jump/fall state stand in for BOR's floating-point
`checkhole()`/`toss()` path. `endhole`/`blocked` are not present in 2EASY and
remain unexercised rather than being claimed complete. Biker driver-spawn
behavior from `biker_takedamage()` is likewise outside the bounded 2EASY
subtype closure; the distinct Biker-K' drive and damage routing are represented.

The two 2EASY `2pitem` records use the accepted source predicate: the Fence's
contained item is revealed only with two active players; collection remains
ordinary collector-owned pickup behavior.

## G15 Batch C status (2026-09-10)

Original BOR `DATA\\EASY\\3AEASY.TXT` is imported at physical catalog index 12
and is the fifth logical BOR Easy stage: `1A -> 1B -> 1C -> 2EASY -> 3AEASY ->
TITLE`. The Boat level preserves six panels, 30 ordered panel entries, 31
active spawns, three waits, four groups, and its two Box records containing
Apple and Gold. It contains no hole, `endhole`, `blocked`, or `2pitem` record.

Angel, Shermie, K', and Billy are appended runtime-only enemy identities;
Box is an appended runtime-only obstacle identity. The normal 13-character
selection roster and six actor windows are unchanged. New enemy identities
use the shared identified-enemy spawn subtype, which streams their real model
without assigning boss status. Angel's source remap set contains five entries;
the SNES two-bit map field packs the first three source-ordered remaps, a
bounded presentation adaptation. The level has no authored boss flag; the
final Yashiro/Ralf/Billy wave completes through the existing queue-clear
boundary and returns to TITLE.

## G15 Batch L5 status (2026-09-11)

The BOR logical campaign now uses typed entries: 13 physical stage entries
followed by the generated Rugal scene entry (logical ordinal 13). The shipped
boundary remains `6BEASY -> RUGAL -> TITLE`; the source continuation to 6CEASY
is documented but not imported. Scene cleanup uses the same continuation path
for natural completion and skip, and campaign end selects TITLE without a fake
physical stage index. The direct scene test remains TITLE-continuing.
