"""Compile static surroundings with zero native-window placeholders.

The joined native producer must overwrite the reserved tile slots before display.
This isolated fixture relocates the existing measured Mode4 IRQ renderer.
"""
import json
import struct
from pathlib import Path
import numpy as np
from bg_component_residency import encode
from m4_hybrid_scene_native import prepare
from m4_bg_components_native import compile_rom


def atlas(folder,window):
 x,y,w,h=window;cache=folder/'native-window-atlas';cache.mkdir(exist_ok=True)
 high_start=max(4096,(((folder/'obj_chr.bin').stat().st_size+4095)//4096)*4096)
 counts=[]
 for plane,bpp in(('high',8),('low',2)):
  pixels=np.fromfile(folder/(plane+'.bin'),np.uint8).reshape(224,256)
  data=bytearray(w*h*bpp//8);vocabulary={};tilemap=np.zeros((32,32),dtype='<u2')
  for yy in range(0,224,8):
   for xx in range(0,256,8):
    if x<=xx<x+w and y<=yy<y+h:number=((yy-y)//8)*(w//8)+(xx-x)//8
    else:
     raw=encode(pixels[yy:yy+8,xx:xx+8],bpp)
     if raw not in vocabulary:vocabulary[raw]=len(data)//(bpp*8);data.extend(raw)
     number=vocabulary[raw]
    tilemap[yy//8,xx//8]=number
  if plane=='high':
   promoted=np.fromfile(folder/'promoted.bin',np.bool_).reshape(28,32)
   tilemap[:28]|=promoted.astype(np.uint16)*0x2000
  (cache/(plane+'.chr')).write_bytes(data);(cache/('0-'+plane+'.map')).write_bytes(tilemap.tobytes());counts.append(len(data)//(bpp*8))
 if 49152+counts[1]*16>61440:raise ValueError('NATIVE_WINDOW_PPU_LOW_VRAM_LIMIT')
 high=(cache/'high.chr').read_bytes();highmap=np.fromfile(cache/'0-high.map',dtype='<u2').reshape(32,32)
 boundary=(49152-high_start)//64;tail=((49152+counts[1]*16+63)//64)*64
 if counts[0]>boundary:
  gap=(tail-49152)//64
  numbers=highmap&1023;highmap=np.where(numbers>=boundary,highmap+gap,highmap).astype('<u2')
  high=high[:boundary*64]+bytes(gap*64)+high[boundary*64:]
 if high_start+len(high)>61440:raise ValueError('NATIVE_WINDOW_PPU_HIGH_VRAM_LIMIT')
 (cache/'high.chr').write_bytes(high);(cache/'0-high.map').write_bytes((highmap+high_start//64).astype('<u2').tobytes())
 (cache/'layout.json').write_text(json.dumps(dict(low_chr_vram_base=49152)))
 return cache,counts,high_start


def relocate_code(raw,old_base,new_base,hook=b'',wide=True):
 """Decode the existing fixture's restricted instruction set before relocation."""
 lengths={0x78:1,0x18:1,0xfb:1,0xc2:2,0xe2:2,0xa2:3,0x9a:1,0x8d:3,0xad:3,
          0xf0:2,0xd0:2,0x4c:3,0x58:1,0xe8:1,0x48:1,0x68:1,0x40:1,0xbf:4,0xe0:3,0xb0:2}
 marker=bytes.fromhex('ad 12 42 29 80 f0 f9');at=raw.index(marker)if hook else len(raw)
 out=bytearray();pos=0
 while pos<len(raw):
  op=raw[pos];size=(3 if wide else 2)if op in(0xa9,0x29)else lengths.get(op)
  if size is None:raise ValueError('NATIVE_WINDOW_RELOCATOR_OPCODE:'+hex(op))
  if pos==at:out.extend(hook)
  part=bytearray(raw[pos:pos+size])
  if op in(0xc2,0xe2)and part[1]&32:wide=op==0xc2
  if op==0x4c:
   target=struct.unpack_from('<H',part,1)[0]
   if not old_base<=target<old_base+len(raw):raise ValueError('NATIVE_WINDOW_RELOCATOR_JUMP')
   struct.pack_into('<H',part,1,target-old_base+new_base+(len(hook)if target-old_base>=at else 0))
  if op==0xa9 and size==2 and raw[pos+size:pos+size+3]in(bytes.fromhex('8d 74 43'),bytes.fromhex('8d 04 43')):
   part[1]+=18
  if op==0xbf:part[3]+=18
  out.extend(part);pos+=size
 return bytes(out)


def compile_boot(folder,window):
 source,report,path,inputs=prepare(folder);cache,counts,high_start=atlas(folder,window)
 rom,trace,resources=compile_rom(report,inputs,160,cache_assets=cache,offset_alias='low',
     high_base=0,high_tile_offset=high_start//64,obj_chr=(folder/'obj_chr.bin').read_bytes(),oam=(folder/'oam.bin').read_bytes())
 tail=rom[0x8000:0x8400];code=tail[:tail.index(bytes([255])*32)]
 hook=bytes.fromhex('9c 00 00 22 00 c0 01 a9 01 8d 03 00')
 code=relocate_code(code,0x8000,0xd000,hook)
 irq=rom[0x8400:resources['irq_exit_prg_offset']+1]
 irq=relocate_code(irq,0x8400,0xe000,wide=False)
 resources.update(irq_entry_prg_offset=0xe000,irq_exit_prg_offset=0xe000+len(irq)-1,native_window_tile_counts=counts,native_window_HIGH_VRAM=high_start,native_window_LOW_VRAM=49152,
     native_window_placeholder_bytes=window[2]*window[3]*10//8,static_data_bank_offset=18)
 return dict(code=code,irq=irq,data=rom[0x10000:0x40000],resources=resources,trace=trace,expected=(folder/'expected.bin').read_bytes())
