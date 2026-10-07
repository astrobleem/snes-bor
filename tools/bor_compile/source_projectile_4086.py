"""Named knife_spawn post-constructor semantics; allocation remains a service.

Only the named/indexed constructor branch is represented here. Weapon,
animation flash/knife, and implicit Knife/Shot lookups require their separate
source registry services. This reference does not admit a foreign profile.
"""
from source_model_core_4086 import binary32

def named_knife(owner, child, altitude, colourmap):
    if child is None:
        return None
    data=child['modeldata']
    child['ptype']=0
    child['a']=binary32(altitude)
    data['type']=32 if owner['modeldata']['type']&1 else owner['modeldata']['type']
    if owner['energycost']>0 and owner['nocost']:
        owner['cantfire']=1
    if not child['model_speed'] and not data['nomove']:
        data['speed']=2.0
    elif data['nomove']:
        data['speed']=0.0
    child.update(owner=owner['token'],nograb=1,attacking=1,think='common_think',
                 nextthink=(owner['time']+1)&0xffffffff,trymove=None,
                 takedamage='arrow_takedamage',takeaction=None,
                 remove_on_attack=data['remove'],autokill=data['nomove'],speedmul=2.0)
    data['aimove']=256
    if not data['offscreenkill']:
        data['offscreenkill']=200
    data['aiattack']=4
    selected=colourmap&0xffffffff
    child['map']=selected if selected<=data['maps_loaded'] else 0
    child['base']=child['a']
    for field in ('hostile','candamage'):
        if data[field]<0:
            data[field]=owner['modeldata'][field]
    if owner['modeldata']['type']&1 and (owner['nohit']or owner['saved_mode']):
        data['hostile']&=~1
        data['candamage']&=~1
    for field in ('subject_to_wall','subject_to_platform','subject_to_hole','subject_to_gravity','no_adjust_base'):
        data[field]=1
    return child
