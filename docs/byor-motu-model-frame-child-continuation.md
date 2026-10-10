# Native model transition frame children

The generic model pipeline returns ticket 4 when animation synchronization requires
a real frame-zero child. It validates the model/animation-init identities and
matching slot before returning. After the child completes, the actual source
transition acknowledgement advances service 4; the observer never writes an Ack.

The frame owner consumes this ticket using the existing scoped nested-frame
stack. It executes the child's real scripts and effects, restores the waiting
parent, then resumes model script/factor copying. Both zero synchronization and
a missing current animation passed 12 native cases. These are explicitly
synthetic API/entity inputs at the real transition boundary. The missing role
is derived from the actual post-inheritance animation cache. Immutable authored
frame, weapon and script tables remain unchanged; this is not authored playback.

The synchronized nested-idle regression passed 40 cases. Actual synchronized
player dropweapon also passed. The caller audit found that dropweapon could
otherwise mistake a carry-clear ticket for completion; it now requires A=0 and
fails explicitly on an unconsumed child. The generic frame owner also checks its
completion result. These changes use private native code outside bank zero.
Bank zero remains byte-identical, and all 17 protected tracked hashes match.

The [receipt](receipts/byor-motu-model-frame-child-continuation.json) records
exact native artifact hashes, service traces and costs. Costs include interrupts
and do not establish a production tick budget. Standalone model transitions,
complete player spawning, gameplay resource ownership, the MOTU foreign profile
and Demo completion remain open. No color reduction was applied.
