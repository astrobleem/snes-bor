"""Literal player_die versus resumable mutation plan and explicit child trace."""
import argparse,hashlib,itertools,json,os,re,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_die_4086 import player_die,Service

def initial(c):
 e=dict(token=1,playerindex=c['index'],health=150,mp=80,nodieblink=c['nodie'],type=1,weaploss=c['weap'],rush_max=17,think=1,action=1,exists=1)
 other=dict(e,token=2,playerindex=(c['index']+1)%4)
 players=[dict(lives=c['lives']if i==c['index']else 9,ent=e if i==c['index']else other if c['other']and i==(c['index']+1)%4 else None,joining=1 if c['joining']==i+1 else 0,credits=c['credits'],spawnhealth=-7,spawnmp=-8,weapnum=7,rush_saved=21+i)for i in range(4)]
 return dict(self=e,other=other,firstplayer=e if c['first']else other,players=players,livescheat=c['cheat'],rush_policy=c['rush'],noshare=c['noshare'],credits=c['credits'],timeleft=-77,nodropen=c['nodrop'],noreset=c['noreset'],settime=60,setweap=5)

def words(s,events):
 result=[s['firstplayer']['token']if s['firstplayer']else 0,s['timeleft']]
 for p in s['players']:result.extend([p['lives'],p['ent']['token']if p['ent']else 0,p['spawnhealth'],p['spawnmp'],p['weapnum'],p['rush_saved']])
 e=s['self'];result.extend([e['exists'],e['think'],e['action'],e['type'],len(events)]);result.extend(events)
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1');assert re.search(r'#define\s+GAME_SPEED\s+200',header)and re.search(r'#define\s+COUNTER_SPEED\s+\(GAME_SPEED\*2\)',header);body=extract(raw,'player_die')
 fields=('index','lives','cheat','first','nodie','rush','other','noshare','credits','joining','weap','nodrop','noreset')
 base=dict(zip(fields,(0,1,0,1,0,0,0,0,0,0,3,0,0)))
 cases=[dict(base,**dict(zip(fields[:10],v)))for v in itertools.product(range(4),(0,1,2),(0,1),(0,1),(0,3),(0,1,2),(0,1),(0,1),(0,1),(0,1,3))]
 for index,lives,weap,nodrop,noreset in itertools.product(range(4),(0,1,2),(0,1,2,3),(0,1),(-1,0,1)):cases.append(dict(base,index=index,lives=lives,weap=weap,nodrop=nodrop,noreset=noreset))
 code='''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define COUNTER_SPEED 400
#define TYPE_NONE 0
#define WEAPLOSS_TYPE_CHANGE 3
typedef unsigned int u32;
typedef struct entity {int playerindex,exists;struct {int health,mp,nodieblink,type;int weaploss[2];}modeldata;struct {struct {int max;}count;}rush;void (*think)(void),(*takeaction)(void);} entity;
entity e,other,replacement,*self=&e,*firstplayer;
struct {int lives;entity *ent;int joining,credits,spawnhealth,spawnmp,weapnum;}player[4];
struct {int setweap,noreset,settime;}lev,*level=&lev;
int livescheat,nomaxrushreset[5],noshare,credits,timeleft,nodropen,events[64],n;
void dummy(void){}
void event(int id,int a,int b){events[n++]=id;events[n++]=a;events[n++]=b;}
void execute_pdie_script(int i){event(1,i,0);}
void kill(entity *p){event(2,p==&e?1:2,0);p->exists=0;}
void spawnplayer(int i){event(3,i,0);player[i].ent=&replacement;}
void execute_respawn_script(int i){event(4,i,0);}
void control_rumble(int i,int force){event(5,i,force);}
void drop_all_enemies(void){event(6,0,0);}
int token(entity *p){return !p?0:p==&e?1:p==&other?2:3;}
'''+body+'''
int main(void){u32 v[13],w[64];int i,j;if(sizeof(int)!=4||sizeof(void*)!=4)return 3;setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);while(fread(v,4,13,stdin)==13){memset(player,0,sizeof(player));memset(&e,0,sizeof(e));e.playerindex=v[0];e.exists=1;e.modeldata.health=150;e.modeldata.mp=80;e.modeldata.nodieblink=v[4];e.modeldata.type=1;e.modeldata.weaploss[0]=v[10];e.rush.count.max=17;e.think=dummy;e.takeaction=dummy;other=e;firstplayer=v[3]?&e:&other;self=&e;n=0;for(i=0;i<4;i++){player[i].lives=i==v[0]?v[1]:9;player[i].ent=i==v[0]?&e:v[6]&&i==(v[0]+1)%4?&other:NULL;player[i].joining=v[9]==i+1;player[i].credits=v[8];player[i].spawnhealth=-7;player[i].spawnmp=-8;player[i].weapnum=7;nomaxrushreset[i]=21+i;}livescheat=v[2];nomaxrushreset[4]=v[5];noshare=v[7];credits=v[8];timeleft=-77;nodropen=v[11];lev.setweap=5;lev.noreset=v[12];lev.settime=60;player_die();j=0;w[j++]=token(firstplayer);w[j++]=timeleft;for(i=0;i<4;i++){w[j++]=player[i].lives;w[j++]=token(player[i].ent);w[j++]=player[i].spawnhealth;w[j++]=player[i].spawnmp;w[j++]=player[i].weapnum;w[j++]=nomaxrushreset[i];}w[j++]=e.exists;w[j++]=!!e.think;w[j++]=!!e.takeaction;w[j++]=e.modeldata.type;w[j++]=n;fwrite(w,4,j,stdout);fwrite(events,4,n,stdout);}return 0;}
'''
 (out/'playerdie.c').write_text(code);b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','playerdie.c','-fe=playerdie.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 expected=[]
 for c in cases:
  s=initial(c);events=[]
  for service,arg,value in player_die(s):
   events.extend((int(service),arg,value))
   if service==Service.KILL:s['self']['exists']=0
   if service==Service.SPAWN:s['players'][arg]['ent']=dict(s['self'],token=3)
  w=words(s,events);expected.append(struct.pack('<'+'I'*len(w),*(v&0xffffffff for v in w)))
 actual=subprocess.check_output([str(out/'playerdie.exe')],input=b''.join(struct.pack('<13I',*(c[k]&0xffffffff for k in fields))for c in cases));wanted=b''.join(expected);ok=actual==wanted;(out/'actual.bin').write_bytes(actual);(out/'expected.bin').write_bytes(wanted)
 r=dict(schema='BYOR_PLAYER_DIE_SOURCE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),cases=len(cases),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(wanted).hexdigest(),counter_speed=400,no_players_continue_timeleft=4000,no_credits_timeleft=200,joining_index_bug_preserved=True,child_services_instrumented=True,initialized_script_mutation_domain_exercised=False,native_player_die_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(cases),'literal player_die cases');assert ok
if __name__=='__main__':main()
