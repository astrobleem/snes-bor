"""Native opaque-span clipping/composition before lossless SCREEN shading.

The stage window and source spans are compiler inputs. Actor origins are mutable
native inputs. No live camera, source VM binding or production lease is claimed.
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
from source_screen_lookup import derive
import source_scene_bg
import m4_screen_sa1_native as base
from m4_screen_grouped_native import capture_plane
from m4_sound_mix_sa1_native import Code
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact


def compile_inputs(source,stage,scene,catalog):
 _,metadata=base.capture(source,stage,scene);effects=[v for v in metadata['layers']if v['alpha']==1]
 if len(effects)!=1:raise ValueError('SINGLE_SCREEN_WINDOW_REQUIRED')
 effect=effects[0];wx,wy=effect['position'];w,h=effect['source_dimensions'];vw,vh=scene.get('viewport',[256,224])
 if not 0<=wx<wx+w<=vw or not 0<=wy<wy+h<=vh or w*h*2>0x5000:raise ValueError('ISOLATED_UNDERLAY_WINDOW_DOMAIN')
 di={tuple(c):i for i,c in enumerate(catalog['destinations'])};actors=[];background=[];original=source_scene_bg.overlay;ordinal=0;seen=False
 def overlay(canvas,indices,rgb,x,y,alpha=0,transparent=True):
  nonlocal ordinal,seen
  layer=metadata['layers'][ordinal];ordinal+=1
  if alpha==1:
   background.append(np.array([di[tuple(map(int,c))]*2 for c in canvas[wy:wy+h,wx:wx+w].reshape(-1,3)],dtype='<u2').tobytes());seen=True
  elif not seen and layer['kind'].startswith('actor:'):
   actors.append((indices.copy(),rgb.copy(),x-wx,y-wy,layer));return 0
  return original(canvas,indices,rgb,x,y,alpha,transparent)
 with patch.object(source_scene_bg,'overlay',overlay):source_scene_bg.compose_rgb8(source,stage,scene)
 if len(background)!=1:raise ValueError('UNDERLAY_BACKGROUND_CAPTURE')
 descriptors=bytearray();pixels=bytearray();origins=bytearray()
 for actor,(indices,rgb,x,y,layer)in enumerate(actors):
  origins.extend(struct.pack('<hh',x,y))
  for row in range(indices.shape[0]):
   mask=indices[row]!=0;edges=np.diff(np.r_[False,mask,False].astype(np.int8));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1)
   for left,right in zip(starts,ends):
    pointer=0xc50000+len(pixels);words=[di[tuple(map(int,c))]*2 for c in rgb[row,left:right]]
    descriptors.extend(struct.pack('<HHHHI',row,int(left),int(right-left),actor*4,pointer)+bytes(4));pixels.extend(struct.pack('<'+'H'*len(words),*words))
 if not descriptors or len(descriptors)//16*4>4096 or len(pixels)>65536 or len(descriptors)>65536 or len(origins)>256:raise ValueError('UNDERLAY_SPAN_ROM_CAPACITY')
 return background[0],bytes(descriptors),bytes(pixels),bytes(origins),actors,(wx,wy,w,h)


def build(background,descriptors,pixels,origins,w,h,retain_stage=False,shader_target=None,expected_context_epoch=None):
 rom,_,_=base.build(np.zeros((3,2),dtype=np.uint16),True,iram=True);rom=bytearray(rom)+bytearray([255])*(1048576-len(rom))
 for at,data in((0x20000,descriptors),(0x30000,origins),(0x40000,background),(0x50000,pixels)):rom[at:at+len(data)]=data
 c=Code(0x3200);c.emit('78 18 fb c2 30 a2 ff 37 9a a9 00 30 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 42 48 ab c2 20 a9 00 00 85 16 85 18 8f f4 3f 41')
 c.label('entry');c.emit('e2 20 a9 42 48 ab c2 20')
 if expected_context_epoch is not None:
  c.emit('af 00 51 42');c.word(0xc9,expected_context_epoch&65535);c.branch(0xf0,'epoch_low_valid');c.jump('epoch_fault');c.label('epoch_low_valid');c.emit('af 02 51 42');c.word(0xc9,expected_context_epoch>>16);c.branch(0xf0,'epoch_valid');c.jump('epoch_fault');c.label('epoch_valid')
 c.emit('64 04 64 12 64 14 e2 20 a9 84 8f 30 22 00 a9 20 8f 0b 22 00 a9 c4 8f 34 22 00 c2 20')
 if retain_stage:c.emit('a5 16');c.branch(0xd0,'restore')
 c.emit('a9 00 00 8f 32 22 00 8f 35 22 00');c.word(0xa9,len(background));c.emit('8f 38 22 00 e2 20 a9 02 8f 37 22 00 c2 20')
 if retain_stage:
  c.jump('restored');c.label('restore');c.emit('a2 00 00 a5 18');c.branch(0xf0,'restored');c.label('restore_span');c.emit('bd 00 60 8f 32 22 00 8f 35 22 00 bd 02 60 8f 38 22 00 e2 20 a9 02 8f 37 22 00 c2 20 e8 e8 e8 e8 e4 18');c.branch(0xd0,'restore_span');c.label('restored');c.emit('64 18')
 c.label('span');c.emit('a6 04 bf 00 00 c2 85 00 bf 02 00 c2 85 02 bf 04 00 c2 85 08 bf 08 00 c2 85 0c e2 20 bf 0a 00 c2 85 0e c2 20 bf 06 00 c2 aa bd 02 50 18 65 00')
 c.branch(0x10,'row_nonnegative');c.jump('next');c.label('row_nonnegative');c.word(0xc9,h);c.branch(0x90,'row_visible');c.jump('next');c.label('row_visible');c.emit('85 00 bd 00 50 18 65 02');c.branch(0x10,'left_nonnegative')
 c.emit('49 ff ff 1a c5 08');c.branch(0x90,'left_clipped');c.jump('next');c.label('left_clipped');c.emit('85 0a a5 08 38 e5 0a 85 08 a5 0a 0a 18 65 0c 85 0c');c.branch(0x90,'pointer_no_carry');c.emit('e2 20 e6 0e c2 20');c.label('pointer_no_carry');c.emit('a9 00 00')
 c.label('left_nonnegative');c.word(0xc9,w);c.branch(0x90,'left_visible');c.jump('next');c.label('left_visible');c.emit('85 02');c.word(0xa9,w);c.emit('38 e5 02 c5 08');c.branch(0xb0,'width_ready');c.emit('85 08');c.label('width_ready')
 c.emit('e2 20 a9 00 8f 50 22 00 c2 20 a5 00 8f 51 22 00');c.word(0xa9,w);c.emit('8f 53 22 00 ea ea ea af 06 23 00 18 65 02 0a 85 1a 8f 35 22 00 a5 0c 8f 32 22 00 a5 08 18 65 14 85 14 a5 08 0a 8f 38 22 00 e2 20 a5 0e 8f 34 22 00 a9 02 8f 37 22 00 c2 20 e6 12')
 if retain_stage:c.emit('a6 18 a5 1a 9d 00 60 a5 08 0a 9d 02 60 e8 e8 e8 e8 86 18')
 c.label('next');c.emit('a5 04 18 69 10 00 85 04');c.word(0xc9,len(descriptors));c.branch(0xf0,'done');c.jump('span')
 c.label('done');c.emit('a5 12 8f f6 3f 41 a5 14 8f f8 3f 41')
 if shader_target is not None:c.emit('5c '+shader_target.to_bytes(3,'little').hex(' '))
 c.emit('a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16');c.jump('entry');c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop')
 if expected_context_epoch is not None:c.label('epoch_fault');c.emit('a9 e1 b4 8f f0 3f 41');c.jump('stop')
 worker=c.finish()
 if c.base+len(worker)>0x3700:raise ValueError('UNDERLAY_SPAN_IRAM_CAPACITY')
 rom[0x9000:0x9000+len(worker)]=worker;main=bytearray(rom[0x8000:0x8400]);main=main[:main.index(bytes([255])*32)];needle=bytes.fromhex('bf 00 90 01 9f 00 32 00 e8 e0');at=main.index(needle)+len(needle);main[at:at+2]=struct.pack('<H',len(worker))
 extra=bytes.fromhex('c2 20 a2 00 00 bf 00 00 c3 9f 00 50 42 e8 e8 e0')+struct.pack('<H',len(origins))+bytes.fromhex('d0 f1 e2 20')
 if expected_context_epoch is not None:extra+=bytes.fromhex('c2 20 a9')+struct.pack('<H',expected_context_epoch&65535)+bytes.fromhex('8f 00 51 42 a9')+struct.pack('<H',expected_context_epoch>>16)+bytes.fromhex('8f 02 51 42 e2 20')
 if main[-3]!=0x4c:raise ValueError('UNDERLAY_SPAN_HOST_LAYOUT')
 main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(extra));at=main.index(needle)-3;main[at:at]=extra;rom[0x8000:0x8400]=main+bytes([255])*(1024-len(main));rom[0x7fd7]=10
 return bytes(rom),{n:c.base+c.labels[n]for n in(('entry','done','epoch_fault')if expected_context_epoch is not None else('entry','done'))},worker


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--move-actor-index',type=int,default=1);p.add_argument('--move-x',type=int,default=-30);p.add_argument('--move-altitude',type=int,default=0);p.add_argument('--retain-stage',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);catalog=derive(source);scene=json.loads(a.scene.read_text());bg,desc,pixels,origins,actors,window=compile_inputs(source,a.stage,scene,catalog);wx,wy,w,h=window;di={tuple(c):i for i,c in enumerate(catalog['destinations'])};expected=[]
 actor_model=scene['actors'][a.move_actor_index]['model'];moving=[i for i,v in enumerate(actors)if v[4]['kind'].split(':',1)[1].casefold()==actor_model.casefold()]
 if len(moving)!=1:raise ValueError('UNIQUE_MOVING_SOURCE_ACTOR_REQUIRED')
 for phase,shift in enumerate((0,a.move_x)):
  pose=json.loads(json.dumps(scene));pose['actors'][a.move_actor_index]['position'][0]+=shift;pose['actors'][a.move_actor_index]['position'][2]+=a.move_altitude if phase else 0;plane,_=capture_plane(source,a.stage,pose,di);full=np.frombuffer(plane,dtype='<u2').reshape(scene.get('viewport',[256,224])[::-1]);expected.append(full[wy:wy+h,wx:wx+w].tobytes())
 rom,entries,worker=build(bg,desc,pixels,origins,w,h,a.retain_stage);path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua'
 observer='local writes=0;local bad=0;local regs={};local transfers=0;local bytes=0;local dmaBad=0\n'+f"emu.addMemoryCallback(function(a,v)writes=writes+1;if a>={0x420000+w*h*2} then bad=bad+1 end end,emu.callbackType.write,0x420000,0x42ffff,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 observer+=f"emu.addMemoryCallback(function(a,v)regs[a]=v;if a==0x2237 and regs[0x2230]==0x84 then local dst=(regs[0x2235] or 0)+(regs[0x2236] or 0)*256+v*65536;local n=(regs[0x2238] or 0)+(regs[0x2239] or 0)*256;if n==0 then n=65536 end;transfers=transfers+1;bytes=bytes+n;if dst<0x20000 or dst+n>{0x20000+w*h*2} then dmaBad=dmaBad+1 end end end,emu.callbackType.write,0x2230,0x2239,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 for n,v in entries.items():observer+=f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('SPANJOB|{n}|'..s.masterClock);"+("writes=0;bad=0;transfers=0;bytes=0;dmaBad=0"if n=='entry'else"emu.log('SPANWRITES|'..writes..'|'..bad);emu.log('SPANDMA|'..transfers..'|'..bytes..'|'..dmaBad)")+f";end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 lua.write_text(observer)
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 actual=[];counts=[]
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for phase,target in enumerate((b'\xa1\xb4',b'\xab\xb4')):
   for _ in range(60):
    run_frames_exact(m,1);marker=m.read_memory('SnesMemory',0x413ff0,2)
    if marker==target:break
   if marker!=target:raise ValueError('NATIVE_UNDERLAY_SPAN_COMPLETION')
   actual.append(m.read_memory('SnesMemory',0x420000,len(expected[phase])));counts.append(struct.unpack('<HH',m.read_memory('SnesMemory',0x413ff6,4)))
   if phase==0:
    offset=moving[0]*4;x=struct.unpack_from('<h',origins,offset)[0]+a.move_x;y=struct.unpack_from('<h',origins,offset+2)[0]-a.move_altitude;m.write_memory('SnesMemory',0x425000+offset,struct.pack('<hh',x,y).hex());m.write_u16(0x413ff4,1)
 events=[v.split('SPANJOB|',1)[1].split('|')for v in(out/'mesen.log').read_text().splitlines()if'SPANJOB|'in v];clocks=[int(events[i+1][1])-int(events[i][1])for i in(0,2)]if[e[0]for e in events]==['entry','done','entry','done']else None;ok=actual==expected and clocks is not None
 report=dict(schema='BYOR_NATIVE_OPAQUE_SPAN_UNDERLAY_V1',status='PASS'if ok else'FAIL',window=list(window),underlay_pixels=w*h,RGB8_identity_word_byte_mismatches=[sum(x!=y for x,y in zip(v,e))for v,e in zip(actual,expected)],native_drawn_spans_and_pixels=counts,source_opaque_spans=len(desc)//16,source_span_pixel_ROM_bytes=len(pixels),stage_window_ROM_bytes=len(bg),worker_IRAM_bytes=len(worker),master_clocks=clocks,milliseconds=[v/21477.27 for v in clocks]if clocks else None,rom_sha256=hashlib.sha256(rom).hexdigest(),source_layers=[v[4]for v in actors],no_color_reduction=True,native_actor_origin_clipping=True,retained_stage_window=a.retain_stage,restore_descriptor_cache_bytes=len(desc)//4 if a.retain_stage else 0,move_x=a.move_x,move_altitude=a.move_altitude,native_opaque_actor_composition=True,native_stage_camera_composition=False,SCREEN_shading_joint=False,production_memory_lease=False,motu_gameplay_proven=False,scope='Two source-derived opaque underlays produced natively from compiled opaque spans and mutable actor origins. The stage window and layer order remain offline inputs. No live VM, camera, palette allocator, CHR publication or joint audio proof.')
 for phase,data in enumerate(actual):(out/('underlay-%d.rgb8ids'%phase)).write_bytes(data)
 write_trace=[[int(n)for n in v.split('SPANWRITES|',1)[1].split('|')]for v in(out/'mesen.log').read_text().splitlines()if'SPANWRITES|'in v]
 expected_writes=[(2*counts[i-1][1] if a.retain_stage and i else len(bg))+2*values[1]for i,values in enumerate(counts)];write_covered=len(write_trace)==2 and [v[0]for v in write_trace]==expected_writes
 report.update(SA1_write_callback_trace=write_trace,expected_composition_bytes_written=expected_writes,write_callback_covers_normal_DMA=write_covered,outside_window_writes=[v[1]for v in write_trace])
 dma_trace=[[int(n)for n in v.split('SPANDMA|',1)[1].split('|')]for v in(out/'mesen.log').read_text().splitlines()if'SPANDMA|'in v]
 dma_ok=dma_trace==[[values[0]+(counts[i-1][0] if a.retain_stage and i else 1),expected_writes[i],0]for i,values in enumerate(counts)]
 report.update(native_DMA_descriptor_trace=dma_trace,DMA_destination_ranges_checked=dma_ok)
 cache_writes=[4*values[0]if a.retain_stage else 0 for values in counts]
 report.update(expected_CPU_restore_cache_writes=cache_writes,CPU_write_trace_is_restore_cache_only=write_trace==[[n,n]for n in cache_writes],stage_window_epoch_unchanged_required=a.retain_stage,native_epoch_invalidation_bound=False)
 if write_trace!=[[n,n]for n in cache_writes]:ok=False;report['status']='FAIL'
 if not dma_ok:ok=False;report['status']='FAIL'
 if write_covered and any(v[1]for v in write_trace):ok=False;report['status']='FAIL'
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='source_layers'}))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
