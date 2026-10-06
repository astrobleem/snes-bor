"""Pinned kill/ent_unlink policy; callbacks and damage are explicit services.

Relations are physical entity identities. Retirement cannot be replaced by
an alive-bit write. Script clear handlers must implement method 1 lifecycle,
including clear entry and persistent-name value cleanup, before resuming.
"""
from dataclasses import dataclass,field
from enum import IntEnum

class Service(IntEnum):
    ONKILL=1
    CLEAR_SCRIPTS=2
    DAMAGE_MINION=3

@dataclass(eq=False)
class Entity:
    identity:int
    exists:bool=True
    health:int=100
    type:int=0
    summonkill:int=0
    takedamage:bool=False
    cantfire:int=1
    cleared:int=0
    parent:object=None
    subentity:object=None
    owner:object=None
    opponent:object=None
    binding:object=None
    landed:object=None
    hithead:object=None
    lasthit:object=None
    link:object=None
    grabbing:object=None
    weapent:object=None

@dataclass
class Owner:
    entities:list
    players:list=field(default_factory=lambda:[None]*4)
    self_entity:object=None
    smartbomber:object=None
    textbox:object=None
    ent_count:int=0
    level_completed:bool=False

def unlink(ent):
    if ent.link is not None:
        ent.link.link=None;ent.link.grabbing=None
    ent.link=None;ent.grabbing=None

def kill(owner,victim):
    """Valid-pointer domain; openbor_killentity handles NULL before kill()."""
    if victim is None:raise ValueError('SOURCE_KILL_NULL_ENGINE_UNDEFINED')
    oldself=owner.self_entity
    yield Service.ONKILL,victim,None
    if not victim.exists:return
    if victim.type&32 and victim.owner is not None and victim.owner.type&1:
        victim.owner.cantfire=0
    unlink(victim);victim.weapent=None;victim.health=0;victim.exists=False;owner.ent_count-=1
    yield Service.CLEAR_SCRIPTS,victim,1
    if victim.parent is not None and victim.parent.subentity is victim:
        victim.parent.subentity=None
    victim.parent=None
    if victim.summonkill==1 and victim.subentity is not None:
        victim.subentity.parent=None;owner.self_entity=victim.subentity
        child=owner.self_entity
        if child.takedamage and not owner.level_completed:
            yield Service.DAMAGE_MINION,child,child.health
        else:yield from kill(owner,child)
    victim.subentity=None
    for i,ent in enumerate(owner.players):
        if ent is victim:owner.players[i]=None;break
    if owner.smartbomber is victim:owner.smartbomber=None
    if owner.textbox is victim:owner.textbox=None
    # C checks existence once per iteration, before a possible minion kill.
    # It still repairs that same row after a damage/kill service removes it.
    for ent in owner.entities:
        if ent.exists:
            owner.self_entity=ent
            if ent.parent is victim:
                ent.parent=None
                if victim.summonkill==2:
                    if ent.takedamage and not owner.level_completed:
                        yield Service.DAMAGE_MINION,ent,ent.health
                    else:yield from kill(owner,ent)
            if ent.owner is victim:ent.owner=victim.owner
            for name in ('opponent','binding','landed','hithead','lasthit'):
                if getattr(ent,name) is victim:setattr(ent,name,None)
            if owner.textbox is None and ent.type&128:owner.textbox=ent
    owner.self_entity=oldself
