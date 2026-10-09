"""Real source sound lifetimes through native gather and predictive BRR jobs.

Isolated SA-1 code exchange only; SPC transport and event admission unbound.
"""
import argparse,hashlib,io,json,struct,subprocess,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from compiler import Source
from source_frame_audio import stream_wav
from source_mixed_brr_quality import compact_encode
from m4_sound_gather_mix_sa1_native import build as gather
from m4_brr_filter1_sa1_native import build as encoder
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('source','assets','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());full=next(r for r in authority['results']if r['case']=='full');assert authority['status']=='PASS'and authority['complete_asset_lifetimes_proven']and full['frames_per_batch']==176;frames=176;jobs=full['batches'];source=Source(a.source);manifest=json.loads((a.assets/'report.json').read_text());inputs=[]
 for index in (27,17):
  row=next(r for r in manifest['compiled']if r['sound_index']==index);raw=source.read(row['source_path']);assert hashlib.sha256(raw).hexdigest()==row['source_sha256'];wav,_,_=stream_wav(raw,11025);assert hashlib.sha256(wav).hexdigest()==row['canonical_wav_sha256']
  with wave.open(io.BytesIO(wav),'rb')as w:pcm=w.readframes(w.getnframes())
  inputs.append(dict(values=list(pcm),initial_Q12=0))
 payload=struct.pack('<I',jobs)+b''.join(struct.pack('<II',len(r['values']),0)+bytes(r['values'])for r in inputs);actualC=subprocess.check_output([str(a.authority.resolve().parent/'source-end.exe')],input=payload,cwd=a.authority.resolve().parent);assert len(actualC)==jobs*frames*4+24
 stereo=struct.unpack('<'+'h'*(jobs*frames*2),actualC[:-24]);assert stereo[::2]==stereo[1::2];samples=stereo[::2];expected_pcm=struct.pack('<'+'h'*len(samples),*samples);expected_brr=compact_encode(samples,True);states=list(struct.unpack('<6I',actualC[-24:]))
 gr,ge,gw=gather(frames,4096,64,False,expanded_byte_sum=True,completion=True,input_channels=inputs,unroll=4,packed_mono=True,source_bank=0xe0)
 er,ee,ew=encoder(samples[:frames],False,True,True,worker_base=0x3500,input_bank=0x42,persistent_jobs=jobs)
 if len(inputs[0]['values'])*2>0xf000:raise ValueError('DESCRIPTOR_TAIL_RESERVATION')
 rom=bytearray(gr);rom[:len(er)]=er;rom[:0x10000]=gr[:0x10000];rom[0x7fd7]=12
 rom[0x20f000:0x20f090]=gr[0x1a400:0x1a490]
 main=bytearray(rom[0x8000:0x8400]);main=main[:main.index(bytes([255])*32)]
 for before,after in ((bytes.fromhex('bf 00 a4 03'),bytes.fromhex('bf 00 f0 e0')),(bytes.fromhex('bf 30 a4 03'),bytes.fromhex('bf 30 f0 e0'))):
  assert main.count(before)==1;main[main.index(before):main.index(before)+4]=after
 extra=bytes.fromhex('c2 20 a9 00 00 8f 00 f0 43 8f 02 f0 43 8f 04 f0 43 e2 20')
 if main[-3]!=0x4c:raise ValueError('HOST_WAIT_LAYOUT')
 main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(extra));at=main.index(bytes.fromhex('a9 00 8d 03 22'));main[at:at]=extra;rom[0x8000:0x8400]=main+bytes([255])*(1024-len(main))
 gw=bytearray(gw);needle=bytes.fromhex('bf 60 a4 03');assert gw.count(needle)==1;gw[gw.index(needle):gw.index(needle)+4]=bytes.fromhex('bf 60 f0 e0');done=ge['done']-0x3500;gw=bytes(gw[:done])+bytes.fromhex('5c 00 a0 01');rom[0x9000:0x9000+len(gw)]=gw;rom[0x9800:0x9800+len(ew)]=ew
 def exchange(source_at,size):return bytes.fromhex('e2 20 a9 00 48 ab a9 80 8d 30 22 a9 20 8d 0b 22 c2 20 a9')+struct.pack('<H',source_at)+bytes.fromhex('8d 32 22 e2 20 a9 c0 8d 34 22 c2 20 a9')+struct.pack('<H',size)+bytes.fromhex('8d 38 22 a9 00 35 8d 35 22 5c 00 35 00')
 for at,src,worker in ((0xa000,0x9800,ew),(0xa100,0x9000,gw)):
  glue=exchange(src,len(worker));rom[at:at+len(glue)]=glue
 path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua';points=[('gather_entry',ge['entry']),('gather_done',ge['done']),('encode_entry',ee['entry']),('encode_done',ee['done'])];callbacks=[]
 for i,(name,address)in enumerate(points):
  capture="local bytes={};for j=0,"+str(frames*2-1)+" do bytes[#bytes+1]=string.format('%02x',emu.read(0x420000+j,emu.memType.snesMemory))end;emu.log('ENDBRRPCM|'..table.concat(bytes))"if name=='encode_entry'else''
  callbacks.append(f"emu.addMemoryCallback(function()if stage=={i} then stage=(stage+1)%4;local s=emu.getState();emu.log('ENDBRR|{name}|'..s.masterClock);{capture}end end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)")
 lua.write_text('local stage=0\n'+'\n'.join(callbacks))
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for _ in range(240):
   run_frames_exact(m,1)
   if m.read_memory('SnesMemory',0x413ff0,32)[:2]==b'\xab\xb4':break
  brr=m.read_memory('SnesMemory',0x430000,len(expected_brr));phases=list(struct.unpack('<2I',m.read_memory('SnesMemory',0x435000,8)));active=list(struct.unpack('<2I',m.read_memory('SnesMemory',0x435100,8)));guard=m.read_memory('SnesMemory',0x413ff2,2)==b'\xad\xde';job_count=struct.unpack('<H',m.read_memory('SnesMemory',0x43f002,2))[0]
 log=(out/'mesen.log').read_text();events=[l.split('ENDBRR|')[1].split('|')for l in log.splitlines()if'ENDBRR|'in l];pcm=b''.join(bytes.fromhex(l.split('ENDBRRPCM|')[1])for l in log.splitlines()if'ENDBRRPCM|'in l);trace=[n for n,_ in events]==[n for n,_ in points]*jobs
 costs=[dict(zip([n for n,_ in points],[int(c)for _,c in events[i:i+4]]))for i in range(0,len(events),4)]if trace else []
 totals=[c['encode_done']-c['gather_entry']for c in costs];ok=pcm==expected_pcm and brr==expected_brr and phases==states[2::3]and active==states[1::3]and job_count==jobs and not guard and trace
 report=dict(schema='BYOR_REAL_SOURCE_AUDIO_END_BRR_NATIVE_V1',status='PASS'if ok else'FAIL',jobs=jobs,frames_per_job=frames,PCM_expected_bytes=len(expected_pcm),PCM_observed_bytes=len(pcm),PCM_mismatches=sum(a!=b for a,b in zip(pcm,expected_pcm)),BRR_expected_bytes=len(expected_brr),BRR_mismatches=sum(a!=b for a,b in zip(brr,expected_brr)),actual_phases=phases,expected_phases=states[2::3],actual_active=active,expected_active=states[1::3],completed_jobs=job_count,clipping_guard=guard,peak_job_master_clocks=max(totals)if totals else None,job_total_master_clocks=totals,gather_worker_bytes=len(gw),encoder_worker_bytes=len(ew),rom_sha256=hashlib.sha256(rom).hexdigest(),PCM_sha256=hashlib.sha256(pcm).hexdigest(),BRR_sha256=hashlib.sha256(brr).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),source_function_sha256=authority['source_functions_sha256'],source_identities=authority['source_identities'],full_asset_lifetimes_and_native_codec_bound=ok,source_event_admission_bound=False,SPC_transport_bound=False,joint_graphics_bound=False,realtime_pacing_bound=False,production_memory_lease=False,complete_backend_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_PCM_files_copied=True);(out/'native.brr').write_bytes(brr);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],'jobs',job_count,'PCM mismatches',report['PCM_mismatches'],'BRR mismatches',report['BRR_mismatches'],'peak',report['peak_job_master_clocks'])
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
