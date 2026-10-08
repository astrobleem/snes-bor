"""Pinned airborne integration before landing, with explicit service boundaries.

Uses source binary32 stores and binary64 expressions. Native numeric adaptation,
ceiling, drop/land frames, landing reactions and live callbacks are separate.
"""
from source_model_core_4086 import binary32 as f32


def check_gravity_air(entity,time,physics,adjust_base,is_frozen,onmovea):
    if entity['update_mark']&8:return
    adjust_base(entity)
    if not is_frozen(entity):
        due=entity['toss_time']<=(time&0xffffffff)
        if (entity['falling']or entity['velocity_y']or entity['a']!=entity['base'])and due:
            if entity['height'] and entity['subject_to_platform']>0 and entity['velocity_y']>0:
                raise ValueError('CHECK_GRAVITY_CEILING_BACKEND_REQUIRED')
            entity['hithead']=None
            entity['a']=f32(entity['a']+entity['velocity_y']*100.0/200)
            gravity=0 if entity['animation_antigrav']else f32(f32(physics['gravity'])*(1.0-f32(entity['antigravity'])))
            if entity['subject_to_gravity']>0:
                entity['velocity_y']=f32(entity['velocity_y']+gravity*100.0/200)
            if entity['velocity_y']<physics['maxfallspeed']:entity['velocity_y']=f32(physics['maxfallspeed'])
            elif entity['velocity_y']>physics['maxtossspeed']:entity['velocity_y']=f32(physics['maxtossspeed'])
            if entity['dropframe']>=0 and entity['velocity_y']<=0 and entity['animpos']<entity['dropframe']:
                raise ValueError('CHECK_GRAVITY_DROPFRAME_BACKEND_REQUIRED')
            if entity['velocity_y']:onmovea(entity)
            if entity['idling'] and entity['walkoff_valid'] and abs(f32(entity['a']-entity['base']))>2:
                raise ValueError('CHECK_GRAVITY_WALKOFF_BACKEND_REQUIRED')
            if (entity['a']<=entity['base']or abs(f32(entity['a']-entity['base']))<0.1)and entity['velocity_y']<=0:
                raise ValueError('CHECK_GRAVITY_LANDING_BACKEND_REQUIRED')
        if due:entity['toss_time']=(time+1)&0xffffffff
    entity['update_mark']|=8
