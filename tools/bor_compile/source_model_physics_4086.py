"""Cached model gravity/ceiling/bounce inputs from the pinned model loader."""
import argparse
import json
from pathlib import Path
import struct
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_model_core_4086 import TYPE_NAMES,integer,binary32


def load(rows):
    fields=dict(antigravity=0.0,height=0,bounce=0)
    for row in rows:
        name,values=row['directive'],row['values']
        if name=='type':
            if len(values)!=1 or values[0].casefold() not in TYPE_NAMES:
                raise ValueError('MODEL_PHYSICS_TYPE_UNSUPPORTED')
            if values[0].casefold() in ('player','enemy','npc'):fields['bounce']=1
            elif values[0].casefold()=='panel':fields['antigravity']=1.0
        elif name in ('height','bounce'):fields[name]=integer(values)
        elif name=='antigravity':
            # atof stores to binary32 before the compound division by100.
            fields[name]=binary32(binary32(values[0] if values else 0)/100)
    return fields


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    models=[]
    for index,model in enumerate(discover(source,docs)['models']):
        doc=docs[key(model['source_path'])]
        models.append(dict(index=index,identity=model['declaration'],source_path=doc['source_path'],
            source_sha256=doc['sha256'],fields=load(doc['directives'])))
    return dict(schema='BYOR_4086_MODEL_PHYSICS_INPUTS_V1',engine_commit=ENGINE_COMMIT,
        models=models,model_switch_policy='source shallow-copy values; instance mutations require separate storage or capability revocation',
        numeric_policy='source binary32 antigravity; integer height/bounce',
        native_instance_physics_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack(report):
    models=report['models']
    if not 1<=len(models)<=16:raise ValueError('MODEL_PHYSICS_NATIVE_MODEL_CAPACITY')
    result=bytearray(struct.pack('<4s6H',b'B4MP',1,len(models),12,0,0,0))
    for index,model in enumerate(models):
        if index!=model['index']:raise ValueError('MODEL_PHYSICS_ORDER')
        f=model['fields'];result.extend(struct.pack('<fii',f['antigravity'],f['height'],f['bounce']))
    return bytes(result)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();report=derive(Source(a.source));raw=pack(report)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    a.output.with_suffix('.b4mp').write_bytes(raw);print(len(report['models']),'source model physics rows',len(raw),'bytes')


if __name__=='__main__':main()
