"""Continuous isolated lossless component sequence from offline tile deadlines."""
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


def build(sequence,residency,deadlines,output,timer,word_dma=False):
    schedule=json.loads(deadlines.read_text());plan=json.loads((residency/'report.json').read_text())
    if not schedule['resident_identity_replay'] or not plan['offset_map_aliases_bg1']:
        raise ValueError('SEQUENCE_DEADLINES_OR_OFFSET_ALIAS_UNPROVEN')
    count=len(schedule['source_frame_start_fields'])
    if count>40:raise ValueError('SEQUENCE_FIXTURE_TABLE_LIMIT')
    assets=[sequence/f'frame-{i:02d}' for i in range(count)]
    reports=[json.loads((p/'frame.json').read_text()) for p in assets]
    chr_data={n:(residency/f'{n}-tiles.chr').read_bytes() for n in ('high','low')}
    cache=output/'boot-cache';cache.mkdir(exist_ok=True)
    for name in chr_data:
        plane=plan[name];size=plane['bpp']*8;data=bytearray(plane.get('slot_extent',plane['capacity'])*size)
        for w in plane['frames'][0]['writes']:
            data[w['slot']*size:(w['slot']+1)*size]=chr_data[name][w['tile']*size:(w['tile']+1)*size]
        for w in schedule['fields'][0]['jobs']:
            if w['plane']==name:data[w['slot']*size:(w['slot']+1)*size]=chr_data[name][w['tile']*size:(w['tile']+1)*size]
        (cache/f'{name}.chr').write_bytes(data)
        (cache/f'0-{name}.map').write_bytes((residency/f'00-{name}.map').read_bytes())
    (cache/'layout.json').write_text(json.dumps(dict(low_chr_vram_base=plan['allocation']['low_chr'][0])))
    raw,_,resources=compile_rom(reports[0],assets[0],timer,cache,offset_alias=True)
    rom=bytearray(raw)+bytearray([255])*(2097152-len(raw));traces=[]
    for index,(r,folder) in enumerate(zip(reports,assets)):
        initial=json.loads((folder/'initial.json').read_text());state=list(initial);targets=bytearray();payload=bytearray();trace=[]
        for row,burst in zip(r['trace'],r['contiguous_bursts']):
            if row['scanline']:
                for e in row['updates']:state[e['slot']-1]=e['color']
            start=burst['start_slot'];targets.append(start+3)
            data=struct.pack('<'+'H'*r['span'],*[v or 0 for v in state[start-1:start-1+r['span']]])
            payload.extend(data);trace.extend([f'2121:{start+3:02x}',*[f'2122:{v:02x}' for v in data]])
        rom[0x2a800+index*256:0x2a800+index*256+224]=targets
        pos=(6+index)*32768;rom[pos:pos+len(payload)]=payload
        pos=46*32768+index*472;rom[pos:pos+472]=struct.pack('<236H',*[v or 0 for v in initial])
        traces.append(trace)
    programs=[];frame=0;cursor=47*32768
    # One initial no-transfer field makes the first full visible field the
    # source clock epoch. Boot unblank itself happens during VBlank.
    fields=[dict(field=0,jobs=[],mandatory=[])]+schedule['fields'][1:]+[dict(field=schedule['fields'][-1]['field']+1,jobs=[],mandatory=[])]
    for row in fields:
        while frame+1<count and schedule['source_frame_start_fields'][frame+1]<=row['field']:frame+=1
        items=[]
        for job in row['jobs']:
            raw=chr_data[job['plane']];size=job['bytes']
            items.append((job['address'],raw[job['tile']*size:(job['tile']+1)*size]))
        for t in row['mandatory']:
            name='high' if t['address']<0xf800 else 'low';base=0xf000 if name=='high' else 0xf800
            data=(residency/f'{frame:02d}-{name}.map').read_bytes();start=t['address']-base
            items.append((t['address'],data[start:start+t['bytes']]))
        packets=[]
        for address,data in sorted(items):
            if packets and packets[-1][0]+len(packets[-1][1])==address:packets[-1][1].extend(data)
            else:packets.append([address,bytearray(data)])
        reserve=1024+50*len(packets);payload_size=sum(len(p[1]) for p in packets)
        if cursor%32768+reserve+payload_size>32768:cursor=(cursor//32768+1)*32768
        if cursor+reserve+payload_size>len(rom):raise ValueError('CONTINUOUS_FIXTURE_ROM_LIMIT')
        start=cursor;code=bytearray();data_cursor=start+reserve;settings={}
        def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
        def dma(source,bank,dest,size,target=None):
            if word_dma:
                def word(address,value):code.extend(bytes([0xa9,value&255,value>>8,0x8d,address&255,address>>8]))
                if target is not None:word(0x2116,target)
                cfg=(1 if dest==0x18 else 0)|(dest<<8)
                if settings.get('cfg')!=cfg:word(0x4370,cfg);settings['cfg']=cfg
                if settings.get('bank')!=bank:word(0x4374,bank);settings['bank']=bank
                word(0x4372,source);word(0x4375,size)
                # The transfer owns VBlank: clear HDMA during each word trigger
                # and restore its field mask once all transfer work is complete.
                word(0x420b,128)
                return
            if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
            for address,value in [(0x4370,1 if dest==0x18 else 0),(0x4371,dest),(0x4374,bank)]:
                if settings.get(address)!=value:store(address,value);settings[address]=value
            for address,value in [(0x4372,source&255),(0x4373,source>>8),(0x4375,size&255),(0x4376,size>>8),(0x420b,128)]:store(address,value)
        code.extend(bytes.fromhex('ad 12 42 29 80 d0 f9 ad 12 42 29 80 f0 f9 78'))
        store(0x4200,0);store(0,1)
        store(5,row['field'])
        if word_dma:code.extend(bytes.fromhex('c2 20'))
        for address,data in packets:
            rom[data_cursor:data_cursor+len(data)]=data
            dma(0x8000+data_cursor%32768,data_cursor//32768,0x18,len(data),address//2);data_cursor+=len(data)
        if word_dma:code.extend(bytes.fromhex('e2 20'))
        store(0x2121,4)
        if word_dma:code.extend(bytes.fromhex('c2 20'))
        dma(0x8000+frame*472,46,0x22,472)
        if word_dma:
            code.extend(bytes.fromhex('e2 20'));store(0x420c,1)
        for address,value in [(0x4370,0),(0x4371,0x22),(0x4372,0),(0x4373,0x80),(0x4374,6+frame),
                              (0x4375,reports[frame]['span']*2),(0x4376,0),(2,224),(3,frame),(4,reports[frame]['span']*2),(1,frame)]:store(address,value)
        code.extend(bytes([0xa2,0,frame]));store(0,0);store(0x4200,0x10);code.append(0x58)
        jump=len(code);code.extend(bytes.fromhex('5c 00 00 00'))
        if len(code)>reserve:raise ValueError('CONTINUOUS_CODE_RESERVATION')
        rom[start:start+len(code)]=code
        programs.append(dict(field=row['field'],frame=frame,start=start,jump=start+jump,packets=len(packets),bytes=payload_size))
        cursor=data_cursor
    for index,p in enumerate(programs):
        target=programs[index+1]['start'] if index+1<len(programs) else p['start']
        rom[p['jump']+1:p['jump']+4]=bytes([(0x8000+target%32768)&255,(0x8000+target%32768)>>8,0x80+target//32768])
    prefix=rom[0x8000:0x8400];end=prefix.find(bytes.fromhex('a9 0f 8d 00 21'))
    if end<0:raise ValueError('CONTINUOUS_BOOT_PREFIX')
    code=bytearray(prefix[:end])
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    for address,value in [(0,0),(1,0),(2,224),(3,0),(4,reports[0]['span']*2),(5,0),
                          (0x4370,0),(0x4371,0x22),(0x4372,0),(0x4373,0x80),(0x4374,6),(0x4375,reports[0]['span']*2),(0x4376,0),(0x420d,1)]:store(address,value)
    code.extend(bytes.fromhex('a2 00 00'));store(0x2100,15);store(0x4200,0x10);code.append(0x58)
    target=programs[0]['start'];code.extend(bytes([0x5c,(0x8000+target%32768)&255,(0x8000+target%32768)>>8,0x80+target//32768]))
    if len(code)>0x700:raise ValueError('CONTINUOUS_BOOT_SIZE')
    rom[0x8000:0x8800]=bytes(0x800);rom[0x8000:0x8000+len(code)]=code
    rom[:4]=bytes.fromhex('5c 00 80 81')
    irq=bytearray.fromhex('48 ad 11 42 ad 12 42 29 80 d0 00 e4 02 b0 00')
    irq.extend(bytes.fromhex('a5 04 8d 75 43 bf 00 a8 05 8d 21 21 a9 80 8d 0b 42 e8 68 40'))
    irq[10]=len(irq)-2-11;irq[14]=len(irq)-2-15
    rom[0x100:0x104]=bytes.fromhex('5c 00 f0 01');rom[0xf000:0xf000+len(irq)]=irq
    rom[0x7fd5]=0x30;rom[0x7fd7]=11
    resources.update(programs=programs,source_frame_start_fields=schedule['source_frame_start_fields'],
                     main_cpu_fastrom=True,irq_cpu_fastrom=False,source_clock_hypothesis=[200,60],
                     full_sequence_production_admitted=False)
    resources['word_dma']=word_dma
    return bytes(rom),traces,resources,assets


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('sequence','residency','deadlines','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--timer',type=int,default=160);p.add_argument('--word-dma',action='store_true')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    rom,traces,resources,assets=build(a.sequence,a.residency,a.deadlines,folder,a.timer,a.word_dma)
    path=folder/'proof.sfc';path.write_bytes(rom);lua=folder/'observer.lua'
    lua.write_text('''local active=false;local restore=false;local frames=0;local n=0;local rows={};local field=0
emu.addMemoryCallback(function(a,v)
 restore=v==1
 if active and frames<75 then local s=emu.getState();emu.log('SEQBOUND|'..table.concat({v,emu.read(5,emu.memType.snesMemory),s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) if v==15 then active=true;frames=0 end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and not restore and frames>=1 and frames<=74 then
  if n==0 then field=emu.read(1,emu.memType.snesMemory) end
  n=n+1;rows[#rows+1]=string.format('%04x:%02x',a,v)
  local count=1+emu.read(4,emu.memType.snesMemory)
  if n%count==2 or n%count==0 then local s=emu.getState();emu.log('SEQTIME|'..table.concat({s['ppu.frameCount'],s['ppu.scanline'],s['masterClock']},',')) end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() if active and frames>=1 and frames<=74 then emu.log('SEQTRACE|'..field..'|'..table.concat(rows,','));rows={};n=0 end;frames=frames+1 end,emu.eventType.endFrame)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    expected=[np.fromfile(f/'expected.rgb555',dtype='<u2').reshape(224,256) for f in assets];pixels=[];advanced=0;advancement=[]
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        for _ in range(85):
            progress=m.tool('run_frames',{'count':1});advancement.append(progress);advanced+=progress['framesAdvanced']
            if progress['framesAdvanced']:
                shot=m.tool('take_screenshot',{'format':'path'});rgb=np.asarray(Image.open(shot['path']).convert('RGB'),dtype=np.int32)
                actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
                matches=[i for i,e in enumerate(expected) if actual.shape==e.shape and np.array_equal(actual,e)]
                pixels.append(dict(field=advanced,matches=matches))
                if matches:shutil.copyfile(shot['path'],folder/f'frame-{matches[0]:02d}.png')
            if advanced>=78:break
    lines=(folder/'mesen.log').read_text().splitlines();observed=[]
    for line in lines:
        if 'SEQTRACE|' in line:
            frame,data=line.split('SEQTRACE|',1)[1].split('|',1);frame=int(frame)
            observed.append(dict(frame=frame,verified=data.split(',')==traces[frame],writes=len(data.split(','))))
    times=[[int(v) for v in line.split('SEQTIME|',1)[1].split(',')] for line in lines if 'SEQTIME|' in line]
    bounds=[[int(v) for v in line.split('SEQBOUND|',1)[1].split(',')] for line in lines if 'SEQBOUND|' in line]
    windows=[dict(field=bounds[i+1][1],start_line=bounds[i][3],end_line=bounds[i+1][3],master_clocks=bounds[i+1][4]-bounds[i][4]) for i in range(0,len(bounds)-1,2)]
    unsafe=sum(88<=(r[2]+4*(r[0]//2))%1364<1096 for r in times)
    starts=resources['source_frame_start_fields']
    def frame_at(field):return max(i for i,t in enumerate(starts) if t<=field)
    observer_cadence=(len(observed)==74 and all(r['frame']==frame_at(i) for i,r in enumerate(observed)))
    # Screenshots expose the last completed display buffer, one field behind
    # the current IRQ observer epoch, after two forced-blank boot fields.
    pixel_cadence=all(frame_at(p['field']-4) in p['matches'] for p in pixels if p['field']>=4)
    result=dict(resources=resources,rom_sha256=hashlib.sha256(rom).hexdigest(),pixels=pixels,observer=observed,
                transfer_windows=windows,timing_samples=len(times),unsafe_palette_samples=unsafe,no_color_reduction=True,
                observer_cadence_verified=observer_cadence,pixel_cadence_verified=pixel_cadence,
                scope='Continuous precomposed fixed-context sequence at offline 200/60 clock hypothesis. No live compositor, production TAD/MSU or MOTU gameplay.')
    result['pass']=(advanced==78 and all(r['framesAdvanced']<=1 for r in advancement)
                    and observer_cadence and pixel_cadence and all(r['verified'] for r in observed) and len(times)==74*448 and unsafe==0
                    and all(225<=r['start_line']<=r['end_line']<=261 for r in windows)
                    and all(p['matches'] for p in pixels[2:])
                    and set(range(len(assets)))<=set(i for p in pixels for i in p['matches']))
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
