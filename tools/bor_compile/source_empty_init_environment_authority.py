"""Verbatim 4086 empty initialization queries; full testplatform short circuit."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');functions='\n'.join(extract(raw,n)for n in ('testplatform','check_platform_below','checkwall_below'))
 source=r'''#include <stdio.h>
#include <string.h>
#define MIN_INT (-2147483647-1)
typedef struct {float (*platform)[8];} Anim;
typedef struct entity {int exists,animpos;Anim *animation;struct {float x,y,z;} position;} entity;
typedef struct {int numwalls;struct {float height;}walls[1];} Level;
entity pool[128],*ent_list[128];Anim anim[128];float platforms[128][1][8];Level lev,*level;int ent_max,wall_calls;
int testwall(int i,float x,float z){wall_calls++;return 1;}
'''+functions+r'''
int main(void){int l,count,mode,exists,exclude,coord,i,n=0;unsigned bits[]={0,0x7f800000,0x7fc00000,0xff800000};float x,z,a;
if(sizeof(void*)!=4)return 2;
for(l=0;l<2;l++)for(count=0;count<3;count++)for(mode=0;mode<3;mode++)for(exists=0;exists<3;exists++)for(exclude=0;exclude<3;exclude++)for(coord=0;coord<4;coord++){
 memset(pool,0,sizeof(pool));memset(platforms,0,sizeof(platforms));memset(&lev,0,sizeof(lev));level=l?&lev:NULL;ent_max=count==0?0:count==1?1:128;wall_calls=0;
 for(i=0;i<128;i++){ent_list[i]=pool+i;pool[i].exists=exists==0?0:exists==1?1:i&1;pool[i].animation=mode==0?NULL:anim+i;anim[i].platform=mode==1?NULL:platforms[i];}
 memcpy(&x,bits+coord,4);z=a=x;
 printf("EMPTY|%d|%d,%d,%d\n",n++,check_platform_below(x,z,a,exclude==0?NULL:pool+(exclude==1?0:127))==NULL,checkwall_below(x,z,a),wall_calls);
}return 0;}
'''
 (a.output/'empty.c').write_text(source);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','empty.c','-fe=empty.exe'],cwd=a.output.resolve(),env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('EMPTY_INIT_C_BUILD')
 log=subprocess.check_output([str((a.output/'empty.exe').resolve())],text=True);(a.output/'authority.log').write_text(log);results=[]
 for line in log.splitlines():
  if line.startswith('EMPTY|'):
   _,i,v=line.split('|');values=list(map(int,v.split(',')));results.append(dict(case=int(i),values=values,pass_case=values==[1,-1,0]))
 ok=len(results)==648 and all(r['pass_case']for r in results);report=dict(schema='BYOR_4086_EMPTY_INIT_ENVIRONMENT_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),cases=len(results),results=results,source_testplatform_body_verbatim=True,source_check_platform_below_body_verbatim=True,source_checkwall_below_body_verbatim=True,testwall_instrumented=True,loader_platform_absence_authority_bound=False,native_queries_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results),'empty environment cases')
 if not ok:raise SystemExit(1)

if __name__=='__main__':main()
