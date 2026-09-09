# BOR source startup and player selection

This specification records the source-backed contract for the P1 fidelity
slice.  It is based on the original BOR `DATA\MODELS.TXT`, `DATA\LEVELS.TXT`
and the original `BOR.C` menu/player code.

## State graph

`startup()` -> logo scene/wait -> intro scene loop -> title prompt -> title
menu.  Choosing Start game calls `choose_difficulty()`, then
`selectplayer(p1on, p2on)`, then starts the selected set's first level.

`choose_difficulty()` presents the authored set list from `LEVELS.TXT`, gates
locked entries with `ifcomplete`, wraps Up/Down, and confirms with a button.
The current port has only the Easy BOR content prefix; Normal, Hard and Bonus
must remain explicit availability/content work rather than silently aliasing
Easy.

`selectplayer()` owns an independent cursor, selected model and ready state for
each active player.  Left/Right changes only that player's cursor; any button
confirms that player.  The screen exits when every active player is ready.
The source does not establish a fixed P2 identity or a duplicate-character
restriction.

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

## Evidence

- [Original BOR source repository](https://github.com/Plombo/beatsofrage)
- [Original BOR.C](https://raw.githubusercontent.com/Plombo/beatsofrage/master/BOR.C)

