"""Literal source uppercut/runattack selectors and their early false gates."""
import argparse, hashlib, itertools, json, os, subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1')
 functions={n:extract(source,n)for n in ('common_try_upper','common_try_runattack')}
 enums=json.loads((Path(__file__).parent/'authority/4086_animation_ids.json').read_text())['enum'];ids={n:enums[n]for n in ('ANI_UPPER','ANI_RUNATTACK')}
 rows=[dict(selector=s,animation=a,running=r,target=t,jumping=j,vulnerable=v,drop=d,attacking=k)for s,a,r,t,j,v,d,k in itertools.product((2,4),(0,1),(0,1,-1,65536),(0,1),(0,1),(0,1),(0,1),(0,1))]
 code='#include <stdio.h>\n#include <stddef.h>\n'+''.join('#define '+n+' '+str(v)+'\n'for n,v in ids.items())+'''
typedef struct animation {int vulnerable[1];} animation;
typedef struct entity {int running,jumping,drop,attacking,animpos;void (*takeaction)(void);struct {float x,z;} velocity;animation *animation;} entity;
entity ent,victim,*self=&ent;animation anim;int present,found,findcalls,setcalls;
int validanim(entity *e,int n){return present;}
entity *normal_find_target(int a,int b){findcalls++;return found?&victim:NULL;}
void common_attack_proc(void){}
void set_attacking(entity *e){setcalls++;e->attacking=1;}
void ent_set_anim(entity *e,int a,int b){setcalls++;}
'''+ '\n'.join(functions.values())+'\nint cases[][8]={'+','.join('{'+','.join(str(c[k])for k in ('selector','animation','running','target','jumping','vulnerable','drop','attacking'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;present=cases[i][1];ent.running=cases[i][2];found=cases[i][3];victim.jumping=cases[i][4];anim.vulnerable[0]=cases[i][5];victim.drop=cases[i][6];victim.attacking=cases[i][7];victim.animation=&anim;victim.animpos=0;findcalls=setcalls=0;r=cases[i][0]==2?common_try_upper(NULL):common_try_runattack(NULL);printf("%d,%d,%d\\n",r,findcalls,setcalls);}return 0;}
'''
 (a.output/'attack_entry.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','attack_entry.c','-fe=attack_entry.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 log=subprocess.check_output([str(a.output/'attack_entry.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  find=bool(c['animation'])and(c['selector']==2 or bool(c['running']));result=find and c['target']and(c['jumping']if c['selector']==2 else c['vulnerable']or not(c['drop']or c['attacking']));expected.append([int(result),int(find),2*int(result)]);c['requires_target_service']=int(find)
 ok=actual==expected
 report=dict(schema='BYOR_4086_ATTACK_ENTRY_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256={n:hashlib.sha256(v.encode()).hexdigest()for n,v in functions.items()},animation_constants=ids,cases=len(rows),inputs=rows,actual=actual,expected=expected,target_and_mutation_bodies_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'attack entry source cases');assert ok
if __name__=='__main__':main()
