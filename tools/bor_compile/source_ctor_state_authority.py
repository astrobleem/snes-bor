"""Pinned constructor-state loader and default palette identity authority."""
import argparse,hashlib,json,os,re,subprocess
from decimal import Decimal
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_ctor_state import derive

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);r=derive(Source(a.source));raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
 names=['LIFESPAN','SUMMONKILL','ALPHA'];cases=[]
 for n in names:
  start=raw.index('case CMD_MODEL_'+n+':');end=raw.index('\n            case ',start+1);cases.append(raw[start:end])
 defaults=[]
 for name in('lifespan','summonkill'):
  defaults.append(re.search(r'^    newchar->'+name+r'\s*= [^;]+;',raw,re.M)[0])
 colour=extract(raw,'ent_set_colourmap');default='\n'.join(defaults);authority=default+'\n'+'\n'.join(cases)+'\n'+colour
 inputs=['0','1.5','2','3','1.005','-1.005','0.005','-0.005','0.045','-0.045']+[format(Decimal(i)/200,'f')for i in range(-400,401)]
 data=','.join('"'+x+'"'for x in inputs)
 code=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GAME_SPEED 200
#define CMD_MODEL_LIFESPAN 0
#define CMD_MODEL_SUMMONKILL 1
#define CMD_MODEL_ALPHA 2
#define GET_FLOAT_ARG(n) ((float)atof(value))
#define GET_INT_ARG(n) atoi(value)
typedef struct {int lifespan,summonkill,alpha,maps_loaded;void *palette,*colourmap[2];} Model;
typedef struct {Model modeldata;void *colourmap;unsigned map;} entity;
'''+colour+'\nchar *inputs[]={'+data+'};\n'+r'''
int main(void){Model model,*newchar=&model;entity e;char *value;unsigned n,which;int op;
if(sizeof(void*)!=4||sizeof(int)!=4)return 2;
for(n=0;n<sizeof(inputs)/sizeof(inputs[0]);n++){memset(&model,0,sizeof(model));
'''+default+r'''
value=inputs[n];op=0;switch(op){'''+ '\n'.join(cases)+r''' }
printf("TICKS|%u|%d\n",n,model.lifespan);}
memset(&e,0,sizeof(e));e.modeldata.maps_loaded=2;e.modeldata.palette=(void*)0x12345678;e.modeldata.colourmap[0]=(void*)0x23456789;e.modeldata.colourmap[1]=(void*)0x3456789a;
for(n=0;n<5;n++){which=n==4?0xffffffff:n;ent_set_colourmap(&e,which);printf("MAP|%u|%u|%08x\n",which,e.map,(unsigned)e.colourmap);}return 0;}
'''
 (a.output/'state.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','state.c','-fe=state.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('CTOR_STATE_C_AUTHORITY_BUILD')
 log=subprocess.check_output([str(a.output/'state.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);results=[];maps=[]
 for line in log.splitlines():
  if line.startswith('TICKS|'):
   _,n,t=line.split('|');n=int(n);wanted=int(float(inputs[n])*200);results.append(dict(input=inputs[n],actual=int(t),expected=wanted,pass_case=int(t)==wanted))
  elif line.startswith('MAP|'):
   _,which,m,v=line.split('|');which=int(which);want=which if which<=2 else 0;palette=[0x12345678,0x23456789,0x3456789a][want];maps.append(dict(input=which,map=int(m),palette=int(v,16),pass_case=int(m)==want and int(v,16)==palette))
 ok=len(results)==len(inputs)and len(maps)==5 and all(x['pass_case']for x in results+maps)
 d=dict(schema='BYOR_4086_CONSTRUCTOR_STATE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,authority_sha256=hashlib.sha256(authority.encode()).hexdigest(),authority_text=authority,tick_cases=len(results),ticks=results,palette_cases=maps,model_state=r,name_cache_lookup_bound=False,native_body_reset_bound=False,palette_rendering_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(results),'lifespan assignments,',len(maps),'palette identities')
 if not ok:raise SystemExit(1)
if __name__=='__main__':main()
