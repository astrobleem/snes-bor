# Model-transition palette identity

The generic compiler derives each model's declared or first-frame palette and
its ordered alternate palettes. B5MP holds a model directory and complete
256-entry RGB555 vectors. Source index zero stays transparent. The source RGB8
high-bit adaptation is unchanged; there is no color-count reduction. A
per-frame palette policy remains explicit and requires the frame consumer to
resolve that model's source palette. Unsupported remap/globalmap declarations
fail this capability rather than borrowing another model's palette.

The second model-transition colour service uses the existing constructor body
row: map at +48 and palette owner at +50. It validates the pending unacknowledged
service 6, current physical slot/token, side/core addresses, installed new model,
restored original type, model counts, constructor capability and body-row lease.
It clamps a selected map above the new model's maps_loaded to zero and retains
valid maps. Palette owner becomes the new model's identity. The exact map and
owner pair selects the compiled palette; the owner is not a hardware bank or
a fabricated engine pointer.

Only successful publication acknowledges service 6 through the actual native
transition owner. The owner reaches service 7 and clears acknowledgement. A stale
request faults without changing entity/body rows or acknowledging a service.
The 386-case native proof covers all sixteen authored models, slots 0, 1 and 127,
seven map values, the Skeletor and Knightbot alternate maps, and fifty stale
owner/row/lease guards. Entity storage and CPU context remain intact apart from
the two intended map/owner words. The source tables and native ROM are hashed
in `receipts/byor-motu-model-palette-service-native.json`. The compiled palette
table is 9,872 bytes and retains all nineteen source palette vectors.

The first colour service now also publishes that map/owner pair and invokes
the actual transition Ack, which calls the actual model-animation owner. Its
438-case native proof uses all authored B4AI/B4FE descriptors and the source
animation cache. It covers retained and clamped synchronized frames, exact
next-frame delays, restoration of previous entity type 1 from each new authored
type (including TYPE_NONE), and the service-5 continuation. Forty-six stale
owner/row requests are rejected before publication. Eight deliberately stale
animation children fault after successful map publication; the proof retains
that ordered partial state and does not claim transactional rollback. The
receipt is `receipts/byor-motu-model-first-palette-service-native.json`.

First-service core validation checks the physical address; original-type
matching applies only to the second service because ent_set_model must run
initialization under the newly installed type before restoring the original.
The synchronized branch does not execute frame-zero effects. Unsynchronized
initialization and its nested frame continuation remain separately owned.
The default service-6 emitted assembly is byte-identical to the prior commit.

This proves identity selection, not palette hardware admission or upload. The
complete weapon transition, live presentation and Demo remain open. The
isolated fixture installs the request lease. The foreign
profile remains unregistered. No production assembly, bank-0 code, new mutable
state, color reduction or PCM copies are added.
