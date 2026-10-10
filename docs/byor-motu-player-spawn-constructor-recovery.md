# Actual constructor joined to spawn recovery

The `--spawn-recovery-joint` isolated fixture joins the actual native player
constructor result to `SpawnRecovery_Apply`. Both source-derived player cases
pass. The constructor performs real slot selection, retirement/cleanup when
needed, factor copying, body/model/script installation, default initialization,
authored JUMP frame zero and completion before publishing the pointer result.
The join then installs the corresponding player role/global self and executes
the real recovery and input-history routines.

Observed recovery outputs are health/MP `22/-1` for saved values `17/-3`, and
`150/0` when saved values are zero. The latter retains the actual constructed
source values. Both cases compare player globals, the role records, constructed
entity view/core and all four history rows with zero mismatches. Existing native
constructor, script, effect, CPU-context and immutable-input checks also pass.
Recovery call costs are recorded separately from the full constructor wrapper.

The isolated join explicitly withdraws optional combat/physics readiness before
construction because it owns no such payloads. Earlier attempts rejected their
uninitialized borrowed-scratch flags. A real production installer must establish
all required owners and payloads; zeroing their flags is not a production binding.
The fixture grants the checked foreign canvas/global leases at the join and
retires the legacy water entry points through the existing generic water gates.

This closes a real child-to-recovery connection. Terrain placement, weapon child,
full `spawnplayer`, complete death/respawn, production dispatcher/renderer and MOTU
Demo remain unproven. All added proof code is outside production bank 0, whose
bytes match the baseline exactly. No PCM copies or color reduction were applied.
