"""Pinned ordinary arrow_move policy, with wall lookup an explicit service.

Homing and fall reactions require their own backends. Unsupported reactions
raise rather than substituting straight movement or deleting the projectile.
This reference preserves binary32 values; it does not integrate position.
"""
from source_model_core_4086 import binary32

SUBTYPE_CHASE = 11


def arrow_move(entity, *, level_present=False, checkwall=None, valid_fall=False):
    data = entity['modeldata']
    if data['subtype'] == SUBTYPE_CHASE:
        raise ValueError('ARROW_MOVE_HOMING_BACKEND_REQUIRED')
    direction = entity['direction']
    if direction == 0:
        entity['velocity']['x'] = binary32(-binary32(data['speed']))
    elif direction == 1:
        entity['velocity']['x'] = binary32(data['speed'])
    if level_present and data['subject_to_wall']:
        if checkwall is None:
            raise ValueError('ARROW_MOVE_WALL_QUERY_REQUIRED')
        height = checkwall(entity['position']['x'], entity['position']['z'])
        if height is not None and entity['position']['y'] < binary32(height):
            if valid_fall:
                raise ValueError('ARROW_MOVE_WALL_FALL_BACKEND_REQUIRED')
    entity['autokill'] = (entity['autokill'] | entity['ptype']) & 0xffffffff
    return 1
