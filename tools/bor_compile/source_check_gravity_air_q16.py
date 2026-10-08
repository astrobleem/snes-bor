"""Explicit bounded Q16 airborne adaptation; callbacks remain required services.

Arithmetic right shift is floor division, including negative half-LSB values.
Overflow rejects before publishing air fields. This is numeric compatibility,
not source binary32 identity or a native gameplay admission.
"""
LIMIT_LOW=-(1<<31)
LIMIT_HIGH=(1<<31)-1


def checked(value):
    if not LIMIT_LOW<=value<=LIMIT_HIGH:raise ValueError('SOURCE_AIR_Q16_OVERFLOW')
    return value


def check_gravity_air_q16(entity,time,physics,adjust_base,is_frozen,onmovea,landing=None):
    if entity['update_mark']&8:return
    adjust_base(entity)
    if not is_frozen(entity):
        due=entity['toss_time']<=(time&0xffffffff)
        if (entity['falling']or entity['velocity_y']or entity['a']!=entity['base'])and due:
            if entity['height'] and entity['subject_to_platform']>0 and entity['velocity_y']>0:
                raise ValueError('SOURCE_AIR_Q16_CEILING_BACKEND_REQUIRED')
            altitude=checked(entity['a']+(entity['velocity_y']>>1))
            gravity=0 if entity['animation_antigrav']else checked((physics['gravity']*(65536-entity['antigravity']))>>16)
            velocity=entity['velocity_y']
            if entity['subject_to_gravity']>0:velocity=checked(velocity+(gravity>>1))
            velocity=max(physics['maxfallspeed'],min(physics['maxtossspeed'],velocity))
            if entity['dropframe']>=0 and velocity<=0 and entity['animpos']<entity['dropframe']:
                raise ValueError('SOURCE_AIR_Q16_DROPFRAME_BACKEND_REQUIRED')
            entity['hithead']=None;entity['a']=altitude;entity['velocity_y']=velocity
            if velocity:onmovea(entity)
            if entity['idling'] and entity['walkoff_valid'] and abs(entity['a']-entity['base'])>2*65536:
                raise ValueError('SOURCE_AIR_Q16_WALKOFF_BACKEND_REQUIRED')
            must_land=(entity['a']<=entity['base']or abs(entity['a']-entity['base'])<6554)and entity['velocity_y']<=0
            if must_land:
                if landing is None:raise ValueError('SOURCE_AIR_Q16_LANDING_BACKEND_REQUIRED')
                landing(entity)
        if due:entity['toss_time']=(time+1)&0xffffffff
    entity['update_mark']|=8
