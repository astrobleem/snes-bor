"""Derive a flat-stage, closed movement-script and grab-animation capability."""
import argparse
import json
from pathlib import Path
from compiler import Source, key
from source_profile import document, discover
from source_empty_init_environment import derive as environment
from source_level_physics_4086 import derive as physics
from dialect_4086 import ENGINE_COMMIT


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs)
    if structure['diagnostics']:raise ValueError('TRYMOVE_SOURCE_DIAGNOSTICS')
    models=[]
    for i,m in enumerate(structure['models']):
        doc=docs[key(m['source_path'])]
        grabs=[r for r in doc['directives'] if r['directive']=='anim' and r['values'] and r['values'][0].lower() in ('grab','throw')]
        events=[r for r in doc['directives'] if r['directive'].startswith('onblock') or r['directive'] in ('onmovexscript','onmovezscript')]
        models.append(dict(id=i,identity=m['declaration'],source_path=doc['source_path'],source_sha256=doc['sha256'],grab_animations=grabs,movement_events=events))
    env=environment(source);stages=physics(source)['stages']
    diagnostics=[]
    if any(m['grab_animations'] for m in models):diagnostics.append('TRYMOVE_GRAB_OWNER_REQUIRED')
    if any(m['movement_events'] for m in models):diagnostics.append('TRYMOVE_MOVEMENT_SCRIPT_OWNER_REQUIRED')
    if not env['platform_query_admitted']:diagnostics.append('TRYMOVE_PLATFORM_OWNER_REQUIRED')
    if any(not s['empty_geometry'] for s in stages):diagnostics.append('TRYMOVE_STAGE_GEOMETRY_OWNER_REQUIRED')
    if not 1<=len(models)<=16:diagnostics.append('TRYMOVE_MODEL_CAPACITY')
    return dict(schema='BYOR_4086_FLAT_TRYMOVE_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,
        capability='SOURCE_FLAT_CLOSED_TRYMOVE',admitted=not diagnostics,diagnostics=diagnostics,models=models,stages=stages,
        runtime_requirements=['current generation and serialized phase11 caller lease','actual B504/B4D1 immutable empty geometry lease',
            'closed installed model registry; revoke before geometry or movement-event mutation',
            'actual cached grab/throw handles remain absent','live obstacle/trap type candidate scan must prove empty when obstacle tests are enabled',
            'actual B5EA process-wide CRT random stream','actual B5CE source camera viewport and depth bounds'],
        coordinate_policy='ACCEPTED_COMPAT_Q16_16',native_world_owner_bound=False,foreign_profile_admitted=False,
        motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(r['capability'],r['admitted'],len(r['models']),'models',len(r['stages']),'stages')


if __name__=='__main__':main()
