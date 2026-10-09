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
from source_foreign_state_layout import layout
from source_current_colourmap import layout as colours


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--filtered-force',action='store_true')
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();sy=symbols(Path('src/main.sym'));attacks=derive(Source(a.source))['attacks'];work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');w=colours()['controls'];original=joined.parent.loop.run_fixture
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  anchor='AttackGateProbe_EffectBegin:\n.a16\n.i16';assert kw['append'].count(anchor)==1
  prefix=' jsl DamageContactCapture_Run\n bcs AttackGateProbe_Return\n jsl DamageContactCapture_Run\n bcs AttackGateProbe_Return\n'
  if a.filtered_force:prefix+=' jsl DamageForcePrepare_Run\n bcs AttackGateProbe_Return\n'
  kw['append']=kw['append'].replace(anchor,prefix+anchor)+emit(attacks,work,sy)
  if a.filtered_force:kw['append']+=force(work,sy,allow_nonplayer=True,prefix='DamageForcePrepare')
  anchor='before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
  setup=f' put({work}+60,0xb6b3);put({work}+62,0);put({work}+64,0);put({work}+72,0,4);put({work}+76,0,4);put({w}+40,0)\n'
  lua=lua.replace(anchor,setup+anchor)
  kw['probes'].update(CAPTURE='DamageContactCapture_Run',CAPTUREBAD='DamageContactCapture_Bad')
  for n in re.findall(r'^DamageContactCapture_Guard(\d+):',kw['append'],re.M):
   kw['probes']['CAPG'+n]='DamageContactCapture_Guard'+n
   lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("CAPTUREGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,CAPG{n},CAPG{n},emu.cpuType.snes,mt)\n'
  lua+='\nemu.addMemoryCallback(function()emu.log("DAMAGECAPTURE|"..word(INDEX))end,emu.callbackType.exec,CAPTURE,CAPTURE,emu.cpuType.snes,mt)\n'
  lua+='\nemu.addMemoryCallback(function()emu.log("DAMAGECAPTUREFAULT|"..word(INDEX))end,emu.callbackType.exec,CAPTUREBAD,CAPTUREBAD,emu.cpuType.snes,mt)\n'
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  calls=[int(l.split('DAMAGECAPTURE|')[1])for l in log.splitlines()if'DAMAGECAPTURE|'in l];reporter.check('two real capture calls preserve the same retained damage request',calls==[i for i in range(len(rows))for _ in range(2)]);return raw,log
 args=['m4_combat_health_join_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 old_contact=joined.contact
 def captured_contact(*args,**kwargs):return old_contact(*args,**kwargs,captured_force=a.filtered_force)
 with patch.object(joined,'contact',captured_contact),patch.object(joined.parent.loop,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:joined.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_DAMAGE_CONTACT_CAPTURE_NATIVE_V1',damage_contact_derived_by_native_code=True,damage_contact_capture_retried=True,prepared_force_before_common_body=a.filtered_force,captured_world_globals_installed_by_fixture=True,production_globals_capture_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
