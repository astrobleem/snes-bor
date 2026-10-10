"""Literal spawnplayer mutation plan with explicit terrain/constructor/weapon children.

This is source authority, not a native constructor or gameplay admission.
"""
import struct

SCROLL_LEFT=8
SCROLL_INWARD=32
SCROLL_OUTWARD=64
MAX_SPECIAL_INPUTS=27


def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]


def spawnplayer(state,index,checkwall,checkhole,smartspawn,set_weapon):
    index &= 3
    player=state['players'][index];level=state['level'];width=state['hres']
    sx,sz=level['spawn'][index];minimum,maximum=state['minz'],state['maxz']
    left=bool(level['scrolldir'] & SCROLL_LEFT)
    x=f32(width-sx if sx else width-20-30*index) if left else f32(sx if sx else 20+30*index)
    z=f32(sz if level['scrolldir'] & (SCROLL_INWARD|SCROLL_OUTWARD) else minimum+sz) if sz else f32(minimum+5 if maximum-minimum>5 else minimum)
    if z<minimum:z=f32(minimum)
    elif z>maximum:z=f32(maximum)
    found=False
    for _ in range(width//4):
        if x>width:x=f32(x-width)
        if x<0:x=f32(x+width)
        query_x=f32(state['advancex']+x)
        if minimum==maximum:
            wall=checkwall(query_x,z)
            if wall is not None and wall<state['max_wall_height']:break
            # C evaluates checkhole before the high-wall disjunct here.
            hole=checkhole(query_x,z)
            if hole or (wall is not None and wall>=state['max_wall_height']):found=False
            else:break
        else:
            for _ in range((maximum-minimum)//3):
                if z>maximum:z=f32(z-(maximum-minimum))
                if z<minimum:z=f32(z+(maximum-minimum))
                wall=checkwall(query_x,z)
                if wall is not None and wall<state['max_wall_height']:
                    found=True;break
                if wall is not None and wall>=state['max_wall_height']:
                    z=f32(z+3);continue
                if checkhole(query_x,z):
                    z=f32(z+3);continue
                found=True;break
            else:
                # Each unsuccessful C for-loop iteration also adds three.
                pass
        if found:break
        x=f32(x+(-4 if left else 4))
    descriptor=dict(name=player['name'],index=-1,itemindex=-1,weaponindex=-1,
                    colourmap=player['colourmap'],spawnplayer_count=-1,flip=0 if left else 1,
                    position=dict(x=x,y=0.0,z=z))
    state['currentspawnplayer']=index
    entity=smartspawn(descriptor)
    player['ent']=entity
    if entity is None:raise RuntimeError('PLAYER_SPAWN_FACTORY_NULL')
    entity['playerindex']=index
    entity['rush_max']=state['rush_saved'][index] if state['rush_policy']>=1 else 0
    player['combokey']=[0]*MAX_SPECIAL_INPUTS;player['inputtime']=[0]*MAX_SPECIAL_INPUTS;player['combostep']=0
    if player['spawnhealth']:entity['health']=player['spawnhealth']+5
    if entity['health']>entity['model_health']:entity['health']=entity['model_health']
    if player['spawnmp']:entity['mp']=player['spawnmp']+2
    if entity['mp']>entity['model_mp']:entity['mp']=entity['model_mp']
    set_weapon(entity,player['weapnum'] if player['weapnum'] else level['setweap'],0)
    return descriptor
