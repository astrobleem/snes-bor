"""Pure native resume admission against all source-derived B4NC identities."""
import argparse, hashlib, json
from pathlib import Path
from source_native_continuation import unpack, SEGMENTS
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav

LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu={},{}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do emu.write(r[1]+j,(j*17+91)&255,mt)end end
 set('SourceNativeContinuation4086_Ready',0xb612);set('SourceNativeContinuation4086_State',0);set('SourceNativeContinuation4086_Request',0xb613);set('SourceNativeContinuation4086_Base',0x8000);set('SourceNativeContinuation4086_Bank',60);set('SourceNativeContinuation4086_Bytes',TABLEBYTES);set('SourceNativeContinuation4086_Count',RECORDS)
 set('SourceVMRun4086_Ready',0xb4d7);set('SourceVMRun4086_Busy',0);set('VmState_Status',3,1);set('VmState_Budget',0);set('VmState_Ip',c.resume_ip);set('VmState_SlotCount',1024);set('VmState_FrameTop',#c.frame_callsites)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_State',c.callback_state);set('SourceAnimationCallback4086_Program',c.program)
 set('VmSourceFrame_Program',c.program);set('VmSourceCallback_Ready',0xb4a5);set('VmSourceCallback_Active',0xb4a6);set('VmSourceCallback_Request',0)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',1);set('SourceUpdateFrame4086_Pending',1)
 set('SourceFrameStack4086_Ready',0xb4ed);set('SourceFrameStack4086_Fault',0);set('SourceFrameStack4086_Depth',c.depth)
 put(sy.VmCall_TargetId,c.native_id);put(sy.VmPriv_C,c.callsite)
 for i,site in ipairs(c.frame_callsites)do put(FRAMES+(i-1)*12+4,site)end
 for _,g in ipairs(c.guards)do put(sy[g[1]],g[2],g[3]or 2)end
 if c.frame_bad then put(FRAMES+4,65535)end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 local c=rows[word(INDEX)+1]
 emu.log('NATIVEMATCH|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNativeContinuation4086_State)..'|'..word(sy.SourceNativeContinuation4086_Record)..'|'..word(sy.SourceNativeContinuation4086_Row)..'|'..word(sy.SourceNativeContinuation4086_Frames)..'|'..word(sy.SourceNativeContinuation4086_Slots)..'|'..word(sy.SourceNativeContinuation4086_Payload))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 set('VmState_Status',4,1);set('VmSourceCallback_Active',0);set('SourceUpdateFrame4086_Ready',0)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output','table'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    table=a.table.read_bytes();decoded,*_=unpack(table);rows=[]
    for i,r in enumerate(decoded):
        for state,depth in [(1,0),(2,0),(1,6)]:rows.append(dict(r,index=i,callback_state=state,depth=depth,fault=0,guards=[]))
    base=rows[0]
    for name,values in [('Ready',[0,0xb613]),('State',[1,3]),('Request',[0,0xb612]),('Base',[0x7fff,0xff80]),('Bank',[0,64]),('Bytes',[0,len(table)-2]),('Count',[0,1025])]:
        for value in values:rows.append(dict(base,fault=1,guards=[['SourceNativeContinuation4086_'+name,value]]))
    for name,values in [('SourceVMRun4086_Ready',[0]),('SourceVMRun4086_Busy',[1]),('VmState_Status',[0,1,2,4,5]),('VmState_Budget',[1]),('VmState_Ip',[0,65535]),('VmState_SlotCount',[0,1,1025]),('VmState_FrameTop',[0,64]),('SourceAnimationCallback4086_Ready',[0]),('SourceAnimationCallback4086_State',[0,3,4]),('SourceAnimationCallback4086_Program',[65535]),('VmSourceCallback_Ready',[0]),('VmSourceCallback_Active',[0]),('SourceUpdateFrame4086_Ready',[0]),('SourceUpdateFrame4086_State',[0,2]),('SourceUpdateFrame4086_Pending',[0,2]),('SourceFrameStack4086_Ready',[0]),('SourceFrameStack4086_Fault',[1]),('SourceFrameStack4086_Depth',[7,8]),('VmCall_TargetId',[0]),('VmPriv_C',[65535])]:
        for value in values:rows.append(dict(base,fault=1,guards=[[name,value,1 if name=='VmState_Status'else 2]]))
    rows.append(dict(base,fault=1,frame_bad=True))
    ranges=SEGMENTS+[(0x7fc000,8192),(0x7fe100,768),(0x40f000,4096),(0x43fd00,128),(0x7ffb50,528)]
    r=Reporter('M4-NATIVE-CONTINUATION-MATCH',kind='GATE')
    from actor_s5_entity_fixture import symbols
    sy=symbols(Path('src/main.sym'))
    lua='local ranges='+luav([list(x)for x in ranges])+'\n'+LUA.replace('TABLEBYTES',str(len(table))).replace('RECORDS',str(len(decoded))).replace('FRAMES',str(sy['VmFrames_Wram']))
    raw,log=run_fixture(a.rom,a.output,rows,'SourceNativeContinuation4086_Match','SourceNativeContinuation4086_Ready',0xb612,[(60,0,table)],lua,r,batch_size=4)
    actual=[list(map(int,l.split('NATIVEMATCH|',1)[1].split('|')))for l in log.splitlines()if'NATIVEMATCH|'in l]
    failures=[]
    for i,(c,v)in enumerate(zip(rows,actual)):
        prefix=[i,0,0,3 if c['fault']else 2]
        if v[:4]!=prefix or not c['fault']and(v[4]!=c['index']or v[6:]!=[len(c['frame_callsites']),len(c['slots']),c['snapshot_bytes']]):failures.append(dict(input=c,actual=v))
    r.check('all source-native resume identities including shared functions with different callers; guards; VM/frame/slot/continuation/context state untouched',len(actual)==len(rows)and not failures)
    (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NATIVE_CONTINUATION_MATCH_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,failures=failures[:10],table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),native_request_instrumented=True,capture_execution_bound=False,constructor_execution_bound=False,live_native_api_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
