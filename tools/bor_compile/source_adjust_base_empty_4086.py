"""Pinned adjust_base in a proved empty wall/hole/basemap/platform world."""
from source_model_core_4086 import binary32 as f32


def adjust_base_empty(entity):
    if entity['landed_on_platform']is not None:
        raise ValueError('ADJUST_BASE_PLATFORM_INSTANCE_BACKEND_REQUIRED')
    if entity['no_adjust_base']<=0:
        seta=f32(entity['frame_base']if entity['frame_base']else-1)
        if entity['subject_to_hole']>0 and entity['base']==-1000:
            if entity['a']>=0:entity['base']=0.
            else:entity['velocity_x']=entity['velocity_z']=0.
        if entity['base']!=-1000:
            if seta>=0:
                total=f32(seta+f32(entity['altbase']))
                entity['base']=f32(int(total>=0)*total)
            elif entity['frame_move_y']==0:entity['base']=0.
    entity['platform_below']=None
