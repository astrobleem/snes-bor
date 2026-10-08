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
 p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
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
  pending=status in (1,4,5)
  rows.append(dict(slot=(0,63,127)[i%3],handle=1,a=0,base=0,altbase=0,vy=-65536,noadjust=1,hole=1,wall=1,platform=1,
   freeze=0,mark=0,time=48,toss=0,falling=1,hithead=1,gravity=0,minfall=-6*65536,maxtoss=100*65536,subject=0,
   damage=c['force'],dead=c['dead'],health=c['health'],callback=c['callback'],factor_bits=struct.unpack('<I',struct.pack('<f',c['factor']))[0],
   autoland=0,noquake=0,fault=0,bounced=0,pending=int(pending),status=status,authority_case=i,
   health_after=c['health']if pending else result[0],damage_after=c['force']if pending else result[1],
   expected=[0,0,0,0,0,0 if pending else 49,0 if pending else 12,11]))
 seed=next(r for r in rows if r['health']==100 and r['damage']==7 and r['status']==2)
 for bad in ('factor_ready','factor_lease','factor_model','health_tag','health_reserved','damage_slot'):
  rows.append(dict(seed,bad=bad,fault=1,pending=1,status=3,health_after=100,damage_after=7,expected=[0,0,0,0,0,0,0,11]))
 lua=BASE_LUA[:BASE_LUA.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
 lua=lua.replace('TABLEBYTES',str(len(ph))).replace('PLANBYTES',str(len(lp))).replace('PLANCOUNT','1')
 lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',1)")
 install=r'''
 set('SourcePostAir4086_Ready',0xb628);set('SourcePostAir4086_State',0);set('SourcePostAir4086_Service',0);set('SourcePostAir4086_Slot',s)
 set('SourcePostStationary4086_Ready',0);set('SourceCheckMove4086_Ready',0xb617);set('SourceCheckMove4086_Status',0)
 set('SourceLandingDamage4086_Ready',0xb629);set('SourceLandingDamage4086_Status',0)
 set('SourceFactors4086_Ready',0xb5f1);put(0x43b900+s*4,0);put(0x43b902+s*4,0xb5f1);put(0x432800+s*32,c.factor_bits,4)
 set('SourceSelf4086_GlobalLow',0,4);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Fault',0)
 put(aux,0,4);put(aux+4,0,4);put(aux+16,0);put(life+4,0,4);put(life+8,c.callback,4);put(core+72,0,4)
 put(view+48,2);put(view+50,0);put(view+52,10*65536,4);put(view+56,2);put(view+58,0);put(view+60,20*65536,4);put(side+24,48,4)
 put(view+32,1);put(view+34,0);put(view+36,c.health,4);put(view+64,1);put(view+66,0);put(view+68,123456,4)
 if c.bad=='factor_ready'then set('SourceFactors4086_Ready',0)
 elseif c.bad=='factor_lease'then put(0x43b902+s*4,0)
 elseif c.bad=='factor_model'then put(0x43b900+s*4,1)
 elseif c.bad=='health_tag'then put(view+32,2)
 elseif c.bad=='health_reserved'then put(view+34,1)end
'''
 lua=lua.replace(' before={};for',install+' before={};for')
 lua=lua.replace(' local n=0;for a,v in pairs(before)',r'''
 for _,r in ipairs({{view+36,c.health_after},{phy+12,c.damage_after},{side+24,c.pending==0 and 49 or 48}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)''')
 lua=lua.replace("emu.log('GRAVITYCOMMIT|'","emu.log('LANDDAMAGE|'")
 lua=lua.replace("word(sy.SourceGravityLanding4086_Service))", "word(sy.SourceGravityLanding4086_Service)..'|'..word(sy.SourcePostAir4086_State)..'|'..word(sy.SourceCheckMove4086_Status)..'|'..word(sy.SourceLandingDamage4086_Status)..'|'..word(sy.SourceSelf4086_GlobalLow)..'|'..word(sy.SourceSelf4086_GlobalHigh))")
 # A stale damage slot is injected at the actual leaf entry, after POST owns it.
 lua+=r'''
 emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];if c.bad=='damage_slot'then set('SourceLandingDamage4086_Slot',128)end end,emu.callbackType.exec,DAMAGE,DAMAGE,emu.cpuType.snes,mt)
'''
 reporter=Reporter('M4-LANDING-DAMAGE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'PostPendingFixture_Run','SourcePostAir4086_Ready',0xb628,
  [(58,0,ph),(59,0,lp)],lua,reporter,append=ASM,
  bindings=dict(POSTBEGIN='SourcePostAir4086_Begin',POSTCONTINUE='SourcePostAir4086_Continue',POSTCHECK='SourcePostAir4086_CheckAck',DAMAGE='SourceLandingDamage4086_Execute'))
 actual=[list(map(int,l.split('LANDDAMAGE|',1)[1].split('|')))for l in log.splitlines()if'LANDDAMAGE|'in l]
 expected=[]
 for i,r in enumerate(rows):
  fault=r['fault'];pending=r['pending'];token=0x414000+r['slot']*80 if pending and not fault else 0
  expected.append([i,0,0,3 if fault else 1 if pending else 2,1 if pending else 2,2 if pending else 0,
   3 if fault else 1 if pending else 2,0 if pending else 2,r['status'],token&65535,token>>16])
 reporter.check('exact source nonlethal health/force; callback, lethal and other arithmetic stay pending; stale factor/health/slot guards retain actor bytes',actual==expected)
 report=dict(schema='BYOR_4086_LANDING_DAMAGE_NATIVE_V1',status='PASS'if actual==expected else'FAIL',cases=len(rows),inputs=rows,
  actual=actual,expected=expected,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
  native_null_handler_unit_defense_nonlethal_damage=actual==expected,callback_and_kill_and_other_arithmetic_backend_proven=False,
  exact_binary32_equivalent_domain='positive integer health and force below 2^23; unit defense; positive resulting health',
  full_dynamic_world_traversal_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
