"""Pinned animation physics inputs, independent of presentation and callbacks.

Final animation metadata applies to every frame, including declarations after
the final FRAME. Movement BASE/Y values persist until changed, reset at ANIM.
This IR does not grant a native gravity, landing or collision capability.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import struct
from compiler import Source, key
from dialect_4086 import ENGINE_COMMIT
from source_model_core_4086 import integer
from source_profile import document, discover
from script_dispatch_4086 import compile_source


def loader_frames(rows):
    animations=[]; current=None; movement=None
    for row in rows:
        name, values=row['directive'], row['values']
        if name=='anim':
            current=dict(role=' '.join(values), antigrav=0, dropframe=-1,
                         landframe=-1, land_entity=0, frames=[])
            animations.append(current)
            movement=dict(base=-1, x=0, y=0, z=0)
        elif current is None:
            continue
        elif name in ('dive', 'dive1', 'dive2'):
            # All three loader commands set antigrav; JUMPFRAME does not
            # clear it. Their jump event remains owned by the frame backend.
            current['antigrav']=1
        elif name in ('dropframe', 'landframe'):
            frame=len(current['frames']) if values and values[0].casefold()=='this' else integer(values)
            current[name]=frame
            if name=='landframe':
                current['land_entity']=values[1] if len(values)>1 and values[1] else None
        elif name in ('seta', 'move', 'movea', 'movez'):
            movement[dict(seta='base', move='x', movea='y', movez='z')[name]]=integer(values)
        elif name=='frame':
            if not values:
                raise ValueError('ANIMATION_PHYSICS_FRAME_IDENTITY_REQUIRED')
            current['frames'].append(dict(index=len(current['frames']),
                source_line=row['line'], image=values[0], movement=deepcopy(movement)))
    return animations


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs)
    handles={(h['model'],h['role']):h['handle'] for h in compile_source(source)['animation_handles']}
    models={m['declaration'].casefold():i for i,m in enumerate(structure['models'])}
    animations=[]
    for model in structure['models']:
        doc=docs[key(model['source_path'])]
        for animation in loader_frames(doc['directives']):
            entity=animation['land_entity']
            if isinstance(entity,str):
                if entity.casefold() not in models:
                    raise ValueError('ANIMATION_PHYSICS_LAND_ENTITY_UNBOUND:'+entity)
                animation['land_entity_index']=models[entity.casefold()]
            else:
                animation['land_entity_index']=-1 if entity is None else entity
            animation.update(model=model['declaration'], handle=handles[model['declaration'],animation['role']],
                source_path=doc['source_path'], source_sha256=doc['sha256'])
            animations.append(animation)
    return dict(schema='BYOR_4086_ANIMATION_PHYSICS_INPUTS_V1',engine_commit=ENGINE_COMMIT,
        animations=animations, numeric_policy='source integer movement and frame numbers; no native numeric lowering',
        native_active_gravity_or_landing_bound=False, motu_gameplay_proven=False, no_color_reduction=True)


HEADER=struct.Struct('<4sHHII')
DIRECTORY=struct.Struct('<HHiiiii')
FRAME=struct.Struct('<ii')


def pack(report):
    animations=sorted(report['animations'],key=lambda a:a['handle'])
    if not 1<=len(animations)<=128:
        raise ValueError('ANIMATION_PHYSICS_NATIVE_ANIMATION_CAPACITY')
    frames=bytearray();directory=bytearray()
    first=HEADER.size+len(animations)*DIRECTORY.size
    for handle,animation in enumerate(animations,1):
        if animation['handle']!=handle or not 1<=len(animation['frames'])<=65535:
            raise ValueError('ANIMATION_PHYSICS_NATIVE_HANDLE_OR_FRAME_COUNT')
        directory.extend(DIRECTORY.pack(handle,len(animation['frames']),animation['antigrav'],
            animation['dropframe'],animation['landframe'],animation['land_entity_index'],first+len(frames)))
        for frame in animation['frames']:
            frames.extend(FRAME.pack(frame['movement']['base'],frame['movement']['y']))
    size=first+len(frames)
    if size>32768:
        raise ValueError('ANIMATION_PHYSICS_NATIVE_BANK_CAPACITY')
    return HEADER.pack(b'B4PH',1,len(animations),size,0)+directory+frames


def unpack(raw):
    if len(raw)<HEADER.size:
        raise ValueError('ANIMATION_PHYSICS_HEADER_TRUNCATED')
    magic,version,count,size,reserved=HEADER.unpack_from(raw)
    if magic!=b'B4PH' or version!=1 or reserved or size!=len(raw) or not 1<=count<=128 or size>32768:
        raise ValueError('ANIMATION_PHYSICS_HEADER')
    cursor=HEADER.size+count*DIRECTORY.size
    if cursor>size:
        raise ValueError('ANIMATION_PHYSICS_DIRECTORY_TRUNCATED')
    animations=[]
    for index in range(count):
        handle,n,antigrav,drop,land,entity,offset=DIRECTORY.unpack_from(raw,HEADER.size+index*DIRECTORY.size)
        if handle!=index+1 or not n or antigrav not in (0,1) or offset!=cursor or cursor+n*FRAME.size>size or entity< -1:
            raise ValueError('ANIMATION_PHYSICS_DIRECTORY')
        animations.append(dict(handle=handle,antigrav=antigrav,dropframe=drop,landframe=land,
            land_entity_index=entity,frames=[dict(base=b,y=y)for b,y in
                (FRAME.unpack_from(raw,cursor+i*FRAME.size)for i in range(n))]))
        cursor+=n*FRAME.size
    if cursor!=size:
        raise ValueError('ANIMATION_PHYSICS_TRAILING_BYTES')
    return animations


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--binary',type=Path,help='Compile bounded B4PH physics metadata for native lookup.')
    a=p.parse_args();report=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.binary:
        raw=pack(report);unpack(raw);a.binary.parent.mkdir(parents=True,exist_ok=True);a.binary.write_bytes(raw)
        report['compiled_bytes']=len(raw)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(animations=len(report['animations']),
        antigrav=sum(a['antigrav']!=0 for a in report['animations']),
        landframes=sum(a['landframe']>=0 for a in report['animations']))))


if __name__=='__main__':main()
