"""Compiled palette contexts and native RGB555-to-HIGH/LOW index conversion.

Each admitted pose has a full-screen palette schedule including static OBJ
ownership. Context choice here is a two-pose fixture input, not live allocation.
"""
import json
import hashlib
import struct
import numpy as np
from source_hybrid_scene import derive
from m4_sound_mix_sa1_native import Code


def compile_contexts(source,stage,poses,window,out,direct=False,persistent_actor_high=False):
 x,y,w,h=window;maps=bytearray();pointers=bytearray();expected=[];decoders=[];reports=[];unique={};assignment_cache={}
 words=np.arange(32768,dtype=np.uint16)
 keys=(words&31)|((words&0x3c0)>>1)|((words&0x7800)>>2)
 for phase,pose in enumerate(poses):
  r,a=derive(source,stage,pose,3,promoted_windows=[window],persistent_actor_high=persistent_actor_high,
   fixed_background_policy='scanline_live'if persistent_actor_high else'whole_frame',
   retain_full_actor_art=persistent_actor_high,assignment_cache=assignment_cache)
  if a is None:raise ValueError('COMPILED_WINDOW_PALETTE_CONTEXT_UNPROVEN')
  folder=out/('palette-context-%d'%phase);folder.mkdir(exist_ok=True)
  (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n')
  state=[0]*256
  for v in r['bg_schedule']['initial']:state[v['slot']]=v['color'] or 0
  updates={v['scanline']:v for v in r['bg_schedule']['trace']};rows=[]
  for line in range(224):
   if line in updates:
    v=updates[line];state[v['cgram_start']:v['cgram_start']+len(v['values'])]=[c or 0 for c in v['values']]
   if y<=line<y+h:
    lut=np.zeros(8192,dtype=np.uint8)
    for word,index in zip(a['bg'][line,x:x+w],a['high'][line,x:x+w]):
     key=(int(word)&31)|((int(word)&0x3c0)>>1)|((int(word)&0x7800)>>2)
     if lut[key] not in (0,int(index)):raise ValueError('HIGH_COMPONENT_MAPPING_CONFLICT')
     lut[key]=index
    if direct:
     digest=hashlib.sha256(lut.tobytes()).digest()
     if digest not in unique:unique[digest]=len(maps);maps.extend(lut[keys].tobytes())
     offset=unique[digest];pointers.extend((0xe00000+offset%0x100000).to_bytes(3,'little')+bytes([2+offset//0x100000]))
    else:pointers.extend(struct.pack('<I',0xe00000+len(maps)));maps.extend(lut.tobytes())
    rows.append(list(state))
  pairs=np.stack((a['high'][y:y+h,x:x+w],a['low'][y:y+h,x:x+w]),axis=-1).astype(np.uint8)
  expected.append(pairs.tobytes());decoders.append(np.array(rows,dtype=np.uint16));reports.append(r)
 if len(maps)>(0x600000 if direct else 0x200000) or len(pointers)>0x1000:raise ValueError('WINDOW_PALETTE_MAP_ROM_CAPACITY')
 return bytes(maps),bytes(pointers),expected,decoders,reports


def decode(data,rows,w,h):
 p=np.frombuffer(data,dtype=np.uint8).reshape(h,w,2)
 if np.any(p[:,:,1]>3):raise ValueError('NATIVE_LOW_COMPONENT_INDEX_RANGE')
 return (np.take_along_axis(rows,p[:,:,0],axis=1)+np.array([0,32,1024,1056],dtype=np.uint16)[p[:,:,1]]).astype('<u2').tobytes()


def prefill(maps,pointers,background,w,h):
 """Compiler indices for stage-only pixels; actor-covered holes may be zero.

Zero holes are overwritten by source spans before publication. Native output
is still compared with the complete admitted pose, including these positions.
"""
 words=np.frombuffer(background,dtype='<u2').reshape(h,w);result=[]
 for phase in range(2):
  indices=np.zeros((h,w,2),dtype=np.uint8)
  for row in range(h):
   at=(phase*h+row)*4;pointer=int.from_bytes(pointers[at:at+3],'little');mapper=pointers[at+3]
   start=(mapper-2)*0x100000+pointer-0xe00000
   lut=np.frombuffer(maps[start:start+32768],dtype=np.uint8)
   indices[row,:,0]=lut[words[row]];indices[row,:,1]=((words[row]>>5)&1)|(((words[row]>>10)&1)<<1)
  result.append(indices.tobytes())
 return result


def sparse_kernel(w,h,return_entry):
 """ROM worker plus five-byte IRAM lookup; visit visible producer spans once."""
 c=Code(0xa000);c.emit('e2 20 a9 42 48 ab c2 30 a9 00 00 a2 00 00')
 c.label('clear');c.emit('9d 00 d2 e8 e8');c.word(0xe0,(w*h+7)//8+2);c.branch(0x90,'clear')
 c.emit('64 04 64 32 a9 00 00 a5 16');c.branch(0xf0,'phase');c.word(0xa9,h*4);c.label('phase');c.emit('85 2a a5 18');c.branch(0xd0,'span');c.jump('done')
 c.label('span');c.emit('a6 04 bd 00 60 a8 bd 02 60 4a 85 2c e2 20 a9 01 8f 50 22 00 c2 20 98 8f 51 22 00');c.word(0xa9,w*2);c.emit('8f 53 22 00'+' ea'*16+' af 06 23 00 0a 0a 18 65 2a aa bf 00 80 c3 8f 01 37 00 e2 20 bf 02 80 c3 8f 03 37 00 bf 03 80 c3 85 30 cf e9 3f 41');c.branch(0xf0,'mapped');c.emit('8f e8 3f 41');c.label('map_wait');c.emit('af e9 3f 41 c5 30');c.branch(0xd0,'map_wait');c.label('mapped');c.emit('c2 20')
 c.label('pixel');c.emit('98 29 0e 00 aa bf 00 80 df 85 26 98 4a 4a 4a 4a aa bd 00 d2 25 26');c.branch(0xd0,'skip');c.emit('bd 00 d2 05 26 9d 00 d2 e2 20 be 00 70 22 00 37 00');c.branch(0xd0,'valid');c.jump('fault');c.label('valid');c.emit('99 00 70 bf 00 00 df c8 99 00 70 c8 c2 20 e6 32');c.branch(0x80,'next_pixel');c.label('skip');c.emit('c8 c8');c.label('next_pixel');c.emit('c6 2c');c.branch(0xd0,'pixel');c.emit('a5 04 18 69 04 00 85 04 c5 18');c.branch(0xf0,'done');c.jump('span')
 c.label('done');c.emit('a5 32 8f e6 3f 41 a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');c.label('fault');c.emit('c2 20 a9 ae b4 8f f0 3f 41');c.jump('stop')
 entries={n:0x010000+c.base+c.labels[n]for n in('phase','done','fault')};entries['phase']=0x010000+c.base
 return c.finish(),entries


def sparse_trace(descriptors,origins,moving_actor,move_x,pointers,w,h):
 trace=[];counts=[]
 for phase in range(2):
  occupied=np.zeros((h,w),dtype=bool)
  for at in range(0,len(descriptors),16):
   row,left,length,actor=struct.unpack_from('<4H',descriptors,at);ox,oy=struct.unpack_from('<hh',origins,actor)
   if phase and actor==moving_actor*4:ox+=move_x
   line=row+oy;start=max(0,left+ox);end=min(w,left+ox+length)
   if not 0<=line<h or start>=end:continue
   mapper=pointers[(phase*h+line)*4+3]
   if not trace or trace[-1][0]!=mapper:trace.append([mapper,mapper])
   occupied[line,start:end]=True
  counts.append(int(np.count_nonzero(occupied)))
 return trace,counts


def bitmap_kernel(w,h,return_entry,iram=False):
 """Merge dirty span ranges into a bitset, then walk each dirty pixel once."""
 if w%8:raise ValueError('BITMAP_CONVERTER_TILE_WINDOW_REQUIRED')
 c=Code(0x3040 if iram else 0xa000);c.emit('e2 20 a9 42 48 ab c2 30 a9 00 00 a2 00 00')
 c.label('clear');c.emit('9d 00 d2 e8 e8');c.word(0xe0,(w*h+7)//8+2);c.branch(0x90,'clear')
 c.emit('64 04 64 32 a5 18');c.branch(0xd0,'mark_span');c.jump('marked')
 c.label('mark_span');c.emit('a6 04 bd 02 60 4a 85 2c bd 00 60 4a 48 29 07 00 85 34 a9 08 00 38 e5 34 c5 2c');c.branch(0x90,'partial_ready');c.emit('a5 2c');c.label('partial_ready');c.emit('85 38 a5 2c 38 e5 38 85 2c 68 4a 4a 4a 85 3a a5 34 0a 0a 0a 0a 0a 18 65 38 65 38 aa bf 00 81 df a6 3a 1d 00 d2 9d 00 d2 e8 86 3a')
 c.label('whole_byte');c.emit('a5 2c c9 08 00');c.branch(0x90,'tail');c.emit('38 e9 08 00 85 2c e2 20 a9 ff 9d 00 d2 c2 20 e8 86 3a');c.jump('whole_byte')
 c.label('tail');c.emit('0a aa bf 00 82 df a6 3a 1d 00 d2 9d 00 d2 a5 04 18 69 04 00 85 04 c5 18');c.branch(0xf0,'marked');c.jump('mark_span')
 c.label('marked');c.emit('a9 00 00 a5 16');c.branch(0xf0,'phase');c.word(0xa9,h*4);c.label('phase');c.emit('85 28 64 3a a0 00 00');c.word(0xa9,h);c.emit('85 2a')
 c.label('row');c.emit('a6 28 bf 00 80 c3 8f 01 37 00 e2 20 bf 02 80 c3 8f 03 37 00 bf 03 80 c3 85 30 cf e9 3f 41');c.branch(0xf0,'mapped');c.emit('8f e8 3f 41');c.label('map_wait');c.emit('af e9 3f 41 c5 30');c.branch(0xd0,'map_wait');c.label('mapped');c.emit('c2 20');c.word(0xa9,w//8);c.emit('85 38')
 c.label('byte');c.emit('a6 3a e2 20 bd 00 d2 85 34');c.branch(0xd0,'bits');c.emit('c2 20 98 18 69 10 00 a8');c.jump('next_byte')
 c.label('bits');c.emit('a9 08 85 36');c.label('bit');c.emit('46 34');c.branch(0x90,'skip');c.emit('be 00 70 22 00 37 00');c.branch(0xd0,'valid');c.jump('fault');c.label('valid');c.emit('99 00 70 bf 00 00 df c8 99 00 70 c8 c2 20 e6 32 e2 20');c.branch(0x80,'next_bit');c.label('skip');c.emit('c8 c8');c.label('next_bit');c.emit('c6 36');c.branch(0xd0,'bit');c.emit('c2 20')
 c.label('next_byte');c.emit('e6 3a c6 38');c.branch(0xd0,'byte');c.emit('a5 28 18 69 04 00 85 28 c6 2a');c.branch(0xf0,'done');c.jump('row')
 c.label('done');c.emit('a5 32 8f e6 3f 41 a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');c.label('fault');c.emit('c2 20 a9 ae b4 8f f0 3f 41');c.jump('stop')
 worker=c.finish()
 if iram and c.base+len(worker)>0x3200:raise ValueError('BITMAP_CONVERTER_PRODUCER_IRAM_OVERLAP')
 return worker,{n:(0 if iram else 0x010000)+c.base+(0 if n=='phase'else c.labels[n])for n in('phase','done','fault')}


def kernel(w,h,return_entry,direct=False):
 c=Code(0x3700);c.emit('e2 20 a9 42 48 ab c2 30 a0 00 00 a2 00 00 a5 16');c.branch(0xf0,'phase');c.word(0xa2,h*4);c.label('phase');c.emit('86 28');c.word(0xa9,h);c.emit('85 2a')
 c.label('row');c.emit('a6 28 bf 00 80 c3 8f 00 00 00');lo=len(c.data)-3;c.emit('e2 20 bf 02 80 c3 8f 00 00 00');bank=len(c.data)-3
 if direct:
  c.emit('bf 03 80 c3 85 2e cf e9 3f 41');c.branch(0xf0,'mapped');c.emit('8f e8 3f 41');c.label('map_wait');c.emit('af e9 3f 41 c5 2e');c.branch(0xd0,'map_wait');c.label('mapped')
 c.emit('c2 20');c.word(0xa9,w);c.emit('85 2c')
 c.label('pixel');c.emit('e2 20 be 00 70'if direct else'b9 00 70 85 24 29 1f 00 85 26 a5 24 29 c0 03 4a 05 26 85 26 a5 24 29 00 78 4a 4a 05 26 aa e2 20')
 c.label('lookup');c.emit('bf 00 00 e0');c.branch(0xd0,'valid');c.jump('fault');c.label('valid');c.emit('99 00 70')
 if direct:c.emit('bf 00 00 df c8 99 00 70 c8 c2 20 c6 2c')
 else:c.emit('c2 20 a5 24 29 20 00 4a 4a 4a 4a 4a 85 26 a5 24 29 00 04'+' 4a'*9+' 05 26 e2 20 c8 99 00 70 c8 c2 20 c6 2c')
 c.branch(0xd0,'pixel');c.emit('a5 28 18 69 04 00 85 28 c6 2a');c.branch(0xd0,'row')
 c.label('done');c.emit('a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');c.label('fault');c.emit('c2 20 a9 ae b4 8f f0 3f 41');c.jump('stop')
 worker=bytearray(c.finish());worker[lo:lo+3]=(c.base+c.labels['lookup']+1).to_bytes(3,'little');worker[bank:bank+3]=(c.base+c.labels['lookup']+3).to_bytes(3,'little')
 if c.base+len(worker)>0x37d0:raise ValueError('WINDOW_INDEX_KERNEL_STACK_OVERLAP')
 return bytes(worker),{n:c.base+c.labels[n]for n in('phase','done','fault')}
