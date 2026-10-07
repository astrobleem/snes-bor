"""Pinned update_animation prefix with timed advance not due."""
import argparse,hashlib,itertools,json,os,random,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(raw,'update_animation');rows=[]
 for time in (0,50,65536,0x80000000,0xffffffff):
  for idling,animnum,animating in itertools.product((0,1,2,3,65536,0xffffffff),(0,80,65536),(-1,0,1)):
   rows.append(dict(time=time,idling=idling,animnum=animnum,animating=animating,invincible=0,invinctime=time,sealtime=0,level=time%2))
  for invincible,delta,seal_delta in itertools.product((0,1,65536,0xffffffff),(-1,0,1),(-1,0,1)):
   rows.append(dict(time=time,idling=2,animnum=80,animating=0,invincible=invincible,invinctime=(time+delta)&0xffffffff,sealtime=(time+seal_delta)&0xffffffff,level=1))
 rng=random.Random(4086)
 for _ in range(128):rows.append(dict(time=rng.randrange(1<<32),idling=rng.randrange(1<<32),animnum=rng.choice((0,80,65536)),animating=rng.choice((-1,0,1)),invincible=rng.randrange(1<<32),invinctime=rng.randrange(1<<32),sealtime=rng.randrange(1<<32),level=rng.randrange(2)))
 code=r'''#include <stdio.h>
#include <string.h>
#define FACING_ADJUST_RIGHT 1
#define FACING_ADJUST_LEFT 2
#define FACING_ADJUST_LEVEL 3
#define DIRECTION_RIGHT 1
#define DIRECTION_LEFT 0
#define TYPE_PANEL 1024
#define TYPE_TEXTBOX 128
#define ANI_SLEEP 80
#define SUBTYPE_NOSKIP 6
#define SCROLL_RIGHT 1
#define SCROLL_LEFT 2
#define SCROLL_UP 4
#define FLAG_JUMP 1
#define FLAG_ATTACK 2
#define FLAG_ATTACK2 4
#define FLAG_ATTACK3 8
#define FLAG_ATTACK4 16
#define FLAG_SPECIAL 32
 typedef struct {int numframes;struct {int mode;struct {int min,max;}frame;}loop;}animation;
 typedef struct {struct {int facing,type,sleepwait,escapehits,subtype;float scroll,speed;}modeldata;struct {float x,y;}position;float base;unsigned idling,sleeptime,invincible,blink,invinctime,arrowon,freezetime,maptime,sealtime,seal,inpain,escapecount,nextanim,update_mark;int direction,animnum,animating,autokill,map,animpos;animation*animation;}entity;
 typedef struct {int facing,scrolldir;}stage;
 entity actor,*self=&actor;stage scene,*level;animation anim;unsigned time,bothnewkeys;float scrolldx,scrolldy;int thaws,maps,updates,kills;
 void unfrozen(entity*e){thaws++;}void ent_set_colourmap(entity*e,int m){maps++;}void update_frame(entity*e,int f){updates++;}void kill(entity*e){kills++;}
 '''+function+'\nint main(void){\n'
 for c in rows:
  code+='memset(self,0,sizeof(*self));self->animation=&anim;self->modeldata.sleepwait=1000;self->sleeptime=123;self->blink=55;self->arrowon=66;self->seal=77;self->escapecount=88;self->direction=1;thaws=maps=updates=kills=0;'
  for n in ('idling','animnum','animating','invincible','invinctime','sealtime'):code+='self->'+n+'='+str(c[n])+('u'if c[n]>=0 else'')+';'
  code+='time='+str(c['time'])+'u;self->nextanim=time^1;level='+('&scene'if c['level']else'NULL')+';update_animation();'
  code+='printf("%u,%u,%u,%u,%u,%u,%u,%d,%d,%d,%d,%d,%d\\n",self->sleeptime,self->invincible,self->blink,self->invinctime,self->arrowon,self->seal,self->sealtime,thaws,maps,updates,kills,self->animating,self->direction);\n'
 code+='return 0;}\n';(a.output/'prefix.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','prefix.c','-fe=prefix.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str((a.output/'prefix.exe').resolve())],text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  sleep=not(c['idling']&2)or c['animnum']==80 and c['animating']==0;inv=bool(c['invincible'])and c['time']>=c['invinctime'];seal=bool(c['sealtime'])and c['time']>=c['sealtime']
  expected.append([(c['time']+1000)&0xffffffff if sleep else 123,0 if inv else c['invincible'],0 if inv else 55,0 if inv else c['invinctime'],0 if inv else 66,0 if seal else 77,c['sealtime'],0,0,0,0,c['animating'],1])
 assert actual==expected
 r=dict(schema='BYOR_4086_UPDATE_ANIMATION_PREFIX_AUTHORITY_V1',status='PASS',engine_commit=ENGINE_COMMIT,source_function_sha256=hashlib.sha256(function.encode()).hexdigest(),source_function_unmodified=True,cases=len(rows),inputs=rows,actual=actual,expected=expected,domain='facing/scroll/escapehits=0; sleepwait=1000; freezetime/maptime=0; timed frame not due',instrumented_services=['unfrozen','ent_set_colourmap','update_frame','kill'],native_bound=False,motu_gameplay_proven=False);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(rows),'literal update_animation prefix cases')
if __name__=='__main__':main()
