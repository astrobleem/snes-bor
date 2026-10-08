"""Measure grouped source-colour SCREEN reads with in-place RGB555 output.

Compiler-owned groups preserve every opaque pixel. Two mutable underlays are
inputs to this shader proof; live geometry gathering and palette publication
remain unbound. Every destination byte offset is checked before a LUT read.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from compiler import Source
from source_screen_lookup import derive,matrix
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
from m4_sound_mix_sa1_native import Code
import m4_screen_sa1_native as channel
import source_scene_bg


def capture_plane(source,stage,scene,destinations):
 """Capture the exact opaque underlay and screen addresses before SCREEN."""
 original=source_scene_bg.overlay;captures=[]
 def overlay(canvas,indices,rgb,x,y,alpha=0,transparent=True):
  if alpha==1:
   h,w=canvas.shape[:2];ih,iw=indices.shape;x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
   if x1>x0 and y1>y0:
    mask=indices[y0-y:y1-y,x0-x:x1-x]!=0;yy,xx=np.nonzero(mask)
    plane=np.array([destinations[tuple(map(int,c))]*2 for c in canvas.reshape(-1,3)],dtype='<u2')
    captures.append((plane.tobytes(),((yy+y0)*w+xx+x0)*2))
  return original(canvas,indices,rgb,x,y,alpha,transparent)
 with patch.object(source_scene_bg,'overlay',overlay):source_scene_bg.compose_rgb8(source,stage,scene)
 if len(captures)!=1:raise ValueError('GATHER_SINGLE_SCREEN_LAYER_REQUIRED')
 return captures[0]


def build(descriptors,inputs,table,columns,busy,iram_dma_cache=False,planes=None,dirty_split=None,output_bytes=None,native_dirty=False):
 base,_,_=channel.build(np.zeros((3,2),dtype=np.uint16),busy,iram=True);rom=bytearray(base)+bytearray([255])*(2097152-len(base))
 if len(descriptors)%8 or len(inputs)>32768 or len(table)>1048576:raise ValueError('GROUPED_SCREEN_ROM_CAPACITY')
 if dirty_split is not None and (not output_bytes or output_bytes>0x1800 or native_dirty and len(inputs)>0x2c00):raise ValueError('DIRTY_SCREEN_ISOLATED_BUFFER_CAPACITY')
 rom[0x10000:0x10000+len(descriptors)]=descriptors;rom[0x20000:0x20000+len(inputs)]=inputs;rom[0x100000:0x100000+len(table)]=table
 if planes:
  if iram_dma_cache or any(len(p)>131072 for p in planes):raise ValueError('GATHER_PLANE_CAPACITY')
  for i,plane in enumerate(planes):rom[0x40000+i*0x20000:0x40000+i*0x20000+len(plane)]=plane
 c=Code(0x3100 if iram_dma_cache else 0x3200);c.emit('78 18 fb c2 30 a2 ff 37 9a a9 00 30 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 '+('00'if iram_dma_cache else'42')+' 48 ab c2 20 a9 00 00 85 0c 8f f4 3f 41')
 c.label('entry');c.emit('a9 00 00 85 04 85 0e a0 00 00')
 if native_dirty:c.emit('64 12')
 if dirty_split is not None:
  c.emit('a5 0c');c.branch(0xd0,'dirty_entry');c.word(0xa9,dirty_split);c.emit('85 08');c.branch(0x80,'entry_ready');c.label('dirty_entry');c.word(0xa9,dirty_split);c.emit('85 04');c.word(0xa9,len(descriptors));c.emit('85 08');c.label('entry_ready')
 c.label('group');c.emit('a6 04 bf 00 00 c1');patches=[]
 for name in('pixel0','pixel1','pixel2','tail_pixel'):
  c.emit('8d 00 00'if iram_dma_cache else'8f 00 00 00');patches.append((len(c.data)-(2 if iram_dma_cache else 3),name,1))
 c.emit('e2 20 bf 02 00 c1')
 for name in('pixel0','pixel1','pixel2','tail_pixel'):
  c.emit('8d 00 00'if iram_dma_cache else'8f 00 00 00');patches.append((len(c.data)-(2 if iram_dma_cache else 3),name,3))
 c.emit('c2 20 bf 04 00 c1 85 00 bf 06 00 c1 85 02')
 if planes:
  c.emit('e2 20 bf 03 00 c1 18 65 0c')
  for name in('pixel0','pixel1','pixel2','tail_pixel'):
   c.emit('8f 00 00 00');patches.append((len(c.data)-3,name+'_gather',3))
  c.emit('c2 20')
 if iram_dma_cache:
  c.emit('a5 00 0a 18 65 00 18 65 02 0a 85 06 8d 38 22 a5 0e 8d 32 22 e2 20 a9 02 8d 34 22 a9 81 8d 30 22 a9 20 8d 0b 22 c2 20 a9 00 34 8d 35 22 a0 00 00')
 c.emit('a5 00')
 if dirty_split is not None:c.branch(0xd0,'triples');c.jump('tail')
 else:c.branch(0xf0,'tail')
 def pixel(name):
  c.emit('be 00 '+('18'if dirty_split is not None else'34'if iram_dma_cache else'00'))
  if planes:c.label(name+'_gather');c.emit('bf 00 00 c4 aa')
  if native_dirty:
   c.emit('86 10 be 02 18');c.word(0xe0,output_bytes);c.branch(0x90,name+'_cache_range');c.jump('fault');c.label(name+'_cache_range');c.emit('8a 89 01 00');c.branch(0xf0,name+'_cache_even');c.jump('fault');c.label(name+'_cache_even');c.emit('bd 00 44 c5 10');c.branch(0xf0,name+'_skip');c.emit('a6 10')
  c.word(0xe0,columns*2);c.branch(0x90,name+'_range_ok');c.jump('fault');c.label(name+'_range_ok');c.emit('8a 89 01 00');c.branch(0xf0,name+'_even');c.jump('fault');c.label(name+'_even')
  if native_dirty:c.emit('48 be 02 18 68 9d 00 44 a6 10')
  if native_dirty:c.emit('e6 12')
  c.label(name);c.emit('bf 00 00 00')
  if dirty_split is not None:
   c.emit('48 be 02 18')
   if not native_dirty:
    c.word(0xe0,output_bytes);c.branch(0x90,name+'_output_range');c.jump('fault');c.label(name+'_output_range');c.emit('8a 89 01 00');c.branch(0xf0,name+'_output_even');c.jump('fault');c.label(name+'_output_even')
   c.emit('68 9d 00 00');c.label(name+'_skip');c.emit('c8 c8 c8 c8')
  else:c.emit('99 00 '+('34'if iram_dma_cache else'00')+' c8 c8')
 c.label('triples')
 for i in range(3):pixel('pixel'+str(i))
 c.emit('c6 00')
 if dirty_split is not None:c.branch(0xf0,'tail');c.jump('triples')
 else:c.branch(0xd0,'triples')
 c.label('tail');c.emit('a5 02');c.branch(0xf0,'next_group');pixel('tail_pixel');c.emit('c6 02');c.branch(0xd0,'tail')
 c.label('next_group')
 if iram_dma_cache:
  c.emit('e2 20 a9 86 8d 30 22 a9 20 8d 0b 22 c2 20 a5 06 8d 38 22 a9 00 34 8d 32 22 a5 0e 8d 35 22 e2 20 a9 00 8d 34 22 a9 02 8d 37 22 c2 20 a5 0e 18 65 06 85 0e')
 c.emit('a5 04 18 69 08 00 85 04')
 if dirty_split is not None:c.emit('c5 08')
 else:c.word(0xc9,len(descriptors))
 c.branch(0xf0,'done');c.jump('group')
 c.label('done')
 if native_dirty:c.emit('a5 12 8f f6 3f 41')
 c.emit('a5 0c');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 0c');
 if planes:c.emit('e6 0c')
 c.jump('entry')
 c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');c.label('fault');c.emit('a9 ae b4 8f f0 3f 41');c.jump('stop')
 worker=bytearray(c.finish())
 for at,name,delta in patches:
  size=2 if iram_dma_cache else 3;worker[at:at+size]=(c.base+c.labels[name]+delta).to_bytes(size,'little')
 if len(worker)>0x500:raise ValueError('GROUPED_SCREEN_IRAM_CAPACITY')
 rom[0x9000:0x9000+len(worker)]=worker
 main=bytearray(rom[0x8000:0x8400]);main=main[:main.index(bytes([255])*32)];needle=bytes.fromhex('bf 00 90 01 9f 00 32 00 e8 e0');at=main.index(needle)+len(needle);main[at:at+2]=struct.pack('<H',len(worker))
 if iram_dma_cache:
  if c.base+len(worker)>0x3400:raise ValueError('GROUPED_SCREEN_DMA_CACHE_CODE_OVERLAP')
  at=main.index(needle)+5;main[at:at+2]=struct.pack('<H',c.base);at=main.index(bytes.fromhex('a9 32 8d 04 22'));main[at+1]=c.base>>8
 extra=bytes.fromhex('c2 20 a2 00 00 bf 00 00 c2 9f 00 '+('18'if dirty_split is not None else'00')+' 42 e8 e8 e0')+struct.pack('<H',len(inputs))+bytes.fromhex('d0 f1 e2 20')
 if native_dirty:extra+=bytes.fromhex('c2 20 a9 ff ff a2 00 00 9f 00 44 42 e8 e8 e0')+struct.pack('<H',output_bytes)+bytes.fromhex('d0 f5 e2 20')
 if main[-3]!=0x4c:raise ValueError('GROUPED_SCREEN_HOST_LAYOUT')
 main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(extra));at=main.index(bytes.fromhex('bf 00 90 01'))-3;main[at:at]=extra;rom[0x8000:0x8400]=main+bytes([255])*(1024-len(main));rom[0x7fd7]=11
 return bytes(rom),{n:c.base+c.labels[n]for n in('entry','done','fault')},bytes(worker)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--move-actor-index',type=int,default=1);p.add_argument('--move-x',type=int,default=-30);p.add_argument('--busy-host',action='store_true');p.add_argument('--invalid-destination',choices=('range','odd'));p.add_argument('--iram-dma-cache',action='store_true');p.add_argument('--gather-underlay',action='store_true');p.add_argument('--dirty-underlay',action='store_true');p.add_argument('--native-dirty-scan',action='store_true');p.add_argument('--invalid-output',choices=('range','odd'));a=p.parse_args();a.dirty_underlay|=a.native_dirty_scan;a.gather_underlay|=a.dirty_underlay;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);catalog=derive(source);scene=json.loads(a.scene.read_text());samples=[];metadata=[]
 for shift in(0,a.move_x):
  pose=json.loads(json.dumps(scene));pose['actors'][a.move_actor_index]['position'][0]+=shift;pairs,layers=channel.capture(source,a.stage,pose);samples.append(pairs.reshape(-1,3,2));metadata.append(layers)
 if not np.array_equal(samples[0][:,:,0],samples[1][:,:,0]):raise ValueError('SOURCE_FRAME_EPOCH_CHANGED')
 effect=next(e for e in catalog['effects']if all(tuple(map(int,c))in e['colors']for s in samples for c in s[:,:,0]));si={tuple(c):i for i,c in enumerate(effect['colors'])};di={tuple(c):i for i,c in enumerate(catalog['destinations'])};words=matrix(effect['colors'],catalog['destinations'])
 gathered=[capture_plane(source,a.stage,m['scene'],di)for m in metadata]if a.gather_underlay else None
 if gathered and (a.iram_dma_cache or a.invalid_destination):raise ValueError('GATHER_MODE_COMBINATION_UNSUPPORTED')
 if gathered and not np.array_equal(gathered[0][1],gathered[1][1]):raise ValueError('GATHER_EFFECT_GEOMETRY_EPOCH_CHANGED')
 source_ids=[si[tuple(map(int,c))]for c in samples[0][:,:,0]];groups={}
 for i,index in enumerate(source_ids):groups.setdefault((index,int(gathered[0][1][i])>>16)if gathered else(index,0),[]).append(i)
 descriptors=bytearray();order=[]
 for (index,plane_bank),indices in sorted(groups.items()):
  chunks=[indices[i:i+256]for i in range(0,len(indices),256)]if a.iram_dma_cache else[indices]
  for chunk in chunks:descriptors.extend(struct.pack('<IHH',(0xd00000+index*effect['columns']*2)|((0xc4+plane_bank)<<24 if gathered else 0),len(chunk)//3,len(chunk)%3));order.extend(chunk)
 input_data=[];expected=[]
 for sample in samples:
  destinations=[di[tuple(map(int,c))]for c in sample[:,:,1]];input_data.append(struct.pack('<'+'H'*len(order),*(destinations[i]*2 for i in order)));expected.append(struct.pack('<'+'H'*len(order),*(int(words[source_ids[i],destinations[i]])for i in order)))
 if a.invalid_destination:
  invalid=effect['columns']*2 if a.invalid_destination=='range'else 1;input_data[0]=struct.pack('<H',invalid)+input_data[0][2:]
 if gathered:input_data=[struct.pack('<'+'H'*len(order),*(int(g[1][i])&65535 for i in order))for g in gathered]
 dirty_split=None;dirty_pixels=None
 if a.dirty_underlay:
  changed=np.any(samples[0][:,:,1]!=samples[1][:,:,1],axis=1);dirty_pixels=int(changed.sum())
  if not dirty_pixels:raise ValueError('DIRTY_PROOF_REQUIRES_CHANGED_UNDERLAY')
  descriptors=bytearray();input_data=[];expected=[]
  for phase,sample in enumerate(samples):
   records=bytearray()
   for (index,plane_bank),indices in sorted(groups.items()):
    selected=[i for i in indices if a.native_dirty_scan or phase==0 or changed[i]]
    if not selected:continue
    descriptors.extend(struct.pack('<IHH',(0xd00000+index*effect['columns']*2)|((0xc4+plane_bank)<<24),len(selected)//3,len(selected)%3))
    for i in selected:records.extend(struct.pack('<HH',int(gathered[phase][1][i])&65535,i*2))
   if phase==0:dirty_split=len(descriptors)
   input_data.append(bytes(records));destinations=[di[tuple(map(int,c))]for c in sample[:,:,1]];expected.append(struct.pack('<'+'H'*len(source_ids),*(int(words[source_ids[i],destinations[i]])for i in range(len(source_ids)))))
 if a.invalid_output:
  if not a.dirty_underlay:raise ValueError('OUTPUT_GUARD_REQUIRES_SCATTER_MODE')
  bad=len(expected[0]) if a.invalid_output=='range' else 1;input_data[0]=input_data[0][:2]+struct.pack('<H',bad)+input_data[0][4:]
 rom,entries,worker=build(descriptors,input_data[0],words.tobytes(),effect['columns'],a.busy_host,a.iram_dma_cache,[g[0]for g in gathered]if gathered else None,dirty_split,len(expected[0]),a.native_dirty_scan);path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua';lua.write_text('\n'.join(f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('GROUPSCREEN|{n}|'..s.masterClock)end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)"for n,address in entries.items()))
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 actual=[];shader_counts=[]
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for phase,target in enumerate((b'\xa1\xb4',b'\xab\xb4')):
   for _ in range(60):
    run_frames_exact(m,1);marker=m.read_memory('SnesMemory',0x413ff0,2)
    if marker in(target,b'\xae\xb4'):break
   if marker==b'\xae\xb4':break
   if marker!=target:raise ValueError('GROUPED_SCREEN_COMPLETION')
   actual.append(m.read_memory('SnesMemory',0x420000,len(expected[phase])))
   if a.native_dirty_scan:shader_counts.append(int.from_bytes(m.read_memory('SnesMemory',0x413ff6,2),'little'))
   if phase==0:m.write_memory('SnesMemory',0x421800 if a.dirty_underlay else 0x420000,input_data[1].hex());m.write_u16(0x413ff4,1)
 events=[l.split('GROUPSCREEN|',1)[1].split('|')for l in(out/'mesen.log').read_text().splitlines()if'GROUPSCREEN|'in l];timings=[int(events[i+1][1])-int(events[i][1])for i in(0,2)]if[e[0]for e in events]==['entry','done','entry','done']else None
 ok=marker==b'\xae\xb4'and[e[0]for e in events]==['entry','fault']if a.invalid_destination or a.invalid_output else actual==expected and timings is not None
 if a.native_dirty_scan and not a.invalid_output:ok=ok and shader_counts==[len(source_ids),dirty_pixels]
 report=dict(schema='BYOR_GROUPED_SOURCE_SCREEN_NATIVE_V1',status='PASS'if ok else'FAIL',opaque_pixels=len(order),source_color_groups=len(groups),group_descriptors_bytes=len(descriptors),mutable_pixel_buffer_bytes=len(input_data[0]),worker_IRAM_bytes=len(worker),RGB555_byte_mismatches=[sum(x!=y for x,y in zip(o,e))for o,e in zip(actual,expected)],master_clocks=timings,milliseconds=[v/21477.27 for v in timings]if timings else None,rom_sha256=hashlib.sha256(rom).hexdigest(),table_sha256=hashlib.sha256(words.tobytes()).hexdigest(),in_place_destination_to_RGB555=True,destination_range_and_alignment_checked=True,invalid_destination=a.invalid_destination,busy_host_BWRAM_reads=a.busy_host,source_poses=[m['scene']for m in metadata],geometry_gathering_native=False,online_palette_allocation_native=False,CHR_publication_native=False,joint_audio_proven=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
 report.update(IRAM_DMA_cache=a.iram_dma_cache,cache_IRAM_bytes=512 if a.iram_dma_cache else 0,normal_DMA_setup_and_transfer_in_timing=a.iram_dma_cache,group_packets=len(descriptors)//8)
 report.update(native_underlay_plane_gather=a.gather_underlay,underlay_plane_storage='precomposed source RGB8 identity planes in ROM'if gathered else None,underlay_plane_bytes=[len(g[0])for g in gathered]if gathered else [],live_underlay_composition_native=False,screen_addresses_source_derived=bool(gathered),underlay_plane_sha256=[hashlib.sha256(g[0]).hexdigest()for g in gathered]if gathered else [])
 report.update(source_color_groups=len(set(source_ids)),source_color_plane_bank_groups=len(groups),scope='Native source-address gather and exact SCREEN shader over two precomposed opaque underlays. No native layer composition, palette allocation, CHR publication, production lease or gameplay admission.'if gathered else 'Exact SCREEN shader over two offline-gathered underlays. No live renderer or gameplay admission.')
 report.update(incremental_underlay_update=a.dirty_underlay,changed_underlay_pixels=dirty_pixels,retained_output_pixels=len(source_ids)-dirty_pixels if dirty_pixels is not None else None,dirty_selection_native=a.native_dirty_scan,retained_underlay_identity_bytes=len(expected[0]) if a.native_dirty_scan else 0,output_range_and_alignment_checked=a.dirty_underlay)
 report.update(invalid_output=a.invalid_output,observed_native_shader_pixel_counts=shader_counts,full_output_bytes=len(expected[0]),pixel_records_bytes=[len(i)for i in input_data],source_layers=metadata[0]['layers'],in_place_destination_to_RGB555=not a.dirty_underlay)
 report.update(proof_kind='EXPECTED_GUARD_REJECTION'if a.invalid_destination or a.invalid_output else'EXACT_PIXEL_SHADER',retained_output_pixels=len(source_ids)-dirty_pixels if dirty_pixels is not None and len(actual)==2 else None)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ('source_poses','source_layers')}))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
