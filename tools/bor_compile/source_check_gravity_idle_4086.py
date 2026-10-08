"""Pinned check_gravity inactive-air branch, with explicit service boundaries.

The caller must execute actual adjust_base before freeze/air admission. This
reference does not replace moving airborne, ceiling, landing or script owners.
"""


def check_gravity_idle(entity,time,adjust_base,is_frozen):
    if entity['update_mark']&8:return
    adjust_base(entity)
    if not is_frozen(entity):
        due=entity['toss_time']<=(time&0xffffffff)
        airborne=bool(entity['falling']or entity['velocity_y']or entity['a']!=entity['base'])
        if airborne and due:raise ValueError('CHECK_GRAVITY_AIRBORNE_BACKEND_REQUIRED')
        if due:entity['toss_time']=(time+1)&0xffffffff
    entity['update_mark']|=8
