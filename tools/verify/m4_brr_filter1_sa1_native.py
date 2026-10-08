"""Bounded native predictive BRR fast path with explicit clipping guard.

Guarded chunks are rejected by this fixture; a general backend still needs
an exact slow path for those samples. No production codec is admitted here.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
from m4_sound_mix_sa1_native import Code
from m4_brr_filter0_sa1_native import build as filter0_build
from source_mixed_brr_quality import compact_encode


def synthetic_input(kind,frames):
 if kind=='minimum':return struct.pack('<'+'h'*frames,*([-32768]*frames))
 samples=[]
 for value in(-32768,-32767,-32766,-28672,-16384,-1,0,1,16383,28672,32766,32767):samples.extend([value]*32)
 samples.extend([-32768,32767]*128);samples.extend(range(-32768,32768,256));rng=random.Random(4086)
 samples.extend(rng.randrange(-32768,32768)for _ in range(max(0,frames-len(samples))))
 return struct.pack('<'+'h'*frames,*samples[:frames])


def residual_lookup(shift,avoid_min=False):
 table=bytearray()
 for raw in range(65536):
  target=raw if raw<32768 else raw-65536
  numerator=target*2;n=(abs(numerator)//(1<<shift))*(-1 if numerator<0 else 1);n=max(-8,min(7,n))
  candidates=[((target-((candidate<<shift)>>1))**2+(100000000 if avoid_min and ((candidate<<shift)>>1)==-16384 else 0),candidate)for candidate in sorted(set(max(-8,min(7,n+d))for d in(-1,0,1)))]
  table.append(min(candidates)[1]&15)
 return bytes(table)


def build(samples,busy,predictor_dbr=False,clip_repair=False,worker_base=0x3200,input_bank=0xc2,persistent_jobs=0):
 raw,_,_=filter0_build(samples,busy);rom=bytearray(raw)
 prediction=[(p if p<16384 else p-32768)+((-(p if p<16384 else p-32768))>>4)for p in range(32768)]
 rom[0x10000:0x20000]=struct.pack('<32768h',*prediction)
 ranges=bytes(next((s for s in range(13)if peak<=7*(1<<s)//2),12)for peak in range(32769))
 rom[0x30000:0x30000+len(ranges)]=ranges
 for shift in range(13):
  rom[0x40000+shift*65536:0x50000+shift*65536]=residual_lookup(shift,True)
  rom[0x110000+shift*65536:0x120000+shift*65536]=residual_lookup(shift)
  residual=[((n if n<8 else n-16)<<shift)>>1 for n in range(16)]
  rom[0x39000+shift*32:0x39020+shift*32]=struct.pack('<16h',*residual)
 rom[0x1e0000:0x1f0000]=bytes(65536)
 c=Code(worker_base);c.emit('78 18 fb c2 30 a2 ff 37 9a a9 00 30 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 00 48 ab c2 20')
 c.label('entry');c.emit('a9 00 00 8f f2 3f 41 85 28 85 00 85 04 85 10 85 14 85 18 e2 20 a9 43 85 06 a9 c3 85 24 c2 20')
 if persistent_jobs:c.emit('af 00 f0 43 85 14 af 04 f0 43 85 04 af 02 f0 43 85 2c')
 def present(name):
  c.emit('a6 10')
  if persistent_jobs:c.branch(0xd0,name);c.emit('a6 2c');c.label(name)
 c.label('block');c.emit('e2 20 a9 c1');present('predictor_present');c.branch(0xd0,'predictor_bank');c.emit('a9 de');c.label('predictor_bank');c.emit(('48 ab'if predictor_dbr else'85 1a')+' c2 20 a9 00 00 85 08 a5 14 85 12 a9 10 00 85 20')
 if persistent_jobs:c.emit('a6 10')
 predictor='b9 00 00'if predictor_dbr else'b7 18'
 source_load='bf 00 00 '+f'{input_bank:02x}'
 c.label('peak');c.emit(source_load+' c9 00 80 6a 85 1c a5 12 29 ff 7f 0a a8 '+predictor+' 85 1e a5 1c 85 12 38 e5 1e')
 c.branch(0x10,'absolute');c.emit('49 ff ff 1a');c.label('absolute');c.emit('c5 08');c.branch(0x90,'retain');c.emit('85 08');c.label('retain');c.emit('e8 e8 c6 20');c.branch(0xd0,'peak')
 c.emit('a6 08 e2 20 bf 00 00 c3 85 0a 18 69 d1');present('quant_present');c.branch(0xd0,'quant_bank');c.emit('a5 0a 18 69 c4');c.label('quant_bank');c.emit('85 02 a5 0a 0a 0a 0a 0a');present('header_present');c.branch(0xf0,'header');c.emit('09 04');c.label('header');c.emit('87 04 c2 20 e6 04 a5 0a 29 ff 00 0a 0a 0a 0a 0a 18 69 00 90 85 22 a6 10 a9 08 00 85 0c')
 c.label('pair')
 for side in range(2):
  c.emit(source_load+' c9 00 80 6a 85 1c a5 14 29 ff 7f 0a a8 '+predictor+' 85 1e a5 1c 38 e5 1e a8 e2 20 b7 00 85 26')
  if not clip_repair:c.emit('0a 0a 0a 0a 85 0e'if side==0 else'05 0e 87 04')
  c.emit('c2 20')
  if clip_repair:c.emit('a9 00 00 85 2a')
  c.label('decode_'+str(side));c.emit('a5 26 29 ff 00 0a a8 b7 22 18 65 1e')
  c.branch(0x10,'positive_'+str(side));c.emit('c9 00 c0');c.branch(0x90,'negative_fix_'+str(side)if clip_repair else'fault');c.branch(0xf0,'negative_fix_'+str(side)if clip_repair else'fault');c.branch(0x80,'decoded_'+str(side))
  c.label('positive_'+str(side));c.emit('c9 00 40');c.branch(0xb0,'positive_fix_'+str(side)if clip_repair else'fault')
  if clip_repair:
   c.branch(0x80,'decoded_'+str(side));c.label('negative_fix_'+str(side));c.emit('a5 26 1a');c.branch(0x80,'repair_'+str(side));c.label('positive_fix_'+str(side));c.emit('a5 26 3a');c.label('repair_'+str(side));c.emit('29 0f 00 85 26 a5 2a');c.branch(0xf0,'retry_'+str(side));c.jump('fault');c.label('retry_'+str(side));c.emit('a9 01 00 85 2a e6 28');c.jump('decode_'+str(side))
  c.label('decoded_'+str(side));c.emit('85 14')
  if clip_repair:
   c.emit('e2 20 a5 26');c.emit('0a 0a 0a 0a 85 0e'if side==0 else'05 0e 87 04');c.emit('c2 20')
  c.emit('e8 e8')
 c.emit('e6 04 c6 0c');c.branch(0xf0,'pair_done');c.jump('pair');c.label('pair_done');c.emit('86 10');c.word(0xe0,len(samples)*2);c.branch(0xf0,'done');c.jump('block')
 c.label('fault');c.emit('a9 ad de 8f f2 3f 41');c.jump('done')
 c.label('done')
 if persistent_jobs:
  c.emit('a5 14 8f 00 f0 43 a5 04 8f 04 f0 43 a5 2c 1a 8f 02 f0 43');c.word(0xc9,persistent_jobs);c.branch(0xb0,'final_job');c.emit('5c 00 a1 01');c.label('final_job')
 c.emit('a5 04 38 e9 09 00 85 04 e2 20 a7 04 09 01 87 04 c2 20 a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');worker=c.finish()
 if len(worker)>0x500:raise ValueError('PREDICTIVE_WORKER_IRAM_GAP')
 rom[0x9000:0x9000+len(worker)]=worker
 main=bytearray(rom[0x8000:0x8400]);needle=bytes.fromhex('bf 00 90 01 9f 00 32 00 e8 e0');at=main.index(needle)+len(needle);main[at:at+2]=struct.pack('<H',len(worker));rom[0x8000:0x8400]=main
 return bytes(rom),{n:c.base+c.labels[n]for n in('entry','done')},worker


def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--mixed',type=Path);g.add_argument('--synthetic',choices=('minimum','edge-and-random'));p.add_argument('--output',type=Path,required=True);p.add_argument('--frames',type=int,default=192);p.add_argument('--busy-host',action='store_true');p.add_argument('--predictor-dbr',action='store_true');p.add_argument('--expect-guard',action='store_true');p.add_argument('--clip-repair',action='store_true');a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 if a.frames<=0 or a.frames%16 or a.frames>8192:raise ValueError('BOUNDED_BRR_BLOCK_DOMAIN')
 data=synthetic_input(a.synthetic,a.frames)if a.synthetic else a.mixed.read_bytes()[:a.frames*2]
 if len(data)!=a.frames*2:raise ValueError('MIXTURE_TOO_SHORT')
 samples=struct.unpack('<'+'h'*a.frames,data);expected=compact_encode(samples,True);rom,entries,worker=build(samples,a.busy_host,a.predictor_dbr,a.clip_repair);path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua'
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
  actual=m.read_memory('SnesMemory',0x430000,len(expected));guard=m.read_memory('SnesMemory',0x413ff2,2)==b'\xad\xde';repair_count=struct.unpack('<H',m.read_memory('SnesMemory',0x003028,2))[0];(out/'native.brr').write_bytes(actual)
 events=[l.split('BRRCOST|',1)[1].split('|')for l in(out/'mesen.log').read_text().splitlines()if'BRRCOST|'in l]
 elapsed=int(events[1][1])-int(events[0][1])if[e[0]for e in events]==['entry','done']else None
 encoding_exact=actual==expected and not guard
 ok=elapsed is not None and(guard if a.expect_guard else encoding_exact)
 report=dict(schema='BYOR_NATIVE_FILTER1_BRR_V1',status='PASS'if ok else'FAIL',frames=a.frames,blocks=a.frames//16,brr_bytes=len(expected),byte_mismatches=sum(x!=y for x,y in zip(actual,expected)),clipping_guard_hit=guard,master_clocks=elapsed,milliseconds=elapsed/21477.27 if elapsed else None,worker_IRAM_bytes=len(worker),predictor_DBR=a.predictor_dbr,lookup_ROM_bytes=26*65536+65536+32769+416+65536,busy_host_BWRAM_reads=a.busy_host,mixed_input_sha256=hashlib.sha256(data).hexdigest(),rom_sha256=hashlib.sha256(rom).hexdigest(),brr_sha256=hashlib.sha256(actual).hexdigest(),filter1_native=True,codec_quality_admitted=False,guard_slow_path_bound=False,PCM_gather_and_mix_in_timing=False,mixed_transport_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
 report.update(expected_clipping_guard=a.expect_guard,encoding_exact=encoding_exact,clip_repair=a.clip_repair,repair_count=repair_count,synthetic_input=a.synthetic,scope='explicit unsupported clipping guard'if a.expect_guard else'bounded exact predictive encoding')
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
