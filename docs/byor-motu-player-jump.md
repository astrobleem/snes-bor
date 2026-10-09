The compiler derives a closed ordinary jump capability from all source models:
zero jumpmovex/jumpmovez and no JUMPSPECIAL or alternate air attacks. Runtime
noaircancel must be zero; other controls/profiles require another owner and fail
explicitly. This capability does not admit direct air-flag mutations.

The helper preserves source query order and the SPECIAL-before-ATTACK branch.
If SPECIAL is pressed but JUMPSPECIAL is absent, the ATTACK branch remains
suppressed. Otherwise ATTACK clears only its input bit and sets attacking before
readonly animation queries and the real default jump-attack frame. Zero air
controls leave velocities/direction unchanged after callbacks.

The unchanged complete player_jump_check passes 3072 comparisons in this
domain, including optional default animation and all four input rows. Sixty-four
native cases use the actual SELECT constructor and jump-attack frame owner,
checking query order, negative nospecial, simultaneous buttons, velocity and
RUN predicates, high input bits and actual animation identity. Input/velocity
context and helper entry are instrumented. Production jump state, wider air
controls, gravity/landing and complete player_think remain unbound.

The controller address plan uses 5864 of 6400 bytes, leaving 536. This is not a
production canvas lease. No color reduction or new bank-0 code is introduced.
