"""Pinned check_move with explicit movement/link services and no platform owner.

This function publishes displacement and nextmove, but does not run gravity.
Position/movement float stores preserve binary32 engine authority here.
"""
from source_model_core_4086 import binary32


def check_move(e, time, is_frozen, trymove=None, link_move=None):
    if e['update_mark'] & 4:
        return
    if e['landed_on_platform'] is not None:
        raise ValueError('CHECK_MOVE_PLATFORM_BACKEND_REQUIRED')
    x, z = binary32(e['position']['x']), binary32(e['position']['z'])
    if not is_frozen(e):
        if e['nextmove'] <= time:
            if e['movex'] or e['movez']:
                if e['trymove'] is not None:
                    if trymove is None and link_move is None:
                        raise ValueError('CHECK_MOVE_TRYMOVE_BACKEND_REQUIRED')
                    if e['grabbing'] and e['grabwalking']:
                        if link_move is None:raise ValueError('CHECK_MOVE_LINK_BACKEND_REQUIRED')
                        link_move(e['movex'],e['movez'])
                    else:
                        if trymove is None:raise ValueError('CHECK_MOVE_TRYMOVE_BACKEND_REQUIRED')
                        if trymove(e['movex'],e['movez']) != 1 and e['idling']:
                            e['pathblocked'] = (e['pathblocked'] + time % 2) & 0xffffffff
                        else:e['pathblocked'] = 0
                else:
                    e['position']['x'] = binary32(x + binary32(e['movex']))
                    e['position']['z'] = binary32(z + binary32(e['movez']))
            e['nextmove'] = (time + 1) & 0xffffffff
    e['movex'] = binary32(binary32(e['position']['x']) - x)
    e['movez'] = binary32(binary32(e['position']['z']) - z)
    e['update_mark'] = (e['update_mark'] | 4) & 0xffffffff
