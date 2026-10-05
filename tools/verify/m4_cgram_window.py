"""Bounded native DMA probe; independent fixture, no production ROM edits."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct
from types import SimpleNamespace
from unittest.mock import patch
from _harness import McpSession, MESEN_EXE, _free_tcp_port


def make_rom(count,audio_hdma=False):
    rom=bytearray([0xff])*32768
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    store(0x4200,0);store(0x420c,0);store(0x2100,0x80)
    store(0x4370,0);store(0x4371,0x22);store(0x4374,0)
    if audio_hdma:
        for address,value in [(0x4300,4),(0x4301,0x40),(0x4302,0),(0x4303,0xa0),(0x4304,0)]:store(address,value)
        # Arm during VBlank so channel 0 cursors initialize on the next field.
        code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
        store(0x420c,1)
    store(0x2100,15)
    # Wait for an active-to-HBlank edge, then start a contiguous DMA.
    loop=len(code)
    store(0x2121,128);store(0x4372,0);store(0x4373,0x90)
    store(0x4375,count);store(0x4376,0)
    code.extend(bytes.fromhex('ad 12 42 29 40 d0 f9'))
    code.extend(bytes.fromhex('ad 12 42 29 40 f0 f9'))
    store(0x420b,0x80)
    code.extend(bytes([0x4c,(0x8000+loop)&255,(0x8000+loop)>>8]))
    rom[:len(code)]=code
    rom[0x1000:0x1000+count]=bytes(i%128 for i in range(count))
    if audio_hdma:rom[0x2000:0x2000+1121]=bytes([0x81,0,0,0,57])*224+bytes([0])
    rom[0x7fc0:0x7fd5]=b'M4 CGRAM WINDOW PROBE'
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom)


def make_irq_rom(count,audio_hdma=False,timer=224):
    """Prepared HIRQ DMA, isolated fixture. New handler body lives in bank 1."""
    rom=bytearray([0xff])*131072
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    for address,value in [(0x4200,0),(0x420c,0),(0x2100,0x80),(0x4370,0),
                          (0x4371,0x22),(0x4372,0),(0x4373,0x80),(0x4374,2),(0x4376,0),
                          (0x4207,timer&255),(0x4208,timer>>8)]:store(address,value)
    if audio_hdma:
        for address,value in [(0x4300,4),(0x4301,0x40),(0x4302,0),(0x4303,0x90),(0x4304,3)]:store(address,value)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    if audio_hdma:store(0x420c,1)
    store(0x2100,15);store(0x4200,0x10);code.extend(bytes.fromhex('58 80 fe'))
    irq=bytearray.fromhex('ad 11 42 ad 12 42 29 80 d0 12')
    irq.extend(bytes([0xa9,count,0x8d,0x75,0x43,0xa9,128,0x8d,0x21,0x21,0xa9,128,0x8d,0x0b,0x42,0x40]))
    # Branch skips 15-byte active DMA block, landing on RTI.
    irq[9]=15
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x100:0x104]=bytes.fromhex('5c 00 82 01')
    rom[0x8000:0x8000+len(code)]=code;rom[0x8200:0x8200+len(irq)]=irq
    rom[0x10000:0x18000]=bytes([0x11,0x11])*16384
    rom[0x19000:0x19000+1121]=bytes([0x81,0,0,0,57])*224+bytes([0])
    rom[0x7fc0:0x7fd5]=b'M4 HIRQ CGRAM PROOF'.ljust(21)
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,7,0,1,0,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000);rom[0x7fee:0x7ff0]=struct.pack('<H',0x8100)
    return bytes(rom)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bytes',type=int,default=50)
    parser.add_argument('--audio-hdma',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--irq',action='store_true');parser.add_argument('--timer',type=int,default=224)
    args=parser.parse_args()
    folder=args.output.resolve() if args.output else Path(__file__).resolve().parents[2]/'out/byor-motu-cgram-probe'
    folder.mkdir(exist_ok=True)
    rom=folder/'window.sfc';rom.write_bytes(make_irq_rom(args.bytes,args.audio_hdma,args.timer) if args.irq else make_rom(args.bytes,args.audio_hdma))
    trace=folder/'writes.csv';trace.write_text('')
    lua=folder/'observer.lua'
    lua.write_text('''local n=0;local audio=0
emu.addMemoryCallback(function(a,v) if audio<64 then audio=audio+1;emu.log('M4APU|'..a..','..v) end end,emu.callbackType.write,0x2140,0x2143,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if n>=100 then return end
 local s=emu.getState()
    if s['ppu.frameCount']>=MINFRAME and s['ppu.scanline']>0 and s['ppu.scanline']<224 then
  n=n+1
  emu.log('M4CGRAM|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],s['ppu.hClock'] or -1,s['ppu.cycle'] or -1,s['masterClock'],a,v,emu.read(0x4212,emu.memType.snesMemory)},','))
 end
end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
'''.replace('MINFRAME','1' if args.audio_hdma else '0'))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        advancement=[];advanced=0;target=3 if args.audio_hdma else 2
        for _ in range(8):
            result=m.tool('run_frames',{'count':1});advancement.append(result)
            advanced+=result['framesAdvanced']
            if advanced>=target:break
        state=m.tool('get_state')
    lines=[line.split('M4CGRAM|',1)[1] for line in (folder/'mesen.log').read_text().splitlines() if 'M4CGRAM|' in line]
    trace.write_text('\n'.join(lines)+'\n')
    rows=[[int(v) for v in line.split(',')] for line in lines]
    # getState's serialized PPU map lacks HClock in this binary. In the
    # reset field, normal scanlines are 1364 clocks; retain raw clocks too.
    derived=[(r[4]+4*(r[0]//2))%1364 for r in rows]
    result=dict(rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),observed_writes=len(rows),
        field_hclocks_derived=derived,requested_cgram_bytes=args.bytes,
        audio_hdma_stress=args.audio_hdma,
        observed_audio_register_writes=sum('M4APU|' in line for line in (folder/'mesen.log').read_text().splitlines()),
        mechanism='HIRQ_PREPARED_DMA' if args.irq else 'POLLING_DMA',timer_dots=args.timer if args.irq else None,
        frame_advancement=advancement,requested_fields_completed=(advanced>=target),
        writes_during_active_cgram_window=sum(88<=c<1096 for c in derived),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),cpu_state=state,
        scope='Isolated timing fixture; includes CPU setup and optional 4-byte APU HDMA bus stress. Not production audio/contention admission.')
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='field_hclocks_derived'},indent=2))


if __name__=='__main__':main()
