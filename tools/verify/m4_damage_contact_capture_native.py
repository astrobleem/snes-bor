"""Source damage request capture before the real opponent/effects/health join."""
import argparse,json,re,sys
from pathlib import Path
from unittest.mock import patch
import m4_combat_health_join_native as joined
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_combat_effects_requirements import derive
from source_damage_contact_capture_native import emit
from source_player_damage_force_native import emit as force
from source_combat_hit_scalars_native import derive as hit_requirements,emit as hit_scalars
from source_combat_death_native import emit as death
from m4_combat_death_native import authority as death_authority
from source_foreign_state_layout import layout
from source_current_colourmap import layout as colours


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--filtered-force',action='store_true');p.add_argument('--hit-scalars',action='store_true');p.add_argument('--death-prefix',action='store_true')
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();
 if a.hit_scalars and not a.filtered_force:p.error('--hit-scalars requires --filtered-force')
 if a.death_prefix and not a.hit_scalars:p.error('--death-prefix requires --hit-scalars')
 hr=hit_requirements(Source(a.source))if a.hit_scalars else None
 sy=symbols(Path('src/main.sym'));attacks=derive(Source(a.source))['attacks'];work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');w=colours()['controls'];original=joined.parent.loop.run_fixture;proof={}
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  anchor='AttackGateProbe_EffectBegin:\n.a16\n.i16';assert kw['append'].count(anchor)==1
  prefix=' jsl DamageContactCapture_Run\n bcs AttackGateProbe_Return\n jsl DamageContactCapture_Run\n bcs AttackGateProbe_Return\n'
  if a.filtered_force:prefix+=' jsl DamageForcePrepare_Run\n bcs AttackGateProbe_Return\n'
  kw['append']=kw['append'].replace(anchor,prefix+anchor)+emit(attacks,work,sy)
  if a.filtered_force:kw['append']+=force(work,sy,allow_nonplayer=True,prefix='DamageForcePrepare')
  if a.hit_scalars:
   for c in rows:c['common_cursor']=4
   anchor=' jsl HealthContact_Run';assert kw['append'].count(anchor)==1
   kw['append']=kw['append'].replace(anchor,' jsl CombatHitScalars_Run\n bcs AttackGateProbe_Return\n jsl CombatHitScalars_Run\n bcs AttackGateProbe_Return\n'+anchor)+hit_scalars(hr,work,sy)
   lua=lua.replace('local ranges={','local ranges={{0x7fbfa0,32},')
  if a.death_prefix:
   nominal=[c for c in rows if not c['fault']]
   for c in nominal:
    c.update(source_health=c['health_after'],root_kind=1,score_index=0,death_score=0,death_sound=-1,death_item=0,player=c['target_type'])
   proof['death_authority_sha256']=death_authority(folder,nominal)
   proof['death_source_C_cases']=len(nominal)
   proof['lethal_contacts']=sum(c['source_health']<=0 for c in nominal)
   for c in nominal:c['common_cursor']=c['death_cursor']
   anchor=' jsl HealthContact_Run\n bcs AttackGateProbe_Return';assert kw['append'].count(anchor)==1
   kw['append']=kw['append'].replace(anchor,anchor+'\n jsl CombatDeath_Run\n bcs AttackGateProbe_Return\n jsl CombatDeath_Run\n bcs AttackGateProbe_Return')+death(work,sy)
   lua=lua.replace('local ranges={','local ranges={{0x43eb00,4096},')
   kw['probes']['DEATHCALL']='CombatDeath_Run'
   lua+='\nemu.addMemoryCallback(function()emu.log("JOINDEATH|"..word(INDEX))end,emu.callbackType.exec,DEATHCALL,DEATHCALL,emu.cpuType.snes,mt)\n'
  anchor='before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
  setup=f' put({work}+60,0xb6b3);put({work}+62,0);put({work}+64,0);put({work}+72,0,4);put({work}+76,0,4);put({w}+40,0)\n'
  if a.hit_scalars:
   setup+=f' put({work}+84,0,4);put({work}+88,0xb6b4);put({work}+90,0);put({work}+92,0)\n'
   setup+=' for i=0,127 do put(0x40c000+96*i,0,4);put(0x414028+80*i,1,4);put(0x41402c+80*i,0,4)end\n'
   for key,value in(('Ready',0xb631),('StatsReady',0xb633),('NoScriptsReady',0xb632),('ScriptMask',0),('LifeScore',hr['globals']['lifescore'])):
    setup+=f' put({sy["SourceScore4086_"+key]},{value},{4 if key=="LifeScore"else 2})\n'
   setup+=' for i=0,3 do put(0x7fbfa0+4*i,100,4);put(0x7fbfb0+4*i,5,4)end\n'
  if a.death_prefix:
   setup+=f"""
 put(0x439010+80*c.first,0,4);put(0x439014+80*c.first,0,4);put(0x43eb00+32*c.first,1,4)
 put(0x409038+64*c.first,c.target_model);put(0x40903a+64*c.first,0xb638);put(0x40903c+64*c.first,0,4)
 put(0x414048+80*c.first,0,4);put(0x41404c+80*c.first,-1,4);put(0x433838+64*c.first,0,4)
 put({sy['SourceDeathFields4086_Ready']},0xb638);put({work}+94,0)
 """
  lua=lua.replace(anchor,setup+anchor)
  if a.death_prefix:
   anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
   expected=f"""
 if c.fault==0 then
  for _,f in ipairs({{{{0x439014+80*c.first,c.death_dead}},{{0x439010+80*c.first,c.death_nograb}},{{0x43eb00+32*c.first,c.death_idle}}}})do for j=0,3 do before[f[1]+j]=(f[2]>>(8*j))&255 end end
  before[{work}+94]=c.death_status;before[{work}+95]=0
 end
 """
   lua=lua.replace(anchor,expected+anchor)
  kw['probes'].update(CAPTURE='DamageContactCapture_Run',CAPTUREBAD='DamageContactCapture_Bad')
  for n in re.findall(r'^DamageContactCapture_Guard(\d+):',kw['append'],re.M):
   kw['probes']['CAPG'+n]='DamageContactCapture_Guard'+n
   lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("CAPTUREGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,CAPG{n},CAPG{n},emu.cpuType.snes,mt)\n'
  lua+='\nemu.addMemoryCallback(function()emu.log("DAMAGECAPTURE|"..word(INDEX))end,emu.callbackType.exec,CAPTURE,CAPTURE,emu.cpuType.snes,mt)\n'
  lua+='\nemu.addMemoryCallback(function()emu.log("DAMAGECAPTUREFAULT|"..word(INDEX))end,emu.callbackType.exec,CAPTUREBAD,CAPTUREBAD,emu.cpuType.snes,mt)\n'
  if a.hit_scalars:
   kw.setdefault('bindings',{})['SCORECALL']='SourceScore4086_Execute'
   lua+=f'\nemu.addMemoryCallback(function()if word({w}+44)==2 then emu.log("JOINHITSCORE|"..word(INDEX))end end,emu.callbackType.exec,SCORECALL,SCORECALL,emu.cpuType.snes,mt)\n'
   for n in re.findall(r'^CombatHitScalars_Guard(\d+):',kw['append'],re.M):
    kw['probes']['SCG'+n]='CombatHitScalars_Guard'+n
    lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("JOINSCALARGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,SCG{n},SCG{n},emu.cpuType.snes,mt)\n'
  if a.death_prefix:
   # The composed body exceeds the short-branch range of the earlier fixture.
   branch=0
   def far_return(match):
    nonlocal branch
    branch+=1
    return f' bcc ContactDeathJoin_Continue{branch}\n jmp AttackGateProbe_Return\nContactDeathJoin_Continue{branch}:\n.a16\n.i16'
   kw['append']=re.sub(r' bcs AttackGateProbe_Return',far_return,kw['append'])
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  if a.death_prefix:
   calls=[int(l.split('JOINDEATH|')[1])for l in log.splitlines()if'JOINDEATH|'in l]
   reporter.check('death runs twice only after admitted real contact health, preserving completed death state',calls==[i for i,c in enumerate(rows)if not c['fault']for _ in range(2)])
  if a.hit_scalars:
   calls=[int(l.split('JOINHITSCORE|')[1])for l in log.splitlines()if'JOINHITSCORE|'in l]
   expected=[i for i,c in enumerate(rows)if not c['fault']and c['opponents'][c['first']]==c['slot']]
   reporter.check('actual source zero-add score follows opponent/drop/effects/facing and executes once under retry',calls==expected)
  calls=[int(l.split('DAMAGECAPTURE|')[1])for l in log.splitlines()if'DAMAGECAPTURE|'in l];reporter.check('two real capture calls preserve the same retained damage request',calls==[i for i in range(len(rows))for _ in range(2)]);return raw,log
 args=['m4_combat_health_join_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 old_contact=joined.contact
 def captured_contact(*args,**kwargs):return old_contact(*args,**kwargs,captured_force=a.filtered_force,common_cursor=4 if a.hit_scalars else 2,advance_cursor=5 if a.death_prefix else None)
 with patch.object(joined,'contact',captured_contact),patch.object(joined.parent.loop,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:joined.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_DAMAGE_CONTACT_CAPTURE_NATIVE_V1',damage_contact_derived_by_native_code=True,damage_contact_capture_retried=True,prepared_force_before_common_body=a.filtered_force,actual_hit_scalars_bound=a.hit_scalars,actual_death_prefix_bound=a.death_prefix,**proof,captured_world_globals_installed_by_fixture=True,production_globals_capture_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
