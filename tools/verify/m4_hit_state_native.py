"""All physical hit-identity rows, unsigned bits, generation and sibling guards."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as _IMPORT_PATH
from source_hit_state_layout import layout
from source_hit_state_native import emit
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter


ASM="""HitStateProbe:
.a16
.i16
 php
 phx
 phy
 sed
 ldx #$5678
 ldy #$1234
 lda.l W+24
 beq HitStateProbe_Birth
 cmp #1
 beq HitStateProbe_Write
 cmp #2
 beq HitStateProbe_Reset
 jsl HitState_Read
 bra HitStateProbe_Return
HitStateProbe_Birth:
.a16
.i16
 jsl HitState_ClearBirth
 bra HitStateProbe_Return
HitStateProbe_Write:
.a16
.i16
 jsl HitState_Write
 bra HitStateProbe_Return
HitStateProbe_Reset:
.a16
.i16
 jsl HitState_ResetAttack
HitStateProbe_Return:
.a16
.i16
 nop
 bcs HitStateProbe_Bad
 ply
 plx
 plp
 clc
 rtl
HitStateProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
"""
LUA=r"""
local mt=emu.memType.snesMemory;local before,cpu={},{};local ctx,decimal=0,0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);ctx=0;decimal=0
 for j=0,63 do put(W+j,0,1)end
 for j=-8,SIZE+7 do put(BASE+j,(j*13+91)&255,1)end
 local at=BASE+16*c.slot
 put(W,0xb6a0);put(W+4,c.slot);put(W+8,0x12345678,4);put(W+16,BASE%65536);put(W+18,0x42);put(W+20,c.capacity or CAPACITY);put(W+22,128);put(W+24,c.op)
 put(W+28,c.attack,4);put(W+32,c.hitby,4)
 put(at,0xffffffff,4);put(at+4,0x80000000,4);put(at+8,0x12345678,4);put(at+12,0xb6a1);put(at+14,c.slot)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_Count,128)
 if c.bad=='ready'then put(W,0)elseif c.bad=='zero_generation'then put(W+8,0,4)
 elseif c.bad=='generation_low'then put(W+8,0x12345679,4)elseif c.bad=='generation_high'then put(W+10,0)
 elseif c.bad=='zero_capacity'then put(W+20,0)
 elseif c.bad=='capacity'then put(W+20,CAPACITY+2)elseif c.bad=='base'then put(W+16,BASE%65536+2)
 elseif c.bad=='bank'then put(W+18,0x43)elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='zero_count'then put(sy.VmSourceWorld_Count,0)elseif c.bad=='large_count'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='slot'then put(W+4,128)elseif c.bad=='entity_count'then put(W+22,127)
 elseif c.bad=='marker'then put(at+12,0)elseif c.bad=='row_generation'then put(at+8,0,4)
 elseif c.bad=='row_generation_high'then put(at+10,0)elseif c.bad=='row_slot'then put(at+14,(c.slot+1)%128)end
 before={};for j=-8,SIZE+7 do before[BASE+j]=emu.read(BASE+j,mt)end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()decimal=emu.getState()['cpu.ps']&8 end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local at=BASE+16*c.slot
 local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
 if c.fault==0 then
  if c.op==0 then expect(at,0,4);expect(at+4,0,4);expect(at+8,0x12345678,4);expect(at+12,0xb6a1,2);expect(at+14,c.slot,2)
  elseif c.op==1 then expect(at,c.attack,4);expect(at+4,c.hitby,4)
  elseif c.op==2 then expect(at,0,4)end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 local reads=0;if c.fault==0 and c.op==3 then for j=0,7 do if emu.read(W+28+j,mt)~=before[at+j]then reads=reads+1 end end end
 emu.log('HITSTATE|'..word(INDEX)..'|'..word(W+2)..'|'..n..'|'..reads..'|'..ctx..'|'..decimal)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 plan=layout();sy=symbols(Path('src/main.sym'))
 rows=[dict(slot=s,op=op,attack=(0xffffffff,0x80000000,0,0x7fffffff)[s%4],hitby=(0,1,0x80000001,0xffffffff)[s%4],fault=0)for s in range(128)for op in range(4)]
 from source_hit_contact_layout import layout as contact_layout
 for slot in range(128):
  for op in range(4):rows.append(dict(rows[slot*4+op],capacity=contact_layout()['chr_capacity']))
 for slot in (0,127):
  for bad in ('ready','zero_generation','generation_low','generation_high','capacity','base','bank','world','zero_count','large_count','slot','entity_count','marker','row_generation','row_generation_high','row_slot','zero_capacity'):
   rows.append(dict(rows[-1],slot=slot,op=3,bad=bad,fault=1))
 replacements=dict(W=plan['controls'],BASE=plan['base'],SIZE=plan['bytes'],CAPACITY=plan['chr_capacity'])
 import re
 asm=ASM;lua=LUA
 for n,v in replacements.items():asm=re.sub(r'\b'+n+r'\b',str(v),asm);lua=re.sub(r'\b'+n+r'\b',str(v),lua)
 reporter=Reporter('M4-SOURCE-HIT-IDENTITY-STORAGE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'HitStateProbe','VmState_Error',0xb6a0,[],lua,reporter,append=asm+emit(plan,sy),probes={'RETURN':'HitStateProbe_Return'},batch_size=4,link_pcm=False)
 actual=[list(map(int,line.split('HITSTATE|',1)[1].split('|')))for line in log.splitlines()if 'HITSTATE|'in line]
 wanted=[[i,3 if c['fault']else 2,0,0,0,8]for i,c in enumerate(rows)]
 reporter.check('birth/read/write/reset, all 128 physical slots, exact unsigned identities, sibling rows and CPU',actual==wanted)
 reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_SOURCE_HIT_IDENTITY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guard_cases=34,plan=plan,results=actual,expected=wanted,rom_sha256=hashlib.sha256(raw).hexdigest(),ram_ownership_instrumented=True,independent_register_generation=True,production_memory_lease=False,actual_constructor_hook_bound=False,actual_model_copy_hook_bound=False,hit_resolution_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
