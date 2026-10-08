"""Pinned animation physics inputs, independent of presentation and callbacks.

Final animation metadata applies to every frame, including declarations after
the final FRAME. Movement BASE/Y values persist until changed, reset at ANIM.
This IR does not grant a native gravity, landing or collision capability.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(animations=len(report['animations']),
        antigrav=sum(a['antigrav']!=0 for a in report['animations']),
        landframes=sum(a['landframe']>=0 for a in report['animations']))))


if __name__=='__main__':main()
