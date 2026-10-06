"""Native exact SCREEN matrix reads with mutable BW-RAM destination indices.

Two source-derived underlays exercise the same effect geometry. They are an
input witness, not a gameplay or runtime underlay generation certification.
"""
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
from _harness import McpSession,MESEN_EXE,_free_tcp_port
import m4_screen_sa1_native as channel
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_screen_lookup import derive,matrix


def build(records,table,busy,iram=False,rom_rows=False,unroll=1,destination_count=1375):
    if len(records)%6 or not records or len(records)>49152 or len(table)>1048576:
        raise ValueError('SCREEN_INDEXED_FIXTURE_CAPACITY')
    if len(records)%(6*unroll): raise ValueError('SCREEN_INDEXED_UNROLL_ALIGNMENT')
    base,_,_=channel.build(np.zeros((3,2),dtype=np.uint16),busy)
    rom=bytearray(base)+bytearray([255])*(2097152-len(base))
    rom[0x10000:0x10000+len(records)]=records;rom[0x100000:0x100000+len(table)]=table
    # Populate mutable input descriptors before releasing the worker.
    main=bytearray(rom[0x8000:0x8400]);end=main.find(bytes([255])*32);main=main[:end]
    insert=main.index(bytes.fromhex('a9 00 8d 03 22'))
    copy=bytearray.fromhex('c2 20 a2 00 00');loop=len(copy)
    copy.extend(bytes.fromhex('bf 00 00 c1 9f 00 40 41 e8 e8 e0')+struct.pack('<H',len(records)))
    copy.extend(bytes([0xd0,(loop-len(copy)-2)&255])+bytes.fromhex('e2 20'))
    worker=bytearray.fromhex('78 18 fb c2 30 a2 ff 37 9a a9 00 30 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 00 8d 50 22 c2 20')
    worker_base=0x3200 if iram else 0x9000
    worker.extend(bytes.fromhex('a9 00 00 8f f2 3f 41'))
    entry=worker_base+len(worker);worker.extend(bytes.fromhex('a2 00 00'));loop=len(worker)
    # Row base is source-derived. Destination ID may change in BW-RAM.
    # Long indirect,Y reaches the exact RGB555 matrix without RGB8 arithmetic.
    def long(op,address): return bytes([op])+address.to_bytes(3,'little')
    failures=[]
    for i in range(unroll):
        at=i*6;row_base=0xc10000 if rom_rows else 0x414000
        worker.extend(long(0xbf,row_base+at)+bytes.fromhex('85 00'))
        worker.extend(long(0xbf,row_base+at+2)+bytes.fromhex('85 02'))
        worker.extend(long(0xbf,0x414004+at)+bytes([0xc9])+struct.pack('<H',destination_count)+bytes.fromhex('90 03 4c'))
        failures.append(len(worker));worker.extend(b'\0\0')
        worker.extend(bytes.fromhex('0a a8 b7 00')+long(0x9f,0x420000+at))
    worker.extend(bytes.fromhex('8a 18 69')+struct.pack('<H',6*unroll)+bytes.fromhex('aa e0'))
    worker.extend(struct.pack('<H',len(records)))
    distance=loop-len(worker)-2
    if not -128<=distance<=127:raise ValueError('SCREEN_INDEXED_LOOP_BRANCH')
    worker.extend(bytes([0xd0,distance&255]))
    done=worker_base+len(worker);worker.extend(bytes.fromhex('a9 ab b4 8f f0 3f 41'))
    stop=worker_base+len(worker);worker.extend(bytes([0x4c,stop&255,stop>>8]))
    bad=worker_base+len(worker)
    for pos in failures:worker[pos:pos+2]=struct.pack('<H',bad)
    worker.extend(bytes.fromhex('a9 01 00 8f f2 3f 41 a9 ae b4 8f f0 3f 41'))
    stop=worker_base+len(worker);worker.extend(bytes([0x4c,stop&255,stop>>8]))
    if iram:
        at=main.index(bytes.fromhex('a9 88 8d 04 22'));main[at+1]=0x32
        iram_copy=bytearray.fromhex('a2 00 00');loop=len(iram_copy)
        iram_copy.extend(bytes.fromhex('bf 00 90 01 9f 00 32 00 e8 e0')+struct.pack('<H',len(worker)))
        iram_copy.extend(bytes([0xd0,(loop-len(iram_copy)-2)&255]));copy.extend(iram_copy)
    target=struct.unpack_from('<H',main,len(main)-2)[0]+len(copy)
    main[-2:]=struct.pack('<H',target);main[insert:insert]=copy
    rom[0x8000:0x8000+len(main)]=main
    rom[0x9000:0x9000+len(worker)]=worker;rom[0x7fd7]=11
    return bytes(rom),entry,done,bad


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--busy-host',action='store_true');p.add_argument('--iram',action='store_true')
    p.add_argument('--rom-rows',action='store_true');p.add_argument('--unroll',type=int,choices=(1,2,3),default=1)
    p.add_argument('--invalid-destination',action='store_true')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);catalog=derive(source);scene=json.loads(a.scene.read_text())
    samples=[];metadata=[]
    for shift in (0,-30):
        pose=json.loads(json.dumps(scene))
        for actor in pose['actors']:
            if actor['model'].lower()=='he_manb':actor['position'][0]+=shift
        pairs,layers=channel.capture(source,a.stage,pose)
        samples.append(pairs.reshape(-1,3,2));metadata.append(layers)
    effect=next(e for e in catalog['effects'] if all(tuple(map(int,c)) in e['colors'] for s in samples for c in s[:,:,0]))
    src_ids={tuple(c):i for i,c in enumerate(effect['colors'])};dst_ids={tuple(c):i for i,c in enumerate(catalog['destinations'])}
    words=matrix(effect['colors'],catalog['destinations'])
    lut=np.zeros((effect['rows'],effect['columns']),dtype='<u2');lut[:,:words.shape[1]]=words
    records=bytearray();expected=[];changed=0
    for sample in samples:
        for s,d in zip(sample[:,:,0],sample[:,:,1]):
            si=src_ids[tuple(map(int,s))];di=dst_ids[tuple(map(int,d))]
            row=0xd00000+si*effect['columns']*2
            records.extend(struct.pack('<IH',row,di));expected.append(int(words[si,di]))
    if len(samples[0])==len(samples[1]):changed=int(np.count_nonzero(np.any(samples[0][:,:,1]!=samples[1][:,:,1],axis=1)))
    if a.invalid_destination:struct.pack_into('<H',records,4,catalog['destination_rgb8_colors'])
    rom,entry,done,bad=build(records,lut.tobytes(),a.busy_host,a.iram,a.rom_rows,a.unroll,catalog['destination_rgb8_colors']);path=folder/'proof.sfc';path.write_bytes(rom)
    lua=folder/'observer.lua';lua.write_text('''local function sample(a,v) local s=emu.getState();emu.log('INDEXJOB|'..a..','..s['masterClock']) end
emu.addMemoryCallback(sample,emu.callbackType.exec,ENTRY,ENTRY,emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(sample,emu.callbackType.exec,DONE,DONE,emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(sample,emu.callbackType.exec,FAULT,FAULT,emu.cpuType.sa1,emu.memType.snesPrgRom)
'''.replace('ENTRY',str(entry)).replace('DONE',str(done)).replace('FAULT',str(bad)).replace('emu.memType.snesPrgRom','emu.memType.sa1Memory' if a.iram else 'emu.memType.snesPrgRom'))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        marker=b''
        for n in range(1500):
            m.tool('run_frames',{'count':1});v=m.read_memory('SnesMemory',0x413ff0,2)
            marker=bytes.fromhex(v['hex']) if isinstance(v,dict) else bytes(v)
            if marker in (b'\xab\xb4',b'\xae\xb4'):break
        v=m.read_memory('SnesMemory',0x413ff2,2);fault=bytes.fromhex(v['hex']) if isinstance(v,dict) else bytes(v)
        raw=m.read_memory('SnesMemory',0x420000,len(records))
    raw=bytes.fromhex(raw['hex']) if isinstance(raw,dict) else bytes(raw)
    observed=list(struct.unpack_from('<H',raw,n)[0] for n in range(0,len(records),6))
    events=[[int(v) for v in line.split('INDEXJOB|')[1].split(',')] for line in (folder/'mesen.log').read_text().splitlines() if 'INDEXJOB|' in line]
    duration=events[1][1]-events[0][1] if len(events)==2 else None
    r=dict(status='PASS' if marker==b'\xab\xb4' and observed==expected and duration is not None else 'FAIL',
        rom_sha256=hashlib.sha256(rom).hexdigest(),table_sha256=hashlib.sha256(lut.tobytes()).hexdigest(),
        table_bytes=lut.nbytes,source_color_rows=effect['rows'],destination_color_count=catalog['destination_rgb8_colors'],
        input_pixels=len(expected),pose_pixels=[len(s) for s in samples],changed_underlay_pixels=changed,
        rgb555_mismatches=sum(x!=y for x,y in zip(observed,expected)),job_master_clocks=duration,
        clocks_per_pixel=duration/len(expected) if duration else None,events=events,busy_host_bwram_reads=a.busy_host,
        iram_code=a.iram,immutable_source_rows_in_rom=a.rom_rows,loop_unroll=a.unroll,
        destination_range_checked=True,native_fault=int.from_bytes(fault,'little'),invalid_destination_probe=a.invalid_destination,
        no_color_reduction=True,source_poses=[m['scene'] for m in metadata],
        scope='Native exact table reads with mutable destination IDs; source-derived changed underlay inputs. No live compositor, online palette allocation, BG update or gameplay proof.')
    if not changed:r['status']='FAIL'
    if a.invalid_destination:
        r.update(status='PASS' if marker==b'\xae\xb4' and fault==b'\x01\0' else 'FAIL',
                 rgb555_mismatches=None,clocks_per_pixel=None,
                 scope='Explicit invalid destination ID rejection before a matrix read; no rendering claim')
    elif fault!=b'\0\0':r['status']='FAIL'
    (folder/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
