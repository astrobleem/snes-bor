# BOR source startup and player selection

This specification records the source-backed contract for the P1 fidelity
slice.  It is based on the original BOR `DATA\MODELS.TXT`, `DATA\LEVELS.TXT`
and the original `BOR.C` menu/player code.

## State graph

`startup()` -> logo scene/wait -> intro scene loop -> title prompt -> title
menu. The SNES presentation is a bounded static/text adaptation: production
reset enters `GAME_STATE_INTRO`, presents the logo card, presents the intro
card, and advances on Start to TITLE. Choosing Start game calls the port's
Easy set selector, then `selectplayer(p1on, p2on)`, then starts the selected
set's first level.

`choose_difficulty()` presents the authored set list from `LEVELS.TXT`, gates
locked entries with `ifcomplete`, wraps Up/Down, and confirms with a button.
The current port has only the Easy BOR content prefix; Normal, Hard and Bonus
must remain explicit availability/content work rather than silently aliasing
Easy.

Normal and Hard are source-authored but not converted in this build. The
current bounded menu exposes Easy only and never redirects an unavailable set
to Easy; this is a `TEMP_DEV_SCAFFOLD` until those sets are shipped.

`selectplayer()` owns an independent cursor, selected model and ready state for
each active player.  Left/Right changes only that player's cursor; any button
confirms that player.  The screen exits when every active player is ready.
The source does not establish a fixed P2 identity or a duplicate-character
restriction.

The current implementation follows that contract: P1 and P2 use independent
source-normal cursors/readiness and resolve through the generated mapping.
P2 is not rewritten to Leo in the normal BOR path. The physical layout is
slot 0=P1, slot 1=P2, slots 2-5=NPCs.

## SNES presentation adaptation

The source scene assets are `DATA\SCENES\LOGO.TXT` (`senile.gif`) and
`DATA\SCENES\INTRO.TXT` (`city.gif`, `flashes.gif`). The SNES build uses two
text/static cards because the GIF assets are not in the current tile pipeline.
Their order and input-driven transition to TITLE are preserved; the original
animation artwork and scene audio are omitted.

## Source-normal BOR players

The uncommented player models in `DATA\MODELS.TXT`, with their display names,
are ordered: **Kula**, **Max**, **Mandy**, **Mighty**.  `Max` resolves to the
Maxima model path and `Mandy` to the Mary model path.  The SNES runtime must
use an explicit selectable-ordinal-to-runtime-roster mapping; runtime-loadable
AI, boss, TMNT and prop identities are not thereby selectable.

## Mighty's missing attack animation

`DATA\CHARS\MIGHTY\MIGHTY.TXT` declares a player model and has no
`ANI_ATTACK1`/`attack1` animation.  This is intentional source behavior, not
missing conversion data.  Original `BOR.C` checks animation presence in the
normal attack path: when `ANI_ATTACK1` is absent it resets the combo step and
calls `dojump(1)`.  The missing-freespecial path similarly calls `dojump(2)`.
`dojump(speedmul)` marks the player jumping and attacking, selects the real
jump animation, applies the jump toss and multiplies horizontal launch speed.

The implementation target is therefore generic `attack_frame_count == 0`
dispatch to the existing jump system, with no fabricated attack frames and no
name check for Mighty.  The source freespecial command is represented only if
the current SNES command path is reachable; otherwise that specific path stays
documented fidelity debt.

## Runtime evidence

`tools/verify/game_bor_startup_select.py` proves cold reset -> INTRO -> TITLE,
Easy selection, four-player 1P selection, and independent 2P selection.
`tools/verify/game_bor_mighty_attack.py` proves the missing-attack fallback
and Kula's attack1 control.

## Evidence

- [Original BOR source repository](https://github.com/Plombo/beatsofrage)
- [Original BOR.C](https://raw.githubusercontent.com/Plombo/beatsofrage/master/BOR.C)
