"""Literal weighted picker, range macro, energy predicate and engine RNG."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from script_dispatch_4086 import compile_source
from source_animation_range_4086 import derive as ranges
from source_animation_energy_4086 import derive as energy,check as check_energy
from source_check_range_4086 import check as check_range
from source_model_core_4086 import derive as core
from source_attack_choice_4086 import derive,choose
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def git(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd='E:/gh/openbor-bcec').decode('latin1')
 raw=git('engine/openbor.c');header=git('engine/openbor.h');picker=extract(raw,'pick_random_attack');ec=extract(raw,'check_energy')
 macro=header[header.index('#define check_range(self, target, animnum)'):header.index('#define check_range_both(')]
 validanim=next(l for l in header.splitlines()if l.startswith('#define validanim('))
 enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+n+r'\s*;',header,re.S)[0]for n in ('e_cost_check','e_cost_type','e_entity_type','e_entity_type_sub'))
 source=Source(a.source);profile=derive(source);rr=ranges(source);er=energy(source);mr=core(source)
 range_by={an['handle']:an['ranges']for an in rr['animations']};energy_by={an['handle']:an['fields']for an in er['animations']};frames={an['handle']:an['numframes']for an in er['animations']}
 models={m['identity']:m['id']for m in mr['models']};caches=[{}for _ in models]
 for h in compile_source(source)['animation_handles']:caches[models[h['model']]][h['engine_animation_id']]=h['handle']
 roles=profile['normal_roles']+profile['special_roles']+profile['extra_roles'];rows=[]
 for model in range(len(caches)):
  for pose in range(6):
   for testonly in (0,1):
    for seed in (0,1,0xffffffff,0x1234ffff):
     rows.append(dict(model=model,cache=caches[model],type=mr['models'][model]['fields']['type'],seal=(0,1,6)[pose%3],mp=(0,6,100)[pose%3],health=(1,6,100)[pose%3],source=[0]*4,target=([0,50,300,-50,80,0][pose]*65536,0,0,0),target_present=pose!=5,direction=1,projectile=pose%2==0,testonly=testonly,seed=seed))
 for mask in (0,1,3,15,255,4095,32767):
  cache={role:1 for i,role in enumerate(roles)if mask&(1<<i)}
  for testonly in (0,1,65536):
   for seed in (0,1,65535,0xffffffff):
    rows.append(dict(model=0,cache=cache,type=1,seal=0,mp=-1,health=1,source=[0]*4,target=[0]*4,target_present=True,direction=1,projectile=True,testonly=testonly,seed=seed,synthetic_mutable_cache=True))
 expected=[]
 for c in rows:
  valid={int(role)for role,h in c['cache'].items()if frames[h]};range_ok={int(role)for role,h in c['cache'].items()if check_range(range_by[h],c['source'],c['target'],c['direction'])}
  energy_ok={int(role)for role,h in c['cache'].items()if check_energy(1,energy_by[h],c['type'],c['seal'],c['mp'],c['health'])or check_energy(0,energy_by[h],c['type'],c['seal'],c['mp'],c['health'])}
  e=choose(profile,valid,range_ok,energy_ok,c['projectile'],c['testonly'],c['seed'],c['target_present']);expected.append([e['result'],e['seed_after'],e['calls']]);c['choices']=e['choices'];c['total']=e['total']
 code='''#include <stdio.h>
#include <string.h>
#include "rand32.h"
#define FALSE 0
#define TRUE 1
#define DIRECTION_RIGHT 1
'''+enums+'\n#define MAX_ANIMATIONS '+str(profile['maximum_animations'])+'\n'
 for name,role in zip(('ANI_THROWATTACK','ANI_JUMPATTACK','ANI_UPPER'),profile['extra_roles']):code+='#define '+name+' '+str(role)+'\n'
 code+='''typedef struct {int x,z,y,base;} axes;
typedef struct {int numframes;struct {axes min,max;}range;struct {int cost,mponly,disable;}energycost;} animation;
typedef struct entity {struct {int type,subtype;animation*animation[MAX_ANIMATIONS];}modeldata;int seal,mp,health,direction;struct {float x,z,y;}position;float base;struct entity*weapent;} entity;
entity ent,victim,weapon,*self=&ent;
'''+validanim+'\n'+macro+'\nint max_attacks='+str(len(profile['normal_roles']))+',max_freespecials='+str(len(profile['special_roles']))+';\n'
 for name,array in (('animattacks',profile['normal_roles']),('animspecials',profile['special_roles'])):code+='int '+name+'[]={'+','.join(map(str,array))+'};\n'
 code+='''#define rand32 rand32_body
#include "rand32.c"
#undef rand32
unsigned random_calls;
unsigned int rand32(void){random_calls++;return rand32_body();}
int atkchoices[109];
'''+ec+'\n'+picker+'\nanimation animations[]={ {0},\n'
 for handle in sorted(range_by):
  r=range_by[handle];f=energy_by[handle]
  code+='{'+str(frames[handle])+',{{'+','.join(str(r[i])for i in (0,2,4,6))+'},{'+','.join(str(r[i])for i in (1,3,5,7))+'}},{'+','.join(str(f[k])for k in ('cost','mponly','disable'))+'}},\n'
 code+='};typedef struct {int type,seal,mp,health,direction,present,projectile,testonly;unsigned long seed;float source[4],target[4];int cache[MAX_ANIMATIONS];} input;input cases[]={\n'
 for c in rows:
  cache=[c['cache'].get(i,0)for i in range(profile['maximum_animations'])]
  code+='{'+','.join(str(c[k])for k in ('type','seal','mp','health','direction'))+','+str(int(c['target_present']))+','+str(int(c['projectile']))+','+str(c['testonly'])+','+str(c['seed'])+'UL,{'+','.join(repr(n/65536)+'f'for n in c['source'])+'},{'+','.join(repr(n/65536)+'f'for n in c['target'])+'},{'+','.join(map(str,cache))+'}},\n'
 code+='''};int main(void){unsigned i,j;input*c;int result;unsigned long before;
weapon.modeldata.subtype=SUBTYPE_PROJECTILE;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=&cases[i];self->modeldata.type=c->type;self->seal=c->seal;self->mp=c->mp;self->health=c->health;self->direction=c->direction;self->weapent=c->projectile?&weapon:NULL;
'''
 for i,axis in enumerate(('x','z','y','base')):
  f='base'if axis=='base'else'position.'+axis;code+='self->'+f+'=c->source['+str(i)+'];victim.'+f+'=c->target['+str(i)+'];\n'
 code+='''for(j=0;j<MAX_ANIMATIONS;j++)self->modeldata.animation[j]=c->cache[j]?&animations[c->cache[j]]:NULL;
seed=c->seed;before=seed;random_calls=0;result=pick_random_attack(c->present?&victim:NULL,c->testonly);printf("%d,%lu,%u\\n",result,seed,random_calls);
}return 0;}
''';(a.output/'picker.c').write_text(code)
 for name in ('rand32.c','rand32.h'):(a.output/name).write_text(git('engine/source/randlib/'+name))
 (a.output/'types.h').write_text('typedef unsigned long long u64;\n')
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','picker.c','-fe=picker.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'picker.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];ok=actual==expected
 report=dict(schema='BYOR_4086_ATTACK_CHOICE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),profile=profile,inputs=rows,actual=actual,expected=expected,source_picker_sha256=hashlib.sha256(picker.encode()).hexdigest(),source_energy_sha256=hashlib.sha256(ec.encode()).hexdigest(),source_range_macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),source_rng_sha256=hashlib.sha256((a.output/'rand32.c').read_bytes()).hexdigest(),literal_picker_and_dependencies=True,source_coordinates_integral=True,enum_storage_bits=32,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'literal source weighted choices');assert ok

if __name__=='__main__':main()
