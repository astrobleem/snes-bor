"""Pinned recovery mutation plans, with animation/death/map children explicit."""
from enum import IntEnum

class Service(IntEnum):
    SET_DEATH=1
    COLOURMAP=2
    SET_RISE=3
    SET_ANIMATION=4
    SET_IDLE=5

def common_lie(e,time):
    events=[]
    if e['health']<=0:
        if e['falldie']==2:events.append([Service.SET_DEATH,e['damagetype'],0])
        policy=e['nodieblink']
        if policy==0 or policy==1 and not e['animating']:
            e['action']=2 if e['type']&1 else 3
            e['blink']=1;e['stall']=(time+400)&0xffffffff
        elif policy==2 and not e['animating']:
            e['action']=4 if e['type']&1 else 3
        elif policy==3 and not e['animating']:
            if e['type']&1:e['action']=4
            else:e['type']=0;e['noai']=1
        if e['ko'] and (e['kotype']==0 or not e['animating']):
            events.append([Service.COLOURMAP,e['ko']]);e['colourmap']=e['ko']+1000
        return events
    if time<e['stall'] or e['y']!=e['base'] or e['vy']:return events
    events.append([Service.SET_RISE,e['damagetype'],0])
    return events

def set_rise(target,self,type,reset,valid,roles):
    events=[]
    def available(t):
        events.append([6,roles[t]])
        return valid[t]
    if type<0 or type>=len(roles) or not available(type):type=0
    if not available(type):return 0,events
    events.append([Service.SET_ANIMATION,roles[type],reset])
    target.update(action=5,drop=0,falling=0,projectile=0,nograb=0,vx=0.)
    # Source assigns the other two components through global self, even when
    # iRise differs. Do not replace this with a target-only vector clear.
    self['vz']=0.;self['vy']=0.
    target['juggle']=target['maxjuggle']
    return 1,events

def common_rise(e,time):
    if e['animating']:return []
    e['action']=0;e['riseattack_stall']=0
    if e['riseinv']:
        e['blink']=int(e['riseinv']>0)
        e['invinctime']=(time+abs(e['riseinv']))&0xffffffff;e['invincible']=1
    return [[Service.SET_IDLE]]
