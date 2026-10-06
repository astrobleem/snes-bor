"""Compile a continuous fixed-context sequence into the banked canvas NMI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from m4_bg_components_native import compile_rom
from m4_raster_production_nmi import build as production_build
from m4_raster_irq_gate_native import gate_observer
from actor_s5_entity_fixture import symbols
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,exact_input_edge,run_frames_exact
import game_bor_startup_select as startup


def build(sequence,residency,deadlines,original,sy,folder,audio_service=False,source_clock=False,compact_canvas_nmi=False,sparse_palette=False,serialize_audio_raster=False,fold_first_use=False):
    schedule=json.loads(deadlines.read_text());plan=json.loads((residency/'report.json').read_text())
    if not schedule['resident_identity_replay']:raise ValueError('PRODUCTION_SEQUENCE_UNPROVEN_DEADLINES')
    hybrid=plan.get('schema')=='BYOR_HYBRID_FIXED_CONTEXT_RESIDENCY_V1'
    assets=[sequence/f'frame-{i:02d}' for i in range(len(schedule['source_frame_start_fields']))]
    if hybrid:
        from m4_hybrid_scene_native import prepare
        prepared=[prepare(p) for p in assets];reports=[v[1] for v in prepared];assets=[v[3] for v in prepared]
        for r in reports:r['native_obj_entries']=plan['static_obj_entries']
    else:reports=[json.loads((p/'frame.json').read_text()) for p in assets]
    initials=[json.loads((p/'initial.json').read_text()) for p in assets]
    folds=[]
    if fold_first_use:
        if not sparse_palette:raise ValueError('FIRST_USE_REQUIRES_SPARSE_PALETTE_EVENTS')
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
        from raster_palette_first_use import fold
        transformed=[]
        for i,(report,initial,asset) in enumerate(zip(reports,initials,assets)):
            indices=np.fromfile(asset/'indices.bin',dtype=np.uint8).reshape(224,256)+3
            revised,palette,evidence=fold(report,initial,indices)
            destination=folder/'first-use-inputs'/f'frame-{i:02d}';destination.mkdir(parents=True,exist_ok=True)
            for n in ('indices.bin','low_indices.bin','expected.rgb555'):
                if not (destination/n).exists():os.link(asset/n,destination/n)
            (destination/'initial.json').write_text(json.dumps(palette)+'\n')
            (destination/'report.json').write_text(json.dumps(revised)+'\n')
            reports[i]=revised;initials[i]=palette;folds.append(evidence);transformed.append(destination)
        assets=transformed
    prefix=100
    if hybrid:
        prefix=0
        while prefix<236 and all((v[prefix] or 0)==(initials[0][prefix] or 0) for v in initials):prefix+=1
        if prefix==236:raise ValueError('HYBRID_FULLY_STATIC_SEQUENCE_RESTORE_NOT_REQUIRED')
    suffix=0
    if hybrid:
        while suffix<236-prefix and all((v[235-suffix] or 0)==(initials[0][235-suffix] or 0) for v in initials):suffix+=1
        for r in reports:
            if any(e['slot']>236-suffix and (e['color'] or 0)!=(initials[0][e['slot']-1] or 0)
                   for row in r['trace'] for e in row['updates']):raise ValueError('HYBRID_FIXED_SUFFIX_MUTATION')
    palette_count=236-prefix-suffix;palette_bytes=palette_count*2
    if any(row[:prefix]!=initials[0][:prefix] for row in initials):raise ValueError('SEQUENCE_ANCHOR_IDENTITY')
    for r,initial in zip(reports,initials):
        if any(e['slot']<=prefix and e['color']!=initial[e['slot']-1] for row in r['trace'] for e in row['updates']):
            raise ValueError('SEQUENCE_ANCHOR_MUTATION')
    chr_data={n:(residency/f'{n}-tiles.chr').read_bytes() for n in ('high','low')}
    cache=folder/'boot-cache';cache.mkdir(exist_ok=True)
    for name in chr_data:
        plane=plan[name];size=plane['bpp']*8;data=bytearray(plane.get('slot_extent',plane['capacity'])*size)
        for w in [*plane['frames'][0]['writes'],*[j for j in schedule['fields'][0]['jobs'] if j['plane']==name]]:
            data[w['slot']*size:(w['slot']+1)*size]=chr_data[name][w['tile']*size:(w['tile']+1)*size]
        (cache/f'{name}.chr').write_bytes(data)
        (cache/f'0-{name}.map').write_bytes((residency/f'00-{name}.map').read_bytes())
    (cache/'layout.json').write_text(json.dumps(dict(low_chr_vram_base=49152)))
    kwargs={}
    if hybrid:
        if not plan.get('offset_map_aliases_bg2') or not plan.get('static_obj_subdivision'):
            raise ValueError('HYBRID_PRODUCTION_LAYOUT_UNPROVEN')
        kwargs=dict(high_tile_offset=64,obj_obsel=0,obj_chr=(residency/'obj.chr').read_bytes(),
            oam=(residency/'oam.bin').read_bytes(),obj_rom_bank=5,obj_rom_address=0xb000)
    component,_,resources=compile_rom(reports[0],assets[0],73 if sparse_palette else (74 if audio_service else 76),cache,offset_alias='low' if hybrid else True,**kwargs)
    fields=schedule['fields']+[dict(field=schedule['fields'][-1]['field']+1,jobs=[],mandatory=[])]
    fields[0]=dict(field=0,jobs=[],mandatory=[])
    # Pack all per-field programs and their immutable bytes into fast ROM.
    programs=[];blocks=[];cursor=53*32768;frame=0;descriptor_state={}
    for row in fields:
        while frame+1<len(assets) and schedule['source_frame_start_fields'][frame+1]<=row['field']:frame+=1
        items=[]
        for job in row['jobs']:
            raw=chr_data[job['plane']];size=job['bytes']
            items.append((job['address'],raw[job['tile']*size:(job['tile']+1)*size]))
        for transfer in row['mandatory']:
            name='high' if transfer['address']<0xf800 else 'low';base=0xf000 if name=='high' else 0xf800
            raw=(residency/f'{frame:02d}-{name}.map').read_bytes();start=transfer['address']-base
            items.append((transfer['address'],raw[start:start+transfer['bytes']]))
        packets=[]
        for address,data in sorted(items):
            if packets and packets[-1][0]+len(packets[-1][1])==address:packets[-1][1].extend(data)
            else:packets.append([address,bytearray(data)])
        reserve=256+40*len(packets);data_size=sum(len(p[1]) for p in packets)
        if cursor%32768+reserve+data_size>32768:cursor=(cursor//32768+1)*32768
        if cursor+reserve+data_size>64*32768:raise ValueError('PRODUCTION_SEQUENCE_FASTROM_CAPACITY')
        start=cursor;payload=start+reserve;code=bytearray();config=None;bank_state=None;source_end=None
        def longword(address,value):code.extend(bytes([0xa9,value&255,value>>8,0x8f,address&255,(address>>8)&255,address>>16]))
        def descriptor(address,value):
            # The compiled programs execute sequentially under one exclusive
            # descriptor owner. No IRQ/NMI consumer changes these fields.
            if descriptor_state.get(address)!=value:
                longword(address,value);descriptor_state[address]=value
        def word(address,value):code.extend(bytes([0xa9,value&255,value>>8,0x8d,address&255,address>>8]))
        # The post-NMI hook initializes Row and RowLimit from TargetBase.
        # Writing them again here only spends the transfer window.
        descriptor(0x7ff844,frame*(512 if sparse_palette else 256))
        if sparse_palette:
            events=[r for r in reports[frame]['trace'] if r['scanline'] and r['updates']]
            descriptor(0x7ff864,frame*512+len(events)*2)
            descriptor(0x7ff886,events[0]['scanline'] if events else 224)
        descriptor(0x7ff84e,0x8000+frame*palette_bytes);descriptor(0x7ff850,0xae)
        offset=frame*8192
        descriptor(0x7ff848,offset&65535);descriptor(0x7ff84a,0xe0+(offset>>16));descriptor(0x7ff84c,reports[frame]['span']*2)
        descriptor(0x7ff870,frame);longword(0x7ff872,row['field'])
        for address,data in packets:
            source=0x8000+payload%32768;bank=0x80+payload//32768
            word(0x2116,address//2)
            if config!=0x1801:word(0x4370,0x1801);config=0x1801
            if bank_state!=bank:word(0x4374,bank);bank_state=bank
            if not hybrid or source_end!=(bank,source):word(0x4372,source)
            word(0x4375,len(data));word(0x420b,128);source_end=(bank,(source+len(data))&65535)
            blocks.append((payload,bytes(data)));payload+=len(data)
        code.append(0x6b)
        if len(code)>reserve:raise ValueError('PRODUCTION_SEQUENCE_CODE_RESERVATION')
        blocks.append((start,bytes(code)));programs.append(dict(field=row['field'],frame=frame,start=start,packets=len(packets),bytes=data_size))
        cursor=payload
    asm='''
.bank 39
.org $D000
SourceCanvasFrameTick:
.a16
.i16
    lda.l SourceRaster_Frames
    cmp #%d
    bcc SourceCanvasFrameInRange
    lda #%d
SourceCanvasFrameInRange:
.a16
.i16
    asl a
    asl a
    tax
    lda.l $A7C400,x
    sta.l $7FF866
    inx
    inx
    lda.l $A7C400,x
    sep #$20
.a8
    pha
    rep #$20
.a16
    lda.l $7FF866
    pha
    rtl
.org $C400
SourceCanvasProgramTable:
'''%(len(programs),len(programs)-1)
    for program in programs:
        pos=program['start'];asm+='    .dw $%04X,$%04X\n'%(0x8000+pos%32768-1,0x80+pos//32768)
    raw,gates=production_build(component,reports[0],folder,original,sy,True,True,prefix,0xa7d000,asm,audio_service,source_clock,palette_count=palette_count,compact_canvas_nmi=compact_canvas_nmi,sparse_targets=sparse_palette,serialize_audio_raster=serialize_audio_raster)
    rom=bytearray(raw)
    for first,size in [(46*32768,32768),(53*32768,11*32768),(64*32768,5*65536)]:
        if rom[first:first+size]!=bytes(size):raise ValueError('PRODUCTION_SEQUENCE_ROM_RESERVATION_OCCUPIED')
    for address,data in blocks:rom[address:address+len(data)]=data
    traces=[]
    for i,(r,initial) in enumerate(zip(reports,initials)):
        state=list(initial);target=bytearray();payload=bytearray();trace=[]
        events=[row['scanline'] for row in r['trace'] if row['scanline'] and row['updates']]
        for row,burst in zip(r['trace'],r['contiguous_bursts']):
            if row['scanline']:
                for e in row['updates']:state[e['slot']-1]=e['color']
            if sparse_palette and row['scanline'] not in events:continue
            slot=burst['start_slot'];target.append(slot+3)
            if sparse_palette:
                idx=events.index(row['scanline']);target.append(events[idx+1] if idx+1<len(events) else 224)
            data=struct.pack('<'+'H'*r['span'],*[c or 0 for c in state[slot-1:slot-1+r['span']]])
            payload.extend(data);trace.extend([f'2121:{slot+3:02x}',*[f'2122:{b:02x}' for b in data]])
        stride=512 if sparse_palette else 256
        rom[52*32768+i*stride:52*32768+i*stride+len(target)]=target
        rom[46*32768+i*palette_bytes:46*32768+(i+1)*palette_bytes]=struct.pack('<'+'H'*palette_count,*[c or 0 for c in initial[prefix:prefix+palette_count]])
        pos=64*32768+i*8192;rom[pos:pos+len(payload)]=payload
        traces.append(trace)
    resources.update(programs=programs,source_frame_start_fields=schedule['source_frame_start_fields'],production_canvas_nmi=True,
                     palette_prefix_colors=prefix,no_live_world_claim=True,production_audio_service=audio_service,
                     native_source_clock_service=source_clock)
    resources.update(hybrid_static_obj=hybrid,per_field_palette_restore_bytes=palette_bytes)
    resources.update(fixed_palette_suffix_words=suffix)
    resources['compact_canvas_nmi']=compact_canvas_nmi
    resources['sparse_palette_events']=sparse_palette
    resources['serialized_audio_raster']=serialize_audio_raster
    resources['palette_first_use_folds']=folds
    if hybrid:resources.update(static_obj_oam_sha256=plan['oam_sha256'],static_obj_subdivision=plan['static_obj_subdivision'])
    return bytes(rom),gates,resources,traces,assets


def verify(rom,gates,resources,traces,assets,source_rom,sy,folder):
    path=folder/'proof.sfc';path.write_bytes(rom)
    for p in [source_rom.with_suffix('.msu'),*source_rom.parent.glob('bor-*.pcm')]:
        destination=folder/('proof'+p.name[3:])
        if not destination.exists():os.link(p,destination)
    lua=folder/'observer.lua'
    expected_runs=[]
    for p in assets:
        values=np.fromfile(p/'expected.rgb555',dtype='<u2')
        boundaries=np.r_[0,np.flatnonzero(values[1:]!=values[:-1])+1,len(values)]
        expected_runs.append(''.join(f'{b-a:04x}{int(values[a]):04x}' for a,b in zip(boundaries[:-1],boundaries[1:])))
    pixel_observer='''
local expected={}
for i,runs in ipairs(EXPECTEDRUNS) do
 local pieces={}
 for count,color in runs:gmatch('(%x%x%x%x)(%x%x%x%x)') do
  local c=tonumber(color,16)
  pieces[#pieces+1]=string.rep(string.char(c&255,c>>8),tonumber(count,16))
 end
 expected[i]=table.concat(pieces)
end
local displayed=nil;local displayfield=nil;local pixelcount=0
emu.addEventCallback(function()
 if displayed~=nil and pixelcount<75 then
  local screen=emu.getScreenBuffer();local source=expected[displayed+1];local bad=0
  -- Mesen's raw non-overscan SNES buffer has seven top and eight bottom
  -- border rows. Compare all 256x224 native visible pixels, without resizing.
  for i=1,256*224 do
   local c=screen[i+256*7] or 0;local actual=((c>>19)&31)|(((c>>11)&31)<<5)|(((c>>3)&31)<<10)
   local lo,hi=source:byte(i*2-1,i*2)
   if hi==nil or actual~=lo+256*hi then bad=bad+1 end
  end
  if #screen~=256*239 or #source~=256*224*2 then bad=bad+1 end
  emu.log('PRODSEQPIXEL|'..displayfield..'|'..displayed..'|'..(256*224)..'|'..bad)
  pixelcount=pixelcount+1;displayed=nil
 end
end,emu.eventType.startFrame)
'''.replace('EXPECTEDRUNS','{'+','.join(json.dumps(p) for p in expected_runs)+'}')
    lua.write_text('''local active=false;local restoring=false;local data={};local n=0;local frame=0;local completed=0
local firstmin=9999;local firstmax=0;local lastmin=9999;local lastmax=0
local function word(a) return emu.read(a,emu.memType.snesMemory)+256*emu.read(a+1,emu.memType.snesMemory) end
'''+pixel_observer+'''
emu.addMemoryCallback(function(a,v) if v==15 and word(0x7ff840)==0xb4b0 and not active then active=true end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) restoring=v==1 end,emu.callbackType.write,0x7ff85c,0x7ff85c,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and not restoring and completed<75 then
  if n==0 then frame=word(0x7ff870) end
  n=n+1;data[#data+1]=string.format('%04x:%02x',a,v)
  if a==0x2122 then
   local size=word(0x7ff84c)+1;local index=n%size
   if index==2 or index==0 then
    local s=emu.getState();local h=(s.masterClock+4*math.floor(s['ppu.frameCount']/2))%1364
    if index==2 then firstmin=math.min(firstmin,h);firstmax=math.max(firstmax,h) end
    if index==0 then local ending=h<88 and h+1364 or h;lastmin=math.min(lastmin,ending);lastmax=math.max(lastmax,ending) end
   end
  end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 if active and (n>0 or SPARSEEVENTS) and completed<75 then
  frame=word(0x7ff870)
  displayfield=word(0x7ff872);displayed=frame
  emu.log('PRODSEQTRACE|'..displayfield..'|'..frame..'|'..table.concat(data,','));data={};n=0;completed=completed+1
  emu.log('PRODSEQWINDOW|'..displayfield..'|'..firstmin..'|'..firstmax..'|'..lastmin..'|'..lastmax)
  firstmin=9999;firstmax=0;lastmin=9999;lastmax=0
 end
end,emu.eventType.endFrame)
'''.replace('SPARSEEVENTS','true' if resources.get('sparse_palette_events') else 'false')+gate_observer(gates,'word(0x7ff84c)',sy['Vm_Fetch']-32768,sy['nmi_handler']-32768,
                 sy['nmi_handler']+7-32768 if resources.get('compact_canvas_nmi') else None)+'''
local vramunsafe=0;local boundaries=0
emu.addMemoryCallback(function(a,v)
 if active then
  local s=emu.getState()
  if s['ppu.scanline']<225 then vramunsafe=vramunsafe+1 end
 end
end,emu.callbackType.write,0x2118,0x2119,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if active and boundaries<75 then
  local s=emu.getState()
  emu.log('PRODSEQRETURN|'..word(0x7ff872)..'|'..s['ppu.scanline']..'|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..vramunsafe)
  boundaries=boundaries+1
 end
end,emu.callbackType.exec,'''+str(sy['nmi_handler']+7-32768 if resources.get('compact_canvas_nmi') else 39*32768+(gates['SourceRasterAfterReturn']&65535)-32768)+''','''+str(sy['nmi_handler']+7-32768 if resources.get('compact_canvas_nmi') else 39*32768+(gates['SourceRasterAfterReturn']&65535)-32768)+''',emu.cpuType.snes,emu.memType.snesPrgRom)
''')
    if resources.get('hybrid_static_obj'):
        with lua.open('a') as script:
            script.write('''
local hybridshown=false;local hybridcount=0;local hybridoam={}
emu.addMemoryCallback(function(a,v)
 if not hybridshown then hybridcount=hybridcount+1;hybridoam[(hybridcount-1)%544+1]=string.format('%02x',v) end
end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if v==15 and word(0x7ff840)==0xb4b0 and not hybridshown then
  hybridshown=true;local ordered={}
  for i=1,544 do ordered[i]=hybridoam[(hybridcount+i-1)%544+1] or '' end
  emu.log('PRODHYBRIDOAM|'..table.concat(ordered,''))
 end
end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() if hybridshown then emu.log('PRODHYBRIDFLAGS|'..emu.read(0x213e,emu.memType.snesMemory)) end end,emu.eventType.endFrame)
''')
    if resources.get('production_audio_service'):
        with lua.open('a') as script:
            script.write('''
local audioevents=0
local function audio(a,v)
 if active and audioevents<160 then
  audioevents=audioevents+1;local s=emu.getState()
  emu.log('PRODSEQAUDIO|'..a..'|'..s.masterClock..'|'..word(0x7ff884)..'|'..word(ACCEPTED)..'|'..emu.read(STATE,emu.memType.snesMemory)..'|'..word(CHUNKS)..'|'..emu.read(EXHAUSTED,emu.memType.snesMemory))
 end
end
emu.addMemoryCallback(audio,emu.callbackType.exec,START,START,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(audio,emu.callbackType.exec,DONE,DONE,emu.cpuType.snes,emu.memType.snesPrgRom)
'''.replace('ACCEPTED',str(sy['TadPrivate_stream_chunks_accepted']))
               .replace('STATE',str(sy['AudioStream_State'])).replace('CHUNKS',str(sy['AudioStream_SourceChunks']))
               .replace('EXHAUSTED',str(sy['TadPrivate_stream_producer_done']))
               .replace('START',str(39*32768+(gates['SourceCanvasAudioStart']&65535)-32768))
               .replace('DONE',str(39*32768+(gates['SourceCanvasAudioDone']&65535)-32768)))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    expected=[np.fromfile(p/'expected.rgb555',dtype='<u2').reshape(224,256) for p in assets]
    pixels=[];steps=[];snapshots=[]
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        reporter=Reporter('M4-PRODUCTION-SEQUENCE',kind='GATE')
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('PRODUCTION_SEQUENCE_PLAYING_REQUIRED')
        run_frames_exact(m,12);m.write_u8(0x7ff860,0xa5)
        advanced=0;owned=False
        for attempt in range(1500):
            progress=m.tool('run_frames',{'count':1});steps.append(progress)
            if progress['framesAdvanced'] not in (0,1):raise ValueError('PRODUCTION_SEQUENCE_OVERRUN')
            if not progress['framesAdvanced']:continue
            if startup.u16(m,0x7ff856):raise ValueError('PRODUCTION_SEQUENCE_HANDOFF_FAULT')
            if startup.u16(m,0x7ff840)!=0xb4b0:continue
            owned=True;advanced+=1
            shot=m.tool('take_screenshot',{'format':'path'});rgb=np.asarray(Image.open(shot['path']).convert('RGB'),dtype=np.int32)
            actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
            matches=[i for i,e in enumerate(expected) if actual.shape==e.shape and np.array_equal(actual,e)]
            descriptor=m.read_memory('SnesMemory',0x7ff840,64);field=int.from_bytes(descriptor[50:52],'little')
            pixels.append(dict(sample=advanced,program_field=field,matches=matches));snapshots.append(descriptor.hex())
            if matches:shutil.copyfile(shot['path'],folder/f'frame-{matches[0]:02d}.png')
            if field>=72 and advanced>=77:break
        (folder/'cpu-state.json').write_text(json.dumps(m.get_cpu_state(),indent=2))
        (folder/'audio-closeout.bin').write_bytes(m.read_memory('SnesMemory',sy['TadPrivate_stream_frame'],64))
        if resources.get('native_source_clock_service'):
            (folder/'clock-closeout.bin').write_bytes(m.read_memory('SnesMemory',sy['SourceClock4086_Ready'],80))
    lines=(folder/'mesen.log').read_text().splitlines();observed=[]
    for line in lines:
        if 'PRODSEQTRACE|' in line:
            field,frame,data=line.split('PRODSEQTRACE|',1)[1].split('|',2);frame=int(frame)
            values=data.split(',') if data else []
            observed.append(dict(field=int(field),frame=frame,verified=values==traces[frame],writes=len(values)))
    contexts=[line.split('GATECONTEXT|',1)[1] for line in lines if 'GATECONTEXT|' in line]
    counts=[int(v) for v in contexts[-1].split(',')] if contexts else [0,0,-1,0,-1,0]
    starts=resources['source_frame_start_fields']
    def frame_at(field):return max(i for i,t in enumerate(starts) if t<=max(0,field))
    last=resources['programs'][-1]['field']
    cadence=all(r['field']==min(i,last) and r['frame']==frame_at(r['field']) for i,r in enumerate(observed))
    display_pixels=[];returns=[]
    for line in lines:
        if 'PRODSEQPIXEL|' in line:
            f,i,size,bad=map(int,line.split('PRODSEQPIXEL|',1)[1].split('|'))
            display_pixels.append(dict(field=f,frame=i,pixels=size,mismatches=bad))
        if 'PRODSEQRETURN|' in line:
            f,scanline,clock,ppu_field,unsafe=map(int,line.split('PRODSEQRETURN|',1)[1].split('|'))
            h=(clock+4*(ppu_field//2))%1364
            remaining=(262-scanline)*1364-h
            returns.append(dict(field=f,scanline=scanline,h_clock=h,master_clock=clock,ppu_field=ppu_field,
                                clocks_before_next_field=remaining,unsafe_vram_writes=unsafe))
    pixel_cadence=(len(display_pixels)>=73 and all(p['field']==min(i,last) and p['frame']==frame_at(p['field']) and p['pixels']==224*256 and p['mismatches']==0 for i,p in enumerate(display_pixels)))
    # Native RTI fetch + two 6-clock idle cycles + four 8-clock stack reads
    # costs 50 clocks. Reserve 64 to cover the four-clock short-field offset.
    transfer_window=(len(returns)>=73 and all(225<=r['scanline']<=261 and r['clocks_before_next_field']>=64 and r['unsafe_vram_writes']==0 for r in returns))
    result=dict(resources=resources,rom_sha256=hashlib.sha256(rom).hexdigest(),pixels=pixels,observer=observed,
                snapshots=snapshots,context_faults=counts[2],unsafe_palette_samples=counts[4],peak_nmi_master_clocks=counts[5],
                source_clock_observer_verified=cadence,no_color_reduction=True,
                completed_display_pixels=display_pixels,pixel_cadence_verified=pixel_cadence,
                nmi_returns=returns,transfer_window_verified=transfer_window,
                scope='Continuous fixed-context compiled sequence through a banked canvas NMI after real production cold boot. No live compositor, world or TAD frame-service admission.')
    result['pass']=owned and len(observed)>=73 and cadence and pixel_cadence and transfer_window and all(r['verified'] for r in observed) and counts[2]==0 and counts[4]==0 and counts[5]<=50464 and set(range(len(assets)))<=set(i for p in pixels for i in p['matches'])
    if resources.get('hybrid_static_obj'):
        oam=[v.split('PRODHYBRIDOAM|',1)[1] for v in lines if 'PRODHYBRIDOAM|' in v]
        flags=[int(v.split('PRODHYBRIDFLAGS|',1)[1]) for v in lines if 'PRODHYBRIDFLAGS|' in v]
        result.update(oam_observer_verified=len(oam)==1 and hashlib.sha256(bytes.fromhex(oam[0])).hexdigest()==resources['static_obj_oam_sha256'],
            obj_overflow_samples=sum(bool(v&0xc0) for v in flags),obj_status_samples=len(flags))
        result['pass']=result['pass'] and result['oam_observer_verified'] and bool(flags) and not result['obj_overflow_samples']
    if resources.get('production_audio_service'):
        audio=[list(map(int,line.split('PRODSEQAUDIO|',1)[1].split('|'))) for line in lines if 'PRODSEQAUDIO|' in line]
        spans=[audio[i+1][1]-audio[i][1] for i in range(0,len(audio)-1,2)]
        closeout=(folder/'audio-closeout.bin').read_bytes()
        def final_word(name):return struct.unpack_from('<H',closeout,sy[name]-sy['TadPrivate_stream_frame'])[0]
        accepted=final_word('TadPrivate_stream_chunks_accepted')
        # A field can spend multiple display epochs inside the real TAD
        # loading pump. Service frequency is measured, never invented.
        admitted=len(audio)>=2 and accepted>0
        result.update(audio_service_events=audio,audio_service_peak_master_clocks=max(spans,default=0),
                      audio_stream_chunks_accepted=accepted,
                      audio_stream_transport_active_verified=admitted,
                      audio_stream_transport_complete_verified=audio[-1][3]==audio[-1][5] and audio[-1][6]==1 if audio else False,
                      scope='Continuous fixed-context sequence with the real production TAD frame and late pumps, plus a native original-BOR source-2 stream request. No moving compositor, MOTU audio binding or live world admission.')
        result['pass']=result['pass'] and admitted
    if resources.get('native_source_clock_service'):
        closeout=(folder/'clock-closeout.bin').read_bytes()
        def clock_word(name):return struct.unpack_from('<H',closeout,sy[name]-sy['SourceClock4086_Ready'])[0]
        ready=clock_word('SourceClock4086_Ready');fault=clock_word('SourceClock4086_Fault')
        time=clock_word('SourceClock4086_TimeLo')+65536*clock_word('SourceClock4086_TimeHi')
        result.update(native_clock_ready=ready,native_clock_fault=fault,native_clock_ticks_committed=time,
                      clock_scope='Owned 4086 physical-field clock with empty logical ticks; no live entity update or MOTU gameplay.')
        result['pass']=result['pass'] and ready==0xb4c5 and fault==0 and time>0
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('resources','pixels','observer','snapshots','completed_display_pixels','nmi_returns','audio_service_events')}))
    if not result['pass']:raise SystemExit(1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('sequence','residency','deadlines','rom','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--audio-service',action='store_true')
    p.add_argument('--source-clock',action='store_true')
    p.add_argument('--compact-canvas-nmi',action='store_true')
    p.add_argument('--sparse-palette',action='store_true')
    p.add_argument('--serialize-audio-raster',action='store_true')
    p.add_argument('--fold-first-use',action='store_true')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path(__file__).resolve().parents[2]/'src/main.sym')
    rom,gates,resources,traces,assets=build(a.sequence,a.residency,a.deadlines,a.rom.read_bytes(),sy,folder,a.audio_service,a.source_clock,a.compact_canvas_nmi,a.sparse_palette,a.serialize_audio_raster,a.fold_first_use)
    (folder/'proof.sfc').write_bytes(rom)
    (folder/'compiled.json').write_text(json.dumps(dict(resources=resources,gates=gates,assets=[str(p) for p in assets],traces=traces),indent=2))
    print('PRODUCTION_SEQUENCE_COMPILED')
    verify(rom,gates,resources,traces,assets,a.rom.resolve(),sy,folder)


if __name__=='__main__':main()
