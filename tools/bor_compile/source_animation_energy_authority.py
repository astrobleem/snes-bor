"""Literal loader energy triples and real check_energy C authority."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_animation_energy_4086 import load,check,FIELDS
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def git(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd='E:/gh/openbor-bcec').decode('latin1')
 raw=git('engine/openbor.c');header=git('engine/openbor.h');func=extract(raw,'check_energy');translator=extract(raw,'translate_ani_id')
 assert '#define validanim(e, a) ((e)->modeldata.animation[a]&&(e)->modeldata.animation[a]->numframes)' in header
 enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+n+r'\s*;',header,re.S)[0]for n in ('e_cost_check','e_cost_type','e_entity_type'))
 default='\n'.join(l for l in raw.splitlines()if 'newanim->energycost.'in l and ('COST_TYPE_MP_THEN_HP' in l or re.search(r'disable\s*=\s*0',l)))
 special=translator[translator.index('else if(stricmp(value, "special")'):translator.index('else if(stricmp(value, "special2")')]
 assert translator.count('newanim->energycost.')==special.count('newanim->energycost.')==1
 blocks=[]
 for name in ('ENERGYCOST','MPONLY'):
  m=re.search(r'            case CMD_MODEL_'+name+r':.*?                break;',raw,re.S);assert m;blocks.append(m[0])
 source=Source(a.source);docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};discovery=discover(source,docs)
 rows=[dict(identity=m['declaration'],rows=docs[key(m['source_path'])]['directives'])for m in discovery['models']]
 def row(n,*v):return dict(directive=n,values=list(map(str,v)))
 for role in ('idle','special','special1','special2','freespecial'):
  for values in ((),('7',),('0','0','0'),('12tail','-9other','-2'),('-2147483648','2147483647','-1')):
   rows.append(dict(identity='defaults-and-atoi',rows=[row('anim',role),row('energycost',*values),row('mponly','2'),row('anim',role)]))
 rows.append(dict(identity='role-defaults',rows=[row('anim',n)for n in ('idle','special','special1','special2','freespecial')]))
 code='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define FALSE 0
#define TRUE 1
'''+enums+'''
typedef struct {struct {int cost,mponly,disable;}energycost;int numframes;} animation;
typedef struct {struct {int type;animation*animation[1];}modeldata;int seal,mp,health;} entity;
entity ent,*self=&ent;
#define validanim(e, a) ((e)->modeldata.animation[a]&&(e)->modeldata.animation[a]->numframes)
#define GET_ARG(i) args[i]
#define GET_INT_ARG(i) atoi(GET_ARG(i))
enum {ANI_SPECIAL,CMD_MODEL_ENERGYCOST,CMD_MODEL_MPCOST,CMD_MODEL_MPONLY};
void begin(char*value,animation*newanim){int ani_id=0;
'''+default+'\nif(0){}\n'+special+'}\nvoid command(int cmd,char**args,animation*newanim){switch(cmd){'+'\n'.join(blocks)+'}}\n'+func+'\nint main(void){animation anim,*newanim=&anim;char*args[32];\n'
 expected_loader=[]
 for case in rows:
  expected_loader.extend([v['fields'][f]for f in FIELDS]for v in load(case['rows']));active=False
  for r in case['rows']:
   n,v=r['directive'],r['values']
   if n=='anim':
    if active:code+='printf("L,%d,%d,%d\\n",newanim->energycost.cost,newanim->energycost.mponly,newanim->energycost.disable);\n'
    code+='memset(newanim,0,sizeof(anim));begin('+json.dumps(' '.join(v))+',newanim);\n';active=True
   elif n in ('energycost','mpcost','mponly'):
    code+=''.join('args['+str(i)+']='+json.dumps(v[i-1]if i and i<=len(v)else'')+';'for i in range(32))+'\ncommand(CMD_MODEL_'+('MPONLY'if n=='mponly'else'ENERGYCOST')+',args,newanim);\n'
  if active:code+='printf("L,%d,%d,%d\\n",newanim->energycost.cost,newanim->energycost.mponly,newanim->energycost.disable);\n'
 checks=[]
 for t in (0,1,2,512,3,513,514,65536):
  for disable in (0,1,2,512,-1,-2,-3,-4,65536):
   for cost in (-1,0,1,6,65536):
    for only in (-1,0,1,2,65536):
     for seal in (0,cost-1,cost,cost+1):
      for which in (0,1,65536):checks.append(dict(which=which,type=t,seal=seal,mp=cost+((len(checks)//3)%3)-1,health=cost+len(checks)%3-1,fields=dict(cost=cost,mponly=only,disable=disable)))
 code+='return 0;}\n';(a.output/'energy_loader.c').write_text(code)
 # Keep the real predicate in a separate compact data-driven program.
 pre=code[:code.index('int main(void)')]
 ccode=pre+'typedef struct {int which,type,seal,mp,health,cost,only,disable;} input;input cases[]={\n'
 for c in checks:ccode+='{'+','.join(str(c[k])for k in ('which','type','seal','mp','health'))+','+','.join(str(c['fields'][k])for k in FIELDS)+'},\n'
 ccode+='''};int main(void){unsigned i;input*c;animation anim;self->modeldata.animation[0]=&anim;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=&cases[i];self->modeldata.type=c->type;self->seal=c->seal;self->mp=c->mp;self->health=c->health;anim.energycost.cost=c->cost;anim.energycost.mponly=c->only;anim.energycost.disable=c->disable;printf("%d\\n",check_energy(c->which,0));}return 0;}
''';ccode=ccode.replace('self->modeldata.animation[0]=&anim;', 'anim.numframes=1;self->modeldata.animation[0]=&anim;');(a.output/'check_energy.c').write_text(ccode)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');actuals=[]
 for name in ('energy_loader','check_energy'):
  b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt',name+'.c','-fe='+name+'.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/(name+'-build.log')).write_text(b.stdout+b.stderr);assert b.returncode==0
  log=subprocess.check_output([str(a.output/(name+'.exe'))],cwd=a.output,text=True);(a.output/(name+'-authority.log')).write_text(log);actuals.append(log)
 actual_loader=[list(map(int,l.split(',')[1:]))for l in actuals[0].splitlines()];actual=[int(l)for l in actuals[1].splitlines()];expected=[int(check(c['which'],c['fields'],c['type'],c['seal'],c['mp'],c['health']))for c in checks];ok=actual_loader==expected_loader and actual==expected
 r=dict(schema='BYOR_4086_ANIMATION_ENERGY_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,source_sha256=hashlib.sha256((default+special+'\n'.join(blocks)+func).encode()).hexdigest(),enum_storage_bits=32,enum_compiler_option='-ei',validanim_macro_unmodified=True,fixture_animation_numframes=1,loader_cases=len(actual_loader),predicate_cases=len(checks),inputs=checks,actual=actual,expected=expected,loader_inputs=rows,loader_actual=actual_loader,loader_expected=expected_loader,energy_body_instrumented=False,runtime_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(actual_loader),'loader rows;',len(checks),'literal energy checks');assert ok

if __name__=='__main__':main()
