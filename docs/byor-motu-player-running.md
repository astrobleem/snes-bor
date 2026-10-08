# Source running cancellation

The running-cancellation block of pinned 4086 `player_think` is preserved in
the literal C authority harness. `source_player_run_4086.retain` follows its
directional cancellation, `runupdown` flags and previous-velocity tests.
`oldrunning` comes from function entry, before preinput callbacks. Current
running, held keys, model flags and velocity come from the cancellation point.
These values cannot be flattened into one stale snapshot.

The authority comparison passes 12672 cases: all sixteen directional input
combinations, fresh/existing runs, signed running values, signed/high-word
model flags and both velocity signs/zero. A nonzero running integer remains
unchanged when retained; cancellation writes zero.

The native predicate passes 6338 cases, including owner/busy guards. It takes
an exclusive 48-byte caller lease, without allocating canonical entity state.
All calls enter with decimal mode set; the predicate performs binary arithmetic
and restores flags, registers and stack. Operands remain unchanged. Velocity
inputs use the existing finite Q16 ABI and this predicate only tests sign/zero.

| Offset | Value |
| --- | --- |
| +0 / +2 | B677 ready / 0 idle, 2 complete, 3 fault |
| +4 | Current running int32 |
| +8 | Function-entry oldrunning int32 |
| +12 | Current runupdown int32 |
| +16 | Current held input keys uint32 |
| +20 / +24 | Current X/Z velocity signed Q16 |
| +28 | Retained/cancelled running int32 result |

The complete player owner still needs to bind canonical running storage,
capture oldrunning before preinput, and invoke this predicate at the source
position after attack/jump branches. Turning, ordinary movement and its
animation services remain separate dependencies. This is not player_think or
MOTU gameplay certification. No color reduction is applied.
