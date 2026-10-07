"""Literal unsigned source timer mutations, including two successive calls."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(source,'recheck_nextattack')
 rows=[dict(blocking=b,attacking=k,jumping=j,timer=t)for b,k,j,t in itertools.product((0,1,-1,65536),(0,1,-1,65536),(0,1,-1,65536),(0,1,4,5,16,17,65535,65536,0xffffffff))]
 code='''#include <stdio.h>
typedef unsigned int u32;
typedef struct entity {int blocking,attacking,jumping;u32 nextattack;} entity;
entity ent,victim,*self=&ent;
'''+function+'\nunsigned cases[][4]={'+','.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in ('blocking','attacking','jumping','timer'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){u32 first,second;victim.blocking=cases[i][0];victim.attacking=cases[i][1];victim.jumping=cases[i][2];ent.nextattack=cases[i][3];first=recheck_nextattack(&victim);second=recheck_nextattack(&victim);printf("%u,%u,%u\\n",first,second,ent.nextattack);}return 0;}
'''
 (a.output/'recheck.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','recheck.c','-fe=recheck.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'recheck.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  def step(t):return 0 if c['blocking']else t-4 if c['attacking']and t>4 else t-16 if c['jumping']and t>16 else t
  first=step(c['timer']);second=step(first);expected.append([first,second,second])
 ok=actual==expected
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_RECHECK_NEXTATTACK_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,body_instrumented=False,motu_gameplay_proven=False),indent=2)+'\n');print('PASS'if ok else'FAIL',len(rows),'literal recheck timer pairs');assert ok
if __name__=='__main__':main()
