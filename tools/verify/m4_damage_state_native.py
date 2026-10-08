"""Native source damage-state birth, exact binary32 and adjacent WRAM fences."""
import argparse
import hashlib
import json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''DamageStateFixture_Run:
.a16
.i16
 php
 rep #$38
 lda.l SLOT
 jsl BIRTH
 bcs DamageStateFixture_Bad
 plp
 clc
 rtl
DamageStateFixture_Bad:
.a16
.i16
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local ranges={{0x7fb8f0,1552},{0x7fbf06,266},{0x439000,10240}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(sy.SourceWorldTick4086_Slot,c.slot)
 put(0x7fbf00,c.ready);put(sy.SourceLifecycle4086_Ready,c.life_ready)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 local life=0x439000+80*(c.slot%128);put(life+64,c.bits,4);put(life+74,c.marker)
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,ENTER,ENTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp']or(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.ready==0xb62b and c.fault==0 then
  local row=0x7fb900+c.slot*12
  for i=0,11 do before[row+i]=i<4 and((c.bits>>(8*i))&255)or 0 end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('DAMAGESTATE|'..word(INDEX)..'|'..ctx..'|'..n)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 seed=dict(slot=0,bits=0,ready=0xb62b,life_ready=0xb4fb,marker=0xb4fb,fault=0)
 rows=[dict(seed,slot=s)for s in range(128)]
 rows.extend(dict(seed,slot=s,bits=b)for s in(0,63,127)for b in(0x80000000,0x40600000,0xc0000000,0x3dcccccd,0x00000001,0x7f7fffff))
 rows.extend(dict(seed,**change,fault=1)for change in(dict(ready=1),dict(slot=128),dict(slot=65535),dict(life_ready=0),dict(marker=0),dict(bits=0x7fc00000),dict(bits=0x7f800000),dict(bits=0xff800000)))
 rows.append(dict(seed,slot=65535,life_ready=0,ready=0))
 reporter=Reporter('M4-DAMAGE-STATE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'DamageStateFixture_Run','SourceDamageState4086_Ready',0xb62b,[],LUA,reporter,
  append=ASM,bindings=dict(SLOT='SourceWorldTick4086_Slot',BIRTH='SourceDamageState4086_InitializeBirth'),probes=dict(ENTER='DamageStateFixture_Run'))
 actual=[list(map(int,l.split('DAMAGESTATE|',1)[1].split('|')))for l in log.splitlines()if'DAMAGESTATE|'in l]
 expected=[[i,0,0]for i in range(len(rows))];ok=actual==expected
 reporter.check('exact model binary32 copy and zero timers/type; all 128 rows; neighboring FP cache and VM slots and life preserved; finite/slot/lease rejection and cold no-op',ok)
 report=dict(schema='BYOR_4086_DAMAGE_STATE_BIRTH_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
  rom_sha256=hashlib.sha256(raw).hexdigest(),allocation=dict(base='7FB900',bytes=1536,end_exclusive='7FBF00',left_authority='StreamCacheFp_SlotStamp ends 7FB900 exclusive',right_authority='VmSlots_Wram begins 7FC000'),
  source_spawn_assignment='e->knockdowncount = e->modeldata.knockdowncount',source_knockdowntime_and_damagetype_memset_zero=True,
  full_constructor_integration_proven=False,native_damage_callback_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
