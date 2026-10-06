"""Source ent_default_init owner. Animation/environment services must run.

Float values are source-reference values, not native Q16 certification.
Callbacks are semantic identities, never host pointers or actor-name rules.
"""
from enum import IntEnum

class Service(IntEnum):
    SET_ANIMATION=1
    SET_IDLE=2
    RANDOM_FLOAT=3
    IN_AIR=4
    WALK_ANIMATION=5
    PLATFORM_BELOW=6
    WALL_BELOW=7
    NEAREST_WALL_X=8

def initialize(e,o):
    if e is None:return
    d=e['modeldata'];t=d['type'];level=o['level'];time=o['time']
    valid=lambda name:name in e['modeldata']['animations'] and e['modeldata']['animations'][name]>0
    def callback(field,name):e[field]=name
    if (not o['select'] and not time) or t!=1:
        if valid('spawn'):yield Service.SET_ANIMATION,e,'spawn'
        elif valid('respawn'):yield Service.SET_ANIMATION,e,'respawn'
    elif not o['select'] and time and t==1:
        if valid('respawn'):yield Service.SET_ANIMATION,e,'respawn'
        elif valid('spawn'):yield Service.SET_ANIMATION,e,'spawn'
    elif o['select'] and valid('select'):yield Service.SET_ANIMATION,e,'select'
    # ent_set_anim runs update_frame synchronously; scripts may replace the
    # current modeldata. The C switch reads it after that call returns.
    d=e['modeldata'];t=d['type']
    if level is None:
        if e['animation'] is None:yield Service.SET_IDLE,e,None
        return
    if t in (4,256):e['nograb']=1
    elif t==1:
        callback('takedamage','player_takedamage');callback('think','player_think');callback('trymove','player_trymove')
        if valid('spawn') or valid('respawn'):callback('takeaction','common_spawn')
        elif e['animation'] is None and time and level['spawn_y'][e['playerindex']]>e['a']:
            callback('takeaction','common_drop');e['a']=level['spawn_y'][e['playerindex']]
            if valid('jump'):yield Service.SET_ANIMATION,e,'jump'
        d=e['modeldata']
        if time and d['makeinv']:
            e.update(invincible=1,blink=int(d['makeinv']>0),invinctime=(time+abs(d['makeinv']))&0xffffffff,arrowon=1)
    elif t in (2,512):
        if t==512 and d['multiple']==0:d['multiple']=-1
        callback('think','common_think');sub=d['subtype']
        if sub==1:
            e.update(nograb=1,attacking=1)
            speed=d['speed'] if d['speed'] else 1.7+(yield Service.RANDOM_FLOAT,e,0.6)
            e['vx']=speed if e['direction']==1 else -speed
            callback('takedamage','biker_takedamage');e['speedmul']=2
        elif sub==3:
            e['health']=1
            if not d['speed'] and not d['nomove']:d['speed']=2
            elif d['nomove']:d['speed']=0
            e.update(base=0 if e['ptype'] else e['a'],nograb=1,attacking=1,speedmul=2)
            callback('takedamage','arrow_takedamage')
        else:
            callback('trymove','common_trymove')
            if not d['speed'] and not d['nomove']:d['speed']=1
            elif d['nomove']:d['speed']=0
            if d['multiple']==0:d['multiple']=5
            callback('takedamage','common_takedamage')
            if sub==2:e['nograb']=1
            if valid('spawn') or valid('respawn'):callback('takeaction','common_spawn')
            else:
                dodrop=level['scroll'] in ('up','down')
                if not o['nodropspawn'] and (dodrop or (o['advancex']-30<e['x']<o['advancex']+o['width']+30 and e['a']==0)):
                    e['a']+=o['height']+(yield Service.RANDOM_FLOAT,e,40)
                if (yield Service.IN_AIR,e,None):
                    callback('takeaction','common_drop')
                    if valid('jump'):yield Service.SET_ANIMATION,e,'jump'
    elif t==64:
        callback('think','trap_think');callback('takedamage','common_takedamage');e['speedmul']=2
    elif t==8:
        e['nograb']=1
        if e['health']<=0:e['dead']=1
        callback('takedamage','obstacle_takedamage')
    elif t==16:
        e['nograb']=1;callback('think','steamer_think');e['base']=e['a']
    elif t==128:
        e['nograb']=1;callback('think','text_think')
    elif t==32:
        e.update(health=1,nograb=1,attacking=1,speedmul=2)
        callback('think','common_think');callback('takedamage','arrow_takedamage')
        if not e['model']['speed'] and not d['nomove']:d['speed']=2
        elif d['nomove']:d['speed']=0
        e['base']=0 if e['ptype'] else e['a']
    elif t==0:
        e['nograb']=1
        if d['subject_to_gravity']<0:d['subject_to_gravity']=1
        if d['no_adjust_base']<0:d['no_adjust_base']=1
        if valid('walk'):
            e['vx']=d['speed'] if e['direction']==1 else -d['speed'];callback('think','anything_walk')
            yield Service.WALK_ANIMATION,e,None
        else:e['speedmul']=2
    elif t==1024:e['nograb']=1
    if e['animation'] is None:yield Service.SET_IDLE,e,None
    d=e['modeldata'] # jump/walk/set_idle can each run frame-zero callbacks
    if d['multiple']<0:d['multiple']=0
    other=None
    if d['subject_to_platform']>0:other=yield Service.PLATFORM_BELOW,e,None
    if other is not None:e['base']=other['a']+other['platform_height']
    elif d['subject_to_wall']>0:
        wall=yield Service.WALL_BELOW,e,9999999
        if wall>=0:
            if level['walls'][wall]>o['max_wall_height']:e['x']=yield Service.NEAREST_WALL_X,e,wall
            else:e['base']=level['walls'][wall]
