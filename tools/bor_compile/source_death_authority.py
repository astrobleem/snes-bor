"""Pinned checkdeath with actual addscore; sound/item/boss services observed.

This separates source field ordering from runtime service completion. No
instrumented service is claimed as a native implementation.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
 p.add_argument('--coupled-authority',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads((a.coupled_authority/'report.json').read_text())
 assert authority['status']=='PASS' and authority['actual_addscore_and_SDL_rumble_bodies_proven']
 code=(a.coupled_authority/'callback.c').read_text().split('\nstruct Case{',1)[0]
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 bodies={n:extract(raw,n)for n in('checkdeath','addscore')}
 for name,body in bodies.items():assert extract(code,name)==body
 # Observe field state at each external service boundary, without replacing
 # either pinned function. The actual addscore runs before nograb/idling.
 code=code.replace('void sound_play_sample(int sample,int loop,int l,int r,int speed){event(9);}',
  'void sound_play_sample(int sample,int loop,int l,int r,int speed){if(loop||l!=37||r!=37||speed!=100)unexpected();event(900+sample);event(self->dead);event(self->nograb);event(self->idling);}')
 code=code.replace('int count_ents(int t){unexpected();return 0;}',
  'int players;int count_ents(int t){if(t!=TYPE_PLAYER)unexpected();event(20);return players;}')
 code=code.replace('void drop_item(entity *e){unexpected();}',
  'void drop_item(entity *e){if(e!=self)unexpected();event(21);}')
 code=code.replace('void kill_all_enemies(void){unexpected();}',
  'void kill_all_enemies(void){event(22);event(self->boss);event(level->bosses);event(level_completed);}')
 rows=[dict(zip(('health','opponent','type','score','diesound','item','players','item_count','boss','bosses'),v))
  for v in itertools.product((-7,0,1),(0,1,2,3),(1,2),(-1,0,77),(-1,17,18),(0,1),(0,2),(0,2),(0,1),(1,2))]
 code+='\nstruct Case{int health,opponent,type,score,diesound,item,players,item_count,boss,bosses;}cases[]={\n'
 code+=',\n'.join('{'+','.join(str(v)for v in row.values())+'}'for row in rows)+'\n};\n'
 code+=r'''
int main(void){unsigned i;int j;struct Case *c;
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(&victim,0,sizeof(victim));memset(&opponent,0,sizeof(opponent));memset(player,0,sizeof(player));memset(&lev,0,sizeof(lev));self=&victim;ne=0;
victim.exists=1;victim.health=c->health;victim.idling=1;victim.modeldata.type=c->type;victim.modeldata.score=c->score;victim.modeldata.diesound=c->diesound;lifescore=0xffffffff;
victim.opponent=c->opponent==0?NULL:c->opponent==1?self:&opponent;opponent.modeldata.type=c->opponent==2?TYPE_PLAYER:TYPE_ENEMY;
victim.item=c->item?&opponent:NULL;victim.itemplayer_count=c->item_count;players=c->players;victim.boss=c->boss;level->bosses=c->bosses;level_completed=0;savedata.effectvol=37;
checkdeath();printf("DEATH|%u|%d,%d,%d,%d,%d,%u,%d,%d|",i,victim.exists,victim.health,victim.dead,victim.nograb,victim.idling,player[0].score,victim.boss,level->bosses);
printf("%d|",level_completed);for(j=0;j<ne;j++)printf("%s%d",j?",":"",events[j]);puts("");
}return 0;}
'''
 (a.output/'death.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','death.c','-fe=death.exe'],cwd=a.output,env=env,capture_output=True,text=True)
 (a.output/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('DEATH_SOURCE_C_BUILD:'+build.stdout+build.stderr)
 log=subprocess.check_output([str(a.output/'death.exe')],cwd=a.output,text=True)
 actual=[];expected=[]
 for line,row in zip(log.splitlines(),rows):
  _,index,state,completed,events=line.split('|');assert int(index)==len(actual)
  actual.append(dict(state=list(map(int,state.split(','))),completed=int(completed),events=list(map(int,events.split(',')))if events else []))
  dead=int(row['health']<=0);is_player=row['opponent']==2 or(row['opponent']==1 and row['type']==1)
  score=min(row['score']&0xffffffff,999999999)if dead and is_player else 0
  trace=[]
  if dead:
   if row['diesound']>=0:trace.extend((900+row['diesound'],1,1,0))
   if row['item']:
    trace.append(20)
    if row['players']>row['item_count']:trace.append(21)
  bosses=row['bosses']-int(dead and row['boss']);completed=int(dead and row['boss']and bosses==0 and row['type']==2)
  if completed:trace.extend((22,0,0,0))
  expected.append(dict(state=[1,row['health'],dead,dead,1-dead,score,0 if dead else row['boss'],bosses],completed=completed,events=trace))
 ok=actual==expected and len(actual)==len(rows)
 out=dict(schema='BYOR_4086_DEATH_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),inputs=rows,actual=actual,expected=expected,
  function_sha256={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},source_exists_preserved=True,source_dead_is_not_retired=True,
  actual_addscore=True,score_domain='initial zero scores, lifescore UINT_MAX, no extra life or score script',sound_item_boss_services_instrumented=True,native_death_service_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(rows),'pinned death cases')
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
