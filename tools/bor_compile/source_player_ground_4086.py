"""Pinned player_think ground movement and its mandatory service boundaries.

Called only after the earlier controller gates and running cancellation.
The player row is the entry-captured row; callbacks may mutate the live entity.
"""
from enum import IntEnum
import struct
from source_player_run_4086 import KEYS


class Service(IntEnum):
    SET_ANIMATION = 1
    TOUCH_ITEM = 2
    WALK = 3
    BACKWALK = 4
    UP = 5
    DOWN = 6
    IDLE = 7


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def execute(entity, player, context, valid):
    action = 0
    velocity = entity['velocity']
    keys = player['keys']
    model = entity['modeldata']
    if context['min_z'] != context['max_z']:
        axis = 'up' if keys & KEYS['moveup'] else 'down' if keys & KEYS['movedown'] else None
        if axis:
            # validanim executes even when running is nonzero.
            if valid(axis) and not entity['running']:
                action = 2 if axis == 'up' else 3
                speed = model['speed']
            elif entity['running']:
                action = 4
                speed = model['runspeed']
            else:
                action = 1
                speed = model['speed']
            velocity['z'] = f32((-speed if axis == 'up' else speed) / 2)
        else:
            velocity['z'] = 0.0
    elif valid('duck') and keys & KEYS['movedown'] and context['notinair']:
        yield Service.SET_ANIMATION, entity, 'duck', 0
        # Source writes these after the frame callback returns.
        entity['velocity']['x'] = entity['velocity']['z'] = 0.0
        return

    # UP and LEFT retain source precedence for opposing held keys.
    direction = 0 if player['keys'] & KEYS['moveleft'] else 1 if player['keys'] & KEYS['moveright'] else None
    if direction is not None:
        model = entity['modeldata']
        if entity['direction'] == 1 - direction:
            if model['turndelay'] and not entity['turntime']:
                entity['turntime'] = (context['time'] + model['turndelay']) & 0xffffffff
            elif entity['turntime'] and context['time'] >= entity['turntime']:
                entity['turntime'] = 0
                if valid('turn'):
                    entity['takeaction'] = 'common_turn'
                    entity['turning'] = 1
                    entity['idling'] = 0
                    entity['velocity']['x'] = entity['velocity']['z'] = 0.0
                    yield Service.SET_ANIMATION, entity, 'turn', 0
                    return
                entity['direction'] = direction
            elif not model['turndelay'] and valid('turn'):
                entity['takeaction'] = 'common_turn'
                entity['turning'] = 1
                entity['idling'] = 0
                entity['velocity']['x'] = entity['velocity']['z'] = 0.0
                yield Service.SET_ANIMATION, entity, 'turn', 0
                return
            elif not entity['turntime']:
                entity['direction'] = direction
        else:
            entity['turntime'] = 0
        if entity['running']:
            action = 4
            speed = model['runspeed']
        else:
            if action not in (2, 3):
                action = 1
            speed = model['speed']
        entity['velocity']['x'] = f32(-speed if direction == 0 else speed)
    else:
        entity['velocity']['x'] = 0.0
        entity['turntime'] = 0

    # Caller performs find_ent_here, then didhit and didfind_item in source order.
    yield Service.TOUCH_ITEM, entity
    if action:
        entity['takeaction'] = None
        entity['idling'] = 1
    if action == 1:
        backward = 0
        level = context.get('level')
        if level is not None and valid('backwalk'):
            model = entity['modeldata']
            if model['facing'] == context['facing_right'] or level['facing'] == context['facing_right']:
                backward = int(not entity['direction'])
            # Preserve the literal second level-facing RIGHT test in BOR.
            elif model['facing'] == context['facing_left'] or level['facing'] == context['facing_right']:
                backward = entity['direction']
            elif (model['facing'] == context['facing_level'] or level['facing'] == context['facing_level']) and level['scrolldir'] & context['scroll_left'] and entity['direction'] == 0:
                backward = 1
            elif (model['facing'] == context['facing_level'] or level['facing'] == context['facing_level']) and level['scrolldir'] & context['scroll_right'] and entity['direction'] == 1:
                backward = 1
            elif entity['turntime'] and model['turndelay']:
                backward = 1
        yield Service.BACKWALK if backward else Service.WALK, entity
    elif action == 2:
        yield Service.UP, entity
    elif action == 3:
        yield Service.DOWN, entity
    elif action == 4:
        yield Service.SET_ANIMATION, entity, 'run', 0
    elif entity['idling']:
        yield Service.IDLE, entity
