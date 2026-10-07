"""Literal pinned loader authority for model attack/stealth policy fields."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_attack_policy import FIELDS,load
from source_model_switch_4086 import CACHED_FIELDS
from source_model_core_4086 import FLOAT_FIELDS,TYPE_NAMES
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def git(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd='E:/gh/openbor-bcec').decode('latin1')
 raw=git('engine/openbor.c');header=git('engine/openbor.h');typefunc=extract(raw,'lcmHandleCommandType')
 enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+n+r'\s*;',header,re.S)[0]for n in ('e_entity_type','e_entity_type_sub','e_aimove_1','e_aimove_2','e_aiattack_1'))
 init=raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')]
 assert re.search(r'newchar\s*=\s*calloc\(1,\s*sizeof\(\*newchar\)\)',init)
 defaults='\n'.join(l for l in init.splitlines()if re.match(r'\s*newchar->(?:stealth\.hide|stealth\.detect|nopassiveblock|blockodds)\s*=',l))
 blocks=[]
 for n in ('NOPASSIVEBLOCK','BLOCKODDS','STEALTH'):
  match=re.search(r'            case CMD_MODEL_'+n+r':.*?                break;',raw,re.S);assert match;blocks.append(match[0])
 source=Source(a.source);docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};discovery=discover(source,docs)
 rows=[dict(identity=m['declaration'],rows=docs[key(m['source_path'])]['directives'])for m in discovery['models']]
 def row(n,*v):return dict(directive=n,values=list(map(str,v)))
 for t in TYPE_NAMES:
  for n in (0,1,-1,65536,-2147483648):
   for prefix in ([],[row('type','player')],[row('nopassiveblock',n)]):rows.append(dict(identity='synthetic-type-order',rows=prefix+[row('type',t),row('blockodds',n),row('stealth',n,-n if n!=-2147483648 else 2147483647)]))
 for values in ([],['7'],['-1','65536'],['2147483647','-2147483648'],['12tail','-9other']):rows.append(dict(identity='synthetic-stealth-atoi',rows=[row('stealth',*values)]))
 declarations=';'.join(('float 'if f in FLOAT_FIELDS else'int ')+f for f in CACHED_FIELDS if '.'not in f)+';'
 code='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GAME_SPEED 200
#define MAX_ATCHAIN 12
typedef struct {char *args[32];} ArgList;
#define GET_ARGP(i) (arglist->args[i])
#define GET_ARG(i) (arglist->args[i])
#define GET_INT_ARG(i) atoi(GET_ARG(i))
'''+enums+'\ntypedef struct {'+declarations+'''int type,subtype,nopassiveblock,blockodds,atchain[12],chainlength,bounce,offscreenkill,ground,score;
float antigravity;struct {int def,pain,get,die,usemap;} icon;struct {int fall_land,jump_land,jump_start;} dust;struct {int rise,riseattack;} risetime;struct {int hide,detect;} stealth;} s_model;
void shutdown(int n,char *s,...){exit(3);}
'''+typefunc+'\nvoid initialize(s_model *newchar){'+defaults+'\n}\nenum {CMD_MODEL_NOPASSIVEBLOCK=1,CMD_MODEL_BLOCKODDS=2,CMD_MODEL_STEALTH=3};\nvoid command(ArgList *arglist,s_model *newchar,int cmd){switch(cmd){'+'\n'.join(blocks)+'\n}}\nint main(void){s_model model,*newchar=&model;ArgList args,*arglist=&args;\nif(sizeof(int)!=4)return 2;\n'
 expected=[]
 for i,c in enumerate(rows):
  expected.append([load(c['rows'])[f]for f in FIELDS]);code+='memset(newchar,0,sizeof(model));initialize(newchar);\n'
  for r in c['rows']:
   n,v=r['directive'],r['values']
   if n not in ('type','nopassiveblock','blockodds','stealth'):continue
   for j in range(32):code+='args.args['+str(j)+']='+json.dumps(v[j-1]if j and j<=len(v)else'')+';'
   code+='\n'+('lcmHandleCommandType(arglist,newchar,"fixture");'if n=='type'else'command(arglist,newchar,CMD_MODEL_'+n.upper()+');')+'\n'
  code+='printf("%d,%d,%d,%d\\n",'+','.join('newchar->'+f for f in FIELDS)+');\n'
 code+='return 0;}\n';(a.output/'model_attack_policy.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','model_attack_policy.c','-fe=model_attack_policy.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'model_attack_policy.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];ok=actual==expected
 report=dict(schema='BYOR_4086_MODEL_ATTACK_POLICY_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,authority_sha256=hashlib.sha256((enums+typefunc+defaults+'\n'.join(blocks)).encode()).hexdigest(),zero_allocation_verified=True,cases=len(rows),inputs=rows,actual=actual,expected=expected,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'model attack policy source cases');assert ok
if __name__=='__main__':main()
