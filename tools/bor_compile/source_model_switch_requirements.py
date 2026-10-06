"""Source-derived mutable model-presentation requirements, without actor aliases.

Weapon switching preserves the source entity type while globally inheriting
missing cached animation pointers. This is a required capability description;
publishing it does not admit a foreign profile or bind a native model owner.
"""
import argparse,json,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_registry import derive as registry
from script_callback_owner import derive as callbacks
from script_dispatch_4086 import compile_source
from source_animation_ids import configure
from source_frame_effects_4086 import derive as effects
from dialect_4086 import ENGINE_COMMIT


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);models=registry(source);programs,*_=callbacks(source);scripts=compile_source(source)
    config=configure(docs[key(structure['models_path'])]['directives'])
    by_name={m['identity'].lower():m['id'] for m in models['models']};by_program={m['id']:m['program'] for m in programs['models']}
    frame_effects=effects(source);entries=[]
    for model in models['models']:
        rows=docs[key(model['source_path'])]['directives'];flags=0;weapons=None;weaploss=[0,-1];rejections=[]
        for row in rows:
            name,values=row['directive'],row['values']
            if name=='modelflag':
                if len(values)!=1:raise ValueError('MODEL_SWITCH_FLAG_ARITY')
                flags=int(values[0])
                if not 0<=flags<=7:rejections.append('MODEL_SWITCH_UNKNOWN_FLAG_BITS')
            elif name=='weaploss':
                if not 1<=len(values)<=2:raise ValueError('MODEL_SWITCH_WEAPLOSS_ARITY')
                weaploss=[int(values[0]),int(values[1]) if len(values)>1 else 0]
            elif name=='weapons' and values:
                # Pinned helper allocates only on the first nonempty declaration.
                # Growth on a later declaration reaches undefined C memory.
                if weapons is not None and len(values)>len(weapons):
                    rejections.append('SOURCE_WEAPON_REDECLARATION_GROWTH_UNDEFINED')
                resolved=[]
                for value in values:
                    if value.lower()=='none':resolved.append(-1)
                    elif value.lower() in by_name:resolved.append(by_name[value.lower()])
                    else:raise ValueError('MODEL_SWITCH_WEAPON_IDENTITY_UNBOUND:'+value)
                weapons=resolved
        if weapons and any(n<0 for n in weapons):rejections.append('SOURCE_WEAPON_CACHED_INDEX_UNDEFINED')
        handles=[dict(engine_animation_id=h['engine_animation_id'],frame_handle=h['handle'],role=h['role'])
            for h in scripts['animation_handles'] if h['model']==model['identity']]
        weapon_frames=[dict(frame_handle=a['handle'],frame=a['events']['weapon_frame'],
            weapon_number=a['events']['weapon_number'],keep=a['events']['weapon_keep'])
            for a in frame_effects['animations'] if a['model']==model['identity'] and a['events']['weapon_frame']>=0]
        entries.append(dict(id=model['id'],identity=model['identity'],source_path=model['source_path'],
            source_sha256=model['source_sha256'],declared_type=model['declared_type'],model_flag=flags,
            weapon_ids=weapons,weaploss=weaploss,script_program=by_program[model['id']],animation_slots=handles,
            weapon_frame_events=weapon_frames,rejections=sorted(set(rejections)),
            requires_mutable_model_presentation=weapons is not None or bool(weapon_frames)))
    return dict(schema='BYOR_4086_MUTABLE_MODEL_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,
        models=entries,maximum_animations=config['max_animations'],
        cached_animation_map_bytes=len(entries)*config['max_animations']*2,
        source_type_policy='Preserve previous entity type after ent_set_model initialization; retain distinct cached model declaration.',
        source_animation_policy='Mutable shared cached animation pointers; inherited frames keep original immutable frame identity/handle.',
        source_script_policy='Current/default descriptors captured at callback begin; fresh default eligibility after current callback.',
        native_model_switch_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False)


def pack_animation_cache(report):
    count=len(report['models']);maximum=report['maximum_animations']
    if not 1<=count<=128 or not 1<=maximum<=1024 or count*maximum*2>8192:
        raise ValueError('MODEL_ANIMATION_CACHE_NATIVE_CAPACITY')
    values=[0]*(count*maximum);seen=set()
    for index,model in enumerate(report['models']):
        if model['id']!=index:raise ValueError('MODEL_ANIMATION_CACHE_MODEL_ID')
        for animation in model['animation_slots']:
            number,handle=animation['engine_animation_id'],animation['frame_handle']
            if not 0<=number<maximum or not 1<=handle<=65535:
                raise ValueError('MODEL_ANIMATION_CACHE_ANIMATION_ID')
            slot=index*maximum+number
            if slot in seen:raise ValueError('MODEL_ANIMATION_CACHE_DUPLICATE_SLOT')
            seen.add(slot);values[slot]=handle
    return struct.pack('<'+'H'*len(values),*values)


def pack_weapon_metadata(report):
    """Immutable B4MW list identities plus mutable cached pointer/count rows."""
    count=len(report['models'])
    if not 1<=count<=16:raise ValueError('MODEL_WEAPON_METADATA_CAPACITY')
    cache=bytearray(count*32);directory=bytearray();pool=bytearray()
    for number,model in enumerate(report['models']):
        if model['id']!=number:raise ValueError('MODEL_WEAPON_METADATA_IDENTITY')
        flags=model['model_flag'];weapons=model['weapon_ids'];loss=model['weaploss']
        if not 0<=flags<=7 or len(loss)!=2 or any(not -0x80000000<=v<=0x7fffffff for v in loss):
            raise ValueError('MODEL_WEAPON_METADATA_DOMAIN')
        if weapons is not None and (len(weapons)>128 or any(not 0<=v<count for v in weapons)):
            raise ValueError('SOURCE_WEAPON_CACHED_INDEX_UNDEFINED')
        size=len(weapons) if weapons is not None else 0
        owner=number if weapons is not None else 65535
        struct.pack_into('<4H2i',cache,number*32,owner,size,flags,0,*loss)
        at=16+8*count+len(pool)
        directory.extend(struct.pack('<4H',number,size,at,0))
        if weapons:pool.extend(struct.pack('<'+'h'*size,*weapons))
    table=struct.pack('<4s6H',b'B4MW',1,count,8,16,32,0)+directory+pool
    return bytes(cache),table


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(models=len(r['models']),maximum_animations=r['maximum_animations'],
        cached_animation_map_bytes=r['cached_animation_map_bytes'],rejections=sum(len(m['rejections']) for m in r['models']))))


if __name__=='__main__':main()
