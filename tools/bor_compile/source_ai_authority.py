"""Differential complete check_ai sequencing with controlled external bodies."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_ai_4086 import check_ai,Service

def cases():
    base=dict(time=48,nextthink=48,endgame=0,takeaction=1,think=2,noaicontrol=0,update_mark=0x12340001,animation=3,spawn=3,respawn=4,animating=1,exists=1,mutation=0)
    rows=[dict(base,nextthink=n,endgame=g,takeaction=a,think=t,noaicontrol=c,animation=anim,animating=ing)for n,g,a,t,c,anim,ing in itertools.product((47,48,49,0x80000000,0xffffffff),(0,1,-1),(0,1),(0,2),(0,1,-1,65536),(0,3,4,5),(0,1,-1))]
    rows.extend(dict(base,time=time,nextthink=n,mutation=m)for time,n,m in itertools.product((0,48,0xfffffffe,0xffffffff),(0,48,0xfffffffe,0xffffffff),range(1,9)))
    # NULL animation and absent SPAWN pointer compare equal in literal source.
    rows.extend(dict(base,animation=0,spawn=spawn,respawn=respawn,animating=0)for spawn,respawn in itertools.product((0,3),(0,4)))
    return rows

def mutate(e,c):
    m=c['mutation']
    if m==1:e['nextthink']=(c['time']+20)&0xffffffff
    elif m==2:e['think']=0
    elif m==3:e['noaicontrol']=-1
    elif m==4:e['exists']=0
    elif m==5:e['animation']=e['spawn'];e['animating']=0
    elif m==6:e['animation']=5;e['animating']=0
    elif m==7:e['takeaction']=0;e['nextthink']=0
    elif m==8:e['think']=2;e['noaicontrol']=0

def reference(c):
    e=dict(c);trace=[]
    for service,value in check_ai(e,c):
        trace.append(int(service))
        if service==Service.ACTION:mutate(e,c)
        elif service==Service.SET_IDLE:e['animation']=5;e['animating']=1
    return [len(trace),*trace,*([0]*(4-len(trace))),e['update_mark'],e['nextthink'],e['think'],e['noaicontrol']&0xffffffff,e['exists'],e['animation'],e['animating']&0xffffffff]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');f=extract(text,'check_ai')
    fields=['time','nextthink','endgame','takeaction','think','noaicontrol','update_mark','animation','spawn','respawn','animating','exists','mutation'];rows=cases()
    code='''#include <stdio.h>
#include <string.h>
#define THINK_SPEED 2
#define ANI_SPAWN 0
#define ANI_RESPAWN 1
typedef struct {void *animation[2];} model;
typedef struct {unsigned nextthink,update_mark;int noaicontrol,animating,exists;void *animation;model modeldata;void (*takeaction)(void),(*think)(void);} entity;
entity ent,*self=&ent;unsigned time;int endgame,mutation,events[4],count;
void action(void){events[count++]=1;switch(mutation){
case 1:self->nextthink=time+20;break;case 2:self->think=0;break;case 3:self->noaicontrol=-1;break;case 4:self->exists=0;break;case 5:self->animation=self->modeldata.animation[0];self->animating=0;break;case 6:self->animation=(void*)5;self->animating=0;break;case 7:self->takeaction=0;self->nextthink=0;break;case 8:self->noaicontrol=0;break;}}
void think(void){events[count++]=2;}
void execute_think_script(entity *e){events[count++]=3;}
void set_idle(entity *e){events[count++]=4;e->animation=(void*)5;e->animating=1;}
'''+f+'\nunsigned cases[][13]={'+','.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in fields)+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){unsigned *r=cases[i];memset(&ent,0,sizeof(ent));memset(events,0,sizeof(events));count=0;
time=r[0];ent.nextthink=r[1];endgame=r[2];ent.takeaction=r[3]?action:0;ent.think=r[4]?think:0;ent.noaicontrol=r[5];ent.update_mark=r[6];ent.animation=(void*)r[7];ent.modeldata.animation[0]=(void*)r[8];ent.modeldata.animation[1]=(void*)r[9];ent.animating=r[10];ent.exists=r[11];mutation=r[12];check_ai();
printf("%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\\n",count,events[0],events[1],events[2],events[3],ent.update_mark,ent.nextthink,ent.think?2:0,(unsigned)ent.noaicontrol,ent.exists,(unsigned)ent.animation,(unsigned)ent.animating);
}return 0;}
'''
    (a.output/'ai.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','ai.c','-fe=ai.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise ValueError('SOURCE_AI_AUTHORITY_BUILD')
    log=subprocess.check_output([str(a.output/'ai.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];wanted=[reference(c)for c in rows];failures=[i for i,(v,e)in enumerate(zip(actual,wanted))if v!=e];ok=len(actual)==len(rows)and not failures
    d=dict(schema='BYOR_4086_AI_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=wanted,failures=failures[:20],callback_bodies_instrumented=True,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(rows),'AI sequencing cases');assert ok
if __name__=='__main__':main()
