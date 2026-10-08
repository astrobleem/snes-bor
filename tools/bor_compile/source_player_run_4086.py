"""Pinned player_think running cancellation before ordinary movement.

oldrunning is captured before preinput/callbacks, while running, held keys,
velocity and runupdown are read at the actual cancellation point.
"""
from source_script_input import authority

KEYS = {r['name']: r['mask'] for r in authority()['keys']}


def retain(running, oldrunning, runupdown, keys, velx, velz):
    if not running:
        return running
    movex = int(bool(keys & KEYS['moveright'])) - int(bool(keys & KEYS['moveleft']))
    movez = int(bool(keys & KEYS['movedown'])) - int(bool(keys & KEYS['moveup']))
    runx = int(velx > 0) - int(velx < 0) if oldrunning else 0
    runz = int(velz > 0) - int(velz < 0) if oldrunning else 0
    if not runupdown:
        stop = movez or not movex
    elif runupdown & 4:
        stop = (not movex and not movez or
                movex and not movez and runx == -movex or
                movez and not movex and runz == -movez or
                movex and movez and abs(movex-runx) + abs(movez-runz) > 2)
    else:
        stop = not movex or movex == -runx
    return 0 if stop else running
