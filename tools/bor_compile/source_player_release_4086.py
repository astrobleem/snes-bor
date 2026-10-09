"""Source attack release with mandatory punch and animation continuations."""
from enum import IntEnum
from source_player_run_4086 import KEYS
from source_u32_float_threshold_4086 import binary32,compare
class Service(IntEnum):
    PUNCH=1
    SET_ANIMATION=2

def duration(animation):
    n=200*binary32(animation['chargetime'])
    if not n.is_integer()or not 0<=n<=65535:raise ValueError('PLAYER_RELEASE_OTHER_FLOAT_OWNER_REQUIRED')
    return int(n)

def last_attack(e,context):
    data=e['modeldata'];length=data['chainlength']
    if not 1<=length<=len(data['atchain']):raise ValueError('PLAYER_RELEASE_CHAIN_INDEX_UNDEFINED')
    code=data['atchain'][length-1]
    if not 1<=code<=len(context['attacks']):raise ValueError('PLAYER_RELEASE_ATTACK_ROLE_UNDEFINED')
    return context['attacks'][code-1]

def execute(e,context,player,notinair,valid):
    if not player['releasekeys']&KEYS['attack']:return 'CONTINUE'
    active=False
    if e['stalltime'] and notinair:
        role=context['chargeattack']
        if valid(role)and compare(e['stalltime'],context['time'],duration(e['modeldata']['animation'][role])):active=True
        elif not valid(role)and e['modeldata']['chainlength']>0:
            attack=last_attack(e,context)
            if attack not in e['modeldata']['animation']:raise ValueError('PLAYER_RELEASE_SOURCE_ANIMATION_UNDEFINED')
            active=bool(compare(e['stalltime'],context['time'],duration(e['modeldata']['animation'][attack])))
    if active:
        e.update(takeaction=17,attacking=1,idling=0,stalltime=0)
        e['combostep'][0]=0;e['velocity']['x']=e['velocity']['z']=0
        if context['sample_punch']>=0:yield Service.PUNCH
        role=context['chargeattack']if valid(context['chargeattack'])else last_attack(e,context)
        yield Service.SET_ANIMATION,role,0
        return 'RETURN'
    e['stalltime']=0
    return 'CONTINUE'
