# Closed model-copy callback completion

B5SC admits animation scripts only and rejects every other model script kind,
including onmodelcopy. Entities constructed and copied exclusively under this
capability cannot initialize an onmodelcopy callback. The generic final-service
adapter uses this closed admission; it does not discard a declared callback.
Models needing callbacks require a different explicitly bound capability.

The adapter validates unacknowledged service 7, the actual checked B5SC/B4CO
model/program pair, matching clone slot/model, physical side and core addresses,
current model identity, restored original type and the retained initialized
animation instance. Clear/onkill entries and wide initialized values fault.
It then acknowledges 7 through the real transition owner, which clears the
request and reaches done state 2. No entity, variable or factor row is changed.
It allocates no state and does not own a snapshot.

The 158-case isolated native proof passes all sixteen authored descriptors,
two initialized states, slots 0, 1 and 127, and 62 stale owner/program/lease
guards. It checks full entity, relation, variable and factor storage plus CPU
context. The bounded receipt is
`receipts/byor-motu-model-callback-finish-native.json`. Reproduce with
`m4_model_scripts_service_native.py --finish-absent`.

The fixture installs the final-service request; the complete ordered model
transition is not certified by this leaf proof. Initial snapshot service,
remaining scalar installation, weapon-frame binding, live presentation and
Demo remain open. No production assembly, bank-0 code, color reduction or
PCM copies are added. The foreign profile remains unregistered.
