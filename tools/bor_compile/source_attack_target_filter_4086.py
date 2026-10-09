"""Ordered pinned do_attack target admission, before callbacks or damage.

Collision results are supplied by the caller; returned modes expose exact
short-circuit order. This predicate grants no damage or lifetime authority.
"""
FIELDS=('exists','dead','invincible','attack_type','attackone','lasthit_present','is_last','type','them','pain_time','time','takedamage','hit_by','attack_id','lie','otg','falling','jugglecost','jugglepoints','counterattack','normal_hit','counter_hit')


def decide(r):
    if set(r)!=set(FIELDS):raise ValueError('ATTACK_TARGET_FILTER_FIELDS')
    if any(type(v)is not int for v in r.values()):raise ValueError('ATTACK_TARGET_FILTER_INTEGER')
    for k in ('pain_time','time','hit_by','attack_id'):
        if not 0<=r[k]<=0xffffffff:raise ValueError('ATTACK_TARGET_FILTER_U32')
    for k in set(FIELDS)-{'pain_time','time','hit_by','attack_id'}:
        if not -2147483648<=r[k]<=2147483647:raise ValueError('ATTACK_TARGET_FILTER_I32')
    checks=(('exists',bool(r['exists'])),('dead',not r['dead']),
      ('invincible',r['invincible']!=1 or r['attack_type']==15),
      ('attackone',not(r['attackone']>0 and r['lasthit_present']and not r['is_last'])),
      ('type',bool(r['type']&r['them'])),('pain_time',r['pain_time']<r['time']),
      ('takedamage',bool(r['takedamage'])),('hit_id',r['hit_by']!=r['attack_id']),
      ('otg',not r['lie']and r['otg']<2 or r['otg']>=1 and bool(r['lie'])),
      ('juggle',r['falling']==0 and r['jugglecost']>=0 or r['falling']==1 and r['jugglecost']<=r['jugglepoints']))
    for name,ok in checks:
        if not ok:return dict(admitted=False,rejected=name,collision_modes=[])
    modes=[0]
    if r['normal_hit']:return dict(admitted=True,rejected=None,collision_modes=modes)
    if r['counterattack']:
        modes.append(1)
        if r['counter_hit']:return dict(admitted=True,rejected=None,collision_modes=modes)
    return dict(admitted=False,rejected='collision',collision_modes=modes)
