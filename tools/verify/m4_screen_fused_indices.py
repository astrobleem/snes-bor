"""Fuse source SCREEN and BG palette admission into compiler lookup rows."""
import struct
import numpy as np
from m4_sound_mix_sa1_native import Code


def actor_indices(words,contexts):
 result=[]
 for report in contexts:
  mapping={v['color']:v['slot']for v in report['persistent_actor_high_slots']}
  initial={v['slot']:v['color']or 0 for v in report['bg_schedule']['initial']}
  if any(initial[slot]!=color for color,slot in mapping.items()):raise ValueError('PERSISTENT_ACTOR_HIGH_INITIAL_IDENTITY')
  for update in report['bg_schedule']['trace']:
   for offset,color in enumerate(update['values']):
    slot=update['cgram_start']+offset
    if slot in mapping.values()and color!=initial[slot]:raise ValueError('PERSISTENT_ACTOR_HIGH_SLOT_OVERWRITTEN')
  values=[]
  for word in np.frombuffer(words,dtype='<u2'):
   color=int(word);slot=mapping.get(color&0x7bdf)
   if slot is None:raise ValueError('PERSISTENT_ACTOR_HIGH_DOMAIN_MISSING')
   values.append(slot|((((color>>5)&1)|(((color>>10)&1)<<1))<<8))
  result.append(np.array(values,dtype='<u2').tobytes())
 return result


def maps_for_groups(groups,addresses,window):
 x,y,w,h=window;result=[]
 relative=((addresses//2//256-y)*w+addresses//2%256-x)*2
 if np.any(relative<0)or np.any(relative>=w*h*2):raise ValueError('FUSED_SOURCE_GEOMETRY_DOMAIN')
 for phase in groups:
  data=bytearray(w*h*4)
  for group in phase:
   for position in group['positions']:struct.pack_into('<I',data,int(relative[position])*2,0xd00000+group['table_offset'])
  result.append(bytes(data))
 return result


def shader(return_entry):
 c=Code(0x3500);c.emit('c2 30 a9 00 30 5b e2 20 a9 42 48 ab c2 20')
 c.label('entry');c.emit('64 04 64 12 e2 20 a5 16 18 69 c6');patches=[]
 for name in('map_bank','map_pointer'):
  c.emit('8f 00 00 00');patches.append((len(c.data)-3,name))
 c.emit('c2 20 a5 18');c.branch(0xd0,'span');c.jump('done')
 c.label('span');c.emit('a6 04 bd 00 60 85 00 bd 02 60 85 02')
 c.label('pixel');c.emit('a5 00 0a aa e2 20');c.label('map_bank');c.emit('bf 02 00 c6');c.branch(0xf0,'skip');c.emit('8f 00 00 00');bank_at=len(c.data)-3;c.emit('c2 20');c.label('map_pointer');c.emit('bf 00 00 c6 8f 00 00 00');lo_at=len(c.data)-3;c.emit('a6 00 bd 00 00 aa');c.label('lookup');c.emit('bf 00 00 00');c.branch(0xd0,'admitted');c.jump('fault');c.label('admitted');c.emit('a6 00 9d 00 70 e6 12')
 c.label('skip');c.emit('c2 20 e6 00 e6 00 c6 02 c6 02');c.branch(0xd0,'pixel');c.emit('a5 04 18 69 04 00 85 04 c5 18');c.branch(0xd0,'span')
 c.label('done');c.emit('a5 12 8f fa 3f 41 a5 16');c.branch(0xd0,'final');c.emit('a9 a1 b4 8f f0 3f 41');c.label('wait');c.emit('af f4 3f 41 c9 01 00');c.branch(0xd0,'wait');c.emit('e6 16 5c '+return_entry.to_bytes(3,'little').hex(' '));c.label('final');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');c.label('fault');c.emit('c2 20 a9 ae b4 8f f0 3f 41');c.jump('stop')
 worker=bytearray(c.finish());worker[bank_at:bank_at+3]=(c.base+c.labels['lookup']+3).to_bytes(3,'little');worker[lo_at:lo_at+3]=(c.base+c.labels['lookup']+1).to_bytes(3,'little')
 for at,name in patches:worker[at:at+3]=(c.base+c.labels[name]+3).to_bytes(3,'little')
 if c.base+len(worker)>0x3700:raise ValueError('FUSED_SCREEN_IRAM_CODE_CAPACITY')
 return bytes(worker),{n:c.base+c.labels[n]for n in('entry','done','fault')}
