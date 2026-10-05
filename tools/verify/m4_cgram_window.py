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


def make_rom(count):
    rom=bytearray([0xff])*32768
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    store(0x4200,0);store(0x420c,0);store(0x2100,0x80)
    store(0x4370,0);store(0x4371,0x22);store(0x4374,0)
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
    rom[0x7fc0:0x7fd5]=b'M4 CGRAM WINDOW PROBE'
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bytes',type=int,default=50)
    args=parser.parse_args()
    folder=Path(__file__).resolve().parents[2]/'out/byor-motu-cgram-probe'
    folder.mkdir(exist_ok=True)
    rom=folder/'window.sfc';rom.write_bytes(make_rom(args.bytes))
    trace=folder/'writes.csv';trace.write_text('')
    lua=folder/'observer.lua'
    lua.write_text('''local n=0
emu.addMemoryCallback(function(a,v)
 if n>=100 then return end
 local s=emu.getState()
 if s['ppu.scanline']>0 and s['ppu.scanline']<224 then
  n=n+1
  emu.log('M4CGRAM|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],s['ppu.hClock'] or -1,s['ppu.cycle'] or -1,s['masterClock'],a,v,emu.read(0x4212,emu.memType.snesMemory)},','))
 end
end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        print(m.tool('run_frames',{'count':2}))
        state=m.tool('get_state')
    lines=[line.split('M4CGRAM|',1)[1] for line in (folder/'mesen.log').read_text().splitlines() if 'M4CGRAM|' in line]
    trace.write_text('\n'.join(lines)+'\n')
    rows=[[int(v) for v in line.split(',')] for line in lines]
    # getState's serialized PPU map lacks HClock in this binary. In the
    # reset field, normal scanlines are 1364 clocks; retain raw clocks too.
    derived=[r[4]-1364*r[1] for r in rows if r[0]==0]
    result=dict(rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),observed_writes=len(rows),
        reset_field_hclocks_derived=derived,
        writes_during_active_cgram_window=sum(88<=c<1096 for c in derived),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),cpu_state=state,
        scope='Polling fixture; includes CPU setup. Not production contention admission.')
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='reset_field_hclocks_derived'},indent=2))


if __name__=='__main__':main()
