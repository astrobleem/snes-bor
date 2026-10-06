"""Verbatim level spawn loader cases and defaults, Watcom Win32."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from source_player_spawn_height import load

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
 default=re.search(r'^    level->spawn\[0\].y =.*?;',raw,re.M)[0];start=raw.index('        case CMD_LEVEL_SPAWN1:');body=raw[start:raw.index('        case CMD_LEVEL_FRONTPANEL:',start)]
 rows=[[]]+[[dict(directive='spawn'+str(player),values=['10','20',y])]for player in range(1,5)for y in ('','0','-1','300','32767','2147483647','-2147483648','4.9','abc')]
 cases=','.join('{'+str(-1 if not r else int(r[0]['directive'][-1])-1)+',"'+(''if not r else r[0]['values'][2])+'"}'for r in rows)
 source=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define CMD_LEVEL_SPAWN1 0
#define CMD_LEVEL_SPAWN2 1
#define CMD_LEVEL_SPAWN3 2
#define CMD_LEVEL_SPAWN4 3
#define GET_INT_ARG(n) atoi(args[n-1])
typedef struct {struct {int x,z,y;}spawn[4];} Level;
struct {int cmd;char *y;}cases[]={'''+cases+r'''};
int main(void){Level lev,*level=&lev;int n,i,cmd;char *args[3]={"10","20",NULL};for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){memset(&lev,0,sizeof(lev));'''+default+r'''
cmd=cases[n].cmd;args[2]=cases[n].y;switch(cmd){'''+body+r'''}printf("HEIGHT|%d|%d,%d,%d,%d\n",n,lev.spawn[0].y,lev.spawn[1].y,lev.spawn[2].y,lev.spawn[3].y);}return 0;}
'''
 (a.output/'height.c').write_text(source);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','height.c','-fe=height.exe'],cwd=a.output.resolve(),env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('PLAYER_HEIGHT_C_BUILD')
 log=subprocess.check_output([str((a.output/'height.exe').resolve())],text=True);(a.output/'authority.log').write_text(log);results=[]
 for line in log.splitlines():
  if line.startswith('HEIGHT|'):
   _,n,v=line.split('|');i=int(n);actual=list(map(int,v.split(',')));expected=load(rows[i]);results.append(dict(case=rows[i],actual=actual,expected=expected,pass_case=actual==expected))
 ok=len(results)==len(rows)and all(r['pass_case']for r in results);report=dict(schema='BYOR_4086_PLAYER_SPAWN_HEIGHT_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,authority_sha256=hashlib.sha256((default+body).encode()).hexdigest(),cases=len(rows),results=results,source_loader_verbatim=True,native_world_installation_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results),'height cases')
 if not ok:raise SystemExit(1)

if __name__=='__main__':main()
