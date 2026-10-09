"""Source ordering after collision, through ownership/ground rejection.

The caller supplies real event dispatch and inair services. An admitted result
requires the remaining item, blocking and damage body; it is not a hit commit.
"""


def top_owner(pool, slot):
    seen = set()
    while True:
        if not 0 <= slot < len(pool) or slot in seen:
            raise ValueError('HIT_PRELUDE_OWNER_GRAPH')
        seen.add(slot)
        owner = pool[slot]['owner']
        if owner is None:
            return slot
        slot = owner


def prelude(pool, attacker, target, old_self, contact, attack, current_id,
            event, inair):
    top = top_owner(pool, attacker)
    current_self = target
    for who, other, role in ((target, attacker, 0), (attacker, target, 1)):
        event(who, other, attack, role, current_id, current_self, contact)
    if not contact['confirm']:
        # The pinned engine restores temp only inside the confirm branch.
        return dict(required=False, didhit=None, source_self=current_self)
    didhit = int(top != top_owner(pool, target))
    if ((pool[attacker]['owner'] is not None and
         pool[target]['owner'] is not None) or
            (pool[attacker]['ground'] and inair(attacker))):
        didhit = 0
    return dict(required=bool(didhit), didhit=didhit,
                source_self=current_self if didhit else old_self)
