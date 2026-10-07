"""Unmodified pinned knife_spawn, named branch; spawn/map services observed."""
import argparse,hashlib,itertools,json,os,random,re,subprocess
from pathlib import Path
from copy import deepcopy
from dialect_4086 import ENGINE_COMMIT
from source_projectile_4086 import named_knife

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1')
 match=re.search(r'^entity\s*\*\s*knife_spawn\s*\(',raw,re.M);assert match
 first=raw.index('{',match.start());last=first+1;depth=1
 while depth:
  depth+=(raw[last]=='{')-(raw[last]=='}');last+=1
 function=raw[match.start():last];rows=[]
 for parent_type,nomove,cached_speed,nohit,mode,fail in itertools.product((0,1,2,3,0x80000001),(0,1,-1),(0.0,1.5),(0,1),(0,1),(0,1)):
  rows.append(dict(parent_type=parent_type,nomove=nomove,cached_speed=cached_speed,nohit=nohit,mode=mode,fail=fail,time=0xffffffff,altitude=34.0,speed=.75,hostile=-1,candamage=-1,offscreenkill=0,remove=0,map=0,cost=10,nocost=1))
 rng=random.Random(4086)
 for _ in range(128):
  rows.append(dict(parent_type=rng.choice((0,1,2,32,0x80000001)),nomove=rng.choice((0,65536,-2147483648)),cached_speed=rng.choice((0.0,-0.0,.5,-1.5)),nohit=rng.randrange(2),mode=rng.randrange(2),fail=rng.randrange(2),time=rng.randrange(1<<32),altitude=rng.choice((-34.25,0.0,93.5)),speed=rng.choice((.5,1.5,0.0)),hostile=rng.choice((-1,0,33,-2147483648)),candamage=rng.choice((-1,0,33,-2147483648)),offscreenkill=rng.choice((0,30,-1,65536)),remove=rng.choice((0,1,-1)),map=rng.choice((0,1,2,3,-1)),cost=rng.choice((-1,0,10)),nocost=rng.randrange(2)))
 code=r'''#include <stdio.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_SHOT 32
#define AIMOVE1_ARROW 256
#define AIATTACK1_NOATTACK 4
typedef struct entity entity;
typedef struct {int type,nomove,project,knife,pshotno,hostile,candamage,aimove,aiattack,offscreenkill,remove,subject_to_wall,subject_to_platform,subject_to_hole,subject_to_gravity,no_adjust_base,maps_loaded;float speed;} model;
typedef struct {struct {int knife,flash;}projectile;struct {int cost;}energycost;} animation;
struct entity {model modeldata;model*model;animation*animation;entity*weapent,*owner;struct {float y;}position;int ptype,cantfire,nograb,attacking,remove_on_attack,autokill,map;void(*think)(void),(*trymove)(void),(*takedamage)(void),(*takeaction)(void);unsigned nextthink;float speedmul,base;};
typedef struct {int nohit;} stage;
entity parent,child,*self=&parent;model cached;animation anim;stage scene,*level=&scene;struct {int mode;} savedata;unsigned time;int nocost,fail,calls;
void common_think(void){}void arrow_takedamage(void){}
entity*spawn(float x,float z,float a,int d,char*n,int i,model*m){calls++;return fail?NULL:&child;}
void ent_set_colourmap(entity*e,unsigned m){e->map=m>(unsigned)e->modeldata.maps_loaded?0:m;}
'''+function+'\nint main(void){\n';expected=[]
 for c in rows:
  owner=dict(token=1,time=c['time'],energycost=c['cost'],nocost=c['nocost'],cantfire=99,nohit=c['nohit'],saved_mode=c['mode'],modeldata=dict(type=c['parent_type'],hostile=0x80000003,candamage=0x40000003))
  data={k:c[k]for k in ('nomove','speed','hostile','candamage','offscreenkill','remove')};data.update(maps_loaded=2,type=123)
  child=dict(modeldata=deepcopy(data),model_speed=c['cached_speed']);result=named_knife(owner,child,c['altitude'],c['map'])if not c['fail']else named_knife(owner,None,c['altitude'],c['map'])
  code+='memset(&parent,0,sizeof(parent));memset(&child,0,sizeof(child));self->animation=&anim;child.model=&cached;child.ptype=7;child.position.y=-9;child.base=-10;child.speedmul=3;self->cantfire=99;calls=0;'
  for key,value in dict(type=c['parent_type'],hostile=0x80000003,candamage=0x40000003).items():code+='self->modeldata.'+key+'='+str(value)+'u;'
  for key,value in data.items():code+='child.modeldata.'+key+'='+str(value)+('f'if isinstance(value,float)else'')+';'
  code+='cached.speed='+repr(c['cached_speed'])+'f;anim.energycost.cost='+str(c['cost'])+';nocost='+str(c['nocost'])+';scene.nohit='+str(c['nohit'])+';savedata.mode='+str(c['mode'])+';time='+str(c['time'])+'u;fail='+str(c['fail'])+';'
  code+='knife_spawn("fixture",-1,12,220,'+repr(c['altitude'])+'f,1,0,'+str(c['map'])+');'
  code+='printf("%d,%u,%d,%g,%g,%d,%d,%d,%u,%d,%d,%d,%d,%d,%g,%g,%u,%u,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\\n",calls,child.modeldata.type,child.ptype,child.position.y,child.modeldata.speed,child.owner==self,child.nograb,child.attacking,child.nextthink,child.modeldata.aimove,child.modeldata.offscreenkill,child.modeldata.aiattack,child.remove_on_attack,child.autokill,child.speedmul,child.base,child.modeldata.hostile,child.modeldata.candamage,child.modeldata.subject_to_wall,child.modeldata.subject_to_platform,child.modeldata.subject_to_hole,child.modeldata.subject_to_gravity,child.modeldata.no_adjust_base,child.map,self->cantfire,child.think==common_think,child.takedamage==arrow_takedamage,child.trymove==NULL&&child.takeaction==NULL);\n'
  if result:
   d=result['modeldata'];e=[1,d['type']&0xffffffff,0,result['a'],d['speed'],1,1,1,result['nextthink'],256,d['offscreenkill'],4,d['remove'],d['nomove'],2,result['base'],d['hostile']&0xffffffff,d['candamage']&0xffffffff,1,1,1,1,1,result['map'],owner['cantfire'],1,1,1]
  else:
   e=[1,123,7,-9,c['speed'],0,0,0,0,0,c['offscreenkill'],0,0,0,3,-10,c['hostile']&0xffffffff,c['candamage']&0xffffffff,0,0,0,0,0,0,99,0,0,1]
  expected.append(e)
 code+='return 0;}\n';(a.output/'projectile.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','projectile.c','-fe=projectile.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 log=subprocess.check_output([str(a.output/'projectile.exe')],text=True);(a.output/'authority.log').write_text(log);actual=[[float(n)if i in (3,4,14,15)else int(n)for i,n in enumerate(line.split(','))]for line in log.splitlines()]
 assert actual==expected,[(i,v,expected[i])for i,v in enumerate(actual)if v!=expected[i]][:2]
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NAMED_KNIFE_AUTHORITY_V1',status='PASS',engine_commit=ENGINE_COMMIT,source_function_sha256=hashlib.sha256(function.encode()).hexdigest(),source_function_unmodified=True,cases=len(rows),inputs=rows,actual=actual,expected=expected,spawn_and_colourmap_services_instrumented=True,native_projectile_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');print('PASS',len(rows),'literal named knife_spawn cases')

if __name__=='__main__':main()
