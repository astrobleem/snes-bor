"""Isolated native source-pose cache refill, with exact pixels and bus witnesses."""
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
from _harness import McpSession, MESEN_EXE, _free_tcp_port


def build(sequence, residency, index, output, timer, preload_first_packets=None):
    plan = json.loads((residency/'report.json').read_text())
    if not 1 <= index < len(plan['high']['frames']):
        raise ValueError('REFILL_TRANSITION_INDEX')
    assets = [sequence/f'frame-{i:02d}' for i in (index-1,index)]
    reports = [json.loads((p/'frame.json').read_text()) for p in assets]
    cache = output/'boot-cache';cache.mkdir(exist_ok=True)
    packets = {'PRELOAD':[], 'COMMIT':[]}
    for name, base in [('high',0),('low',49152)]:
        plane=plan[name];size=plane['bpp']*8
        tiles=(residency/f'{name}-tiles.chr').read_bytes()
        resident=bytearray(plane.get('slot_extent',plane['capacity'])*size)
        for frame in plane['frames'][:index]:
            for w in frame['writes']:
                resident[w['slot']*size:(w['slot']+1)*size]=tiles[w['tile']*size:(w['tile']+1)*size]
        (cache/f'{name}.chr').write_bytes(resident)
        (cache/f'0-{name}.map').write_bytes((residency/f'{index-1:02d}-{name}.map').read_bytes())
        # Coalesce contiguous destination slots; source bytes are copied offline.
        for phase in packets:
            writes=sorted((w for w in plane['frames'][index]['writes'] if w['phase']==phase),key=lambda w:w['slot'])
            for w in writes:
                address=base+w['slot']*size;data=tiles[w['tile']*size:(w['tile']+1)*size]
                if packets[phase] and packets[phase][-1][0]+len(packets[phase][-1][1])==address:
                    packets[phase][-1][1].extend(data)
                else:packets[phase].append([address,bytearray(data)])
    transition=plan['transitions'][index-1]
    for t in transition['tilemap_transfers']:
        name='high' if t['vram_byte_address']<0xf800 else 'low'
        data=(residency/f'{index:02d}-{name}.map').read_bytes()
        packets['COMMIT'].append([t['vram_byte_address'],bytearray(data[t['source_byte_offset']:t['source_byte_offset']+t['bytes']])])
    (cache/'layout.json').write_text(json.dumps(dict(low_chr_vram_base=plan['allocation']['low_chr'][0])))
    raw,_,resources=compile_rom(reports[0],assets[0],timer,cache,offset_alias=plan.get('offset_map_aliases_bg1',False))
    rom=bytearray(raw)+bytearray([255])*262144
    prefix=rom[0x8000:0x8400];end=prefix.find(bytes.fromhex('a9 0f 8d 00 21'))
    if end<0:raise ValueError('REFILL_BOOT_PREFIX')
    code=bytearray(prefix[:end]);traces=[]
    for field,(report,folder) in enumerate(zip(reports,assets)):
        state=json.loads((folder/'initial.json').read_text());initial=list(state);targets=bytearray();payload=bytearray();trace=[]
        for row,burst in zip(report['trace'],report['contiguous_bursts']):
            if row['scanline']:
                for event in row['updates']:state[event['slot']-1]=event['color']
            start=burst['start_slot'];targets.append(start+3)
            data=struct.pack('<'+'H'*report['span'],*[v or 0 for v in state[start-1:start-1+report['span']]])
            payload.extend(data);trace.extend([f'2121:{start+3:02x}',*[f'2122:{v:02x}' for v in data]])
        rom[0x2a800+field*256:0x2a800+field*256+224]=targets
        rom[0x30000+field*32768:0x30000+field*32768+len(payload)]=payload
        rom[0x2c000+field*512:0x2c000+field*512+472]=struct.pack('<236H',*[v or 0 for v in initial])
        traces.append(trace)
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    dma_settings={}
    def dma(source,bank,dest,data_len,target=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for address,value in [(0x4370,1 if dest==0x18 else 0),(0x4371,dest),(0x4374,bank)]:
            if dma_settings.get(address)!=value:store(address,value);dma_settings[address]=value
        for address,value in [(0x4372,source&255),(0x4373,source>>8),(0x4375,data_len&255),(0x4376,data_len>>8),(0x420b,128)]:store(address,value)
    def prepare(field):
        for address,value in [(0x4370,0),(0x4371,0x22),(0x4372,0),(0x4373,0x80),(0x4374,6+field),
                              (0x4375,reports[field]['span']*2),(0x4376,0),(2,224),(3,field),(4,reports[field]['span']*2),(1,field)]:store(address,value)
        code.extend(bytes([0xa2,0,field]))
        dma_settings.clear()  # IRQ preparation replaces the channel registers.
    def wait():code.extend(bytes.fromhex('ad 12 42 29 80 d0 f9 ad 12 42 29 80 f0 f9 78'));store(0x4200,0)
    cursor=0x40000
    def transfer(phase, selected=None):
        nonlocal cursor
        store(0,1 if phase=='PRELOAD' else 2)
        for address,data in (packets[phase] if selected is None else selected):
            if cursor%32768+len(data)>32768:cursor=(cursor//32768+1)*32768
            rom[cursor:cursor+len(data)]=data
            dma(0x8000+cursor%32768,cursor//32768,0x18,len(data),address//2);cursor+=len(data)
    def palette(field):store(0x2121,4);dma(0xc000+field*512,5,0x22,472)
    def resume(field):prepare(field);store(0,0);store(0x4200,0x10);code.append(0x58)
    store(0,0);prepare(0);store(0x2100,15);store(0x4200,0x10);code.append(0x58)
    # Preserve displayed slots while spreading safe preloads across two fields.
    if preload_first_packets==-1:
        # Seven immediate-store pairs per packet cost 42 CPU cycles; data DMA
        # costs eight master clocks per byte. This selects a candidate split,
        # never hardware admission: the complete native windows decide PASS.
        costs=[8*len(data)+336 for _,data in packets['PRELOAD']]
        commit_cost=sum(8*len(data)+336 for _,data in packets['COMMIT'])
        split=min(range(len(costs)+1),key=lambda n:max(sum(costs[:n]),sum(costs[n:])+commit_cost))
    else:split=len(packets['PRELOAD'])//2 if preload_first_packets is None else preload_first_packets
    if not 0<=split<=len(packets['PRELOAD']):raise ValueError('REFILL_PRELOAD_SPLIT')
    wait();transfer('PRELOAD',packets['PRELOAD'][:split]);palette(0);resume(0)
    if preload_first_packets is None:
        wait();transfer('PRELOAD',packets['PRELOAD'][split:]);palette(0);resume(0)
        wait();transfer('COMMIT');palette(1);resume(1)
    else:
        packets['COMMIT']=packets['PRELOAD'][split:]+packets['COMMIT']
        packets['PRELOAD']=packets['PRELOAD'][:split]
        wait();transfer('COMMIT');palette(1);resume(1)
    loop=len(code);wait();store(0,3);palette(1);resume(1)
    code.extend(bytes([0x4c,(0x8000+loop)&255,(0x8000+loop)>>8]))
    irq=bytearray.fromhex('48 ad 11 42 ad 12 42 29 80 d0 00 e4 02 b0 00')
    irq.extend(bytes.fromhex('a5 04 8d 75 43 bf 00 a8 05 8d 21 21 a9 80 8d 0b 42 e8 68 40'))
    irq[10]=len(irq)-2-11;irq[14]=len(irq)-2-15
    if len(code)>0x7000 or cursor>len(rom):raise ValueError('REFILL_ROM_CAPACITY')
    rom[0x8000:0xf000]=bytes(0x7000);rom[0x8000:0x8000+len(code)]=code
    rom[0x100:0x104]=bytes.fromhex('5c 00 f0 01');rom[0xf000:0xf000+len(irq)]=irq
    rom[0x7fd7]=9
    resources.update(transition=transition,descriptors={p:len(v) for p,v in packets.items()},
                     irq_entry_prg_offset=0xf000,irq_exit_prg_offset=0xf000+len(irq)-1,
                     palette_spans=[r['span'] for r in reports],source_frame_indices=[index-1,index],
                     preload_first_packets=preload_first_packets,resolved_preload_first_packets=split)
    return bytes(rom),traces,packets,resources,assets


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sequence',type=Path,required=True)
    p.add_argument('--residency',type=Path,required=True);p.add_argument('--to-frame',type=int,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--timer',type=int,default=160)
    p.add_argument('--preload-first-packets',type=int,help='Use two VBlanks: N safe preload packets first, remainder with commit; -1 selects a measured candidate automatically')
    a=p.parse_args();two=a.preload_first_packets is not None
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    rom,traces,packets,resources,assets=build(a.sequence,a.residency,a.to_frame,folder,a.timer,a.preload_first_packets)
    path=folder/'proof.sfc';path.write_bytes(rom);lua=folder/'observer.lua'
    lua.write_text('''local active=false;local phase=0;local v={};local frames=0;local rows={};local n=0;local field=0
emu.addMemoryCallback(function(a,value)
 if active and frames<5 then
  local s=emu.getState();emu.log('REFILLBOUND|'..table.concat({value,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},','))
  if value~=0 then phase=value;v={} else if phase==1 or phase==2 then emu.log('REFILLVRAM|'..phase..'|'..table.concat(v,',')) end;phase=0 end
 end
end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,value) if active and (phase==1 or phase==2) then v[#v+1]=string.format('%02x',value) end end,emu.callbackType.write,0x2118,0x2119,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,value) if value==15 then active=true;frames=0 end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,value)
 if active and phase==0 and frames>=1 and frames<=4 then
  if n==0 then field=emu.read(1,emu.memType.snesMemory) end
  n=n+1;rows[#rows+1]=string.format('%04x:%02x',a,value)
  local count=1+emu.read(4,emu.memType.snesMemory)
  if n%count==2 or n%count==0 then local s=emu.getState();emu.log('REFILLTIME|'..table.concat({n,s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() if active and frames>=1 and frames<=4 then emu.log('REFILLTRACE|'..field..'|'..table.concat(rows,','));rows={};n=0 end;frames=frames+1 end,emu.eventType.endFrame)
''')
    if two:
        lua.write_text(lua.read_text().replace('frames<5','frames<4').replace('frames<=4','frames<=3'))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    expected=[np.fromfile(f/'expected.rgb555',dtype='<u2').reshape(224,256) for f in assets];pixels=[];advancement=[];advanced=0
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        for _ in range(12):
            progress=m.tool('run_frames',{'count':1});advancement.append(progress);advanced+=progress['framesAdvanced']
            if progress['framesAdvanced']:
                shot=m.tool('take_screenshot',{'format':'path'});rgb=np.asarray(Image.open(shot['path']).convert('RGB'),dtype=np.int32)
                actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
                matches=[i for i,e in enumerate(expected) if actual.shape==e.shape and np.array_equal(actual,e)]
                pixels.append(dict(field=advanced,matches=matches,mismatches=[int(np.count_nonzero(actual!=e)) for e in expected] if actual.shape==expected[0].shape else None))
                shutil.copyfile(shot['path'],folder/f'field-{advanced}.png')
            if advanced>=(7 if two else 8):break
    lines=(folder/'mesen.log').read_text().splitlines();observed=[];vr=[]
    preload_vectors=[]
    for line in lines:
        if 'REFILLTRACE|' in line:
            field,data=line.split('REFILLTRACE|',1)[1].split('|',1);field=int(field)
            observed.append(dict(frame=field,writes=len(data.split(',')),verified=data.split(',')==traces[field]))
        if 'REFILLVRAM|' in line:
            phase,data=line.split('REFILLVRAM|',1)[1].split('|',1);phase=int(phase)
            split=len(packets['PRELOAD'])//2
            selected=(packets['PRELOAD'] if two else packets['PRELOAD'][:split] if not preload_vectors else packets['PRELOAD'][split:]) if phase==1 else packets['COMMIT']
            if phase==1:preload_vectors.append(data)
            expect=b''.join(bytes(v) for _,v in selected)
            values=data.split(',') if data else []
            vr.append(dict(phase=phase,bytes=len(values),verified=values==[f'{v:02x}' for v in expect]))
    times=[[int(v) for v in line.split('REFILLTIME|',1)[1].split(',')] for line in lines if 'REFILLTIME|' in line]
    bounds=[[int(v) for v in line.split('REFILLBOUND|',1)[1].split(',')] for line in lines if 'REFILLBOUND|' in line]
    durations=[dict(phase=bounds[i][0],master_clocks=bounds[i+1][3]-bounds[i][3],start_line=bounds[i][2],end_line=bounds[i+1][2]) for i in range(0,len(bounds)-1,2)]
    unsafe=sum(88<=(r[3]+4*(r[1]//2))%1364<1096 for r in times)
    result=dict(resources=resources,rom_sha256=hashlib.sha256(rom).hexdigest(),pixels=pixels,advancement=advancement,
                observer=observed,vram_observer=vr,transfer_windows=durations,timing_samples=len(times),unsafe_cgram_samples=unsafe,
                no_color_reduction=True,scope='Isolated one-way cached-pose preload/commit. No live compositor, production audio, full animation or source cadence admission.')
    # Both preloads must leave the previous source pose pixel exact.
    previous=[p for p in pixels if p['field'] in ((3,4) if two else (3,4,5))]
    result['pass']=(advanced==(7 if two else 8) and all(p['framesAdvanced']<=1 for p in advancement) and len(observed)==(3 if two else 4) and all(r['verified'] for r in observed)
                    and len(vr)==(2 if two else 3) and all(r['verified'] for r in vr) and len(times)==(1344 if two else 1792) and unsafe==0
                    and all(225<=r['start_line']<=r['end_line']<=261 for r in durations)
                    and len(previous)==(2 if two else 3) and all(0 in p['matches'] for p in previous)
                    and all(1 in p['matches'] for p in pixels[-3:]))
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
