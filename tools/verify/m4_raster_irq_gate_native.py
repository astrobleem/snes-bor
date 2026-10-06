"""Private native proof of reused IRQ gateway and post-NMI palette ownership."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
from unittest.mock import patch
import m4_bg_components_native as bg
from _harness import McpSession
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_raster_irq import emit,fetch_prologue
from actor_s5_entity_fixture import symbols


def combine(raw,report,folder,timer):
    asm=folder/'gate.pasm'
    asm.write_text('.snes\nStageWater_Nmi = $018C00\n.bank 28\n.org $9000\nVm_FetchSource:\n.a16\n.i16\n'+fetch_prologue()+'    plp\n    rtl\nVm_FetchSource_End:\n'+emit())
    command=[r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(asm),'--output',str(folder/'gate.bin'),'--symbols',str(folder/'gate.sym'),'--no-pansy']
    process=subprocess.run(command,capture_output=True,text=True)
    (folder/'poppy.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise ValueError('GATE_ASSEMBLY_FAILED')
    sy=symbols(folder/'gate.sym');binary=(folder/'gate.bin').read_bytes()
    if [sy[k] for k in ('SourceRasterNmiGate','SourceRasterIrqGate','SourceRasterNmiAfter')]!=[0x278000,0x279000,0x27b000]:raise ValueError('GATE_FIXED_FASTROM_ABI')
    rom=bytearray(raw)+bytearray([255])*(2097152-len(raw))
    start=28*32768+4096;end=start+sy['Vm_FetchSource_End']-sy['Vm_FetchSource']
    rom[start:end]=binary[start:end];rom[39*32768:len(binary)]=binary[39*32768:]
    prefix=rom[0x8000:0x8400];marker=prefix.find(bytes.fromhex('a9 0f 8d 00 21'))
    if marker<0:raise ValueError('GATE_BOOT_PREFIX')
    code=bytearray(prefix[:marker])
    def word(address,value):code.extend(bytes([0xa9,value&255,value>>8,0x8f,address&255,(address>>8)&255,address>>16]))
    code.extend(bytes.fromhex('c2 30'))
    for address,value in [(0x7ff840,0xb4b0),(0x7ff842,0),(0x7ff844,0xa800),(0x7ff846,5),(0x7ff848,0x8000),(0x7ff84a,6),
                          (0x7ff84c,report['span']*2),(0x7ff84e,0x9008),(0x7ff850,5),(0x7ff852,0x81),(0x7ff854,0),(0x7ff856,0),(0x7ff85a,0)]:word(address,value)
    code.extend(bytes.fromhex('e2 20 a9 01 8d 0d 42 a9 0f 8d 00 21 a9 81 8d 00 42 58'))
    # Exercise both width modes, nonzero direct page and WRAM DBR. The gate
    # cannot assume the interrupted source VM has the boot register context.
    code.extend(bytes.fromhex('c2 30 a9 34 12 5b f4 7e 7e ab ab'))
    loop=0x8000+len(code)
    code.extend(bytes.fromhex('a9 34 12 a2 78 56 a0 bc 9a 22 30 81 00 e2 30 a9 ef a2 ab a0 cd 38 22 30 81 00 c2 30 18'))
    code.extend(bytes([0x5c,loop&255,loop>>8,0x81]))
    if len(code)>0x400:raise ValueError('GATE_BOOT_OVERLAP')
    rom[0x8000:0x8400]=bytes([255])*1024;rom[0x8000:0x8000+len(code)]=code
    # Contract-shaped private stubs; production bank-zero bytes are untouched.
    rom[0x100:0x105]=bytes.fromhex('22 00 90 9c 60')
    rom[0x120:0x128]=bytes.fromhex('22 00 80 a7 20 00 82 40')
    rom[0x130:0x134]=bytes.fromhex('20 00 81 6b')
    # Stand-in NMI deliberately replaces DMA7 mode/destination/address/count.
    core=bytearray.fromhex('08 c2 30 48 da 8b e2 20 a9 00 48 ab')
    for address,value in [(0x4370,1),(0x4371,0x18),(0x4372,0x34),(0x4373,0x92),(0x4374,2),(0x4375,0x80),(0x4376,0x03)]:core.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    core.extend(bytes.fromhex('ab c2 30 fa 68 28 60'));rom[0x200:0x200+len(core)]=core
    rom[0x8c00]=0x6b
    rom[0x7fea:0x7fec]=struct.pack('<H',0x8120);rom[0x7fee:0x7ff0]=struct.pack('<H',0x8100)
    rom[0x7fd5]=0x30;rom[0x7fd7]=11
    return bytes(rom),sy


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--timer',type=int,default=76);a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);compile_base=bg.compile_rom;details={}
    def compile_gate(*args,**kwargs):
        raw,trace,resources=compile_base(*args,**kwargs);raw,sy=combine(raw,json.loads(a.report.read_text()),folder,a.timer)
        details.update(symbols=sy)
        resources.update(irq_entry_prg_offset=39*32768+4096,irq_exit_prg_offset=(sy['SourceRasterIrqReturn']>>16)*32768+(sy['SourceRasterIrqReturn']&65535)-32768,
                         reused_irq_gateway=True,post_nmi_hook=True,production_bank0_growth=0)
        return raw,trace,resources
    class Extra(McpSession):
        def __enter__(self):
            sy=details['symbols'];end=(sy['SourceRasterAfterReturn']>>16)*32768+(sy['SourceRasterAfterReturn']&65535)-32768
            with (folder/'observer.lua').open('a') as f:
                f.write('''\nemu.addMemoryCallback(function(a,v) restoring=(v==1) end,emu.callbackType.write,0x7ff85c,0x7ff85c,emu.cpuType.snes,emu.memType.snesMemory)
local pending={};local started={};local counts={IRQ=0,NMI=0};local faults=0;local irqpeak=0;local unsafe=0
local function snapshot()
 local s=emu.getState();local r={}
 for _,k in ipairs({'a','x','y','d','dbr','sp'}) do r[k]=s['cpu.'..k] end
 for i=1,4 do r['stack'..i]=emu.read((r.sp+i)%65536,emu.memType.snesMemory) end
 return r
end
local function enter(kind)
 if pending[kind] then faults=faults+1 end
 pending[kind]=snapshot()
 started[kind]=emu.getState()['masterClock']
end
local function leave(kind)
 local old=pending[kind];local new=snapshot()
 if not old then faults=faults+1 else
  for k,v in pairs(old) do if new[k]~=v then faults=faults+1;emu.log('GATECONTEXTFAIL|'..kind..'|'..k..'|'..v..'|'..new[k]) end end
  counts[kind]=counts[kind]+1
  if kind=='IRQ' then irqpeak=math.max(irqpeak,emu.getState()['masterClock']-started[kind]) end
 end
 pending[kind]=nil
end
emu.addMemoryCallback(function() if (emu.getState()['cpu.ps'] & 4)~=0 then enter('IRQ') end end,emu.callbackType.exec,256,256,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() enter('NMI') end,emu.callbackType.exec,288,288,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() leave('IRQ') end,emu.callbackType.exec,IRQRETURN,IRQRETURN,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() leave('NMI') end,emu.callbackType.exec,NMIRETURN,NMIRETURN,emu.cpuType.snes,emu.memType.snesPrgRom)
local databyte=0
emu.addMemoryCallback(function() databyte=0 end,emu.callbackType.write,0x2121,0x2121,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 databyte=databyte+1
 if counts.NMI>=1 and not restoring and (databyte==1 or databyte==DATASIZE) then
  local s=emu.getState();local h=(s.masterClock+4*math.floor(s['ppu.frameCount']/2))%1364
  if s['ppu.scanline']<225 and h>=88 and h<1096 then
   unsafe=unsafe+1;if unsafe<8 then emu.log('GATEUNSAFE|'..s['ppu.frameCount']..','..s['ppu.scanline']..','..h) end
  end
 end
end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() emu.log('GATECONTEXT|'..counts.IRQ..','..counts.NMI..','..faults..','..irqpeak..','..unsafe) end,emu.eventType.endFrame)
'''.replace('IRQRETURN',str(39*32768+(sy['SourceRasterIrqReturn']&65535)-32768)).replace('NMIRETURN',str(end)).replace('DATASIZE',str(json.loads(a.report.read_text())['span']*2)))
            return super().__enter__()
        def __exit__(self,*args):
            raw=self.read_memory('SnesMemory',0x7ff840,28)
            raw=bytes.fromhex(raw['hex']) if isinstance(raw,dict) else bytes(raw)
            (folder/'gate-state.bin').write_bytes(raw)
            return super().__exit__(*args)
    argv=['m4_bg_components_native','--report',str(a.report),'--assets',str(a.report.parent),'--output',str(folder),'--timer',str(a.timer)]
    with patch.object(bg,'compile_rom',compile_gate),patch.object(bg,'McpSession',Extra),patch.object(sys,'argv',argv):
        try:bg.main()
        except SystemExit as error:
            if error.code!=1:raise
    r=json.loads((folder/'result.json').read_text());state=(folder/'gate-state.bin').read_bytes()
    lines=[line.split('GATECONTEXT|',1)[1] for line in (folder/'mesen.log').read_text().splitlines() if 'GATECONTEXT|' in line]
    counts=[int(v) for v in lines[-1].split(',')] if lines else [0,0,-1,0,-1]
    r.update(gate_state=state.hex(),gate_fault=int.from_bytes(state[22:24],'little'),gate_frames=int.from_bytes(state[26:28],'little'),
             irq_context_checks=counts[0],nmi_context_checks=counts[1],context_faults=counts[2],
             peak_gateway_to_rti_master_clocks=counts[3],
             all_field_unsafe_data_writes=counts[4],
             scope='Private contract-shaped interrupt stubs, palette traces and pixels. No production installation, real NMI/DMA load or TAD protocol admission.')
    r['pass']=r['pass'] and r['gate_fault']==0 and r['gate_frames']>=2 and counts[0]>=224 and counts[1]>=2 and counts[2]==0 and counts[4]==0
    (folder/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
    if not r['pass']:raise SystemExit(1)


if __name__=='__main__':main()
