"""Pinned 4086 dojump body; every external effect requires a real owner.

Arguments are captured by value. Entity fields following a service are read
again, as in the source C body. No sound, spawn, toss or frame is acknowledged
by this reference implementation.
"""
from enum import IntEnum
from source_model_core_4086 import binary32


class Service(IntEnum):
    SOUND = 1
    SPAWN = 2
    ONSPAWN = 3
    TOSS = 4
    SET_ANIMATION = 5


def execute(entity, jumpv, jumpx, jumpz, jumpid, sample_jump, effectvol):
    jumpv, jumpx, jumpz = map(binary32, (jumpv, jumpx, jumpz))
    entity['takeaction'] = 'COMMON_JUMP'
    if sample_jump >= 0:
        yield Service.SOUND, sample_jump, 0, effectvol, effectvol, 100
    if entity['modeldata']['dust_jump_start'] >= 0:
        position = entity['position']
        dust = yield (Service.SPAWN, position['x'], position['z'], position['y'],
                      entity['direction'], None,
                      entity['modeldata']['dust_jump_start'], None)
        if dust is not None:
            dust['base'] = entity['position']['y']
            dust['autokill'] = 2
            yield Service.ONSPAWN, dust
    entity['jumping'] = 1
    entity['idling'] = 0
    yield Service.TOSS, jumpv
    entity['velocity']['x'] = binary32(-jumpx if entity['direction'] == 0 else jumpx)
    entity['velocity']['z'] = jumpz
    yield Service.SET_ANIMATION, jumpid, 0
