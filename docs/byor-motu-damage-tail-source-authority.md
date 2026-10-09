# MOTU damage tail source authority

The pinned BOR 4086 post-checkdeath tail passes 2,008 compiled-C comparisons. The exact suffix of `common_takedamage` executes without edits. Coverage includes player/enemy rumble ordering, pit death, landing early return, conditional unlink, escape counters, weapon loss, death/fall selection, missing fall, grab/pain selection, and unsigned deadline wrapping. `GRAB_STALL` is 160 ticks and `GAME_SPEED / 2` is 100 ticks, verified from the pinned header.

The pinned model loader/default proof passes 217 cases, including all 16 authored models. Every model has zero `falldie`, `escapehits`, and `nopain`. He_Man and He_ManB use weapon-loss type CHANGE (3); the other models keep the ANY (0) default. The actual integer parsing helpers and directive switch blocks execute unchanged.

The literal `set_fall` body passes 768 C comparisons. Invalid attack types and unavailable requested animations fall back to type 0. If that animation is absent, the callback returns zero without flags or script execution. Animation/frame mutation precedes fall flags. Its braced unfreeze clears the deadline only when frozen is nonzero, unlike the unbraced pain macro. The effective fallback attack type reaches the onfall child.

Child services are instrumented in these source-authority fixtures. These receipts do not prove native tail dispatch, weapon loss, animation/frame services, production RAM ownership, gameplay, or MOTU completion. Native children must be joined before the common damage callback can be admitted. NO color reduction applied.

Evidence: [bounded receipt](receipts/byor-motu-damage-tail-source-authority.json). Local reproducible inputs and compiled output remain in the exact `out/byor-motu-damage-tail-*authority` and `out/byor-motu-set-fall-authority` directories named by that receipt.
