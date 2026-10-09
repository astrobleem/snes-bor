"""Source directional run section with real ordered match/query services."""
from enum import IntEnum
from source_player_run_4086 import KEYS
from source_player_input_4086 import match_combo
class Service(IntEnum):
    RUN=1
    ATTACKUP=2
    ATTACKDOWN=3
    DODGE=4
    ATTACKFORWARD=5

def execute(e,player,notinair):
    for key,attack in ((KEYS['moveup'],Service.ATTACKUP),(KEYS['movedown'],Service.ATTACKDOWN)):
        if player['playkeys']&key:
            t=notinair and match_combo([key,key],player)
            running=False
            if t and e['runupdown']&2:running=bool((yield Service.RUN))
            if running:
                player['playkeys']&=~key;player['combostep']=(player['combostep']-1+27)%27;e['running']=1
            elif t:
                if(yield attack):raise ValueError('DIRECTIONAL_ATTACK_OWNER_REQUIRED')
                if(yield Service.DODGE):raise ValueError('DIRECTIONAL_DODGE_OWNER_REQUIRED')
    if player['playkeys']&(KEYS['moveleft']|KEYS['moveright']):
        t=notinair and ((e['direction']==1 and match_combo([KEYS['moveright']]*2,player))or(e['direction']==0 and match_combo([KEYS['moveleft']]*2,player)))
        if t:
            if(yield Service.RUN):
                player['playkeys']&=~(KEYS['moveleft']|KEYS['moveright']);player['combostep']=(player['combostep']-1+27)%27;e['running']=1
            elif(yield Service.ATTACKFORWARD):raise ValueError('DIRECTIONAL_ATTACK_OWNER_REQUIRED')
    return 'CONTINUE'
