"""Isolated native BG scene with precompiled contiguous IRQ palette bursts."""
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


def physical(slot):return slot if slot<=111 else slot+16


def compile_rom(report,assets,timer=80,dma_timer=239):
    if report['status']!='CONTIGUOUS_BURST_SCHEDULE_PROVEN' or report['capacity']!=239:
        raise ValueError('CONTIGUOUS_239_SLOT_PROOF_REQUIRED')
    span=report['span'];count=span*2
    if count>255:raise ValueError('FIXTURE_DMA_COUNT_LIMIT')
    indices=np.frombuffer((assets/'indices.bin').read_bytes(),dtype=np.uint8).reshape(224,256)
    indices=np.where(indices<=111,indices,indices+16).astype(np.uint8)
    tiles=[];lookup={};tilemap=np.zeros((32,32),dtype='<u2')
    for y in range(28):
        for x in range(32):
            tile=indices[y*8:y*8+8,x*8:x*8+8];key=tile.tobytes()
            if key not in lookup:
                encoded=bytearray(64)
                for row in range(8):
                    for plane in range(8):
                        encoded[(plane//2)*16+row*2+plane%2]=sum(((int(tile[row,col])>>plane)&1)<<(7-col) for col in range(8))
                lookup[key]=len(tiles);tiles.append(bytes(encoded))
            tilemap[y,x]=lookup[key]
    chrdata=b''.join(tiles)
    if len(chrdata)>0xe000:raise ValueError('FIXTURE_CHR_TILEMAP_COLLISION')
    palette=np.zeros(256,dtype='<u2');palette[112:128]=np.arange(16,dtype=np.uint16)+0x1234
    state=json.loads((assets/'initial.json').read_text())
    for i,c in enumerate(state):palette[physical(i+1)]=c or 0
    targets=bytearray();data=bytearray();expected_trace=[]
    for row in report['trace']:
        if row['scanline']:
            start=row['start_slot'];values=row['values']
            if values:state[start-1:start-1+span]=values
        else:start=1
        if start<=111<start+span-1:raise ValueError('BURST_TOUCHES_RESERVED_HUD')
        values=[c or 0 for c in state[start-1:start-1+span]]
        targets.append(physical(start));raw=struct.pack('<'+'H'*span,*values);data.extend(raw)
        expected_trace.extend([f'2121:{physical(start):02x}',*[f'2122:{v:02x}' for v in raw]])
    rom=bytearray([0xff])*262144
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    def dma(source,bank,dest,n,mode,target=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for address,value in [(0x4370,mode),(0x4371,dest),(0x4372,source&255),(0x4373,source>>8),
                              (0x4374,bank),(0x4375,n&255),(0x4376,n>>8),(0x420b,128)]:store(address,value)
    for address,value in [(0x4200,0),(0x420c,0),(0x2100,128),(0x2115,128)]:store(address,value)
    dma(0x8000,2,0x18,min(len(chrdata),32768),1,0)
    if len(chrdata)>32768:dma(0x8000,3,0x18,len(chrdata)-32768,1)
    dma(0x8000,4,0x18,2048,1,0x7000)
    store(0x2121,0);dma(0x8800,4,0x22,512,0)
    for address,value in [(0x2105,3),(0x2107,0x70),(0x210b,0),(0x210d,0),(0x210d,0),
            (0x210e,255),(0x210e,255),(0x212c,1),(0x212d,0),(0x2130,0),(0x2131,0),(0x2133,0),
            (0x4300,4),(0x4301,0x40),(0x4302,0),(0x4303,0x90),(0x4304,4),
            (0x4207,timer&255),(0x4208,timer>>8)]:store(address,value)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    store(0x420c,1);store(0x2100,15)
    loop=len(code)
    store(0,1);store(0x2121,1);dma(0x8802,4,0x22,222,0)
    store(0x2121,128);dma(0x8900,4,0x22,256,0)
    for address,value in [(0x4372,0),(0x4373,0x80),(0x4374,5)]:store(address,value)
    code.extend(bytes.fromhex('a2 00 00'));store(0,0);store(0x4200,0x10);code.append(0x58)
    code.extend(bytes.fromhex('ad 12 42 29 80 d0 f9'))
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    code.extend(bytes([0x4c,(0x8000+loop)&255,(0x8000+loop)>>8]))
    irq=bytearray.fromhex('48 ad 11 42 ad 12 42 29 80 d0 00 e0 e0 00 b0 00')
    irq.extend(bytes([0xa9,count,0x8d,0x75,0x43,0xbf,0x00,0x98,0x04,0x8d,0x21,0x21,
                      0xa9,dma_timer&255,0x8d,0x07,0x42,0xa9,dma_timer>>8,0x8d,0x08,0x42,
                      0xcb,0xad,0x11,0x42,0xa9,128,0x8d,0x0b,0x42,
                      0xa9,timer&255,0x8d,0x07,0x42,0xa9,timer>>8,0x8d,0x08,0x42,
                      0xe8,0x68,0x40]))
    irq[10]=len(irq)-2-11;irq[15]=len(irq)-2-16
    if len(code)>0x400:raise ValueError('FIXTURE_CODE_OVERLAP')
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x100:0x104]=bytes.fromhex('5c 00 84 01')
    rom[0x8000:0x8000+len(code)]=code;rom[0x8400:0x8400+len(irq)]=irq
    rom[0x10000:0x18000]=chrdata[:32768].ljust(32768,b'\0')
    rom[0x18000:0x18000+max(0,len(chrdata)-32768)]=chrdata[32768:]
    rom[0x20000:0x20800]=tilemap.tobytes();rom[0x20800:0x20a00]=palette.tobytes()
    rom[0x21000:0x21461]=bytes([0x81,0,0,0,57])*224+bytes([0])
    rom[0x21800:0x218e0]=targets;rom[0x28000:0x28000+len(data)]=data
    rom[0x7fc0:0x7fd5]=b'M4 BG IRQ PROOF'.ljust(21)
    rom[0x7fd5:0x7fdc]=bytes([0x20,0,8,0,1,0,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000);rom[0x7fee:0x7ff0]=struct.pack('<H',0x8100)
    if len(rom)!=262144:raise AssertionError('FIXTURE_ROM_SIZE_DRIFT')
    return bytes(rom),expected_trace,dict(chr_bytes=len(chrdata),oam_entries=0,hdma_channels=[0],dma_channel=7,
        code_bank=1,per_field_palette_restore_bytes=478,peak_cgram_data_bytes=count,
        schedule_data_bytes=len(data)+len(targets),timer_dots=timer,dma_timer_dots=dma_timer,
        mechanism='PREPARE_IRQ_THEN_MASKED_IRQ_WAI_WAKE',spc_protocol_proven=False,
        irq_entry_prg_offset=0x8400,irq_exit_prg_offset=0x8400+len(irq)-1,
        reserved_hud_sha256=hashlib.sha256(palette[112:128].tobytes()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--timer',type=int,default=80);p.add_argument('--dma-timer',type=int,default=239);a=p.parse_args();a.report=a.report.resolve()
    report=json.loads(a.report.read_text());assets=a.report.with_suffix('');folder=assets/'native';folder.mkdir(exist_ok=True)
    rom,expected_trace,resources=compile_rom(report,assets,a.timer,a.dma_timer);path=folder/'proof.sfc';path.write_bytes(rom)
    lua=folder/'observer.lua';count=report['span']*2
    lua.write_text('''local active=false;local restoring=false;local frames=0;local n=0;local rows={}
local function service(a,v)
 if active and frames==1 then local s=emu.getState();emu.log('M4IRQSERVICE|'..table.concat({a,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
end
emu.addMemoryCallback(service,emu.callbackType.exec,ENTRY,ENTRY,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(service,emu.callbackType.exec,EXIT,EXIT,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function(a,v) restoring=(v==1) end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) if v==15 and not active then active=true;frames=0 end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and not restoring and frames==1 then
  rows[#rows+1]=string.format('%04x:%02x',a,v)
  if a==0x2122 then
   n=n+1
   if n%COUNT==1 or n%COUNT==0 then local s=emu.getState();emu.log('M4IRQTIME|'..table.concat({n,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
  end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() frames=frames+1;if frames==2 then emu.log('M4IRQTRACE|'..table.concat(rows,',')) end end,emu.eventType.endFrame)
'''.replace('COUNT',str(count)).replace('ENTRY',str(resources['irq_entry_prg_offset'])).replace('EXIT',str(resources['irq_exit_prg_offset'])))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        advancement=[];advanced=0
        for _ in range(10):
            progress=m.tool('run_frames',{'count':1});advancement.append(progress)
            advanced+=progress['framesAdvanced']
            if advanced>=5:break
        shot=m.tool('take_screenshot',{'format':'path'});cgram=m.read_memory('SnesCgRam',0,512);cpu=m.get_cpu_state()
    shutil.copyfile(shot['path'],folder/'screenshot.png')
    rgb=np.asarray(Image.open(folder/'screenshot.png').convert('RGB'),dtype=np.int32)
    actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
    expected=np.frombuffer((assets/'expected.rgb555').read_bytes(),dtype='<u2').reshape(224,256)
    log=(folder/'mesen.log').read_text();vectors=[line.split('M4IRQTRACE|',1)[1] for line in log.splitlines() if 'M4IRQTRACE|' in line and line.split('M4IRQTRACE|',1)[1]]
    observed=vectors[0].split(',') if len(vectors)==1 and vectors[0] else []
    times=[[int(v) for v in line.split('M4IRQTIME|',1)[1].split(',')] for line in log.splitlines() if 'M4IRQTIME|' in line]
    service=[[int(v) for v in line.split('M4IRQSERVICE|',1)[1].split(',')] for line in log.splitlines() if 'M4IRQSERVICE|' in line]
    durations=[service[i+1][3]-service[i][3] for i in range(0,len(service)-1,2) if service[i][2]<224]
    clocks=[(r[3]+4*(r[1]//2))%1364 for r in times]
    cg=bytes.fromhex(cgram['hex']) if isinstance(cgram,dict) else bytes(cgram)
    result=dict(rom_sha256=hashlib.sha256(rom).hexdigest(),schedule_sha256=hashlib.sha256(a.report.read_bytes()).hexdigest(),
        resources=resources,cpu_state=cpu,advancement=advancement,completed_fields=advanced,
        observer_budget_yields=sum(r['timedOut'] for r in advancement),
        pixel_identity_verified=(actual.shape==expected.shape and np.array_equal(actual,expected)),
        pixel_mismatches=int(np.count_nonzero(actual!=expected)) if actual.shape==expected.shape else None,
        cgram_schedule_observer_verified=(observed==expected_trace),observed_register_writes=len(observed),
        expected_register_writes=len(expected_trace),timing_samples=len(times),active_window_sample_writes=sum(88<=c<1096 for c in clocks),
        hud_palette_unchanged=(hashlib.sha256(cg[224:256]).hexdigest()==resources['reserved_hud_sha256']),
        irq_service_samples=len(durations),peak_irq_service_master_clocks=max(durations,default=0),
        visible_field_irq_service_master_clocks=sum(durations),
        scope='Isolated fixed composed scene. No production compositor, script reachability, upload latency or real TAD protocol admission.')
    (folder/'observer.json').write_text(json.dumps(dict(observed=observed,expected=expected_trace,times=times,service=service),indent=2)+'\n')
    result['pass']=all(result[k] for k in ('pixel_identity_verified','cgram_schedule_observer_verified','hud_palette_unchanged')) and not result['active_window_sample_writes'] and advanced==5 and all(r['framesAdvanced']<=1 for r in advancement)
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
