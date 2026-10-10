"""Literal BOR 4086 recovery functions versus explicit child mutation plans."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_recovery_4086 import common_lie,set_rise,common_rise

FIELDS={'health':'health','falldie':'modeldata.falldie','nodieblink':'modeldata.nodieblink',
 'type':'modeldata.type','animating':'animating','damagetype':'damagetype','blink':'blink',
 'stall':'stalltime','noai':'noaicontrol','ko':'modeldata.maps.ko','kotype':'modeldata.maps.kotype',
 'colourmap':'colourmap','y':'position.y','base':'base','vx':'velocity.x','vy':'velocity.y',
 'vz':'velocity.z','drop':'drop','falling':'falling','projectile':'projectile','nograb':'nograb',
 'juggle':'modeldata.jugglepoints.current','maxjuggle':'modeldata.jugglepoints.max',
 'riseattack_stall':'staydown.riseattack_stall','riseinv':'modeldata.riseinv',
 'invinctime':'invinctime','invincible':'invincible'}
FLOATS={'y','base','vx','vy','vz'}
BASE=dict(zip(FIELDS,(100,0,0,2,0,1,7,48,0,0,0,17,0,0,1,2,3,1,1,2,4,5,9,19,0,31,0)))
BASE['action']=1

def cases():
 rows=[]
 def add(callback,**changes):
  e=dict(BASE);e.update(changes);rows.append(dict(callback=callback,e=e,time=48,same=1,type=1,reset=0,valid=[1,1,1]))
 for health,policy,anim,type,ko,kt,fall in itertools.product((-1,0,100),range(4),(0,1,-1),(0,1,2,3),(0,2),(0,1),(0,2)):
  add(0,health=health,nodieblink=policy,animating=anim,type=type,ko=ko,kotype=kt,falldie=fall)
 for stall,y,base,vy in itertools.product((47,48,49,0xffffffff),(-1,0,1),(-1,0,1),(-1,0,1)):
  add(0,stall=stall,y=y,base=base,vy=vy)
 for same,t,reset,valid in itertools.product((0,1),(-1,0,1,2,3),(0,1,-1),itertools.product((0,1),repeat=3)):
  add(1);rows[-1].update(same=same,type=t,reset=reset,valid=list(valid))
 for anim,inv,time in itertools.product((0,1,-1),(-200,-1,0,1,200),(0,48,0xffffff00,0xffffffff)):
  add(2,animating=anim,riseinv=inv);rows[-1]['time']=time
 return rows

def words(e):
 return [struct.unpack('<I',struct.pack('<f',e[k]))[0]if k in FLOATS else e[k]&0xffffffff for k in FIELDS]+[e['action']]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
 assert 'KOMAP_TYPE_IMMEDIATELY,'in header
 enum=header[header.rfind('typedef enum',0,header.index('KOMAP_TYPE_IMMEDIATELY,')):header.index('} e_komap_type;')]
 assert enum.count('KOMAP_TYPE_')==2 and '='not in enum
 bodies={n:extract(raw,n)for n in ('common_lie','set_rise','common_rise')};rows=cases();roles=[10,11,12]
 code=r'''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct {int falldie,nodieblink,type,riseinv;struct{int ko,kotype;}maps;struct{int current,max;}jugglepoints;}model;
typedef struct entity {int health,animating,damagetype,blink,noaicontrol,colourmap,drop,falling,projectile,nograb,invincible;
u32 stalltime,invinctime;struct{u32 riseattack_stall;}staydown;struct{float y;}position;float base;struct{float x,y,z;}velocity;model modeldata;void(*takeaction)(void);}entity;
entity e,other,*self;u32 time;int max_attack_types=3;int roles[3]={10,11,12},*animrises=roles;int valid[3],n;u32 events[64];
#define TYPE_PLAYER 1
#define TYPE_NONE 0
#define GAME_SPEED 200
#define KOMAP_TYPE_IMMEDIATELY 0
#define ABS(a) ((a)<0?-(a):(a))
void player_blink(void){}void suicide(void){}void player_die(void){}void common_rise(void);void common_lie(void);
void event(int a){events[n++]=(u32)a;}
void set_death(entity*p,int t,int r){event(1);event(t);event(r);}
int model_get_colourmap(model*p,int m){event(2);event(m);return m+1000;}
int set_rise(entity*p,int t,int r);
void ent_set_anim(entity*p,int a,int r){event(4);event(a);event(r);}
void set_idle(entity*p){event(5);}
int validanim(entity*p,int a){event(6);event(a);return a>=10&&a<=12&&valid[a-10];}
u32 bits(float f){u32 a;memcpy(&a,&f,4);return a;}
'''
 # common_lie's child is instrumented, while set_rise itself is separately
 # compiled without edits. Only the child's name is selected by a macro.
 code+='int record_rise(entity*p,int t,int r){event(3);event(t);event(r);return 1;}\n#define set_rise record_rise\n'+bodies['common_lie']+'\n#undef set_rise\n'+bodies['set_rise']+'\n'+bodies['common_rise']+'\n'
 code+='void output(entity*p){u32 w['+str(len(FIELDS)+1)+'];'
 for i,(k,v)in enumerate(FIELDS.items()):code+=f'w[{i}]='+('bits(p->'+v+')'if k in FLOATS else '(u32)p->'+v)+';'
 code+=f'w[{len(FIELDS)}]=p->takeaction==common_lie?1:p->takeaction==player_blink?2:p->takeaction==suicide?3:p->takeaction==player_die?4:p->takeaction==common_rise?5:0;fwrite(w,4,sizeof(w)/4,stdout);}}\n'
 code+='int main(void){u32 row['+str(len(FIELDS)+8)+'],result,i;setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4||sizeof(float)!=4)return 3;while(fread(row,4,'+str(len(FIELDS)+8)+',stdin)=='+str(len(FIELDS)+8)+'){memset(&e,0,sizeof(e));'
 for i,(k,v)in enumerate(FIELDS.items()):
  code+=f'e.{v}='+(f'((int)row[{i}])/4.0f;'if k in FLOATS else f'row[{i}];')
 j=len(FIELDS);code+=f'e.takeaction=common_lie;other=e;self=row[{j+2}]?&e:&other;time=row[{j+1}];valid[0]=row[{j+5}];valid[1]=row[{j+6}];valid[2]=row[{j+7}];n=0;result=0;if(row[{j}]==0)common_lie();else if(row[{j}]==1)result=set_rise(&e,(int)row[{j+3}],(int)row[{j+4}]);else common_rise();output(&e);output(row[{j+2}]?&e:&other);fwrite(&result,4,1,stdout);fwrite(&n,4,1,stdout);fwrite(events,4,n,stdout);}}return 0;}}\n'
 (out/'recovery.c').write_text(code);b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','recovery.c','-fe=recovery.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 inputs=[];expected=[]
 for r in rows:
  inputwords=[int(r['e'][k]*4)if k in FLOATS else r['e'][k] for k in FIELDS]+[r['callback'],r['time'],r['same'],r['type'],r['reset'],*r['valid']]
  inputs.append(struct.pack('<'+'I'*len(inputwords),*(v&0xffffffff for v in inputwords)))
  target=dict(r['e']);self=target if r['same']else dict(target);result=0
  if r['callback']==0:events=common_lie(self,r['time'])
  elif r['callback']==1:result,events=set_rise(target,self,r['type'],r['reset'],r['valid'],roles)
  else:events=common_rise(self,r['time'])
  flat=[int(v)for event in events for v in event];w=words(target)+words(self)+[result,len(flat)]+[v&0xffffffff for v in flat];expected.append(struct.pack('<'+'I'*len(w),*w))
 actual=subprocess.check_output([str(out/'recovery.exe')],input=b''.join(inputs));wanted=b''.join(expected);ok=actual==wanted
 (out/'actual.bin').write_bytes(actual);(out/'expected.bin').write_bytes(wanted)
 report=dict(schema='BYOR_RECOVERY_SOURCE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256={k:hashlib.sha256(v.encode('latin1')).hexdigest()for k,v in bodies.items()},cases=len(rows),cases_by_callback={n:sum(r['callback']==i for r in rows)for i,n in enumerate(bodies)},compared_bytes=len(wanted),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(wanted).hexdigest(),child_services_instrumented=True,set_rise_global_self_velocity_asymmetry_preserved=True,int_min_abs_admitted=False,native_recovery_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'literal recovery cases');assert ok

if __name__=='__main__':main()
