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


def make_rom(count,audio_hdma=False,audio_rows=224):
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
    if audio_hdma:
        data=bytes([0x81,0,0,0,57])*audio_rows+bytes([0]);rom[0x2000:0x2000+len(data)]=data
    rom[0x7fc0:0x7fd5]=b'M4 CGRAM WINDOW PROBE'
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom)


def make_irq_rom(count,audio_hdma=False,timer=224,audio_rows=224,split_first_bytes=None,math_window_hdma=False,cpu_math_windows=False,fixed_window_controls=False):
    """Prepared HIRQ DMA, isolated fixture. New handler body lives in bank 1."""
    if math_window_hdma and cpu_math_windows:raise ValueError('CGRAM_WINDOW_TRANSFER_OWNERS_CONFLICT')
    if fixed_window_controls and not cpu_math_windows:raise ValueError('CGRAM_FIXED_WINDOW_CONTROLS_REQUIRE_CPU_WINDOWS')
    rom=bytearray([0xff])*131072
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    for address,value in [(0x4200,0),(0x420c,0),(0x2100,0x80),(0x4370,0),
                          (0x4371,0x22),(0x4372,0),(0x4373,0x80),(0x4374,2),(0x4376,0),
                          (0x4207,timer&255),(0x4208,timer>>8)]:store(address,value)
    if split_first_bytes is not None:
        if not 0<split_first_bytes<count or split_first_bytes%2 or count%2:raise ValueError('CGRAM_SPLIT_WORD_DOMAIN')
        for address,value in [(0x4350,0),(0x4351,0x22),(0x4352,0),(0x4353,0x80),(0x4354,2),(0x4356,0),
                              (0x4360,8),(0x4361,0x21),(0x4362,0),(0x4363,0x80),(0x4364,3),(0x4366,0)]:store(address,value)
    if audio_hdma:
        for address,value in [(0x4300,4),(0x4301,0x40),(0x4302,0),(0x4303,0x90),(0x4304,3)]:store(address,value)
    window_tables=[]
    if math_window_hdma or cpu_math_windows:
        from raster_math_windows import compile_mask
        masks=[[1]*256,[int(32<=x<=63 or 128<=x<=191)for x in range(256)],
               [int(not(32<=x<=63 or 128<=x<=191))for x in range(256)],[0]*256]
        if fixed_window_controls:masks[2]=[int(0<=x<=31 or 96<=x<=127)for x in range(256)]
        descriptors=[compile_mask(mask,fixed_window_controls)for mask in masks]
        window_tables=[bytearray()for _ in range(4)];cpu_descriptors=bytearray()
        for y in range(224):
            d=descriptors[y%4]
            for table,values in zip(window_tables,(sum(d['bounds'],[]),[d['wobjsel_color_bits']],[d['wobjlog_color_bits']],[0x10|(0x40 if y%8>=4 else 0)])):
                table.extend([0x81,*values])
            cpu_descriptors.extend([*sum(d['bounds'],[]),d['wobjsel_color_bits'],d['wobjlog_color_bits'],0x10|(0x40 if y%8>=4 else 0),0])
        cursor=0xa000
        for ch,(table,mode,dest)in ([]if cpu_math_windows else enumerate(zip(window_tables,(4,0,0,0),(0x26,0x25,0x2b,0x31)),1)):
            table.append(0)
            base=0x4300+16*ch
            for address,value in ((base,mode),(base+1,dest),(base+2,cursor&255),(base+3,cursor>>8),(base+4,3)):store(address,value)
            rom[0x18000+cursor-0x8000:0x18000+cursor-0x8000+len(table)]=table;cursor+=len(table)
        if cpu_math_windows:
            rom[0x1a000:0x1a000+len(cpu_descriptors)]=cpu_descriptors
            store(0x420d,1);code.extend(bytes.fromhex('a2 00 00'))
            if fixed_window_controls:store(0x2125,0xa0);store(0x212b,0)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    if audio_hdma or math_window_hdma:store(0x420c,(1 if audio_hdma else 0)|(0x1e if math_window_hdma else 0))
    store(0x2100,15);store(0x4200,0x10);code.extend(bytes.fromhex('58 80 fe'))
    irq=bytearray.fromhex('ad 11 42 ad 12 42 29 80 d0 12')
    irq.extend(bytes([0xa9,count,0x8d,0x75,0x43,0xa9,128,0x8d,0x21,0x21,0xa9,128,0x8d,0x0b,0x42,0x40]))
    # Branch skips 15-byte active DMA block, landing on RTI.
    irq[9]=15
    if split_first_bytes is not None:
        irq=bytearray.fromhex('ad 11 42 ad 12 42 29 80 d0 19')
        for address,value in [(0x4355,split_first_bytes),(0x4365,1),(0x4375,count-split_first_bytes),(0x2121,128),(0x420b,224)]:
            irq.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
        irq.append(0x40)
    if cpu_math_windows:
        if split_first_bytes is None:raise ValueError('CPU_WINDOW_TIMING_REQUIRES_SPLIT_PACKET')
        irq=bytearray.fromhex('ad 11 42 ad 12 42 29 80 d0 00 e0 00 07 90 04 a2 00 00 40')
        for address,value in [(0x4355,split_first_bytes),(0x4365,1),(0x4375,count-split_first_bytes),(0x2121,128),(0x420b,224)]:
            irq.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
        # Two word writes publish all four bounds. Three byte writes publish
        # selection, logic and mode. Data and handler use FastROM aliases.
        irq.extend(bytes.fromhex('c2 20 bf 00 a0 83 8d 26 21 bf 02 a0 83 8d 28 21 e2 20'))
        if not fixed_window_controls:irq.extend(bytes.fromhex('bf 04 a0 83 8d 25 21 bf 05 a0 83 8d 2b 21'))
        irq.extend(bytes.fromhex('bf 06 a0 83 8d 31 21'))
        irq.extend(bytes([0xe8]*8+[0x40]));irq[9]=len(irq)-1-10
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x100:0x104]=bytes.fromhex('5c 00 82 81'if cpu_math_windows else'5c 00 82 01')
    rom[0x8000:0x8000+len(code)]=code;rom[0x8200:0x8200+len(irq)]=irq
    rom[0x10000:0x18000]=bytes([0x11,0x11])*16384
    if split_first_bytes is not None:rom[0x18000]=192
    data=bytes([0x81,0,0,0,57])*audio_rows+bytes([0]);rom[0x19000:0x19000+len(data)]=data
    rom[0x7fc0:0x7fd5]=b'M4 HIRQ CGRAM PROOF'.ljust(21)
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,7,0,1,0,0])
    if cpu_math_windows:rom[0x7fd5]=0x30
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000);rom[0x7fee:0x7ff0]=struct.pack('<H',0x8100)
    return bytes(rom)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bytes',type=int,default=50)
    parser.add_argument('--audio-hdma',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--irq',action='store_true');parser.add_argument('--timer',type=int,default=224)
    parser.add_argument('--audio-rows',type=int,default=224)
    parser.add_argument('--min-scanline',type=int,default=1)
    parser.add_argument('--aggregate-packets',action='store_true')
    parser.add_argument('--split-first-bytes',type=int)
    parser.add_argument('--frame-attempts',type=int,default=8)
    parser.add_argument('--math-window-hdma',action='store_true')
    parser.add_argument('--cpu-math-windows',action='store_true')
    parser.add_argument('--fixed-window-controls',action='store_true')
    args=parser.parse_args()
    if not 1<=args.bytes<=255 or not 1<=args.audio_rows<=224 or not 1<=args.min_scanline<224 or not 1<=args.frame_attempts<=64:raise ValueError('CGRAM_PROBE_DOMAIN')
    if args.split_first_bytes is not None and not args.irq:raise ValueError('CGRAM_SPLIT_REQUIRES_IRQ')
    if args.math_window_hdma and not args.irq:raise ValueError('CGRAM_MATH_WINDOW_HDMA_REQUIRES_IRQ')
    if args.cpu_math_windows and(not args.irq or args.split_first_bytes is None or args.math_window_hdma):raise ValueError('CGRAM_CPU_WINDOWS_REQUIRE_EXCLUSIVE_SPLIT_IRQ')
    if args.fixed_window_controls and not args.cpu_math_windows:raise ValueError('CGRAM_FIXED_WINDOW_CONTROLS_REQUIRE_CPU_WINDOWS')
    folder=args.output.resolve() if args.output else Path(__file__).resolve().parents[2]/'out/byor-motu-cgram-probe'
    folder.mkdir(exist_ok=True)
    rom=folder/'window.sfc';rom.write_bytes(make_irq_rom(args.bytes,args.audio_hdma,args.timer,args.audio_rows,args.split_first_bytes,args.math_window_hdma,args.cpu_math_windows,args.fixed_window_controls) if args.irq else make_rom(args.bytes,args.audio_hdma,args.audio_rows))
    trace=folder/'writes.csv';trace.write_text('')
    lua=folder/'observer.lua'
    lua.write_text('''local n=0;local audio=0;local packet=nil;local cgramAddress=0;local cgramHigh=false
emu.addMemoryCallback(function(a,v)cgramAddress=v;cgramHigh=false end,emu.callbackType.write,0x2121,0x2121,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if v~=DMAMASK then return end
 local s=emu.getState()
 if s['ppu.frameCount']>=MINFRAME and s['ppu.scanline']>=MINLINE and s['ppu.scanline']<224 then packet={count=0,bad=0,commits=0,badCommits=0,ranges={},frame=s['ppu.frameCount'],line=s['ppu.scanline']}else packet=nil end
end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) if audio<64 then audio=audio+1;emu.log('M4APU|'..a..','..v) end end,emu.callbackType.write,0x2140,0x2143,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 local s=emu.getState()
 local high=cgramHigh;cgramHigh=not cgramHigh
 if AGGREGATE and packet then
  local clock=(s.masterClock+4*(s['ppu.frameCount']//2))%1364
  if packet.count==0 then packet.first=clock;packet.start=s.masterClock end
  local r=packet.ranges[#packet.ranges];if not r or r.address~=cgramAddress then r={address=cgramAddress,count=0};table.insert(packet.ranges,r)end;r.count=r.count+1
  packet.count=packet.count+1;if clock>=88 and clock<1096 then packet.bad=packet.bad+1 end
  if high then
   if packet.commits==0 then packet.firstCommit=clock;packet.commitStart=s.masterClock end
   packet.commits=packet.commits+1;packet.lastCommit=clock;packet.commitSpan=s.masterClock-packet.commitStart
   if clock>=88 and clock<1096 then packet.badCommits=packet.badCommits+1 end
  end
  if packet.count==BYTECOUNT then emu.log('M4PACKET|'..table.concat({packet.frame,packet.line,packet.count,packet.bad,packet.first,clock,s.masterClock-packet.start},','));emu.log('M4COMMITS|'..table.concat({packet.frame,packet.line,packet.count,packet.commits,packet.badCommits,packet.firstCommit or -1,packet.lastCommit or -1,packet.commitSpan or 0},','));if SPLIT then local ranges={packet.frame,packet.line};for _,r in ipairs(packet.ranges)do table.insert(ranges,r.address);table.insert(ranges,r.count)end;emu.log('M4RANGES|'..table.concat(ranges,','))end;packet=nil end
 end
 if n>=100 then return end
    if s['ppu.frameCount']>=MINFRAME and s['ppu.scanline']>=MINLINE and s['ppu.scanline']<224 then
  n=n+1
  emu.log('M4CGRAM|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],s['ppu.hClock'] or -1,s['ppu.cycle'] or -1,s['masterClock'],a,v,emu.read(0x4212,emu.memType.snesMemory)},','))
 end
end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
'''.replace('SPLIT',str(args.split_first_bytes is not None).lower()).replace('DMAMASK','224' if args.split_first_bytes is not None else '128').replace('MINFRAME','1' if args.audio_hdma else '0').replace('MINLINE',str(args.min_scanline)).replace('AGGREGATE',str(args.aggregate_packets).lower()).replace('BYTECOUNT',str(args.bytes)))
    if args.cpu_math_windows:
        with lua.open('a')as script:
            script.write('''\nemu.addMemoryCallback(function(a,v)
 local s=emu.getState();if s['ppu.frameCount']>=1 and s['ppu.scanline']<225 then
 emu.log('M4CPUWINDOW|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],(s.masterClock+4*(s['ppu.frameCount']//2))%1364,s.masterClock,v},','))end
end,emu.callbackType.write,0x2131,0x2131,emu.cpuType.snes,emu.memType.snesMemory)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        advancement=[];advanced=0;target=3 if args.audio_hdma else 2
        for _ in range(args.frame_attempts):
            result=m.tool('run_frames',{'count':1});advancement.append(result)
            advanced+=result['framesAdvanced']
            if advanced>=target:break
        state=m.tool('get_state')
        cgram=m.read_memory('SnesCgRam',0,512)
    lines=[line.split('M4CGRAM|',1)[1] for line in (folder/'mesen.log').read_text().splitlines() if 'M4CGRAM|' in line]
    trace.write_text('\n'.join(lines)+'\n')
    rows=[[int(v) for v in line.split(',')] for line in lines]
    packets=[[int(v)for v in line.split('M4PACKET|',1)[1].split(',')]for line in (folder/'mesen.log').read_text().splitlines()if 'M4PACKET|'in line]
    if args.aggregate_packets:(folder/'packets.json').write_text(json.dumps(packets)+'\n')
    ranges=[[int(v)for v in line.split('M4RANGES|',1)[1].split(',')]for line in (folder/'mesen.log').read_text().splitlines()if 'M4RANGES|'in line]
    if ranges:(folder/'ranges.json').write_text(json.dumps(ranges)+'\n')
    commits=[[int(v)for v in line.split('M4COMMITS|',1)[1].split(',')]for line in (folder/'mesen.log').read_text().splitlines()if 'M4COMMITS|'in line]
    cpu_windows=[[int(v)for v in line.split('M4CPUWINDOW|',1)[1].split(',')]for line in (folder/'mesen.log').read_text().splitlines()if 'M4CPUWINDOW|'in line]
    if cpu_windows:(folder/'cpu-window-timing.json').write_text(json.dumps(cpu_windows)+'\n')
    owned_words=list(range(128,128+(args.split_first_bytes or args.bytes)//2))
    if args.split_first_bytes is not None:owned_words+=list(range(192,192+(args.bytes-args.split_first_bytes)//2))
    owned_identity=all(struct.unpack_from('<H',cgram,2*i)[0]==0x1111 for i in owned_words)if args.irq else None
    (folder/'cgram.bin').write_bytes(cgram)
    if commits:(folder/'commits.json').write_text(json.dumps(commits)+'\n')
    # getState's serialized PPU map lacks HClock in this binary. In the
    # reset field, normal scanlines are 1364 clocks; retain raw clocks too.
    derived=[(r[4]+4*(r[0]//2))%1364 for r in rows]
    result=dict(rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),observed_writes=len(rows),
        field_hclocks_derived=derived,requested_cgram_bytes=args.bytes,
        audio_hdma_stress=args.audio_hdma,
        math_window_hdma_stress=args.math_window_hdma,math_window_hdma_channels=[1,2,3,4]if args.math_window_hdma else[],
        math_window_hdma_bytes_per_line=7 if args.math_window_hdma else 0,
        cpu_math_window_descriptors=args.cpu_math_windows,cpu_math_window_rows_observed=len(cpu_windows),
        cpu_math_window_last_write_latest_hclock=max((r[2]for r in cpu_windows),default=None),
        cpu_window_live_pixel_deadline_admitted=False,
        fixed_positive_union_window_controls=args.fixed_window_controls,
        cpu_math_window_descriptor_bytes_per_line=(5 if args.fixed_window_controls else 7)if args.cpu_math_windows else 0,
        final_owned_cgram_identity_verified=owned_identity,cgram_sha256=hashlib.sha256(cgram).hexdigest(),
        split_first_bytes=args.split_first_bytes,dma_channels=[5,6,7] if args.split_first_bytes is not None else [7],
        dma_cgram_address_bytes=1 if args.split_first_bytes is not None else 0,
        audio_hdma_rows=args.audio_rows if args.audio_hdma else 0,minimum_observed_scanline=args.min_scanline,
        observed_audio_register_writes=sum('M4APU|' in line for line in (folder/'mesen.log').read_text().splitlines()),
        mechanism='HIRQ_PREPARED_DMA' if args.irq else 'POLLING_DMA',timer_dots=args.timer if args.irq else None,
        frame_advancement=advancement,requested_fields_completed=(advanced>=target),
        writes_during_active_cgram_window=sum(88<=c<1096 for c in derived),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),cpu_state=state,
        complete_dma_packets_observed=len(packets),complete_range_traces_observed=len(ranges),
        complete_commit_traces_observed=len(commits),aggregate_high_byte_commits=sum(p[3]for p in commits),
        aggregate_active_window_high_byte_commits=sum(p[4]for p in commits),
        commit_trace_packet_identity_verified=(len(commits)==len(packets)and bool(commits)and all(c[:3]==p[:3] and c[3]==args.bytes//2 for c,p in zip(commits,packets))),
        split_range_identity_verified=(len(ranges)==len(packets) and bool(ranges) and all(row[2:]==[128,args.split_first_bytes,192,args.bytes-args.split_first_bytes] for row in ranges)) if args.split_first_bytes is not None else None,aggregate_active_window_writes=sum(p[3]for p in packets),
        scope='Isolated timing fixture; includes CPU setup and optional 4-byte APU HDMA bus stress. Not production audio/contention admission.')
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='field_hclocks_derived'},indent=2))


if __name__=='__main__':main()
