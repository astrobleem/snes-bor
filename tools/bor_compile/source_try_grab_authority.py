"""Pinned common_try_grab(NULL), mandatory C rand call and selector gates."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(text,'common_try_grab')
 enum_path=Path(__file__).parent/'authority/4086_animation_ids.json';enums=json.loads(enum_path.read_text())['enum'];ids={n:enums[n]for n in ('ANI_THROW','ANI_GRAB')}
 rows=[dict(chance=chance,throw=t,grab=g,idling=i,found=f,grabbed=r)for chance,t,g,i,f,r in itertools.product(range(8),(0,1),(0,1),(0,1,-1,65536),(0,1),(0,1))]
 code='''#include <stdio.h>
#include <stddef.h>
'''+''.join('#define '+n+' '+str(v)+'\n'for n,v in ids.items())+'''
typedef struct entity {int idling;struct {float x,z;} position;struct {int hostile;} modeldata;} entity;
entity ent,other,*self=&ent;int chance,throwanim,grabanim,found,grabbed,randomcalls,findcalls,grabcalls;
int rand(void){randomcalls++;return chance;}
int validanim(entity *e,int n){return n==ANI_THROW?throwanim:grabanim;}
entity *find_ent_here(entity *e,float x,float z,int hostile,entity *exclude){findcalls++;return found?&other:NULL;}
int trygrab(entity *target){grabcalls++;return grabbed;}
'''+function+'\nint cases[][6]={'+','.join('{'+','.join(str(c[k])for k in ('chance','throw','grab','idling','found','grabbed'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;chance=cases[i][0];throwanim=cases[i][1];grabanim=cases[i][2];ent.idling=cases[i][3];found=cases[i][4];grabbed=cases[i][5];randomcalls=findcalls=grabcalls=0;r=common_try_grab(NULL);printf("%d,%d,%d,%d\\n",r,randomcalls,findcalls,grabcalls);}return 0;}
'''
 (a.output/'try_grab.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','try_grab.c','-fe=try_grab.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'try_grab.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  find=int(c['chance']==0 and bool(c['throw']or c['grab'])and bool(c['idling']));expected.append([int(find and c['found']and c['grabbed']),1,find,int(find and c['found'])]);c['requires_find_service']=find
 ok=actual==expected
 report=dict(schema='BYOR_4086_TRY_GRAB_NULL_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),animation_constants=ids,cases=len(rows),inputs=rows,actual=actual,expected=expected,c_rand_return_instrumented=True,find_and_trygrab_bodies_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'try grab NULL source cases');assert ok
if __name__=='__main__':main()
