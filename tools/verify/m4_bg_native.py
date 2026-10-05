"""Isolated native Mode 3 raster BG proof from an offline sampled schedule."""
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
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact


def physical(slot):return slot if slot<=111 else slot+80


def compile_rom(report,assets):
    if report['bg_opaque_slot_capacity'] not in (111,175):
        raise ValueError('FIXTURE_PALETTE_RESERVATION_NOT_SUPPORTED')
    indices=np.frombuffer((assets/'indices.bin').read_bytes(),dtype=np.uint8).reshape(224,256).copy()
    indices=np.where(indices<=111,indices,indices+80).astype(np.uint8)
    tiles=[];lookup={};tilemap=np.zeros((32,32),dtype='<u2')
    for y in range(28):
        for x in range(32):
            tile=indices[y*8:y*8+8,x*8:x*8+8];key=tile.tobytes()
            if key not in lookup:
                encoded=bytearray(64)
                for row in range(8):
                    for plane in range(8):
                        encoded[(plane//2)*16+row*2+(plane%2)]=sum(((int(tile[row,col])>>plane)&1)<<(7-col) for col in range(8))
                lookup[key]=len(tiles);tiles.append(bytes(encoded))
            tilemap[y,x]=lookup[key]
    chrdata=b''.join(tiles)
    if len(chrdata)>32768:raise ValueError('FIXTURE_CHR_BANK_OVERFLOW')
    palette=np.zeros(256,dtype='<u2')
    palette[112:192]=np.arange(80,dtype=np.uint16)+0x1234
    initial=json.loads((assets/'initial.json').read_text())
    for i,c in enumerate(initial):
        if c is not None:palette[physical(i+1)]=c
    tables=[bytearray() for _ in range(7)];state=list(initial)
    for row in report['trace']:
        events=row['updates'] if row['scanline'] else []
        if len(events)>7:raise ValueError('HDMA_WRITE_BUDGET')
        for e in events:state[e['slot']-1]=e['color']
        for ch in range(7):
            if ch<len(events):e=events[ch];slot=physical(e['slot']);color=e['color']
            else:slot=1;color=state[0] or 0
            tables[ch].extend(bytes([0x81,slot,slot,color&255,color>>8]))
    for table in tables:table.append(0)
    rom=bytearray([0xff])*131072
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(a,v):code.extend(bytes([0xa9,v,0x8d,a&255,a>>8]))
    def dma(source,bank,dest,count,mode,targetreg=None,target=0):
        if targetreg is not None:store(targetreg,target&255);store(targetreg+1,target>>8)
        for a,v in [(0x4370,mode),(0x4371,dest),(0x4372,source&255),(0x4373,source>>8),(0x4374,bank),(0x4375,count&255),(0x4376,count>>8),(0x420b,128)]:store(a,v)
    store(0x4200,0);store(0x420c,0);store(0x2100,128)
    store(0x2115,128)
    dma(0x8000,2,0x18,len(chrdata),1,0x2116,0)
    dma(0x8000,3,0x18,2048,1,0x2116,0x7000)
    store(0x2121,0);dma(0x8800,3,0x22,512,0)
    store(0x2105,3);store(0x2107,0x70);store(0x210b,0)
    store(0x210d,0);store(0x210d,0);store(0x210e,255);store(0x210e,255)
    store(0x212c,1);store(0x212d,0);store(0x2130,0);store(0x2131,0);store(0x2133,0)
    cursor=0x9000;channel7_table=None
    # Worst transfer width of the production TAD direct-HDMA channel 0.
    # This exercises bus contention, not production SPC protocol/audio.
    audio_table=bytes([0x81,0,0,0,0x57])*224+bytes([0])
    for a,v in [(0x4300,4),(0x4301,0x40),(0x4302,cursor&255),(0x4303,cursor>>8),(0x4304,3)]:store(a,v)
    rom[0x18000+(cursor-0x8000):0x18000+(cursor-0x8000)+len(audio_table)]=audio_table
    cursor+=len(audio_table)
    for ch,table in enumerate(tables,1):
        if ch==7:channel7_table=cursor
        base=0x4300+ch*16
        for a,v in [(base,3),(base+1,0x21),(base+2,cursor&255),(base+3,cursor>>8),(base+4,3)]:store(a,v)
        rom[0x18000+(cursor-0x8000):0x18000+(cursor-0x8000)+len(table)]=table
        cursor+=len(table)
    # Arming direct HDMA mid-field would run uninitialized table cursors.
    # Enable in VBlank so the next field's HDMA init owns the first access.
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    store(0x420c,0xff);store(0x2100,15)
    # Restore owned early-row colors before replaying the next field.
    loop=len(code)
    code.extend(bytes.fromhex('ad 12 42 29 80 d0 f9'))
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    store(0,1)  # Isolated fixture observer marker; no production WRAM claim.
    store(0x2121,1);dma(0x8802,3,0x22,222,0);store(0x420b,0)
    restore_bytes=222
    if report['bg_opaque_slot_capacity']==175:
        store(0x2121,192);dma(0x8980,3,0x22,128,0);store(0x420b,0)
        restore_bytes+=128
    store(0,0)
    for a,v in [(0x4370,3),(0x4371,0x21),(0x4372,channel7_table&255),(0x4373,channel7_table>>8),(0x4374,3)]:store(a,v)
    code.extend(bytes([0x4c,(0x8000+loop)&255,(0x8000+loop)>>8]))
    # All fixture presentation code is bank 1; bank 0 only reset trampoline.
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x8000:0x8000+len(code)]=code
    rom[0x10000:0x10000+len(chrdata)]=chrdata
    rom[0x18000:0x18800]=tilemap.tobytes();rom[0x18800:0x18a00]=palette.tobytes()
    rom[0x7fc0:0x7fd5]=b'M4 LOSSLESS BG PROOF '
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,7,0,1,0,0]);rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom),dict(chr_bytes=len(chrdata),tilemap_bytes=2048,hdma_table_bytes=cursor-0x9000,code_bank=1,
        hdma_channels=list(range(8)),channel0_stress='4 bytes to APU ports per line; bus contention only',
        per_field_initial_palette_restore_bytes=restore_bytes,channel7_restored_after_vblank_dma=True,
        palette_reserved_before_sha256=hashlib.sha256(palette[112:192].tobytes()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    a.report=a.report.resolve()
    assets=a.report.with_suffix('');report=json.loads(a.report.read_text())
    folder=assets/'native';folder.mkdir(exist_ok=True)
    rom,resources=compile_rom(report,assets);path=folder/'proof.sfc';path.write_bytes(rom)
    lua=folder/'observer.lua'
    lua.write_text('''local active=false;local restoring=false
local rows={};local total=0;local frames=0;local resetrows={}
emu.addMemoryCallback(function(a,v) restoring=(v==1) end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) if v==15 then active=true end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and restoring and frames==2 then resetrows[#resetrows+1]=string.format('%04x:%02x',a,v);return end
 if active and frames==1 then
  total=total+1;rows[#rows+1]=string.format('%04x:%02x',a,v)
  if total%28==1 or total%28==0 then
   local s=emu.getState();emu.log('M4BGTIME|'..table.concat({total,s['ppu.scanline'],s['masterClock']},','))
  end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 frames=frames+1
 if frames==2 then emu.log('M4BGTRACE|'..table.concat(rows,',')) end
 if frames==3 then emu.log('M4BGRESET|'..table.concat(resetrows,',')) end
end,emu.eventType.endFrame)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        advance=run_frames_exact(m,3)
        shot=m.tool('take_screenshot',{'format':'path','path':str(folder/'screenshot.png')})
        cgram=m.read_memory('SnesCgRam',0,512)
        cpu=m.get_cpu_state()
    screenshot=Path(shot['path'])
    retained=folder/'screenshot.png';shutil.copyfile(screenshot,retained);screenshot=retained
    image=Image.open(screenshot).convert('RGB');rgb=np.asarray(image,dtype=np.int32)
    actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
    expected=np.frombuffer((assets/'expected.rgb555').read_bytes(),dtype='<u2').reshape(224,256)
    identity=(actual.shape==expected.shape and np.array_equal(actual,expected))
    log=(folder/'mesen.log').read_text()
    vectors=[line.split('M4BGTRACE|',1)[1] for line in log.splitlines() if 'M4BGTRACE|' in line]
    observed=vectors[0].split(',') if len(vectors)==1 else []
    expected_trace=[];initial=json.loads((assets/'initial.json').read_text());state=list(initial)
    for row in report['trace']:
        events=row['updates'] if row['scanline'] else []
        for e in events:state[e['slot']-1]=e['color']
        for ch in range(7):
            if ch<len(events):e=events[ch];slot=physical(e['slot']);color=e['color']
            else:slot=1;color=state[0] or 0
            expected_trace.extend([f'2121:{slot:02x}',f'2121:{slot:02x}',f'2122:{color&255:02x}',f'2122:{color>>8:02x}'])
    observer_identity=observed==expected_trace
    resets=[line.split('M4BGRESET|',1)[1] for line in log.splitlines() if 'M4BGRESET|' in line]
    observed_reset=resets[0].split(',') if len(resets)==1 else []
    expected_reset=['2121:01']+[f'2122:{b:02x}' for b in rom[0x18802:0x188e0]]
    if report['bg_opaque_slot_capacity']==175:
        expected_reset+=['2121:c0']+[f'2122:{b:02x}' for b in rom[0x18980:0x18a00]]
    reset_identity=observed_reset==expected_reset
    (folder/'cgram-observer.json').write_text(json.dumps(dict(observed=observed,expected=expected_trace,
        observed_reset=observed_reset,expected_reset=expected_reset),separators=(',',':'))+'\n')
    times=[[int(x) for x in line.split('M4BGTIME|')[1].split(',')] for line in log.splitlines() if 'M4BGTIME|' in line]
    (folder/'timing.json').write_text(json.dumps(times)+'\n')
    result=dict(resources,rom_sha256=hashlib.sha256(rom).hexdigest(),frame_advance=advance,
        cpu_state=cpu,
        screenshot=str(screenshot),pixel_identity_verified=identity,
        observer_palette_schedule_identity_verified=observer_identity,observed_register_writes=len(observed),
        observer_vblank_restore_identity_verified=reset_identity,
        screenshot_size=image.size,cgram_reserved_after_sha256=hashlib.sha256(cgram[224:384]).hexdigest(),
        alpha='OFFLINE_BOR4086_SCREEN_COMPOSITING',runtime_compositor_proven=False,
        no_color_reduction=True,scope='One static context; no gameplay/native compositor claim.')
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not (identity and observer_identity and reset_identity and
            result['palette_reserved_before_sha256']==result['cgram_reserved_after_sha256']):
        raise SystemExit(1)


if __name__=='__main__':main()
