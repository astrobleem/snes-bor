"""Combine prepared palette DMA and CPU windows with independent pixel replay.

Generic component fixture, not a source HBreath or production lease proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from _harness import McpSession,MESEN_EXE,_free_tcp_port


def fixture():
    oam=bytearray(544)
    for i in range(128):oam[4*i+1]=240
    for row in range(4):
        for col in range(4):
            i=row*4+col
            oam[4*i:4*i+4]=bytes([96+col*32,80+row*32,0,0x30|(8 if col%2 else 0)])
            oam[512+i//4]|=2<<((i%4)*2)
    palette=bytearray(512)
    struct.pack_into('<H',palette,2,5<<5)
    # Different initial words make the pixel oracle sensitive to omitted DMA.
    for index in (129,193):struct.pack_into('<H',palette,index*2,0x2222)
    objchr=bytes([255,0]*8+[0]*16)*64
    bgchr=bytes([255,0]*8+[0]*16)
    assets={0x1c000:objchr,0x1c800:bgchr,0x1d000:bytes(2048),0x1d800:palette,0x1da00:oam}
    code=bytearray()
    def store(a,v):code.extend([0xa9,v,0x8d,a&255,a>>8])
    def dma(source,dest,n,mode,vram=None):
        if vram is not None:store(0x2116,vram&255);store(0x2117,vram>>8)
        for a,v in ((0x4310,mode),(0x4311,dest),(0x4312,source&255),(0x4313,source>>8),(0x4314,3),(0x4315,n&255),(0x4316,n>>8),(0x420b,2)):store(a,v)
    store(0x2115,128)
    dma(0xc000,0x18,len(objchr),1,0);dma(0xc800,0x18,len(bgchr),1,0x2000)
    dma(0xd000,0x18,2048,1,0x7000);store(0x2121,0);dma(0xd800,0x22,512,0)
    store(0x2102,0);store(0x2103,0);dma(0xda00,4,544,0)
    for a,v in ((0x2101,0x20),(0x2105,1),(0x2107,0x70),(0x210b,2),
                (0x210d,0),(0x210d,0),(0x210e,255),(0x210e,255),
                (0x212c,0x10),(0x212d,1),(0x212e,0),(0x212f,0),
                (0x2130,0x12),(0x2132,0xe0),(0x2133,0)):store(a,v)
    expected=np.zeros((224,256),dtype='<u2')
    masks=[[1]*256,[int(32<=x<=63 or 128<=x<=191)for x in range(256)],
           [int(0<=x<=31 or 96<=x<=127)for x in range(256)],[0]*256]
    for y in range(80,208):
        for x in range(96,224):
            enabled=((x-96)//32)%2==1 and masks[y%4][x]
            half=y%8>=4
            expected[y,x]=(8|(6<<5)|(2<<10))if enabled and half else (17|(13<<5)|(4<<10))if enabled else 0x1111
    return bytes(code),assets,expected,bytes(oam),bytes(palette)


def main():
    from m4_cgram_window import make_irq_rom
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--timer',type=int,default=156);p.add_argument('--preserve-context',action='store_true');p.add_argument('--dma-windows',action='store_true')
    p.add_argument('--context-widths',choices=('16/16','8/16','16/8','8/8'),default='16/16');p.add_argument('--decimal-context',action='store_true');args=p.parse_args()
    if (args.context_widths!='16/16'or args.decimal_context)and not args.dma_windows:raise ValueError('CONTEXT_VARIANTS_REQUIRE_DMA_WINDOWS')
    folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=make_irq_rom(38,True,args.timer,73,24,False,True,True,True,args.preserve_context)
    if args.dma_windows:
        from m4_cgram_dma_windows import compile_rom
        raw=compile_rom(args.timer,args.context_widths,args.decimal_context)
    _,_,expected,oam,initial=fixture();rom=folder/'proof.sfc';rom.write_bytes(raw)
    if args.dma_windows:
        from m4_cgram_dma_windows import expected_frame,palette_color
        expected=expected_frame()
    lua=folder/'observer.lua'
    lua.write_text('''local packet=nil;local high=false;local address=0
emu.addMemoryCallback(function(a,v)address=v;high=false end,emu.callbackType.write,0x2121,0x2121,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if v==224 then local s=emu.getState();packet={frame=s['ppu.frameCount'],line=s['ppu.scanline'],n=0,bad=0}end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if not packet then return end
 local s=emu.getState();local h=(s.masterClock+4*(s['ppu.frameCount']//2))%1364
 if high then
  packet.n=packet.n+1;if h>=88 and h<1096 then packet.bad=packet.bad+1 end
  if packet.n==1 then packet.first=s.masterClock;packet.firstH=h end
  if packet.n==19 then emu.log('PIXPACKET|'..table.concat({packet.frame,packet.line,packet.n,packet.bad,s.masterClock-packet.first,packet.firstH,h},','));packet=nil end
 end
 high=not high
end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)local s=emu.getState();if s['ppu.scanline']<224 then emu.log('PIXWINDOW|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],(s.masterClock+4*(s['ppu.frameCount']//2))%1364,v},','))end end,emu.callbackType.write,0x2131,0x2131,emu.cpuType.snes,emu.memType.snesMemory)
'''.replace('v==224','v==206'if args.dma_windows else'v==224'))
    if args.preserve_context or args.dma_windows:
        # Observe immediately before RTI, after explicit register restoration.
        handler=raw[0x8600:0x8700];ret=0x818600+handler.index(bytes.fromhex('68 40'))+1
        with lua.open('a')as script:
            script.write(f'''emu.addMemoryCallback(function()local s=emu.getState();emu.log('PIXCONTEXT|'..table.concat({{s['cpu.a'],s['cpu.x'],s['cpu.y'],s['cpu.d'],s['cpu.dbr'],s['cpu.sp']}},','))end,emu.callbackType.exec,{ret},{ret},emu.cpuType.snes,emu.memType.snesMemory)\n''')
            script.write(f'''local irqEntry=0
emu.addMemoryCallback(function()irqEntry=emu.getState().masterClock end,emu.callbackType.exec,0x818600,0x818600,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()local s=emu.getState();emu.log('PIXIRQTIME|'..table.concat({{s['ppu.frameCount'],s['ppu.scanline'],s.masterClock-irqEntry}},','))end,emu.callbackType.exec,{ret},{ret},emu.cpuType.snes,emu.memType.snesMemory)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kw):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kw)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as session:
        advancement=[];completed=0
        for _ in range(32):
            result=session.tool('run_frames',{'count':1});advancement.append(result)
            if result['framesAdvanced']not in (0,1):raise AssertionError('PIXEL_FRAME_OVERRUN')
            completed+=result['framesAdvanced']
            if completed==3:break
        if completed!=3:
            (folder/'frame-advancement-failure.json').write_text(json.dumps(advancement,indent=2)+'\n')
            raise AssertionError('PIXEL_FRAME_ADVANCEMENT')
        shot=session.tool('take_screenshot',{'format':'path'})
        observed_oam=session.read_memory('SnesSpriteRam',0,544);cgram=session.read_memory('SnesCgRam',0,512)
        ppu=session.get_ppu_state()
        cpu=session.get_cpu_state()
    retained=folder/'screenshot.png';shutil.copyfile(shot['path'],retained)
    rgb=np.asarray(Image.open(retained).convert('RGB'),dtype=np.uint16)
    actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
    log=(folder/'mesen.log').read_text().splitlines()
    packets=[list(map(int,line.split('PIXPACKET|')[1].split(',')))for line in log if 'PIXPACKET|'in line]
    windows=[list(map(int,line.split('PIXWINDOW|')[1].split(',')))for line in log if 'PIXWINDOW|'in line]
    contexts=[list(map(int,line.split('PIXCONTEXT|')[1].split(',')))for line in log if 'PIXCONTEXT|'in line]
    irq_times=[list(map(int,line.split('PIXIRQTIME|')[1].split(',')))for line in log if 'PIXIRQTIME|'in line]
    index8=args.dma_windows and args.context_widths.endswith('/8')
    wanted_context=[0x1234,0x78 if index8 else 0x5678,0xcd if index8 else 0xabcd,0x2345,0x40,0x1ffb]
    context_identity=(bool(contexts)and all(r==wanted_context for r in contexts))if args.preserve_context or args.dma_windows else None
    wanted_status=1|(0x20 if args.context_widths.startswith('8/')else 0)|(0x10 if index8 else 0)|(8 if args.decimal_context else 0)
    status_identity=(cpu['ps']==wanted_status)if args.dma_windows else None
    packets=[r for r in packets if r[0]>=1];windows=[r for r in windows if r[0]>=1]
    palette=bytearray(initial)
    for i in [*range(128,140),*range(192,199)]:struct.pack_into('<H',palette,i*2,palette_color(223)if args.dma_windows else 0x1111)
    identity=actual.shape==expected.shape and np.array_equal(actual,expected)
    complete=len(packets)==447 and all(len([r for r in packets if r[0]==field])==149 for field in (1,2,3))
    safe=complete and all(r[3]==0 for r in packets)
    visible_windows=[r for r in windows if 81<=r[1]<=208]
    result=dict(schema='BYOR_CPU_WINDOWS_CGRAM_PIXEL_COMPONENT_V1',status='PASS'if identity and safe and cgram==palette and observed_oam==oam and context_identity is not False and status_identity is not False else'FAIL',
        pixel_identity_verified=identity,pixel_mismatches=int(np.count_nonzero(actual!=expected))if actual.shape==expected.shape else None,
        palette_identity_verified=cgram==palette,oam_identity_verified=observed_oam==oam,
        packets=len(packets),high_commits=sum(r[2]for r in packets),unsafe_high_commits=sum(r[3]for r in packets),peak_commit_span=max((r[4]for r in packets),default=None),
        descriptors=len(windows),latest_descriptor_hclock=max((r[2]for r in windows),default=None),
        visible_obj_descriptor_latest_hclock=max((r[2]for r in visible_windows),default=None),
        complete_packet_fields_verified=complete,
        timer=args.timer,first_palette_row=75,first_obj_row=80,first_math_obj_x=128,
        oam_entries=16,peak_sprites=4,peak_slivers=16,dma_channels=[1,2,3,6,7]if args.dma_windows else[5,6,7],dummy_apu_hdma_channel=0,dummy_apu_hdma_rows=73,
        rom_sha256=hashlib.sha256(raw).hexdigest(),expected_rgb555_sha256=hashlib.sha256(expected.tobytes()).hexdigest(),
        source_hbreath_proven=False,production_interrupt_context_proven=False,no_color_reduction=True,frame_advancement=advancement,ppu=ppu,cpu=cpu,
        synthetic_register_context_preserved=context_identity,context_observations=len(contexts),cursor_in_private_wram=args.preserve_context and not args.dma_windows,
        automatic_dma_descriptor_cursors=args.dma_windows,window_transfer='DMA'if args.dma_windows else'CPU',
        per_line_palette_payload_changes=args.dma_windows,
        interrupted_context_widths=args.context_widths,interrupted_decimal_context=args.decimal_context,final_context_status_verified=status_identity,
        irq_entry_to_rti_peak_master_clocks=max((r[2]for r in irq_times),default=None),
        irq_timing_excludes_hardware_entry_gateway_and_rti=True)
    for name,data in [('packets.json',packets),('windows.json',windows),('report.json',result)]: (folder/name).write_text(json.dumps(data,indent=2)+'\n')
    (folder/'expected.rgb555').write_bytes(expected.tobytes());(folder/'cgram.bin').write_bytes(cgram);(folder/'oam.bin').write_bytes(observed_oam)
    if contexts:(folder/'contexts.json').write_text(json.dumps(contexts)+'\n')
    if irq_times:(folder/'irq-times.json').write_text(json.dumps(irq_times)+'\n')
    print(json.dumps(result,indent=2))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
