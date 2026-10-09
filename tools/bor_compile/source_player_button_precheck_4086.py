"""Ordered source button checks before release/ordinary attack/jump handling."""
from enum import IntEnum
from source_player_run_4086 import KEYS
class Service(IntEnum):
    ATTACKBOTH=1
    CHARGE=2
    SPECIAL2=3
    BLOCK=4
    CHECK_SPECIAL=5

def execute(context,player,notinair):
    if not context['ajspecial'] and player['playkeys']&KEYS['jump']:
        if(yield Service.ATTACKBOTH):raise ValueError('PLAYER_ATTACKBOTH_OWNER_REQUIRED')
    if player['playkeys']&KEYS['jump']:
        if(yield Service.CHARGE):raise ValueError('PLAYER_CHARGE_ENTRY_OWNER_REQUIRED')
    if player['playkeys']&KEYS['special']:
        if(yield Service.SPECIAL2):raise ValueError('PLAYER_SPECIAL2_OWNER_REQUIRED')
        if(yield Service.BLOCK) and notinair:raise ValueError('PLAYER_BLOCK_ENTRY_OWNER_REQUIRED')
    if notinair and(yield Service.CHECK_SPECIAL):return 'RETURN'
    return 'CONTINUE'
