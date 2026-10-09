"""Native nonself MP and zero-multiplier hit scoring before common health."""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import m4_player_health_contact_native as player
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_combat_hit_scalars_native import derive,emit
from source_foreign_state_layout import layout
from source_current_colourmap import layout as colours
from script_nested_authority import extract


def authority(folder,req,rows):
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',req['engine_commit']+':engine/openbor.c']).decode('latin1')
 code='''#include <stdio.h>
#include <string.h>
#define TYPE_PLAYER 1
typedef struct entity {struct{int type,multiple,mp,mprate;}modeldata;int playerindex,damage_on_landing,mp;struct entity *opponent;}entity;
typedef struct{int attack_force;}s_attack;
entity target,physical,root,*self=&target;int magic_type,calls,index,amount,rumble;
void addscore(int i,int a){calls++;index=i;amount=a;}
void control_rumble(int i,int f){rumble=f;}
'''+extract(raw,'checkhitscore')+'\n'+extract(raw,'checkmpadd')+'''
int main(void){int i; s_attack a;int rows[][4]={
'''+',\n'.join('{'+','.join(str(c[k])for k in ('root_kind','score_index','effective','magic'))+'}'for c in rows)+'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
memset(&target,0,sizeof(target));memset(&physical,0,sizeof(physical));memset(&root,0,sizeof(root));calls=0;index=-777;amount=-777;rumble=0;
root.modeldata.type=rows[i][0]==0?1:2;root.playerindex=rows[i][1];target.modeldata.type=1;target.playerindex=rows[i][1];target.opponent=rows[i][0]==2?0:rows[i][0]==3?&target:&root;target.modeldata.multiple=0;root.mp=8;root.modeldata.mp=300;root.modeldata.mprate=5;magic_type=rows[i][3];a.attack_force=rows[i][2];checkmpadd();checkhitscore(&physical,&a);printf("%d,%d,%d,%d,%d\\n",calls,index,amount,rumble,root.mp);
}return 0;}
'''
 (folder/'hit_scalars.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');p=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','hit_scalars.c','-fe=hit_scalars.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build-authority-scalars.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
 log=subprocess.check_output([str(folder/'hit_scalars.exe')],cwd=folder,text=True);(folder/'hit-scalars-authority.log').write_text(log);values=[list(map(int,l.split(',')))for l in log.splitlines()];assert len(values)==len(rows)
 for c,v in zip(rows,values):c['score_calls'],c['called_index'],c['called_amount'],c['source_rumble'],c['source_mp']=v
 return hashlib.sha256(code.encode()).hexdigest()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=derive(Source(a.source));sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');w=colours()['controls'];original=player.parent.run_fixture;proof={}
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  rows[:]=[dict(c,root_kind=i%4,score_index=(-1,0,3,7)[(i//4)%4],magic=i%3*2) for i,c in enumerate(rows)if not c['fault']and c['health']in(1,100)]
  proof['authority_sha256']=authority(folder,req,rows)
  seed=next(c for c in rows if c['root_kind']==0 and c['score_index']==0)
  for bad in ('marker','reserved','magic','multiple','opponent','score_ready','score_life','score_script'):
   rows.append(dict(seed,bad='scalar_'+bad,fault=1,expected=seed['health'],score_calls=0))
  lua=lua.replace('local ranges={','local ranges={{0x7fbfa0,32},')
  anchor='before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
  setup=f"""
 put({work}+84,c.magic,4);put({work}+88,0xb6b4);put({work}+90,0);put({work}+92,0)
 put(0x40c000+96*c.slot,0,4);put(0x40903a+64*c.slot,0xb638)
 local root=c.root_kind==3 and c.slot or 3
 put(0x40900c+64*c.slot,c.root_kind==2 and 0 or 0x414000+80*root,4)
 if root~=c.slot then put(0x40c048+96*root,c.root_kind==0 and 1 or 2,4)end
 put(0x414028+80*root,1,4);put(0x41402c+80*root,c.score_index,4)
 put({sy['SourceScore4086_Ready']},0xb631);put({sy['SourceScore4086_StatsReady']},0xb633);put({sy['SourceScore4086_NoScriptsReady']},0xb632);put({sy['SourceScore4086_LifeScore']},{req['globals']['lifescore']},4);put({sy['SourceScore4086_ScriptMask']},0)
 for i=0,3 do put(0x7fbfa0+4*i,49999+i*50000,4);put(0x7fbfb0+4*i,5,4)end
 if c.bad=='scalar_marker'then put({work}+88,0)
 elseif c.bad=='scalar_reserved'then put({work}+92,1)
 elseif c.bad=='scalar_magic'then put({work}+84,1,4)
 elseif c.bad=='scalar_multiple'then put(0x40c000+96*c.slot,1,4)
 elseif c.bad=='scalar_opponent'then put(0x40900c+64*c.slot,0x414001,4)
 elseif c.bad=='scalar_score_ready'then put({sy['SourceScore4086_Ready']},0)
 elseif c.bad=='scalar_score_life'then put({sy['SourceScore4086_LifeScore']},1,4)
 elseif c.bad=='scalar_score_script'then put({sy['SourceScore4086_ScriptMask']},1)end
 """
  lua=lua.replace(anchor,setup+anchor)
  anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
  lua=lua.replace(anchor,f' for j=0,1 do before[{work}+90+j]=((c.fault==1 and 3 or 2)>>(8*j))&255 end\n if c.fault==0 then before[{w}+44]=4;before[{w}+45]=0 end\n'+anchor)
  anchor=' jsl HealthContact_Run';assert kw['append'].count(anchor)==1
  kw['append']=kw['append'].replace(anchor,' jsl CombatHitScalars_Run\n bcs HealthProbe_Bad\n jsl CombatHitScalars_Run\n bcs HealthProbe_Bad\n'+anchor)+emit(req,work,sy)
  kw.setdefault('bindings',{})['SCORECALL']='SourceScore4086_Execute'
  for n in re.findall(r'^CombatHitScalars_Guard(\d+):',kw['append'],re.M):
   kw['probes']['SG'+n]='CombatHitScalars_Guard'+n
   lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("SCALARGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,SG{n},SG{n},emu.cpuType.snes,mt)\n'
  kw['probes']['SCALARFAIL']='CombatHitScalars_Bad'
  lua+='\nemu.addMemoryCallback(function()emu.log("SCALARFAIL|"..word(INDEX))end,emu.callbackType.exec,SCALARFAIL,SCALARFAIL,emu.cpuType.snes,mt)\n'
  lua+=f'''\nemu.addMemoryCallback(function()emu.log('HITSCORECALL|'..word(INDEX)..'|'..word({sy['SourceScore4086_Index']})..'|'..word({sy['SourceScore4086_Add']}))end,emu.callbackType.exec,SCORECALL,SCORECALL,emu.cpuType.snes,mt)\n'''
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  calls=[list(map(int,l.split('HITSCORECALL|')[1].split('|')))for l in log.splitlines()if'HITSCORECALL|'in l];expected=[[i,c['called_index']&65535,0]for i,c in enumerate(rows)if not c['fault']and c['score_calls']]
  reporter.check('source player opponent scoring calls actual B631 exactly once under retry; source MP remains unchanged',calls==expected and all(c['source_mp']==8 for c in rows if not c['fault']));proof['calls']=calls;return raw,log
 old_contact=player.contact
 def scoring_contact(*args,**kwargs):return old_contact(*args,**kwargs,common_cursor=4)
 args=['m4_player_health_contact_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 with patch.object(player,'contact',scoring_contact),patch.object(player.parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:player.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_COMBAT_HIT_SCALARS_NATIVE_V1',hit_scalars_requirements=req,hit_scalar_authority_sha256=proof['authority_sha256'],native_hit_score_calls=proof['calls'],source_checkmpadd_and_checkhitscore_unmodified=True,rumble_policy=req['rumble_policy'],full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
