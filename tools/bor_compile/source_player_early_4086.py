"""Source-order player_think prefix; every search/helper remains mandatory.

Only an empty endlevel search is admitted here. A matching item requires the
full score/reached/branch completion owner, never a silent discarded candidate.
"""
from enum import IntEnum


class Service(IntEnum):
    FIND_ENDLEVEL=1
    PREINPUT=2
    CHARGE=3
    PAIN=4


def execute(entity,context,players):
    port=entity['playerindex']
    if not 0<=port<4:raise ValueError('PLAYER_EARLY_PORT')
    oldrunning=entity['running']
    context['entry_playerindex']=port;context['oldrunning']=oldrunning
    if players[port]['entity']is not entity or entity['dead']:
        return 'RETURN'
    candidate=yield Service.FIND_ENDLEVEL
    if candidate is not None:raise ValueError('PLAYER_ENDLEVEL_COMPLETION_OWNER_REQUIRED')
    if context['time']&0xffffffff>entity['rush_time']&0xffffffff:
        entity['rush_current']=0;entity['rush_time']=0
    intercepted=yield Service.PREINPUT
    if intercepted:return 'RETURN'
    if entity['charging']:
        yield Service.CHARGE
        return 'RETURN'
    if entity['inpain']or(entity['link']and not entity['grabbing']):
        yield Service.PAIN
        return 'RETURN'
    return 'CONTINUE'
