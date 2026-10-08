"""Native adaptive-range filter-0 BRR cost on computed source mixtures.

This is a timing baseline, not codec quality admission or a backend lease.
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
from m4_sound_mix_sa1_native import Code
import m4_screen_sa1_native as base
from source_mixed_brr_quality import compact_encode,clip15


def lookup(shift):
 table=bytearray()
 for raw in range(65536):
  target=(raw if raw<32768 else raw-65536)>>1
  numerator=target*2;n=(abs(numerator)//(1<<shift))*(-1 if numerator<0 else 1);n=max(-8,min(7,n))
  candidates=[]
  for candidate in sorted(set(max(-8,min(7,n+d))for d in(-1,0,1))):
   decoded=clip15((candidate<<shift)>>1)
   candidates.append(((target-decoded)**2+(100000000 if decoded==-16384 else 0),candidate))
  table.append(min(candidates)[1]&15)
 return bytes(table)


def build(samples,busy):
 raw,_,_=base.build(np.zeros((3,2),dtype=np.uint16),busy,iram=True)
 rom=bytearray(raw)+bytearray([255])*(2*1024*1024-len(raw))
 data=struct.pack('<'+'h'*len(samples),*samples);rom[0x20000:0x20000+len(data)]=data
 ranges=bytes(next((s for s in range(13)if peak<=7*(1<<s)//2),12)for peak in range(16385))
 rom[0x30000:0x30000+len(ranges)]=ranges
 for shift in range(13):rom[0x40000+shift*65536:0x50000+shift*65536]=lookup(shift)
 c=Code();c.emit('78 18 fb c2 30 a2 ff 37 9a a9 00 30 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 00 48 ab c2 20')
 c.label('entry');c.emit('a9 00 00 85 00 85 04 85 10 e2 20 a9 43 85 06 c2 20')
 c.label('block');c.emit('a9 00 00 85 08 a6 10 a0 10 00')
 c.label('peak');c.emit('bf 00 00 c2 c9 00 80 6a')
 c.branch(0x10,'absolute');c.emit('49 ff ff 1a');c.label('absolute');c.emit('c5 08');c.branch(0x90,'retain');c.emit('85 08');c.label('retain');c.emit('e8 e8 88');c.branch(0xd0,'peak')
 c.emit('a6 08 e2 20 bf 00 00 c3 85 0a 18 69 c4 85 02 a5 0a 0a 0a 0a 0a 87 04 c2 20 e6 04 a6 10 a9 08 00 85 0c')
 c.label('pair');c.emit('bf 00 00 c2 a8 e2 20 b7 00 0a 0a 0a 0a 85 0e c2 20 bf 02 00 c2 a8 e2 20 b7 00 05 0e 87 04 c2 20 e6 04 e8 e8 e8 e8 c6 0c');c.branch(0xd0,'pair')
 c.emit('86 10');c.word(0xe0,len(data));c.branch(0xf0,'done');c.jump('block')
 c.label('done');c.emit('a5 04 38 e9 09 00 85 04 e2 20 a7 04 09 01 87 04 c2 20 a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop')
 worker=c.finish();rom[0x9000:0x9000+len(worker)]=worker
 main=bytearray(rom[0x8000:0x8400]);needle=bytes.fromhex('bf 00 90 01 9f 00 32 00 e8 e0');at=main.index(needle)+len(needle);main[at:at+2]=struct.pack('<H',len(worker));rom[0x8000:0x8400]=main
 rom[0x7fd7]=11
 return bytes(rom),{n:c.base+c.labels[n]for n in('entry','done')},worker


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mixed',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--frames',type=int,default=192);p.add_argument('--busy-host',action='store_true');a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 if a.frames<=0 or a.frames%16 or a.frames>8192:raise ValueError('BOUNDED_BRR_BLOCK_DOMAIN')
 data=a.mixed.read_bytes()[:a.frames*2]
 if len(data)!=a.frames*2:raise ValueError('MIXTURE_TOO_SHORT')
 samples=struct.unpack('<'+'h'*a.frames,data);expected=compact_encode(samples,False)
 rom,entries,worker=build(samples,a.busy_host);path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua'
 lua.write_text('\n'.join(f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('BRRCOST|{name}|'..s.masterClock)end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)"for name,address in entries.items()))
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for _ in range(60):
   run_frames_exact(m,1)
   if m.read_memory('SnesMemory',0x413ff0,32)[:2]==b'\xab\xb4':break
  actual=m.read_memory('SnesMemory',0x430000,len(expected));(out/'native.brr').write_bytes(actual)
 events=[l.split('BRRCOST|',1)[1].split('|')for l in(out/'mesen.log').read_text().splitlines()if'BRRCOST|'in l]
 elapsed=int(events[1][1])-int(events[0][1])if[e[0]for e in events]==['entry','done']else None
 ok=actual==expected and elapsed is not None
 report=dict(schema='BYOR_NATIVE_FILTER0_BRR_V1',status='PASS'if ok else'FAIL',frames=a.frames,blocks=a.frames//16,brr_bytes=len(expected),byte_mismatches=sum(x!=y for x,y in zip(actual,expected)),master_clocks=elapsed,milliseconds=elapsed/21477.27 if elapsed else None,worker_IRAM_bytes=len(worker),quantization_lookup_ROM_bytes=13*65536,range_lookup_ROM_bytes=16385,busy_host_BWRAM_reads=a.busy_host,mixed_input_sha256=hashlib.sha256(data).hexdigest(),rom_sha256=hashlib.sha256(rom).hexdigest(),brr_sha256=hashlib.sha256(actual).hexdigest(),filter1_native=False,codec_quality_admitted=False,PCM_gather_and_mix_in_timing=False,mixed_transport_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
