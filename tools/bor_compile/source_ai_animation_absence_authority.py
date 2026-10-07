"""Pinned lie/grabbed/escape predicates when required animation is absent."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1')
 functions='\n\n'.join(extract(text,n)for n in ('ai_check_lie','ai_check_grabbed','ai_check_escape'))
 constants_path=Path(__file__).parent/'authority/4086_animation_ids.json';constants=json.loads(constants_path.read_text())
 # Load the enum authority, rather than inventing model-specific animation IDs.
 assert constants['engine_commit']==ENGINE_COMMIT
 enums=constants['enum']
 selected={n:enums[n]for n in ('ANI_RISEATTACK','ANI_SPECIAL','ANI_SPECIAL2')}
 rows=[dict(mask=m,value=v)for m in range(128)for v in (1,65536,-1)]
 code='''#include <stdio.h>
'''+''.join('#define '+n+' '+str(v)+'\n'for n,v in selected.items())+'''
typedef struct entity {struct entity *link;int drop,grabbing,inpain,health,escapecount;struct {float y;} position,velocity;float base;unsigned stalltime;struct {unsigned riseattack_stall;} staydown;struct {int escapehits;} modeldata;void (*takeaction)(void);} entity;
entity ent,other,*self=&ent;unsigned time=48;int effects,randoms,validcalls,air;
void common_prethrow(void){}void other_action(void){}
int validanim(entity *e,int n){validcalls++;return 0;}
int inair(entity *e){return air;}
unsigned rand32(void){randoms++;return 0;}
void common_try_riseattack(void){effects++;}int check_special(void){effects++;return 1;}int check_costmove(int a,int b,int c){effects++;return 1;}
'''+functions+'\nint cases[][2]={'+','.join('{'+str(c['mask'])+','+str(c['value'])+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int m=cases[i][0],v=cases[i][1],a,b,c;ent.drop=(m&1)?v:0;ent.position.y=(m&2)?1:0;ent.base=0;ent.velocity.y=(m&4)?1:0;ent.link=(m&8)?&other:0;ent.grabbing=(m&16)?v:0;ent.inpain=(m&32)?v:0;ent.takeaction=(m&64)?common_prethrow:other_action;ent.stalltime=48;ent.health=v;ent.staydown.riseattack_stall=0;ent.escapecount=v;ent.modeldata.escapehits=0;air=(m&2)?1:0;effects=randoms=validcalls=0;a=ai_check_lie();b=ai_check_grabbed();c=ai_check_escape();printf("%d,%d,%d,%d,%d,%d\\n",a,b,c,effects,randoms,validcalls);}return 0;}
'''
 (a.output/'ai_absence.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','ai_absence.c','-fe=ai_absence.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'ai_absence.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()]
 expected=[]
 for c in rows:
  m,v=c['mask'],c['value'];calls=int(bool(m&1)and not(m&6))+int(bool(m&8)and not(m&16)and not(m&32)and not(m&64)and not(m&2))+int(v>0 and not(m&2));expected.append([0,0,0,0,0,calls])
 ok=actual==expected
 report=dict(schema='BYOR_4086_AI_ANIMATION_ABSENCE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),animation_enum_sha256=hashlib.sha256(constants_path.read_bytes()).hexdigest(),animation_constants=selected,cases=len(rows),inputs=rows,actual=actual,expected=expected,validanim_missing=True,inair_pure_predicate_instrumented=True,initialized_handler_bodies_unbound=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'animation absence predicate cases');assert ok
if __name__=='__main__':main()
