"""4086 movement policy with explicit geometric, random and script services.

Position stores use binary32. The measured 32-bit Watcom compiler spills the
reused common_trymove screen expressions to binary32, while testmove compares
unspilled expressions. This bounded authority reference records that policy;
it does not establish original-binary float equivalence or a native backend.
"""
from source_model_core_4086 import binary32 as f32


def testmove(e, sx, sz, x, z, world, services):
    m = e['modeldata']
    xd, zd = f32(x - sx), f32(z - sz)
    if not xd and not zd:
        return 1
    if m['subject_to_minz'] > 0 and zd and z < world['minz']:
        return 0
    if m['subject_to_maxz'] > 0 and zd and z > world['maxz']:
        return 0
    if m['subject_to_screen'] > 0:
        if x < world['advancex'] + 10 or x > world['advancex'] + (world['hres'] - 10):
            return 0
    if m['subject_to_hole'] > 0:
        if services.hole(x, z) and services.wall(x, z) < 0 and not services.below(x, z, e['y']):
            return -2
    if m['subject_to_obstacle'] > 0:
        other = services.find(x, z, 72)
        if other is not None and not other['platform_solid']:
            return 0
    height = e['anim_height'] or m['height']
    if m['subject_to_platform'] > 0 and services.between(x, z, e['y'], f32(e['y'] + height)):
        return 0
    if m['subject_to_wall'] > 0:
        wall = services.wall_below(x, z, 999999.0)
        if wall >= 0 and world['wall_height'] > e['y']:
            if services.valid('jump') and sz < world['wall_z'] and sz > world['wall_z'] - world['wall_depth']:
                if world['wall_height'] < e['y'] + e['jump_range']:
                    return -1
            return 0
    return 1


def common_trymove(e, xd, zd, world, services):
    xd, zd = f32(xd), f32(zd)
    if not xd and not zd:
        return 0
    m = e['modeldata']
    if m['type'] & 1 and services.rand() & 7 == 0:
        if (services.valid('throw') or services.valid('grab')) and e['idling']:
            other = services.find(e['x'], e['z'], m['hostile'])
            if other is not None and services.grab(other):
                return 0
    ox, oz = xd, zd
    x, z = f32(e['x'] + xd), f32(e['z'] + zd)
    if m['subject_to_minz'] > 0 and z < world['minz']:
        zd = f32(world['minz'] - e['z'])
        services.event('blockz')
    if m['subject_to_maxz'] > 0 and z > world['maxz']:
        zd = f32(world['maxz'] - e['z'])
        services.event('blockz')
    if m['subject_to_screen'] > 0:
        lo, hi = f32(world['advancex'] + 10), f32(world['advancex'] + (world['hres'] - 10))
        if x < lo:
            xd = f32(lo - e['x'])
            services.event('blocks')
        elif x > hi:
            xd = f32(hi - e['x'])
            services.event('blocks')
    if not xd and not zd:
        return 0
    x, z = f32(e['x'] + xd), f32(e['z'] + zd)
    needhole = False
    if not m['type'] & 1 and e['idling'] and (not e['frame_base'] or e['frame_base'] < 0) and m['subject_to_hole'] > 0:
        if not services.inair() and not m['aimove'] & 65536:
            needhole = True
            if zd and services.hole(e['x'], z) and services.wall(e['x'], z) < 0 and not services.below(e['x'], z, e['y']):
                zd = 0.0
            if xd and services.hole(x, e['z']) and services.wall(x, e['z']) < 0 and not services.below(x, e['z'], e['y']):
                xd = 0.0
    if not xd and not zd:
        return 0
    x, z = f32(e['x'] + xd), f32(e['z'] + zd)
    if m['subject_to_obstacle'] > 0:
        previous = None
        other = services.find(x, e['z'], 72)
        if other is not None and (other['x'] > e['x'] if xd > 0 else other['x'] < e['x']) and not other['platform_solid']:
            xd, previous = 0.0, other
            services.event('blocko', other['token'])
        other = services.find(e['x'], z, 72)
        if other is not None and (other['z'] > e['z'] if zd > 0 else other['z'] < e['z']) and not other['platform_solid']:
            zd = 0.0
            if previous is not other:
                services.event('blocko', other['token'])
    if not xd and not zd:
        return 0
    x, z = f32(e['x'] + xd), f32(e['z'] + zd)
    height = e['anim_height'] or m['height']
    if m['subject_to_platform'] > 0:
        if xd and services.between(x, e['z'], e['y'], f32(e['y'] + height)):
            xd = 0.0
        if zd and services.between(e['x'], z, e['y'], f32(e['y'] + height)):
            zd = 0.0
    if not xd and not zd:
        return 0
    x, z = f32(e['x'] + xd), f32(e['z'] + zd)
    # common_trymove intentionally tests truth here; testmove tests > 0.
    if m['subject_to_wall']:
        if xd and services.wall_below(x, e['z'], 999999.0) >= 0 and world['wall_height'] > e['y']:
            xd = 0.0
            services.event('blockw', 1, world['wall_height'])
        if zd and services.wall_below(e['x'], z, 999999.0) >= 0 and world['wall_height'] > e['y']:
            zd = 0.0
            services.event('blockw', 2, world['wall_height'])
    if not xd and not zd:
        return 0
    x, z = f32(e['x'] + xd), f32(e['z'] + zd)
    result = testmove(e, e['x'], e['z'], x, z, world, services)
    if result <= 0 and (result != -2 or needhole):
        return 0
    e['x'], e['z'] = f32(e['x'] + xd), f32(e['z'] + zd)
    if xd:
        services.event('movex')
    if zd:
        services.event('movez')
    return 2 - int(xd == ox and zd == oz)


def player_trymove(e, xd, zd, world, services):
    return common_trymove(e, xd, zd, world, services)
