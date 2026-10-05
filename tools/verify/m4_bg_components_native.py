"""Native lossless two-BG RGB555 addition, with bounded palette observers."""
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


def tiles(indices,bpp):
    data=[];lookup={};tilemap=np.zeros((32,32),dtype='<u2')
    for y in range(28):
        for x in range(32):
            tile=indices[y*8:y*8+8,x*8:x*8+8];key=tile.tobytes()
            if key not in lookup:
                encoded=bytearray(8*bpp)
                for row in range(8):
                    for plane in range(bpp):
                        encoded[(plane//2)*16+row*2+plane%2]=sum(((int(tile[row,col])>>plane)&1)<<(7-col) for col in range(8))
                lookup[key]=len(data);data.append(bytes(encoded))
            tilemap[y,x]=lookup[key]
    return b''.join(data),tilemap.tobytes()


def compile_rom(report,assets,timer=180,cache_assets=None):
    if report['bg_mode']!=4 or report['low_bpp']!=2 or report['high_palette_start']!=4 or report['high_opaque_capacity']!=236:
        raise ValueError('MODE4_COMPONENT_FIXTURE_CONTRACT')
    high=np.frombuffer((assets/'indices.bin').read_bytes(),dtype=np.uint8).reshape(224,256)+3
    low=np.frombuffer((assets/'low_indices.bin').read_bytes(),dtype=np.uint8).reshape(224,256)
    highchr,highmap=tiles(high,8);lowchr,lowmap=tiles(low,2);lowbase=report['low_chr_vram_base']
    if cache_assets is not None:
        highchr=(cache_assets/'high.chr').read_bytes();lowchr=(cache_assets/'low.chr').read_bytes()
        highmap=(cache_assets/'0-high.map').read_bytes();lowmap=(cache_assets/'0-low.map').read_bytes()
        lowbase=((len(highchr)+8191)//8192)*8192
    gaps=[(len(highchr),lowbase),(lowbase+len(lowchr),0xf000)]
    offsetmap=next((((first+2047)//2048)*2048 for first,last in gaps
                    if ((first+2047)//2048)*2048+2048<=last),None)
    if offsetmap is None or lowbase+len(lowchr)>0xf000:raise ValueError('MODE4_VRAM_LAYOUT_LIMIT')
    palette=np.zeros(256,dtype='<u2');palette[:4]=report['low_component_palette']
    palette[240:256]=np.arange(16,dtype=np.uint16)+0x1234
    state=json.loads((assets/'initial.json').read_text())
    for i,c in enumerate(state):palette[i+4]=c or 0
    burst=report.get('contiguous_bursts');span=report.get('span',0)
    tables=[bytearray() for _ in range(7)];expected_trace=[];targets=bytearray();payload=bytearray()
    for row in report['trace']:
        events=row['updates'] if row['scanline'] else []
        if len(events)>7 and not burst:raise ValueError('MODE4_HDMA_BUDGET')
        for e in events:state[e['slot']-1]=e['color']
        if burst:
            start=burst[row['scanline']]['start_slot'];values=state[start-1:start-1+span]
            if len(values)!=span:raise ValueError('MODE4_BURST_RANGE')
            targets.append(start+3);raw=struct.pack('<'+'H'*span,*[c or 0 for c in values]);payload.extend(raw)
            expected_trace.extend([f'2121:{start+3:02x}',*[f'2122:{v:02x}' for v in raw]])
            continue
        for ch in range(7):
            if ch<len(events):e=events[ch];slot=e['slot']+3;color=e['color']
            else:slot=4;color=state[0] or 0
            table=bytes([0x81,slot,slot,color&255,color>>8]);tables[ch].extend(table)
            expected_trace.extend([f'2121:{slot:02x}',f'2121:{slot:02x}',f'2122:{color&255:02x}',f'2122:{color>>8:02x}'])
    for table in tables:table.append(0)
    rom=bytearray([0xff])*262144;code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    def dma(source,bank,dest,n,mode,target=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for address,value in [(0x4370,mode),(0x4371,dest),(0x4372,source&255),(0x4373,source>>8),
                              (0x4374,bank),(0x4375,n&255),(0x4376,n>>8),(0x420b,128)]:store(address,value)
    for address,value in [(0x4200,0),(0x420c,0),(0x2100,128),(0x2115,128)]:store(address,value)
    dma(0x8000,2,0x18,min(len(highchr),32768),1,0)
    if len(highchr)>32768:dma(0x8000,3,0x18,len(highchr)-32768,1)
    dma(0x8000,4,0x18,len(lowchr),1,lowbase//2)
    dma(0x8000,5,0x18,2048,1,0x7800);dma(0x8800,5,0x18,2048,1,0x7c00)
    dma(0x9800,5,0x18,2048,1,offsetmap//2)
    store(0x2121,0);dma(0x9000,5,0x22,512,0)
    for address,value in [(0x2105,4),(0x2107,0x78),(0x2108,0x7c),(0x2109,offsetmap>>9),
                          (0x210b,(lowbase//8192)<<4),
                          (0x210d,0),(0x210d,0),(0x210e,255),(0x210e,255),
                          (0x210f,0),(0x210f,0),(0x2110,255),(0x2110,255),
                          (0x2111,0),(0x2111,0),(0x2112,0),(0x2112,0),
                          (0x212c,1),(0x212d,2),(0x2130,2),(0x2131,1),(0x2132,0xe0),(0x2133,0)]:store(address,value)
    cursor=0xa000;audio=bytes([0x81,0,0,0,57])*224+bytes([0])
    for address,value in [(0x4300,4),(0x4301,0x40),(0x4302,cursor&255),(0x4303,cursor>>8),(0x4304,5)]:store(address,value)
    rom[0x28000+cursor-0x8000:0x28000+cursor-0x8000+len(audio)]=audio;cursor+=len(audio)
    for ch,table in ([] if burst else enumerate(tables,1)):
        base=0x4300+ch*16
        for address,value in [(base,3),(base+1,0x21),(base+2,cursor&255),(base+3,cursor>>8),(base+4,5)]:store(address,value)
        rom[0x28000+cursor-0x8000:0x28000+cursor-0x8000+len(table)]=table
        if ch==7:channel7=cursor
        cursor+=len(table)
    if burst:
        for address,value in [(0x4207,timer&255),(0x4208,timer>>8)]:store(address,value)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'));store(0x420c,1 if burst else 0xff);store(0x2100,15)
    loop=len(code);code.extend(bytes.fromhex('ad 12 42 29 80 d0 f9'));code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    store(0,1);store(0x2121,4);dma(0x9008,5,0x22,472,0);store(0,0)
    if burst:
        for address,value in [(0x4370,0),(0x4371,0x22),(0x4372,0),(0x4373,0x80),(0x4374,6),(0x4375,span*2),(0x4376,0)]:store(address,value)
        code.extend(bytes.fromhex('a2 00 00'));store(0x4200,0x10);code.append(0x58)
    else:
        for address,value in [(0x4370,3),(0x4371,0x21),(0x4372,channel7&255),(0x4373,channel7>>8),(0x4374,5)]:store(address,value)
    code.extend(bytes([0x4c,(0x8000+loop)&255,(0x8000+loop)>>8]))
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x8000:0x8000+len(code)]=code
    irq=None
    if burst:
        irq=bytearray.fromhex('48 ad 11 42 ad 12 42 29 80 d0 00 e0 e0 00 b0 00')
        irq.extend(bytes([0xa9,span*2,0x8d,0x75,0x43,0xbf,0x00,0xa8,0x05,0x8d,0x21,0x21,
                          0xa9,128,0x8d,0x0b,0x42,0xe8,0x68,0x40]))
        irq[10]=len(irq)-2-11;irq[15]=len(irq)-2-16
        rom[0x100:0x104]=bytes.fromhex('5c 00 84 01');rom[0x8400:0x8400+len(irq)]=irq
        rom[0x2a800:0x2a800+len(targets)]=targets;rom[0x30000:0x30000+len(payload)]=payload
        rom[0x7fee:0x7ff0]=struct.pack('<H',0x8100)
    rom[0x10000:0x18000]=highchr[:32768].ljust(32768,b'\0');rom[0x18000:0x18000+len(highchr[32768:])]=highchr[32768:]
    rom[0x20000:0x20000+len(lowchr)]=lowchr;rom[0x28000:0x28800]=highmap;rom[0x28800:0x29000]=lowmap
    rom[0x29000:0x29200]=palette.tobytes();rom[0x29800:0x2a000]=bytes(2048)
    rom[0x7fc0:0x7fd5]=b'M4 BG COMPONENTS'.ljust(21);rom[0x7fd5:0x7fdc]=bytes([0x20,0,8,0,1,0,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    if len(rom)!=262144:raise AssertionError('COMPONENT_ROM_SIZE_DRIFT')
    return bytes(rom),expected_trace,dict(bg_mode=4,high_chr_bytes=len(highchr),low_chr_bytes=len(lowchr),
        low_chr_base=lowbase,offset_tilemap_base=offsetmap,hdma_channels=[0] if burst else list(range(8)),irq_enabled=bool(burst),
        timer_dots=timer if burst else None,irq_entry_prg_offset=0x8400 if irq else None,
        irq_exit_prg_offset=0x8400+len(irq)-1 if irq else None,
        code_bank=1,oam_entries=0,per_field_palette_restore_bytes=472,peak_palette_updates=report['peak_hblank_colors_written'],
        source_color_bits_preserved=15,spc_protocol_proven=False,
        low_palette_sha256=hashlib.sha256(palette[:4].tobytes()).hexdigest(),
        hud_palette_sha256=hashlib.sha256(palette[240:256].tobytes()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--timer',type=int,default=180);a=p.parse_args();a.report=a.report.resolve()
    report=json.loads(a.report.read_text());assets=a.report.with_suffix('');folder=assets/'native';folder.mkdir(exist_ok=True)
    rom,expected_trace,resources=compile_rom(report,assets,a.timer);path=folder/'proof.sfc';path.write_bytes(rom);lua=folder/'observer.lua'
    lua.write_text('''local active=false;local restoring=false;local frames=0;local n=0;local rows={}
emu.addMemoryCallback(function(a,v) restoring=(v==1) end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) if v==15 and not active then active=true;frames=0 end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and not restoring and frames==1 then
  n=n+1;rows[#rows+1]=string.format('%04x:%02x',a,v)
  if n%ROWCOUNT==FIRSTDATA or n%ROWCOUNT==0 then local s=emu.getState();emu.log('M4COMPTIME|'..table.concat({n,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() frames=frames+1;if active and frames==2 then emu.log('M4COMPTRACE|'..table.concat(rows,',')) end end,emu.eventType.endFrame)
'''.replace('ROWCOUNT',str(1+report['span']*2 if report.get('contiguous_bursts') else 28))
   .replace('FIRSTDATA','2' if report.get('contiguous_bursts') else '3'))
    if resources['irq_enabled']:
        with lua.open('a') as script:
            script.write('''
local function service(a,v)
 if active and frames==1 then local s=emu.getState();emu.log('M4COMPSERVICE|'..table.concat({a,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
end
emu.addMemoryCallback(service,emu.callbackType.exec,ENTRY,ENTRY,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(service,emu.callbackType.exec,EXIT,EXIT,emu.cpuType.snes,emu.memType.snesPrgRom)
'''.replace('ENTRY',str(resources['irq_entry_prg_offset'])).replace('EXIT',str(resources['irq_exit_prg_offset'])))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        advancement=[];advanced=0
        for _ in range(10):
            progress=m.tool('run_frames',{'count':1});advancement.append(progress);advanced+=progress['framesAdvanced']
            if advanced>=5:break
        shot=m.tool('take_screenshot',{'format':'path'});cgram=m.read_memory('SnesCgRam',0,512)
    shutil.copyfile(shot['path'],folder/'screenshot.png');rgb=np.asarray(Image.open(folder/'screenshot.png').convert('RGB'),dtype=np.int32)
    actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
    expected=np.frombuffer((assets/'expected.rgb555').read_bytes(),dtype='<u2').reshape(224,256)
    log=(folder/'mesen.log').read_text();vectors=[line.split('M4COMPTRACE|',1)[1] for line in log.splitlines() if 'M4COMPTRACE|' in line]
    observed=vectors[0].split(',') if len(vectors)==1 and vectors[0] else []
    times=[[int(v) for v in line.split('M4COMPTIME|',1)[1].split(',')] for line in log.splitlines() if 'M4COMPTIME|' in line]
    service=[[int(v) for v in line.split('M4COMPSERVICE|',1)[1].split(',')] for line in log.splitlines() if 'M4COMPSERVICE|' in line]
    durations=[service[i+1][3]-service[i][3] for i in range(0,len(service)-1,2) if service[i][2]<224]
    clocks=[(r[3]+4*(r[1]//2))%1364 for r in times]
    cg=bytes.fromhex(cgram['hex']) if isinstance(cgram,dict) else bytes(cgram)
    result=dict(resources=resources,rom_sha256=hashlib.sha256(rom).hexdigest(),
        schedule_sha256=hashlib.sha256(a.report.read_bytes()).hexdigest(),advancement=advancement,completed_fields=advanced,
        pixel_identity_verified=(actual.shape==expected.shape and np.array_equal(actual,expected)),
        pixel_mismatches=int(np.count_nonzero(actual!=expected)) if actual.shape==expected.shape else None,
        cgram_observer_verified=(observed==expected_trace),observed_register_writes=len(observed),
        expected_register_writes=len(expected_trace),timing_samples=len(times),active_window_samples=sum(88<=c<1096 for c in clocks),
        irq_service_samples=len(durations),peak_irq_service_master_clocks=max(durations,default=0),
        visible_field_irq_service_master_clocks=sum(durations),
        low_palette_unchanged=(hashlib.sha256(cg[:8]).hexdigest()==resources['low_palette_sha256']),
        hud_palette_unchanged=(hashlib.sha256(cg[480:512]).hexdigest()==resources['hud_palette_sha256']),
        no_color_reduction=True,scope='Fixed composed source scene. No live compositor, actor reachability, HUD drawing or production audio admission.')
    result['pass']=all(result[k] for k in ('pixel_identity_verified','cgram_observer_verified','low_palette_unchanged','hud_palette_unchanged')) and not result['active_window_samples'] and advanced==5 and all(r['framesAdvanced']<=1 for r in advancement)
    (folder/'observer.json').write_text(json.dumps(dict(observed=observed,expected=expected_trace,times=times,service=service),indent=2)+'\n')
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
