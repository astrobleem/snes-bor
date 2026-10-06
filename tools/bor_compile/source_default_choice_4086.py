"""First animation service of ent_default_init, before type initialization.

This uses exact TYPE_PLAYER equality, unlike ent_set_model's bit test.
No candidate means no initial ent_set_anim call; later set_idle is separate.
"""
def choose(type,select,time,valid,spawn=23,respawn=104,selection=59):
    if (not select and not time) or type!=1:
        return next((n for n in (spawn,respawn) if valid(n)),None)
    if not select and time and type==1:
        return next((n for n in (respawn,spawn) if valid(n)),None)
    return selection if select and valid(selection) else None
