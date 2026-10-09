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

Native canonical binding, smartbomb/freeze services, production input ownership
and full player_think still remain. This is not MOTU gameplay/completion certification.
No color reduction is applied.
