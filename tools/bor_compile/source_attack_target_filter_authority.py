"""Exercise the unchanged pinned do_attack outer target predicate."""
import argparse,hashlib,itertools,json,os,random,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_attack_target_filter_4086 import FIELDS,decide


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 def read(name):return subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/'+name],cwd=a.engine).decode('latin1')
 body=extract(read('openbor.c'),'do_attack');header=read('openbor.h')
 start=body.index('if( ent_list[i]->exists');end=body.index('{',start);predicate=body[start+2:end].strip()
 def enum(name):
  end=header.index('} '+name+';')+len('} '+name+';');start=header.rfind('typedef enum',0,end);return header[start:end]
 enums=enum('e_attack_types')+'\n'+enum('e_otg')
 baseline=dict(zip(FIELDS,(1,0,0,0,0,0,0,1,1,47,48,1,1,2,0,0,0,0,0,0,1,0)))
 axes={k:sorted(set((v,0,1,-65536,65536)))for k,v in baseline.items()}
 for k in ('time','pain_time','hit_by','attack_id'):axes[k]=[0,1,47,48,49,0x7fffffff,0x80000000,0xffffffff]
 axes['attack_type']=[0,15,16];axes['otg']=[-1,0,1,2,3];axes['falling']=[-65536,0,1,65536]
 rows=[baseline]
 for k,l in itertools.combinations(FIELDS,2):
  for v,w in itertools.product(axes[k],axes[l]):rows.append(dict(baseline,**{k:v,l:w}))
 rng=random.Random(4086)
 rows.extend({k:rng.choice(axes[k])for k in FIELDS}for _ in range(20000))
 code="""#include <stdio.h>
#include <string.h>
"""+enums+"""
typedef struct {int current;} metric;
typedef struct {int type;metric jugglepoints;} model;
typedef struct {int attackone;} anim;
typedef struct {int attack_type,otg,jugglecost,counterattack;} attack_t;
typedef struct entity {int exists,dead,invincible,falling;unsigned pain_time;int hit_by_attack_id;void *takedamage,*takeaction;model modeldata;struct entity *lasthit;} entity;
entity actor,target,*e=&actor,*ent_list[1]={&target};anim animation,*current_anim=&animation;attack_t attack_data,*attack=&attack_data;
int them,current_attack_id;unsigned time;int lie_token;void *common_lie=&lie_token;
int normal_result,counter_result,calls[2];
int checkhit(entity *a,entity *b,int mode){calls[mode]++;return mode?counter_result:normal_result;}
int query(void){int i=0;return """+predicate+"""
;}
int main(void){unsigned v[22];int i,ok;if(sizeof(int)!=4 || ATK_ITEM!=15 || OTG_BOTH!=1 || OTG_GROUND_ONLY!=2)return 2;
for(;;){for(i=0;i<22;i++)if(scanf("%u",&v[i])!=1)return i?3:0;
 target.exists=(int)v[0];target.dead=(int)v[1];target.invincible=(int)v[2];attack->attack_type=(int)v[3];current_anim->attackone=(int)v[4];e->lasthit=v[5]?(v[6]?&target:&actor):NULL;
 target.modeldata.type=(int)v[7];them=(int)v[8];target.pain_time=v[9];time=v[10];target.takedamage=v[11]?&actor:NULL;target.hit_by_attack_id=(int)v[12];current_attack_id=(int)v[13];target.takeaction=v[14]?common_lie:NULL;
 attack->otg=(int)v[15];target.falling=(int)v[16];attack->jugglecost=(int)v[17];target.modeldata.jugglepoints.current=(int)v[18];attack->counterattack=(int)v[19];normal_result=(int)v[20];counter_result=(int)v[21];calls[0]=calls[1]=0;
 ok=query();printf("%d %d %d\\n",ok,calls[0],calls[1]);}}
"""
 (a.output/'target_filter.c').write_text(code,encoding='latin1')
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','target_filter.c','-fe=target_filter.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('TARGET_FILTER_C_BUILD:'+build.stdout+build.stderr)
 inputs=''.join(' '.join(str(r[k]&0xffffffff)for k in FIELDS)+'\n'for r in rows);proc=subprocess.run([str((a.output/'target_filter.exe').resolve())],input=inputs,capture_output=True,text=True)
 actual=[list(map(int,l.split()))for l in proc.stdout.splitlines()];expected=[];rejected={}
 for r in rows:
  q=decide(r);expected.append([int(q['admitted']),int(0 in q['collision_modes']),int(1 in q['collision_modes'])]);rejected[q['rejected']or 'ADMITTED']=rejected.get(q['rejected']or 'ADMITTED',0)+1
 mismatch=[dict(index=i,input=rows[i],actual=actual[i]if i<len(actual)else None,expected=expected[i])for i in range(len(rows))if i>=len(actual)or actual[i]!=expected[i]]
 report=dict(schema='BYOR_ATTACK_TARGET_FILTER_AUTHORITY_V1',status='PASS'if proc.returncode==0 and len(actual)==len(rows)and not mismatch else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),predicate_sha256=hashlib.sha256(predicate.encode('latin1')).hexdigest(),enum_sha256=hashlib.sha256(enums.encode('latin1')).hexdigest(),inputs_sha256=hashlib.sha256(inputs.encode()).hexdigest(),outputs_sha256=hashlib.sha256(proc.stdout.encode()).hexdigest(),rejected=rejected,mismatches=mismatch,checkhit_instrumented=True,callbacks_and_damage_excluded=True,native_target_filter_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'pinned target-filter cases')
 if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
