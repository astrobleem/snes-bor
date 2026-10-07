"""Animation phase issue/ack leases: stale completion cannot retire a new tick."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('rom','output'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--ack',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);rows=[]
 for phase in (5,6,7,8):
  for ready in (0,0xb60e,0xb60f):
   for state in (0,1,2,3):
    for mismatch in ('','slot','time_low','time_high')if a.ack else ('',):
     fault=a.ack and phase==7 and ready!=0 and (ready!=0xb60f or state!=2 or mismatch!='')
     rows.append(dict(phase=phase,ready=ready,state=state,mismatch=mismatch,fault=int(fault)))
 lua=r'''
local mt=emu.memType.snesMemory;local cpu={};local ctx=0
local function word(addr)return emu.read(addr,mt)|(emu.read(addr+1,mt)<<8)end
local function put(addr,value)emu.write(addr,value&255,mt);emu.write(addr+1,(value>>8)&255,mt)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 put(sy.SourceWorldTick4086_Phase,c.phase);put(sy.SourceWorldTick4086_Slot,127);put(sy.SourceWorldTick4086_TimeLo,65535);put(sy.SourceWorldTick4086_TimeHi,32768)
 put(sy.SourceUpdateAnimation4086_Ready,c.ready);put(sy.SourceUpdateAnimation4086_State,c.state);put(sy.SourceUpdateAnimation4086_Slot,c.mismatch=='slot'and 126 or 127);put(sy.SourceUpdateAnimation4086_TimeLo,c.mismatch=='time_low'and 65534 or 65535);put(sy.SourceUpdateAnimation4086_TimeHi,c.mismatch=='time_high'and 0 or 32768)
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();for _,key in ipairs({'a','x','y','d','dbr','ps','sp'})do cpu[key]=st['cpu.'..key]end end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,key in ipairs({'a','x','y','d','dbr'})do if cpu[key]~=st['cpu.'..key]then ctx=ctx+1 end end;if cpu.sp+3~=st['cpu.sp']or(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('ANIMPHASE|'..word(INDEX)..'|'..ctx..'|'..word(sy.SourceUpdateAnimation4086_State))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 apply='SourceUpdateAnimation4086_CheckWorldAck';append='';bindings={}
 if not a.ack:
  apply='AnimationPhasePrimeProbe';bindings['PRIME']='SourceUpdateAnimation4086_PrimeWorldPhase'
  append='''AnimationPhasePrimeProbe:
.a16
.i16
 php
 rep #$38
 jsl PRIME
 plp
 clc
 rtl
'''
 r=Reporter('M4-ANIMATION-PHASE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceUpdateAnimation4086_Ready',0xb60f,[],lua,r,append=append,bindings=bindings,batch_size=64)
 actual=[list(map(int,line.split('ANIMPHASE|',1)[1].split('|')))for line in log.splitlines()if 'ANIMPHASE|'in line]
 expected=[[i,0,0 if not a.ack and c['phase']==7 and c['ready']==0xb60f else c['state']]for i,c in enumerate(rows)]
 r.check('only fresh admitted animation issue resets state; stale and unsupported acknowledgments reject; CPU retained',actual==expected)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_UPDATE_ANIMATION_PHASE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,ack=a.ack,rom_sha256=hashlib.sha256(raw).hexdigest(),motu_gameplay_proven=False),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
