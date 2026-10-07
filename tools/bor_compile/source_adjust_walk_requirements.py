"""Derived default-series adjust_walk_animation capability, without model aliases."""
import argparse,hashlib,json
from pathlib import Path
from compiler import Source,key
from source_profile import document
from source_animation_ids import configure
from source_model_switch_requirements import derive as model_requirements

def derive(source):
 config=configure(document(source,source.index[key('data/models.txt')][0])['directives']);models=model_requirements(source)
 if any(config['limits'][n]!=1 for n in ('max_walks','max_ups','max_downs','max_backwalks')):raise ValueError('SOURCE_ADJUST_WALK_MULTIPLE_SERIES_REQUIRED')
 roles={n:config['arrays'][arr][0]for n,arr in [('walk','walks'),('up','ups'),('down','downs'),('backwalk','backwalks')]};roles['run']=config['authority']['enum']['ANI_RUN']
 forbidden={roles[n]for n in ('up','down','backwalk')};present=[dict(model=m['identity'],role=a['role'],engine_animation_id=a['engine_animation_id'])for m in models['models']for a in m['animation_slots']if a['engine_animation_id']in forbidden]
 if present:raise ValueError('SOURCE_ADJUST_WALK_DIRECTIONAL_SERVICE_REQUIRED:'+json.dumps(present))
 return dict(schema='BYOR_4086_ADJUST_WALK_REQUIREMENTS_V1',capability='SINGLE_WALK_WITH_RUN_AND_ABSENT_DIRECTIONAL_SERIES',roles=roles,models=[dict(identity=m['identity'],source_sha256=m['source_sha256'],run_present=any(a['engine_animation_id']==roles['run']for a in m['animation_slots']),walk_present=any(a['engine_animation_id']==roles['walk']for a in m['animation_slots']))for m in models['models']],mutable_cache_guards_required=True,walkmode_domain=[0,1],running_nonzero_uses_run=True,absent_run_literal_no_animation=True,absent_walk_literal_no_animation_then_playback_direction=True,source_framezero_required=True,native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);r=derive(Source(a.source));(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['capability'],len(r['models']),r['roles'])
