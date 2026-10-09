"""Exact pending descriptor stores with borrowed RAM and generation guards."""
import argparse,hashlib,json
from pathlib import Path
from source_pending_jump_layout import layout
from source_pending_jump_native import emit
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

WORK=0x7fa000
ASM='''PendingJumpProbe:
.a16
.i16
 php
 sed
 lda.l W+24
 beq PendingJumpProbe_Birth
 cmp #1
 beq PendingJumpProbe_Write
 cmp #2
 beq PendingJumpProbe_Copy
 jsl PendingJump_Read
 bra PendingJumpProbe_Return
PendingJumpProbe_Birth:
 jsl PendingJump_ClearBirth
 bra PendingJumpProbe_Return
PendingJumpProbe_Write:
 jsl PendingJump_Write
 bra PendingJumpProbe_Return
PendingJumpProbe_Copy:
 jsl PendingJump_CopyModel
PendingJumpProbe_Return:
.a16
.i16
 nop
 bcs PendingJumpProbe_Bad
 plp
 clc
 rtl
PendingJumpProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local context=0;local decimal=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);context=0;decimal=0
 for j=0,63 do put(W+j,0,1)end
 for j=-8,SIZE+7 do put(BASE+j,(j*13+91)&255,1)end
 local at=BASE+24*c.slot
 put(W,0xb691);put(W+4,c.slot);put(W+6,c.model);put(W+8,0x12345678,4);put(W+12,0x12345678,4)
 put(W+16,BASE%65536);put(W+18,0x42);put(W+20,BASE-0x420000);put(W+22,16);put(W+24,c.op)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_SideBase,0x6800);put(sy.VmSourceWorld_Count,128)
 put(0x416800+64*c.slot,c.model);put(at+16,c.op==2 and 1 or c.model+1);put(at+18,0xb691);put(at+20,0x12345678,4)
 for j=0,3 do put(W+32+4*j,c.values[j+1],4)end
 if c.bad=='ready'then put(W,0)elseif c.bad=='zero_generation'then put(W+8,0,4);put(W+12,0,4)
 elseif c.bad=='generation_low'then put(W+12,0x12345679,4)elseif c.bad=='generation_high'then put(W+14,0)
 elseif c.bad=='capacity'then put(W+20,0xd800)elseif c.bad=='base'then put(W+16,BASE%65536+2)
 elseif c.bad=='bank'then put(W+18,0x43)elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)elseif c.bad=='side'then put(sy.VmSourceWorld_SideBase,0x6802)
 elseif c.bad=='zero_count'then put(sy.VmSourceWorld_Count,0)elseif c.bad=='large_count'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='slot'then put(W+4,128)elseif c.bad=='model_count'then put(W+22,17)
 elseif c.bad=='model'then put(W+6,16)elseif c.bad=='side_model'then put(0x416800+64*c.slot,c.model+1)
 elseif c.bad=='marker'then put(at+18,0)elseif c.bad=='row_generation'then put(at+20,0)
 elseif c.bad=='row_model'then put(at+16,c.model+2)elseif c.bad=='zero_handle'then put(at+16,0)
 elseif c.bad=='birth_stale_model'then put(0x416800+64*c.slot,0xffff)end
 before={};for j=-8,SIZE+7 do before[BASE+j]=emu.read(BASE+j,mt)end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu['cpu.'..k]~=s['cpu.'..k]then context=context+1 end end
 if cpu['cpu.sp']~=s['cpu.sp']or(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then context=context+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()decimal=emu.getState()['cpu.ps']&8 end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local at=BASE+24*c.slot
 local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
 if c.fault==0 then
  if c.op==0 then for j=0,15 do before[at+j]=0 end end
  if c.op==0 or c.op==2 then expect(at+16,c.model+1,2);expect(at+18,0xb691,2);expect(at+20,0x12345678,4)end
  if c.op==1 then for j=0,3 do expect(at+4*j,c.values[j+1],4)end end
 end
 local mismatch=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then mismatch=mismatch+1 end end
 local reads=0;if c.fault==0 and c.op==3 then for j=0,15 do if emu.read(W+32+j,mt)~=before[at+j]then reads=reads+1 end end end
 emu.log('PENDINGJUMP|'..word(INDEX)..'|'..word(W+2)..'|'..mismatch..'|'..reads..'|'..context..'|'..decimal)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    plan=layout();sy=symbols(Path('src/main.sym'));rows=[]
    for slot in range(128):
        for op in range(4):
            for model in(3,4):rows.append(dict(slot=slot,op=op,model=model,values=[0x40900000,0x3f99999a,0x80000000,0x80000001],fault=0))
    seed=rows[-1]
    for bad in('ready','zero_generation','generation_low','generation_high','capacity','base','bank','world','pool','side','zero_count','large_count','slot','model_count','model','side_model','marker','row_generation','row_model'):
        rows.append(dict(seed,bad=bad,fault=1))
    for bad in('marker','row_generation','zero_handle'):rows.append(dict(seed,op=2,bad=bad,fault=1))
    for values in([0x7fc01234,0xff800000,0x00000001,0xffffffff],[0x80000001,0x7f800000,0x3dcccccd,0x7fffffff]):rows.append(dict(seed,op=1,values=values,fault=0))
    rows.append(dict(seed,op=0,bad='birth_stale_model',fault=0))
    reporter=Reporter('M4-PENDING-JUMP-STORAGE',kind='GATE')
    asm=ASM.replace('W+',str(WORK)+'+')+emit(plan,WORK,sy)
    lua=LUA.replace('WORK',str(WORK)).replace('W+',str(WORK)+'+').replace('(W,','('+str(WORK)+',').replace('word(W','word('+str(WORK)).replace('W+j',str(WORK)+'+j')
    lua=lua.replace('BASE',str(plan['base'])).replace('SIZE',str(plan['bytes']))
    _,log=run_fixture(a.rom,a.output,rows,'PendingJumpProbe','VmState_Error',0xb691,[],lua,reporter,append=asm,probes={'RETURN':'PendingJumpProbe_Return'},batch_size=16,link_pcm=False)
    actual=[list(map(int,l.split('PENDINGJUMP|',1)[1].split('|')))for l in log.splitlines()if 'PENDINGJUMP|'in l]
    wanted=[[i,3 if c['fault']else 2,0,0,0,8]for i,c in enumerate(rows)]
    reporter.check('all 128 pending rows preserve binary32/int bits, siblings, generation guards and CPU context',actual==wanted)
    report=dict(schema='BYOR_SOURCE_PENDING_JUMP_NATIVE_V1',status='PASS'if actual==wanted else'FAIL',cases=len(rows),guard_cases=22,plan=plan,results=actual,expected=wanted,ram_ownership_instrumented=True,production_memory_lease=False,actual_constructor_hook_bound=False,actual_model_copy_hook_bound=False,tryjump_dojump_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');assert actual==wanted


if __name__=='__main__':main()
