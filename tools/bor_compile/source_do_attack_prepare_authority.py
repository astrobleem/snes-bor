"""Unchanged pinned do_attack prefix with native-sized unsigned identity bits."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_do_attack_prepare_4086 import prepare


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');body=extract(raw,'do_attack');start=body.index('    if(level_completed || !attack)');end=body.index('    for(i = 0; i < ent_max && !followed; i++)',start);prefix=body[start:end]
 vals=(-2147483648,-65536,-1,0,1,65536,2147483647)
 rows=list(itertools.product((0,1,-65536),(0,1),(0,1,3,127),vals,(0,2,65536,-2147483648),(1,0xffffffff),(0,1,0x80000000,0xffffffff),(1,0xfffffffe,0xffffffff),(-2147483648,0,7)))
 code="""#include <stdio.h>
#include <string.h>
typedef struct {int candamage,projectilehit;} model;
typedef struct anim {int value;} anim;
typedef struct entity {struct entity *owner;int projectile,attack_id;model modeldata;anim *animation;} entity;
typedef struct {int attack_force;} s_attack;
entity pool[128],*e=pool,*topowner;anim a,*current_anim;s_attack hit,*attack;int level_completed,them,current_attack_id,force;unsigned new_attack_id;
void prefix(void){"""+prefix+"""}
int main(void){int completed,has,depth,projectile,damage,shot,f,i;unsigned id,seq;
if(sizeof(int)!=4 || sizeof(unsigned)!=4)return 2;
while(scanf("%d %d %d %d %d %d %u %u %d",&completed,&has,&depth,&projectile,&damage,&shot,&id,&seq,&f)==9){memset(pool,0,sizeof(pool));
for(i=0;i<depth;i++)pool[i].owner=pool+i+1;e->projectile=projectile;e->modeldata.candamage=damage;e->modeldata.projectilehit=shot;memcpy(&e->attack_id,&id,4);e->animation=&a;
level_completed=completed;hit.attack_force=f;attack=has?&hit:NULL;new_attack_id=seq;topowner=NULL;them=0;force=0;current_anim=NULL;
prefix();printf("%u %u %d %u %d %d\\n",(unsigned)e->attack_id,new_attack_id,topowner?(int)(topowner-pool):-1,(unsigned)them,force,current_anim==&a);}
return 0;}
"""
 (a.output/'prepare.c').write_text(code,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','prepare.c','-fe=prepare.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('DO_ATTACK_PREPARE_BUILD:'+build.stdout+build.stderr)
 inputs=''.join(' '.join(str(v)for v in row)+'\n'for row in rows);proc=subprocess.run([str((a.output/'prepare.exe').resolve())],input=inputs,capture_output=True,text=True);actual=[list(map(int,l.split()))for l in proc.stdout.splitlines()];expected=[]
 for completed,has,depth,projectile,damage,shot,id,seq,f in rows:
  pool=[dict(owner=i+1 if i<depth else None,projectile=projectile,projectilehit=shot,candamage=damage,attack_id=id,animation=123)for i in range(128)]
  q,ns=prepare(pool,0,completed,dict(attack_force=f)if has else None,seq)
  expected.append([pool[0]['attack_id'],ns,q['topowner']if q else-1,q['them']if q else 0,q['force']if q else 0,int(q is not None)])
 mismatch=[dict(index=i,input=list(rows[i]),actual=actual[i]if i<len(actual)else None,expected=expected[i])for i in range(len(rows))if i>=len(actual)or actual[i]!=expected[i]]
 report=dict(schema='BYOR_DO_ATTACK_PREPARE_AUTHORITY_V1',status='PASS'if proc.returncode==0 and len(actual)==len(rows)and not mismatch else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),prefix_sha256=hashlib.sha256(prefix.encode('latin1')).hexdigest(),input_sha256=hashlib.sha256(inputs.encode()).hexdigest(),output_sha256=hashlib.sha256(proc.stdout.encode()).hexdigest(),mismatches=mismatch,defense_threshold_expression_excluded=True,ordered_target_loop_excluded=True,native_combat_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'pinned do_attack preparation cases')
 if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
