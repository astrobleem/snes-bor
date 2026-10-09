# Literal source relation unlinking

The generic private EntUnlink service accepts a canonical physical actor slot and the expected canvas generation. It validates the target, optional linked pointer, frontier and token identities before any actor write. It then follows the pinned C order: clear the linked actor's link and grabbing fields, then the target's fields. It does not test exists or dead, since the source function does not.

The native proof passes 63 cases: 52 comparisons with unmodified ent_unlink C and eleven malformed-world/pointer/generation guards. It covers edge slots, null and distinct links, negative exists truth, inactive actors and dead actors. Full view, relation, core and lifecycle rows are checked against expected bytes, including unrelated actors, alongside caller CPU context. Rejected inputs write no actor fields. Bank 0 is unchanged.

A self-link is outside the admitted pointer domain. The literal C function clears e->link through the first assignment, then dereferences the now-null e->link in its next assignment. The initial C experiment faulted on this case; the native service explicitly rejects it before writes. It does not silently repair that source edge case. The source death-fields comment is also corrected: relation +60 holds an integer cached item model index, not an entity pointer.

The common damage callback's conditional unlink decision, pit/landing early returns, pain/fall services and callback acknowledgement remain unbound. No MOTU gameplay or completion is claimed. No color reduction or PCM copying occurred. See the [receipt](receipts/byor-motu-ent-unlink-native.json).
