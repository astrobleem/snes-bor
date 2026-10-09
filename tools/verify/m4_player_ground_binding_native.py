"""Native canonical ground capture/writeback; services remain caller work."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_model_core_4086 import derive
from source_run_tuple_profile import derive as run_profile
from source_foreign_slot_tail import derive_plan
from source_player_ground_binding import emit
from source_player_state_native import emit as state_emit
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

W,G,S,R,H=0x7fa180,0x7fa000,0x7fa100,0x7fa200,0x7fa300
ASM='''
GroundBindingProbe:
.a16
.i16
 php
 sed
 jsl GroundBinding_Capture
GroundBindingProbe_Captured:
 nop
 bcs GroundBindingProbe_Return
GroundBindingProbe_Request:
 nop
 jsl GroundBinding_Publish
GroundBindingProbe_Return:
 nop
 bcs GroundBindingProbe_Bad
 plp
 clc
 rtl
GroundBindingProbe_Bad:
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before={};local expected={};local failures=0;local cpu={};local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dword(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function retain(a,n)for j=0,n-1 do before[a+j]=emu.read(a+j,mt)end end
local function want(a,v)for j=0,3 do expected[a+j]=(v>>(8*j))&255 end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];failures=0;before={};expected={}
 for _,a in ipairs({W,G,S,R})do for j=0,63 do emu.write(a+j,0,mt)end end
 put(W,0xb67c);put(W+4,c.slot);put(G,0xb679);put(R,0xb678)
 put(S,0xb67b);put(S+8,7,4);put(S+12,SLOTCOUNT);put(S+14,7,4);put(sy.VmState_SlotCount,SLOTCOUNT)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128)
 local i=c.slot;local view=0x414000+i*80;local side=0x416800+i*64
 put(view+4,1,4);put(view+24,1,4);put(view+28,c.direction,4);put(side,c.model)
 put(H+2*i,c.handle);put(side+60,65536+2*i,4)
 local fields={{0x42f400+24*i+4,-3},{0x42e000+40*i+28,0xfedc0000+i},{side+36,123456+i},
 {side+40,0xfffffffe-i},{0x439000+80*i+12,17},{0x43eb00+32*i,-4},{TAIL+24*i+4,-5}}
 for _,p in ipairs(fields)do put(p[1],p[2],4)end
 if c.bad=='ready'then put(W,0)elseif c.bad=='ground'then put(G,0)
 elseif c.bad=='run'then put(R,0)elseif c.bad=='generation'then put(S+8,8)
 elseif c.bad=='module'then put(sy.VmState_SlotCount,SLOTCOUNT-1)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='count'then put(sy.VmSourceWorld_Count,129)elseif c.bad=='slot'then put(W+4,128)
 elseif c.bad=='exists'then put(view+4,0,4)elseif c.bad=='direction_tag'then put(view+24,2)
 elseif c.bad=='direction_reserved'then put(view+26,1)elseif c.bad=='model'then put(side,16)
 elseif c.bad=='handle'then put(H+2*i,0)end
 for _,p in ipairs({{0x414000,10240},{0x416800,8192},{0x42f400,3072},{0x42e000,5120},{0x439000,10240},{0x43eb00,4096},{TAIL,3072},{H,256}})do retain(p[1],p[2])end
 put(EXPECTFAULT,c.bad~=''and 1 or 0)
 local st=emu.getState();start=st.masterClock;cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];if c.bad~=''and c.bad~='turn_service'and c.bad~='changed_model'then return end
 local i=c.slot;local offsets={24,28,32,44,48,52,56,60,64,68,72,36}
 if emu.getState()['cpu.ps']&8==0 then failures=failures+1 end
 local values={(-3)&0xffffffff,c.direction&0xffffffff,0xfedc0000+i,65536+2*i,c.speed,123456+i,(0xfffffffe-i)&0xffffffff,17,(-4)&0xffffffff,(-5)&0xffffffff,0,0}
 for n,off in ipairs(offsets)do if dword(G+off)~=values[n]then failures=failures+1;if word(INDEX)<8 then emu.log('BINDDETAIL|capture|'..word(INDEX)..'|'..off..'|'..dword(G+off)..'|'..values[n])end end end
end,emu.callbackType.exec,CAPTURED,CAPTURED,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local i=c.slot
 if c.bad=='changed_model'then local a=0x416800+64*i;put(a,(c.model+1)%16);before[a]=(c.model+1)%16;before[a+1]=0;return end
 if c.bad=='turn_service'then put(G+60,42,4);return end
 for _,p in ipairs({{28,1-(i&1)},{32,0xabc00000+i},{52,-65536-i},{56,65536+i},{60,0},{64,1},{68,-2147483648+i}})do put(G+p[1],p[2],4)end
 want(0x414000+80*i+28,1-(i&1));want(0x42e000+40*i+28,0xabc00000+i)
 want(0x416800+64*i+36,-65536-i);want(0x416800+64*i+40,65536+i)
 want(0x439000+80*i+12,0);want(0x43eb00+32*i,1);want(TAIL+24*i+4,-2147483648+i)
end,emu.callbackType.exec,REQUESTPOINT,REQUESTPOINT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();for _,k in ipairs({'a','x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then failures=failures+1 end end
 if (cpu.ps&254)~=(st['cpu.ps']&254)then failures=failures+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];for a,v in pairs(before)do if emu.read(a,mt)~=(expected[a]or v)then failures=failures+1;if word(INDEX)<8 then emu.log('BINDDETAIL|memory|'..word(INDEX)..'|'..a..'|'..emu.read(a,mt)..'|'..(expected[a]or v))end end end
 local st=emu.getState()
 local status=word(W+2);if status~=(c.bad==''and 2 or 3)then failures=failures+1 end
 emu.log('GROUNDBIND|'..word(INDEX)..'|'..failures..'|'..status..'|'..(st.masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();source=Source(a.source);plan=derive_plan(source);models=derive(source)['models'];run=run_profile(source)
    import struct
    rows=[]
    for i in range(128):
        for handle,raw in enumerate(run['tuples'],1):
            rows.append(dict(slot=i,model=i%16,handle=handle,speed=int(struct.unpack_from('<f',bytes.fromhex(raw))[0]*65536),direction=i&1,bad=''))
    for direction in (-2147483648,-1,2,65536,2147483647):
        for base in (rows[0],rows[-1]):rows.append(dict(base,direction=direction))
    guards=('ready','ground','run','generation','module','world','pool','count','slot','exists','direction_tag','direction_reserved','model','handle','turn_service','changed_model')
    rows += [dict(rows[0],bad=b)for b in guards]
    sy=symbols(Path('src/main.sym'));folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    reporter=Reporter('M4-GROUND-CANONICAL-BINDING',kind='GATE')
    (folder/'report.json').write_text(json.dumps(dict(status='RUNNING'))+'\n')
    code=state_emit(plan,S,sy)+emit(W,G,S,R,H,models,run,sy)
    lua=LUA
    import re
    for k,v in dict(W=W,G=G,S=S,R=R,H=H,TAIL=plan['base'],SLOTCOUNT=plan['live_slot_count']).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    raw,log=run_fixture(a.rom,folder,rows,'GroundBindingProbe','SourceAnimationInit4086_Ready',0xb4ec,[],lua,reporter,
        append=ASM+code,probes=dict(CAPTURED='GroundBindingProbe_Captured',REQUESTPOINT='GroundBindingProbe_Request'),batch_size=4,frame_limit=1000,link_pcm=False)
    results=[list(map(int,line.split('GROUNDBIND|',1)[1].strip().split('|')))for line in log.splitlines()if 'GROUNDBIND|'in line]
    errors=[r for r in results if r[1]]
    reporter.check('canonical capture, guarded publication, exact signed turning and all sibling/readonly bytes retained',len(results)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_GROUND_CANONICAL_BINDING_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guards=len(guards),observed=len(results),errors=errors[:8],
        rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max((r[3]for r in results),default=0),canonical_actor_storage_bound=True,
        module_lease_installer_instrumented=True,ground_services_bound=False,common_turn_publication_rejected=True,production_player_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
