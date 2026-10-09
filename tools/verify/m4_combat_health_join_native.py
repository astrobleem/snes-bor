"""Real collision/block/opponent/drop/effects/facing joined to common health."""
import argparse,json,re,sys
from pathlib import Path
from unittest.mock import patch
import m4_combat_effects_native as parent
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_combat_health_native import derive,emit
from source_combat_health_contact_native import emit as contact
from source_combat_effects_requirements import derive as effects
from source_current_colourmap import layout as colours
from source_foreign_state_layout import layout
from source_foreign_water_retirement import emit as water,transform as retire_water
from source_model_core_4086 import derive as core_models


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();src=Source(a.source);req=derive(src);attacks=effects(src)['attacks'];types=core_models(src)['models'];sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');original=parent.loop.run_fixture;observed=[]
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  # The earlier effects matrix includes synthetic Shock-type victims. Keep
  # the authored enemy models for this source-type common callback join.
  rows[:]=[c for c in rows if types[c['target_model']]['fields']['type']&2]
  for i,c in enumerate(rows):
   c['health_before']=(1,10,100,300)[i%4];c['health_after']=c['health_before']-attacks[c['attack_index']-1]['attack_force'];c['target_type']=types[c['target_model']]['fields']['type']
  anchor=' before={};for _,r in ipairs(ranges)'
  # The outer contact fixture seeds its view before this installed snapshot.
  if anchor not in lua:anchor='before={};for _,r in ipairs(ranges)'
  assert lua.count(anchor)==1
  setup="""
 for _,i in ipairs({c.slot,c.first})do
  put(0x414020+80*i,1,4);put(0x414024+80*i,i==c.first and c.health_before or 100,4);put(0x414040+80*i,1,4);put(0x414044+80*i,300,4)
  put(0x432800+32*i,0x3f800000,4);put(0x43281c+32*i,0x3f800000,4)
  put(0x439018+80*i,0,4);put(0x439048+80*i,i==c.first and c.target_model or 0);put(0x43904a+80*i,0xb4fb)
  put(0x416810+64*i,0,4)
 end
 put(0x40c048+96*c.first,c.target_type,4)
 put(0x40c030+96*c.slot,2,4);put(0x40c034+96*c.slot,2,4)
 set('SourceLifecycle4086_Ready',0xb4fb)
"""
  lua=lua.replace(anchor,setup+anchor)
  anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
  lua=lua.replace(anchor," if c.fault==0 then for j=0,3 do before[0x414024+80*c.first+j]=(c.health_after>>(8*j))&255 end end\n"+anchor)
  anchor=' jsl DamageFlip_Run\n bcs AttackGateProbe_Return';assert kw['append'].count(anchor)==1
  kw['append']=kw['append'].replace(anchor,anchor+'\n jsl HealthContact_Run\n bcs AttackGateProbe_Return')+emit(req,work,sy)+contact(attacks,work,sy)+water(sy)
  old_transform=kw.get('rom_transform')
  def transform(raw,linked):
   if old_transform:old_transform(raw,linked)
   retire_water(raw,linked)
  kw['rom_transform']=transform
  kw['probes'].update(HEALTHCALL='HealthContact_Run',HEALTHFAIL='CombatHealth_Bad',CONTACTFAIL='HealthContact_Bad')
  for n in re.findall(r'^CombatHealth_Guard(\d+):',kw['append'],re.M):
   kw['probes']['HEALTHG'+n]='CombatHealth_Guard'+n
   lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("JOINHEALTHGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,HEALTHG{n},HEALTHG{n},emu.cpuType.snes,mt)\n'
  lua+=f'\nemu.addMemoryCallback(function()emu.log("JOINHEALTHCALL|"..word(INDEX))end,emu.callbackType.exec,HEALTHCALL,HEALTHCALL,emu.cpuType.snes,mt)\n'
  lua+=f'\nemu.addMemoryCallback(function()emu.log("JOINHEALTHFAULT|"..word(INDEX).."|"..word({work}+2))end,emu.callbackType.exec,HEALTHFAIL,HEALTHFAIL,emu.cpuType.snes,mt)\n'
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  calls=[int(l.split('JOINHEALTHCALL|')[1])for l in log.splitlines()if'JOINHEALTHCALL|'in l];observed.extend(calls);reporter.check('common health runs once for each admitted damage contact and never for rejected contacts',calls==[i for i,c in enumerate(rows)if not c['fault']]);return raw,log
 args=['m4_combat_effects_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output),'--opponent','--damagedrop']
 with patch.object(parent.loop,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_COMBAT_COMMON_HEALTH_JOIN_NATIVE_V1',actual_common_health_bound=True,health_calls=observed,player_damage_filter_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
