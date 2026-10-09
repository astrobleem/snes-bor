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

This proves identity selection, not palette hardware admission or upload. The
first colour service, complete weapon transition, live presentation and Demo
remain open. The isolated fixture installs the request lease. The foreign
profile remains unregistered. No production assembly, bank-0 code, new mutable
state, color reduction or PCM copies are added.
