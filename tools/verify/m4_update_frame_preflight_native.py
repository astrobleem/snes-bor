"""Pure update_frame admission: actor bytes and source-self context unchanged."""
import argparse, hashlib, json, struct
from pathlib import Path
from m4_frame_owner_native import LUA
from source_frame_effects_4086 import pack as pack_fe
from source_frame_effect_plan import derive, pack as pack_plan
from source_update_frame_authority import events
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('rom','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    frames=[dict(move=dict(base=0,x=0,y=0,z=0),sound=None,delay_ticks=d) for d in (6,8)]
    effects=dict(models=['dust','effect'],animations=[dict(handle=i,events=events(),frames=frames) for i in (1,2)])
    fe=pack_fe(effects);plan=pack_plan(derive(effects));h=struct.unpack_from('<4s6H4I',plan)
    rows=[]
    for slot in (0,1,95,96,127):
        for request in (0,1,2,32767):
            rows.append(dict(slot=slot,request=request,old=0x4000+80*((slot+1)%128),time=0xffffffff,level=1,direction=1,animating=1,bad='',mode=0))
        for bad in ('ready','state','pending','self_active','self_fault','vm_running','vm_yielded','vm_fault','world','slot','request','handle','base','bank','bytes','plan_state','plan_pending'):
            rows.append(dict(slot=slot,request=0,old=0x4000,time=7,level=1,direction=1,animating=1,bad=bad,mode=0))
    lua=LUA[:LUA.index('emu.addMemoryCallback(function()\n local s=emu.getState();cpu=')]
    lua=lua.replace('set(\'SourceUpdateFrame\',\'Request\',0)','set(\'SourceUpdateFrame\',\'Request\',c.request)')
    values=dict(FEBYTES=len(fe),PLANBYTES=len(plan),PAIRLO=h[-2]&65535,PAIRHI=h[-2]>>16,BODYLO=h[-1]&65535,BODYHI=h[-1]>>16)
    for key,value in values.items():lua=lua.replace(key,str(value))
    guards=r'''
 if c.bad=='ready'then set('SourceUpdateFrame','Ready',0)
 elseif c.bad=='state'then set('SourceUpdateFrame','State',3)
 elseif c.bad=='pending'then set('SourceUpdateFrame','Pending',1)
 elseif c.bad=='self_active'then set('SourceSelf','Active',1)
 elseif c.bad=='self_fault'then set('SourceSelf','Fault',1)
 elseif c.bad=='vm_running'then put(sy.VmState_Status,2,1)
 elseif c.bad=='vm_yielded'then put(sy.VmState_Status,3,1)
 elseif c.bad=='vm_fault'then put(sy.VmState_Status,5,1)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='slot'then set('SourceUpdateFrame','Slot',128)
 elseif c.bad=='request'then set('SourceUpdateFrame','Request',65535)
 elseif c.bad=='handle'then put(s+4,3)
 elseif c.bad=='base'then set('SourceUpdateFrame','Base',0x7fff)
 elseif c.bad=='bank'then set('SourceUpdateFrame','Bank',64)
 elseif c.bad=='bytes'then set('SourceUpdateFrame','Bytes',24)
 elseif c.bad=='plan_state'then set('SourceFrameEffectPlan','State',3)
 elseif c.bad=='plan_pending'then set('SourceFrameEffectPlan','State',2);set('SourceFrameEffectPlan','Service',1)end
 put(EXPECTFAULT,c.bad==''and 0 or 1)
'''
    lua=lua.replace(' before={};for',guards+' before={};for')
    lua+=r'''
emu.addMemoryCallback(function()
 local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
 beforeSelf={};for _,k in ipairs({'GlobalLow','GlobalHigh','Active','Fault'})do beforeSelf[k]=word(sy['SourceSelf4086_'..k])end
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=st['cpu.sp']or(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local changed=0;for addr,v in pairs(before)do if emu.read(addr,mt)~=v then changed=changed+1 end end
 local selfChanges=0;for k,v in pairs(beforeSelf)do if word(sy['SourceSelf4086_'..k])~=v then selfChanges=selfChanges+1 end end
 emu.log('PREFLIGHTRESULT|'..word(INDEX)..'|'..changed..'|'..ctx..'|'..selfChanges..'|'..word(sy.SourceUpdateFrame4086_Count))
 put(sy.VmSourceWorld_Ready,0);put(sy.SourceWorldTick4086_Ready,0)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    r=Reporter('M4-UPDATE-FRAME-PREFLIGHT',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'SourceUpdateFrame4086_Preflight','SourceUpdateFrame4086_Ready',0xb4e3,[(60,0,fe),(59,0,plan)],lua,r,batch_size=4)
    actual=[list(map(int,line.split('PREFLIGHTRESULT|',1)[1].split('|')))for line in log.splitlines()if 'PREFLIGHTRESULT|'in line]
    r.check('pure actor/self preflight and CPU preservation',len(actual)==len(rows)and all(v[:4]==[i,0,0,0]for i,v in enumerate(actual)))
    r.check('valid and out-of-range no-op requests capture actual count',all(v[4]==2 for v,c in zip(actual,rows)if not c['bad']))
    (folder/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_UPDATE_FRAME_PREFLIGHT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',inputs=rows,actual=actual,cases=len(rows),rom_sha256=hashlib.sha256(raw).hexdigest(),frame_effects_sha256=hashlib.sha256(fe).hexdigest(),actor_mutation=False,self_entry=False,motu_gameplay_proven=False),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
