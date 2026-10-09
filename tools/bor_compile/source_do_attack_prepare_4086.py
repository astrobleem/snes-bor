"""Pinned do_attack preparation before the ordered target loop."""
from source_attack_identity_4086 import assign


def prepare(pool,slot,completed,attack,sequence):
    if completed or attack is None:return None,sequence
    top=slot;seen=set()
    while pool[top]['owner']is not None:
        if top in seen:raise ValueError('DO_ATTACK_OWNER_CYCLE')
        seen.add(top);top=pool[top]['owner']
        if type(top)is not int or not 0<=top<len(pool):raise ValueError('DO_ATTACK_OWNER_POINTER')
    actor=pool[slot];mask=actor['projectilehit']if actor['projectile']>0 else actor['candamage']
    actor['attack_id'],sequence=assign(actor['attack_id'],sequence)
    return dict(topowner=top,them=mask&0xffffffff,attack_id=actor['attack_id'],force=attack['attack_force'],animation=actor['animation']),sequence
