"""Literal ParseArgs, default chain loop and NOMOVE/ATCHAIN loader proof."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source
from source_profile import document
from source_attack_body_profile import derive,load,pack
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def git(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd='E:/gh/openbor-bcec').decode('latin1')
 raw=git('engine/openbor.c');header=git('engine/openbor.h');parser=extract(raw,'ParseArgs');source=Source(a.source);profile=derive(source);cases=[dict(identity=m['identity'],rows=document(source,m['source_path'])['directives'])for m in profile['models']]
 def row(n,*v):return dict(directive=n,values=list(map(str,v)))
 for noflip in (-2147483648,-1,0,1,65536,2147483647):cases.append(dict(identity='synthetic-nomove',rows=[row('nomove',0,noflip)]))
 for values in ((),(1,),(1,2,1,2,1,3),(-1,99),(0,0,0,0,0,0,0,0,0,0,0,4),tuple(range(15))):cases.append(dict(identity='synthetic-chain',rows=[row('atchain',*values)]))
 cases.append(dict(identity='synthetic-overwrite',rows=[row('nomove',1,-1),row('nomove',0),row('atchain',1,2),row('atchain',0,0,3)]))
 for style in (-2147483648,-1,0,1,2,3,65536,2147483647):cases.append(dict(identity='synthetic-style',rows=[row('combostyle',style)]))
 cases.append(dict(identity='synthetic-style-overwrite',rows=[row('combostyle',3),row('combostyle')]))
 blocks=[]
 for tag in ('NOMOVE','ATCHAIN','COMBOSTYLE'):
  start=raw.index('            case CMD_MODEL_'+tag+':');end=raw.index('                break;',start)+len('                break;');blocks.append(raw[start:end])
 start=raw.index('    // Default Attack1 in chain must be referenced if not used.');end=raw.index('    if(magic_type',start);init=raw[start:end]
 macros='\n'.join(re.search(r'^#define\s+'+n+r'\b[^\n]*',header,re.M)[0]for n in ('MAX_ARG_LEN','MAX_ARG_COUNT','MAX_ATCHAIN'))
 code='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
'''+macros+'''
typedef struct {char *args[MAX_ARG_COUNT];size_t arglen[MAX_ARG_COUNT],count;} ArgList;
#define GET_ARG(z) (arglist.count > z ? arglist.args[z] : "")
#define GET_INT_ARG(z) atoi(GET_ARG(z))
typedef struct {int nomove,noflip,nodrop,chainlength,atchain[MAX_ATCHAIN],combostyle;} Model;
int max_attacks='''+str(profile['maximum_attacks'])+';\n'+parser+'\nvoid init(Model *newchar){int i;memset(newchar,0,sizeof(*newchar));\n'+init+'''}
enum {CMD_MODEL_NOMOVE=1,CMD_MODEL_ATCHAIN=2,CMD_MODEL_COMBOSTYLE=3};
void command(Model *newchar,int cmd,char *text){int i;ArgList arglist;char output[MAX_ARG_LEN];ParseArgs(&arglist,text,output);switch(cmd){
'''+ '\n'.join(blocks)+'''}}
int main(void){Model model;int j;
''';expected=[]
 for c in cases:
  d=load(c['rows'],profile['maximum_attacks'],profile['chain_capacity']);expected.append([d['noflip'],d['chainlength'],*d['atchain'],d['combostyle']]);code+='init(&model);\n'
  for r in c['rows']:
   if r['directive']not in ('nomove','atchain','combostyle'):continue
   code+='command(&model,'+str(dict(nomove=1,atchain=2,combostyle=3)[r['directive']])+','+json.dumps(' '.join([r['directive'],*r['values']]))+');\n'
  code+='printf("%d,%d",model.noflip,model.chainlength);for(j=0;j<MAX_ATCHAIN;j++)printf(",%d",model.atchain[j]);printf(",%d\\n",model.combostyle);\n'
 code+='return 0;}\n';(a.output/'body_profile.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-ei','-bt=nt','body_profile.c','-fe=body_profile.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'body_profile.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];ok=actual==expected;data=pack(profile)
 report=dict(schema='BYOR_4086_ATTACK_BODY_PROFILE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(cases),inputs=cases,actual=actual,expected=expected,literal_parser_and_loader_unmodified=True,parser_sha256=hashlib.sha256(parser.encode()).hexdigest(),literal_loader_sha256=hashlib.sha256((init+'\n'+'\n'.join(blocks)).encode()).hexdigest(),table_sha256=hashlib.sha256(data).hexdigest(),native_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(cases),'literal turn/chain loader cases');assert ok

if __name__=='__main__':main()
