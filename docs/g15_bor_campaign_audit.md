# G15 — Original Beats of Rage campaign audit

Status: audit and implementation plan only. No production source or content was
changed by this audit.

## Authority and current boundary

The authoritative input is `Beats of Rage Original [v.3.0 Build 4086].pak`
(SHA-256 `A2A55CDD5E1145E845607ECEC3AD85A342529492E7120449A928F3A6EAEA81D6`).
Its `DATA\\LEVELS.TXT` Easy set is the source of campaign order. Normal and
Hard repeat the same six-stage topology with difficulty-specific files. Bonus
is conditional on completion and is separate from the main six-stage campaign.

The Easy set contains 14 level parts in six stage groups. The current build
ships two converted original parts (`1BEASY.TXT` then `1AEASY.TXT`) and
ships no other original campaign part. Thus the main campaign has six groups,
one partially represented group, and 12 unshipped level parts. The original
bonus `extra.txt` is not part of the six-stage acceptance target.

## Campaign order

| Campaign stage | Set order from LEVELS.TXT | Easy level parts | Current state | boss / notable content |
|---|---:|---|---|---|
| 1 | 1 | 1AEASY -> 1BEASY -> 1CEASY | 1A and 1B converted and shipped, but current runtime starts 1B then hands off to 1A; 1C unshipped | Angel/Yamazaki; Trash/Chair/Table props |
| 2 | 2 | 2EASY | unshipped | Heavy boss; Biker-K'; Fence |
| 3 | 3 | 3AEASY -> 3BEASY -> 3CEASY | unshipped | Robert boss; Joe, K', Billy; furnace/steamer/crate |
| 4 | 4 | 4AEASY -> 4BEASY | unshipped | Mrbig boss; Jhun; Box/Crate |
| 5 | 5 | 5AEASY -> 5BEASY | unshipped | Eiji; Drum/Steamer |
| 6 | 6 | 6AEASY -> 6BEASY -> 6CEASY | unshipped | Rugal boss; hotel/boss scenes; dense final waves |
| — | after stage 6 | scene Rugal -> scene ending | scene adaptation not shipped for original campaign | Rugal animation scene, then ending/credits |
| Bonus | Bonus / ifcomplete 1 | extra.txt -> scene sewer | outside main six-stage target | optional bonus scene |

The source file names, including the split level parts, are the exact order
from `LEVELS.TXT`; filenames alone are not being used to infer ordering.

All Easy level files use the existing backdrop declarations (`background`,
`panel`, `order`, and sometimes `frontpanel`). The audit found these
event keywords across the campaign: `spawn`, `wait`, `group`, `boss`,
`health`, `map`, `item`, `coords`, `flip`, `alias`, `music`,
`bossmusic`, `hole`, `endhole`, `blocked`, `water`, `rock`,
`mirror`, `direction`, and `2pitem`. Per-file support status is below;
the level parser must preserve the source data even where runtime work is
deferred.

## Level and mechanic classification

| Feature/content | Classification | Audit result |
|---|---|---|
| background/panel/order/frontpanel | CONTENT_CONVERSION_ONLY | Existing BG/FP converters cover the declarations; each remaining level needs its own assets and stage record. |
| spawn, coords, flip, health, alias | ALREADY_SUPPORTED / CONTENT_CONVERSION_ONLY | Existing spawn-table path handles these fields; aliases remain presentation metadata. |
| item props (apple, meat, money, gold, 1up) | ALREADY_SUPPORTED / CONTENT_CONVERSION_ONLY | Existing prop/pickup path covers known item types; new source prop art may be needed for Box/Fence/Crate/Drum. |
| wait | ALREADY_SUPPORTED | Existing wait gate is implemented and gated. |
| group | ALREADY_SUPPORTED | Existing group metadata is implemented; dense groups still need capacity/runtime acceptance per stage. |
| boss flag | ALREADY_SUPPORTED / CONTENT_CONVERSION_ONLY | Boss path is implemented, but original bosses need real content assets or an explicit reskin decision. |
| map/remap | ALREADY_SUPPORTED / CONTENT_CONVERSION_ONLY | Existing remap conversion applies where source art has matching palettes. |
| music/bossmusic | CONTENT_CONVERSION_ONLY / AUDIO FOLLOW-UP | Carry metadata into stage records; do not expand audio architecture in G15 audit. |
| hole/endhole/blocked | SMALL_RUNTIME_GAP | These are real level semantics requiring focused source/runtime review. `blocked` is a pit-hazard flag, not scroll-back. |
| water/rock/mirror/direction/2pitem | CONTENT AUDIT REQUIRED | Preserve and classify per occurrence; do not assume keyword meaning from names. They are not current campaign-wide blockers until an occurrence is shown to affect reachable behavior. |
| openborscript references | SCRIPT_VM BLOCKED only if correctness depends on them | No Easy level entry was established by this audit as requiring a script for its core stage-clear path. Keep the VM shelved pending exact script-reference evidence. |
| scenes/animation | SCENE/PRESENTATION_ADAPTATION | Use text/static-image adaptations; no FMV or animation transport redesign. |

The dense final and multi-part stages are the first places to check for spawn
record count, simultaneous occupancy, and scene timing. Existing six-actor
capacity is not to be increased for this audit; content must be scheduled
within the accepted slot policy.

## Character and prop coverage

Distinct fighter names observed in the Easy campaign include Ralf, Jhun, Joe,
Yashiro, Shermie, Angel, Yamazaki, Heavy, Biker-K', K', Billy, Robert, Mrbig,
Eiji, K9999, and Rugal. Current real roster coverage includes Ralf, Jhun, Joe,
Yashiro, and the accepted TMNT/prop roster. Therefore the minimum player-visible
original-campaign additions are:

- ordinary recurring fighters: Shermie, Angel, K', Eiji, Billy, and Biker-K'
  (verify whether K and K' share source art before adding separate slots);
- bosses: Yamazaki, Heavy, Robert, Mrbig, K9999, and Rugal;
- existing Joe/Jhun/Ralf/Yashiro remain reusable.

The minimum should be reduced only after direct source comparison proves an
actor is a visual/mechanical duplicate. Do not add every asset in the PAK
automatically. Current runtime can deliberately reskin unresident ordinary
enemies, but bosses and recurring player-visible identities should be explicit
acceptance decisions.

Distinct prop/hazard names include Trash, Chair, Table, Fence, Box, Crate,
Drum, furnace, and steamer. Existing runtime art covers several of these
(Trash, Chair, Table and the accepted pickup set); Fence/Box/Crate/Drum and
the furnace/steamer hazards need content conversion or a documented faithful
adaptation. `1up` is already covered.

Required real animations are the existing role set (idle/walk/attack/pain/fall/
rise and boss behavior where applicable). The source also declares mechanics
such as `waiting`, `slide`, `grab`, `throw`, `special`, `jumpattack`,
and `attack2`; only mechanics already supported by the current runtime should
be claimed. Unsupported per-character moves remain a content/runtime decision,
not a reason to start a generic VM or transport rewrite.

## Script VM hard gate

The PAK contains OpenBOR script assets and scripts, but this audit did not find
a campaign-order entry proving that Easy stage completion depends on one.
The declarative level files contain the stage waves and gates directly. The
current position is therefore: no demonstrated script-VM blocker for the main
campaign. Any future script reference must name the exact file, call site,
visible behavior, and whether existing declarative conversion already covers
it before changing this classification.

## Audio reachability

The six-stage campaign makes its level `music`/ `bossmusic` metadata and
the Rugal/ending scene music reachable. The PAK scene files explicitly reference
`data/music/haha.bor` for Rugal and `data/music/time.bor` for ending and
sewer scenes. Per-level music/bossmusic fields must be cross-referenced against
`docs/audio_inventory.md` during each conversion batch. This audit does not
convert or repack audio and does not reopen accepted SOUND scope.

## Scenes

| Scene | Source behavior | Adaptation |
|---|---|---|
| Rugal | `rugal.txt`: music `haha.bor`, one GIF animation | Optional static/text boss interstitial; preserve skip behavior and boss-to-next-stage continuity. |
| Ending | `ending.txt`: music `time.bor`, five GIF pages (falla/fallb/consp/creds/thanks) | Required text/static-page adaptation using existing G10 machinery; no GIF/FMV subsystem. |
| Bonus sewer | `sewer.txt`: music `time.bor`, sewer and thanks GIFs | Optional bonus presentation, not required for the main six-stage target. |

## Recommended conversion order

1. **Batch A — finish stage 1:** convert and ship 1C, then normalize the
   campaign order to 1A -> 1B -> 1C with a real three-part transition gate.
2. **Batch B — stage 2:** convert 2EASY, exercising existing map/order,
   wait/group, prop, and boss metadata with one new original boss.
3. **Batch C — stage 3:** convert 3A/3B/3C, the first three-part stage with
   Robert, K'/Billy, and furnace/steamer/crate content. This exposes the first
   meaningful content-density and boss-identity batch.
4. **Batch D — stage 4:** convert 4A/4B with Mrbig and warehouse/pier props.
5. **Batch E — stage 5:** convert 5A/5B with the elevator/factory presentation,
   Eiji, and Drum/Steamer content.
6. **Batch F — final stage:** convert 6A/6B/6C with Rugal, dense final waves,
   and the Rugal scene handoff.
7. **Batch G — campaign reconciliation:** make 1P authoritative from title
   through all six groups, then ending/credits/title restart; run 2P campaign
   smoke without expanding mechanics.
8. **Optional Batch H — Bonus:** only after the main campaign is complete,
   audit `extra.txt` and the sewer scene.

Each batch must remain playable and end with a real transition gate. No batch
should introduce actor-count growth, animation transport redesign, or a script
VM.

## G15 acceptance

G15 final acceptance requires all six original campaign groups in the exact
source order, reachable bosses, identifiable supported actors, converted props
or explicit faithful adaptations, bounded spawn tables, carried music metadata,
1P completion through existing ending/credits back to title, a new-game restart,
and a 2P progression smoke pass. It does not require Double Dragon Moto,
generic OpenBOR script compatibility, unused characters/audio, actor-count
growth, or animation transport redesign.

Current explicit qualifications remain: no-target AI movement is
TOOLING-LIMITED / UNMEASURED; `confirmed_busy_denials` is null/unmeasured.

