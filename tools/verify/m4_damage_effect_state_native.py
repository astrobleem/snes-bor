"""Native source damage-effect birth with full allocation and fence checks."""
import argparse
import hashlib
import json
from pathlib import Path
from source_damage_inputs_4086 import pack
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''DamageEffectsStateFixture_Run:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SLOT
 jsl BIRTH
 bcs DamageEffectsStateFixture_Bad
 pla
 plp
 clc
 rtl
DamageEffectsStateFixture_Bad:
.a16
.i16
 pla
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local ranges={{0x7ef000,4096},{0x7eeaa6,32},{0x7fb900,1536},{0x7fc000,16}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(SLOT,c.slot)
 put(EFFECTREADY,c.ready);put(sy.SourceLifecycle4086_Ready,0xb4fb);put(sy.SourceLandingDrop4086_Ready,0xb62e)
 put(sy.SourceLandingDrop4086_Base,0x8000);put(sy.SourceLandingDrop4086_Bank,0x3a);put(sy.SourceLandingDrop4086_Bytes,TABLEBYTES);put(sy.SourceLandingDrop4086_Models,3)
 local slot=c.slot%128;local life=0x439000+slot*80;local side=0x416800+slot*64
 put(life+72,c.model);put(life+74,0xb4fb);put(side,c.model)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 local changes={unknown_ready={EFFECTREADY,1},input_ready={sy.SourceLandingDrop4086_Ready,0},life_ready={sy.SourceLifecycle4086_Ready,0},life_marker={life+74,0},side_model={side,7},models_zero={sy.SourceLandingDrop4086_Models,0},models_large={sy.SourceLandingDrop4086_Models,17},bytes={sy.SourceLandingDrop4086_Bytes,TABLEBYTES-1},base={sy.SourceLandingDrop4086_Base,0x7fff},extent={sy.SourceLandingDrop4086_Base,0xfff0},bank={sy.SourceLandingDrop4086_Bank,0x40},bank_high={sy.SourceLandingDrop4086_Bank,0x13a}}
 if c.bad then local r=changes[c.bad];if r then put(r[1],r[2])end end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 for _,r in ipairs({{life,80},{side,64}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,ENTER,ENTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'a','x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp']or(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.ready~=0 and c.fault==0 then
  local row=0x7ef100+c.slot*24
  for i=0,23 do before[row+i]=0 end
  for i=0,3 do before[row+16+i]=(c.guard>>(8*i))&255 end
  before[row+20]=0x2f;before[row+21]=0xb6;before[row+22]=c.model
  for i=0,3 do before[0x7efd00+c.slot*4+i]=0 end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('DAMAGEEFFECTSTATE|'..word(INDEX)..'|'..ctx..'|'..n)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    guards=(0,-1,2147483647)
    table=pack(dict(models=[dict(id=i,fields=dict(animal=0,nodrop=0,guardpoints=g))for i,g in enumerate(guards)]))
    seed=dict(slot=0,model=0,guard=0,ready=0xb62f,fault=0)
    rows=[dict(seed,slot=slot,model=slot%3,guard=guards[slot%3]&0xffffffff)for slot in range(128)]
    rows.extend(dict(seed,bad=bad,fault=1)for bad in('unknown_ready','input_ready','life_ready','life_marker','side_model','models_zero','models_large','bytes','base','extent','bank','bank_high'))
    rows.extend(dict(seed,slot=slot,fault=1)for slot in(128,65535))
    rows.append(dict(seed,model=3,fault=1));rows.append(dict(seed,slot=65535,ready=0))
    reporter=Reporter('M4-DAMAGE-EFFECT-STATE',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'DamageEffectsStateFixture_Run','SourceDamageEffectsState4086_Ready',0xb62f,[(58,0,table)],LUA.replace('TABLEBYTES',str(len(table))),reporter,
                        append=ASM,bindings=dict(SLOT='SourceWorldTick4086_Slot',BIRTH='SourceDamageEffectsState4086_InitializeBirth',EFFECTREADY='SourceDamageEffectsState4086_Ready'),probes=dict(ENTER='DamageEffectsStateFixture_Run'))
    actual=[list(map(int,l.split('DAMAGEEFFECTSTATE|',1)[1].split('|')))for l in log.splitlines()if'DAMAGEEFFECTSTATE|'in l]
    expected=[[i,0,0]for i in range(len(rows))];ok=actual==expected
    reporter.check('all128 rows initialize exact source projectile/staydown/guard/model and toexplode state; adjacent G12/frontpanel/VM/damage state preserved; malformed slots/leases/descriptors reject atomically; cold no-op',ok)
    report=dict(schema='BYOR_4086_DAMAGE_EFFECT_STATE_BIRTH_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
                rom_sha256=hashlib.sha256(raw).hexdigest(),allocation=dict(base='7EF100',bytes=3072,end_exclusive='7EFD00',left_authority='G12_AnimTrace_Ring7EF000..7EF03F; StageFp_BG2HistoryEnd7EEAB6'),
                toexplode_allocation=dict(base='7EFD00',bytes=512,end_exclusive='7EFF00'),
                source_policy='memset-zero projectile/staydown/toexplode; shallow modeldata guardpoints copy; fresh model identity',
                full_constructor_integration_proven=False,native_damage_callback_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
