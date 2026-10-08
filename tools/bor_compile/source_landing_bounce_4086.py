"""Pinned landing velocity/toss branch; external effects are ordered services."""
from source_model_core_4086 import binary32 as f32


def bounce_predicate(entity, autoland):
    return bool(entity['animation_bounce'] and abs(entity['velocity_y']) > 1.5
                and not ((autoland == 1 and entity['damage_on_landing'] == -1)
                         or entity['damage_on_landing'] == -2))


def toss(entity, lift, time):
    lift = f32(lift)
    if not lift:
        return
    entity['toss_time'] = (time + 1) & 0xffffffff
    entity['velocity_y'] = lift
    entity['a'] = f32(entity['a'] + f32(.5))


def landing_velocity(entity, time, autoland, *, quake, sound, rumble,
                     has_level=True, sample_fall=-1):
    """Position/falling publish precedes this branch in check_gravity."""
    if bounce_predicate(entity, autoland) and entity['model_bounce']:
        factor = entity['animation_bounce']
        entity['velocity_x'] = f32(entity['velocity_x'] / factor)
        entity['velocity_z'] = f32(entity['velocity_z'] / factor)
        toss(entity, f32(-entity['velocity_y'] / factor), time)
        if has_level and not (entity['noquake'] & 1):
            quake(4)
        if sample_fall >= 0:
            sound(sample_fall)
        if entity['type'] & 1:
            rumble(entity['playerindex'], int(100 * int(entity['velocity_y']) / 2))
        for player in range(4):
            rumble(player, int(75 * int(entity['velocity_y']) / 2))
        return True
    if entity['frame_base'] <= 0 and entity['frame_move_y'] <= 0:
        entity['velocity_x'] = entity['velocity_z'] = 0.0
    entity['velocity_y'] = 0.0
    return False
