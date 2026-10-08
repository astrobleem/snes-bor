"""Pinned check_special/player_check_special with real callback continuations."""
from enum import IntEnum
from source_player_run_4086 import KEYS


class Service(IntEnum):
    SET_IDLE = 1
    SMART_BOMB = 2
    SET_ANIMATION = 3


def execute(entity, context, energy):
    """energy(which) queries current live model/HP/MP/seal, including after yields."""
    if context['nospecial'] not in (0, 3) or entity['cantfire']:
        return 0
    if not (energy(0) or energy(1)):
        return 0
    entity['takeaction'] = 17
    entity['attacking'] = 1
    entity['idling'] = 0
    entity['combostep'] = [0]*5
    linked = entity['link']
    if linked is not None:
        linked['takeaction'] = None
        linked['link'] = None
        linked['grabbing'] = None
        entity['link'] = None
        entity['grabbing'] = None
        yield Service.SET_IDLE, linked
    model = entity['modeldata']
    if model['smartbomb'] and not model['dofreeze']:
        yield Service.SMART_BOMB, entity, model['smartbomb']
    entity['running'] = 0
    entity['velocity']['x'] = entity['velocity']['z'] = 0
    yield Service.SET_ANIMATION, entity, 'special', 0
    if entity['modeldata']['dofreeze']:
        context['smartbomber'] = entity
    if not context['nocost'] and not context['healthcheat']:
        field = 'mp' if energy(1) else 'health'
        descriptor = entity['modeldata']['animation'].get('special')
        if descriptor is None:
            raise ValueError('SOURCE_SPECIAL_POST_CALLBACK_ANIMATION_REQUIRED')
        value = entity[field] - descriptor['energycost']['cost']
        if not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError('SOURCE_SPECIAL_POST_CALLBACK_SIGNED_OVERFLOW')
        entity[field] = value
    return 1


def player_execute(entity, context, players, valid, energy):
    """Preserve input query order; clear the fresh post-callback player row."""
    if (not context['ajspecial'] or not valid('block')) and players[entity['playerindex']]['playkeys'] & KEYS['special']:
        key = KEYS['special']
    elif context['ajspecial'] and players[entity['playerindex']]['playkeys'] & KEYS['jump'] and players[entity['playerindex']]['keys'] & KEYS['attack']:
        key = KEYS['jump']
    else:
        return 0
    succeeded = yield from execute(entity, context, energy)
    if not succeeded:
        return 0
    entity['stalltime'] = 0
    players[entity['playerindex']]['playkeys'] &= ~key & 0xffffffff
    return 1
