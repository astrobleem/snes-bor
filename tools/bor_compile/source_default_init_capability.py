"""Source-derived admission contract for the closed native default-init owner.

This is control-flow admission, not a foreign-game or constructor certificate.
All callback/frame effects still execute through their separate native owners.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_animation_ids import derive as animation_ids,configure,role_id
from source_model_core_4086 import derive as model_core
from source_lifecycle_inputs import derive as lifecycle
from source_idle_4086 import default_idle_capability
from source_walk_animation_4086 import default_walk_capability
from source_empty_init_environment import derive as empty_environment,descriptor as empty_descriptor
from source_player_spawn_height import derive as spawn_height
from source_default_drop_context import derive as drop_context
from source_binary32_q16 import project
from dialect_4086 import ENGINE_COMMIT

def derive(source):
 identities=animation_ids(source);core=model_core(source);life=lifecycle(source)
 idle=default_idle_capability(identities,core);walk=default_walk_capability(identities)
 empty=empty_environment(source);heights=spawn_height(source);drop=drop_context(source)
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);config=configure(docs[key(structure['models_path'])]['directives'])
 if not empty['platform_query_admitted']:raise ValueError('SOURCE_DEFAULT_INIT_PLATFORM_QUERY_REQUIRED')
 stages=[]
 for e,h,d in zip(empty['stages'],heights['stages'],drop['stages']):
  if e['stage_id']!=h['stage_id']or e['stage_id']!=d['stage_id']:raise ValueError('SOURCE_DEFAULT_INIT_STAGE_PAIR')
  empty_descriptor(empty,e['stage_id'])
  stages.append(dict(stage_id=e['stage_id'],source_path=e['source_path'],source_sha256=e['source_sha256'],empty_environment_descriptor_hex=empty_descriptor(empty,e['stage_id']).hex(),player_spawn_height_descriptor_hex=h['descriptor_hex'],drop_context=d))
 if not(len(empty['stages'])==len(heights['stages'])==len(drop['stages'])):raise ValueError('SOURCE_DEFAULT_INIT_STAGE_COUNT')
 models=[]
 for c,l,i in zip(core['models'],life['models'],identities['models']):
  if c['identity']!=l['identity']or c['identity']!=i['identity']:raise ValueError('SOURCE_DEFAULT_INIT_MODEL_PAIR')
  f=c['fields'];sub=l['fields']['subtype']
  if f['type']not in(0,1,2,512):raise ValueError('SOURCE_DEFAULT_INIT_TYPE_UNBOUND:'+c['identity']+':'+str(f['type']))
  if f['type']in(2,512)and sub in(1,3):raise ValueError('SOURCE_DEFAULT_INIT_ENEMY_SUBTYPE_UNBOUND:'+c['identity']+':'+str(sub))
  bits=struct.unpack('<I',struct.pack('<f',f['speed']))[0];speed=project(bits)
  models.append(dict(id=c['id'],identity=c['identity'],source_sha256=c['source_sha256'],type=f['type'],subtype=sub,roles=[a['role']for a in i['animations']],initial_speed_binary32_bits=bits,initial_speed_q16=speed,initial_speed_nonzero=int(bool(bits&0x7fffffff))))
 return dict(schema='BYOR_4086_DEFAULT_INIT_CONTROL_CAPABILITY_V1',engine_commit=ENGINE_COMMIT,capability='SOURCE_DEFAULT_INIT_CLOSED_NORMAL',models=models,stages=stages,role_inputs={n:role_id(config,n)for n in('spawn','respawn','select','jump','walk')},idle_capability=idle,walk_capability=walk,native_entry_points=['SourceDefaultInit4086_Begin','SourceDefaultInit4086_Continue'],pending_result=1,completed_result=0,frame_zero_owner='SourceAnimationInit4086 StartFrame + complete callbacks/effects + checked Ack',persistent_fields={'phase':0x7ffc8c,'slot':0x7ffc8e,'walk':0x7ffcba},snapshot_span=[0x7ffb50,0x7ffd60],caller_requirements=['install matching immutable animation/model/role tables and current actor core/lifecycle/speed identity','publish current stage B4D1/B504/B505 and hash-verified B5DC/B5RF context','republish B503 source time/JUMP and current-stage X/Y context at each Begin/Continue','run real frame-zero callback and effect service before Continue','do not invoke this nonrecursive initializer from a live animation-script interpreter'],numeric_policy='ACCEPTED_COMPAT_Q16_16; nonzero binary32 speed identity remains distinct from zero projection; source drop altitude expression table preserves source binary32 store before projection',constructor_cleanup_bound=False,script_copy_onspawn_bound=False,executable_ai_bound=False,production_world_installer_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print('SOURCE_DEFAULT_INIT_CLOSED_NORMAL',len(r['models']),'models',len(r['stages']),'stages; production world binding remains unproven')

if __name__=='__main__':main()
