"""Source jump-entry and delayed-jump continuations with mandatory services.

The readonly lane has no SLIDE/RUNSLIDE/RUNJUMP/FORWARDJUMP. Queries retain
their source order. TRY_JUMP and DO_JUMP require their complete owners.
"""
from enum import IntEnum
from source_player_run_4086 import KEYS
from source_model_core_4086 import binary32


class Service(IntEnum):
    TRY_JUMP=1
    SET_ANIMATION=2
    DO_JUMP=3


def execute(entity,player,notinair,roles,valid):
    if not(player['playkeys']&KEYS['jump'] and notinair):return 'CONTINUE'
    player['playkeys']&=(~KEYS['jump'])&0xffffffff
    model=entity['modeldata']
    if entity['running']:
        if player['keys']&KEYS['movedown'] and valid(roles['runslide']):
            raise ValueError('PLAYER_JUMP_ENTRY_RUNSLIDE_OWNER_REQUIRED')
        if valid(roles['runjump']):raise ValueError('PLAYER_JUMP_ENTRY_RUNJUMP_OWNER_REQUIRED')
        if valid(roles['forwardjump']):raise ValueError('PLAYER_JUMP_ENTRY_FORWARDJUMP_OWNER_REQUIRED')
        if valid(roles['jump']):
            yield Service.TRY_JUMP,model['runjumpheight'],binary32(model['jumpspeed']*model['runjumpdist']),entity['velocity']['z']if model['jumpmovez']else 0,roles['jump']
    else:
        if player['keys']&KEYS['movedown'] and valid(roles['slide']):
            raise ValueError('PLAYER_JUMP_ENTRY_SLIDE_OWNER_REQUIRED')
        if not(player['keys']&(KEYS['moveleft']|KEYS['moveright']))and valid(roles['jump']):
            yield Service.TRY_JUMP,model['jumpheight'],0,entity['velocity']['z']if model['jumpmovez']else 0,roles['jump']
            return 'RETURN'
        if player['keys']&KEYS['moveleft']:entity['direction']=0
        elif player['keys']&KEYS['moveright']:entity['direction']=1
        if valid(roles['forwardjump']):raise ValueError('PLAYER_JUMP_ENTRY_FORWARDJUMP_OWNER_REQUIRED')
        if valid(roles['jump']):
            yield Service.TRY_JUMP,model['jumpheight'],model['jumpspeed'],entity['velocity']['z']if model['jumpmovez']else 0,roles['jump']
    return 'RETURN'


def try_jump(entity,roles,valid,y,x,z,role):
    entity['jump']=dict(y=binary32(y),x=binary32(x),z=binary32(z),id=role)
    if valid(roles['jumpdelay']):
        entity['takeaction']='COMMON_PREJUMP';entity['idling']=0
        entity['velocity']['x']=entity['velocity']['z']=0
        yield Service.SET_ANIMATION,roles['jumpdelay'],0
    else:
        yield Service.DO_JUMP,binary32(y),binary32(x),binary32(z),role


def common_prejump(entity):
    if entity['animating']:return
    pending=entity['jump']
    yield Service.DO_JUMP,pending['y'],pending['x'],pending['z'],pending['id']
