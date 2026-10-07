"""Pinned check_ai continuation; executable callback bodies are services."""
from enum import IntEnum
class Service(IntEnum):
    ACTION=1
    THINK=2
    THINK_SCRIPT=3
    SET_IDLE=4

def check_ai(e,context):
    if e['nextthink']<=context['time'] and not context['endgame']:
        e['update_mark']=(e['update_mark']|2)&0xffffffff
        if e['takeaction']:yield Service.ACTION,e['takeaction']
        if e['think']:
            if e['nextthink']<=context['time']:e['nextthink']=(context['time']+2)&0xffffffff
            if not e['noaicontrol']:yield Service.THINK,e['think']
        yield Service.THINK_SCRIPT,0
        if (e['animation']==e['spawn'] or e['animation']==e['respawn']) and not e['animating']:
            yield Service.SET_IDLE,0
