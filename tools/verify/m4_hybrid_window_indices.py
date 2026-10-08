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


def compile_contexts(source,stage,poses,window,out,direct=False):
 x,y,w,h=window;maps=bytearray();pointers=bytearray();expected=[];decoders=[];reports=[];unique={}
 words=np.arange(32768,dtype=np.uint16)
 keys=(words&31)|((words&0x3c0)>>1)|((words&0x7800)>>2)
 for phase,pose in enumerate(poses):
  r,a=derive(source,stage,pose,3,promoted_windows=[window])
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
