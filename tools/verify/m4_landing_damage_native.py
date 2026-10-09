"""Native exact nonlethal NULL-handler landing branch against pinned source C."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_animation_physics_4086 import pack as pack_physics
from source_landing_plan_4086 import pack as pack_landing
from m4_post_air_pending_native import ASM
from m4_gravity_landing_commit_native import LUA as BASE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from source_entity_abi import PROPERTIES
assert PROPERTIES[3] == ('health', 1) and PROPERTIES[7] == ('maxhealth', 1)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
 p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--domain-only',action='store_true')
 p.add_argument('--kill-backend',action='store_true');p.add_argument('--retirement-authority',type=Path);a=p.parse_args()
 a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 ph=pack_physics(dict(animations=[dict(handle=1,antigrav=0,dropframe=-1,landframe=-1,land_entity_index=-1,frames=[dict(movement=dict(base=-1,y=0))])]))
 lp=pack_landing(dict(plans=[dict(handle=1,model_index=0,animation_bounce=0.,model_bounce=0,noquake=0)]))
 rows=[]
 for i,(c,result)in enumerate(zip(authority['inputs'],authority['actual'])):
  status=0
  if c['force']>0 and not c['dead']:
   if c['callback']:status=1
   elif c['factor']!=1. or c['health']>=0x800000 or c['force']>=0x800000:status=5
   elif result[0]<=0:status=4
   else:status=2
  killed=int(a.kill_backend and status==4)
  if killed:status=2
  pending=status in (1,4,5)
  rows.append(dict(slot=(0,63,127)[i%3],handle=1,a=0,base=0,altbase=0,vy=-65536,noadjust=1,hole=1,wall=1,platform=1,
   freeze=0,mark=0,time=48,toss=0,falling=1,hithead=1,gravity=0,minfall=-6*65536,maxtoss=100*65536,subject=0,
   damage=c['force'],dead=c['dead'],health=c['health'],callback=c['callback'],factor_bits=struct.unpack('<I',struct.pack('<f',c['factor']))[0],
   autoland=0,noquake=0,fault=0,bounced=0,pending=int(pending),status=status,authority_case=i,
   killed=killed,health_after=c['health']if pending else 0 if killed else result[0],damage_after=c['force']if pending else result[1],
   expected=[0,0,0,0,0,0 if pending else 49,0 if pending else 12,11]))
 seed=next(r for r in rows if r['health']==100 and r['damage']==7 and r['status']==2)
 for bad in ('factor_ready','factor_lease','factor_model','health_tag','health_reserved','damage_slot'):
  rows.append(dict(seed,bad=bad,fault=1,pending=1,status=3,health_after=100,damage_after=7,expected=[0,0,0,0,0,0,0,11]))
 if a.kill_backend:
  lethal=next(r for r in rows if r['health']==0 and r['damage']==1 and r['killed'])
  for bad in ('kill_ready','kill_sticky','retirement_ready','retirement_sticky','onkill','clear_entry','minion','live_count'):
   rows.append(dict(lethal,bad=bad,fault=1,pending=1,status=3,killed=0,health_after=0,damage_after=1,expected=[0,0,0,0,0,0,0,11]))
  for slot in (0,63,127):
   for bad in ('move_kill_ready','move_kill_status','move_kill_slot','move_kill_time','move_kill_token','move_ret_status','move_ret_slot','move_ret_victim'):
    rows.append(dict(lethal,slot=slot,bad=bad,afterkill_fault=1,fault=1,pending=1,status=2,expected=[0,0,0,0,0,49,8,11]))
 if a.domain_only:
  rows=[dict(seed,slot=slot,health=health,health_after=health,status=5,pending=1,damage_after=7,
    authority_case=None,domain_guard=True,expected=[0,0,0,0,0,0,0,11])
    for slot in (0,63,127)for health in(-8388609,-2147483648,8388608,2147483647)]
 lua=BASE_LUA[:BASE_LUA.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
 lua=lua.replace('TABLEBYTES',str(len(ph))).replace('PLANBYTES',str(len(lp))).replace('PLANCOUNT','1')
 lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',1)")
 install=r'''
 set('SourcePostAir4086_Ready',0xb628);set('SourcePostAir4086_State',0);set('SourcePostAir4086_Service',0);set('SourcePostAir4086_Slot',s)
 set('SourcePostStationary4086_Ready',0);set('SourceCheckMove4086_Ready',0xb617);set('SourceCheckMove4086_Status',0)
 set('SourceLandingDamage4086_Ready',0xb629);set('SourceLandingDamage4086_Status',0)
 set('SourceLandingKill4086_Ready',0);set('SourceLandingKill4086_Status',0)
 set('SourceFactors4086_Ready',0xb5f1);put(0x43b900+s*4,0);put(0x43b902+s*4,0xb5f1);put(0x432800+s*32,c.factor_bits,4)
 set('SourceSelf4086_GlobalLow',0,4);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Fault',0)
 put(aux,0,4);put(aux+4,0,4);put(aux+16,0);put(life+8,0,4);put(life+4,c.callback,4);put(core+72,0,4)
 put(view+48,2);put(view+50,0);put(view+52,10*65536,4);put(view+56,2);put(view+58,0);put(view+60,20*65536,4);put(side+24,48,4)
 put(view+32,1);put(view+34,0);put(view+36,c.health,4);put(view+64,1);put(view+66,0);put(view+68,123456,4)
 if c.bad=='factor_ready'then set('SourceFactors4086_Ready',0)
 elseif c.bad=='factor_lease'then put(0x43b902+s*4,0)
 elseif c.bad=='factor_model'then put(0x43b900+s*4,1)
 elseif c.bad=='health_tag'then put(view+32,2)
 elseif c.bad=='health_reserved'then put(view+34,1)end
'''
 lua=lua.replace(' before={};for',install+' before={};for')
 if a.kill_backend:
  retirement=json.loads(a.retirement_authority.read_text());assert retirement['status']=='PASS'
  kill_install=r'''
 set('SourceLandingKill4086_Ready',0xb62a);set('SourceLandingKill4086_Status',0)
 set('SourceRetirement4086_Ready',0xb4f8);set('SourceRetirement4086_Status',0)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128)
 set('SourceIdle4086_Ready',0xb4f3);set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 for j=0,127 do if j~=s then put(0x414004+j*80,0,4)end end
 for j=0,8191 do emu.write(0x409000+j,0,mt)end
 for j=0,24575 do emu.write(0x418800+j,0,mt)end
 for j=0,31 do emu.write(0x43fd80+j,0,mt)end
 put(0x43fd80,1,4);put(core+80,0,4);put(core+84,0,4);put(0x43eb00+s*32+28,0,4)
 put(0x409000+s*64+44,7,4)
 put(0x418800,view,4);put(0x418804,1);put(0x418808,1,4);put(0x41880c,123456,4)
 set('SourceWorldTick4086_Index',0)
 if c.bad=='kill_ready'then set('SourceLandingKill4086_Ready',0xb62b)
 elseif c.bad=='kill_sticky'then set('SourceLandingKill4086_Status',3)
 elseif c.bad=='retirement_ready'then set('SourceRetirement4086_Ready',0)
 elseif c.bad=='retirement_sticky'then set('SourceRetirement4086_Status',3)
 elseif c.bad=='onkill'then put(0x409000+s*64+52,1,4)
 elseif c.bad=='clear_entry'then put(0x409000+s*64+48,1,4)
 elseif c.bad=='minion'then put(0x409000+s*64+4,view,4);put(0x409000+s*64+36,1,4)
 elseif c.bad=='live_count'then put(0x43fd80,2,4)end
'''
  lua=lua.replace(' before={};for',kill_install+' before={};for')
  lua=lua.replace('{life-8,96}', '{life-8,96},{0x409000,8192},{0x43fd80,32},{0x418800,24576}')
  lua=lua.replace(' local n=0;for a,v in pairs(before)',r'''
 if c.killed==1 then
  for _,r in ipairs({{view+4,0,4},{0x409000+c.slot*64+44,0,4},{0x43fd80,0,4},{0x418808,0,8}})do for i=0,r[3]-1 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 end
 local n=0;for a,v in pairs(before)''')
  lua=lua.replace("emu.log('LANDDAMAGE|'", "emu.log('LANDDAMAGE|'")
 lua=lua.replace(' local n=0;for a,v in pairs(before)',r'''
 for _,r in ipairs({{view+36,c.health_after},{phy+12,c.damage_after},{side+24,c.pending==0 and 49 or 48}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)''')
 lua=lua.replace("emu.log('GRAVITYCOMMIT|'","emu.log('LANDDAMAGE|'")
 lua=lua.replace("word(sy.SourceGravityLanding4086_Service))", "word(sy.SourceGravityLanding4086_Service)..'|'..word(sy.SourcePostAir4086_State)..'|'..word(sy.SourceCheckMove4086_Status)..'|'..word(sy.SourceLandingDamage4086_Status)..'|'..word(sy.SourceSelf4086_GlobalLow)..'|'..word(sy.SourceSelf4086_GlobalHigh))")
 # A stale damage slot is injected at the actual leaf entry, after POST owns it.
 lua+=r'''
 emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];if c.bad=='damage_slot'then set('SourceLandingDamage4086_Slot',128)elseif c.bad=='kill_sticky'then set('SourceLandingKill4086_Status',3)end end,emu.callbackType.exec,DAMAGE,DAMAGE,emu.cpuType.snes,mt)
'''
 if a.kill_backend:
  lua+=r'''
 emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local fields={move_kill_ready={'SourceLandingKill4086_Ready',0xb62b},move_kill_status={'SourceLandingKill4086_Status',3},move_kill_slot={'SourceLandingKill4086_Slot',128},move_kill_time={'SourceLandingKill4086_Time',47},move_kill_token={'SourceLandingKill4086_Token',0},move_ret_status={'SourceRetirement4086_Status',3},move_ret_slot={'SourceRetirement4086_Slot',128},move_ret_victim={'SourceRetirement4086_Victim',0}}
 if fields[c.bad]then local r=fields[c.bad];set(r[1],r[2])end
 end,emu.callbackType.exec,MOVE,MOVE,emu.cpuType.snes,mt)
'''
 if a.kill_backend:
  lua+=r'''
 emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local view=0x414000+c.slot*80
 emu.log('LANDKILLWORLD|'..word(INDEX)..'|'..word(view+4)..'|'..word(view+68)..'|'..word(sy.SourceLandingKill4086_Status)..'|'..word(sy.SourceRetirement4086_Status)..'|'..word(sy.SourceWorldTick4086_Pending)..'|'..word(sy.SourceWorldTick4086_Index))
 end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 asm=ASM
 if a.kill_backend:
  asm=asm.replace(' jsl POSTCHECK\n bcs PostPendingFixture_Bad',' jsl POSTCHECK\n bcs PostPendingFixture_Bad\n lda #11\n jsl WORLDACK\n bcs PostPendingFixture_Bad')
 reporter=Reporter('M4-LANDING-DAMAGE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'PostPendingFixture_Run','SourcePostAir4086_Ready',0xb628,
  [(58,0,ph),(59,0,lp)],lua,reporter,append=asm,
  bindings=dict(POSTBEGIN='SourcePostAir4086_Begin',POSTCONTINUE='SourcePostAir4086_Continue',POSTCHECK='SourcePostAir4086_CheckAck',DAMAGE='SourceLandingDamage4086_Execute',WORLDACK='SourceWorldTick4086_Ack',MOVE='SourceCheckMove4086_Execute'),frame_limit=4000,link_pcm=False)
 actual=[list(map(int,l.split('LANDDAMAGE|',1)[1].split('|')))for l in log.splitlines()if'LANDDAMAGE|'in l]
 expected=[]
 for i,r in enumerate(rows):
  fault=r['fault'];pending=r['pending'];token=0x414000+r['slot']*80 if pending and not fault else 0
  expected.append([i,0,0,3 if fault else 1 if pending else 2,1 if pending else 2,2 if pending else 0,
   3 if fault else 1 if pending else 2,0 if pending else 2,r['status'],token&65535,token>>16])
  if r.get('afterkill_fault'):expected[-1]=[i,0,0,2,2,0,3,3,2,0,0]
 reporter.check('exact source direct landing health/force; required callbacks and arithmetic stay pending; stale factor/health/slot guards retain actor bytes',actual==expected)
 world=[];world_expected=[]
 if a.kill_backend:
  world=[list(map(int,l.split('LANDKILLWORLD|',1)[1].split('|')))for l in log.splitlines()if'LANDKILLWORLD|'in l]
  for i,r in enumerate(rows):
   world_expected.append([i,0 if r['killed']else 1,123456&65535,3 if r.get('bad')in('kill_sticky','retirement_ready','retirement_sticky','onkill','clear_entry','minion','live_count','move_kill_status')else 2 if r['killed']else 0,
    3 if r.get('bad')in('retirement_ready','retirement_sticky','onkill','clear_entry','minion','live_count','move_ret_status')else 2 if r['killed']else 0,r['pending'],0 if r['pending']else 1])
  reporter.check('real retired existence, maxhealth preservation and completed world acknowledgement; retirement prerequisites reject',world==world_expected)
 ok=actual==expected and world==world_expected
 report=dict(schema='BYOR_4086_LANDING_DAMAGE_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,
  actual=actual,expected=expected,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
  native_null_handler_unit_defense_nonlethal_damage=actual==expected,callback_and_other_arithmetic_backend_proven=False,
  exact_binary32_equivalent_domain='positive integer health and force below 2^23; unit defense; positive resulting health',
  world_actual=world,world_expected=world_expected,native_lethal_no_event_retirement=a.kill_backend and ok,
  retirement_authority_sha256=hashlib.sha256(a.retirement_authority.read_bytes()).hexdigest()if a.kill_backend else None,
  source_kill_current_health_zero_exists_zero_count_and_scripts=True if a.kill_backend and actual==expected else False,
  held_retired_victim_real_check_move=a.kill_backend and actual==expected,
  full_dynamic_world_traversal_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
