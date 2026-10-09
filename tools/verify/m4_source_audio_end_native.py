"""Real normalized 1UP/death assets through banked native ending and resume.

This checks isolated mixing and phase ownership. Source event admission and
SPC/BRR transport are not supplied by this proof.
"""
import argparse,hashlib,io,json,os,struct,subprocess,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_frame_audio import stream_wav
from m4_sound_gather_mix_sa1_native import build
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('source','assets','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--frames',type=int,choices=(176,184),default=184);a=p.parse_args();frames=a.frames;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);source=Source(a.source);manifest=json.loads((a.assets/'report.json').read_text());inputs=[];identities=[]
 for index in (27,17):
  row=next(r for r in manifest['compiled']if r['sound_index']==index);raw=source.read(row['source_path']);assert hashlib.sha256(raw).hexdigest()==row['source_sha256'];wav,meaningful,policy=stream_wav(raw,11025);assert hashlib.sha256(wav).hexdigest()==row['canonical_wav_sha256']
  with wave.open(io.BytesIO(wav),'rb')as w:pcm=w.readframes(w.getnframes())
  assert len(pcm)==row['normalized_frames'];inputs.append(pcm);identities.append(dict(sound_index=index,source_path=row['source_path'],source_sha256=row['source_sha256'],normalized_frames=len(pcm),meaningful_frames=meaningful,normalized_pcm_sha256=hashlib.sha256(pcm).hexdigest(),policy=policy))
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/source/gamelib/soundmix.c']).decode('latin1');names=('clearmixbuffer','mixaudio','update_sample','sound_play_sample');bodies={n:extract(raw,n)for n in names}
 import re
 macros='\n'.join(re.search(r'^#define\s+'+n+r'[^\n]*',raw,re.M)[0]for n in('MIXSHIFT','MAXVOLUME','MAX_CHANNELS','INT_TO_FIX','FIX_TO_INT','CHANNEL_PLAYING','CHANNEL_LOOPING','MUSIC_NUM_BUFFERS','SOUND_MONO'))
 typedefs=raw[raw.index('typedef struct'):raw.index('} musicchannelstruct;')+len('} musicchannelstruct;')]
 code='#define JOB_FRAMES '+str(frames)+'\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <fcntl.h>\n#include <io.h>\n'+macros+'\n'+typedefs+"""
typedef signed int s32;
channelstruct vchannel[MAX_CHANNELS];musicchannelstruct musicchannel;
s_soundcache cache[2],*soundcache=cache;
int max_channels=12,playbits=16,playfrequency=11025,mixing_inited=1,sound_cached=2,sample_play_id;
unsigned samplesplayed;s32 storage[JOB_FRAMES*2],*mixbuf=storage;
int sound_reload_sample(int n){return 0;}
"""+'\n'.join(bodies.values())+"""
int main(void){int i,j,n,pos,batches,channel,slots[2],state[3];unsigned short output[JOB_FRAMES*2];
setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);
if(fread(&batches,4,1,stdin)!=1||batches<1||batches>128)return 1;
for(i=0;i<2;i++){if(fread(&n,4,1,stdin)!=1||fread(&pos,4,1,stdin)!=1)return 2;
cache[i].sample.bits=8;cache[i].sample.frequency=11025;cache[i].sample.soundlen=n;cache[i].sample.channels=1;cache[i].sample.sampleptr=malloc(n);
if(fread(cache[i].sample.sampleptr,1,n,stdin)!=n)return 3;
channel=sound_play_sample(i,0,64,64,100);if(channel<0)return 4;slots[i]=channel;vchannel[channel].fp_samplepos=pos;}
for(j=0;j<batches;j++){update_sample((unsigned char*)output,sizeof(output));if(fwrite(output,sizeof(output),1,stdout)!=1)return 5;}
for(i=0;i<2;i++){channel=slots[i];state[0]=channel;state[1]=vchannel[channel].active;state[2]=vchannel[channel].fp_samplepos;if(fwrite(state,sizeof(state),1,stdout)!=1)return 6;}
return 0;}
"""
 (out/'source-end.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');run=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','source-end.c','-fe=source-end.exe'],cwd=out,env=env,capture_output=True,text=True);(out/'build-authority.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stdout+run.stderr
 results=[]
 for name,remaining,batches in (('start',(0,0),2),('tail',(119,57),2),('full',(0,0),(max(map(len,inputs))+frames-1)//frames)):
  folder=out/name;folder.mkdir(exist_ok=True);rows=[dict(values=list(pcm),initial_Q12=0 if not left else (len(pcm)-left)*4096)for pcm,left in zip(inputs,remaining)]
  payload=struct.pack('<I',batches)+b''.join(struct.pack('<II',len(pcm),r['initial_Q12'])+pcm for pcm,r in zip(inputs,rows));expected=subprocess.check_output([str(out/'source-end.exe')],input=payload,cwd=out);assert len(expected)==frames*4*batches+24
  expected_pcm=expected[:-24];states=list(struct.unpack('<6I',expected[-24:]));assert states[0]==11 and states[3]==10
  rom,entries,worker=build(frames,4096,64,False,expanded_byte_sum=True,completion=True,input_channels=rows,batches=batches,unroll=4);path=folder/'proof.sfc';path.write_bytes(rom);lua=folder/'observer.lua'
  callbacks=[]
  for n,v in entries.items():
   capture="local bytes={};for j=0,"+str(frames*4-1)+" do bytes[#bytes+1]=string.format('%02x',emu.read(0x420000+j,emu.memType.snesMemory))end;emu.log('REALENDPCM|'..table.concat(bytes))"if n=='done'else''
   callbacks.append(f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('REALEND|{n}|'..s.masterClock);{capture}end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)")
  lua.write_text('\n'.join(callbacks))
  class Observed(McpSession):
   def __enter__(self):
    import mesen_mcp.session as module
    def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
    with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
  with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as m:
   for _ in range(60):
    run_frames_exact(m,1)
    if m.read_memory('SnesMemory',0x413ff0,32)[:2]==b'\xab\xb4':break
   phases=list(struct.unpack('<2I',m.read_memory('SnesMemory',0x435000,8)));active=list(struct.unpack('<2I',m.read_memory('SnesMemory',0x435100,8)))
  log=(folder/'mesen.log').read_text();observed=b''.join(bytes.fromhex(l.split('REALENDPCM|')[1])for l in log.splitlines()if'REALENDPCM|'in l);events=[l.split('REALEND|')[1].split('|')for l in log.splitlines()if'REALEND|'in l];trace=[n for n,_ in events]==['entry','gather_mix_done','done']*batches
  ok=observed==expected_pcm and phases==states[2::3]and active==states[1::3]and trace
  result=dict(case=name,frames_per_batch=frames,batches=batches,status='PASS'if ok else'FAIL',source_slots=states[0::3],initial_Q12=[r['initial_Q12']for r in rows],PCM_observed_bytes=len(observed),PCM_expected_bytes=len(expected_pcm),PCM_mismatches=sum(a!=b for a,b in zip(observed,expected_pcm)),actual_phases=phases,expected_phases=states[2::3],actual_active=active,expected_active=states[1::3],batch_master_clocks=[int(events[i+2][1])-int(events[i][1])for i in range(0,len(events),3)]if trace else [],worker_bytes=len(worker),rom_sha256=hashlib.sha256(rom).hexdigest(),PCM_sha256=hashlib.sha256(observed).hexdigest());results.append(result);print(name,result['status'],'batches',batches,'peak clocks',max(result['batch_master_clocks'])if trace else None)
  if not ok:break
 report=dict(schema='BYOR_REAL_SOURCE_AUDIO_END_NATIVE_V1',status='PASS'if len(results)==3 and all(r['status']=='PASS'for r in results)else'FAIL',results=results,source_identities=identities,source_functions_sha256={n:hashlib.sha256(s.encode('latin1')).hexdigest()for n,s in bodies.items()},banked_complete_assets=True,complete_asset_lifetimes_proven=len(results)==3 and results[-1]['status']=='PASS' and results[-1]['actual_active']==[0,0],bank_select_policy='one 64KiB bank per admitted PCM8 channel; self-modifying isolated IRAM load operand',source_event_admission_bound=False,BRR_SPC_transport_bound=False,source_PCM16_bound=False,arbitrary_within_sample_bank_crossing_bound=False,production_memory_lease=False,complete_backend_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_PCM_files_copied=True);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
