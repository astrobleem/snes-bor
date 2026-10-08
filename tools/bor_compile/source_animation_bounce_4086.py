"""Pinned per-animation bounce defaults and final BOUNCEFACTOR overrides."""
import argparse
import json
from pathlib import Path
import re
import struct
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_model_core_4086 import binary32
from script_dispatch_4086 import compile_source


def initial_bounce(role):
    role=role.casefold()
    return 4.0 if role in ('shock','burn') or re.fullmatch(r'fall(?:[1-9][0-9]*)?',role) else 0.0


def load(rows):
    animations=[];current=None
    for row in rows:
        name,values=row['directive'],row['values']
        if name=='anim':
            current=dict(role=' '.join(values),bounce=initial_bounce(' '.join(values)))
            animations.append(current)
        elif name=='bouncefactor' and current is not None:
            current['bounce']=binary32(values[0] if values else 0)
    return animations


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    handles={(h['model'],h['role']):h['handle']for h in compile_source(source)['animation_handles']}
    animations=[]
    for model in discover(source,docs)['models']:
        doc=docs[key(model['source_path'])]
        for animation in load(doc['directives']):
            animation.update(model=model['declaration'],handle=handles[model['declaration'],animation['role']],
                source_path=doc['source_path'],source_sha256=doc['sha256'])
            animations.append(animation)
    return dict(schema='BYOR_4086_ANIMATION_BOUNCE_INPUTS_V1',engine_commit=ENGINE_COMMIT,
        animations=animations,native_bounce_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack(report):
    animations=sorted(report['animations'],key=lambda a:a['handle'])
    if not 1<=len(animations)<=128:raise ValueError('ANIMATION_BOUNCE_NATIVE_CAPACITY')
    result=bytearray(struct.pack('<4s6H',b'B4AB',1,len(animations),8,0,0,0))
    for handle,animation in enumerate(animations,1):
        if handle!=animation['handle']:raise ValueError('ANIMATION_BOUNCE_HANDLE')
        result.extend(struct.pack('<HHf',handle,0,animation['bounce']))
    return bytes(result)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=derive(Source(a.source));raw=pack(report);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n');a.output.with_suffix('.b4ab').write_bytes(raw)
    print(len(report['animations']),'animation bounce rows',len(raw),'bytes')


if __name__=='__main__':main()
