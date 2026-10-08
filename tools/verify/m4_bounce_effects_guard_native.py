"""Bounce effect admission and pending/fault ownership, without host completion."""
import argparse
import hashlib
import json
from pathlib import Path
from source_animation_physics_4086 import pack as pack_physics
from source_landing_plan_4086 import pack as pack_landing
from m4_post_air_pending_native import ASM
from m4_gravity_landing_commit_native import LUA as BASE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ph=pack_physics(dict(animations=[dict(handle=1,antigrav=0,dropframe=-1,landframe=-1,land_entity_index=-1,frames=[dict(movement=dict(base=-1,y=0))])]))
 lp=pack_landing(dict(plans=[dict(handle=1,model_index=0,animation_bounce=4.,model_bounce=1,noquake=0)]))
 rows=[]
 for slot in(0,63,127):
  for bad in('', 'busy', 'namespace', 'sample', 'bounce_ready', 'controller', 'state', 'bounce_slot', 'time', 'velocity_ready', 'velocity_status', 'velocity_slot'):
   fault=int(bad not in('', 'busy'));pending=int(bad!='')
   rows.append(dict(slot=slot,handle=1,a=0,base=0,altbase=0,vy=-6*65536,noadjust=1,hole=1,wall=1,platform=1,freeze=0,mark=0,time=48,toss=0,falling=1,hithead=1,gravity=0,minfall=-6*65536,maxtoss=100*65536,subject=0,damage=0,autoland=0,noquake=0,fault=fault,bounced=1,bad=bad,pending=pending,
    expected=[32768,98304,24576,-12288,0,49,0 if pending else 12,4]))
 lua=BASE_LUA[:BASE_LUA.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
 lua=lua.replace('TABLEBYTES',str(len(ph))).replace('PLANBYTES',str(len(lp))).replace('PLANCOUNT','1').replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',1)")
 install=r'''
 set('SourcePostAir4086_Ready',0xb628);set('SourcePostAir4086_State',0);set('SourcePostAir4086_Slot',s)
 set('SourcePostStationary4086_Ready',0);set('SourceCheckMove4086_Ready',0xb617);set('SourceCheckMove4086_Status',0)
 set('SourceBounceEffects4086_Ready',c.bad=='bounce_ready'and 0xb62e or 0xb62c);set('SourceBounceEffects4086_State',0)
 set('SourceBounceEffects4086_NoRumbleReady',c.bad=='controller'and 0 or 0xb62d)
 set('SourceBounceEffects4086_SampleFall',c.bad=='busy'or c.bad=='namespace'and 21 or c.bad=='sample'and 65534 or 65535)
 if c.bad=='busy'then set('SourceBounceEffects4086_SampleFall',21)end
 set('SourceSelf4086_GlobalLow',0,4);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Fault',0)
 put(aux,0,4);put(aux+4,0,4);put(aux+16,0);put(life+4,0,4);put(core+72,0,4)
 put(view+48,2);put(view+50,0);put(view+52,10*65536,4);put(view+56,2);put(view+58,0);put(view+60,20*65536,4);put(side+24,48,4)
 put(0x7e28f0,0);put(0x7e28f2,7);put(ACTIVE,c.bad=='busy'and 1 or 0,1)
'''
 # Avoid Lua boolean-to-number precedence in the source-index selection.
 install=install.replace("c.bad=='busy'or c.bad=='namespace'and 21", "(c.bad=='busy'or c.bad=='namespace')and 21")
 lua=lua.replace(' before={};for',install+' before={};for')
 lua=lua.replace(' local n=0;for a,v in pairs(before)',r'''
 if c.pending==0 then for i=0,3 do before[side+24+i]=(49>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)''')
 lua=lua.replace("emu.log('GRAVITYCOMMIT|'","emu.log('BOUNCEEFFECT|'")
 lua=lua.replace("word(sy.SourceGravityLanding4086_Service))", "word(sy.SourceGravityLanding4086_Service)..'|'..word(sy.SourcePostAir4086_State)..'|'..word(sy.SourceCheckMove4086_Status)..'|'..word(sy.SourceBounceEffects4086_State)..'|'..word(sy.SourceSelf4086_GlobalLow)..'|'..word(sy.SourceSelf4086_GlobalHigh)..'|'..word(0x7e28f0)..'|'..word(0x7e28f2))")
 lua+=r'''
 emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.bad=='state'then set('SourceBounceEffects4086_State',3)
 elseif c.bad=='bounce_slot'then set('SourceBounceEffects4086_State',1);set('SourceBounceEffects4086_Slot',128);set('SourceBounceEffects4086_Time',48,4)
 elseif c.bad=='time'then set('SourceBounceEffects4086_State',1);set('SourceBounceEffects4086_Slot',c.slot);set('SourceBounceEffects4086_Time',47,4)
 elseif c.bad=='velocity_ready'then set('SourceLandingVelocity4086_Ready',0)
 elseif c.bad=='velocity_status'then set('SourceLandingVelocity4086_Status',2)
 elseif c.bad=='velocity_slot'then set('SourceLandingVelocity4086_Slot',128)end
 end,emu.callbackType.exec,EFFECT,EFFECT,emu.cpuType.snes,mt)
'''
 reporter=Reporter('M4-BOUNCE-EFFECT-GUARDS',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'PostPendingFixture_Run','SourcePostAir4086_Ready',0xb628,[(58,0,ph),(59,0,lp)],lua,reporter,append=ASM,
  bindings=dict(POSTBEGIN='SourcePostAir4086_Begin',POSTCONTINUE='SourcePostAir4086_Continue',POSTCHECK='SourcePostAir4086_CheckAck',EFFECT='SourceBounceEffects4086_Execute',ACTIVE='AudioSemantic_FootDieStreamActive'))
 actual=[list(map(int,l.split('BOUNCEEFFECT|',1)[1].split('|')))for l in log.splitlines()if'BOUNCEEFFECT|'in l]
 expected=[]
 for i,c in enumerate(rows):
  pending=c['pending'];fault=c['fault'];token=0x414000+c['slot']*80 if pending and not fault else 0
  expected.append([i,0,0,3 if fault else 1 if pending else 2,1 if pending else 2,3 if pending else 0,3 if fault else 1 if pending else 2,0 if pending else 2,
   0 if c['bad']=='bounce_ready'else 3 if fault else 1 if pending else 2,token&65535,token>>16,3 if c['bad']=='busy'else 2 if c['bad']=='namespace'else 0,7])
 reporter.check('missing source sample completes; busy retains real POST/self ownership; invalid sound/leases/time/slot reject; no stale identity or early movement',actual==expected)
 report=dict(schema='BYOR_4086_BOUNCE_EFFECT_GUARD_NATIVE_V1',status='PASS'if actual==expected else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),busy_condition_instrumented=True,native_audio_playback_proven=False,missing_sample_branch_controlled=True,full_dynamic_world_traversal_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
