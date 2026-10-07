"""Literal source argument parser and attack timing loader differential proof."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document
from source_attack_timing_4086 import derive,load,bits
from script_nested_authority import extract
from dialect_4086 import ENGINE_COMMIT

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def git(name):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+name],cwd='E:/gh/openbor-bcec').decode('latin1')
 raw=git('engine/openbor.c');header=git('engine/openbor.h');parser=extract(raw,'ParseArgs');profile=derive(Source(a.source));cases=[]
 for m in profile['models']:cases.append(dict(identity=m['identity'],rows=document(Source(a.source),m['source_path'])['directives']))
 def row(n,*v):return dict(directive=n,values=list(map(str,v)))
 for value in (-2147483648,-1,0,1,149,150,2147483647):cases.append(dict(identity='synthetic-aggression',rows=[row('aggression',value)]))
 for value in ('-1','0','.05','.5','.95','1','2'):
  for values in ((value,),(value,'0'),(value,'.75')):cases.append(dict(identity='synthetic-throttle',rows=[row('attackthrottle',*values)]))
 cases.append(dict(identity='synthetic-zero-values',rows=[row('attackthrottle')]))
 cases.append(dict(identity='synthetic-overwrite',rows=[row('attackthrottle','.5','1'),row('attackthrottle','.25'),row('aggression',10),row('aggression',-20)]))
 blocks=[]
 for tag in ('AGGRESSION','ATTACKTHROTTLE'):
  start=raw.index('            case CMD_MODEL_'+tag+':');end=raw.index('                break;',start)+len('                break;');blocks.append(raw[start:end])
 init='\n'.join(line for line in raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')].splitlines()if re.match(r'\s*newchar->attackthrottle(?:time)?\s*=',line))
 globals='\n'.join(re.search(r'^float '+name+r'\s*=.*?;',raw,re.M)[0]for name in ('min_noatk_chance','offscreen_noatk_factor','noatk_duration'))
 macros='\n'.join(re.search(r'^#define\s+'+name+r'\b[^\n]*',header,re.M)[0]for name in ('MAX_ARG_LEN','MAX_ARG_COUNT'))
 code='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define GAME_SPEED 200
'''+macros+'''
typedef struct {char *args[MAX_ARG_COUNT];size_t arglen[MAX_ARG_COUNT],count;} ArgList;
#define GET_ARG(z) (arglist.count > z ? arglist.args[z] : "")
#define GET_INT_ARG(z) atoi(GET_ARG(z))
#define GET_FLOAT_ARG(z) ((float)atof(GET_ARG(z)))
typedef struct {int aggression;float attackthrottle,attackthrottletime;} Model;
'''+globals+'\n'+parser+'\nvoid init(Model *newchar){memset(newchar,0,sizeof(*newchar));\n'+init+'\n}\n'+'''
enum {CMD_MODEL_AGGRESSION=1,CMD_MODEL_ATTACKTHROTTLE=2};
void command(Model *newchar,int cmd,char *text){ArgList arglist;char output[MAX_ARG_LEN];ParseArgs(&arglist,text,output);switch(cmd){
'''+ '\n'.join(blocks)+'''}}
unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}
int main(void){Model model;unsigned i=0;
'''
 expected=[]
 for c in cases:
  d=load(c['rows']);expected.append([d['aggression'],bits(d['attackthrottle']),bits(d['attackthrottletime'])]);code+='init(&model);\n'
  for r in c['rows']:
   if r['directive']not in ('aggression','attackthrottle'):continue
   text=' '.join([r['directive'],*r['values']]);cmd=1 if r['directive']=='aggression'else 2
   code+='command(&model,'+str(cmd)+','+json.dumps(text)+');\n'
  code+='printf("%d,%u,%u\\n",model.aggression,bits(model.attackthrottle),bits(model.attackthrottletime));\n'
 code+='return 0;}\n';(a.output/'timing.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-ei','-bt=nt','timing.c','-fe=timing.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'timing.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];ok=actual==expected
 report=dict(schema='BYOR_4086_ATTACK_TIMING_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(cases),inputs=cases,actual=actual,expected=expected,parser_sha256=hashlib.sha256(parser.encode()).hexdigest(),literal_loader_sha256=hashlib.sha256((init+'\n'+'\n'.join(blocks)).encode()).hexdigest(),literal_parser_and_loader_unmodified=True,binary32_identity_preserved=True,runtime_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(cases),'literal parser/attack timing rows');assert ok

if __name__=='__main__':main()
