"""Literal common_try_jumpattack with instrumented target/mutation services."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(source,'common_try_jumpattack')
 enums=json.loads((Path(__file__).parent/'authority/4086_animation_ids.json').read_text())['enum'];ids={n:enums[n]for n in ('ANI_JUMPATTACK','ANI_JUMPATTACK2')}
 rows=[dict(first=f,second=s,random=r,target=t)for f,s,r,t in itertools.product((0,1),(0,1),(0,1,-1,65536),(0,1))]
 code='#include <stdio.h>\n#include <stddef.h>\n'+''.join('#define '+n+' '+str(v)+'\n'for n,v in ids.items())+'''
#define DIRECTION_RIGHT 1
typedef struct animation {int vulnerable[1];} animation;
typedef struct entity {int animpos,drop,attacking,direction,jumping,autokill;float base;unsigned nextattack;void(*takeaction)(void);struct {float x,y,z;} position,velocity;struct {float attackthrottletime,jumpheight;struct {int jump_start;} dust;}modeldata;animation*animation;} entity;
entity ent,victim,*self=&ent;animation anim;unsigned time=48;int first,second,randomvalue,found,randomcalls,findcalls,mutations;
int validanim(entity*e,int n){return n==ANI_JUMPATTACK?first:second;}
unsigned rand32(void){randomcalls++;return (unsigned)randomvalue;}
float randf(float x){randomcalls++;return 0;}
entity*normal_find_target(int a,int b){findcalls++;return found?&victim:NULL;}
unsigned recheck_nextattack(entity*e){return 0;}
int check_attack_chance(entity*e,float a,float b){return 1;}
void common_jump(void){}
void set_attacking(entity*e){mutations++;}
void toss(entity*e,float h){mutations++;}
entity*spawn(float x,float z,float y,int d,void*a,int i,void*b){mutations++;return NULL;}
void execute_onspawn_script(entity*e){mutations++;}
void ent_set_anim(entity*e,int a,int b){mutations++;}
'''+function+'\nint cases[][4]={'+','.join('{'+','.join(str(c[k])for k in ('first','second','random','target'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;first=cases[i][0];second=cases[i][1];randomvalue=cases[i][2];found=cases[i][3];randomcalls=findcalls=mutations=0;anim.vulnerable[0]=1;victim.animation=&anim;victim.animpos=victim.drop=victim.attacking=0;ent.modeldata.dust.jump_start=-1;r=common_try_jumpattack(NULL);printf("%d,%d,%d,%d\\n",r,randomcalls,findcalls,mutations);}return 0;}
'''
 (a.output/'jump_attack.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','jump_attack.c','-fe=jump_attack.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 log=subprocess.check_output([str(a.output/'jump_attack.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  present=bool(c['first']or c['second']);result=present and c['target'];expected.append([int(bool(result)),int(bool(c['first']and c['second'])),int(present),3*int(bool(result))]);c['requires_target_service']=int(present)
 ok=actual==expected
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_JUMP_ATTACK_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),animation_constants=ids,cases=len(rows),inputs=rows,actual=actual,expected=expected,target_mutation_and_random_services_instrumented=True,motu_gameplay_proven=False),indent=2)+'\n');print('PASS'if ok else'FAIL',len(rows),'literal jump attack cases');assert ok
if __name__=='__main__':main()
