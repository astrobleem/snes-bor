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
    p.add_argument('--fixed-color',type=lambda s:int(s,0),help='Use a constant COLDATA operand and cycle all four exact math modes in the DMA-window component.')
    p.add_argument('--dynamic-fixed-color',action='store_true',help='Publish three COLDATA bytes per scanline using the otherwise unused DMA channel 4.')
    p.add_argument('--context-widths',choices=('16/16','8/16','16/8','8/8'),default='16/16');p.add_argument('--decimal-context',action='store_true');p.add_argument('--general-windows',action='store_true');p.add_argument('--three-ranges',action='store_true');p.add_argument('--fixed-math-mode',action='store_true');p.add_argument('--retire-audio-hdma',action='store_true');p.add_argument('--fetch-gateway',action='store_true');p.add_argument('--direct-fetch-route',action='store_true');p.add_argument('--compact-visible-handler',action='store_true');args=p.parse_args()
    if args.fixed_color is not None and not args.dma_windows:raise ValueError('FIXED_COLOR_REQUIRES_DMA_WINDOWS')
    if args.dynamic_fixed_color and(args.fixed_color is None or args.fixed_math_mode):raise ValueError('DYNAMIC_FIXED_COLOR_REQUIRES_CHANGING_DMA_CONTROLS')
    if args.compact_visible_handler and not args.dma_windows:raise ValueError('COMPACT_VISIBLE_HANDLER_REQUIRES_DMA_WINDOWS')
    if args.direct_fetch_route and not args.dma_windows:raise ValueError('DIRECT_FETCH_ROUTE_REQUIRES_DMA_WINDOWS')
    if args.fetch_gateway and not args.dma_windows:raise ValueError('FETCH_GATEWAY_REQUIRES_DMA_WINDOWS')
    if args.retire_audio_hdma and not args.dma_windows:raise ValueError('HDMA_RETIREMENT_REQUIRES_DMA_WINDOWS')
    if (args.context_widths!='16/16'or args.decimal_context)and not args.dma_windows:raise ValueError('CONTEXT_VARIANTS_REQUIRE_DMA_WINDOWS')
    if args.general_windows and not args.dma_windows:raise ValueError('GENERAL_WINDOWS_REQUIRE_DMA_WINDOWS')
    if args.three_ranges and not args.dma_windows:raise ValueError('THREE_RANGES_REQUIRE_DMA_WINDOWS')
    folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=make_irq_rom(38,True,args.timer,73,24,False,True,True,True,args.preserve_context)
    if args.dma_windows:
        from m4_cgram_dma_windows import compile_rom
        raw=compile_rom(args.timer,args.context_widths,args.decimal_context,args.general_windows,args.three_ranges,args.fixed_math_mode,args.retire_audio_hdma,args.fetch_gateway,args.direct_fetch_route,args.compact_visible_handler,args.fixed_color,args.dynamic_fixed_color)
    _,_,expected,oam,initial=fixture();rom=folder/'proof.sfc';rom.write_bytes(raw)
    if args.dma_windows:
        from m4_cgram_dma_windows import expected_frame,palette_color
        expected=expected_frame(args.general_windows,args.fixed_math_mode,args.fixed_color,args.dynamic_fixed_color)
    lua=folder/'observer.lua'
    lua.write_text('''local packet=nil;local high=false;local address=0;local low=0
emu.addMemoryCallback(function(a,v)address=v;high=false end,emu.callbackType.write,0x2121,0x2121,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if v==224 then local s=emu.getState();packet={frame=s['ppu.frameCount'],line=s['ppu.scanline'],n=0,bad=0,words={}}end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if not packet then return end
 local s=emu.getState();local h=(s.masterClock+4*(s['ppu.frameCount']//2))%1364
 if high then
  table.insert(packet.words,address);table.insert(packet.words,low+(v%128)*256);address=(address+1)%256
  packet.n=packet.n+1;if h>=88 and h<1096 then packet.bad=packet.bad+1 end
  if packet.n==1 then packet.first=s.masterClock;packet.firstH=h end
  if packet.n==19 then emu.log('PIXPACKET|'..table.concat({packet.frame,packet.line,packet.n,packet.bad,s.masterClock-packet.first,packet.firstH,h},','));emu.log('PIXCGRAM|'..packet.frame..','..packet.line..','..table.concat(packet.words,','));packet=nil end
 else low=v end
 high=not high
end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)local s=emu.getState();if s['ppu.scanline']<224 then emu.log('PIXWINDOW|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],(s.masterClock+4*(s['ppu.frameCount']//2))%1364,v},','))end end,emu.callbackType.write,0x2131,0x2131,emu.cpuType.snes,emu.memType.snesMemory)
'''.replace('v==224','v==126'if args.fixed_math_mode else'v==254'if args.general_windows or args.three_ranges else'v==222'if args.dynamic_fixed_color else'v==206'if args.dma_windows else'v==224').replace('packet.n==19','packet.n==20'if args.three_ranges else'packet.n==19'))
    if args.dynamic_fixed_color:
        with lua.open('a')as script:
            script.write('''emu.addMemoryCallback(function(a,v)local s=emu.getState();local cursor=emu.read(0x4342,emu.memType.snesMemory)+256*emu.read(0x4343,emu.memType.snesMemory)-0xa700;if s['ppu.frameCount']>=1 then emu.log('PIXCOLDATA|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],(s.masterClock+4*(s['ppu.frameCount']//2))%1364,cursor,v},','))end end,emu.callbackType.write,0x2132,0x2132,emu.cpuType.snes,emu.memType.snesMemory)\n''')
    if args.preserve_context or args.dma_windows:
        # Observe immediately before RTI, after explicit register restoration.
        handler=raw[0x8600:0x8700];ret=0x818600+handler.index(bytes.fromhex('68 28 40'if args.fetch_gateway else'68 40'))+(2 if args.fetch_gateway else 1)
        with lua.open('a')as script:
            script.write(f'''emu.addMemoryCallback(function()local s=emu.getState();emu.log('PIXCONTEXT|'..table.concat({{s['cpu.a'],s['cpu.x'],s['cpu.y'],s['cpu.d'],s['cpu.dbr'],s['cpu.sp'],emu.read(0x7e0000+s['cpu.sp']+1,emu.memType.snesMemory)}},','))end,emu.callbackType.exec,{ret},{ret},emu.cpuType.snes,emu.memType.snesMemory)\n''')
            script.write(f'''local irqEntry=0
emu.addMemoryCallback(function()local s=emu.getState();if not {str(args.fetch_gateway).lower()} or (s['cpu.ps']&4)~=0 then irqEntry=s.masterClock;emu.log('PIXENTRYCONTEXT|'..table.concat({{s['cpu.a'],s['cpu.x'],s['cpu.y'],s['cpu.d'],s['cpu.dbr'],s['cpu.sp'],emu.read(0x7e0000+s['cpu.sp']+1,emu.memType.snesMemory)}},','))end end,emu.callbackType.exec,{0x818a00 if args.fetch_gateway else 0x818600},{0x818a00 if args.fetch_gateway else 0x818600},emu.cpuType.snes,emu.memType.snesMemory)
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
    entry_contexts=[list(map(int,line.split('PIXENTRYCONTEXT|')[1].split(',')))for line in log if 'PIXENTRYCONTEXT|'in line]
    irq_times=[list(map(int,line.split('PIXIRQTIME|')[1].split(',')))for line in log if 'PIXIRQTIME|'in line]
    cgram_words=[list(map(int,line.split('PIXCGRAM|')[1].split(',')))for line in log if 'PIXCGRAM|'in line]
    fixed_writes=[list(map(int,line.split('PIXCOLDATA|')[1].split(',')))for line in log if 'PIXCOLDATA|'in line]
    fixed_identity=None
    if args.dynamic_fixed_color:
        fixed_identity=len(fixed_writes)==2016 and all(0<=r[3]<672 and r[4]==raw[0x1a700+r[3]]for r in fixed_writes)
        fixed_identity=fixed_identity and all([r[3]for r in fixed_writes if r[0]==field]==list(range(672))for field in (1,2,3))
    index8=args.dma_windows and args.context_widths.endswith('/8')
    wanted_context=[0x1234,0x78 if index8 else 0x5678,0xcd if index8 else 0xabcd,0x2345,0x40,0x1ffb]
    context_identity=(bool(contexts)and all(r[:6]==wanted_context for r in contexts))if args.preserve_context or args.dma_windows else None
    wanted_status=1|(0x20 if args.context_widths.startswith('8/')else 0)|(0x10 if index8 else 0)|(8 if args.decimal_context else 0)
    status_identity=(bool(contexts)and all(r[6]==wanted_status for r in contexts))if args.dma_windows else None
    if args.fetch_gateway or args.direct_fetch_route:
        # A frame-exact pause may be inside the final IRQ. Every completed
        # handler must have one matching entry; at most one may be pending.
        paired=bool(contexts)and len(contexts)<=len(entry_contexts)<=len(contexts)+1
        context_identity=paired and all(a[:6]==b[:6]for a,b in zip(entry_contexts,contexts))
        status_identity=paired and all(a[6]==b[6]for a,b in zip(entry_contexts,contexts))
    packets=[r for r in packets if r[0]>=1];windows=[r for r in windows if r[0]>=1]
    palette=bytearray(initial)
    addresses=[*range(129,137),*range(161,167),*range(193,199)]if args.three_ranges else[*range(129,141),*range(193,200)]if args.dma_windows else[*range(128,140),*range(192,199)]
    for i in addresses:struct.pack_into('<H',palette,i*2,palette_color(223)if args.dma_windows else 0x1111)
    identity=actual.shape==expected.shape and np.array_equal(actual,expected)
    complete=len(packets)==447 and all(len([r for r in packets if r[0]==field])==149 for field in (1,2,3))
    cgram_words=[r for r in cgram_words if r[0]>=1]
    word_identity=len(cgram_words)==447 and all(r[2:]==[v for a in addresses for v in (a,palette_color(r[1])if args.dma_windows else 0x1111)]for r in cgram_words)
    safe=complete and all(r[3]==0 for r in packets)
    visible_windows=[r for r in windows if 81<=r[1]<=208]
    result=dict(schema='BYOR_CPU_WINDOWS_CGRAM_PIXEL_COMPONENT_V1',status='PASS'if identity and safe and cgram==palette and observed_oam==oam and context_identity is not False and status_identity is not False and word_identity and fixed_identity is not False else'FAIL',
        pixel_identity_verified=identity,pixel_mismatches=int(np.count_nonzero(actual!=expected))if actual.shape==expected.shape else None,
        palette_identity_verified=cgram==palette,oam_identity_verified=observed_oam==oam,
        every_packet_destination_and_word_identity_verified=word_identity,observed_cgram_word_packets=len(cgram_words),opaque_palette_words_per_line=20 if args.three_ranges else 19 if args.dma_windows else 17,
        packets=len(packets),high_commits=sum(r[2]for r in packets),unsafe_high_commits=sum(r[3]for r in packets),peak_commit_span=max((r[4]for r in packets),default=None),
        descriptors=len(windows),latest_descriptor_hclock=max((r[2]for r in windows),default=None),
        visible_obj_descriptor_latest_hclock=max((r[2]for r in visible_windows),default=None),
        complete_packet_fields_verified=complete,
        timer=args.timer,first_palette_row=75,first_obj_row=80,first_math_obj_x=128,
        oam_entries=16,peak_sprites=4,peak_slivers=16,dma_channels=list(range(1,7))if args.fixed_math_mode else list(range(1,8))if args.general_windows or args.three_ranges else[1,2,3,4,6,7]if args.dynamic_fixed_color else[1,2,3,6,7]if args.dma_windows else[5,6,7],dummy_apu_hdma_channel=0,dummy_apu_hdma_rows=73,
        rom_sha256=hashlib.sha256(raw).hexdigest(),expected_rgb555_sha256=hashlib.sha256(expected.tobytes()).hexdigest(),
        source_hbreath_proven=False,production_interrupt_context_proven=False,no_color_reduction=True,frame_advancement=advancement,ppu=ppu,cpu=cpu,
        synthetic_register_context_preserved=context_identity,context_observations=len(contexts),cursor_in_private_wram=args.preserve_context and not args.dma_windows,
        automatic_dma_descriptor_cursors=args.dma_windows,window_transfer='DMA'if args.dma_windows else'CPU',
        per_line_palette_payload_changes=args.dma_windows,
        general_window_controls=args.general_windows,window_descriptor_bytes=7 if args.general_windows else 5,
        cgram_destination_ranges=3 if args.three_ranges else 2,
        fixed_math_mode=args.fixed_math_mode,
        fixed_color_rgb555=args.fixed_color,fixed_color_loaded_in_vblank=args.fixed_color is not None,
        per_line_fixed_color_changes=args.dynamic_fixed_color,
        four_math_modes_cycled=args.fixed_color is not None and not args.fixed_math_mode,
        per_line_fixed_color_component_pixel_replay_verified=args.dynamic_fixed_color and identity and fixed_identity is True,
        fixed_color_control_bytes_observed=len(fixed_writes),fixed_color_control_payload_identity_verified=fixed_identity,
        visible_obj_fixed_color_latest_hclock=max((r[2]for r in fixed_writes if 80<=r[3]//3<=207),default=None),
        authored_fixed_color_control_deadlines_proven=False,
        completed_dummy_audio_hdma_retired=args.retire_audio_hdma,
        production_fetch_gateway_instruction_shape=args.fetch_gateway,ordinary_fetch_body_stubbed=args.fetch_gateway,
        direct_fetch_route_instruction_shape=args.direct_fetch_route,ordinary_far_fetch_body_stubbed=args.direct_fetch_route,
        compact_visible_irq_cursor_checks=args.compact_visible_handler,
        irq_entry_context_observations=len(entry_contexts),
        interrupted_context_widths=args.context_widths,interrupted_decimal_context=args.decimal_context,hardware_return_status_verified=status_identity,
        cpu_snapshot_may_be_inside_irq=True,
        irq_entry_to_rti_peak_master_clocks=max((r[2]for r in irq_times),default=None),
        visible_irq_entry_to_rti_peak_master_clocks=max((r[2]for r in irq_times if 76<=r[1]<=224),default=None),
        irq_timing_excludes_hardware_entry_gateway_and_rti=True)
    for name,data in [('packets.json',packets),('windows.json',windows),('report.json',result)]: (folder/name).write_text(json.dumps(data,indent=2)+'\n')
    (folder/'expected.rgb555').write_bytes(expected.tobytes());(folder/'cgram.bin').write_bytes(cgram);(folder/'oam.bin').write_bytes(observed_oam)
    if contexts:(folder/'contexts.json').write_text(json.dumps(contexts)+'\n')
    if entry_contexts:(folder/'entry-contexts.json').write_text(json.dumps(entry_contexts)+'\n')
    if irq_times:(folder/'irq-times.json').write_text(json.dumps(irq_times)+'\n')
    (folder/'cgram-word-observer.json').write_text(json.dumps(cgram_words)+'\n')
    if fixed_writes:(folder/'fixed-color-observer.json').write_text(json.dumps(fixed_writes)+'\n')
    print(json.dumps(result,indent=2))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
