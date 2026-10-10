# Whole-animation exact-context raster capacity

The generic animation checker derives every frame and its timing from source.
It examines complete exact additive operands, with geometry and per-bank
assignment relaxed, optimal initial residency and unlimited preloading.
These necessary bounds are not palette schedules or native admission.

All 40 HBreath idle frames have been checked in four explicit contexts:

| Context | Largest validated peak-write lower bound | Frame |
| --- | ---: | ---: |
| Effect alone | 14.428571 | 11 |
| Effect and player | 19.8 | 14 |
| Effect, player and one Knightbot | 19.8 | 14 |
| Effect, player and three Knightbots with mixed source maps | 23.8 | 14 |

The concurrent checks correlate the player frame with effect start ticks using
the supplied birth tick 48. The source parent is on frames 4, 4, 5, 5, then 6
for the rest of this animation. Its final frame lasts 240 ticks. This assumes
an uninterrupted parent animation. The queue admits three enemies; their poses
and exact combat reachability remain explicit inputs, as in the prior bounded
native hybrid proof. The three-enemy context uses camera 1800.

Every nonempty-frame LP reports validated primal and dual residuals below
the solver's checked tolerance. Source PNG hashes and exact final-context
RGB555 hashes are retained per frame. The wholly transparent last effect
frame has empty effect-only demand.

The three-enemy frame 14 bound requires at least **24 integer palette writes**.
Even with one free preloaded low byte, the earliest-to-latest high-byte commit
span is at least `16 * (24 - 1) = 368` master clocks. This exceeds the measured
356-clock legal window before address setup or runtime contention. It rejects
opaque/full-additive OBJ routing for this exact context, independently of
fixed-bank geometry, slot allocation and lookahead. It does not reject other
OBJ math modes, altered BG resource allocation or prove the pose's reachability.

Frame 11's largest raw source palette is consequently insufficient as the only
bandwidth test: frame 14 is worse with these concurrent source actors. No colors
or dimensions have been reduced. The [receipt](receipts/byor-motu-animation-raster-capacity.json)
retains all four artifacts and their per-frame bounds. Full native raster and
MOTU gameplay certification remain open.
