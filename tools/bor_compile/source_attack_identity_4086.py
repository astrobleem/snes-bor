"""Pinned unsigned attack sequence, retaining its signed entity bit pattern."""

def assign(entity_id, sequence):
    if any(type(v) is not int or not 0 <= v <= 0xffffffff for v in (entity_id, sequence)):
        raise ValueError('SOURCE_ATTACK_ID_U32')
    if entity_id:
        return entity_id, sequence
    sequence = (sequence + 1) & 0xffffffff
    if sequence == 0:
        sequence = 1
    return sequence, sequence
