"""Every physics scalar birth row and adjacent guards, including invalid slots."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''
PhysicsStateBirthProbe_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SLOTINPUT
 jsl INITIALIZE
 bcs PhysicsStateBirthProbe_Bad
 ply
 plx
 plp
 clc
 rtl
PhysicsStateBirthProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu,ctx={}, {},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(sy.SourceAIReadonly4086_Result,c.slot);put(sy.SourcePhysicsState4086_Ready,c.ready)
 before={};for a=0x42d7f0,0x42e00f do emu.write(a,0xa5,mt);before[a]=0xa5 end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];if c.fault==0 and c.ready==0xb61c then for j=0,15 do before[0x42d800+c.slot*16+j]=0 end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('AIBIRTH|'..word(INDEX)..'|'..ctx..'|'..n)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 rows=[dict(slot=s,ready=0xb61c,fault=int(s>=128))for s in (*range(128),128,65535)]+[dict(slot=s,ready=0,fault=0)for s in (0,127,128,65535)]+[dict(slot=0,ready=0xb61d,fault=1)]
 r=Reporter('M4-PHYSICS-STATE-BIRTH',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'PhysicsStateBirthProbe_Begin','SourcePhysicsState4086_Ready',0xb61c,[],LUA,r,append=ASM,bindings=dict(SLOTINPUT='SourceAIReadonly4086_Result',INITIALIZE='SourcePhysicsState4086_InitializeBirth'),batch_size=2)
 results=[list(map(int,l.split('AIBIRTH|',1)[1].split('|')))for l in log.splitlines()if 'AIBIRTH|'in l]
 r.check('all 128 physical rows cleared exactly, adjacent rows/regions and CPU retained; invalid slots reject without writes',results==[[i,0,0]for i in range(len(rows))])
 report=dict(schema='BYOR_4086_PHYSICS_STATE_BIRTH_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),row_bytes=16,state_base=0x42d800,state_end_exclusive=0x42e000,native_active_gravity_or_landing_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
