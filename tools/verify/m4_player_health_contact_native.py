"""Join source player/NPC copied force to the guarded common health contact.

Collision/effects completion and global inputs are installed by this fixture.
Health expectations come from the parent's unmodified source C checkdamage.
"""
import argparse,json,re,sys
from pathlib import Path
from unittest.mock import patch
import m4_combat_health_native as parent
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_combat_effects_requirements import derive
from source_combat_health_contact_native import emit as contact
from source_player_damage_force_native import emit as force
from source_foreign_state_layout import layout
from source_current_colourmap import layout as colours


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();sy=symbols(Path('src/main.sym'));attacks=derive(Source(a.source))['attacks'];assert attacks[8]['attack_force']==7 and attacks[8]['no_kill']==0
 work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');w=colours()['controls'];original=parent.run_fixture
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  # Match source attack 9. Pair source-C results for force 7 and force 0.
  bases=[c for c in rows if not c['fault'] and c['force']==7 and not c['nokill']]
  zero={(c['slot'],c['health'],c['inv'],c['alt'],c['life']):c['expected'] for c in rows if not c['fault'] and c['force']==0 and not c['nokill']}
  # The parent has no force-zero pit matrix: those were separately certified.
  bases=[c for c in bases if (c['slot'],c['health'],c['inv'],c['alt'],c['life']) in zero]
  joined=[]
  for c in bases:
   for player,other_type,cheat,nohurt in ((1,2,0,0),(1,2,1,0),(1,2,0,1),(1,0,0,1),(1,2,-2147483648,0),(0,2,1,1)):
    filtered=bool(player and (cheat or (nohurt and other_type&2)))
    joined.append(dict(c,player=player,other_type=other_type,cheat=cheat,nohurt=nohurt,effective=0 if filtered else 7,expected=zero[(c['slot'],c['health'],c['inv'],c['alt'],c['life'])] if filtered else c['expected']))
  seed=joined[0]
  for bad in ('snapshot','globals','globals_reserved','contact_marker','contact_time','contact_frame','raw_force','contact_attack'):
   joined.append(dict(seed,bad=bad,fault=1,expected=seed['health']))
  rows[:]=joined
  lua=lua.replace('local ranges={',f'local ranges={{{{{work},96}},{{{w},64}},{{0x40c000,12288}},')
  anchor='before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
  setup=f"""
 put(0x40c048+96*c.slot,c.player,4);put(0x40c048+96*c.other,c.other_type,4)
 put({work}+60,0xb6b3);put({work}+62,0);put({work}+64,0xb6b2);put({work}+66,0);put({work}+68,7,4);put({work}+72,c.cheat,4);put({work}+76,c.nohurt,4);put({work}+80,165*0x1010101,4)
 put({w}+40,0xb6ad);put({w}+42,2);put({w}+44,2);put({w}+48,c.slot);put({w}+46,c.other);put({w}+8,1,4);put({w}+12,48,4);put({w}+50,9);put({w}+52,0);put({w}+54,11)
 put({sy['SourceCollisionFrame4086_Attack']},9);put({sy['SourceCollisionFrame4086_Frame']},0);put({sy['SourceCollisionFrame4086_Handle']},11)
 if c.bad=='snapshot'then put({work}+64,0)
 elseif c.bad=='globals'then put({work}+60,0)
 elseif c.bad=='globals_reserved'then put({work}+62,1)
 elseif c.bad=='contact_marker'then put({w}+40,0)
 elseif c.bad=='contact_time'then put({w}+12,49,4)
 elseif c.bad=='contact_frame'then put({w}+52,1)
 elseif c.bad=='raw_force'then put({work}+68,8,4)
 elseif c.bad=='contact_attack'then put({w}+50,32)end
 """
  lua=lua.replace(anchor,setup+anchor)
  anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
  expected=f"""
 local early=c.bad=='snapshot' or c.bad=='globals' or c.bad=='globals_reserved'
 for j=0,1 do before[{work}+2+j]=((c.fault==1 and 3 or 2)>>(8*j))&255;before[{work}+66+j]=((early and 3 or 2)>>(8*j))&255 end
 if not early then
  local eff=c.bad=='raw_force' and 8 or c.effective
  for j=0,3 do before[{work}+80+j]=(eff>>(8*j))&255 end
 end
 if c.fault==0 then for j=0,3 do before[{work}+12+j]=(c.effective>>(8*j))&255;before[{work}+16+j]=0 end end
 """
  lua=lua.replace(anchor,expected+anchor)
  anchor=' jsl CombatHealth_Run';assert kw['append'].count(anchor)==1
  kw['append']=kw['append'].replace(anchor,' jsl DamageForcePrepare_Run\n bcs HealthProbe_Bad\n jsl HealthContact_Run')
  anchor='HealthProbe_Bad:\n.a16\n.i16';assert kw['append'].count(anchor)==1
  kw['append']=kw['append'].replace(anchor,anchor+f'\n lda #3\n sta.l {work}+2')
  kw['append']+=force(work,sy,allow_nonplayer=True,prefix='DamageForcePrepare')+contact(attacks,work,sy,captured_force=True)
  return original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
 args=['m4_combat_health_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_PLAYER_HEALTH_CONTACT_NATIVE_V1',player_force_before_common_body=True,actual_source_attack_index=9,contact_and_effects_completion_installed_by_fixture=True,production_globals_capture_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
