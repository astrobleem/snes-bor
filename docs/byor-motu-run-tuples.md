# Exact per-entity RUN snapshots

The existing canonical AI state already stores `running` at +4 of each
24-byte row at 42F400. Freeze state already stores `stalltime` and `turntime`
at +8 and +28 of each 40-byte row at 42E000. These fields must use those stores.

The missing RUN model-data fields are runspeed, runjumpheight, runjumpdist,
runupdown and runhold. Reading the current shared cached model during player
updates would be wrong: later cache inheritance can change that model while
the entity retains its earlier shallow copy.

The pinned inheritance policy copies all five RUN fields together whenever
the new cached runspeed is numerically zero. Under that policy every reachable
tuple is one initially compiled tuple. Immutable tuple handles preserve each
entity's snapshot independently of later cached-model mutations. Signed zero
and all other source binary32/int32 bits remain exact.

MOTU has two distinct declared tuples. The two player models share one; the
other models share the second. The B4RT table is 56 bytes including its header.
The full 128-entity handle array is 256 bytes instead of 2560 duplicate bytes.
This is exact data sharing, without numeric projection or color reduction.

`source_run_tuple_native.Copy` checks the actual cached RUN values against the
compiled tuple directory, then calls the real native entity model-data copier.
Only after it succeeds does Copy publish the entity handle. Read expands that
handle to the exact original 20 bytes. Unknown tuples and invalid owners fail
explicitly. Direct RUN property writes need their own admitted mutation owner;
this capability must not silently consult the shared cache as a fallback.

The native proof covers all sixteen source models, both low/high physical slot
regions and nine malformed-owner/value guards. It copies actual source model
data, executes actual cached-model inheritance, and verifies that the existing
entity snapshot remains unchanged while the shared cached RUN values change.
Sibling handles, actor bytes during Read, registers and stack are retained.

The controller arena plan uses 5264 bytes with 1136 remaining. RUN handles and
their 64-byte controls are appended; previous controller addresses are retained.
The controls contain B678 ready at +0, status at +2, slot/model at +4/+6,
captured handle at +8 and expanded tuple at +20..+39. Status 2 is complete and
3 is fault. Handle zero is uninitialized and fails Read.

CaptureCurrent validates and snapshots the current cached tuple without a
second entity core copy. Its isolated actual-constructor bridge runs after the
fresh model copier and before script binding/default callbacks. It preserves
the source's earlier exists=1 write: pinned spawn writes exists and increments
ent_count before copying modeldata. Clearing AI/player scalar state belongs at
the earlier zero-initialization boundary; reading the old side model there
would capture the wrong RUN tuple. The corrected proof observes tuple 2,
unchanged sibling handles and real authored SELECT completion in both directions.

The complete production constructor/model-switch owner still must initialize
and bind this capability under a real foreign workspace lease. The isolated
proofs do not register MOTU, bind player movement, or certify its Demo. No color
reduction is applied.
