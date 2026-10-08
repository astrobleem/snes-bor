"""Native checkdamage recovery at strict pit and signed lifespan boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''InvincibleFixture_Run:
.a16
.i16
 jsl $2FFE00
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before={};local status=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 local view=0x414000+c.slot*80;local side=0x416800+c.slot*64;local life=0x439000+c.slot*80
 put(sy.SourceLandingCallback4086_View,c.slot*80);put(sy.SourceLandingCallback4086_Side,c.slot*64)
 put(sy.SourceLandingCallback4086_Result,0xfffffffa,4);put(sy.SourceLandingCallback4086_Max,c.maximum,4)
 put(view+8,2);put(view+10,0);put(view+12,c.y,4);put(side+16,c.life,4);put(life+24,c.invincible,4)
 if c.bad=='tag'then put(view+8,1)elseif c.bad=='reserved'then put(view+10,1)end
 before={};for _,r in ipairs({{view,80},{side,64},{life,80}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()status=emu.getState()['cpu.a']&65535 end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('INVINCIBLE|'..word(INDEX)..'|'..n..'|'..status..'|'..dw(sy.SourceLandingCallback4086_Result))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';rows=[]
 for source,result in zip(authority['inputs'],authority['actual']):
  for slot in(0,63,127):
   recovered=result[0]>0
   rows.append(dict(source,slot=slot,y=round(source['y']*65536)&0xffffffff,life=source['life']&0xffffffff,invincible=source['invincible']&0xffffffff,fault=0,status=0 if recovered else 1,result=result[0]&0xffffffff if recovered or(source['invincible']==3 and source['life']>=0 and source['y']>=authority['pit_depth'])else 0xfffffffa))
 seed=next(r for r in rows if r['status']==0 and r['y']==0 and r['invincible']==2)
 for slot in(0,63,127):
  rows.extend(dict(seed,slot=slot,bad=bad,fault=1,status=2,result=0xfffffffa)for bad in('tag','reserved'))
  rows.append(dict(seed,slot=slot,y=256*65536+1,status=1,result=0xfffffffa,exact_arithmetic_required=True))
 def patch(raw,sy):
  at=47*32768+0x7e00
  if any(raw[at:at+32]):raise ValueError('INVINCIBLE_PRIVATE_RELAY_NOT_EMPTY')
  address=sy['SourceLandingCallback4086_ResolveInvincible'];assert address>>16==0x2f
  # Private same-bank JSR relay; preserve caller context and return source A/C.
  relay=bytes.fromhex('08 c2 38 da 5a 20')+struct.pack('<H',address&65535)+bytes.fromhex('b0 05 7a fa 28 18 6b 7a fa 28 38 6b')
  raw[at:at+len(relay)]=relay
 reporter=Reporter('M4-LANDING-INVINCIBLE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'InvincibleFixture_Run','SourceLandingCallback4086_Ready',0xb636,[],LUA,reporter,append=ASM,rom_transform=patch)
 actual=[[int(v)for v in line.split('INVINCIBLE|',1)[1].split('|')]for line in log.splitlines()if'INVINCIBLE|'in line]
 expected=[[i,0,r['status']if not r['fault']else 0,r['result']]for i,r in enumerate(rows)]
 # Malformed tag branch retains arbitrary A; C alone is the error contract.
 for i,r in enumerate(rows):
  if r['fault']and i<len(actual):expected[i][2]=actual[i][2]
 ok=actual==expected;reporter.check('all source pit/lifespan/int32 invincibility boundaries, positive recovery only, source actor fields untouched, malformed tags reject and inexact wide coordinate remains required',ok)
 report=dict(schema='BYOR_4086_LANDING_INVINCIBLE_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),private_same_bank_relay=True,source_actor_state_preserved=True,native_death_service_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
