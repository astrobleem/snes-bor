"""Complete source common_jump action with mandatory landing services."""
from enum import IntEnum
from source_model_core_4086 import binary32


class Service(IntEnum):
    SET_ANIMATION = 1
    SPAWN = 2
    ONSPAWN = 3
    SET_IDLE = 4


def inair(entity):
    a, b = entity['position']['y'], entity['base']
    return binary32(b-a if a < b else a-b) >= 0.1


def execute(entity, jumpland_role, valid):
    if inair(entity):
        return
    if entity['velocity']['y'] <= 0:
        entity['velocity']['y'] = 0
        entity['position']['y'] = entity['base']
        entity['jumping'] = 0
        entity['attacking'] = 0
        if not entity['modeldata']['runhold']:
            entity['running'] = 0
        entity['velocity']['z'] = entity['velocity']['x'] = 0
        if valid(jumpland_role) and entity['animation']['landframe'] == -1:
            entity['takeaction'] = 'COMMON_JUMPLAND'
            yield Service.SET_ANIMATION, jumpland_role, 0
            if entity['modeldata']['dust_jump_land'] >= 0:
                yield from spawn_dust(entity)
        else:
            if entity['modeldata']['dust_jump_land'] >= 0 and entity['animation']['landframe'] == -1:
                yield from spawn_dust(entity)
            if entity['animation']['landframe'] >= 0 and entity['animating']:
                return
            entity['takeaction'] = None
            yield (Service.SET_IDLE,)


def spawn_dust(entity):
    position = entity['position']
    dust = yield (Service.SPAWN, position['x'], position['z'], position['y'],
                  entity['direction'], None, entity['modeldata']['dust_jump_land'], None)
    if dust is not None:
        dust['base'] = entity['position']['y']
        dust['autokill'] = 2
        yield Service.ONSPAWN, dust


def jumpland(entity):
    if entity['animating']:
        return
    entity['takeaction'] = None
    yield (Service.SET_IDLE,)
