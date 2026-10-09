The charging service implements pinned BOR 4086 `player_charge_check` over
canonical actor/input state and the checked module-tail lease. Both JUMP and
SPECIAL must remain held. Otherwise it clears takeaction and charging before
calling actual set_idle, then yields until the real idle frame completes.

The unchanged C helper passes 256 cases, including callback-prefix order and
callback mutations. The native proof passes 64 cases across all four input rows,
both directions and all held-key combinations. It retains state while both keys
are held, and preserves fresh callback mutations when canceling charge. The
private fixture supplies actor/input mutations and resource leases; production
player dispatch and complete MOTU gameplay remain unbound.

The controller address plan uses 6104 of 6400 bytes, leaving 296. This plan is
not a production canvas lease. No bank-0 code or color reduction is introduced.
