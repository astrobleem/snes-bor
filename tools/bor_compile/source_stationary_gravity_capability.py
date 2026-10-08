"""Derive non-gravitating stationary-air requirements from source metadata.

No actor identity selects behavior. The native caller must still verify actual
instance identity, typed coordinates, velocity and resolved no_adjust_base.
"""
import argparse
import json
from pathlib import Path
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_model_core_4086 import derive as core
from source_level_physics_4086 import derive as physics


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);models=[]
    for model,cached in zip(structure['models'],core(source)['models']):
        doc=docs[key(model['source_path'])]
        drops=[r for r in doc['directives']if r['directive']=='dropframe']
        walkoff=any(a['role'].casefold()=='walkoff'for a in model['animations'])
        fields=cached['fields'];eligible=fields['type']==0 and fields['subject_to_gravity']==0 and not drops and not walkoff
        models.append(dict(id=cached['id'],identity=cached['identity'],source_path=doc['source_path'],source_sha256=doc['sha256'],
                           type=fields['type'],declared_subject_to_gravity=fields['subject_to_gravity'],dropframe_declarations=drops,
                           walkoff_animation_present=walkoff,non_gravitating_hover_requirements=eligible,
                           capability='SOURCE_STICKY_NONGRAVITATING_HOVER'if eligible else'OTHER_GRAVITY_BACKEND_REQUIRED'))
    stages=[]
    for s in physics(source)['stages']:
        limits=s['physics'];stages.append(dict(source_path=s['source_path'],source_sha256=s['source_sha256'],physics=limits,
            zero_vertical_velocity_retained=limits['maxfallspeed']<=0<=limits['maxtossspeed']))
    return dict(schema='BYOR_SOURCE_STATIONARY_GRAVITY_CAPABILITY_V1',engine_commit=ENGINE_COMMIT,models=models,stages=stages,
        native_entry='SourceGravityIdle4086_Execute',post_update_entry='SourcePostStationary4086_Execute',post_owner_state=2,post_owner_phase=11,post_lease='B61A; native Issue binds current physical slot; Ack requires completed status2',native_lease='B619; B618 keeps the stricter altitude==base branch',
        caller_requirements=['complete source constructor and current model/frame identity','B504 immutable no-platform registry plus current B4D1 stage','stage fall/toss limits cover zero and remain immutable','compiler-closed falling=0 and no binding mutation capability','invalidate on dropframe/WALKOFF, physics, registry or instance-policy mutation','native checks positive no_adjust_base, zero vertical velocity, typed altitude/base and nonlanding Q16 difference'],
        numeric_policy='ACCEPTED_COMPAT_Q16_16; nonlanding difference >=6554 represents pinned inair threshold >=0.1',
        alpha_and_presentation_selected_separately=True,production_world_installer_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(models=[m['identity']for m in r['models']if m['non_gravitating_hover_requirements']],stages=r['stages'])))


if __name__=='__main__':main()
