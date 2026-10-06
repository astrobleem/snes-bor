"""Resumable pinned update_frame ordering; callers execute every yielded service.

Events reference the captured animation even if weapon/idle services later
replace the current one. Only the initial callback has an interruption check.
The yielded owner must preserve and restore source self across nested services.
"""
from dataclasses import dataclass, field
from enum import IntEnum


class Service(IntEnum):
    ANIMATION_SCRIPT=1
    DROP_WEAPON=2
    SET_WEAPON=3
    SET_IDLE=4
    UNSUMMON_DAMAGE=5
    UNSUMMON_KILL=6
    SPAWN=7
    SUMMON=8
    SOUND=9
    TOSS=10
    DUST_BIRTH=11
    DUST_ONSPAWN=12
    THROW_KNIFE=13
    THROW_STAR=14
    SHOOT=15
    BOMB=16


@dataclass
class Frame:
    base:int=-1
    x:int=0
    y:int=0
    z:int=0
    delay:int=6
    sound:int=-1


@dataclass
class Animation:
    frames:list[Frame]
    events:dict
    quake_count:int=0


@dataclass
class Entity:
    animation:Animation
    frame:int=0
    animating:int=1
    nextanim:int=0
    pausetime:int=123
    direction:int=1
    movex:float=0
    movez:float=0
    base:float=0
    altbase:float=0
    vx:float=0
    vz:float=0
    vy:float=0
    altitude:float=10
    toss_time:int=123
    subentity:object=None
    health:int=7
    takedamage:bool=False
    dead:bool=False
    jumping:bool=False
    reactive:bool=False
    autokill:int=0
    exists:bool=True


@dataclass
class Owner:
    time:int=48
    level:bool=True
    quake:int=0
    self_entity:Entity|None=None
    dust:Entity|None=None
    projectile_succeeded:bool=False
    completed:bool=False


def update_frame(owner,ent,f):
    """Valid-domain update_frame; backend sends service results through owner."""
    anim=ent.animation
    if f<0:raise ValueError('SOURCE_UPDATE_FRAME_NEGATIVE_UNDEFINED')
    if f>=len(anim.frames):return
    oldself=owner.self_entity;owner.self_entity=ent;owner.completed=False
    try:
        ent.frame=f
        if ent.animating:
            ent.nextanim=(owner.time+anim.frames[f].delay)&0xffffffff
            ent.pausetime=0
            yield Service.ANIMATION_SCRIPT,ent
        if ent.animation is not anim or ent.frame!=f:return
        frame=anim.frames[f];e=anim.events
        if owner.level and (frame.x or frame.z):
            ent.movex+=-frame.x if not ent.direction else frame.x
            ent.movez+=frame.z
        base=anim.frames[0].base
        if base and base>=0 and ent.base<=0:ent.base=float(base)
        elif not base or base<0:
            ent.base+=frame.y
            ent.altbase=ent.altbase+frame.y if frame.y else 0
        if e['flipframe']==f:ent.direction=int(not ent.direction)
        if e['weapon_frame']==f:
            yield Service.DROP_WEAPON,ent
            yield Service.SET_WEAPON,ent
            if not e['weapon_keep']:yield Service.SET_IDLE,ent
        if e['quake_start']+anim.quake_count==f:
            if owner.level:
                owner.quake=e['quake_value'] if anim.quake_count%2 or e['quake_value']>0 else -e['quake_value']
            anim.quake_count=anim.quake_count+1 if e['quake_repeat']-anim.quake_count>1 else 0
        if e['unsummonframe']==f and ent.subentity is not None:
            owner.self_entity=ent.subentity
            yield (Service.UNSUMMON_DAMAGE if ent.subentity.takedamage else Service.UNSUMMON_KILL),ent.subentity
            owner.self_entity=ent;ent.subentity=None
        if e['spawn_frame']==f and e['subentity'] is not None:yield Service.SPAWN,ent
        if e['summon_frame']==f and e['subentity'] is not None and (ent.subentity is None or ent.subentity.dead):
            yield Service.SUMMON,ent
        if frame.sound>=0:yield Service.SOUND,ent
        if e['jump_frame']==f:
            yield Service.TOSS,ent
            ent.vx=e['jump_x'] if ent.direction else -e['jump_x'];ent.vz=e['jump_z']
            if e['jump_entity'] is not None:
                owner.dust=None
                yield Service.DUST_BIRTH,ent
                if owner.dust is not None:
                    owner.dust.base=ent.altitude
                    owner.dust.autokill=2
                    yield Service.DUST_ONSPAWN,owner.dust
        if e['throw_frame']==f:
            if e['knife'] is not None or e['flash'] is not None:yield Service.THROW_KNIFE,ent
            elif e['star'] is not None:yield Service.THROW_STAR,ent
            elif ent.jumping:
                owner.projectile_succeeded=False
                yield Service.THROW_STAR,ent
                if not owner.projectile_succeeded:yield Service.THROW_KNIFE,ent
            else:
                owner.projectile_succeeded=False
                yield Service.THROW_KNIFE,ent
                if not owner.projectile_succeeded:yield Service.THROW_STAR,ent
            ent.reactive=True
        if e['shoot_frame']==f:
            yield Service.SHOOT,ent;ent.reactive=True
        if e['toss_frame']==f:
            yield Service.BOMB,ent;ent.reactive=True
    finally:
        owner.self_entity=oldself;owner.completed=True
