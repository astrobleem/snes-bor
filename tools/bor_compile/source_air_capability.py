"""Derive the closed B621 air requirements without actor identity exceptions."""
import argparse
import json
from pathlib import Path
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_model_physics_4086 import derive as model_physics
from source_animation_physics_4086 import derive as animation_physics
from source_level_physics_4086 import derive as stage_physics


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs);physics=model_physics(source)['models'];animations=animation_physics(source)['animations']
    models=[]
    for model,fields in zip(structure['models'],physics):
        own=[a for a in animations if a['model']==model['declaration']]
        callbacks=[r for r in docs[key(model['source_path'])]['directives']if r['directive']=='onmoveascript']
        failures=[]
        if fields['fields']['height']!=0:failures.append('CEILING_BACKEND_REQUIRED')
        if fields['fields']['antigravity']!=0:failures.append('MODEL_ANTIGRAVITY_MULTIPLY_BACKEND_REQUIRED')
        if any(a['dropframe']>=0 for a in own):failures.append('DROPFRAME_CONTINUATION_REQUIRED')
        if any(a['role'].casefold()=='walkoff'for a in own):failures.append('WALKOFF_CONTINUATION_REQUIRED')
        if callbacks:failures.append('ONMOVEA_CALLBACK_CONTINUATION_REQUIRED')
        models.append(dict(index=fields['index'],identity=fields['identity'],source_path=fields['source_path'],source_sha256=fields['source_sha256'],
            requirements_satisfied=not failures,failures=failures,model_physics=fields['fields'],
            animation_handles=[a['handle']for a in own],
            capability='SOURCE_EMPTY_WORLD_ZERO_MODEL_ANTIGRAVITY_AIR'if not failures else'OTHER_AIR_BACKEND_REQUIRED'))
    stages=stage_physics(source)['stages']
    eligible=all(m['requirements_satisfied']for m in models)and all(s['empty_geometry']for s in stages)
    return dict(schema='BYOR_SOURCE_AIR_CAPABILITY_V1',engine_commit=ENGINE_COMMIT,models=models,stages=stages,
        closed_zero_profile_source_requirements_satisfied=eligible,
        native_entry='SourceGravityAir4086_Execute',leases=['B621 air','B622 immutable zero-height/zero-model-antigravity/no DROPFRAME/WALKOFF/onmovea registry','B623 immutable current-stage Q16 gravity/fall/toss limits','B620 closed empty geometry base','B61F immutable current-frame metadata','B61C physical physics state'],
        required_runtime_checks=['matching current-stage identity','current physical model/frame identity','revoke on model physics or callback or registry or geometry mutation','all native bounds/overflow guards','actual source base and freeze services'],
        numeric_policy='ACCEPTED_COMPAT_Q16_16; measured separately against binary32 authority',
        landing_status='Status1 is a pending source landing service; no toss/update_mark commit or whole POST Ack until real landing completion',
        native_landing_backend_bound=False,production_world_installer_bound=False,foreign_profile_admitted=False,
        motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(len(report['models']),'models; closed source requirements:',report['closed_zero_profile_source_requirements_satisfied'])


if __name__=='__main__':main()
