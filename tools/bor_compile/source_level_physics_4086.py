"""Pinned load_level/load_levelorder physics inputs and geometry requirements."""
import argparse
import json
import math
from pathlib import Path
import struct
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_model_core_4086 import binary32 as f32
from source_profile import document,discover

FIELDS=('gravity','maxfallspeed','maxtossspeed')
DEFAULTS=dict(gravity=f32(-.1),maxfallspeed=f32(-6),maxtossspeed=f32(100))


def argument(values,index=0):
    try:value=f32(values[index])if index<len(values)else 0.0
    except (ValueError,OverflowError):raise ValueError('SOURCE_PHYSICS_NUMERIC_ARGUMENT_REQUIRED')
    if not math.isfinite(value):raise ValueError('SOURCE_PHYSICS_FINITE_ARGUMENT_REQUIRED')
    return value


def global_physics(rows,initial=None):
    values=dict(DEFAULTS if initial is None else initial)
    for r in rows:
        if r['directive']=='gravity':values={k:argument(r['values'],i)for i,k in enumerate(FIELDS)}
    return values


def stage_physics(rows,defaults):
    values=dict(defaults)
    for r in rows:
        n=r['directive']
        if n in FIELDS:values[n]=f32(argument(r['values'])/(100 if n=='gravity'else 10))
    return values


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs)
    if structure['diagnostics']:raise ValueError('SOURCE_PHYSICS_SOURCE_DIAGNOSTICS')
    global_doc=docs[key(structure['levels_path'])];defaults=global_physics(global_doc['directives']);seen=set();stages=[]
    for s in structure['sets']:
        for e in s['entries']:
            if e['kind']!='STAGE'or key(e['source_path'])in seen:continue
            seen.add(key(e['source_path']));doc=docs[key(e['source_path'])];values=stage_physics(doc['directives'],defaults)
            requirements={n:[r for r in doc['directives']if r['directive']==n]for n in ('wall','hole','basemap')}
            stages.append(dict(source_path=doc['source_path'],source_sha256=doc['sha256'],physics=values,
                               physics_binary32_bits={k:struct.unpack('<I',struct.pack('<f',v))[0]for k,v in values.items()},
                               geometry_requirements=requirements,empty_geometry=not any(requirements.values())))
    return dict(schema='BYOR_4086_SOURCE_LEVEL_PHYSICS_V1',engine_commit=ENGINE_COMMIT,levels_source=global_doc['source_path'],levels_sha256=global_doc['sha256'],defaults=defaults,stages=stages,
                numeric_policy='Source binary32 parser stores; stage gravity /100, fall/toss limits /10. Global gravity triple is unscaled.',
                native_numeric_policy_proven=False,geometry_queries_bound=False,production_world_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps([dict(stage=s['source_path'],physics=s['physics'],empty_geometry=s['empty_geometry'])for s in r['stages']]))


if __name__=='__main__':main()
