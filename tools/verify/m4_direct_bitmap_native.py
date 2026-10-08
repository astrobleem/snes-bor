"""One-pass opaque source spans and exact SCREEN into lossless BG bitmaps."""
import json
import hashlib
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from m4_sound_mix_sa1_native import Code
from m4_underlay_spans_sa1_native import build
from m4_window_characters import expected_bitmap,sparse_bitmap_tables,type1_service,expected as expected_chr
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact


def selected_tiles(data,w,h,mask,bitmap=True):
 from sa1_character_conversion import bitmap_bytes
 from bg_component_residency import encode
 pixels=np.frombuffer(data,np.uint8).reshape(h,w,2)
 result=[]
 for plane,bpp in((0,8),(1,2)):
  tiles=np.array([pixels[y:y+8,x:x+8,plane]for y in range(0,h,8)for x in range(0,w,8)if mask[y//8,x//8]])
  result.append(bitmap_bytes(tiles,bpp,1)if bitmap else b''.join(encode(tile,bpp)for tile in tiles))
 return b''.join(result)


def covered_source_pixels(descriptors,origins,mask,w,h):
 count=0
 for at in range(0,len(descriptors),16):
  row,left,length,origin,pointer=struct.unpack_from('<HHHHI',descriptors,at);ox,oy=struct.unpack_from('<hh',origins,origin);y=row+oy
  if not 0<=y<h:continue
  for x in range(max(0,left+ox),min(w,left+ox+length)):
   count+=int(mask[y//8,x//8])
 return count


def row_kernel(w,h,tile_count=None):
 low_base=(tile_count*64)if tile_count is not None else w*h
 c=Code(0x3500);c.emit('a5 08 85 60 a5 1a 85 62 a5 0c 85 64 e2 20 a5 0e 85 66 a5 16 18 69 c6');patches=[]
 for name in('map_bank','map_pointer'):
  c.emit('8f 00 00 00');patches.append((len(c.data)-3,name))
 c.emit('c2 20')
 c.label('pixel')
 if tile_count is not None:
  c.emit('a6 62 e2 20 bf 00 00 cf');c.branch(0xd0,'promoted');c.emit('c2 20');c.jump('advance');c.label('promoted');c.emit('c2 20')
 c.emit('a5 62 0a aa e2 20');c.label('map_bank');c.emit('bf 02 00 c6');c.branch(0xf0,'plain');c.emit('85 6c c2 20');c.label('map_pointer');c.emit('bf 00 00 c6 85 6a a7 64 a8 b7 6a');c.branch(0xd0,'admitted');c.jump('fault');c.label('admitted');c.emit('85 70');c.branch(0x80,'packed')
 c.label('plain');c.emit('a5 66 18 69 04 85 66 c2 20 a7 64 85 70 e2 20 a5 66 38 e9 04 85 66 c2 20')
 c.label('packed');c.emit('a6 62 bf 00 00 ce a8 e2 20 a5 70 99 00 00 c2 20 98 29 03 00 85 72 0a 0a 85 74 a5 70 eb 29 03 00 05 74 aa e2 20 bf 00 80 ce 85 74 c2 20 98 4a 4a a8 a6 72 e2 20 bf 10 80 ce');c.word(0x39,low_base);c.emit('05 74');c.word(0x99,low_base);c.emit('c2 20');c.label('advance');c.emit('a5 64 18 69 02 00 85 64');c.branch(0x90,'source_advanced');c.emit('e2 20 e6 66 c2 20');c.label('source_advanced');c.emit('e6 62 e6 62 c6 60');c.branch(0xf0,'done');c.jump('pixel');c.label('done');c.emit('6b');c.label('fault');c.emit('a9 ae b4 8f f0 3f 41');c.label('stop');c.jump('stop')
 code=bytearray(c.finish())
 for at,name in patches:code[at:at+3]=(c.base+c.labels[name]+3).to_bytes(3,'little')
 if c.base+len(code)>0x3600:raise ValueError('DIRECT_BITMAP_TYPE1_IRAM_BUFFER_OVERLAP')
 return bytes(code),{n:c.base+c.labels[n]for n in('pixel','done','fault')}


def run(a,out,bg,descriptors,pixels,origins,actors,moving,window,contexts,canvases,actor_indices,tables,maps,epoch):
 x,y,w,h=window
 if actor_indices[0]!=actor_indices[1]:raise ValueError('DIRECT_BITMAP_FIXED_ACTOR_INDEX_CONTRACT')
 mask=np.ones((h//8,w//8),bool)
 if a.effect_tile_direct:
  masks=[np.fromfile(out/('palette-context-%d/promoted.bin'%i),np.bool_).reshape(28,32)[y//8:(y+h)//8,x//8:(x+w)//8]for i in range(2)]
  if not np.array_equal(*masks):raise ValueError('DIRECT_BITMAP_TILE_MASK_EPOCH_CHANGED')
  mask=masks[0]
 tile_count=int(mask.sum());bitmap_bytes=tile_count*80;high_bytes=tile_count*64;low_bytes=tile_count*16
 ppu_boot=None;high_target=0;low_target=0x4000
 if a.ppu_scene:
  from m4_native_window_ppu import compile_boot
  ppu_boot=compile_boot(out/'palette-context-1',window,a.effect_tile_direct)
  high_target=ppu_boot['resources']['native_window_HIGH_VRAM'];low_target=49152
 baseline=b''.join(selected_tiles(v,w,h,mask)for v in canvases)
 worker,row_entries=row_kernel(w,h,tile_count if a.effect_tile_direct else None)
 rom,entries,producer=build(bg,descriptors,pixels,origins,w,h,expected_context_epoch=epoch,
     bitmap_row_target=0x3500,bitmap_baselines=baseline,bitmap_actor_indices=actor_indices[0],notify_cpu=a.idle_direct_cpu,bitmap_tile_count=tile_count)
 rom=bytearray(rom)+bytearray([255])*1048576
 rom[0x9c00:0x9c00+len(worker)]=worker
 for at,data in((0x60000,maps[0]),(0x70000,maps[1]),(0x100000,tables)):
  rom[at:at+len(data)]=data
 offsets,masks=sparse_bitmap_tables(w,h);rom[0xe0000:0xe0000+len(offsets)]=offsets;rom[0xe8000:0xe8000+len(masks)]=masks
 if a.effect_tile_direct:
  yy,xx=np.indices((h,w));rank=np.cumsum(mask.flat).reshape(mask.shape)-1;active=mask[yy//8,xx//8];offset=rank[yy//8,xx//8]*64+(yy%8)*8+xx%8
  offsets=np.where(active,offset,65535).astype('<u2').tobytes();flags=active.astype('<u2').tobytes()
  rom[0xe0000:0xe0000+len(offsets)]=offsets;rom[0xf0000:0xf0000+len(flags)]=flags
 main=bytearray(rom[0x8000:0x8400]);main=main[:main.index(bytes([255])*32)]
 extra=bytes.fromhex('e2 20 a2 00 00 bf 00 9c 01 9f 00 35 00 e8 e0')+struct.pack('<H',len(worker))+bytes.fromhex('d0 f2')
 at=main.index(bytes.fromhex('bf 00 90 01'))-3;main[at:at]=extra;main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(extra))
 initial=bytes.fromhex('9c 00 00 9c 02 00 9c f0 30 9c f1 30');main[11:11]=initial;main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(initial))
 if a.idle_direct_cpu:
  loop=struct.unpack('<H',main[-2:])[0];main[-7:]=bytes.fromhex('cb 22 00 c0 01 a9 80 8d 02 22 4c')+struct.pack('<H',loop)
  setup=bytes.fromhex('a9 80 8d 01 22');at=main.index(bytes.fromhex('a9 00 8d 03 22'));main[at:at]=setup;main[-2:]=struct.pack('<H',loop+len(setup))
 else:main[-7:-7]=bytes.fromhex('22 00 c0 01')
 service,vram_entries,vram_desc=type1_service(w,h,high_target,low_target,tile_count);rom[0xc000:0xc000+len(service)]=service
 if ppu_boot:
  rom[0xa0000:0xd0000]=ppu_boot['data'];rom[0xd000:0xd000+len(ppu_boot['code'])]=ppu_boot['code'];rom[0xe000:0xe000+len(ppu_boot['irq'])]=ppu_boot['irq'];rom[0x100:0x104]=bytes.fromhex('5c 00 e0 01');rom[0x7fee:0x7ff0]=struct.pack('<H',0x8100)
  main[-3:-3]=bytes.fromhex('ad 02 00 c9 02 d0 04 5c 00 d0 01')
 rom[0x8000:0x8400]=main+bytes([255])*(1024-len(main));path=out/'proof.sfc';path.write_bytes(rom)
 observer='local regs={};local active=false;local writes=0;local bad=0;local dmas=0;local dmaBytes=0;local dmaBad=0\n'
 observer+=f"emu.addMemoryCallback(function(a,v)if active then writes=writes+1;if a>={0x420000+bitmap_bytes} then bad=bad+1 end end end,emu.callbackType.write,0x420000,0x426000,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 observer+=f"emu.addMemoryCallback(function(a,v)regs[a]=v;if active and a==0x2237 and regs[0x2230]==0x84 then local dst=(regs[0x2235]or 0)+(regs[0x2236]or 0)*256+v*65536;local n=(regs[0x2238]or 0)+(regs[0x2239]or 0)*256;dmas=dmas+1;dmaBytes=dmaBytes+n;if dst~=0x20000 or n~={bitmap_bytes} then dmaBad=dmaBad+1 end end end,emu.callbackType.write,0x2230,0x2239,emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 for name,address in entries.items():
  extra="active=true;writes=0;bad=0;dmas=0;dmaBytes=0;dmaBad=0"if name=='entry'else"active=false;emu.log('DIRECTBOUNDS|'..writes..'|'..bad..'|'..dmas..'|'..dmaBytes..'|'..dmaBad)"if name=='done'else''
  observer+=f"emu.addMemoryCallback(function()emu.log('DIRECTJOB|{name}|'..emu.getState().masterClock);{extra} end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 for name,address in vram_entries.items():observer+=f"emu.addMemoryCallback(function()emu.log('DIRECTVRAM|{name}|'..emu.getState().masterClock)end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,emu.memType.snesMemory)\n"
 if ppu_boot:
  observer+='local ppuActive=false;local ppuFrames=0;local ppuRestore=false;local ppuRows={};local ppuOam={};local ppuClocks={}\n'
  observer+="emu.addMemoryCallback(function(a,v)ppuRestore=v==1 end,emu.callbackType.write,0,0,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addMemoryCallback(function(a,v)if v==15 then ppuActive=true end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addMemoryCallback(function(a,v)if ppuActive and ppuFrames==1 and not ppuRestore then ppuRows[#ppuRows+1]=string.format('%04x:%02x',a,v);if #ppuRows%31==2 or #ppuRows%31==0 then local s=emu.getState();ppuClocks[#ppuClocks+1]=(s.masterClock+4*(s['ppu.frameCount']//2))%1364 end end end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addMemoryCallback(function(a,v)ppuOam[#ppuOam+1]=string.format('%02x',v)end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)\n"
  observer+="emu.addEventCallback(function()if ppuActive then ppuFrames=ppuFrames+1;emu.log('DIRECTPPUFLAGS|'..emu.read(0x213e,emu.memType.snesMemory));if ppuFrames==2 then emu.log('DIRECTPPUCGRAM|'..table.concat(ppuRows,','));emu.log('DIRECTPPUOAM|'..table.concat(ppuOam,''));emu.log('DIRECTPPUCLOCKS|'..table.concat(ppuClocks,','))end end end,emu.eventType.endFrame)\n"
 lua=out/'observer.lua';lua.write_text(observer)
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 actual=[];vram=[];counts=[];marker=b''
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for phase,target in enumerate((b'\xa1\xb4',b'\xab\xb4')):
   for _ in range(60):
    run_frames_exact(m,1)
    if m.read_memory('SnesMemory',0x7e0002,1)!=bytes([phase+1])or ppu_boot and phase==1 and m.read_memory('SnesMemory',0x7e0003,1)!=b'\x01':continue
    marker=m.read_memory('SnesMemory',0x413ff0,2)
    if marker==target:break
   if marker!=target:raise ValueError('DIRECT_BITMAP_NATIVE_COMPLETION:'+marker.hex())
   actual.append(m.read_memory('SnesMemory',0x420000,bitmap_bytes));vram.append(m.read_memory('SnesVideoRam',high_target,high_bytes)+m.read_memory('SnesVideoRam',low_target,low_bytes));counts.append(struct.unpack('<HH',m.read_memory('SnesMemory',0x413ff6,4)))
   if phase==0:
    offset=moving[0]*4;new_x=struct.unpack_from('<h',origins,offset)[0]+a.move_x;m.write_memory('SnesMemory',0x42d000+offset,struct.pack('<h',new_x).hex());m.write_u16(0x0030f0,1)
  if ppu_boot:
   import shutil
   for _ in range(5):run_frames_exact(m,1)
   shot=m.tool('take_screenshot',{'format':'path'});shutil.copyfile(shot['path'],out/'screenshot.png')
 log=(out/'mesen.log').read_text().splitlines();jobs=[v.split('DIRECTJOB|',1)[1].split('|')for v in log if'DIRECTJOB|'in v];bounds=[[int(n)for n in v.split('DIRECTBOUNDS|',1)[1].split('|')]for v in log if'DIRECTBOUNDS|'in v]
 expected=[selected_tiles(v,w,h,mask)for v in contexts[2]];packed=[selected_tiles(v,w,h,mask,False)for v in contexts[2]]
 masked_counts=[]
 for shift in(0,a.move_x):
  changed=bytearray(origins);offset=moving[0]*4;struct.pack_into('<h',changed,offset,struct.unpack_from('<h',changed,offset)[0]+shift);masked_counts.append(covered_source_pixels(descriptors,changed,mask,w,h))
 expected_bounds=[[2*count,0,1,bitmap_bytes,0]for count in masked_counts]
 clocks=[int(jobs[i+1][1])-int(jobs[i][1])for i in(0,2)]if[v[0]for v in jobs]==['entry','done']*2 else None
 ok=actual==expected and vram==packed and bounds==expected_bounds and clocks is not None
 report=dict(schema='BYOR_DIRECT_SCREEN_BITMAP_NATIVE_V1',status='PASS'if ok else'FAIL',window=window,
     ROM_sha256=hashlib.sha256(rom).hexdigest(),producer_IRAM_bytes=len(producer),row_worker_IRAM_bytes=len(worker),
     bitmap_byte_mismatches=[sum(a!=b for a,b in zip(v,e))for v,e in zip(actual,expected)],VRAM_byte_mismatches=[sum(a!=b for a,b in zip(v,e))for v,e in zip(vram,packed)],
     native_span_and_pixel_counts=counts,write_and_DMA_bounds=bounds,expected_write_and_DMA_bounds=expected_bounds,
     source_effect_tile_mask=a.effect_tile_direct,promoted_native_window_tiles=tile_count,bitmap_bytes=bitmap_bytes,actor_pixels_in_promoted_tiles=masked_counts,
     master_clocks=clocks,milliseconds=[v/21477.27 for v in clocks]if clocks else None,native_bitmap_sha256=[hashlib.sha256(v).hexdigest()for v in actual],
     no_color_reduction=True,alpha_policy='Exact source RGB8 SCREEN before RGB555 conversion',
     SCPU_WAI_during_source_job=a.idle_direct_cpu,source_job_completion_IRQ=a.idle_direct_cpu,production_CPU_contention_admitted=False,
     intermediate_underlay_canvas=False,intermediate_full_index_canvas=False,source_actor_index_atlas_identical=True,
     CHR_publication=ok,native_PPU_scene=False,joint_audio_proven=False,production_memory_lease=False,motu_gameplay_proven=False,
     scope='Native signed clipped source spans directly draw exact SCREEN or opaque indices into compiler stage-baseline bitmaps, then type1 VRAM conversion. Two explicit poses, fixed source art/camera/context; no live world or production deadline admission.')
 if ppu_boot:
  from PIL import Image
  rgb=np.asarray(Image.open(out/'screenshot.png').convert('RGB'),np.uint16);rendered=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10);source=np.frombuffer(ppu_boot['expected'],dtype='<u2').reshape(224,256)
  cg=[v.split('DIRECTPPUCGRAM|',1)[1].split(',')for v in log if'DIRECTPPUCGRAM|'in v];oam=[v.split('DIRECTPPUOAM|',1)[1]for v in log if'DIRECTPPUOAM|'in v];flags=[int(v.split('DIRECTPPUFLAGS|',1)[1])for v in log if'DIRECTPPUFLAGS|'in v];timing=[[int(n)for n in v.split('DIRECTPPUCLOCKS|',1)[1].split(',')]for v in log if'DIRECTPPUCLOCKS|'in v]
  timing_ok=len(timing)==1 and len(timing[0])==448 and not any(88<=c<1096 for c in timing[0]);oam_ok=oam==[(out/'palette-context-1/oam.bin').read_bytes().hex()]
  ppu_ok=rendered.shape==source.shape and np.array_equal(rendered,source)and cg==[ppu_boot['trace']]and oam_ok and bool(flags)and not any(v&192 for v in flags)and timing_ok
  report.update(native_PPU_scene=ppu_ok,PPU_pixel_mismatches=int(np.count_nonzero(rendered!=source))if rendered.shape==source.shape else None,CGRAM_observer_verified=cg==[ppu_boot['trace']],OAM_observer_verified=oam_ok,CGRAM_HBlank_timing_verified=timing_ok,OBJ_status=flags,PPU_resources=ppu_boot['resources'])
  (out/'ppu-observer.json').write_text(json.dumps(dict(CGRAM=cg,OAM=oam,OBJ_status=flags,CGRAM_HBlank_clocks=timing),indent=2)+'\n')
  if not ppu_ok:ok=False;report['status']='FAIL'
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not ok:raise SystemExit(1)
