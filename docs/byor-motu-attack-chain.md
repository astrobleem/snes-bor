# Source attack-chain continuation

`source_attack_chain_4086.py` follows pinned 4086 `perform_atchain`, including
source target-query order, the player range-check shortcut, ranged-chain search,
the literal `set_attacking` macro, and post-animation cleanup. A mandatory
animation service separates the prefix from the tail. The tail reads current
combo step, chain length, style, time and delay after callbacks.

The unmodified C function and header macro pass 4096 policy comparisons with
five callback mutation modes. The comparison includes ordered query traces and
163840 state bytes. Loader authority separately proves signed `combostyle`,
including default zero, missing arguments and repeated declarations. The
existing B4BC packed chain format remains unchanged; combostyle is a separate
mutable entity field.

`source_attack_chain_native.py` uses actual canonical combat, lifecycle, flags
and core rows, the existing B4BC chain reader, and the current model animation
cache. It requests target selection and frame-zero execution as distinct
continuations. No actor name selects native behavior. Invalid indices and
signed overflow fail explicitly. Scripts changing chain geometry require a
capability beyond the existing immutable B4BC reader.

The caller must serialize these services and lease 96 control bytes plus 128
signed combostyle rows. The compiler controller arena plan now uses 4720 bytes,
with 1680 bytes remaining. Existing input/command/costmove addresses are retained.
This plan does not initialize entity fields or grant runtime ownership by itself.

| Control | Meaning |
| --- | --- |
| +0 | B675 caller readiness |
| +2 | 0 idle, 1 running, 2 false, 3 target pending, 4 frame pending, 5 complete, 6 fault |
| +4 | Current entity slot |
| +6 | Selected animation role |
| +14 | Signed 32-bit target-result truth value |
| +18 | B676 response acknowledgement, cleared before every target request |
| +50 | Requested target animation role |
| +52 / +54 | Response slot / role echoes; both must match |
| +58 | Current unsigned 32-bit combodelay |

Begin returns 8001 for target pending and 8002 for frame pending. TargetResume
requires a fresh matching response. Finish requires actual animation owner
completion for the same slot and role; callers execute StartFrame, FrameOwner
and AnimationAck before Finish. Pending is not success.

The isolated native tests cover authored and synthetic chain rows in both
physical B4BC actor regions, timer boundaries/wrap, player/enemy type masks,
ranged searches, absent animations, malformed owners and undefined indices.
All calls enter with decimal mode set and preserve that flag while performing
binary source arithmetic. Target results and synthetic chain rows are
instrumented; the real target-search owner is still a production dependency.

The separate He_ManB final-chain-step fixture executes the real compiled frame
callback and native effect owners in both directions before Finish. A second
run mutates combo step/style/delay after that real callback and proves cleanup
and timer updates use those fresh fields. Sound and the exclusive payload lease
remain instrumented. These are focused helper proofs, not complete player_think,
combat, production canvas admission or MOTU Demo certification.

No color reduction is applied.
