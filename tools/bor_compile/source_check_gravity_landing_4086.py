"""Pinned non-bouncing landing with explicit frame/dust/damage service boundaries.

Called after actual air integration. Numeric stores retain source binary32.
Callbacks are services, not substitutes for native script/frame owners.
"""
from source_model_core_4086 import binary32 as f32


def land(entity,tobounce,update_frame,*,spawn=None,onspawn=None,take_damage=None,kill=None):
    entity['a']=entity['base'];entity['falling']=0
    if entity['fall_land_dust']>=0 and entity['velocity_y']<-1 and entity['drop']:
        if spawn is None or onspawn is None:raise ValueError('CHECK_GRAVITY_LAND_DUST_BACKEND_REQUIRED')
        dust=spawn(entity,entity['fall_land_dust'])
        if dust is not None:
            dust['base']=entity['a'];dust['autokill']=2;onspawn(dust)
    if tobounce(entity)and entity['model_bounce']:
        raise ValueError('CHECK_GRAVITY_BOUNCE_BACKEND_REQUIRED')
    if entity['frame_base']<=0 and entity['frame_move_y']<=0:
        entity['velocity_x']=entity['velocity_z']=0
    entity['velocity_y']=0
    if entity['landed_on_platform'] is not None or entity['platform_below'] is not None:
        raise ValueError('CHECK_GRAVITY_LANDING_PLATFORM_BACKEND_REQUIRED')
    lf=entity['landframe']
    if lf>=0 and lf<=entity['numframes']and entity['animpos']<lf:
        if entity['landframe_entity']>=0:
            if spawn is None or onspawn is None:raise ValueError('CHECK_GRAVITY_LANDFRAME_DUST_BACKEND_REQUIRED')
            dust=spawn(entity,entity['landframe_entity'])
            if dust is not None:
                dust['base']=entity['a'];dust['autokill']=2;onspawn(dust)
        update_frame(entity,lf)
    if entity['damage_on_landing']>0 and not entity['dead']:
        if take_damage is not None:take_damage(entity,entity['damage_on_landing'])
        else:
            damage=f32(f32(entity['damage_on_landing'])*f32(entity['land_defense']))
            entity['health']=int(f32(f32(entity['health'])-damage))
            if entity['health']<=0:
                if kill is None:raise ValueError('CHECK_GRAVITY_LAND_KILL_BACKEND_REQUIRED')
                kill(entity)
            entity['damage_on_landing']=0
    entity['hithead']=None
