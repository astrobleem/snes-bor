"""Native source-span producer feeding exact SCREEN without host pixel inputs."""
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
import source_scene_bg
from source_hybrid_scene import capture as hybrid_capture
from source_bg_feasibility import rgb555
from source_screen_lookup import derive,matrix
from m4_screen_grouped_native import capture_plane
from m4_underlay_spans_sa1_native import compile_inputs,build as underlay_build
from m4_sound_mix_sa1_native import Code
import m4_screen_sa1_native as source_capture
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact


def validate_opaque_identities(data,columns):
 if len(data)%2 or not 0<columns<=32768:raise ValueError('COMPILER_OPAQUE_RGB8_IDENTITY_CONTRACT')
 ids=np.frombuffer(data,dtype='<u2')
 if np.any(ids&1)or np.any(ids>=columns*2):raise ValueError('COMPILER_OPAQUE_RGB8_IDENTITY_CONTRACT')


def correction_shader(baseline_bytes,return_entry,adaptive_threshold=None,whole_window=False,large_map=False):
 """Correct preblended stage pixels using the producer's visible-span cache."""
 c=Code(0x3500);c.emit('c2 30 a9 00 30 5b e2 20 a9 42 48 ab c2 20')
 c.label('entry');c.emit('64 04 64 12 a9 00 00 8f fa 3f 41 8f fc 3f 41')
 if adaptive_threshold is not None:
  c.emit('a5 14');c.word(0xc9,adaptive_threshold);c.branch(0x90,'corrections');c.emit('a9 01 00 8f fc 3f 41 5c 00 36 00');c.label('corrections')
 if not whole_window:
  c.emit('e2 20 a9 84 8f 30 22 00 a9 20 8f 0b 22 00 a9 c8 8f 34 22 00 c2 20 a9 00 00 8f 32 22 00 a9 00 70 8f 35 22 00');c.word(0xa9,baseline_bytes);c.emit('8f 38 22 00 e2 20 a9 02 8f 37 22 00 c2 20')
 c.emit('a5 18');c.branch(0xd0,'span');c.jump('done')
 c.label('span');c.emit('a6 04 bd 00 60 85 00 bd 02 60 85 02')
 c.label('pixel');c.emit('a5 00 0a 18 65 00 aa');map_patches=[]
 if large_map:
  c.emit('e2 20 a9 c6 69 00')
  for name in('map_slot','map_pointer','map_bank'):
   c.emit('8f 00 00 00');map_patches.append((len(c.data)-3,name))
  c.emit('c2 20')
 c.label('map_slot');c.emit('bf 00 00 c6 c9 ff ff');c.branch(0xf0,'skip');c.emit('85 0a');c.label('map_pointer');c.emit('bf 02 00 c6 8f 00 00 00');lo_at=len(c.data)-3;c.emit('e2 20');c.label('map_bank');c.emit('bf 04 00 c6 8f 00 00 00');bank_at=len(c.data)-3;c.emit('c2 20 a6 00 bd 00 00 aa');c.label('lookup');c.emit('bf 00 00 00 a6 0a 9d 00 70 e6 12')
 c.label('skip');c.emit('e6 00 e6 00 c6 02 c6 02');c.branch(0xd0,'pixel');c.emit('a5 04 18 69 04 00 85 04 c5 18');c.branch(0xd0,'span')
 c.label('done');c.emit('a5 12 8f fa 3f 41 a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop')
 worker=bytearray(c.finish());worker[lo_at:lo_at+3]=(c.base+c.labels['lookup']+1).to_bytes(3,'little');worker[bank_at:bank_at+3]=(c.base+c.labels['lookup']+3).to_bytes(3,'little')
 for at,name in map_patches:worker[at:at+3]=(c.base+c.labels[name]+3).to_bytes(3,'little')
 if c.base+len(worker)>0x3700:raise ValueError('CORRECTION_SHADER_IRAM_CAPACITY')
 return bytes(worker),{n:c.base+c.labels[n]for n in('entry','done')}


def shader(descriptors,columns,return_entry,typed_underlay=False,worker_base=0x3500,whole_window=False):
 c=Code(worker_base);c.emit('c2 30 a9 00 30 5b e2 20 a9 c3 48 ab c2 20 a9 00 70 85 20 e2 20 a9 42 85 22 c2 20')
 c.label('entry');c.emit('64 04 a0 00 00');c.label('group');c.emit('a6 04 bf 00 00 c1');patches=[]
 for name in('pixel0','pixel1','pixel2','tail_pixel'):
  c.emit('8f 00 00 00');patches.append((len(c.data)-3,name,1))
 c.emit('e2 20 bf 02 00 c1')
 for name in('pixel0','pixel1','pixel2','tail_pixel'):
  c.emit('8f 00 00 00');patches.append((len(c.data)-3,name,3))
 c.emit('c2 20 bf 04 00 c1 85 00 bf 06 00 c1 85 02 a5 00');c.branch(0xf0,'tail')
 def pixel(name):
  c.emit('be 00 10 bf 00 00 42 aa')
  if not typed_underlay:
   c.word(0xe0,columns*2);c.branch(0x90,name+'_range');c.jump('fault');c.label(name+'_range');c.emit('8a 89 01 00');c.branch(0xf0,name+'_even');c.jump('fault');c.label(name+'_even')
  c.label(name);c.emit('bf 00 00 00')
  c.emit('be 00 10 9f 00 70 42 c8 c8'if whole_window else'97 20 c8 c8')
 c.label('triples')
 for i in range(3):pixel('pixel'+str(i))
 c.emit('c6 00');c.branch(0xd0,'triples');c.label('tail');c.emit('a5 02');c.branch(0xf0,'next');pixel('tail_pixel');c.emit('c6 02');c.branch(0xd0,'tail');c.label('next');c.emit('a5 04 18 69 08 00 85 04');c.word(0xc9,len(descriptors));c.branch(0xf0,'done');c.jump('group')
 c.label('done');c.emit('a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');c.label('fault');c.emit('a9 ae b4 8f f0 3f 41');c.jump('stop')
 worker=bytearray(c.finish())
 for at,name,delta in patches:worker[at:at+3]=(c.base+c.labels[name]+delta).to_bytes(3,'little')
 if c.base+len(worker)>0x3700:raise ValueError('JOINT_SCREEN_IRAM_CAPACITY')
 return bytes(worker),{n:c.base+c.labels[n]for n in('entry','done','fault')}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--move-actor-index',type=int,default=1);p.add_argument('--move-x',type=int,default=-30);p.add_argument('--retain-stage',action='store_true');p.add_argument('--typed-underlay',action='store_true');p.add_argument('--background-corrections',action='store_true');p.add_argument('--adaptive-shader',action='store_true');p.add_argument('--invalidate-context',choices=('low','high'));p.add_argument('--whole-tile-canvas',action='store_true');p.add_argument('--palette-indices',action='store_true');p.add_argument('--direct-palette-lookup',action='store_true');p.add_argument('--sparse-palette-indices',action='store_true');p.add_argument('--bitmap-palette-indices',action='store_true');p.add_argument('--iram-bitmap-indices',action='store_true');p.add_argument('--fused-screen-indices',action='store_true');p.add_argument('--invalidate-fused-palette',action='store_true');p.add_argument('--native-characters',action='store_true');p.add_argument('--iram-native-characters',action='store_true');p.add_argument('--native-bitmaps',action='store_true');p.add_argument('--type1-vram',action='store_true');p.add_argument('--ppu-scene',action='store_true');p.add_argument('--sparse-native-bitmaps',action='store_true');p.add_argument('--adaptive-native-bitmaps',action='store_true');p.add_argument('--direct-native-bitmaps',action='store_true');p.add_argument('--idle-direct-cpu',action='store_true');p.add_argument('--effect-tile-direct',action='store_true');p.add_argument('--fixed-underlay-actor',type=int);p.add_argument('--invalidate-fixed-underlay',action='store_true');p.add_argument('--invalidate-fixed-underlay-frame',action='store_true');a=p.parse_args();a.direct_native_bitmaps|=a.effect_tile_direct;a.direct_native_bitmaps|=a.idle_direct_cpu;a.native_bitmaps|=a.direct_native_bitmaps;a.sparse_native_bitmaps|=a.adaptive_native_bitmaps;a.native_bitmaps|=a.sparse_native_bitmaps;a.type1_vram|=a.ppu_scene;a.native_bitmaps|=a.type1_vram;a.iram_native_characters|=a.native_bitmaps;a.bitmap_palette_indices|=a.iram_bitmap_indices;a.sparse_palette_indices|=a.bitmap_palette_indices;a.direct_palette_lookup|=a.sparse_palette_indices;a.native_characters|=a.iram_native_characters;a.fused_screen_indices|=a.invalidate_fused_palette or a.native_characters;a.palette_indices|=a.direct_palette_lookup or a.fused_screen_indices;a.whole_tile_canvas|=a.palette_indices;a.background_corrections|=a.whole_tile_canvas;a.background_corrections|=a.adaptive_shader;a.typed_underlay|=a.background_corrections;a.retain_stage|=a.background_corrections;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 if a.fused_screen_indices and(a.adaptive_shader or a.direct_palette_lookup):raise ValueError('FUSED_PRESENTATION_USES_COMPILED_PERSISTENT_ACTOR_INDICES')
 if a.sparse_palette_indices and a.adaptive_shader:raise ValueError('SPARSE_INDEX_PIPELINE_REQUIRES_ACTOR_CORRECTIONS')
 source=Source(a.source);catalog=derive(source);scene=json.loads(a.scene.read_text());bg,span_desc,pixels,origins,actors,window=compile_inputs(source,a.stage,scene,catalog,a.whole_tile_canvas);wx,wy,w,h=window
 di={tuple(c):i for i,c in enumerate(catalog['destinations'])};pairs,metadata=source_capture.capture(source,a.stage,scene);samples=pairs.reshape(-1,3,2);effect=next(e for e in catalog['effects']if all(tuple(map(int,c))in e['colors']for c in samples[:,:,0]));si={tuple(c):i for i,c in enumerate(effect['colors'])};table=matrix(effect['colors'],catalog['destinations']);source_ids=[si[tuple(map(int,c))]for c in samples[:,:,0]]
 plane,addresses=capture_plane(source,a.stage,scene,di);vw=scene.get('viewport',[256,224])[0];relative=((addresses//2//vw-wy)*w+(addresses//2%vw-wx))*2
 if np.any(relative<0)or np.any(relative>=w*h*2):raise ValueError('JOINT_EFFECT_GEOMETRY_RANGE')
 groups={}
 for i,index in enumerate(source_ids):groups.setdefault(index,[]).append(i)
 if not groups or table.nbytes>1048576:raise ValueError('JOINT_SCREEN_NONEMPTY_ROM_DOMAIN')
 desc=bytearray();order=[]
 for index,indices in sorted(groups.items()):desc.extend(struct.pack('<IHH',0xd00000+index*effect['columns']*2,len(indices)//3,len(indices)%3));order.extend(indices)
 poses=[];coordinates=struct.pack('<'+'H'*len(order),*(int(relative[i])for i in order));expected=[];underlays=[]
 for shift in(0,a.move_x):
  pose=json.loads(json.dumps(scene));pose['actors'][a.move_actor_index]['position'][0]+=shift;poses.append(pose);values,_=source_capture.capture(source,a.stage,pose);s=values.reshape(-1,3,2)
  if not np.array_equal(s[:,:,0],samples[:,:,0]):raise ValueError('JOINT_SOURCE_EPOCH_CHANGED')
  destination=[di[tuple(map(int,c))]for c in s[:,:,1]];expected.append(struct.pack('<'+'H'*len(order),*(int(table[source_ids[i],destination[i]])for i in order)))
  full,_=capture_plane(source,a.stage,pose,di);underlays.append(np.frombuffer(full,dtype='<u2').reshape(scene.get('viewport',[256,224])[::-1])[wy:wy+h,wx:wx+w].tobytes())
  if a.whole_tile_canvas:
   canvas,full_metadata,draws=hybrid_capture(source,a.stage,pose);after=False
   for layer,draw in zip(full_metadata['layers'],draws):
    if layer['alpha']==1:after=True
    elif after and np.any(draw['mask'][wy:wy+h,wx:wx+w]):raise ValueError('WHOLE_TILE_POST_LAYER_COMPOSITION_REQUIRED')
   expected[-1]=rgb555(canvas)[wy:wy+h,wx:wx+w].astype('<u2').tobytes()
 moving=[i for i,v in enumerate(actors)if v[4]['kind'].split(':',1)[1].casefold()==scene['actors'][a.move_actor_index]['model'].casefold()]
 if len(moving)!=1:raise ValueError('JOINT_MOVING_ACTOR_DOMAIN')
 for data in(bg,pixels):validate_opaque_identities(data,effect['columns'])
 colour_canvas=None;colour_pixels=None
 if a.whole_tile_canvas:
  rgb=np.array(catalog['destinations'],dtype=np.uint16);rgb_words=((rgb[:,0]>>3)|((rgb[:,1]>>3)<<5)|((rgb[:,2]>>3)<<10)).astype('<u2');colour_words=rgb_words[np.frombuffer(bg,dtype='<u2')//2].copy()
  for i,offset in enumerate(relative):colour_words[int(offset)//2]=table[source_ids[i],int(np.frombuffer(bg,dtype='<u2')[int(offset)//2])//2]
  colour_canvas=colour_words.tobytes();colour_pixels=rgb_words[np.frombuffer(pixels,dtype='<u2')//2].tobytes()
 immutable_layers=[{k:v for k,v in layer.items()if k not in ('position','visible_source_pixels')}for layer in metadata['layers']]
 immutable_context=dict(layers=immutable_layers,window=list(window),stage=metadata['stage'],stage_sha256=metadata['stage_sha256'],camera=scene.get('camera',[0,0]),viewport=scene.get('viewport',[256,224]))
 context_digest=hashlib.sha256(bg+span_desc+pixels+coordinates+desc+table.tobytes()+json.dumps(immutable_context,sort_keys=True).encode()).digest();context_epoch=int.from_bytes(context_digest[:4],'little')
 if a.fixed_underlay_actor is not None:
  if not a.direct_native_bitmaps or a.fixed_underlay_actor!=0:raise ValueError('FIXED_UNDERLAY_LOWEST_ACTOR_DIRECT_PRESENTATION_REQUIRED')
  ordered=sorted(scene['actors'],key=lambda v:(v['position'][1],v['order']));selected=ordered[0]
  if selected['model'].casefold()!=actors[0][4]['kind'].split(':',1)[1].casefold():raise ValueError('FIXED_UNDERLAY_SOURCE_ACTOR_IDENTITY')
  retained={v['kind'].split(':',1)[1].casefold()for v in metadata['layers']if v['alpha']==1}
  fixed_scene=json.loads(json.dumps(scene));fixed_scene['actors']=[v for v in ordered if v is selected or v['model'].casefold()in retained]
  fixed_canvas,_,_=hybrid_capture(source,a.stage,fixed_scene);colour_canvas=rgb555(fixed_canvas)[wy:wy+h,wx:wx+w].astype('<u2').tobytes()
 index_data=None;colour_canvas_second=None;colour_pixels_second=None;original_bg=bg;fused_report=None;fused_tables=None;fused_maps=None
 if a.palette_indices:
  from m4_hybrid_window_indices import compile_contexts,prefill
  index_data=compile_contexts(source,a.stage,poses,window,out,a.direct_palette_lookup or a.fused_screen_indices,a.fused_screen_indices,not a.effect_tile_direct)
  if a.sparse_palette_indices or a.fused_screen_indices:
   colour_canvas,colour_canvas_second=prefill(index_data[0],index_data[1],colour_canvas,w,h)
 if a.fused_screen_indices:
  from m4_screen_fused_capacity import compile_tables
  from m4_screen_fused_indices import actor_indices,maps_for_groups
  fused_report,fused_tables,fused_groups=compile_tables(source,a.stage,index_data[4],window,True)
  if fused_report['status']!='TABLE_STORAGE_PROVEN'or len(fused_tables)>0x100000:raise ValueError('FUSED_NATIVE_FIXED_ROM_WINDOW_CAPACITY')
  colour_pixels,colour_pixels_second=actor_indices(colour_pixels,index_data[4]);fused_maps=maps_for_groups(fused_groups,addresses,window)
  new_di={tuple(c):i for i,c in enumerate(fused_report['underlay_vocabulary'])};remap=np.full(len(catalog['destinations']),65535,dtype=np.uint16)
  for color,index in new_di.items():remap[di[color]]=index
  def dense_opaque(data):
   values=remap[np.frombuffer(data,dtype='<u2')//2]
   if np.any(values==65535):raise ValueError('FUSED_CONTEXT_OPAQUE_DOMAIN_MISSING')
   return (values*2).astype('<u2').tobytes()
  bg=dense_opaque(bg);pixels=dense_opaque(pixels);underlays=[dense_opaque(v)for v in underlays]
  for data in(bg,pixels):validate_opaque_identities(data,len(new_di))
  immutable_context['underlay_RGB8_vocabulary']=fused_report['underlay_vocabulary']
  context_digest=hashlib.sha256(bg+span_desc+pixels+fused_tables+b''.join(fused_maps)+json.dumps(immutable_context,sort_keys=True).encode()+json.dumps([v['bg_schedule']for v in index_data[4]],sort_keys=True).encode()).digest();context_epoch=int.from_bytes(context_digest[:4],'little')
 if a.direct_native_bitmaps:
  from m4_direct_bitmap_native import run
  run(a,out,bg,span_desc,pixels,origins,actors,moving,window,index_data,[colour_canvas,colour_canvas_second],[colour_pixels,colour_pixels_second],fused_tables,fused_maps,context_epoch);return
 rom,entries,span_worker=underlay_build(bg,span_desc,pixels,origins,w,h,a.retain_stage,0x3500,context_epoch,colour_canvas,colour_pixels,colour_canvas_second,colour_pixels_second,a.native_characters);rom=bytearray(rom)+bytearray([255])*1048576;screen_worker,screen_entries=shader(desc,effect['columns'],entries['entry'],a.typed_underlay)
 if len(span_worker)>0x300:raise ValueError('UNDERLAY_SHADER_IRAM_CODE_OVERLAP')
 correction_map=None;baseline=None;expected_corrections=[]
 if a.background_corrections:
  correction_map=bytearray(struct.pack('<HI',65535,0)*(w*h));bg_ids=np.frombuffer(original_bg,dtype='<u2')
  baseline=struct.pack('<'+'H'*len(order),*(int(table[source_ids[i],int(bg_ids[int(relative[i])//2])//2])for i in order))
  for output,i in enumerate(order):struct.pack_into('<HI',correction_map,int(relative[i])*3,int(relative[i])if a.whole_tile_canvas else output*2,0xd00000+source_ids[i]*effect['columns']*2)
  if len(correction_map)>(131072 if a.whole_tile_canvas else 65536):raise ValueError('BACKGROUND_CORRECTION_MAP_CAPACITY')
  for phase in range(2):
   total=0
   for actor,(idx,_,x,y,_)in enumerate(actors):
    yy,xx=np.nonzero(idx);xx=xx+x+(a.move_x if phase and actor==moving[0] else 0);yy=yy+y;valid=(xx>=0)&(xx<w)&(yy>=0)&(yy<h)
    total+=sum(struct.unpack_from('<H',correction_map,(int(py)*w+int(px))*6)[0]!=65535 for py,px in zip(yy[valid],xx[valid]))
   expected_corrections.append(total)
  screen_worker,screen_entries=correction_shader(len(baseline),entries['entry'],max(1,len(order)//2)if a.adaptive_shader else None,a.whole_tile_canvas,len(correction_map)>65536);rom[0x60000:0x60000+len(correction_map)]=correction_map
  if not a.whole_tile_canvas:rom[0x80000:0x80000+len(baseline)]=baseline
 if a.fused_screen_indices:
  from m4_screen_fused_indices import shader as fused_shader
  screen_worker,screen_entries=fused_shader(entries['entry']);rom[0x60000:0x60000+len(fused_maps[0])]=fused_maps[0];rom[0x70000:0x70000+len(fused_maps[1])]=fused_maps[1]
 full_worker=None;full_entries=None
 if a.adaptive_shader:
  full_worker,full_entries=shader(desc,effect['columns'],entries['entry'],True,0x3600,a.whole_tile_canvas);rom[0x9d00:0x9d00+len(full_worker)]=full_worker
  if len(screen_worker)>256:raise ValueError('ADAPTIVE_CORRECTION_FULL_IRAM_OVERLAP')
 for at,data in((0x10000,desc),(0x31000,coordinates),(0x9c00,screen_worker),(0x100000,fused_tables if a.fused_screen_indices else table.tobytes())):rom[at:at+len(data)]=data
 index_worker=None;index_entries={};index_expected=[];index_decoders=[];palette_reports=[]
 if a.palette_indices and not a.fused_screen_indices:
  from m4_hybrid_window_indices import compile_contexts,kernel
  index_maps,index_pointers,index_expected,index_decoders,palette_reports=index_data
  if a.sparse_palette_indices:
   from m4_hybrid_window_indices import sparse_kernel
   if a.bitmap_palette_indices:
    from m4_hybrid_window_indices import bitmap_kernel
    sparse_worker,index_entries=bitmap_kernel(w,h,entries['entry'],a.iram_bitmap_indices)
   else:sparse_worker,index_entries=sparse_kernel(w,h,entries['entry'])
   index_worker=bytes.fromhex('bf 00 00 e0 6b')
  else:index_worker,index_entries=kernel(w,h,entries['entry'],a.direct_palette_lookup)
  rom.extend(bytes([255])*((8388608 if a.direct_palette_lookup else 4194304)-len(rom)))
  rom[0x200000:0x200000+len(index_maps)]=index_maps;rom[0x38000:0x38000+len(index_pointers)]=index_pointers;rom[0x9e00:0x9e00+len(index_worker)]=index_worker
  if a.direct_palette_lookup:
   words=np.arange(32768,dtype=np.uint16);rom[0x1f0000:0x1f8000]=(((words>>5)&1)|(((words>>10)&1)<<1)).astype(np.uint8).tobytes()
  if a.sparse_palette_indices:
   rom[0xa000:0xa000+len(sparse_worker)]=sparse_worker;rom[0x1f8000:0x1f8010]=struct.pack('<8H',*(1<<i for i in range(8)))
   if a.bitmap_palette_indices:
    masks=[(((1<<length)-1)<<start)&255 if length<=8-start else 0 for start in range(8)for length in range(16)]
    rom[0x1f8100:0x1f8200]=struct.pack('<128H',*masks);rom[0x1f8200:0x1f8210]=struct.pack('<8H',*((1<<i)-1 for i in range(8)))
  # Preserve the correction count before handing the completed canvas over.
  at=0x9c00+screen_entries['done']-0x3500+(6 if a.background_corrections else 0);rom[at:at+4]=bytes.fromhex('5c 40 30 00'if a.iram_bitmap_indices else('5c 00 a0 01'if a.sparse_palette_indices else'5c 00 37 00'))
  if full_entries:
   at=0x9d00+full_entries['done']-0x3600;rom[at:at+4]=bytes.fromhex('5c 40 30 00'if a.iram_bitmap_indices else('5c 00 a0 01'if a.sparse_palette_indices else'5c 00 37 00'))
 chr_worker=None;chr_entries={}
 if a.native_characters:
  from m4_window_characters import adaptive_bitmap_kernel,sparse_bitmap_kernel,sparse_bitmap_tables,expected_bitmap,bitmap_kernel,kernel as chr_kernel
  if a.native_bitmaps:chr_kernel=bitmap_kernel
  if a.sparse_native_bitmaps:
   chr_kernel=sparse_bitmap_kernel;baseline_bitmaps=expected_bitmap(colour_canvas,w,h)+expected_bitmap(colour_canvas_second,w,h)
   rom[0xd0000:0xd0000+len(baseline_bitmaps)]=baseline_bitmaps;offsets,masks=sparse_bitmap_tables(w,h);rom[0xe0000:0xe0000+len(offsets)]=offsets;rom[0xe8000:0xe8000+len(masks)]=masks
  if a.adaptive_native_bitmaps:chr_kernel=adaptive_bitmap_kernel
  chr_worker,chr_entries=chr_kernel(w,h,entries['entry'],a.iram_native_characters);rom[0xa000:0xa000+len(chr_worker)]=chr_worker
  at=0x9c00+screen_entries['done']-0x3500+6;rom[at:at+4]=bytes.fromhex('5c 00 b0 01'if a.iram_native_characters else'5c 00 a0 01')
  if a.iram_native_characters:
   from m4_window_characters import swaps
   enter_swap,leave_swap,restore_done=swaps(len(chr_worker),len(span_worker),entries['entry'],a.type1_vram);rom[0xb000:0xb000+len(enter_swap)]=enter_swap;rom[0xb100:0xb100+len(leave_swap)]=leave_swap
   chr_entries={'entry':0x01b000,'done':restore_done}
 main=bytearray(rom[0x8000:0x8400]);main=main[:main.index(bytes([255])*32)];extra=bytes.fromhex('e2 20 a2 00 00 bf 00 9c 01 9f 00 35 00 e8 e0')+struct.pack('<H',len(screen_worker))+bytes.fromhex('d0 f2')
 if a.adaptive_shader:extra+=bytes.fromhex('e2 20 a2 00 00 bf 00 9d 01 9f 00 36 00 e8 e0')+struct.pack('<H',len(full_worker))+bytes.fromhex('d0 f2')
 if index_worker:extra+=bytes.fromhex(('a9 00 8f e8 3f 41 8f e9 3f 41 'if a.direct_palette_lookup else'')+'e2 20 a2 00 00 bf 00 9e 01 9f 00 37 00 e8 e0')+struct.pack('<H',len(index_worker))+bytes.fromhex('d0 f2')
 if a.iram_bitmap_indices:extra+=bytes.fromhex('e2 20 a2 00 00 bf 00 a0 01 9f 40 30 00 e8 e0')+struct.pack('<H',len(sparse_worker))+bytes.fromhex('d0 f2')
 main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(extra));at=main.index(bytes.fromhex('bf 00 90 01'))-3;main[at:at]=extra
 if a.direct_palette_lookup:
  # MMC bank registers belong to S-CPU. SA-1 requests and waits for an ACK;
  # it cannot change $2222 itself. The native cost includes this service.
  main[-7:-7]=bytes.fromhex('af e8 3f 41 f0 0d 8d 22 22 8f e9 3f 41 a9 00 8f e8 3f 41')
 vram_entries={};vram_descriptors=[];ppu_high_start=max(4096,(((out/"palette-context-1/obj_chr.bin").stat().st_size+4095)//4096)*4096)if a.ppu_scene else 0
 if a.type1_vram:
  from m4_window_characters import type1_service
  service,vram_entries,vram_descriptors=type1_service(w,h,ppu_high_start if a.ppu_scene else 0,49152 if a.ppu_scene else 0x4000);rom[0xc000:0xc000+len(service)]=service
  main[-7:-7]=bytes.fromhex('22 00 c0 01')
  main[11:11]=bytes.fromhex('9c 00 00 9c 02 00 9c f0 30 9c f1 30');main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+12)
 ppu_boot=None
 if a.ppu_scene:
  from m4_native_window_ppu import compile_boot
  ppu_boot=compile_boot(out/'palette-context-1',window)
  rom[0xa0000:0xd0000]=ppu_boot['data'];rom[0xd000:0xd000+len(ppu_boot['code'])]=ppu_boot['code'];rom[0xe000:0xe000+len(ppu_boot['irq'])]=ppu_boot['irq'];rom[0x100:0x104]=bytes.fromhex('5c 00 e0 01');rom[0x7fee:0x7ff0]=struct.pack('<H',0x8100)
  main[-3:-3]=bytes.fromhex('ad 02 00 c9 02 d0 04 5c 00 d0 01')
 rom[0x8000:0x8400]=main+bytes([255])*(1024-len(main));rom[0x7fd7]=13 if a.direct_palette_lookup else(12 if index_worker else 11)
 if a.invalidate_fused_palette:rom[0x100000:0x100000+len(fused_tables)]=bytes(len(fused_tables))
 path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua';all_entries={**{'underlay_'+k:v for k,v in entries.items()},**{'shader_'+k:v for k,v in screen_entries.items()}}
 observer='local chrStage=false;local regs={};local transfers=0;local bytes=0;local dmaBad=0;local pixels=0;local pixelBad=0;local screenStage=false\n'
 if a.native_characters:
  observer+='local ct={};for i=0,255 do local c=i;for j=1,8 do c=(c&1)~=0 and((c>>1)~0xedb88320)or(c>>1)end;ct[i]=c end\n'
  observer+=f"local function underlayCrc()local c=0xffffffff;for i=0,{w*h*2-1} do local v=emu.read(0x420000+i,emu.memType.sa1Memory);c=(c>>8)~ct[(c~v)&255]end;return (~c)&0xffffffff end\n"
 extra_colour=f"or (not screenStage and dst>=0x27000 and dst+n<={0x27000+len(expected[0])})"if a.whole_tile_canvas else''
 observer+=f"emu.addMemoryCallback(function(a,v)regs[a]=v;if a==0x2237 and regs[0x2230]==0x84 then local dst=(regs[0x2235] or 0)+(regs[0x2236] or 0)*256+v*65536;local n=(regs[0x2238] or 0)+(regs[0x2239] or 0)*256;if n==0 then n=65536 end;transfers=transfers+1;bytes=bytes+n;local first=screenStage and 0x27000 or 0x20000;local last=screenStage and {0x27000+len(expected[0])} or {0x20000+w*h*2};if not ((dst>=first and dst+n<=last) {extra_colour}) then dmaBad=dmaBad+1 end end end,emu.callbackType.write,0x2230,0x2239,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 observer+=f"emu.addMemoryCallback(function(a,v)pixels=pixels+1;if a>={0x427000+len(expected[0])} then pixelBad=pixelBad+1 end end,emu.callbackType.write,0x427000,0x42ffff,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 for n,v in all_entries.items():
  extra='screenStage=false;transfers=0;bytes=0;dmaBad=0'if n=='underlay_entry'else"emu.log('JOINTDMA|'..transfers..'|'..bytes..'|'..dmaBad)"if n=='underlay_done'else'screenStage=true;transfers=0;bytes=0;dmaBad=0;pixels=0;pixelBad=0'if n=='shader_entry'else"emu.log('JOINTPIXELS|'..pixels..'|'..pixelBad);emu.log('SCREENBASE|'..transfers..'|'..bytes..'|'..dmaBad)"if n in('shader_done','shader_fault')else"emu.log('EPOCHFAULTDMA|'..transfers..'|'..bytes..'|'..dmaBad)"if n=='underlay_epoch_fault'else''
  if a.type1_vram and n=='underlay_entry':extra+=";emu.log('TYPE1ENTRY|'..emu.read(0x413ff4,emu.memType.sa1Memory)..'|'..emu.read(0x42d100,emu.memType.sa1Memory)..'|'..emu.read(0x42d101,emu.memType.sa1Memory)..'|'..emu.read(0x42d102,emu.memType.sa1Memory)..'|'..emu.read(0x42d103,emu.memType.sa1Memory)..'|'..emu.read(0x3216,emu.memType.sa1Memory))"
  if a.native_characters and n=='shader_done':extra+=";emu.log('UNDERLAYCRC|'..underlayCrc())"
  guard="if not chrStage then"if a.iram_native_characters and n.startswith("underlay_")else""
  guard_end="end"if guard else""
  observer+=f"emu.addMemoryCallback(function(){guard} local s=emu.getState();emu.log('JOINTSCREEN|{n}|'..s.masterClock);{extra};{guard_end} end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 if a.adaptive_shader:
  v=full_entries['done'];observer+=f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('JOINTSCREEN|shader_done|'..s.masterClock);emu.log('JOINTPIXELS|'..pixels..'|'..pixelBad);emu.log('SCREENBASE|'..transfers..'|'..bytes..'|'..dmaBad);end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 if a.direct_palette_lookup:
  observer+="emu.addMemoryCallback(function(a,v)emu.log('WINDOWMMC|'..v..'|'..emu.read(0x413fe8,emu.memType.snesMemory))end,emu.callbackType.write,0x2222,0x2222,emu.cpuType.snes,emu.memType.snesMemory)\n"
 if index_worker:
  observer+='local indexStage=false;local indexWrites=0;local indexBad=0\n'
  observer+=f"emu.addMemoryCallback(function(a,v)if indexStage and not ({'true'if a.sparse_palette_indices else'false'} and a>=0x42d200 and a<0x42d200+{(w*h+7)//8+2}) then indexWrites=indexWrites+1;if a>={0x427000+w*h*2} then indexBad=indexBad+1 end end end,emu.callbackType.write,0x427000,0x42ffff,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
  for n in('phase','done'):
   v=index_entries[n];observer+=f"emu.addMemoryCallback(function()emu.log('WINDOWINDEX|{n}|'..emu.getState().masterClock);"+('indexStage=true;indexWrites=0;indexBad=0;'if n=='phase'else"emu.log('WINDOWWRITES|'..indexWrites..'|'..indexBad);indexStage=false;")+f"end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 if a.native_characters:
  observer+='local chrBitmapDmas=0;local chrBitmapBytes=0;local chrBitmapBad=0;local chrCpuBytes=0;local chrCpuBad=0;local chrRegs={};local chrTransfers=0;local chrBytes=0;local chrBad=0;local chrHighRows=0;local chrLowRows=0\n'
  observer+=f"emu.addMemoryCallback(function(a,v)chrRegs[a]=v;if not chrStage then return end;if a==0x2237 and chrRegs[0x2230]==0x86 then local n=(chrRegs[0x2238]or 0)+(chrRegs[0x2239]or 0)*256;local src=(chrRegs[0x2232]or 0)+(chrRegs[0x2233]or 0)*256+(chrRegs[0x2234]or 0)*65536;local dst=(chrRegs[0x2235]or 0)+(chrRegs[0x2236]or 0)*256+v*65536;local high=chrTransfers<{w*h//64};local size=high and 64 or 16;local tile=high and chrTransfers or chrTransfers-{w*h//64};local expectedSrc=0x3600+(tile%2)*size;if n~=size or src~=expectedSrc or dst~=0x20000+chrBytes then chrBad=chrBad+1 end;chrTransfers=chrTransfers+1;chrBytes=chrBytes+n end end,emu.callbackType.write,0x2230,0x2239,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
  observer+="emu.addMemoryCallback(function(a,v)if chrStage and(a==0x2247 or a==0x224f)then if chrRegs[0x2230]~=0xa0 then chrBad=chrBad+1 end;if chrRegs[0x2231]==0 then chrHighRows=chrHighRows+1 elseif chrRegs[0x2231]==2 then chrLowRows=chrLowRows+1 else chrBad=chrBad+1 end end end,emu.callbackType.write,0x2240,0x224f,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
  observer+=f"emu.addMemoryCallback(function(a,v)if chrStage then chrCpuBytes=chrCpuBytes+1;if a>={0x420000+w*h*10//8} then chrCpuBad=chrCpuBad+1 end end end,emu.callbackType.write,0x420000,0x426000,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
  observer+=f"emu.addMemoryCallback(function(a,v)if chrStage and a==0x2237 and chrRegs[0x2230]==0x84 then local dst=(chrRegs[0x2235]or 0)+(chrRegs[0x2236]or 0)*256+v*65536;local n=(chrRegs[0x2238]or 0)+(chrRegs[0x2239]or 0)*256;local src=(chrRegs[0x2232]or 0)+(chrRegs[0x2233]or 0)*256+(chrRegs[0x2234]or 0)*65536;chrBitmapDmas=chrBitmapDmas+1;chrBitmapBytes=chrBitmapBytes+n;if dst~=0x20000 or n~={w*h*10//8} or(src~=0xcd0000 and src~=0xcd0000+{w*h*10//8})then chrBitmapBad=chrBitmapBad+1 end end end,emu.callbackType.write,0x2230,0x2239,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
  observer+=f"emu.addMemoryCallback(function()chrBitmapDmas=0;chrBitmapBytes=0;chrBitmapBad=0;chrCpuBytes=0;chrCpuBad=0;chrTransfers=0;chrBytes=0;chrBad=0;chrHighRows=0;chrLowRows=0 end,emu.callbackType.exec,{chr_entries['entry']},{chr_entries['entry']},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
  observer+=f"emu.addMemoryCallback(function()emu.log('CHRBITMAPDMA|'..chrBitmapDmas..'|'..chrBitmapBytes..'|'..chrBitmapBad);emu.log('CHRCPU|'..chrCpuBytes..'|'..chrCpuBad);emu.log('CHRBOUNDS|'..chrTransfers..'|'..chrBytes..'|'..chrBad..'|'..chrHighRows..'|'..chrLowRows)end,emu.callbackType.exec,{chr_entries['done']},{chr_entries['done']},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
  for n,v in chr_entries.items():observer+=f"emu.addMemoryCallback(function()chrStage={'true'if n=='entry'else'false'};emu.log('JOINTCHR|{n}|'..emu.getState().masterClock)end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 if a.type1_vram:
  observer+='local type1Active=false;local type1Reads=0;local type1BadReads=0;local type1Sa1Reads=0\n'
  observer+="emu.addMemoryCallback(function(a,v)if a==0x2236 then type1Active=true elseif a==0x2231 and(v&128)~=0 then type1Active=false end end,emu.callbackType.write,0x2231,0x2236,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+=f"emu.addMemoryCallback(function(a,v)if type1Active then type1Reads=type1Reads+1;if not(a>=0x420000 and a<{0x420000+w*h*10//8})then type1BadReads=type1BadReads+1 end end end,emu.callbackType.read,0x400000,0x43ffff,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addMemoryCallback(function(a,v)if type1Active then type1Sa1Reads=type1Sa1Reads+1 end end,emu.callbackType.read,0x400000,0x43ffff,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 for n,v in vram_entries.items():
  if n=='dma0':observer+=f"emu.addMemoryCallback(function()type1Reads=0;type1BadReads=0;type1Sa1Reads=0 end,emu.callbackType.exec,{v},{v},emu.cpuType.snes,emu.memType.snesMemory)\n"
  if n=='done1':observer+=f"emu.addMemoryCallback(function()emu.log('TYPE1READS|'..type1Reads..'|'..type1BadReads..'|'..type1Sa1Reads)end,emu.callbackType.exec,{v},{v},emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+=f"emu.addMemoryCallback(function()emu.log('CHRV RAM|{n}|'..emu.getState().masterClock)end,emu.callbackType.exec,{v},{v},emu.cpuType.snes,emu.memType.snesMemory)\n"
 if a.ppu_scene:
  observer+="local ppuActive=false;local ppuFrames=0;local ppuRestore=false;local ppuRows={};local ppuOam={};local ppuClocks={};local ppuFlags={}\n"
  observer+="emu.addMemoryCallback(function(a,v)ppuRestore=v==1 end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addMemoryCallback(function(a,v)if v==15 then ppuActive=true end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addMemoryCallback(function(a,v)if ppuActive and ppuFrames==1 and not ppuRestore then ppuRows[#ppuRows+1]=string.format('%04x:%02x',a,v);if #ppuRows%31==2 or #ppuRows%31==0 then local state=emu.getState();ppuClocks[#ppuClocks+1]=(state.masterClock+4*(state['ppu.frameCount']//2))%1364 end end end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addMemoryCallback(function(a,v)ppuOam[#ppuOam+1]=string.format('%02x',v)end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addEventCallback(function()if ppuActive then ppuFrames=ppuFrames+1;emu.log('NATIVEPPUFLAGS|'..emu.read(0x213e,emu.memType.snesMemory));if ppuFrames==2 then emu.log('NATIVEPPUCGRAM|'..table.concat(ppuRows,','));emu.log('NATIVEPPUOAM|'..table.concat(ppuOam,''));emu.log('NATIVEPPUCLOCKS|'..table.concat(ppuClocks,','))end end end,emu.eventType.endFrame)\n"
 lua.write_text(observer)
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 bitmap_paths=[];native_vram=[];native_chr=[];converted_counts=[];actual_indices=[];actual=[];actual_underlays=[];counts=[];correction_counts=[];selected_paths=[]
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for phase,target in enumerate((b'\xa1\xb4',b'\xab\xb4')):
   for _ in range(60):
    run_frames_exact(m,1)
    if a.type1_vram and(m.read_memory('SnesMemory',0x7e0002,1)!=bytes([phase+1])or a.ppu_scene and phase==1 and m.read_memory('SnesMemory',0x7e0003,1)!=b'\x01'):continue
    marker=m.read_memory('SnesMemory',0x413ff0,2)
    if marker in(target,b'\xae\xb4',b'\xe1\xb4'):break
   if marker==b'\xe1\xb4' and a.invalidate_context and phase==1:break
   if marker==b'\xae\xb4'and a.invalidate_fused_palette:break
   if marker!=target:raise ValueError('JOINT_NATIVE_SCREEN_COMPLETION:'+marker.hex()+':'+m.read_memory('SnesMemory',0x413fea,4).hex())
   actual.append(m.read_memory('SnesMemory',0x427000,len(expected[phase])));actual_underlays.append(m.read_memory('SnesMemory',0x420000,len(underlays[phase])))if not a.native_characters else None
   if a.native_characters:native_chr.append(m.read_memory('SnesMemory',0x420000,w*h*10//8))
   if a.type1_vram:native_vram.append(m.read_memory('SnesVideoRam',ppu_high_start if a.ppu_scene else 0,w*h)+m.read_memory('SnesVideoRam',49152 if a.ppu_scene else 0x4000,w*h//4))
   if a.adaptive_native_bitmaps:bitmap_paths.append(int.from_bytes(m.read_memory('SnesMemory',0x413fe0,2),'little'))
   if a.sparse_palette_indices:converted_counts.append(int.from_bytes(m.read_memory('SnesMemory',0x413fe6,2),'little'))
   if index_worker or a.fused_screen_indices:
    if a.fused_screen_indices:index_decoders=index_data[3];index_expected=index_data[2];palette_reports=index_data[4]
    from m4_hybrid_window_indices import decode
    actual_indices.append(actual[-1]);actual[-1]=decode(actual[-1],index_decoders[phase],w,h)
   counts.append(struct.unpack('<HH',m.read_memory('SnesMemory',0x413ff6,4)))
   if a.background_corrections:correction_counts.append(int.from_bytes(m.read_memory('SnesMemory',0x413ffa,2),'little'))
   if a.adaptive_shader:selected_paths.append(int.from_bytes(m.read_memory('SnesMemory',0x413ffc,2),'little'))
   if phase==0:
    offset=moving[0]*4;x=struct.unpack_from('<h',origins,offset)[0]+a.move_x;m.write_memory('SnesMemory',0x42d000+offset,struct.pack('<h',x).hex())
    if a.invalidate_context:
     half=(context_epoch>>16)if a.invalidate_context=='high'else(context_epoch&65535);m.write_memory('SnesMemory',0x42d100+(2 if a.invalidate_context=='high'else 0),struct.pack('<H',half^1).hex())
    m.write_u16(0x0030f0 if a.type1_vram else 0x413ff4,1)
  if a.ppu_scene:
   import shutil
   for _ in range(5):run_frames_exact(m,1)
   shot=m.tool('take_screenshot',{'format':'path'});shutil.copyfile(shot['path'],out/'screenshot.png')
  if a.type1_vram:(out/'type1-cpu-state.json').write_text(json.dumps(dict(snes=m.get_cpu_state(),sa1=m.get_cpu_state('Sa1')),indent=2))
 if a.invalidate_fused_palette:
  log=(out/'mesen.log').read_text();fault_writes=[[int(n)for n in v.split('JOINTPIXELS|',1)[1].split('|')]for v in log.splitlines()if'JOINTPIXELS|'in v]
  events=[v.split('JOINTSCREEN|',1)[1].split('|')for v in log.splitlines()if'JOINTSCREEN|'in v]
  ok=marker==b'\xae\xb4'and fault_writes==[[0,0]]and[v[0]for v in events]==['underlay_entry','underlay_done','shader_entry','shader_fault']
  report=dict(schema='BYOR_FUSED_PALETTE_NATIVE_REJECTION_V1',status='PASS'if ok else'FAIL',proof_kind='EXPECTED_MISSING_PALETTE_ADMISSION_REJECTION',marker=marker.hex(),shader_output_write_trace=fault_writes,job_events=events,rom_sha256=hashlib.sha256(rom).hexdigest(),no_color_reduction=True,frame_identity_proven=False,CHR_publication=False,motu_gameplay_proven=False,production_memory_lease=False)
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
  if not ok:raise SystemExit(1)
  return
 events=[v.split('JOINTSCREEN|',1)[1].split('|')for v in(out/'mesen.log').read_text().splitlines()if'JOINTSCREEN|'in v];one_names=['underlay_entry','underlay_done','shader_entry','shader_done'];names=one_names+['underlay_entry','underlay_epoch_fault']if a.invalidate_context else one_names*2;clocks=[int(events[i+3][1])-int(events[i][1])for i in((0,)if a.invalidate_context else(0,4))]if[v[0]for v in events]==names else None;ok=actual==expected[:len(actual)] and (a.native_characters or actual_underlays==underlays[:len(actual_underlays)]) and clocks is not None and (not a.invalidate_context or marker==b'\xe1\xb4'and len(actual)==1)
 report=dict(schema='BYOR_NATIVE_UNDERLAY_SCREEN_JOINT_V1',status='PASS'if ok else'FAIL',opaque_pixels=len(order),underlay_pixels=w*h,RGB555_byte_mismatches=[sum(x!=y for x,y in zip(v,e))for v,e in zip(actual,expected)],underlay_RGB8_identity_byte_mismatches=[sum(x!=y for x,y in zip(v,e))for v,e in zip(actual_underlays,underlays)],master_clocks=clocks,milliseconds=[v/21477.27 for v in clocks]if clocks else None,job_events=events,underlay_worker_IRAM_bytes=len(span_worker),shader_worker_IRAM_bytes=len(screen_worker),retained_stage_window=a.retain_stage,rom_sha256=hashlib.sha256(rom).hexdigest(),table_sha256=hashlib.sha256(table.tobytes()).hexdigest(),source_layers=metadata['layers'],no_color_reduction=True,host_supplied_pixel_inputs=False,native_opaque_actor_composition=True,native_SCREEN_shading=True,native_camera_bound=False,native_palette_allocation=False,CHR_publication=False,joint_audio_proven=False,production_memory_lease=False,motu_gameplay_proven=False,scope='Native clipped opaque spans produce underlay identities consumed directly by native exact RGB8 SCREEN shading. Two mutable actor origins, fixed stage/camera/source frame/layer order. No host pixel input between stages. No palette allocation, CHR publication, live VM, production lease or joint audio deadline admission.')
 for phase,data in enumerate(actual):(out/('effect-%d.rgb555'%phase)).write_bytes(data)
 lines=(out/'mesen.log').read_text().splitlines();traces={label:[[int(n)for n in v.split(label+'|',1)[1].split('|')]for v in lines if label+'|'in v]for label in('JOINTDMA','JOINTPIXELS','SCREENBASE')}
 expected_dma=[[values[0]+(counts[i-1][0]if a.retain_stage and i and not a.native_characters else 1),(2*counts[i-1][1]if a.retain_stage and i and not a.native_characters else len(bg))+2*values[1],0]for i,values in enumerate(counts)]
 if a.whole_tile_canvas:
  expected_dma=[[values[0]*2+(counts[i-1][0]if a.retain_stage and i and not a.native_characters else 1)+1,(2*counts[i-1][1]if a.retain_stage and i and not a.native_characters else len(bg))+len(bg)+4*values[1],0]for i,values in enumerate(counts)]
 expected_pixel_writes=[[2*n,0]for n in expected_corrections]if a.background_corrections else[[len(v),0]for v in expected]
 expected_baseline_dma=[[1,len(v),0]for v in expected]if a.background_corrections else[[0,0,0]]*2
 if a.whole_tile_canvas:expected_baseline_dma=[[0,0,0]]*2
 active_expected_corrections=list(expected_corrections[:len(actual)])
 if a.adaptive_shader:
  expected_paths=[int(values[1]>=max(1,len(order)//2))for values in counts]
  for i,path in enumerate(expected_paths):
   if path:expected_pixel_writes[i]=[len(order)*2,0];expected_baseline_dma[i]=[0,0,0];active_expected_corrections[i]=0
 else:expected_paths=[]
 observer_ok=traces['JOINTDMA']==expected_dma and traces['JOINTPIXELS']==expected_pixel_writes[:len(actual)] and traces['SCREENBASE']==expected_baseline_dma[:len(actual)] and (not a.background_corrections or correction_counts==active_expected_corrections) and selected_paths==expected_paths
 report.update(observer_traces=traces,expected_DMA_trace=expected_dma,native_DMA_and_shader_output_bounds_proven=observer_ok,compiled_geometry_sha256=hashlib.sha256(coordinates).hexdigest(),compiled_group_descriptors_sha256=hashlib.sha256(desc).hexdigest(),output_sha256=[hashlib.sha256(v).hexdigest()for v in actual])
 report.update(compiler_opaque_RGB8_identity_contract_checked=True,typed_underlay=a.typed_underlay,per_pixel_destination_guards=not a.typed_underlay,identity_producer='Immutable compiler-checked ROM stage/spans; native clipped copies and restores only',arbitrary_underlay_writes_supported=False)
 report.update(precompiled_background_SCREEN=a.background_corrections,native_actor_correction_counts=correction_counts,expected_actor_correction_counts=expected_corrections,correction_map_ROM_bytes=len(correction_map)if correction_map is not None else 0,background_SCREEN_ROM_bytes=len(baseline)if baseline is not None else 0,background_SCREEN_sha256=hashlib.sha256(baseline).hexdigest()if baseline is not None else None,background_epoch_unchanged_required=a.background_corrections,native_baseline_rebuild_bound=False)
 report.update(adaptive_shader=a.adaptive_shader,native_selected_paths=selected_paths,path_legend={'0':'compiled background plus native actor corrections','1':'full typed SCREEN shader'},adaptive_actor_pixel_threshold=max(1,len(order)//2)if a.adaptive_shader else None,full_fallback_IRAM_bytes=len(full_worker)if full_worker else 0,adaptive_policy_optimal=False,correction_map_sha256=hashlib.sha256(correction_map).hexdigest()if correction_map is not None else None)
 fault_dma=[[int(n)for n in v.split('EPOCHFAULTDMA|',1)[1].split('|')]for v in lines if'EPOCHFAULTDMA|'in v]
 report.update(compiled_context_epoch=context_epoch,compiled_context_digest=context_digest.hex(),native_context_epoch_admission=True,native_context_owner_bound=False,invalidated_context_half=a.invalidate_context,context_rejection_DMA_trace=fault_dma,proof_kind='EXPECTED_CONTEXT_REJECTION'if a.invalidate_context else'EXACT_NATIVE_PRODUCER_CHAIN')
 report.update(whole_tile_colour_canvas=a.whole_tile_canvas,colour_canvas_source_bytes=len(colour_canvas)if colour_canvas is not None else 0,actor_RGB555_span_ROM_bytes=len(colour_pixels)if colour_pixels is not None else 0,window=list(window),post_layer_overlap_supported=False,transient_memory_map={'underlay':hex(0x420000),'restore_descriptors':hex(0x426000),'RGB555_output':hex(0x427000),'actor_origins':hex(0x42d000),'context_epoch':hex(0x42d100)})
 if index_worker:
  index_events=[v.split('WINDOWINDEX|',1)[1].split('|')for v in lines if'WINDOWINDEX|'in v]
  index_clocks=[int(index_events[i+1][1])-int(index_events[i][1])for i in range(0,len(index_events),2)]
  index_writes=[[int(n)for n in v.split('WINDOWWRITES|',1)[1].split('|')]for v in lines if'WINDOWWRITES|'in v]
  mmc_trace=[[int(n)for n in v.split('WINDOWMMC|',1)[1].split('|')]for v in lines if'WINDOWMMC|'in v]
  mmc_expected=[]
  if a.direct_palette_lookup:
   for offset in range(3,len(index_pointers),4):
    value=index_pointers[offset]
    if not mmc_expected or value!=mmc_expected[-1][0]:mmc_expected.append([value,value])
  if a.sparse_palette_indices:
   from m4_hybrid_window_indices import sparse_trace
   span_mmc_expected,expected_converted_counts=sparse_trace(span_desc,origins,moving[0],a.move_x,index_pointers,w,h)
   if not a.bitmap_palette_indices:mmc_expected=span_mmc_expected
   mmc_ok=mmc_trace==mmc_expected and converted_counts==expected_converted_counts
   write_expected=[[n*2,0]for n in converted_counts]
  else:mmc_ok=mmc_trace==mmc_expected;write_expected=[[w*h*2,0]]*len(actual_indices)
  index_ok=mmc_ok and actual_indices==index_expected[:len(actual_indices)] and index_writes==write_expected
  report.update(native_palette_index_conversion=True,sparse_palette_indices=a.sparse_palette_indices,bitmap_palette_indices=a.bitmap_palette_indices,iram_bitmap_indices=a.iram_bitmap_indices,native_unique_converted_pixels=converted_counts,native_SCPU_MMC_trace=mmc_trace,expected_SCPU_MMC_trace=mmc_expected,direct_palette_lookup=a.direct_palette_lookup,native_palette_index_identity_verified=index_ok,palette_index_kernel_bytes=len(index_worker),palette_index_ROM_worker_bytes=len(sparse_worker)if a.sparse_palette_indices else 0,palette_lookup_ROM_bytes=len(index_maps),palette_index_master_clocks=index_clocks,palette_index_milliseconds=[v/21477.27 for v in index_clocks],palette_index_write_trace=index_writes,compiled_palette_peak_CGRAM_bytes=[v['bg_schedule']['peak_bytes']for v in palette_reports],palette_context_choice='Two explicit fixture poses; live source ownership and selection unbound',native_palette_allocation=False)
  for i,data in enumerate(actual_indices):(out/('window-%d.high-low-indices'%i)).write_bytes(data)
  if not index_ok:ok=False;report['status']='FAIL'
 if a.fused_screen_indices:
  report.update(fused_SCREEN_palette_lookup=True,fused_scanline_map_ROM_bytes=sum(map(len,fused_maps)),fused_actor_index_span_ROM_bytes=len(colour_pixels)+len(colour_pixels_second),fused_stage_index_canvas_ROM_bytes=len(colour_canvas)+len(colour_canvas_second),fused_table_ROM_bytes=len(fused_tables),fused_table_sha256=hashlib.sha256(fused_tables).hexdigest(),fused_underlay_vocabulary_count=fused_report['underlay_vocabulary_count'],persistent_actor_HIGH_slots=[v['persistent_actor_high_slots']for v in palette_reports],compiled_palette_peak_CGRAM_bytes=[v['bg_schedule']['peak_bytes']for v in palette_reports],fused_index_bytes_equal_compiler=actual_indices==index_expected[:len(actual_indices)],native_palette_allocation=False,fused_index_context_policy='Two compiler pose contexts with persistent actor HIGH slots and scanline-live BG palettes; live context owner unbound')
  for i,data in enumerate(actual_indices):(out/('window-%d.high-low-indices'%i)).write_bytes(data)
 if a.native_characters:
  import zlib
  from m4_window_characters import expected_bitmap,expected as expected_chr
  if a.native_bitmaps:expected_chr=expected_bitmap
  chr_events=[v.split('JOINTCHR|',1)[1].split('|')for v in lines if'JOINTCHR|'in v];chr_clocks=[int(chr_events[i+1][1])-int(chr_events[i][1])for i in range(0,len(chr_events),2)]
  underlay_crc=[int(v.split('UNDERLAYCRC|',1)[1])for v in lines if'UNDERLAYCRC|'in v];expected_crc=[zlib.crc32(v)for v in underlays[:len(actual)]]
  chr_expected=[expected_chr(v,w,h)for v in index_expected[:len(actual)]]
  chr_bounds=[[int(n)for n in v.split('CHRBOUNDS|',1)[1].split('|')]for v in lines if'CHRBOUNDS|'in v]
  expected_chr_bounds=([[0,0,0,0,0]]if a.native_bitmaps else[[w*h//32,w*h*10//8,0,w*h//8,w*h//8]])*len(native_chr)
  chr_cpu=[[int(n)for n in v.split('CHRCPU|',1)[1].split('|')]for v in lines if'CHRCPU|'in v]
  expected_chr_cpu=[[w*h*10//8 if bitmap_paths[i]else 2*v[1],0]for i,v in enumerate(counts)]if a.adaptive_native_bitmaps else[[2*v[1],0]for v in counts]if a.sparse_native_bitmaps else([[w*h*10//8,0]]if a.native_bitmaps else[[0,0]])*len(native_chr)
  bitmap_dma=[[int(n)for n in v.split('CHRBITMAPDMA|',1)[1].split('|')]for v in lines if'CHRBITMAPDMA|'in v]
  expected_bitmap_dma=[[0,0,0]if path else[1,w*h*10//8,0]for path in bitmap_paths]if a.adaptive_native_bitmaps else([[1,w*h*10//8,0]]if a.sparse_native_bitmaps else[[0,0,0]])*len(native_chr)
  chr_ok=native_chr==chr_expected and underlay_crc==expected_crc and chr_bounds==expected_chr_bounds and chr_cpu==expected_chr_cpu and bitmap_dma==expected_bitmap_dma and(not a.adaptive_native_bitmaps or bitmap_paths==[0 if v[1]<2200 else 1 for v in counts])
  report.update(adaptive_native_bitmap_serialization=a.adaptive_native_bitmaps,native_bitmap_selected_paths=bitmap_paths,native_bitmap_selection_threshold=2200 if a.adaptive_native_bitmaps else None,native_bitmap_selection_optimal=False,native_bitmap_path_legend={0:"stage bitmap plus clipped actor updates",1:"full window serialization"},sparse_native_bitmap_serialization=a.sparse_native_bitmaps,native_bitmap_stage_DMA_trace=bitmap_dma,expected_bitmap_stage_DMA_trace=expected_bitmap_dma,native_type1_bitmap_serialization=a.native_bitmaps,native_bitmap_CPU_write_trace=chr_cpu,expected_bitmap_CPU_write_trace=expected_chr_cpu,native_character_DMA_and_type2_trace=chr_bounds,expected_character_DMA_and_type2_trace=expected_chr_bounds,native_character_transfer_bounds_verified=chr_bounds==expected_chr_bounds,character_code_swap_transfer_bounds_verified=False)
  report.update(native_8bpp_2bpp_character_packing=not a.native_bitmaps,iram_native_characters=a.iram_native_characters,native_character_code_swap=bool(a.iram_native_characters),CHR_publication=False,native_character_ROM_worker_bytes=len(chr_worker),native_character_bytes_per_pose=w*h*10//8,native_character_byte_mismatches=[sum(a!=b for a,b in zip(v,e))for v,e in zip(native_chr,chr_expected)],native_character_master_clocks=chr_clocks,native_character_milliseconds=[v/21477.27 for v in chr_clocks],native_character_sha256=[hashlib.sha256(v).hexdigest()for v in native_chr],underlay_RGB8_identity_byte_mismatches=None,underlay_observer_crc32=underlay_crc,expected_underlay_crc32=expected_crc,underlay_consumed_then_reloaded=True,character_IRAM_buffers=[0x3600,0x3680],character_output_BWRAM=[0x420000,0x420000+w*h*10//8])
  for i,data in enumerate(native_chr):(out/('window-%d.chr'%i)).write_bytes(data)
  if not chr_ok:ok=False;report['status']='FAIL'
 if a.type1_vram:
  from m4_window_characters import expected as packed_chr
  vram_expected=[packed_chr(v,w,h)for v in index_expected]
  vram_events=[v.split('CHRV RAM|',1)[1].split('|')for v in lines if'CHRV RAM|'in v]
  vram_clocks=[int(vram_events[i+1][1])-int(vram_events[i][1])for i in range(0,len(vram_events),2)]
  type1_reads=[[int(n)for n in v.split('TYPE1READS|',1)[1].split('|')]for v in lines if'TYPE1READS|'in v]
  type1_read_expected=[[w*h*10//8,0,0]]*(3 if a.ppu_scene else 2)
  vram_ok=native_vram==vram_expected and type1_reads==type1_read_expected and len(vram_clocks)==(6 if a.ppu_scene else 4) and all(v>=d['bytes']*8 for v,d in zip(vram_clocks,vram_descriptors*(3 if a.ppu_scene else 2))) and[v[0]for v in vram_events]==['dma0','done0','dma1','done1']*(3 if a.ppu_scene else 2)
  report.update(type1_exclusive_BWRAM_read_trace=type1_reads,type1_expected_exclusive_BWRAM_read_trace=type1_read_expected,scope='Two explicit poses: native opaque spans, exact SCREEN, palette indices, bitmap serialization and forced-blank CHR delivery. No PPU scene, live context, audio deadline or production memory lease.',forced_blank_native_CHR_publication=vram_ok,CHR_publication=vram_ok,type1_vram_descriptors=vram_descriptors,type1_vram_master_clocks=vram_clocks,type1_vram_byte_mismatches=[sum(a!=b for a,b in zip(v,e))for v,e in zip(native_vram,vram_expected)],type1_VBlank_deadline_admitted=False)
  if not vram_ok:ok=False;report['status']='FAIL'
 if a.ppu_scene:
  from PIL import Image
  pixels=np.asarray(Image.open(out/'screenshot.png').convert('RGB'),dtype=np.uint16)
  rendered=(pixels[:,:,0]>>3)|((pixels[:,:,1]>>3)<<5)|((pixels[:,:,2]>>3)<<10)
  expected_ppu=np.frombuffer(ppu_boot['expected'],dtype='<u2').reshape(224,256)
  cg=[v.split('NATIVEPPUCGRAM|',1)[1].split(',')for v in lines if'NATIVEPPUCGRAM|'in v]
  oam=[v.split('NATIVEPPUOAM|',1)[1]for v in lines if'NATIVEPPUOAM|'in v]
  flags=[int(v.split('NATIVEPPUFLAGS|',1)[1])for v in lines if'NATIVEPPUFLAGS|'in v]
  ppu_clocks=[[int(n)for n in v.split('NATIVEPPUCLOCKS|',1)[1].split(',')]for v in lines if'NATIVEPPUCLOCKS|'in v]
  ppu_timing_ok=len(ppu_clocks)==1 and len(ppu_clocks[0])==448 and not any(88<=v<1096 for v in ppu_clocks[0])
  (out/'ppu-observer.json').write_text(json.dumps(dict(CGRAM=cg,OAM=oam,OBJ_flags=flags,CGRAM_first_last_hclocks=ppu_clocks),indent=2)+'\n')
  ppu_ok=rendered.shape==expected_ppu.shape and np.array_equal(rendered,expected_ppu)and cg==[ppu_boot['trace']]and oam==[(out/'palette-context-1/oam.bin').read_bytes().hex()]and bool(flags)and not any(v&192 for v in flags)and ppu_timing_ok
  report.update(native_PPU_CGRAM_HBlank_timing_verified=ppu_timing_ok,native_PPU_CGRAM_hclock_range=[min(ppu_clocks[0]),max(ppu_clocks[0])]if ppu_clocks else None,scope='Native opaque composition through exact SCREEN, palette indices, type1 CHR DMA and PPU presentation for two explicit poses. Static surroundings and offline palette schedules; no live context, joint audio deadline or production memory lease.',native_PPU_scene_pixel_identity=ppu_ok,native_PPU_pixel_mismatches=int(np.count_nonzero(rendered!=expected_ppu))if rendered.shape==expected_ppu.shape else None,native_PPU_CGRAM_observer_verified=cg==[ppu_boot['trace']],native_PPU_OAM_observer_verified=oam==[(out/'palette-context-1/oam.bin').read_bytes().hex()],native_PPU_OBJ_flags=flags,native_PPU_resources=ppu_boot['resources'],native_window_static_placeholder_overwritten=True,motu_gameplay_proven=False)
  if not ppu_ok:ok=False;report['status']='FAIL'
 if a.invalidate_context and fault_dma!=[[0,0,0]]:ok=False;report['status']='FAIL'
 if not observer_ok:ok=False;report['status']='FAIL'
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='source_layers'}))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
