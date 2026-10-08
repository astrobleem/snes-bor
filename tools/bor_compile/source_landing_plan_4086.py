"""Immutable per-animation landing velocity requirements, joined by source identity."""
import argparse
import json
from pathlib import Path
import struct
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document
from source_model_core_4086 import integer
from source_model_core_4086 import derive as model_core
from source_model_physics_4086 import derive as model_physics
from source_animation_bounce_4086 import derive as animation_bounce


def noquake(rows):
    value=0
    for row in rows:
        if row['directive']=='noquake':
            args=row['values']
            value |= (1 if integer(args[:1])else 0) | (2 if integer(args[1:2])else 0)
    return value


def derive(source):
    models=model_physics(source)['models'];animations=animation_bounce(source)['animations']
    indexed={m['identity']:m for m in models};cores={m['identity']:m for m in model_core(source)['models']};plans=[]
    for animation in animations:
        model=indexed[animation['model']]
        doc=document(source,source.index[key(model['source_path'])][0])
        plans.append(dict(handle=animation['handle'],model_index=model['index'],model=model['identity'],
                          animation=animation['role'],animation_bounce=animation['bounce'],model_bounce=model['fields']['bounce'],
                          fall_land_dust=cores[model['identity']]['fields']['dust.fall_land'],
                          noquake=noquake(doc['directives']),source_sha256=doc['sha256']))
        plan=plans[-1]
        failures=[]
        if plan['fall_land_dust']>=0:failures.append('FALL_LAND_DUST_CONTINUATION_REQUIRED')
        if plan['model_bounce'] and plan['animation_bounce'] not in (0.,4.):
            failures.append('OTHER_BOUNCE_DIVISION_BACKEND_REQUIRED')
        plan.update(native_velocity_requirements_satisfied=not failures,failures=failures,
                    capability='SOURCE_LANDING_VELOCITY_ZERO_OR_FOUR'if not failures else'OTHER_LANDING_VELOCITY_BACKEND_REQUIRED')
    return dict(schema='BYOR_4086_LANDING_PLAN_V1',engine_commit=ENGINE_COMMIT,plans=plans,
                immutable_registry_requires_revocation_on_model_or_animation_mutation=True,
                no_fall_land_dust_registry_requirements_satisfied=all(p['fall_land_dust']<0 for p in plans),
                native_velocity_registry_requirements_satisfied=all(p['native_velocity_requirements_satisfied']for p in plans),
                native_landing_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack(report):
    plans=sorted(report['plans'],key=lambda p:p['handle'])
    if not 1<=len(plans)<=128:raise ValueError('LANDING_PLAN_CAPACITY')
    raw=bytearray(struct.pack('<4s6H',b'B4LP',1,len(plans),16,0,0,0))
    for handle,p in enumerate(plans,1):
        if handle!=p['handle']:raise ValueError('LANDING_PLAN_HANDLE_ORDER')
        if not 0<=p['model_index']<=127:raise ValueError('LANDING_PLAN_MODEL_INDEX')
        raw.extend(struct.pack('<HHfiI',handle,p['model_index'],p['animation_bounce'],p['model_bounce'],p['noquake']))
    return bytes(raw)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=derive(Source(a.source));raw=pack(report);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n');a.output.with_suffix('.b4lp').write_bytes(raw)
    print(len(report['plans']),'identity-bound landing plans',len(raw),'bytes')


if __name__=='__main__':main()
