# Model alpha and combo-style installation

The generic service-2 adapter installs source modeldata alpha and combostyle
after the actual entity-model copier has completed. It checks that copier's
success status and matching slot/model, canonical view and core addresses,
current side-model identity, constructor/body-row lease and world/model counts.
It calls the existing SourceForeignWork_Check with the caller's expected
32-bit canvas generation before touching the controller arena. Stale generation,
unretired frontpanel/water owners, invalid canvas target and a queued DMA read
from the overlaid arena reject the operation.

Alpha uses the existing sidecar +30 word. Combo style uses the existing
signed 32-bit entity rows in the derived foreign arena. Neither operation resets
entity lifetime, name, position, HP, animation, dynamic AI state, input history
or other controller storage. The adapter acknowledges service 2 through the
actual transition owner only after publication; the owner advances to service 3.

All 124 native cases pass: sixteen authored scalar records in slots 0, 1 and
127 plus 76 stale copier, request, row, generation, canvas and queue guards.
The fixture installs the completed copier request and canvas lease explicitly.
It compares full entity/body/style storage and CPU context. Authored HBreath
alpha 1 is preserved. This is scalar installation, not an alpha rendering proof.
The bounded receipt is `receipts/byor-motu-model-scalar-service-native.json`.

The complete ordered weapon transition and Demo remain open. No mutable storage,
production assembly, bank-0 code, color reduction or PCM copies are added. The
foreign profile remains unregistered. The arena still has eight unused bytes.
