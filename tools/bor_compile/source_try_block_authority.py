"""Pinned common_try_block(NULL), full32 mask and ordered random/valid gates."""
import argparse, hashlib, itertools, json, os, subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--random-authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ra=json.loads(a.random_authority.read_text());assert ra['status']=='PASS';randomrows=ra['rows'][:8]
 source=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(source,'common_try_block')
 enums=json.loads((Path(__file__).parent/'authority/4086_animation_ids.json').read_text())['enum'];block=enums['ANI_BLOCK']
 rows=[dict(nopassiveblock=n,blockodds=o,random_index=r,random=randomrows[r][2],animation=v,found=f,attacking=k)for n,o,r,v,f,k in itertools.product((0,1,-1,65536),(0,1,2,3,65537,-1,-2147483647),range(8),(0,1),(0,1),(0,1,-1,65536))]
 code='''#include <stdio.h>
#include <stddef.h>
'''+ '#define ANI_BLOCK '+str(block)+'''
typedef struct entity {int attacking;void (*takeaction)(void);struct {float x,z;} velocity;struct {int nopassiveblock,blockodds;} modeldata;} entity;
entity ent,victim,*self=&ent;int present,found,randomcalls,validcalls,findcalls,setcalls;unsigned long randomvalue;
unsigned long rand32(void){randomcalls++;return randomvalue;}
int validanim(entity *e,int a){validcalls++;return present;}
entity *block_find_target(int a,int b){findcalls++;return found?&victim:NULL;}
void common_block(void){}
void set_blocking(entity *e){setcalls++;}
void ent_set_anim(entity *e,int a,int b){setcalls++;}
'''+function+'\nint cases[][6]={'+','.join('{'+','.join(str(c[k]if k!='random'else c[k]if c[k]<2147483648 else c[k]-4294967296)for k in ('nopassiveblock','blockodds','random','animation','found','attacking'))+'}'for c in rows)+'''};
int main(void){unsigned i;if(sizeof(int)!=4||sizeof(unsigned long)!=4)return 2;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;ent.modeldata.nopassiveblock=cases[i][0];ent.modeldata.blockodds=cases[i][1];randomvalue=(unsigned long)cases[i][2];present=cases[i][3];found=cases[i][4];victim.attacking=cases[i][5];randomcalls=validcalls=findcalls=setcalls=0;r=common_try_block(NULL);printf("%d,%d,%d,%d,%d\\n",r,randomcalls,validcalls,findcalls,setcalls);}return 0;}
'''
 (a.output/'try_block.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','try_block.c','-fe=try_block.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'try_block.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  rand=bool(c['nopassiveblock']);valid=rand and(c['random']&(c['blockodds']&0xffffffff))==1;find=valid and bool(c['animation']);result=find and c['found']and bool(c['attacking']);expected.append([int(result),int(rand),int(valid),int(find),2*int(result)]);c['requires_target_service']=int(find)
 ok=actual==expected;report=dict(schema='BYOR_4086_TRY_BLOCK_NULL_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),animation_constant=block,random_authority_sha256=hashlib.sha256(a.random_authority.read_bytes()).hexdigest(),random_rows=randomrows,cases=len(rows),inputs=rows,actual=actual,expected=expected,rand32_return_instrumented=True,target_and_mutation_bodies_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'try block source cases');assert ok
if __name__=='__main__':main()
