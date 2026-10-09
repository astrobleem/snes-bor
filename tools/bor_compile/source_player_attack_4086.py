"""Ordinary player attack in a derived absent-alternates, empty-item lane.

The item service must prove an empty live candidate set. A matching candidate
needs the complete player_test_pickable/pickup owner, never a fabricated miss.
Attack-chain and animation services must complete their real callbacks before
resuming. The punch predicate reads fresh attacking after the chain service.
"""
from enum import IntEnum
from source_player_run_4086 import KEYS


class Service(IntEnum):
    FIND_ITEM_EMPTY=1
    ATTACK_CHAIN=2
    PUNCH=3
    SET_ANIMATION=4


def execute(entity,context,player,notinair,valid):
    if not(player['playkeys']&KEYS['attack'] and notinair):return 'CONTINUE'
    player['playkeys']&=(~KEYS['attack'])&0xffffffff
    entity['stalltime']=0
    roles=context['roles']
    if player['keys']&KEYS['movedown'] and valid(roles['duckattack']):
        raise ValueError('PLAYER_ATTACK_DUCK_OWNER_REQUIRED')
    if entity['running']and valid(roles['runattack']):
        entity.update(takeaction=17,attacking=1,idling=0,running=0)
        entity['velocity']['x']=entity['velocity']['z']=0;entity['combostep'][0]=0
        yield Service.SET_ANIMATION,roles['runattack'],0
        return 'RETURN'
    if valid(roles['attackbackward']):raise ValueError('PLAYER_ATTACK_BACKWARD_OWNER_REQUIRED')
    if valid(roles['get']):
        empty=yield Service.FIND_ITEM_EMPTY
        if empty is not True:raise ValueError('PLAYER_ATTACK_ITEM_OWNER_REQUIRED')
    entity['stalltime']=context['time']&0xffffffff
    entity['velocity']['x']=entity['velocity']['z']=0
    weapon=entity['weapent']
    if weapon is not None and weapon['subtype']==context['projectile_subtype']and valid(roles['throwattack']):
        raise ValueError('PLAYER_ATTACK_THROW_OWNER_REQUIRED')
    picked=yield Service.ATTACK_CHAIN
    if picked not in(0,1):raise ValueError('PLAYER_ATTACK_CHAIN_RESULT_DOMAIN')
    if picked:
        if context['sample_punch']>=0 and entity['attacking']:yield Service.PUNCH
        return 'RETURN'
    return 'CONTINUE'
