# S8 selected Normal timer integration

Campaign 3 only. Easy classification and accepted 60 Hz actor callbacks are
unchanged. Timer and concrete host live in ROM bank 16; timer WRAM is exactly
`$7E5900..$7E591F`. Row ownership separately reserves `$7E5920..$7E5921`;
source search found no other occupants there. Opponent HUD owns `$7E5A00..$7E5ACF`.

Pinned BOR.C: `eba02fe6c9e97e388126c51560a92024f406d8c0`, SHA256
`68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41`.
Source timer resets to 40000, divides by 400 for display capped at 99,
and times out on the tick after reaching zero. Timeout uses real lethal
self-damage/fall/lives callbacks, source TIMEOVER audio, then reset/show.
The literal source duplicated-P1 absence test is retained, not corrected.

## Implemented wiring

- `core/nmi.pasm`: private field counter runs before BOTH busy skips.
- `core/game_state.pasm`: service before state/input events, level reset,
  continue/respawn/all-OUT lifecycle. Pauses consume elapsed fields without ticks.
- `core/jump.pasm`: physical-slot kind6 collection bypasses legacy reward/free.
  Time requires the physical collector's Y/attack edge; recognized denial and
  pending duplicates return handled without mutation. Success consumes the edge
  and selects available GET over the compat attack pose. Ordinary pickups keep
  accepted touch behavior, with James's HUD hooks after each Time intercept.
- `core/spawn.pasm`: five pending-slot reservations and wait-release reset.
- `main.pasm`: generic attack target walker excludes Time and pending items.
- `stage_timer_host.pasm`: real actor, unlink, HUD, GET, SFX and death callbacks;
  hide immediately, retain occupancy for 600 timer ticks, then retire.

Nominal target adapter: 10/3 timer ticks per NMI field, 5/3 gravity ticks.
Stalled main service catches up elapsed fields; no actor/world replay. Bounds
consumes `StageTimer_TakeGravityTicks`. This is ACCEPTED_COMPAT timing, not
source PIT or exact NTSC wall time. StartLevel never writes FieldCounter;
it snapshots the NMI-owned word. Current stage load also disables NMI.

## Visible timer reservation

BG3 row **11**, columns **11..19**, separate from opponent rows 6/10,
player rows 0..3/7..9, demo rows 4/5 and frontpanel rows 21..27.
`StageTimerHost_FrameService` calls `StageTimerHost_DrawTimer` for campaign3
PLAYING only. It consumes the actual `StageTimer_Display` snapshot and queues
one 18-byte transfer from immutable bank16 ROM rows: `TIME 00` through
`TIME 99`, or `TIME OVER`. Uses existing initialized font/palette/priority.
No TextStaging writes or direct PPU writes. Failed enqueue retries,
including restoring the timeout flag if its last visible snapshot was rejected.
Exit cleanup is owned by the host's dedicated RowOwned word, not ShowTimeOver.
The existing all-state FrameService queues an immutable 18-byte blank whenever
an owned row leaves Normal PLAYING (including pause, title, gameover and campaign
changes). Rejected cleanup retains ownership; accepted cleanup releases it.
Never-owned Easy does not clear anything. Pending destination DMA drains before
another draw/blank is queued, preventing stale draws after cleanup. Boot INTRO
initializes ownership after boot's full BG3 clear; StartLevel does not reset it.

## Other-owner integration / validation remaining

Main renderer must skip a physical actor when
`StageTimerHost_IsPendingOffset(X=actor byte offset)` returns carry set.
Moving the consumed prop off-world alone is not a proven rendering exclusion.
Bounds already skips pending slots and cancels on removal. Main owns generated
campaign/data linkage; Volta owns the actual TIMEOVER asset and constants.
James must retain the row11 reservation when changing HUD/menu layouts.

Focused validation: `python -B -m unittest discover -s tools/bor_compile -p
test_timer_contract.py -v` (single shell line). Twenty tests cover source oracle,
effect metadata, WRAM, clock/pause/stall boundaries, concrete module assembly,
ROM display glyphs, queued transfer and NMI reset ownership. Assembly fixtures
are not a production link or runtime proof. Combined production assembly still
requires main's generated campaign layout. No emulator or commit performed.
