# Source placement and actual constructor join

The compiler derives source video mode 0 (320 by 240), ordered LEVELS walk bounds,
stage spawn offsets and horizontal direction. It evaluates literal spawnplayer
placement offline only for immutable empty wall/hole terrain. Nonempty terrain
requires a query owner explicitly. Camera translation remains a separate child.
No source identity selects an implementation branch.

The source Demo gives GUILE2 z bounds 160..240 and HOLES 220..232. Their four
relative x positions are 20, 50, 80 and 110, with z 165 and 225 respectively.
All sixteen authored/index-alias cases match the pinned C executable's full
80-byte records, including query-order digest. This reuses the checked authority;
it does not rerun the broad 5634-case proof.

The native initial-camera leaf passes 22 cases: eight index aliases and fourteen
stale lease, generation, stage, geometry, constructor, camera and player guards.
It checks all surrounding constructor controls and CPU context. Peak wrapper
cost is 6882 master clocks. ROM SHA256:
`698b267480a6726394577fc7a42743e2d5201317b5af9ba0e08253531cd45656`.

The actual constructor fixture additionally calls that native placement before
constructor Begin, then actual slot selection, model/body/factors/scripts,
authored JUMP frame zero, result publication, recovery and default weapon child.
Both generations publish native player slot zero at exact Q16 coordinates
1310720/10813440 (20/165). The observer does not write the published position.
Placement costs are 6414 and 6454 clocks, excluding the constructor and other
children. ROM SHA256:
`0758cec4f7edfe6458fa6a8c9572d204e7360b60f710806b730a2b08d8b16fff`.

The initial-camera emitter allocates no mutable arena and leaves bank zero
identical. Nonzero camera is rejected before input publication. The checked
media alias moves between owned fixtures; no PCM copies. This does not bind
moving-camera respawn, source smartspawn palette publication, selection,
full spawnplayer/world services or MOTU Demo completion. No color reduction.

Reproduce with `m4_player_spawn_inputs_authority.py`,
`m4_player_spawn_inputs_native.py`, and the actual constructor fixture's
`--spawn-placement-authority` option. Bounded receipts accompany this document.
