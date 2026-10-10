# Empty-terrain spawn at an integer horizontal camera

The generic compiled placement emitter now optionally adds the current horizontal
camera before publishing constructor inputs. Pinned BOR 4086 smartspawn passes
props->position.x + advancex to spawn on horizontal stages. Both integer operands
and their accepted signed Q16 sum are exactly representable in binary32.
Fractional camera, nonzero vertical camera, stale stage/lease, nonempty terrain
and arithmetic overflow fail explicitly. Overflow is checked before publication.
The default initial-camera assembly is byte-for-byte unchanged.

The native leaf passed 63 cases: eight index aliases at six cameras, fourteen
existing ownership/stage guards and a positive-overflow guard. Full input and
CPU scope comparisons check the resulting world coordinates and unchanged fields.
These build on the existing literal-C authored relative-placement authority.

The actual constructor join also passed both recovery/weapon cases with a supplied
camera of 1000. Native placement publishes X=1020, Z=165 and direction=1; the real
constructor publishes those world coordinates. The observer writes no actor
position. Authored JUMP frame zero, recovery/history and same-model weapon
continuations still execute. The camera API input and resource lease are supplied
by the isolated fixture; no live camera/scroller integration is claimed.

The [receipt](receipts/byor-motu-player-spawn-horizontal-camera.json) retains
native hashes and costs. Bank zero remains byte-identical. Full spawnplayer,
fractional camera handling, MOTU gameplay and Demo completion remain open.
No color reduction or PCM copies.
