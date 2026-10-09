"""Native checkdeath prefix, including real score and explicit child requirements."""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import m4_combat_hit_scalars_native as parent
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_combat_death_native import emit
from source_foreign_state_layout import layout
from source_current_colourmap import layout as colours
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def authority(folder,rows):
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 code='''#include <stdio.h>
#include <string.h>
#include <setjmp.h>
#define TYPE_PLAYER 1
#define TYPE_ENEMY 2
#define LONG long
#define VT_INTEGER 1
typedef struct {long lVal;int type;}ScriptVariant;
typedef struct {int initialized;}Script;
typedef struct entity {int health,dead,nograb,idling,boss,playerindex,itemplayer_count,exists,item;struct{int type,score,diesound;}modeldata;struct entity *opponent;}entity;
entity target,root,*self=&target;struct{unsigned score;int lives;}player[4];Script score_script[4];unsigned lifescore=50000;int SAMPLE_1UP=27;struct{int effectvol;}savedata;struct{int bosses;}lev,*level=&lev;int level_completed,request; jmp_buf pause;
void sound_play_sample(int sample,int loop,int l,int r,int speed){request=sample==27?1:2;longjmp(pause,1);}
int Script_IsInitialized(Script*s){return 0;}
void ScriptVariant_Init(ScriptVariant*v){}
void ScriptVariant_ChangeType(ScriptVariant*v,int t){}
void Script_Set_Local_Variant(Script*s,char*n,ScriptVariant*v){}
void Script_Execute(Script*s){}
void ScriptVariant_Clear(ScriptVariant*v){}
int count_ents(int t){request=3;longjmp(pause,1);return 0;}
void drop_item(entity*e){}
void kill_all_enemies(void){}
'''+extract(raw,'addscore')+'\n'+extract(raw,'checkdeath')+'''
int main(void){int i,j;int rows[][7]={
'''+',\n'.join('{'+','.join(str(c[k])for k in ('source_health','root_kind','score_index','death_score','death_sound','death_item','player'))+'}'for c in rows)+'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
memset(&target,0,sizeof(target));memset(&root,0,sizeof(root));for(j=0;j<4;j++){player[j].score=49999+j*50000;player[j].lives=5;}request=0;
target.health=rows[i][0];target.exists=1;target.idling=1;target.modeldata.type=rows[i][6];target.playerindex=rows[i][2];target.modeldata.score=rows[i][3];target.modeldata.diesound=rows[i][4];root.modeldata.type=rows[i][1]==0?1:2;root.playerindex=rows[i][2];target.opponent=rows[i][1]==2?0:rows[i][1]==3?&target:&root;target.item=rows[i][5]?1:0;
if(!setjmp(pause))checkdeath();printf("%d,%d,%d,%d",target.dead,target.nograb,target.idling,request);for(j=0;j<4;j++)printf(",%u,%d",player[j].score,player[j].lives);puts("");
}return 0;}
'''
 (folder/'death_prefix.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','death_prefix.c','-fe=death_prefix.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build-death-authority.log').write_text(b.stdout+b.stderr);assert b.returncode==0,b.stdout+b.stderr
 log=subprocess.check_output([str(folder/'death_prefix.exe')],cwd=folder,text=True);(folder/'death-prefix-authority.log').write_text(log);values=[list(map(int,l.split(',')))for l in log.splitlines()];assert len(rows)==len(values)
 for c,v in zip(rows,values):
  c['death_dead'],c['death_nograb'],c['death_idle'],c['death_request']=v[:4];c['death_stats']=v[4:];c['death_status']=int(bool(v[3]));c['death_cursor']={0:10,1:6,2:8,3:9}[v[3]]
 return hashlib.sha256(code.encode()).hexdigest()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');w=colours()['controls'];original=parent.player.parent.run_fixture;proof={}
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  rows[:]=[dict(c,source_health=c['expected'],death_score=(0,77,300,-1)[i%4],death_sound=(-1,17,18)[(i//4)%3],death_item=int(i%5==0))for i,c in enumerate(rows)if not c['fault']]
  seed=next(c for c in rows if c['source_health']<0 and c['root_kind']==0 and c['player']==1)
  rows.extend(dict(seed,death_score=score,death_sound=sound,death_item=item,score_index=index,called_index=index) for score in (0,77,300,-1)for sound in (-1,17,18)for item in (0,1)for index in (-1,0,3,7))
  proof['authority_cases']=len(rows)
  proof['authority_sha256']=authority(folder,rows)
  seed=next(c for c in rows if c['source_health']<0 and c['root_kind']==0 and c['score_index']==0)
  for bad in ('ready','ctor_ready','life_marker','life_model','relation_marker','relation_model','body_marker'):
   rows.append(dict(seed,fault=1,hit_stage_completed=True,bad='death_'+bad,death_score=0,death_sound=-1,death_item=0,death_dead=0,death_nograb=0,death_idle=1,death_request=-1,death_cursor=5,death_status=3,death_stats=[v for i in range(4) for v in (49999+i*50000,5)]))
  lua=lua.replace('local ranges={','local ranges={{0x43eb00,4096},{0x433800,8192},')
  anchor='before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
  setup=f"""
 put(0x439010+80*c.slot,0,4);put(0x439014+80*c.slot,0,4);put(0x43eb00+32*c.slot,1,4)
 put(0x409038+64*c.slot,0);put(0x40903a+64*c.slot,0xb638);put(0x40903c+64*c.slot,c.death_item==1 and 0x4140f0 or 0,4)
 put(0x414048+80*c.slot,c.death_score,4);put(0x41404c+80*c.slot,c.death_sound,4)
 put(0x433838+64*c.slot,0,4);put(0x43383e+64*c.slot,0xb5c2)
 put({work}+94,0)
 put({sy['SourceDeathFields4086_Ready']},0xb638);put({sy['SourceCtorState4086_Ready']},0xb5c2)
 for i=0,3 do put(0x7fbfa0+4*i,49999+i*50000,4)end
 """
  lua=lua.replace(anchor,setup+anchor)
  # Observe the final continuation cursor, not the earlier hit-score cursor.
  old=f'if c.fault==0 then before[{w}+44]=4;before[{w}+45]=0 end';assert lua.count(old)==1;lua=lua.replace(old,f'before[{w}+44]=c.death_cursor;before[{w}+45]=0')
  anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
  expected=f"""
 for _,f in ipairs({{{{0x439014+80*c.slot,c.death_dead}},{{0x439010+80*c.slot,c.death_nograb}},{{0x43eb00+32*c.slot,c.death_idle}}}})do for j=0,3 do before[f[1]+j]=(f[2]>>(8*j))&255 end end
 before[{work}+94]=c.death_status;before[{work}+95]=0
 if c.fault==1 then
  before[{work}+90]=2;before[{work}+91]=0
  for j=0,3 do before[0x414024+80*c.slot+j]=(c.source_health>>(8*j))&255;before[{work}+12+j]=(c.effective>>(8*j))&255;before[{work}+16+j]=0 end
 end
 for i=0,3 do for j=0,3 do before[0x7fbfa0+4*i+j]=(c.death_stats[2*i+1]>>(8*j))&255;before[0x7fbfb0+4*i+j]=(c.death_stats[2*i+2]>>(8*j))&255 end end
 """
  lua=lua.replace(anchor,expected+anchor)
  anchor=' jsl HealthContact_Run';assert kw['append'].count(anchor)==1
  kw['append']=kw['append'].replace(anchor,anchor+'\n bcs HealthProbe_Bad\n jsl CombatDeath_Run\n bcs HealthProbe_Bad\n jsl CombatDeath_Run')+emit(work,sy)
  for n in re.findall(r'^CombatDeath_Guard(\d+):',kw['append'],re.M):
   kw['probes']['DG'+n]='CombatDeath_Guard'+n
   lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("DEATHGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,DG{n},DG{n},emu.cpuType.snes,mt)\n'
  kw['probes']['DEATHBEGIN']='CombatDeath_Run'
  lua+=f'''
\nemu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local a,v
 if c.bad=='death_ready'then a={sy['SourceDeathFields4086_Ready']};v=0
 elseif c.bad=='death_ctor_ready'then a={sy['SourceCtorState4086_Ready']};v=0
 elseif c.bad=='death_life_marker'then a=0x43904a+80*c.slot;v=0
 elseif c.bad=='death_life_model'then a=0x439048+80*c.slot;v=1
 elseif c.bad=='death_relation_marker'then a=0x40903a+64*c.slot;v=0
 elseif c.bad=='death_relation_model'then a=0x409038+64*c.slot;v=1
 elseif c.bad=='death_body_marker'then a=0x43383e+64*c.slot;v=0 end
 if a then put(a,v);for j=0,1 do if before[a+j]~=nil then before[a+j]=(v>>(8*j))&255 end end end
end,emu.callbackType.exec,DEATHBEGIN,DEATHBEGIN,emu.cpuType.snes,mt)
'''
  kw['probes']['DBAD']='CombatDeath_Bad';lua+='\nemu.addMemoryCallback(function()emu.log("DEATHFAULT|"..word(INDEX))end,emu.callbackType.exec,DBAD,DBAD,emu.cpuType.snes,mt)\n'
  kw.setdefault('bindings',{})['DEATHSCORE']='SourceScore4086_Execute'
  lua+=f'\nemu.addMemoryCallback(function()if word({w}+44)==6 then emu.log("DEATHSCORECALL|"..word(INDEX))end end,emu.callbackType.exec,DEATHSCORE,DEATHSCORE,emu.cpuType.snes,mt)\n'
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  calls=[int(l.split('DEATHSCORECALL|')[1])for l in log.splitlines()if'DEATHSCORECALL|'in l]
  expected=[i for i,c in enumerate(rows)if not c['fault']and c['source_health']<=0 and(c['root_kind']==0 or c['root_kind']==3 and c['player']&1)]
  reporter.check('retained kill-score executes once even while its extra-life child remains required',calls==expected)
  proof['score_calls']=calls

  proof['required_counts']={k:sum(c['death_request']==v for c in rows)for k,v in dict(extra_life_audio=1,death_audio=2,item_count=3).items()};return raw,log
 old_contact=parent.player.contact
 def death_contact(*args,**kwargs):return old_contact(*args,**kwargs,advance_cursor=5)
 args=['m4_combat_hit_scalars_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 with patch.object(parent.player,'contact',death_contact),patch.object(parent.player.parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_COMBAT_DEATH_PREFIX_NATIVE_V1',death_authority_sha256=proof['authority_sha256'],death_source_C_cases=proof['authority_cases'],death_required_counts=proof['required_counts'],death_score_calls=proof['score_calls'],retained_score_not_restarted=True,source_checkdeath_and_addscore_unmodified=True,source_audio_and_item_count_pause_boundaries_instrumented=True,source_exists_preserved=True,positive_sound_item_boss_services_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
