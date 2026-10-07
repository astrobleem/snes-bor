"""Derived admission for default-map named knife post-construction.

This capability currently admits remove_on_attack=0. Nonzero remove must get
its own persistent field binding before native admission. No model names select
the capability. Palette map arguments other than zero remain explicit faults.
"""
import argparse, hashlib, json
from pathlib import Path
from compiler import Source, key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document, discover
from source_model_core_4086 import integer

def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    models=[]
    for i,model in enumerate(discover(source,docs)['models']):
        doc=docs[key(model['source_path'])];remove=0
        for row in doc['directives']:
            if row['directive']=='anim':break
            if row['directive']=='remove':
                if len(row['values'])!=1:raise ValueError('NAMED_KNIFE_REMOVE_ARITY')
                remove=integer(row['values'])
        models.append(dict(id=i,identity=model['declaration'],source_sha256=doc['sha256'],remove=remove,
                           eligible=remove==0))
    if not 1<=len(models)<=16:raise ValueError('NAMED_KNIFE_MODEL_CAPACITY')
    if not all(m['eligible']for m in models):raise ValueError('NAMED_KNIFE_REMOVE_FIELD_BACKEND_REQUIRED')
    return dict(schema='BYOR_4086_NAMED_KNIFE_CAPABILITY_V1',engine_commit=ENGINE_COMMIT,
                capability='NAMED_KNIFE_ZERO_REMOVE_DEFAULT_MAP',models=models,
                map_argument_domain=[0],ptype=0,remove_on_attack=0,
                native_api_bound=False,constructor_allocation_bound=False,
                motu_gameplay_proven=False,no_color_reduction=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(len(r['models']),'derived zero-remove models')

if __name__=='__main__':main()
