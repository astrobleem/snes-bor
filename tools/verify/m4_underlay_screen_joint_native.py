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


def shader(descriptors,columns,return_entry,typed_underlay=False):
 c=Code(0x3500);c.emit('c2 30 a9 00 30 5b e2 20 a9 c3 48 ab c2 20 a9 00 70 85 20 e2 20 a9 42 85 22 c2 20')
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
  c.label(name);c.emit('bf 00 00 00 97 20 c8 c8')
 c.label('triples')
 for i in range(3):pixel('pixel'+str(i))
 c.emit('c6 00');c.branch(0xd0,'triples');c.label('tail');c.emit('a5 02');c.branch(0xf0,'next');pixel('tail_pixel');c.emit('c6 02');c.branch(0xd0,'tail');c.label('next');c.emit('a5 04 18 69 08 00 85 04');c.word(0xc9,len(descriptors));c.branch(0xf0,'done');c.jump('group')
 c.label('done');c.emit('a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');c.label('fault');c.emit('a9 ae b4 8f f0 3f 41');c.jump('stop')
 worker=bytearray(c.finish())
 for at,name,delta in patches:worker[at:at+3]=(c.base+c.labels[name]+delta).to_bytes(3,'little')
 if c.base+len(worker)>0x3700:raise ValueError('JOINT_SCREEN_IRAM_CAPACITY')
 return bytes(worker),{n:c.base+c.labels[n]for n in('entry','done','fault')}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--move-actor-index',type=int,default=1);p.add_argument('--move-x',type=int,default=-30);p.add_argument('--retain-stage',action='store_true');p.add_argument('--typed-underlay',action='store_true');a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);catalog=derive(source);scene=json.loads(a.scene.read_text());bg,span_desc,pixels,origins,actors,window=compile_inputs(source,a.stage,scene,catalog);wx,wy,w,h=window
 di={tuple(c):i for i,c in enumerate(catalog['destinations'])};pairs,metadata=source_capture.capture(source,a.stage,scene);samples=pairs.reshape(-1,3,2);effect=next(e for e in catalog['effects']if all(tuple(map(int,c))in e['colors']for c in samples[:,:,0]));si={tuple(c):i for i,c in enumerate(effect['colors'])};table=matrix(effect['colors'],catalog['destinations']);source_ids=[si[tuple(map(int,c))]for c in samples[:,:,0]]
 plane,addresses=capture_plane(source,a.stage,scene,di);vw=scene.get('viewport',[256,224])[0];relative=((addresses//2//vw-wy)*w+(addresses//2%vw-wx))*2
 if np.any(relative<0)or np.any(relative>=w*h*2):raise ValueError('JOINT_EFFECT_GEOMETRY_RANGE')
 groups={}
 for i,index in enumerate(source_ids):groups.setdefault(index,[]).append(i)
 if not groups or table.nbytes>1048576:raise ValueError('JOINT_SCREEN_NONEMPTY_ROM_DOMAIN')
 desc=bytearray();order=[]
 for index,indices in sorted(groups.items()):desc.extend(struct.pack('<IHH',0xd00000+index*effect['columns']*2,len(indices)//3,len(indices)%3));order.extend(indices)
 coordinates=struct.pack('<'+'H'*len(order),*(int(relative[i])for i in order));expected=[];underlays=[]
 for shift in(0,a.move_x):
  pose=json.loads(json.dumps(scene));pose['actors'][a.move_actor_index]['position'][0]+=shift;values,_=source_capture.capture(source,a.stage,pose);s=values.reshape(-1,3,2)
  if not np.array_equal(s[:,:,0],samples[:,:,0]):raise ValueError('JOINT_SOURCE_EPOCH_CHANGED')
  destination=[di[tuple(map(int,c))]for c in s[:,:,1]];expected.append(struct.pack('<'+'H'*len(order),*(int(table[source_ids[i],destination[i]])for i in order)))
  full,_=capture_plane(source,a.stage,pose,di);underlays.append(np.frombuffer(full,dtype='<u2').reshape(scene.get('viewport',[256,224])[::-1])[wy:wy+h,wx:wx+w].tobytes())
 moving=[i for i,v in enumerate(actors)if v[4]['kind'].split(':',1)[1].casefold()==scene['actors'][a.move_actor_index]['model'].casefold()]
 if len(moving)!=1:raise ValueError('JOINT_MOVING_ACTOR_DOMAIN')
 for data in(bg,pixels):validate_opaque_identities(data,effect['columns'])
 rom,entries,span_worker=underlay_build(bg,span_desc,pixels,origins,w,h,a.retain_stage,0x3500);rom=bytearray(rom)+bytearray([255])*1048576;screen_worker,screen_entries=shader(desc,effect['columns'],entries['entry'],a.typed_underlay)
 for at,data in((0x10000,desc),(0x31000,coordinates),(0x9c00,screen_worker),(0x100000,table.tobytes())):rom[at:at+len(data)]=data
 main=bytearray(rom[0x8000:0x8400]);main=main[:main.index(bytes([255])*32)];extra=bytes.fromhex('e2 20 a2 00 00 bf 00 9c 01 9f 00 35 00 e8 e0')+struct.pack('<H',len(screen_worker))+bytes.fromhex('d0 f2')
 main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(extra));at=main.index(bytes.fromhex('bf 00 90 01'))-3;main[at:at]=extra;rom[0x8000:0x8400]=main+bytes([255])*(1024-len(main));rom[0x7fd7]=11
 path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua';all_entries={**{'underlay_'+k:v for k,v in entries.items()},**{'shader_'+k:v for k,v in screen_entries.items()}}
 observer='local regs={};local transfers=0;local bytes=0;local dmaBad=0;local pixels=0;local pixelBad=0\n'
 observer+=f"emu.addMemoryCallback(function(a,v)regs[a]=v;if a==0x2237 and regs[0x2230]==0x84 then local dst=(regs[0x2235] or 0)+(regs[0x2236] or 0)*256+v*65536;local n=(regs[0x2238] or 0)+(regs[0x2239] or 0)*256;if n==0 then n=65536 end;transfers=transfers+1;bytes=bytes+n;if dst<0x20000 or dst+n>{0x20000+w*h*2} then dmaBad=dmaBad+1 end end end,emu.callbackType.write,0x2230,0x2239,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 observer+=f"emu.addMemoryCallback(function(a,v)pixels=pixels+1;if a>={0x427000+len(expected[0])} then pixelBad=pixelBad+1 end end,emu.callbackType.write,0x427000,0x42ffff,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 for n,v in all_entries.items():
  extra='transfers=0;bytes=0;dmaBad=0'if n=='underlay_entry'else"emu.log('JOINTDMA|'..transfers..'|'..bytes..'|'..dmaBad)"if n=='underlay_done'else'pixels=0;pixelBad=0'if n=='shader_entry'else"emu.log('JOINTPIXELS|'..pixels..'|'..pixelBad)"if n=='shader_done'else''
  observer+=f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('JOINTSCREEN|{n}|'..s.masterClock);{extra};end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 lua.write_text(observer)
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 actual=[];actual_underlays=[];counts=[]
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for phase,target in enumerate((b'\xa1\xb4',b'\xab\xb4')):
   for _ in range(60):
    run_frames_exact(m,1);marker=m.read_memory('SnesMemory',0x413ff0,2)
    if marker in(target,b'\xae\xb4'):break
   if marker!=target:raise ValueError('JOINT_NATIVE_SCREEN_COMPLETION')
   actual.append(m.read_memory('SnesMemory',0x427000,len(expected[phase])));actual_underlays.append(m.read_memory('SnesMemory',0x420000,len(underlays[phase])))
   counts.append(struct.unpack('<HH',m.read_memory('SnesMemory',0x413ff6,4)))
   if phase==0:
    offset=moving[0]*4;x=struct.unpack_from('<h',origins,offset)[0]+a.move_x;m.write_memory('SnesMemory',0x425000+offset,struct.pack('<h',x).hex());m.write_u16(0x413ff4,1)
 events=[v.split('JOINTSCREEN|',1)[1].split('|')for v in(out/'mesen.log').read_text().splitlines()if'JOINTSCREEN|'in v];names=['underlay_entry','underlay_done','shader_entry','shader_done']*2;clocks=[int(events[i+3][1])-int(events[i][1])for i in(0,4)]if[v[0]for v in events]==names else None;ok=actual==expected and actual_underlays==underlays and clocks is not None
 report=dict(schema='BYOR_NATIVE_UNDERLAY_SCREEN_JOINT_V1',status='PASS'if ok else'FAIL',opaque_pixels=len(order),underlay_pixels=w*h,RGB555_byte_mismatches=[sum(x!=y for x,y in zip(v,e))for v,e in zip(actual,expected)],underlay_RGB8_identity_byte_mismatches=[sum(x!=y for x,y in zip(v,e))for v,e in zip(actual_underlays,underlays)],master_clocks=clocks,milliseconds=[v/21477.27 for v in clocks]if clocks else None,job_events=events,underlay_worker_IRAM_bytes=len(span_worker),shader_worker_IRAM_bytes=len(screen_worker),retained_stage_window=a.retain_stage,rom_sha256=hashlib.sha256(rom).hexdigest(),table_sha256=hashlib.sha256(table.tobytes()).hexdigest(),source_layers=metadata['layers'],no_color_reduction=True,host_supplied_pixel_inputs=False,native_opaque_actor_composition=True,native_SCREEN_shading=True,native_camera_bound=False,native_palette_allocation=False,CHR_publication=False,joint_audio_proven=False,production_memory_lease=False,motu_gameplay_proven=False,scope='Native clipped opaque spans produce underlay identities consumed directly by native exact RGB8 SCREEN shading. Two mutable actor origins, fixed stage/camera/source frame/layer order. No host pixel input between stages. No palette allocation, CHR publication, live VM, production lease or joint audio deadline admission.')
 for phase,data in enumerate(actual):(out/('effect-%d.rgb555'%phase)).write_bytes(data)
 lines=(out/'mesen.log').read_text().splitlines();traces={label:[[int(n)for n in v.split(label+'|',1)[1].split('|')]for v in lines if label+'|'in v]for label in('JOINTDMA','JOINTPIXELS')}
 expected_dma=[[values[0]+(counts[i-1][0]if a.retain_stage and i else 1),(2*counts[i-1][1]if a.retain_stage and i else len(bg))+2*values[1],0]for i,values in enumerate(counts)]
 observer_ok=traces['JOINTDMA']==expected_dma and traces['JOINTPIXELS']==[[len(v),0]for v in expected]
 report.update(observer_traces=traces,expected_DMA_trace=expected_dma,native_DMA_and_shader_output_bounds_proven=observer_ok,compiled_geometry_sha256=hashlib.sha256(coordinates).hexdigest(),compiled_group_descriptors_sha256=hashlib.sha256(desc).hexdigest(),output_sha256=[hashlib.sha256(v).hexdigest()for v in actual])
 report.update(compiler_opaque_RGB8_identity_contract_checked=True,typed_underlay=a.typed_underlay,per_pixel_destination_guards=not a.typed_underlay,identity_producer='Immutable compiler-checked ROM stage/spans; native clipped copies and restores only',arbitrary_underlay_writes_supported=False)
 if not observer_ok:ok=False;report['status']='FAIL'
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='source_layers'}))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
