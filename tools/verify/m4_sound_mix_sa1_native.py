"""Native PCM8 stereo accumulation cost versus actual pinned C output.

Input gathering, channel position advancement, BRR encoding and transport are
excluded. This measures one kernel, not a complete twelve-channel backend.
The isolated ROM owns its RAM; no production memory lease is published.
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
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
import m4_screen_sa1_native as base


class Code:
 def __init__(self):self.data=bytearray();self.labels={};self.refs=[]
 def emit(self,h):self.data.extend(bytes.fromhex(h))
 def word(self,op,v):self.data.extend(bytes([op])+struct.pack('<H',v))
 def label(self,n):self.labels[n]=len(self.data)
 def branch(self,op,n):self.data.extend((op,0));self.refs.append((len(self.data)-1,n,1))
 def jump(self,n):self.data.extend((0x4c,0,0));self.refs.append((len(self.data)-2,n,2))
 def finish(self):
  for at,n,size in self.refs:
   address=self.labels[n]
   if size==1:
    delta=address-at-1
    if not -128<=delta<=127:raise ValueError('MIX_KERNEL_BRANCH_RANGE:'+n)
    self.data[at]=delta&255
   else:self.data[at:at+2]=struct.pack('<H',0x3200+address)
  return bytes(self.data)


def build(frames,busy_host,unroll=1,volume=37):
 rom,_,_=base.build(np.zeros((3,2),dtype=np.uint16),busy_host,iram=True)
 rom=bytearray(rom)
 lut=np.array([sample*volume for volume in range(65)for sample in range(256)],dtype='<u2')
 rom[0x10000:0x10000+lut.nbytes]=lut.tobytes()
 records=bytearray()
 for frame in range(frames):
  for channel in range(12):
   position=channel*4+frame//4
   sample=(position*37+channel*13)&255
   records.extend(struct.pack('<HH',(volume*256+sample)*2,((64-volume)*256+sample)*2))
 rom[0x20000:0x20000+len(records)]=records
 c=Code();c.emit('78 18 fb c2 30 a2 ff 37 9a a9 00 30 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 c2 48 ab c2 20')
 c.label('entry');c.emit('a0 00 00 a9 00 00 85 0c');c.word(0xa9,frames);c.emit('85 0e')
 c.label('frame');c.emit('a9 00 00 85 00 85 02 85 04 85 06 a9 0c 00 85 08')
 c.label('channel')
 for item in range(unroll):
  for side,lo,hi in [('left',0,2),('right',4,6)]:
   offset=item*4+(0 if side=='left'else 2);label=f'no_carry_{side}_{item}'
   c.emit('be '+f'{offset:02x}'+' 00 bf 00 00 c1 18 65 '+f'{lo:02x}'+' 85 '+f'{lo:02x}')
   c.branch(0x90,label);c.emit('e6 '+f'{hi:02x}');c.label(label)
 if unroll==1:
  c.emit('c8 c8 c8 c8 c6 08');c.branch(0xd0,'channel')
 else:c.emit('98 18 69 30 00 a8')
 for side,lo,hi,out in [('left',0,2,0),('right',4,6,2)]:
  c.emit('a5 '+f'{lo:02x}'+' 38 e9 00 80 85 10 a5 '+f'{hi:02x}'+' e9 01 00')
  c.branch(0xf0,'positive_'+side);c.emit('c9 ff ff');c.branch(0xf0,'negative_'+side);c.branch(0x30,'low_'+side)
  c.emit('a9 ff 7f');c.branch(0x80,'store_'+side)
  c.label('low_'+side);c.emit('a9 00 80');c.branch(0x80,'store_'+side)
  c.label('positive_'+side);c.emit('a5 10 18 6a');c.branch(0x80,'store_'+side)
  c.label('negative_'+side);c.emit('a5 10 38 6a')
  c.label('store_'+side);c.emit('a6 0c 9f '+f'{out:02x}'+' 00 42')
 c.emit('a5 0c 18 69 04 00 85 0c c6 0e');c.branch(0xf0,'done');c.jump('frame')
 c.label('done');c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop')
 worker=c.finish()
 if len(worker)>0x600:raise ValueError('MIX_KERNEL_IRAM_CAPACITY')
 rom[0x9000:0x9000+len(worker)]=worker
 main=bytearray(rom[0x8000:0x8400]);needle=bytes.fromhex('bf 00 90 01 9f 00 32 00 e8 e0');at=main.index(needle)+len(needle)
 main[at:at+2]=struct.pack('<H',len(worker));rom[0x8000:0x8400]=main
 return bytes(rom),dict(entry=0x3200+c.labels['entry'],done=0x3200+c.labels['done']),worker


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--busy-host',action='store_true');p.add_argument('--unroll',type=int,choices=(1,12),default=1);p.add_argument('--volume',type=int,choices=(0,1,32,37,64),default=37);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';frames=authority['output_frames'];case=authority['inputs'].index([12,8,a.volume,1024,257,1]);expected=authority['actual'][case][:frames*2]
 rom,entries,worker=build(frames,a.busy_host,a.unroll,a.volume);path=a.output/'proof.sfc';path.write_bytes(rom);lua=a.output/'observer.lua'
 lua.write_text('\n'.join(f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('MIXCOST|{name}|'..s.masterClock)end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)"for name,address in entries.items()))
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log')as m:
  for _ in range(60):
   run_frames_exact(m,1)
   if m.read_memory('SnesMemory',0x413ff0,32)[:2]==b'\xab\xb4':break
  data=m.read_memory('SnesMemory',0x420000,frames*4);actual=list(struct.unpack('<'+'H'*(frames*2),data));(a.output/'mixed-s16.bin').write_bytes(data)
 events=[l.split('MIXCOST|',1)[1].split('|')for l in (a.output/'mesen.log').read_text().splitlines()if'MIXCOST|'in l]
 clocks=int(events[1][1])-int(events[0][1])if [e[0]for e in events]==['entry','done']else None
 ok=actual==expected and clocks is not None
 report=dict(schema='BYOR_SOURCE_PCM8_MIX_KERNEL_NATIVE_V1',status='PASS'if ok else'FAIL',rom_sha256=hashlib.sha256(rom).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),source_case=authority['inputs'][case],output_frames=frames,stereo_samples=frames*2,channels=12,unroll=a.unroll,busy_host_BWRAM_reads=a.busy_host,PCM_mismatches=sum(x!=y for x,y in zip(actual,expected)),master_clocks=clocks,milliseconds=clocks/21477.27 if clocks is not None else None,worker_bytes=len(worker),lookup_bytes=65*256*2,input_gathered_offline=True,phase_advance_native=False,BRR_encoding_native=False,production_memory_lease=False,production_contention_proven=False,complete_backend_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
