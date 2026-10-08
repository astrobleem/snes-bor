"""Actual entity toss numerical stores, zero no-op and atomic overflow rejection."""
import argparse
import hashlib
import json
from pathlib import Path
from m4_adjust_base_empty_native import LUA as BASE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=BASE_LUA.replace(" before={};for",r'''
 set('SourceEntityToss4086_Ready',c.ready or 0xb624);set('SourceEntityToss4086_Status',c.status or 0)
 set('SourceEntityToss4086_Slot',c.request_slot or s);set('SourceEntityToss4086_Lift',c.lift,4)
 set('SourceToss4086_Ready',c.toss_ready or 0xb4e2);set('VmSourceWorld_Time',c.time,4)
 put(0x41f300+s*4,c.toss,4)
 if c.toss_bad=='world'then set('VmSourceWorld_Ready',0)elseif c.toss_bad=='atag'then put(view+8,1)
 elseif c.toss_bad=='pointer'then put(view,view+80,4)elseif c.toss_bad=='dead'then put(view+4,0,4)end
 before={};for''').replace('{life-8,96}','{life-8,96},{0x41f300+s*4-8,20}')
start=LUA.index(' local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64',LUA.index('AFTER,AFTER'))
end=LUA.index('end,emu.callbackType.exec,RESULT',start)
LUA=LUA[:start]+r'''
 local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64;local view=0x414000+c.slot*80
 if c.fault==0 and c.lift~=0 then for _,r in ipairs({{view+12,c.a+32768},{side+44,c.lift},{0x41f300+c.slot*4,(c.time+1)&0xffffffff}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('ENTITYTOSS|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceEntityToss4086_Status))
'''+LUA[end:]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    seed=dict(slot=0,handle=1,a=0,base=0,altbase=0,vy=-65536,noadjust=1,hole=1,wall=1,platform=1,fault=0,time=48,toss=123,lift=65536)
    rows=[]
    for slot in (0,63,127):
        for altitude in (-0x80000000,-65536,0,6094848,0x7fff7fff):
            for lift in (-6*65536,-1,0,1,5*65536):
                for time in (48,0xffffffff):rows.append(dict(seed,slot=slot,a=altitude,lift=lift,time=time))
    for change in (dict(ready=1),dict(status=3),dict(toss_ready=1),dict(request_slot=128),dict(toss_bad='world'),
                   dict(toss_bad='atag'),dict(toss_bad='pointer'),dict(toss_bad='dead'),dict(a=0x7fff8000),dict(a=0x7fffffff)):
        rows.append(dict(seed,**change,fault=1))
    # Zero lift executes before any entity dereference in literal pinned toss.
    rows.append(dict(seed,lift=0,request_slot=128,toss_ready=1,toss_bad='world'))
    reporter=Reporter('M4-ENTITY-TOSS',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceEntityToss4086_Execute','SourceEntityToss4086_Ready',0xb624,
                        [],LUA.replace('TABLEBYTES','16'),reporter,batch_size=8)
    actual=[list(map(int,l.split('ENTITYTOSS|',1)[1].split('|')))for l in log.splitlines()if 'ENTITYTOSS|'in l]
    wanted=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)]
    reporter.check('native entity toss preserves all unrelated actor/physics rows and CPU; zero no-op; timer wrap; atomic overflow',actual==wanted)
    report=dict(schema='BYOR_4086_ENTITY_TOSS_NATIVE_V1',status='PASS'if actual==wanted else'FAIL',cases=len(rows),inputs=rows,
                actual=actual,expected=wanted,rom_sha256=hashlib.sha256(raw).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16',
                native_bounce_landing_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
