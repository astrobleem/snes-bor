"""Serialize measured source graphics and real twelve-voice mixing/BRR.

This fixture borrows RAM explicitly. It proves worker handoff, not a production
lease, continuous audio transport, live actor binding or a field deadline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from m4_sound_mix_sa1_native import Code
from _harness import McpSession, MESEN_EXE, _free_tcp_port, run_frames_exact


def substitute(data, before, after, count):
 before=bytes.fromhex(before);after=bytes.fromhex(after)
 if len(before)!=len(after) or data.count(before)!=count:
  raise ValueError('JOINT_WORKER_RELOCATION_CONTRACT:'+before.hex())
 return data.replace(before,after)


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--graphics',type=Path,required=True)
 p.add_argument('--audio',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--reload-workers',action='store_true')
 p.add_argument('--native-actor-index',type=int,default=1)
 p.add_argument('--move-x',type=int,default=-30)
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 gr=json.loads((a.graphics/'report.json').read_text());ar=json.loads((a.audio/'report.json').read_text())
 graphic=(a.graphics/'proof.sfc').read_bytes();audio=(a.audio/'proof.sfc').read_bytes()
 if gr['status']!='PASS' or ar['status']!='PASS' or ar.get('jobs',1)!=1 or ar['active_channels']!=12:
  raise ValueError('JOINT_PROVEN_COMPONENT_DOMAIN')
 if hashlib.sha256(graphic).hexdigest()!=gr['ROM_sha256'] or hashlib.sha256(audio).hexdigest()!=ar['rom_sha256']:
  raise ValueError('JOINT_COMPONENT_ROM_IDENTITY')
 if not gr['native_PPU_scene'] or gr['bitmap_bytes']>0x6000:
  raise ValueError('JOINT_NATIVE_GRAPHICS_DOMAIN')
 rom=bytearray(graphic)+bytearray([255])*(0x400000-len(graphic))
 # Shift immutable audio source and predictor tables to E1..FE. C0..DF
 # remain exactly the graphics image, including SCREEN tables and assets.
 rom[0x210000:0x3f0000]=audio[0x10000:0x1f0000]
 gather=audio[0x9000:0x9000+ar['gather_worker_bytes']]
 gather=substitute(gather,'bf 00 00 c2','bf 00 00 e2',8)
 gather=substitute(gather,'5c 00 a0 01','5c 00 a9 01',1)
 encoder=audio[0x9800:0x9800+ar['encoder_worker_bytes']]
 for before,after in [('a9 c3 85 24','a9 e3 85 24'),('e2 20 a9 c1','e2 20 a9 e1'),
                       ('a9 de','a9 fe'),('bf 00 00 c3','bf 00 00 e3'),
                       ('85 0a 18 69 d1','85 0a 18 69 f1'),('a5 0a 18 69 c4','a5 0a 18 69 e4'),
                       ('a9 ab b4 8f f0 3f 41','a9 b6 b4 8f f0 3f 41')]:
  encoder=substitute(encoder,before,after,1)
 # Keep identical entry/done offsets; replace the encoder's terminal jump.
 if encoder[-3]!=0x4c:raise ValueError('JOINT_ENCODER_STOP_CONTRACT')
 encoder=encoder[:-3]+bytes.fromhex('5c 00 ab 01')
 rom[0xa400:0xa400+len(gather)]=gather;rom[0xa600:0xa600+len(encoder)]=encoder
 producer=bytes(rom[0x9000:0x9000+gr['producer_IRAM_bytes']])
 original_observer=(a.graphics/'observer.lua').read_text()
 entry=int(re.search(r"DIRECTJOB\|entry\|.*?exec,(\d+)",original_observer).group(1))
 continuation=bytes.fromhex('e6 16 4c')+struct.pack('<H',entry)
 if producer.count(continuation)!=1:raise ValueError('JOINT_GRAPHICS_CONTINUATION_CONTRACT')
 producer=producer.replace(continuation,bytes.fromhex('5c 00 a8 01 ea'))
 rom[0x9000:0x9000+len(producer)]=producer
 def code_dma(c,source,size,target=0x3500):
  c.emit('e2 20 a9 00 48 ab a9 80 8d 30 22 a9 20 8d 0b 22 c2 20');c.word(0xa9,source)
  c.emit('8d 32 22 e2 20 a9 c0 8d 34 22 c2 20');c.word(0xa9,size)
  c.emit('8d 38 22');c.word(0xa9,target);c.emit('8d 35 22')
 enter=Code(0xa800);enter.emit('c2 30 e2 20 a9 00 48 ab 8d 30 22 c2 20 a9 b5 b4 8f f0 3f 41 a2 00 00')
 if a.reload_workers:enter.emit('af 16 30 00 8f f2 30 00')
 else:
  enter.label('save');enter.emit('bf 00 30 00 9f 00 e8 41 e8 e8');enter.word(0xe0,0x800);enter.branch(0xd0,'save')
 enter.emit('a2 00 00');enter.label('phases');enter.emit('bf 00 f0 e2 9f 00 50 43 e8 e8');enter.word(0xe0,48);enter.branch(0xd0,'phases')
 code_dma(enter,0xa400,len(gather));enter.emit('5c 00 35 00')
 encode=Code(0xa900);code_dma(encode,0xa600,len(encoder));encode.emit('5c 00 35 00')
 restore=Code(0xab00);restore.emit('c2 30 e2 20 a9 00 48 ab 8d 30 22 c2 20 a2 00 00')
 if a.reload_workers:
  code_dma(restore,0x9000,len(producer),0x3200);code_dma(restore,0x9c00,gr['row_worker_IRAM_bytes']);restore.emit('af f2 30 00 8f 16 30 00')
 else:
  restore.label('restore');restore.emit('bf 00 e8 41 9f 00 30 00 e8 e8');restore.word(0xe0,0x800);restore.branch(0xd0,'restore')
 restore.label('restored');restore.emit('a9 00 30 5b e6 16 5c '+entry.to_bytes(3,'little').hex(' '))
 for c in (enter,encode,restore):
  code=c.finish();rom[c.base:c.base+len(code)]=code
 rom[0x7fd7]=12;path=out/'proof.sfc';path.write_bytes(rom)
 # Original CGRAM/OAM/PPU observer is retained. Audio output is captured
 # before graphics reclaims its BW-RAM bitmap; no host pixel input is used.
 observer=original_observer+'\nlocal audioStage=0;local audioActive=false;local audioPCM=nil\n'
 audio_observer=(a.audio/'observer.lua').read_text()
 points=[]
 for name in ('gather_entry','gather_done','encode_entry','encode_done'):
  address=int(re.search(r'JOINTBRR\|'+name+r'\|.*?exec,(\d+)',audio_observer).group(1));points.append((name,address))
 for i,(name,address)in enumerate(points):
  capture="local bytes={};for j=0,"+str(ar['frames']*2-1)+" do bytes[#bytes+1]=string.format('%02x',emu.read(0x420000+j,emu.memType.sa1Memory))end;emu.log('GRAPHICSAUDIOPCM|'..table.concat(bytes))"if name=='encode_entry'else''
  observer+=f"emu.addMemoryCallback(function()if audioActive and audioStage=={i} then audioStage=audioStage+1;emu.log('GRAPHICSAUDIO|{name}|'..emu.getState().masterClock);{capture} end end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 for name,address in [('handoff',0x01a800),('restore',0x01ab00),('restored',0x010000+restore.base+restore.labels['restored'])]:
  check="local bad=0;for j=0,2047 do if emu.read(0x3000+j,emu.memType.sa1Memory)~=emu.read(0x41e800+j,emu.memType.sa1Memory) then bad=bad+1 end end;emu.log('GRAPHICSRESTORE|'..bad)"if name=='restored'else''
  if a.reload_workers and name=='restored':
   check=f"local bad=0;for j=0,{len(producer)-1} do if emu.read(0x3200+j,emu.memType.sa1Memory)~=emu.read(0x019000+j,emu.memType.sa1Memory) then bad=bad+1 end end;for j=0,{gr['row_worker_IRAM_bytes']-1} do if emu.read(0x3500+j,emu.memType.sa1Memory)~=emu.read(0x019c00+j,emu.memType.sa1Memory) then bad=bad+1 end end;if emu.read(0x3016,emu.memType.sa1Memory)~=0 then bad=bad+1 end;emu.log('GRAPHICSRESTORE|'..bad)"
  activate="audioActive=true;"if name=='handoff'else''
  observer+=f"emu.addMemoryCallback(function(){activate}emu.log('GRAPHICSHANDOFF|{name}|'..emu.getState().masterClock);{check} end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
 lua=out/'observer.lua';lua.write_text(observer)
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 native=[];vram=[];resources=gr['PPU_resources'];high_target=resources['native_window_HIGH_VRAM'];low_target=49152
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for phase in range(2):
   for _ in range(90):
    run_frames_exact(m,1)
    if m.read_memory('SnesMemory',0x7e0002,1)==bytes([phase+1]) and (phase==0 or m.read_memory('SnesMemory',0x7e0003,1)==b'\x01'):break
   else:raise ValueError('JOINT_GRAPHICS_AUDIO_COMPLETION')
   native.append(m.read_memory('SnesMemory',0x420000,gr['bitmap_bytes']));count=gr['promoted_native_window_tiles']
   vram.append(m.read_memory('SnesVideoRam',high_target,count*64)+m.read_memory('SnesVideoRam',low_target,count*16))
   if phase==0:
    address=0x42d000+a.native_actor_index*4;origin=struct.unpack('<h',m.read_memory('SnesMemory',address,2))[0];m.write_memory('SnesMemory',address,struct.pack('<h',origin+a.move_x).hex());m.write_u16(0x0030f0,1)
  brr=m.read_memory('SnesMemory',0x430000,ar['frames']//16*9)
  phases=struct.unpack('<12I',m.read_memory('SnesMemory',0x435000,48))
  for _ in range(5):run_frames_exact(m,1)
  import shutil
  shot=m.tool('take_screenshot',{'format':'path'});shutil.copyfile(shot['path'],out/'screenshot.png')
 log=(out/'mesen.log').read_text().splitlines()
 def events(tag):return [line.split(tag+'|',1)[1].split('|')for line in log if tag+'|'in line]
 ae=events('GRAPHICSAUDIO');he=events('GRAPHICSHANDOFF');ge=events('DIRECTJOB');restore_trace=events('GRAPHICSRESTORE')
 pcm=b''.join(bytes.fromhex(v[0])for v in events('GRAPHICSAUDIOPCM'))
 rgb=np.asarray(Image.open(out/'screenshot.png').convert('RGB'),np.uint16);rendered=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
 expected=np.fromfile(a.graphics/'palette-context-1/expected.bin',dtype='<u2').reshape(224,256)
 pixel_errors=int(np.count_nonzero(rendered!=expected))if rendered.shape==expected.shape else None
 brr_ok=brr==(a.audio/'native.brr').read_bytes();pcm_ok=hashlib.sha256(pcm).hexdigest()==ar['mixed_sha256']
 phase_ok=[phase*c['stride']for phase,c in zip(phases,ar['channels'])]==ar['expected_source_Q12']
 sequence=[v[0]for v in ae]==[v[0]for v in points] and [v[0]for v in he]==['handoff','restore','restored'] and [v[0]for v in ge]==['entry','done']*2
 cg=events('DIRECTPPUCGRAM');oa=events('DIRECTPPUOAM');flags=[int(v[0])for v in events('DIRECTPPUFLAGS')];timing=[int(v)for v in events('DIRECTPPUCLOCKS')[0][0].split(',')]if events('DIRECTPPUCLOCKS')else[]
 original_log=(a.graphics/'mesen.log').read_text().splitlines()
 cg_ok=[v[0]for v in cg]==[v.split('DIRECTPPUCGRAM|',1)[1]for v in original_log if'DIRECTPPUCGRAM|'in v]
 oa_ok=[v[0]for v in oa]==[(a.graphics/'palette-context-1/oam.bin').read_bytes().hex()]
 timing_ok=len(timing)==448 and not any(88<=c<1096 for c in timing)
 # Full bitmap and VRAM identity are compared with the sealed component
 # hashes/independently decoded source image, rather than screenshots alone.
 bitmap_ok=[hashlib.sha256(v).hexdigest()for v in native]==gr['native_bitmap_sha256']
 from m4_direct_bitmap_native import selected_tiles
 x,y,w,h=gr['window'];mask=np.fromfile(a.graphics/'palette-context-1/promoted.bin',np.bool_).reshape(28,32)[y//8:(y+h)//8,x//8:(x+w)//8]
 chr_expected=[]
 for phase in range(2):
  high=np.fromfile(a.graphics/f'palette-context-{phase}/high.bin',np.uint8).reshape(224,256);low=np.fromfile(a.graphics/f'palette-context-{phase}/low.bin',np.uint8).reshape(224,256)
  pairs=np.stack((high[y:y+h,x:x+w],low[y:y+h,x:x+w]),axis=-1).tobytes();chr_expected.append(selected_tiles(pairs,w,h,mask,False))
 vram_ok=vram==chr_expected
 ok=sequence and restore_trace==[['0']] and bitmap_ok and vram_ok and brr_ok and pcm_ok and phase_ok and pixel_errors==0 and cg_ok and oa_ok and timing_ok and bool(flags)and not any(v&192 for v in flags)
 clocks={name:int(clock)for name,clock in ae};handoff={name:int(clock)for name,clock in he}
 if sequence:
  ordered=int(ge[1][1])<handoff['handoff']<clocks['gather_entry']<clocks['gather_done']<clocks['encode_entry']<clocks['encode_done']<handoff['restore']<handoff['restored']<int(ge[2][1])
  ok=ok and ordered
 else:ordered=False
 report=dict(schema='BYOR_SERIALIZED_GRAPHICS_SOURCE_MIX_BRR_NATIVE_V1',status='PASS'if ok else'FAIL',ROM_sha256=hashlib.sha256(rom).hexdigest(),graphics_component_ROM=gr['ROM_sha256'],audio_component_ROM=ar['rom_sha256'],native_bitmap_identity=bitmap_ok,native_VRAM_identity=vram_ok,PPU_pixel_mismatches=pixel_errors,CGRAM_identity=cg_ok,OAM_identity=oa_ok,CGRAM_HBlank_timing_verified=timing_ok,OBJ_status=flags,PCM_identity=pcm_ok,BRR_identity=brr_ok,source_Q12_identity=phase_ok,IRAM_restore_trace=restore_trace,native_event_order_verified=ordered,graphics_events=ge,audio_events=ae,handoff_events=he,active_source_voices=12,output_samples=ar['frames'],audio_output_rate=11025,audio_policy='ACCEPTED_COMPAT mono uniform gain 64 normal pitch',reload_immutable_workers=a.reload_workers,borrowed_IRAM_snapshot=dict(address='0030F2'if a.reload_workers else'41E800',bytes=2 if a.reload_workers else 2048,production_owner='fixture IRAM scratch'if a.reload_workers else'source VM variable pool'),SPC_transport_bound=False,continuous_audio_proven=False,live_actor_source_frame_guard=False,production_memory_lease=False,field_deadline_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,scope='Graphics phase 0 and VRAM publication, native audio gather/mix/BRR, worker state restoration, graphics phase 1 and complete source PPU scene in one ROM. Explicit source poses, not live gameplay.')
 if sequence:
  costs=dict(gather_mix=clocks['gather_done']-clocks['gather_entry'],encode=clocks['encode_done']-clocks['encode_entry'],audio_chain=clocks['encode_done']-clocks['gather_entry'],complete_handoff=handoff['restored']-handoff['handoff'])
  report.update(master_clocks=costs,milliseconds={k:v/21477.27 for k,v in costs.items()})
 (out/'native.brr').write_bytes(brr);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
