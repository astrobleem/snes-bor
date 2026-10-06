"""Measure exact RGB8 SCREEN arithmetic on native SA-1, before live binding."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from _harness import McpSession, MESEN_EXE, _free_tcp_port
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
import source_scene_bg


def capture(source,stage,scene):
    original=source_scene_bg.overlay;pairs=[]
    def overlay(canvas,indices,rgb,x,y,alpha=0,transparent=True):
        h,w=canvas.shape[:2];ih,iw=indices.shape
        x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
        if alpha==1 and x1>x0 and y1>y0:
            mask=indices[y0-y:y1-y,x0-x:x1-x]!=0
            s=rgb[y0-y:y1-y,x0-x:x1-x][mask];d=canvas[y0:y1,x0:x1][mask].copy()
            pairs.extend(zip(s.reshape(-1),d.reshape(-1)))
        return original(canvas,indices,rgb,x,y,alpha,transparent)
    with patch.object(source_scene_bg,'overlay',overlay):canvas,metadata=source_scene_bg.compose_rgb8(source,stage,scene)
    return np.array(pairs,dtype=np.uint16),metadata


def build(pairs,busy_host,method='mul',iram=False):
    if pairs.ndim!=2 or pairs.shape[1]!=2 or pairs.size>32768:raise ValueError('SCREEN_FIXTURE_INPUT_LIMIT')
    if np.any(pairs>255):raise ValueError('SCREEN_RGB8_INPUT_RANGE')
    raw=(pairs[:,0]|(pairs[:,1]<<8)).astype('<u2').tobytes()
    rom=bytearray([255])*262144;rom[0x10000:0x10000+len(raw)]=raw
    if method.startswith('lut'):
        index=np.arange(65536,dtype=np.uint32)
        lut=(255-((255-(index&255))*(255-(index>>8))//255)).astype(np.uint8).tobytes()
        rom[0x18000:0x28000]=lut
        if method=='lut-linear':
            rom[0x10000:0x20000]=lut
            rom[0x20000:0x20000+len(raw)]=raw
    main=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):main.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    for address,value in [(0x4200,0),(0x420c,0),(0x2100,128),(0x2229,255),(0x222a,255),(0x2226,128),(0x2227,128),(0x2228,0),(0x2224,0)]:store(address,value)
    main.extend(bytes.fromhex('a9 00 8f f0 3f 41 8f f1 3f 41'))
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x800:0x804]=bytes.fromhex('5c 00 90 01')
    worker=bytearray.fromhex('78 18 fb c2 30 a2 ff 37 9a a9 00 30 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 00 8d 50 22 c2 20')
    base=0x3200 if iram else 0x9000
    if method=='lut':
        worker.extend(bytes.fromhex('a9 00 80 85 00 e2 20 a9 02 85 02 a9 42 48 ab c2 20'))
    elif method=='lut-linear':
        # SA-1 linear ROM C1:0000..FFFF holds the complete byte LUT. DBR04
        # supplies packed source/destination words via LDX absolute,Y while
        # accumulator width remains eight bits. Output has its own long DP
        # pointer and retains a two-byte stride for the bounded witness.
        worker.extend(bytes.fromhex('a9 00 00 85 00 e2 20 a9 42 85 02 a9 04 48 ab'))
    entry=base+len(worker);worker.extend(bytes.fromhex('a0 00 00' if method.startswith('lut') else 'a2 00 00'));loop=len(worker)
    # Unsigned 0..255 inputs; the SA-1's signed multiplier sees positive
    # operands. floor(n/255)=(n+1+(n>>8))>>8 for n<=255*255.
    if method=='lut-linear':
        if len(pairs)%3:raise ValueError('SCREEN_RGB8_CHANNEL_TRIPLE')
        worker.extend(bytes.fromhex('be 00 80 bf 00 00 c1 97 00 c8 c8')*3)
        worker.append(0xc0)
    elif method=='lut':
        # Three channels per loop retain RGB8 and avoid repeated loop control.
        if len(pairs)%3:raise ValueError('SCREEN_RGB8_CHANNEL_TRIPLE')
        worker.extend(bytes.fromhex('b7 00 aa 10 0a 29 ff 7f aa bf 00 80 04 80 04 bf 00 80 03 29 ff 00 99 00 00 c8 c8')*3)
        worker.append(0xc0)
    else:worker.extend(bytes.fromhex('bf 00 80 02 85 00 29 ff 00 49 ff 00 8d 51 22 a5 00 eb 29 ff 00 49 ff 00 8d 53 22 ea ea ea ad 06 23 85 02 eb 29 ff 00 1a 18 65 02 eb 29 ff 00 49 ff 00 9f 00 00 42 e8 e8 e0'))
    worker.extend(struct.pack('<H',len(raw)));worker.extend(bytes([0xd0,(loop-len(worker)-2)&255]))
    done=base+len(worker)
    if method=='lut-linear':worker.extend(bytes.fromhex('c2 20'))
    worker.extend(bytes.fromhex('a9 ab b4 8f f0 3f 41'))
    stop=base+len(worker);worker.extend(bytes([0x4c,stop&255,stop>>8]));rom[0x9000:0x9000+len(worker)]=worker
    if iram:
        main.extend(bytes.fromhex('a2 00 00'));copy=len(main)
        main.extend(bytes.fromhex('bf 00 90 01 9f 00 32 00 e8 e0'));main.extend(struct.pack('<H',len(worker)))
        main.extend(bytes([0xd0,(copy-len(main)-2)&255]))
    for address,value in [(0x2203,0),(0x2204,0x32 if iram else 0x88),(0x2200,32),(0x2200,0)]:store(address,value)
    wait=0x8000+len(main)
    if busy_host:main.extend(bytes.fromhex('af f0 3f 41'))
    else:main.append(0xcb)
    main.extend(bytes([0x4c,wait&255,wait>>8]));rom[0x8000:0x8000+len(main)]=main
    rom[0x7fc0:0x7fd5]=b'M4 SCREEN SA1'.ljust(21);rom[0x7fd5:0x7fdc]=bytes([0x23,0x35,8,8,1,0x33,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom),entry,done


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source');p.add_argument('--stage')
    p.add_argument('--scene',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--busy-host',action='store_true')
    p.add_argument('--exhaustive-block',type=int,choices=range(5),help='One of five bounded blocks covering every 8-bit channel pair')
    p.add_argument('--method',choices=('mul','lut','lut-linear'),default='mul');p.add_argument('--iram',action='store_true');a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    if a.exhaustive_block is None:
        if not a.source or not a.stage or not a.scene:raise ValueError('SOURCE_SCENE_REQUIRED')
        pairs,metadata=capture(Source(a.source),a.stage,json.loads(a.scene.read_text()))
    else:
        indices=np.arange(a.exhaustive_block*16383,min(65536,(a.exhaustive_block+1)*16383),dtype=np.uint16)
        if len(indices)%3:indices=np.concatenate([indices,np.repeat(indices[-1],3-len(indices)%3)])
        pairs=np.column_stack([indices&255,indices>>8]);metadata=dict(layers=[])
    rom,entry,done=build(pairs,a.busy_host,a.method,a.iram);path=folder/'proof.sfc';path.write_bytes(rom);lua=folder/'observer.lua'
    lua.write_text('''local function sample(a,v) local s=emu.getState();emu.log('SCREENJOB|'..table.concat({a,s['masterClock'],s['ppu.frameCount'],s['ppu.scanline']},',')) end
emu.addMemoryCallback(sample,emu.callbackType.exec,ENTRY,ENTRY,emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(sample,emu.callbackType.exec,DONE,DONE,emu.cpuType.sa1,emu.memType.snesPrgRom)
'''.replace('ENTRY',str(entry)).replace('DONE',str(done)).replace('emu.memType.snesPrgRom','emu.memType.sa1Memory' if a.iram else 'emu.memType.snesPrgRom'))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        for _ in range(30):
            m.tool('run_frames',{'count':1});marker=m.read_memory('SnesMemory',0x413ff0,2)
            marker=bytes.fromhex(marker['hex']) if isinstance(marker,dict) else bytes(marker)
            if marker==b'\xab\xb4':break
        raw=m.read_memory('SnesMemory',0x420000,len(pairs)*2)
    raw=bytes.fromhex(raw['hex']) if isinstance(raw,dict) else bytes(raw)
    actual=np.frombuffer(raw,dtype='<u2')
    if a.method=='lut-linear':actual=actual&255  # high stride bytes are not written by this byte executor
    expected=255-((255-pairs[:,0])*(255-pairs[:,1])//255)
    events=[[int(v) for v in line.split('SCREENJOB|',1)[1].split(',')] for line in (folder/'mesen.log').read_text().splitlines() if 'SCREENJOB|' in line]
    duration=events[1][1]-events[0][1] if len(events)==2 else None
    result=dict(rom_sha256=hashlib.sha256(rom).hexdigest(),source_layers=metadata['layers'],opaque_pixels=len(pairs)//3 if a.exhaustive_block is None else None,
                exhaustive_block=a.exhaustive_block,
                channel_pairs=len(pairs),exact_rgb8_channels=bool(np.array_equal(actual,expected)),
                mismatched_channels=int(np.count_nonzero(actual!=expected)),job_events=events,job_master_clocks=duration,
                busy_host_bwram_reads=a.busy_host,method=a.method,iram_code=a.iram,no_color_reduction=True,
                scope='Exact SA-1 channel arithmetic on source-derived pixels. No palette allocation, geometry loops, live renderer, production contention or gameplay admission.')
    result['pass']=marker==b'\xab\xb4' and result['exact_rgb8_channels'] and duration is not None
    (folder/'actual.rgb8words').write_bytes(raw);(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
