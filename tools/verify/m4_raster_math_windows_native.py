"""Isolated two-color-window OBJ math descriptor and pixel identity proof.

This fixture measures window HDMA independently. It does not admit concurrent
palette DMA, source alpha, HBreath geometry or the production presentation lease.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import shutil
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from raster_math_windows import compile_mask
from _harness import McpSession,MESEN_EXE,_free_tcp_port


def compile_rom():
    masks=[[1]*256,[int(32<=x<=63 or 128<=x<=191)for x in range(256)],
           [int(not(32<=x<=63 or 128<=x<=191))for x in range(256)],[0]*256]
    descriptors=[compile_mask(mask)for mask in masks]
    # Lower/upper banks alternate horizontally, proving lower banks bypass
    # math while upper banks honor the shared color-window mask.
    oam=bytearray(544)
    for i in range(128):oam[i*4+1]=240
    for row in range(7):
        for col in range(8):
            index=row*8+col
            oam[4*index:4*index+4]=bytes([col*32,row*32,0,0x30|(4 if col%2 else 0)*2])
            oam[512+index//4]|=2<<((index%4)*2)
    objchr=bytes([255,0]*8+[0]*16)*64
    # BG1 is a solid green operand on the subscreen, not backdrop: halving
    # stays enabled. Tile zero is index 1 in a 4bpp background.
    bgchr=bytes([255,0]*8+[0]*16)
    palette=bytearray(512)
    for index,color in ((1,10<<5),(129,12),(193,12)):struct.pack_into('<H',palette,index*2,color)
    tables=[bytearray()for _ in range(4)]
    expected=np.zeros((224,256),dtype='<u2')
    for y in range(224):
        pattern=y%4;descriptor=descriptors[pattern];half=y%8>=4
        values=[sum(descriptor['bounds'],[]),[descriptor['wobjsel_color_bits']],
                [descriptor['wobjlog_color_bits']],[0x10|(0x40 if half else 0)]]
        for table,data in zip(tables,values):table.extend([0x81,*data])
        for x in range(256):
            enabled=(x//32)%2==1 and masks[pattern][x]
            expected[y,x]=((6|(5<<5))if half else(12|(10<<5)))if enabled else 12
    for table in tables:table.append(0)
    rom=bytearray([255])*131072
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend([0xa9,value,0x8d,address&255,address>>8])
    def dma(source,dest,n,mode,vram=None):
        if vram is not None:store(0x2116,vram&255);store(0x2117,vram>>8)
        for address,value in ((0x4370,mode),(0x4371,dest),(0x4372,source&255),(0x4373,source>>8),(0x4374,2),(0x4375,n&255),(0x4376,n>>8),(0x420b,128)):store(address,value)
    for address,value in ((0x4200,0),(0x420c,0),(0x2100,128),(0x2115,128)):store(address,value)
    dma(0x8000,0x18,len(objchr),1,0);dma(0x8800,0x18,len(bgchr),1,0x2000)
    dma(0x9000,0x18,2048,1,0x7000);store(0x2121,0);dma(0x9800,0x22,512,0)
    store(0x2102,0);store(0x2103,0);dma(0x9a00,4,544,0)
    for address,value in ((0x2101,0x20),(0x2105,1),(0x2107,0x70),(0x210b,2),
                          (0x210d,0),(0x210d,0),(0x210e,255),(0x210e,255),
                          (0x212c,0x10),(0x212d,1),(0x212e,0),(0x212f,0),
                          (0x2130,0x12),(0x2132,0xe0),(0x2133,0)):store(address,value)
    cursor=0xa000
    for ch,(table,mode,dest)in enumerate(zip(tables,(4,0,0,0),(0x26,0x25,0x2b,0x31)),1):
        base=0x4300+ch*16
        for address,value in ((base,mode),(base+1,dest),(base+2,cursor&255),(base+3,cursor>>8),(base+4,2)):store(address,value)
        start=0x10000+cursor-0x8000;rom[start:start+len(table)]=table;cursor+=len(table)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    store(0x420c,0x1e);store(0x2100,15)
    loop=0x8000+len(code);code.extend([0x4c,loop&255,loop>>8])
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x8000:0x8000+len(code)]=code
    rom[0x10000:0x10000+len(objchr)]=objchr;rom[0x10800:0x10800+len(bgchr)]=bgchr
    rom[0x11000:0x11800]=bytes(2048);rom[0x11800:0x11a00]=palette;rom[0x11a00:0x11c20]=oam
    rom[0x7fc0:0x7fd5]=b'M4 OBJ WINDOW PROOF  '
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,7,0,1,0,0]);rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom),expected,descriptors,bytes(oam),bytes(palette)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw,expected,descriptors,oam,palette=compile_rom();path=folder/'proof.sfc';path.write_bytes(raw)
    lua=folder/'observer.lua';lua.write_text('''local frame=0;local times={};local active=false
emu.addMemoryCallback(function(a,v)if v==15 then active=true end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and frame==1 then
  local clock,line=0,0;if a==0x2126 or a==0x2131 then local s=emu.getState();clock=s.masterClock;line=s['ppu.scanline']end
  times[#times+1]={a,v,clock,line}
 end
end,emu.callbackType.write,0x2125,0x2131,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()frame=frame+1;if frame==2 then
 local rows={};for _,r in ipairs(times)do rows[#rows+1]=table.concat(r,',')end
 emu.log('WINDOWREG|'..table.concat(rows,';'))
end end,emu.eventType.endFrame)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as session:
        advance=[];completed=0
        for _ in range(12):
            progress=session.run_frames(1);advance.append(progress)
            if progress['framesAdvanced']not in (0,1):raise AssertionError('WINDOW_NATIVE_FRAME_OVERRUN')
            completed+=progress['framesAdvanced']
            if completed==3:break
        if completed!=3:raise AssertionError('WINDOW_NATIVE_FRAME_ADVANCEMENT')
        shot=session.tool('take_screenshot',{'format':'path','path':str(folder/'screenshot.png')})
        observed_oam=session.read_memory('SnesSpriteRam',0,544)
        observed_palette=session.read_memory('SnesCgRam',0,512)
        cpu=session.get_cpu_state()
        ppu=session.get_ppu_state()
    retained=folder/'screenshot.png'
    if Path(shot['path']).resolve()!=retained:shutil.copyfile(shot['path'],retained)
    rgb=np.asarray(Image.open(retained).convert('RGB'),dtype=np.uint16)
    actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
    vectors=[line.split('WINDOWREG|')[1]for line in(folder/'mesen.log').read_text().splitlines()if'WINDOWREG|'in line]
    trace=[list(map(int,row.split(',')))for row in vectors[0].split(';')]if len(vectors)==1 else[]
    expected_registers=[]
    for y in range(224):
        d=descriptors[y%4]
        expected_registers.extend([[0x2126+i,value]for i,value in enumerate(sum(d['bounds'],[]))])
        expected_registers.extend([[0x2125,d['wobjsel_color_bits']],[0x212b,d['wobjlog_color_bits']],[0x2131,0x10|(0x40 if y%8>=4 else 0)]])
    identity=actual.shape==expected.shape and np.array_equal(actual,expected)
    register_identity=[row[:2]for row in trace]==expected_registers
    spans=[trace[i+6][2]-trace[i][2]for i in range(0,len(trace),7)]if len(trace)==1568 else[]
    (folder/'register-observer.json').write_text(json.dumps(trace,separators=(',',':'))+'\n')
    (folder/'expected.rgb555').write_bytes(expected.tobytes())
    result=dict(schema='BYOR_NATIVE_OBJ_COLOR_WINDOWS_V1',status='PASS'if identity and register_identity and observed_oam==oam and observed_palette==palette else'FAIL',
                rom_sha256=hashlib.sha256(raw).hexdigest(),compiled_descriptors=descriptors,frame_advance=advance,
                pixel_identity_verified=identity,pixel_mismatches=int(np.count_nonzero(actual!=expected))if actual.shape==expected.shape else None,
                register_identity_verified=register_identity,observed_register_writes=len(trace),oam_identity_verified=observed_oam==oam,
                cgram_identity_verified=observed_palette==palette,oam_entries=56,peak_sprites_per_line=8,peak_slivers_per_line=32,
                hdma_channels=[1,2,3,4],hdma_data_bytes_per_line=7,cpu_state=cpu,source_alpha_proven=False,
                first_to_last_register_write_peak_master_clocks=max(spans,default=None),ppu_state=ppu,
                full_hdma_setup_and_transfer_budget_measured=False,
                concurrent_palette_dma_admitted=False,production_presentation_lease_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
