"""Pinned common_block body, exact child ordering and closed model policy."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_core_4086 import integer
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_ids import configure
from source_player_run_4086 import KEYS

def derive(source,raw):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};st=discover(source,docs)
 if 's_model *newchar = calloc(1, sizeof(*newchar));'not in raw:raise ValueError('COMMON_BLOCK_DEFAULT_CALLOC_AUTHORITY')
 at=re.search(r'case CMD_MODEL_HOLDBLOCK\s*:',raw).start();loader=raw[at:raw.index('break;',at)+6];models=[]
 outside=raw[:at]+raw[at+len(loader):]
 if re.search(r'newchar->holdblock\s*=',outside):raise ValueError('COMMON_BLOCK_DEFAULT_OVERRIDE_REQUIRED')
 for i,m in enumerate(st['models']):
  d=docs[key(m['source_path'])];decl=[r for r in d['directives']if r['directive']=='holdblock'];value=0
  if any(r['directive']=='subclass'for r in d['directives']):raise ValueError('COMMON_BLOCK_SUBCLASS_REQUIRED')
  for r in decl:value=integer(r['values'])
  models.append(dict(id=i,identity=m['declaration'],holdblock=value,declarations=decl,source_sha256=d['sha256'],closed_zero_admitted=value==0))
 return dict(models=models,loader_sha256=hashlib.sha256(loader.encode('latin1')).hexdigest(),zero_default_authority='calloc; no holdblock initialization override',model_policy_mutations_admitted=False,closed_zero_policy=all(m['holdblock']==0 and not m['declarations']for m in models))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(raw,'common_block');req=derive(Source(a.source),raw);special=KEYS['special'];block=configure([])['authority']['enum']['ANI_BLOCK']
 rows=[dict(zip(('holdblock','type','inpain','keys','animating','valid'),v))for v in itertools.product((0,1,2,3,-1),(0,1,2,65536),(0,1,-1),(0,special),(0,1,-1),(0,1))]
 code='''#include <stdio.h>
#include <string.h>
#define TYPE_PLAYER 1
'''+f'#define FLAG_SPECIAL {special}\n#define ANI_BLOCK {block}\n'+'''
typedef struct entity{struct{int holdblock,type;}modeldata;int inpain,animating,blocking,playerindex;void(*takeaction)(void);}entity;
typedef struct {int keys;}playerstate;
entity e,*self=&e;playerstate players[4],*player=players;int present,n,events[16];
int validanim(entity*e,int role){if(role!=ANI_BLOCK)return 0;events[n++]=3;return present;}
void set_idle(entity*e){events[n++]=2;}
void ent_set_anim(entity*e,int role,int reset){if(role!=ANI_BLOCK)return;events[n++]=1;events[n++]=reset;}
'''+body+'\nint main(void){int h,t,p,k,a,v,i;while(scanf("%d %d %d %d %d %d",&h,&t,&p,&k,&a,&v)==6){memset(&e,0,sizeof(e));e.modeldata.holdblock=h;e.modeldata.type=t;e.inpain=p;e.animating=a;e.blocking=-7;e.takeaction=common_block;players[0].keys=k;present=v;n=0;common_block();printf("%d %d %d|",e.inpain,e.blocking,e.takeaction==common_block);for(i=0;i<n;i++)printf("%s%d",i?" ":"",events[i]);puts("");}return 0;}\n'
 (a.output/'common_block.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','common_block.c','-fe=common_block.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'common_block.exe')],input='\n'.join(' '.join(str(c[k])for k in ('holdblock','type','inpain','keys','animating','valid'))for c in rows)+'\n',text=True);(a.output/'authority.log').write_text(log);actual=[];expected=[]
 for c,line in zip(rows,log.splitlines()):
  state,events=line.split('|');actual.append([list(map(int,state.split())),list(map(int,events.split()))]);h=c['holdblock'];pain=c['inpain'];hb1=bool(h and c['type']&1 and(not pain or h&2));hb2=bool(c['keys']&special);ev=[];blocking=-7;action=1
  if pain and h&2 and not c['animating']:
   ev.append(3)
   if c['valid']:pain=0;ev.extend((1,0))
   elif (hb1 and not hb2)or(not c['animating']and(not hb1 or not hb2)):blocking=0;action=0;ev.append(2)
  elif (hb1 and not hb2)or(not c['animating']and(not hb1 or not hb2)):blocking=0;action=0;ev.append(2)
  expected.append([[pain,blocking,action],ev])
 ok=len(actual)==len(rows)and actual==expected;r=dict(schema='BYOR_COMMON_BLOCK_SOURCE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,requirements=req,child_services_instrumented=True,native_common_block_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'common_block source cases; closed zero holdblock:',req['closed_zero_policy']);assert ok

if __name__=='__main__':main()
