"""Verbatim pinned scalar loader cases and defaults for lifecycle inputs."""
import argparse,hashlib,json,os,re,subprocess,struct
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from source_lifecycle_inputs import load

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');names=['NOMOVE','MAKEINV','PRIORITY','KNOCKDOWNCOUNT'];bodies=[]
    for n in names:
        m=re.search(r'case CMD_MODEL_'+n+r'\s*:',raw);end=raw.index('\n            case ',m.end());bodies.append(raw[m.start():end])
    default=re.search(r'^    newchar->priority = 1;',raw,re.M)[0];authority=default+'\n'+'\n'.join(bodies)
    rows=[]
    for n in names:
        for v in (['0','1','-3'] if n in ('NOMOVE','PRIORITY') else ['0','4','0.009','-0.009','-2.5','1.999']):
            for flag in (0,1):rows.append(dict(directive=n.lower(),values=[v,str(flag)] if n in ('NOMOVE','MAKEINV') else [v],line=1))
    cases=',\n'.join('{'+str(names.index(r['directive'].upper()))+',"'+r['values'][0]+'","'+(r['values'][1] if len(r['values'])>1 else '0')+'"}' for r in rows)
    source=r'''#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define GAME_SPEED 200
#define CMD_MODEL_NOMOVE 0
#define CMD_MODEL_MAKEINV 1
#define CMD_MODEL_PRIORITY 2
#define CMD_MODEL_KNOCKDOWNCOUNT 3
#define GET_ARG(n) args[n-1]
#define GET_INT_ARG(n) atoi(args[n-1])
#define GET_FLOAT_ARG(n) ((float)atof(args[n-1]))
typedef struct {int nomove,noflip,nodrop,makeinv,priority;float knockdowncount;} Model;
struct {int op;char *a,*b;} cases[]={'''+cases+r'''};
int main(void){Model model,*newchar=&model;unsigned n,bits;char *args[2],*value;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
memset(&model,0,sizeof(model));'''+default+r'''
args[0]=cases[n].a;args[1]=cases[n].b;switch(cases[n].op){'''+ '\n'.join(bodies)+r'''}
memcpy(&bits,&model.knockdowncount,4);printf("LIFE|%u|%d,%d,%d,%u\n",n,model.nomove,model.makeinv,model.priority,bits);
}return 0;}
'''
    (folder/'life.c').write_text(source);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','life.c','-fe=life.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('LIFECYCLE_INPUT_C_BUILD')
    log=subprocess.check_output([str(folder/'life.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log);results=[]
    for line in log.splitlines():
        if not line.startswith('LIFE|'):continue
        _,n,state=line.split('|');i=int(n);d=load([rows[i]]);expected=[d['nomove'],d['makeinv'],d['priority'],struct.unpack('<I',struct.pack('<f',d['knockdowncount']))[0]];actual=list(map(int,state.split(',')));results.append(dict(case=rows[i],actual=actual,expected=expected,pass_case=actual==expected))
    ok=len(results)==len(rows) and all(r['pass_case'] for r in results);report=dict(schema='BYOR_4086_LIFECYCLE_INPUT_AUTHORITY_V1',status='PASS' if ok else 'FAIL',engine_commit=ENGINE_COMMIT,authority_sha256=hashlib.sha256(authority.encode()).hexdigest(),cases=len(rows),results=results,subtype_loader_bound=False,native_lifecycle_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results),'scalar loader cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
