"""Pinned check_attack control flow; collision/damage remain mandatory services."""


def decide(falling, projectile, drop, frozen, attacks_present, frame_attack_present, attack_id):
    for v in (falling,projectile,drop,frozen):
        if not isinstance(v,int) or not -0x80000000<=v<=0x7fffffff:
            raise ValueError('CHECK_ATTACK_SIGNED_DWORD')
    if not isinstance(attack_id,int) or not 0<=attack_id<=0xffffffff:
        raise ValueError('CHECK_ATTACK_ID_DWORD')
    if falling and not projectile:
        return dict(service='NONE',attack_id=0,events=[])
    if drop and not falling:
        return dict(service='NONE',attack_id=0,events=[])
    events=['is_frozen']
    if not frozen and attacks_present and frame_attack_present:
        return dict(service='DO_ATTACK',attack_id=attack_id,events=events+['do_attack'])
    return dict(service='NONE',attack_id=0,events=events)
