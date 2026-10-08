"""Checked stationary post-update binding, subservices and restoration proof.

Owner context is supplied by the fixture; actual traversal/Ack remains unproven.
"""
import argparse
import hashlib
import json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_gravity_hover_native import LUA as HOVER_LUA

LUA=HOVER_LUA.replace("set('SourceSelf4086_GlobalLow',v,4)","set('SourceSelf4086_GlobalLow',c.oldself,4)")
LUA=LUA.replace("set('SourceToss4086_Ready',0xb4e2)","set('SourceToss4086_Ready',0xb4e2);set('SourceCheckMove4086_Ready',0xb617);set('SourceCheckMove4086_Status',0)")
LUA=LUA.replace("set('SourceGravityIdle4086_Status',0)","set('SourceGravityIdle4086_Status',c.initial_gstatus)").replace("set('SourceCheckMove4086_Status',0)","set('SourceCheckMove4086_Status',c.initial_mstatus)")
LUA=LUA.replace("set('SourceCheckMove4086_Status',c.initial_mstatus)","set('SourceCheckMove4086_Status',c.initial_mstatus);set('SourcePostStationary4086_Ready',c.post_ready);set('SourcePostStationary4086_Status',c.post_status);set('SourcePostStationary4086_Slot',c.post_slot)")
LUA=LUA.replace("if c.fault==0 then for", "if true then for")
LUA=LUA.replace("{freeze+36,c.expected[2]}","{freeze+36,c.expected[2]},{side+24,c.expected[3]}")
LUA=LUA.replace("if faults[c.bad]then", "if c.bad=='trymove'then put(life+4,1,4)end\n if faults[c.bad]then")
LUA=LUA.replace("'|'..dw(freeze+36))", "'|'..dw(freeze+36)..'|'..dw(side+24)..'|'..word(sy.SourceCheckMove4086_Status))")


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 rows=[]
 for slot in (0,1,63,127):
  for oldself in (0,0x414000,0x414050,0x4167b0):
   for freeze in (0,1):
    for mark in (0,4,8,12):
     for time,toss in ((48,0),(48,49),(0xffffffff,0xffffffff)):
      et=toss if mark&8 or freeze or toss>time else(time+1)&0xffffffff
      en=0 if freeze or mark&4 else(time+1)&0xffffffff
      rows.append(dict(slot=slot,oldself=oldself,mark=mark,freeze=freeze,time=time,toss_time=toss,a=93*65536,base=0,gravity=0,altitude=0,nextmove=0,x=5242880,z=14417920,mx=0,mz=0,bad='',fault=0,world_state=2,expected=[et,mark|12,en],gstatus=2,mstatus=2))
 seed=dict(rows[0],mark=0,freeze=0,time=48,toss_time=0)
 for old in (0x414001,0x004000,0x410000,0x424000):
  rows.append(dict(seed,oldself=old,fault=1,expected=[0,0,0],gstatus=0,mstatus=0))
 rows.append(dict(seed,world_state=1,fault=1,expected=[0,0,0],gstatus=0,mstatus=0))
 rows.append(dict(seed,bad='noadjust',fault=1,expected=[0,0,0],gstatus=3,mstatus=0))
 rows.append(dict(seed,bad='trymove',mx=98304,fault=1,expected=[49,8,0],gstatus=2,mstatus=3))
 rows=[dict(c,initial_gstatus=0,initial_mstatus=0)for c in rows]
 for gs,ms in ((2,0),(0,2),(2,2)):
  rows.append(dict(seed,initial_gstatus=gs,initial_mstatus=ms))
 rows.append(dict(seed,initial_gstatus=3,initial_mstatus=0,fault=1,expected=[0,0,0],gstatus=3,mstatus=0))
 rows.append(dict(seed,initial_gstatus=0,initial_mstatus=3,fault=1,expected=[0,0,0],gstatus=0,mstatus=3))
 rows=[dict(c,post_ready=0xb61a,post_status=0,post_slot=c['slot'])for c in rows]
 for change in (dict(post_ready=0),dict(post_ready=0xb61b),dict(post_status=2),dict(post_status=3),dict(post_slot=1)):
  rows.append(dict(seed,initial_gstatus=0,initial_mstatus=0,post_ready=0xb61a,post_status=0,post_slot=0,fault=1,expected=[0,0,0],gstatus=0,mstatus=0)|change)
 reporter=Reporter('M4-POST-STATIONARY',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'SourcePostStationary4086_Execute','SourceGravityIdle4086_Ready',0xb619,[],LUA,reporter,batch_size=2)
 actual=[list(map(int,line.split('GRAVITYIDLE|',1)[1].split('|')))for line in log.splitlines()if'GRAVITYIDLE|'in line]
 expected=[[i,0,0,c['gstatus'],*c['expected'],c['mstatus']]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=rows[i],actual=v,expected=w)for i,(v,w)in enumerate(zip(actual,expected))if v!=w]
 reporter.check('explicit entity binding restores retained self for all slots, NULL/other identities and both subservice fault exits; clocks, marks, siblings and CPU',actual==expected)
 r=dict(schema='BYOR_4086_POST_STATIONARY_NATIVE_V1',status='PASS'if actual==expected else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures,rom_sha256=hashlib.sha256(raw).hexdigest(),world_traversal_and_ack_proven=False,zero_binding_and_falling_compiler_contract=True,active_gravity_or_landing_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
