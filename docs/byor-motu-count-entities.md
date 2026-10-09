# Readonly source entity counting

Pinned count_ents iterates the full ent_max array and counts literal exists truth with a matching type mask. It does not exclude dead entities. Corpse conversion to TYPE_NONE changes the count through type semantics instead. The private generic native service preserves full 32-bit masks, including negative masks and type bits, over the admitted 128-slot canonical pool. It rejects active rows beyond the world frontier and malformed active tokens. Inactive rows need no token dereference.

The A/Y input carries the low/high type-mask word. The service captures that input on its CPU stack, then supplies the actual canvas generation in X/Y to the workspace check. The first attempts incorrectly supplied the mask register to that check; the corrected 173-case native proof passes. Unmodified source C uses ent_max=128 for this admitted capacity and tests empty/full/edge frontiers, negative exists truth, dead corpses, full signed masks and malformed world/token/frontier guards. All actor rows remain readonly and caller CPU context is preserved.

This is a count service for the existing pool representation. Item spawning, boss completion, the production world producer and MOTU gameplay remain unbound. No bank-0 code, color reduction or PCM copying was introduced. See the [receipt](receipts/byor-motu-count-entities.json).
