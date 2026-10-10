# Player death authority and global state

The unchanged pinned player_die function matches the continuation plan in 7,200
literal C cases. The proof covers four player indices, lives and cheat behavior,
first-player clearing, rush preservation, no-player credits/joining timers,
weapon reset, respawn service order, enemy drop and level timer reset. Kill,
scripts and spawning are instrumented children. Initialized script mutations
and native player_die are not admitted by this source authority proof.

COUNTER_SPEED is GAME_SPEED * 2, or 400. The no-player continuation timer is
4,000 units and the no-credit timer is 200. The source duplicates joining[0]
checks and omits joining[2]/[3]; the plan preserves that behavior. It reads global
self again after the pdie script and retains the originally captured player index.

The new generic player-global lease uses 144 bytes following the existing 3,072
actor-state bytes in the compiled module's unused VM slot tail. The current
616-slot module leaves 48 bytes. Slots through 622 fit; 623 fails explicitly.
The lease stores only missing globals and player fields. Existing score/lives,
weapon selection, timer and actor rush state retain their original owners.

The native proof compares all words, the complete 8 KiB slot reservation,
adjacent actor state and the upper guard. It exercises signed DWORD extremes,
read-only access, initialization/release, matching module count/generation and
rejections. A replacement module with 1,024 live slots proves that failed lease
checks perform no writes even to the old control/status address: that address
may now belong to a live VM variable. CPU and decimal state are preserved.

Production installation, VM property bindings, actual pdie/respawn scripts,
player_die and spawning remain open. Bank 0 is unchanged, the width audit has
zero violations and all 17 protected hashes remain intact. No color reduction
or PCM copies are applied. [Receipt](receipts/byor-motu-player-die-state-native.json).
