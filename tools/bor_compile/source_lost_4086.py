"""Pinned check_lost decision owner. Death/damage handlers are requirements.

Input coordinates are source binary32 values; native presentation is unbound.
In particular, the source parked-weapon Z sentinel 100000 is preserved here.
"""
from enum import IntEnum
from source_freeze_4086 import frozen


class Action(IntEnum):
    NONE = 0
    KILL = 1
    PLAYER_DIE = 2
    DAMAGE_PIT = 3
    DAMAGE_LIFESPAN = 4


def decide(s):
    osk = s['offscreenkill'] or s['default_offscreenkill']
    x, z, y = s['x'], s['z'], s['y']
    ax, ay = s['advancex'], s['advancey']
    vertical = s['direction'] in (16, 4)
    offscreen = (ax-x > osk or x-ax-s['hres'] > osk or
                 (not vertical and (ay-z+y > osk or z-y-ay-s['vres'] > osk)) or
                 (vertical and (z-y < -osk or z-y > s['vres']+osk)))
    life = s['lifespan']
    if (z != 100000 and offscreen) or y < -500:
        return dict(action=int(Action.PLAYER_DIE if s['type'] & 1 else Action.KILL), lifespan=life)
    if y < -250 or life < 0:
        if not s['takedamage']:
            return dict(action=int(Action.KILL), lifespan=life)
        return dict(action=int(Action.DAMAGE_PIT if y < -250 else Action.DAMAGE_LIFESPAN), lifespan=life,
                    attack_force=s['health'], attack_type=17 if y < -250 else 18,
                    dropv=list(s['default_dropv']))
    ent=dict(token=s['token'], type=s['type'], frozen=s['frozen'], freezetime=s['freezetime'])
    if not frozen(ent, ent, textbox=s['textbox'], smartbomber=s['bomber'], time=s['time']) and life != 0x7fffffff:
        life -= 1
    return dict(action=0, lifespan=life)
