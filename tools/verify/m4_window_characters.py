"""Native type-2 packing of compiler-indexed BG windows into 8/2bpp CHR.

The consumed underlay window is reused for output. A subsequent composition
must reload it completely. This fixture grants no production memory lease.
"""
import numpy as np
from bg_component_residency import encode
from m4_sound_mix_sa1_native import Code


def expected(data,w,h):
 pixels=np.frombuffer(data,dtype=np.uint8).reshape(h,w,2)
 return b''.join(encode(pixels[y:y+8,x:x+8,plane],bpp)for plane,bpp in((0,8),(1,2))for y in range(0,h,8)for x in range(0,w,8))


def expected_bitmap(data,w,h):
 from sa1_character_conversion import bitmap_bytes
 pixels=np.frombuffer(data,dtype=np.uint8).reshape(h,w,2)
 return b''.join(bitmap_bytes(np.array([pixels[y:y+8,x:x+8,plane]for y in range(0,h,8)for x in range(0,w,8)]),bpp,1)for plane,bpp in((0,8),(1,2)))


def bitmap_kernel(w,h,return_entry,iram=True):
 """Serialize native index words into type-1 tile-column bitmaps, no PPU writes."""
 if w%8 or h%8:raise ValueError('NATIVE_BITMAP_TILE_WINDOW_DOMAIN')
 c=Code(0x3200 if iram else 0xa000);c.emit('c2 30 a9 00 30 5b e2 20 a9 42 48 ab c2 20')
 c.label('entry');c.emit('64 42')
 for plane in(0,1):
  name='high'if plane==0 else'low'
  c.emit('64 40 64 4c');c.word(0xa9,w//8);c.emit('85 44');c.word(0xa9,h//8);c.emit('85 46')
  c.label(name+'_tile');c.emit('a6 40 a4 42 a9 08 00 85 48 e2 20');c.label(name+'_row')
  if plane==0:
   for pixel in range(8):c.emit('bd '+(0x7000+pixel*2).to_bytes(2,'little').hex(' ')+' 99 00 00 c8')
  else:
   for group in range(2):
    c.emit('bd '+(0x7001+group*8+6).to_bytes(2,'little').hex(' '))
    for pixel in(2,1,0):c.emit('0a 0a 1d '+(0x7001+group*8+pixel*2).to_bytes(2,'little').hex(' '))
    c.emit('99 00 00 c8')
  c.emit('c2 20 8a 18');c.word(0x69,w*2);c.emit('aa c6 48');c.branch(0xf0,name+'_packed');c.emit('e2 20');c.jump(name+'_row');c.label(name+'_packed')
  c.emit('84 42 a5 40 18 69 10 00 85 40 c6 44');c.branch(0xf0,name+'_row_done');c.jump(name+'_tile');c.label(name+'_row_done')
  c.word(0xa9,w//8);c.emit('85 44 a5 4c 18');c.word(0x69,w*16);c.emit('85 4c 85 40 c6 46');c.branch(0xf0,name+'_done');c.jump(name+'_tile');c.label(name+'_done')
 c.label('done')
 if iram:c.emit('5c 00 b1 01')
 else:raise ValueError('NATIVE_BITMAP_ROM_COMPLETION_UNBOUND')
 worker=c.finish()
 if c.base+len(worker)>0x3500:raise ValueError('NATIVE_BITMAP_SHADER_IRAM_OVERLAP')
 return worker,{n:c.base+c.labels[n]for n in('entry','done')}


def type1_service(w,h):
 """Forced-blank S-CPU service; exclusively reads BW-RAM through CHR DMA."""
 from sa1_character_conversion import type1_descriptor
 descriptors=[type1_descriptor(0x420000,8,1,w*h//64,0),type1_descriptor(0x420000+w*h,2,1,w*h//64,0x4000)]
 c=Code(0xc000);c.emit('08 da 5a 8b e2 20 a9 00 48 ab af f0 3f 41 c9 a1');c.branch(0xf0,'ready');c.emit('c9 ab');c.branch(0xf0,'ready');c.jump('exit');c.label('ready');c.emit('cd 00 00');c.branch(0xd0,'fresh');c.jump('exit');c.label('fresh');c.emit('8d 00 00 a9 80 8d 15 21')
 for i,d in enumerate(descriptors):
  for address,value in((0x2231,d['cdma']),(0x2232,d['source']&255),(0x2233,(d['source']>>8)&255),(0x2234,d['source']>>16),(0x2235,d['iram']&255),(0x2236,d['iram']>>8)):
   c.emit('a9 '+bytes([value]).hex()+' 8d '+address.to_bytes(2,'little').hex(' '))
  c.label('wait%d'%i);c.emit('ad 00 23 29 20');c.branch(0xf0,'wait%d'%i);c.emit('a9 20 8d 02 22 c2 20');c.word(0xa9,d['vram_word_address']);c.emit('8d 16 21 a9 01 18 8d 70 43 a9 42 00 8d 74 43');c.word(0xa9,d['source']&65535);c.emit('8d 72 43');c.word(0xa9,d['bytes']);c.emit('8d 75 43 e2 20 a9 80');c.label('dma%d'%i);c.emit('8d 0b 42 ea');c.label('done%d'%i);c.emit('a9 80 8d 31 22')
 c.emit('ad 00 00 c9 a1');c.branch(0xd0,'second');c.emit('a9 01');c.branch(0x80,'publish');c.label('second');c.emit('a9 02');c.label('publish');c.emit('8d 02 00');c.label('exit');c.emit('ab 7a fa 28 6b')
 return c.finish(),{n:0x010000+c.base+c.labels[n]for n in('dma0','done0','dma1','done1')},descriptors


def kernel(w,h,return_entry,iram=False):
 if w%8 or h%8:raise ValueError('NATIVE_CHR_TILE_WINDOW_DOMAIN')
 c=Code(0x3200 if iram else 0xa000);c.emit('c2 30 a9 00 30 5b e2 20 a9 42 48 ab c2 20')
 c.label('entry');c.emit('64 42')
 for plane,bpp,fmt in((0,8,0),(1,2,2)):
  label='high'if plane==0 else'low'
  c.emit('64 40 64 48 64 4c');c.word(0xa9,w//8);c.emit('85 44');c.word(0xa9,h//8);c.emit('85 46 e2 20 a9 00 8f 30 22 00 a9 a0 8f 30 22 00');c.emit('a9 '+bytes([fmt]).hex()+' 8f 31 22 00 a9 00 8f 35 22 00 a9 36 8f 36 22 00 c2 20')
  c.label(label+'_tile');c.emit('a6 40 a0 04 00 e2 20');c.label(label+'_rows')
  for start in(0x2240,0x2248):
   for pixel in range(8):c.emit('bd '+(0x7000+plane).to_bytes(2,'little').hex(' ')+' 8f '+(start+pixel).to_bytes(3,'little').hex(' ')+' e8 e8')
   c.emit('c2 20 8a 18');c.word(0x69,w*2-16);c.emit('aa e2 20')
  c.emit('88');c.branch(0xf0,label+'_packed');c.jump(label+'_rows');c.label(label+'_packed')
  # Preserve the type-2 row counter while normal DMA copies its completed tile.
  c.emit('a9 86 8f 30 22 00 c2 20 a5 48 29 01 00'+' 0a'*(6 if bpp==8 else 4)+' 18 69 00 36 8f 32 22 00 a5 42 8f 35 22 00');c.word(0xa9,bpp*8);c.emit('8f 38 22 00 e2 20 a9 00 8f 34 22 00 a9 02 8f 37 22 00 a9 00 8f 35 22 00 a9 36 8f 36 22 00 a9 a0 8f 30 22 00 c2 20 a5 42 18');c.word(0x69,bpp*8);c.emit('85 42 e6 48 a5 40 18 69 10 00 85 40 c6 44');c.branch(0xf0,label+'_row_done');c.jump(label+'_tile');c.label(label+'_row_done')
  c.word(0xa9,w//8);c.emit('85 44 a5 4c 18');c.word(0x69,w*16);c.emit('85 4c 85 40 c6 46');c.branch(0xf0,label+'_done');c.jump(label+'_tile');c.label(label+'_done')
 c.emit('e2 20 a9 00 8f 30 22 00 c2 20');c.label('done')
 if iram:c.emit('5c 00 b1 01')
 else:
  c.emit('a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop')
 worker=c.finish()
 if len(worker)>4096:raise ValueError('NATIVE_CHR_WORKER_ROM_CAPACITY')
 if iram and c.base+len(worker)>0x3500:raise ValueError('NATIVE_CHR_SHADER_IRAM_OVERLAP')
 return worker,{n:(0 if iram else 0x010000)+c.base+c.labels[n]for n in('entry','done')}


def swaps(character_bytes,producer_bytes,return_entry,type1=False):
 def transfer(c,source,size):
  c.emit('e2 20 a9 80 8f 30 22 00 a9 01 8f 34 22 00 c2 20');c.word(0xa9,source);c.emit('8f 32 22 00');c.word(0xa9,size);c.emit('8f 38 22 00 a9 00 32 8f 35 22 00')
 enter=Code(0xb000);transfer(enter,0xa000,character_bytes);enter.emit('5c 00 32 00')
 leave=Code(0xb100);transfer(leave,0x9000,producer_bytes)
 if type1:leave.emit('e2 20 a9 b0 8f 30 22 00 c2 20')
 leave.label('done');leave.emit('a5 16');leave.branch(0xd0,'final');leave.emit('a9 a1 b4 8f f0 3f 41');leave.label('wait');leave.emit(('af f0 30 00'if type1 else'af f4 3f 41')+' c9 01 00');leave.branch(0xd0,'wait');leave.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));leave.label('final');leave.emit('a9 ab b4 8f f0 3f 41');leave.label('stop');leave.jump('stop')
 return enter.finish(),leave.finish(),0x010000+leave.base+leave.labels['done']
