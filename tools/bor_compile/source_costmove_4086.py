"""Pinned check_costmove mutation order; animation is a mandatory service.

A successful move is not complete until the caller executes the emitted source
animation transition (including frame-zero callbacks) and resumes the generator.
"""
from enum import IntEnum
from source_animation_energy_4086 import check

class Service(IntEnum):
    SET_ANIMATION=1


def execute(entity,context,animation,fs,jumphack):
    data=entity['modeldata']['animation'].get(animation)
    def energy(which):
        return check(which,data['energycost']if data else dict(cost=0,mponly=0,disable=0),
                     entity['modeldata']['type'],entity['seal'],entity['mp'],entity['health'],
                     bool(data and data['numframes']))
    nospecial=context['nospecial']
    if not ((fs==1 and nospecial<2)or(fs==0 and nospecial==0)or(fs==0 and nospecial==3)):
        return 0
    if not (energy(0)or energy(1)):return 0
    # Validate signed C subtraction before any mutation; undefined overflows
    # are explicit unsupported source domains rather than wrapped debits.
    debit=None
    if not context['nocost']and not context['healthcheat']:
        field='mp'if energy(1)else'health';value=entity[field]-data['energycost']['cost']
        if not -0x80000000<=value<=0x7fffffff:raise ValueError('SOURCE_COSTMOVE_SIGNED_OVERFLOW')
        debit=field,value
    if not jumphack:entity['takeaction']=17 # semantic common_attack_proc ID
    if debit:entity[debit[0]]=debit[1]
    entity['velocity']['x']=entity['velocity']['z']=0
    entity['attacking']=1;entity['idling']=0;entity['inpain']=0
    entity['combostep']=[0]*5
    if entity['link']is not None:
        entity['link']['link']=None;entity['link']['grabbing']=None
    entity['link']=None;entity['grabbing']=None
    yield Service.SET_ANIMATION,entity,animation,0
    return 1
