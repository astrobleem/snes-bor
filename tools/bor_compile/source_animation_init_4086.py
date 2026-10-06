"""Pinned ent_set_anim policy; frame-zero execution is an explicit service."""
import struct


def derive(source):
    from compiler import key
    from source_profile import document,discover
    from source_animation_ids import configure,loader_sync
    from script_dispatch_4086 import compile_source
    from source_frame_effects_4086 import derive as effects
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);config=configure(docs[key(structure['models_path'])]['directives'])
    sync={}
    for model in structure['models']:
        for a in loader_sync(config,docs[key(model['source_path'])]['directives']):
            sync[model['declaration'],a['role']]=a
    scripts=compile_source(source);frames={a['handle']:a for a in effects(source)['animations']}
    animations=[]
    for h in scripts['animation_handles']:
        s=sync[h['model'],h['role']]
        if s['engine_animation_id']!=h['engine_animation_id']:raise ValueError('ANIMATION_INIT_IDENTITY_MISMATCH')
        animations.append(dict(handle=h['handle'],model=h['model'],role=h['role'],
            engine_animation_id=h['engine_animation_id'],sync=s['sync'],numframes=len(frames[h['handle']]['frames'])))
    return dict(schema='BYOR_4086_ANIMATION_INITIALIZATION_INPUTS_V1',maximum_animations=config['max_animations'],
        animations=animations,native_owner_bound=False,frame_zero_execution_bound=False,motu_gameplay_proven=False)


def pack(report):
    animations=report['animations'];maximum=report['maximum_animations']
    if not 1<=len(animations)<=128 or not 1<=maximum<=1024:raise ValueError('ANIMATION_INIT_CAPACITY')
    payload=bytearray(struct.pack('<4s6H',b'B4AI',1,len(animations),maximum,8,16,0))
    for index,a in enumerate(animations):
        if a['handle']!=index+1 or not 0<=a['numframes']<=65535 or not -1<=a['sync']<maximum or not 0<=a['engine_animation_id']<maximum:
            raise ValueError('ANIMATION_INIT_ROW_DOMAIN')
        payload.extend(struct.pack('<HHhH',a['handle'],a['numframes'],a['sync'],a['engine_animation_id']))
    return bytes(payload)


def set_animation(entity, number, resetable, owner):
    if entity is None or not 0 <= number < owner['maximum']:
        return
    animation = entity['animations'].get(number)
    if animation is None or not animation['numframes']:
        return
    old = entity['animation']
    if not resetable and old is animation:
        return
    if old is not None and (resetable & 2 or animation['sync'] >= 0 and old['sync'] == animation['sync']):
        frame = entity['animpos']
        if frame >= animation['numframes']:
            frame = 0
        entity.update(animnum=number, animation=animation, animpos=frame)
    else:
        entity.update(animation=animation, animnum=number, animating=1,
                      lasthit=entity['grabbing'], altbase=0)
        animation['animhits'] = 0
        owner['update_frame'](entity, 0)
