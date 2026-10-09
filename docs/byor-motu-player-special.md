Pinned BOR 4086 check_special differs from check_costmove. Special eligibility
is HP first, then MP; resource debit occurs after linked-idle, immediate
smartbomb and special-animation callbacks. The debit uses fresh model, MP, HP,
cost flags and energy descriptor fields. It cannot reuse the costmove prefix.

The generic continuation keeps linked-idle, smartbomb and animation as mandatory
services. It preserves unlink order, resets all five combo steps, stops running,
and applies dofreeze after the animation returns. player_check_special preserves
BLOCK/key query order and clears only the selected key from the fresh player row
after callbacks; it then resets stalltime. Unsupported post-callback missing
descriptors or signed resource overflow fail explicitly.

The authority proof compares 4,096 cases and 933,888 bytes against unchanged
check_special, player_check_special, check_energy and ent_unlink functions, with
the pinned set_attacking macro. It compares ordered queries/services and final
state. Five callback modes cover resource, descriptor, dofreeze, cost-flag,
player-index and velocity mutations. Callback services are instrumented here.

The native 192-byte continuation passes all 4,096 authority cases and eight
guards with the same ordered queries/services and callback mutations. HP/MP and
BLOCK queries remain readonly external services; linked idle, smartbomb and
SPECIAL animation remain mandatory callback services. It retains the selected
key through callbacks, debits fresh resources after animation, and clears only
that key from the fresh player-index row. Missing post-callback descriptors,
invalid player indices and signed debit overflow reject explicitly. Decimal
entry and CPU retention are checked natively. The clock peak includes fixture
runtime/NMI activity and is not a production frame-budget admission.

The canonical binding now captures current HP/MP, action/flags, link/grabbing,
RUN velocities, combo state, stalltime, source player index and all four input
rows. It validates typed actor tokens, current model and linked pointers before
publication. Source-derived `NO_MODEL_SMARTBOMB` admission establishes the calloc
smartbomb/dofreeze values for these models; a smartbomb declaration rejects this
capability. Context flags remain explicit caller inputs.

Twenty native cases use actual SELECT construction, independent canonical HP/MP
queries and the real SPECIAL frame owner. They cover both directions, HP-first
short circuit, callback-time HP/MP/player-index changes, no-cost bypass, and
three rejection paths retaining every observed actor/input byte. Linked peers
exercise actual unlink and set_idle, both with IDLE already retained and with
an actual peer IDLE frame completing before the root SPECIAL frame. The peer
state and post-callback mutations are instrumented; this is not a full linked
actor constructor or production gameplay proof.

The controller address plan uses 5760 of 6400 bytes, leaving 640. It does not
grant the production canvas lease. Production input ownership, full player_think,
model smartbomb/freeze services and MOTU gameplay/completion still remain.
No color reduction is applied.
