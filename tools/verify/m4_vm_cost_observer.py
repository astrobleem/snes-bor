"""Bounded native VM execution spans, separate from host checkpoint waiting."""
import json
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from _harness import McpSession
ARM = 0x7ff65e


def observed_session(output, symbols, instruction_count):
    script=output/'vm_cost.lua'
    script.write_text('''local active=false;local start=0;local frame=0;local count=0;local spans=0
local mt=emu.memType.snesMemory
local function word(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
emu.addMemoryCallback(function()
 if word(ARMADDRESS)==0xb48c then
  emu.write(ARMADDRESS,0,mt);emu.write(ARMADDRESS+1,0,mt);emu.breakExecution()
 end
end,emu.callbackType.exec,RUN,RUN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if spans>=32 or word(INSTRCOUNT)~=EXPECTED or emu.read(STATUS,mt)>=4 then return end
 local s=emu.getState();active=true;start=s.masterClock;frame=s['ppu.frameCount'];count=0
end,emu.callbackType.exec,RUN+3,RUN+3,emu.cpuType.snes,mt)
emu.addMemoryCallback(function() if active then count=count+1 end end,
 emu.callbackType.exec,FETCH,FETCH,emu.cpuType.snes,mt)
emu.addMemoryCallback(function(addr,value)
 if not active or (value~=3 and value~=4 and value~=5) then return end
 local s=emu.getState();active=false;spans=spans+1
 emu.log('M4VMCPU|{"start_clock":'..start..',"end_clock":'..s.masterClock..
 ',"master_clocks":'..(s.masterClock-start)..',"start_field":'..frame..
 ',"end_field":'..s['ppu.frameCount']..',"instructions":'..count..
 ',"status":'..value..',"error":'..word(ERROR)..',"native_id":'..word(NATIVE)..'}')
end,emu.callbackType.write,STATUS,STATUS,emu.cpuType.snes,mt)
'''.replace('ARMADDRESS',str(ARM)).replace('INSTRCOUNT',str(symbols['VmState_InstrCount']))
        .replace('EXPECTED',str(instruction_count)).replace('STATUS',str(symbols['VmState_Status']))
        .replace('FETCH',str(symbols['Vm_Fetch'])).replace('RUN',str(symbols['Vm_Run']))
        .replace('ERROR',str(symbols['VmState_Error'])).replace('NATIVE',str(symbols['VmCall_TargetId'])))

    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(script.resolve())],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    return Observed


def spans(log):
    return [json.loads(line.split('M4VMCPU|',1)[1]) for line in log.read_text(errors='replace').splitlines()
            if 'M4VMCPU|' in line]
