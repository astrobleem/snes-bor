"""Actual POST begins/resumes required landing services without early world Ack."""
import argparse
import hashlib
import json
from pathlib import Path
from source_animation_physics_4086 import pack as pack_physics
from source_landing_plan_4086 import pack as pack_plans
from m4_gravity_landing_commit_native import LUA as BASE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''PostPendingFixture_Run:
.a16
.i16
 php
 rep #$38
 jsl POSTBEGIN
 bcs PostPendingFixture_Bad
 cmp #0
 beq PostPendingFixture_Complete
 jsl POSTCONTINUE
 bcs PostPendingFixture_Bad
 jsl POSTCONTINUE
 bcs PostPendingFixture_Bad
 jsl POSTCHECK
 bcc PostPendingFixture_Bad
 bra PostPendingFixture_Good
PostPendingFixture_Complete:
.a16
.i16
 jsl POSTCHECK
 bcs PostPendingFixture_Bad
PostPendingFixture_Good:
.a16
.i16
 plp
 clc
 rtl
PostPendingFixture_Bad:
.a16
.i16
 plp
 sec
 rtl
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    ph=pack_physics(dict(animations=[dict(handle=1,antigrav=0,dropframe=-1,landframe=-1,land_entity_index=-1,
        frames=[dict(movement=dict(base=-1,y=0))])]))
    lp=pack_plans(dict(plans=[dict(handle=1,model_index=0,animation_bounce=4.,model_bounce=1,noquake=0)]))
    rows=[]
    for slot in (0,63,127):
        for oldself in (0,0x414000,0x4167b0):
            for vy,damage,autoland in ((0,0,0),(-65536,0,0),(-2*65536,0,0),(-2*65536,-2,0),(-2*65536,-1,1),(-65536,7,0)):
                bounce=vy==-2*65536 and damage==0;pending=bounce or damage>0
                rows.append(dict(slot=slot,oldself=oldself,handle=1,a=0,base=0,altbase=0,vy=vy,noadjust=1,hole=1,
                    wall=1,platform=1,freeze=0,mark=0,time=48,toss=0,falling=1,hithead=1,gravity=0,
                    minfall=-6*65536,maxtoss=100*65536,subject=0,damage=damage,autoland=autoland,noquake=0,
                    fault=0,bounced=int(bounce),pending=int(pending),
                    expected=[32768 if bounce else 0,32768 if bounce else 0,24576 if bounce else 0,
                              -12288 if bounce else 0,0,49 if bounce or not pending else 0,0 if pending else 12,4 if bounce else 11]))
    lua=BASE_LUA[:BASE_LUA.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
    lua=lua.replace('TABLEBYTES',str(len(ph))).replace('PLANBYTES',str(len(lp))).replace('PLANCOUNT','1')
    lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',1)")
    install=r'''
 set('SourcePostAir4086_Ready',0xb628);set('SourcePostAir4086_State',0);set('SourcePostAir4086_Service',0);set('SourcePostAir4086_Slot',s)
 set('SourcePostStationary4086_Ready',0);set('SourceCheckMove4086_Ready',0xb617);set('SourceCheckMove4086_Status',0)
 set('SourceSelf4086_GlobalLow',c.oldself,4);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Fault',0)
 put(aux,98304,4);put(aux+4,-49152,4);put(aux+16,0);put(life+4,0,4);put(core+72,32,4)
 put(view+48,2);put(view+50,0);put(view+52,10*65536,4);put(view+56,2);put(view+58,0);put(view+60,20*65536,4);put(side+24,48,4)
'''
    lua=lua.replace(' before={};for',install+' before={};for')
    lua=lua.replace(' local n=0;for a,v in pairs(before)',r'''
 if c.pending==0 then
  for _,r in ipairs({{view+52,10*65536+98304},{view+60,20*65536-49152},{side+24,49}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 end
 local n=0;for a,v in pairs(before)''')
    lua=lua.replace("emu.log('GRAVITYCOMMIT|'", "emu.log('POSTPENDING|'")
    lua=lua.replace("word(sy.SourceGravityLanding4086_Service))", "word(sy.SourceGravityLanding4086_Service)..'|'..word(sy.SourcePostAir4086_State)..'|'..word(sy.SourceCheckMove4086_Status)..'|'..word(sy.SourceSelf4086_GlobalLow)..'|'..word(sy.SourceSelf4086_GlobalHigh)..'|'..word(sy.SourceWorldTick4086_Pending))")
    reporter=Reporter('M4-POST-AIR-PENDING',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'PostPendingFixture_Run','SourcePostAir4086_Ready',0xb628,
        [(58,0,ph),(59,0,lp)],lua,reporter,append=ASM,
        bindings=dict(POSTBEGIN='SourcePostAir4086_Begin',POSTCONTINUE='SourcePostAir4086_Continue',POSTCHECK='SourcePostAir4086_CheckAck'))
    actual=[list(map(int,l.split('POSTPENDING|',1)[1].split('|')))for l in log.splitlines()if 'POSTPENDING|'in l]
    expected=[]
    for i,r in enumerate(rows):
        token=0x414000+r['slot']*80 if r['pending']else r['oldself']
        expected.append([i,0,0,1 if r['pending']else 2,1 if r['pending']else 2,
                         3 if r['bounced']else 2 if r['damage']>0 else 0,1 if r['pending']else 2,
                         0 if r['pending']else 2,token&65535,token>>16,1])
    reporter.check('repeated real resumes retain bounce/damage, source self and world pending; complete numeric paths perform movement and restore parent',actual==expected)
    report=dict(schema='BYOR_4086_POST_AIR_PENDING_NATIVE_V1',status='PASS'if actual==expected else'FAIL',
        cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),
        actual_post_begin_and_resume=True,bounce_audio_rumble_and_positive_damage_backend_proven=False,
        native_world_ack_gate=True,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
