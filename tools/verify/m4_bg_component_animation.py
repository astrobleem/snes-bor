"""Bounded two-frame native lossless BG cache transition with exact observers."""
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
from m4_bg_components_native import compile_rom
from _harness import McpSession,MESEN_EXE,_free_tcp_port


def build(reports,assets,cache,timer):
    if any(r.get('span')!=13 for r in reports):raise ValueError('ANIMATION_FIXTURE_13_COLOR_CONTRACT')
    raw,_,resources=compile_rom(reports[0],assets[0],timer,cache)
    rom=bytearray(raw);prefix=rom[0x8000:0x8400]
    end=prefix.find(bytes.fromhex('a9 0f 8d 00 21'))
    if end<0:raise ValueError('FIXTURE_PREFIX_CONTRACT')
    code=bytearray(prefix[:end]);expected=[]
    for field,(report,folder) in enumerate(zip(reports,assets)):
        state=json.loads((folder/'initial.json').read_text());initial=list(state)
        targets=bytearray();payload=bytearray();trace=[]
        for row,burst in zip(report['trace'],report['contiguous_bursts']):
            if row['scanline']:
                for event in row['updates']:state[event['slot']-1]=event['color']
            start=burst['start_slot'];targets.append(start+3)
            data=struct.pack('<13H',*[v or 0 for v in state[start-1:start+12]])
            payload.extend(data);trace.extend([f'2121:{start+3:02x}',*[f'2122:{v:02x}' for v in data]])
        rom[0x2a800+field*256:0x2a800+field*256+224]=targets
        rom[0x30000+field*32768:0x30000+field*32768+len(payload)]=payload
        expected.append(trace)
        if field:
            rom[0x2b000:0x2b800]=(cache/'1-high.map').read_bytes()
            rom[0x2b800:0x2c000]=(cache/'1-low.map').read_bytes()
            palette=np.zeros(256,dtype='<u2');palette[:4]=report['low_component_palette']
            palette[4:240]=[v or 0 for v in initial];palette[240:]=np.arange(16)+0x1234
            rom[0x2c000:0x2c200]=palette.tobytes()
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    def dma(source,destination,count,target=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for address,value in [(0x4370,1 if destination==0x18 else 0),(0x4371,destination),
                              (0x4372,source&255),(0x4373,source>>8),(0x4374,5),
                              (0x4375,count&255),(0x4376,count>>8),(0x420b,128)]:store(address,value)
    def prepare(field):
        for address,value in [(0x4370,0),(0x4371,0x22),(0x4372,0),(0x4373,0x80),
                              (0x4374,6+field),(0x4375,26),(0x4376,0),
                              (2,224),(3,field)]:store(address,value)
        code.extend(bytes([0xa2,0,field]))
    store(0,0);store(1,0);prepare(0);store(0x2100,15);store(0x4200,0x10);code.append(0x58)
    loop=len(code)
    code.extend(bytes.fromhex('ad 12 42 29 80 d0 f9 ad 12 42 29 80 f0 f9 78'))
    store(0x4200,0);store(0,1)
    code.extend(bytes.fromhex('ad 01 00 49 01 8d 01 00 d0 03'))
    jump_first=len(code);code.extend(b'\x4c\x00\x00')
    for field in (1,0):
        if field==0:code[jump_first+1:jump_first+3]=struct.pack('<H',0x8000+len(code))
        store(0x2121,4);dma(0xc008 if field else 0x9008,0x22,472)
        for map_base,source in [(0xf000,0xb000 if field else 0x8000),(0xf800,0xb800 if field else 0x8800)]:
            dma(source+832,0x18,512,(map_base+832)//2)
        prepare(field)
        if field:
            jump_done=len(code);code.extend(b'\x4c\x00\x00')
    code[jump_done+1:jump_done+3]=struct.pack('<H',0x8000+len(code))
    store(0,0);store(0x4200,0x10);code.extend(bytes([0x58,0x4c,(0x8000+loop)&255,(0x8000+loop)>>8]))
    irq=bytearray.fromhex('48 ad 11 42 ad 12 42 29 80 d0 00 e4 02 b0 00')
    irq.extend(bytes.fromhex('a9 1a 8d 75 43 bf 00 a8 05 8d 21 21 a9 80 8d 0b 42 e8 68 40'))
    irq[10]=len(irq)-2-11;irq[14]=len(irq)-2-15
    if len(code)>0x700:raise ValueError('ANIMATION_FIXTURE_CODE_OVERLAP')
    rom[0x8000:0x8800]=bytes(0x800);rom[0x8000:0x8000+len(code)]=code
    rom[0x100:0x104]=bytes.fromhex('5c 00 88 01');rom[0x8800:0x8800+len(irq)]=irq
    resources.update(irq_entry_prg_offset=0x8800,irq_exit_prg_offset=0x8800+len(irq)-1,
                     cached_frames=2,tilemap_bytes_per_transition=1024,chr_bytes_per_transition=0,
                     palette_bytes_per_transition=472,source_animation_timing_admitted=False)
    return bytes(rom),expected,resources


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frame',type=Path,action='append',required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timer',type=int,default=160);a=p.parse_args()
    if len(a.frame)!=2:raise ValueError('TWO_FRAME_FIXTURE')
    reports=[json.loads(f.read_text()) for f in a.frame];assets=[f.with_suffix('') for f in a.frame]
    folder=a.output.resolve();folder.mkdir(exist_ok=True);rom,traces,resources=build(reports,assets,a.cache,a.timer)
    path=folder/'proof.sfc';path.write_bytes(rom);lua=folder/'observer.lua'
    lua.write_text('''local active=false;local restoring=false;local frames=0;local n=0;local rows={};local field=-1;local vr={}
emu.addMemoryCallback(function(a,v)
 restoring=v==1
 if active and frames>=1 and frames<=2 then
  local s=emu.getState();emu.log('M4ANIMVBLANK|'..table.concat({v,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},','))
  if v==1 then vr={} else emu.log('M4ANIMVRAM|'..emu.read(1,emu.memType.snesMemory)..'|'..table.concat(vr,',')) end
 end
end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and restoring and frames>=1 and frames<=2 then vr[#vr+1]=string.format('%02x',v) end
end,emu.callbackType.write,0x2118,0x2119,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) if v==15 and not active then active=true;frames=0 end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and not restoring and frames>=1 and frames<=2 then
  if n==0 then field=emu.read(1,emu.memType.snesMemory) end
  n=n+1;rows[#rows+1]=string.format('%04x:%02x',a,v)
  if n%27==2 or n%27==0 then local s=emu.getState();emu.log('M4ANIMTIME|'..table.concat({n,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 if active and frames>=1 and frames<=2 then emu.log('M4ANIMTRACE|'..field..'|'..table.concat(rows,','));rows={};n=0 end
 frames=frames+1
end,emu.eventType.endFrame)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    expected=[np.fromfile(f/'expected.rgb555',dtype='<u2').reshape(224,256) for f in assets]
    pixels=[];advancement=[]
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        advanced=0
        for _ in range(10):
            progress=m.tool('run_frames',{'count':1});advancement.append(progress);advanced+=progress['framesAdvanced']
            if progress['framesAdvanced']:
                shot=m.tool('take_screenshot',{'format':'path'})
                rgb=np.asarray(Image.open(shot['path']).convert('RGB'),dtype=np.int32)
                actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
                matches=[i for i,e in enumerate(expected) if actual.shape==e.shape and np.array_equal(actual,e)]
                memory=m.read_memory('SnesMemory',1,1)
                pixels.append(dict(field=advanced,matches=matches,state=memory.hex() if isinstance(memory,bytes) else memory,
                    mismatches=[int(np.count_nonzero(actual!=e)) for e in expected] if actual.shape==expected[0].shape else None))
                shutil.copyfile(shot['path'],folder/f'field-{advanced}.png')
                if matches:shutil.copyfile(shot['path'],folder/f'frame-{matches[0]}.png')
            if advanced>=6:break
    log=(folder/'mesen.log').read_text();observed=[]
    for line in log.splitlines():
        if 'M4ANIMTRACE|' in line:
            field,vector=line.split('M4ANIMTRACE|',1)[1].split('|',1)
            observed.append(dict(frame=int(field),writes=vector.split(','),verified=vector.split(',')==traces[int(field)]))
    times=[[int(v) for v in line.split('M4ANIMTIME|',1)[1].split(',')] for line in log.splitlines() if 'M4ANIMTIME|' in line]
    clocks=[(r[3]+4*(r[1]//2))%1364 for r in times]
    vr=[]
    for line in log.splitlines():
        if 'M4ANIMVRAM|' in line:
            field,vector=line.split('M4ANIMVRAM|',1)[1].split('|',1);field=int(field)
            data=b''.join((a.cache/f'{field}-{plane}.map').read_bytes()[832:1344] for plane in ('high','low'))
            vr.append(dict(frame=field,bytes=len(vector.split(',')),verified=vector.split(',')==[f'{v:02x}' for v in data]))
    vblank=[[int(v) for v in line.split('M4ANIMVBLANK|',1)[1].split(',')] for line in log.splitlines() if 'M4ANIMVBLANK|' in line]
    vdurations=[vblank[i+1][3]-vblank[i][3] for i in range(0,len(vblank)-1,2)]
    tail=[r['matches'] for r in pixels[-3:]]
    result=dict(resources=resources,rom_sha256=hashlib.sha256(rom).hexdigest(),pixels=pixels,
        advancement=advancement,completed_fields=advanced,observer_frames=[dict(frame=r['frame'],verified=r['verified'],writes=len(r['writes'])) for r in observed],
        timing_samples=len(times),unsafe_cgram_samples=sum(88<=c<1096 for c in clocks),no_color_reduction=True,
        tilemap_observer=vr,vblank_transition_samples=vblank,vblank_transition_master_clocks=vdurations,
        scope='Alternating cached source poses. No source cadence, live compositor, cache refill or production TAD admission.')
    result['pass']=(advanced==6 and all(r['framesAdvanced']<=1 for r in advancement) and len(observed)==2
                    and all(r['verified'] for r in observed) and len(times)==896 and not result['unsafe_cgram_samples']
                    and len(vr)==2 and all(r['verified'] for r in vr) and len(vblank)==4 and all(225<=r[2]<=261 for r in vblank)
                    and len(tail)==3 and all(len(t)==1 for t in tail) and tail[0]==tail[2] and tail[0]!=tail[1])
    (folder/'observer.json').write_text(json.dumps(dict(observed=observed,times=times),indent=2)+'\n')
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
