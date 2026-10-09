"""Source post-checkdeath tail plan; children remain explicit services."""
from enum import IntEnum

class Service(IntEnum):
    RUMBLE=1
    PLAYER_DIE=2
    KILL=3
    UNLINK=4
    DROP_WEAPON=5
    SET_DEATH=6
    TOSS=7
    SET_FALL=8
    SET_PAIN=9


def run(c):
    e=dict(c);events=[]
    def event(n,*args):events.append([int(n),*args])
    if e['type']&1:event(Service.RUMBLE,e['force']*3)
    if e['y']<=-250 and e['dead']:
        event(Service.PLAYER_DIE if e['type']&1 else Service.KILL);return 1,e,events
    if e['landing']:
        e['landing']=0;return 1,e,events
    if (e['opponent']and not e['other_grabbing'])or e['dead']or e['frozen']or e['drop']:
        event(Service.UNLINK)
    if e['escapehits']:e['escape']=0 if e['drop']else e['escape']+1
    if e['drop']or e['health']<=0:
        e['action']=1
        if (e['weaploss']==2 and e['health']<=0)or e['weaploss']==1:event(Service.DROP_WEAPON,1)
        if e['health']<=0 and e['falldie']==1:
            e['vx']=e['vz']=e['vy']=0;event(Service.SET_DEATH,e['damagetype'],0)
        else:
            e['vx']=-e['dropx']if e['direction']==1 else e['dropx'];e['vz']=e['dropz']
            event(Service.TOSS,e['dropy'])
            e['landing']=e['attack_landing'];e['count']=e['model_count'];e['ktime']=0
            event(Service.SET_FALL,e['damagetype'],1,e['force'],e['attack_drop'],e['no_block'],e['guardcost'],e['jugglecost'],e['pause_add'])
            if not e['valid_fall']:
                event(Service.PLAYER_DIE if e['type']&1 else Service.KILL);return 1,e,events
        if e['type']&1:event(Service.RUMBLE,e['force']*3)
    elif e['grab']and not e['no_pain']:
        e['action']=2;e['other_action']=3;e['other_stall']=(e['time']+160)&0xffffffff;e['release']=(e['time']+100)&0xffffffff
        event(Service.SET_PAIN,e['damagetype'],0)
    elif not e['frozen']and not e['nopain']and not e['no_pain']and not(e['defense_pain']and e['force']<e['defense_pain']):
        e['action']=2;event(Service.SET_PAIN,e['damagetype'],1)
    return 1,e,events
