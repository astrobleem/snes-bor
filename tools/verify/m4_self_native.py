"""Engine-global self lease, pointer restoration and terminal effect; locals preserved."""
import argparse, hashlib, json
from pathlib import Path
from _harness import Reporter
from _source_leaf_fixture import run_fixture


def cases(restore):
    rows=[]
    for count in (1,2,128):
        slots=[s for s in (0,1,127) if s<count]
        for slot in slots:
            for old in [0]+[0x4000+80*s for s in slots]:
                for mode in (0,1):rows.append(dict(count=count,slot=slot,old=old,mode=mode,bad='',fault=0))
    base=dict(count=128,slot=1,old=0x4000,mode=0,bad='',fault=0)
    for mode in (0,1):
        for bad in ('ready','world','pool','count_zero','count_high','misaligned','old_bounds'):
            rows.append(dict(base,mode=mode,bad=bad,fault=1))
        rows.append(dict(base,mode=mode,bad='disabled',fault=int(restore and mode==1)))
    for bad in ('high','mapped_null','slot','active','sticky'):
        rows.append(dict(base,bad=bad,fault=1))
    for bad in ('leave_active','sticky'):
        rows.append(dict(base,mode=1,bad=bad,fault=1))
    if restore:
        for bad in ('prefix','prefix_state','prefix_pending','cursor','cursor_state','opcode','cursor_slot','cursor_handle','cursor_frame','cursor_index','cursor_count','inactive'):
            rows.append(dict(base,mode=1,bad=bad,fault=1))
    return rows


LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0;local start=0;local expected={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(p,k,v)put(sy[p..'4086_'..k],v)end
local ranges={{0x7ff610,32},{0x7ffd1a,6},{0x7ffe38,4},{0x414000,10240}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,(i*37+17)&255,mt)end end
 set('SourceSelf','Ready',0xb4f6);set('SourceSelf','OldLow',c.mode==1 and c.old or 0x7777);set('SourceSelf','Active',c.mode);set('SourceSelf','Fault',0)
 set('SourceSelf','GlobalLow',c.mode==0 and c.old or 0x4000+80*c.slot);set('SourceSelf','GlobalHigh',c.mode==0 and (c.old==0 and 0 or 0x41) or 0x41)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,c.count);set('SourceUpdateFrame','Slot',c.slot)
 set('SourceUpdateFrame','Ready',0xb4e3);set('SourceUpdateFrame','State',1);set('SourceUpdateFrame','Pending',2);set('SourceUpdateFrame','Handle',1);set('SourceUpdateFrame','Request',0)
 set('SourceFrameEffectPlan','Ready',0xb4f2);set('SourceFrameEffectPlan','State',1);set('SourceFrameEffectPlan','Service',23);set('SourceFrameEffectPlan','Slot',c.slot);set('SourceFrameEffectPlan','Handle',1);set('SourceFrameEffectPlan','Frame',0);set('SourceFrameEffectPlan','Index',0);set('SourceFrameEffectPlan','Count',1)
 put(EXPECTFAULT,c.fault);put(MODE,c.mode)
 if c.bad=='ready'then set('SourceSelf','Ready',1)
 elseif c.bad=='disabled'then set('SourceSelf','Ready',0)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='count_zero'then put(sy.VmSourceWorld_Count,0)
 elseif c.bad=='count_high'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='misaligned'then set('SourceSelf',c.mode==0 and 'GlobalLow' or 'OldLow',0x4002)
 elseif c.bad=='old_bounds'then set('SourceSelf',c.mode==0 and 'GlobalLow' or 'OldLow',0x6800)
 elseif c.bad=='high'then set('SourceSelf','GlobalHigh',0x42)
 elseif c.bad=='mapped_null'then set('SourceSelf','GlobalLow',0);set('SourceSelf','GlobalHigh',0x41)
 elseif c.bad=='slot'then set('SourceUpdateFrame','Slot',128)
 elseif c.bad=='active'then set('SourceSelf','Active',1)
 elseif c.bad=='leave_active'then set('SourceSelf','Active',2)
 elseif c.bad=='sticky'then set('SourceSelf','Fault',1)
 elseif c.bad=='prefix'then set('SourceUpdateFrame','Ready',0)
 elseif c.bad=='prefix_state'then set('SourceUpdateFrame','State',2)
 elseif c.bad=='prefix_pending'then set('SourceUpdateFrame','Pending',1)
 elseif c.bad=='cursor'then set('SourceFrameEffectPlan','Ready',0)
 elseif c.bad=='cursor_state'then set('SourceFrameEffectPlan','State',2)
 elseif c.bad=='opcode'then set('SourceFrameEffectPlan','Service',17)
 elseif c.bad=='cursor_slot'then set('SourceFrameEffectPlan','Slot',2)
 elseif c.bad=='cursor_handle'then set('SourceFrameEffectPlan','Handle',2)
 elseif c.bad=='cursor_frame'then set('SourceFrameEffectPlan','Frame',1)
 elseif c.bad=='cursor_index'then set('SourceFrameEffectPlan','Index',65535)
 elseif c.bad=='cursor_count'then set('SourceFrameEffectPlan','Count',0)
 elseif c.bad=='inactive'then set('SourceSelf','Active',0)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
local function capture()local s=emu.getState();start=s.masterClock;ctx=0;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end end
emu.addMemoryCallback(capture,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,SECONDARY,SECONDARY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('SELFCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local function expect(k,n)local a=sy['SourceSelf4086_'..k];before[a]=n&255;before[a+1]=(n>>8)&255 end
 if c.fault==1 then expect('Fault',1)
 elseif c.bad~='disabled'then
  if c.mode==0 then expect('OldLow',c.old);expect('Active',1);expect('GlobalLow',0x4000+80*c.slot);expect('GlobalHigh',0x41)
  else expect('Active',0);expect('GlobalLow',c.old);expect('GlobalHigh',c.old==0 and 0 or 0x41)end
 end
 local mismatch=0;for addr,v in pairs(before)do if emu.read(addr,mt)~=v then mismatch=mismatch+1 end end
 local terminal=0;if restore and c.mode==1 then
  if word(sy.SourceFrameEffectPlan4086_State)~=(c.fault==1 and 3 or 2)then terminal=1 end
  if c.fault==0 and (word(sy.SourceFrameEffectPlan4086_Service)~=0 or word(sy.SourceFrameEffectPlan4086_Acknowledged)~=0)then terminal=1 end
 end
 emu.log('SELFRESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..terminal)
 -- Isolate the self ownership guard from separately verified frame owners.
 for _,p in ipairs({'SourceUpdateFrame','SourceFrameEffectPlan','SourceAnimationInit','SourceModelAnimation','SourceModelTransition','SourceWorldTick','SourceFrameStack'})do set(p,'Ready',0)end
 set('SourceClock','Ready',0xb4c5);set('SourceClock','Due',1);set('SourceClock','TimeLo',48);set('SourceClock','TimeHi',0);set('SourceClock','Fault',0)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('SELFCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,POSTRESULT,POSTRESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--restore-effect',action='store_true');a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);rows=cases(a.restore_effect)
    lua='local restore='+str(a.restore_effect).lower()+'\n'+LUA;reporter=Reporter('M4-SOURCE-SELF',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'SourceSelf4086_Enter','SourceSelf4086_Ready',0xb4f6,[],lua,reporter,finish='SourceSelf4086_RestoreEffect' if a.restore_effect else 'SourceSelf4086_Leave',post='SourceClock4086_Commit')
    results=[];costs=[];clocks=[]
    for line in log.splitlines():
        for marker,target in [('SELFRESULT|',results),('SELFCOST|',costs),('SELFCLOCK|',clocks)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('pointer identity, script locals, live entities and CPU context preserved',len(results)==len(rows) and all(r==[i,0,0,0] for i,r in enumerate(results)))
    reporter.check('admitted pending/faulty self blocks clock; disabled lease retains existing path',len(clocks)==len(rows) and all(r==([i,1,48,1] if c['bad']!='disabled' and (c['fault'] or c['mode']==0) else [i,0,49,0]) for i,(r,c) in enumerate(zip(clocks,rows))))
    report=dict(schema='BYOR_4086_SOURCE_SELF_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),results=results,cpu_costs=costs,clock_results=clocks,terminal_restore_effect_bound=a.restore_effect,script_locals_unchanged=True,admitted_pointer_domain='NULL or aligned physical entity token in 414000 pool',native_nested_global_self_proven=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
