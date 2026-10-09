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
from source_foreign_state_layout import layout
from source_current_colourmap import layout as colours


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--filtered-force',action='store_true');p.add_argument('--hit-scalars',action='store_true')
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();
 if a.hit_scalars and not a.filtered_force:p.error('--hit-scalars requires --filtered-force')
 hr=hit_requirements(Source(a.source))if a.hit_scalars else None
 sy=symbols(Path('src/main.sym'));attacks=derive(Source(a.source))['attacks'];work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');w=colours()['controls'];original=joined.parent.loop.run_fixture
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
  anchor='before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
  setup=f' put({work}+60,0xb6b3);put({work}+62,0);put({work}+64,0);put({work}+72,0,4);put({work}+76,0,4);put({w}+40,0)\n'
  if a.hit_scalars:
   setup+=f' put({work}+84,0,4);put({work}+88,0xb6b4);put({work}+90,0);put({work}+92,0)\n'
   setup+=' for i=0,127 do put(0x40c000+96*i,0,4);put(0x414028+80*i,1,4);put(0x41402c+80*i,0,4)end\n'
   for key,value in(('Ready',0xb631),('StatsReady',0xb633),('NoScriptsReady',0xb632),('ScriptMask',0),('LifeScore',hr['globals']['lifescore'])):
    setup+=f' put({sy["SourceScore4086_"+key]},{value},{4 if key=="LifeScore"else 2})\n'
   setup+=' for i=0,3 do put(0x7fbfa0+4*i,100,4);put(0x7fbfb0+4*i,5,4)end\n'
  lua=lua.replace(anchor,setup+anchor)
  kw['probes'].update(CAPTURE='DamageContactCapture_Run',CAPTUREBAD='DamageContactCapture_Bad')
  for n in re.findall(r'^DamageContactCapture_Guard(\d+):',kw['append'],re.M):
   kw['probes']['CAPG'+n]='DamageContactCapture_Guard'+n
   lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("CAPTUREGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,CAPG{n},CAPG{n},emu.cpuType.snes,mt)\n'
  lua+='\nemu.addMemoryCallback(function()emu.log("DAMAGECAPTURE|"..word(INDEX))end,emu.callbackType.exec,CAPTURE,CAPTURE,emu.cpuType.snes,mt)\n'
  lua+='\nemu.addMemoryCallback(function()emu.log("DAMAGECAPTUREFAULT|"..word(INDEX))end,emu.callbackType.exec,CAPTUREBAD,CAPTUREBAD,emu.cpuType.snes,mt)\n'
  if a.hit_scalars:
   kw.setdefault('bindings',{})['SCORECALL']='SourceScore4086_Execute'
   lua+='\nemu.addMemoryCallback(function()emu.log("JOINHITSCORE|"..word(INDEX))end,emu.callbackType.exec,SCORECALL,SCORECALL,emu.cpuType.snes,mt)\n'
   for n in re.findall(r'^CombatHitScalars_Guard(\d+):',kw['append'],re.M):
    kw['probes']['SCG'+n]='CombatHitScalars_Guard'+n
    lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("JOINSCALARGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,SCG{n},SCG{n},emu.cpuType.snes,mt)\n'
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  if a.hit_scalars:
   calls=[int(l.split('JOINHITSCORE|')[1])for l in log.splitlines()if'JOINHITSCORE|'in l]
   expected=[i for i,c in enumerate(rows)if not c['fault']and c['opponents'][c['first']]==c['slot']]
   reporter.check('actual source zero-add score follows opponent/drop/effects/facing and executes once under retry',calls==expected)
  calls=[int(l.split('DAMAGECAPTURE|')[1])for l in log.splitlines()if'DAMAGECAPTURE|'in l];reporter.check('two real capture calls preserve the same retained damage request',calls==[i for i in range(len(rows))for _ in range(2)]);return raw,log
 args=['m4_combat_health_join_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 old_contact=joined.contact
 def captured_contact(*args,**kwargs):return old_contact(*args,**kwargs,captured_force=a.filtered_force,common_cursor=4 if a.hit_scalars else 2)
 with patch.object(joined,'contact',captured_contact),patch.object(joined.parent.loop,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:joined.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_DAMAGE_CONTACT_CAPTURE_NATIVE_V1',damage_contact_derived_by_native_code=True,damage_contact_capture_retried=True,prepared_force_before_common_body=a.filtered_force,actual_hit_scalars_bound=a.hit_scalars,captured_world_globals_installed_by_fixture=True,production_globals_capture_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
