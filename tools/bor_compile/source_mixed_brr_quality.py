"""Bounded real-WAV C mixer and compact BRR codec quality experiment.

The explicit simultaneous mixtures are service stress, not authored timing.
No source PCM is copied to disk. Output PCM is a newly computed mixer result.
"""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import wave
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def sha(data):
 return hashlib.sha256(data).hexdigest()


def clip15(value):
 value=max(-32768,min(32767,value))
 return ((value+16384)&32767)-16384


def compact_encode(samples, predictive):
 """One peak-derived range, feedback predictor, three local nibble candidates."""
 data=bytearray();p1=p2=0
 for begin in range(0,len(samples),16):
  block=[v>>1 for v in samples[begin:begin+16]]
  filt=int(predictive and begin!=0)
  previous=p1;peak=0
  for target in block:
   prediction=previous+((-previous)>>4) if filt else 0
   peak=max(peak,abs(target-prediction));previous=target
  shift=next((s for s in range(13)if peak<=7*(1<<s)//2),12)
  nibbles=[]
  for target in block:
   prediction=p1+((-p1)>>4) if filt else 0
   numerator=2*(target-prediction)
   n=(abs(numerator)//(1<<shift))*(-1 if numerator<0 else 1)
   n=max(-8,min(7,n));options=[]
   for candidate in sorted(set(max(-8,min(7,n+d))for d in(-1,0,1))):
    decoded=clip15(((candidate<<shift)>>1)+prediction)
    penalty=100000000 if decoded==-16384 else 0
    if decoded==p1==-16384:penalty+=1000000000
    if decoded==p1==p2==-16384:penalty+=2147483647
    options.append(((target-decoded)**2+penalty,candidate,decoded))
   _,n,decoded=min(options);nibbles.append(n&15);p2,p1=p1,decoded
  data.append((shift<<4)|(filt<<2)|int(begin+16==len(samples)))
  data.extend((nibbles[i]<<4)|nibbles[i+1]for i in range(0,16,2))
 return bytes(data)


def metrics(expected,decoded):
 errors=[a-b for a,b in zip(expected,decoded)]
 mse=sum(e*e for e in errors)/len(errors);signal=sum(v*v for v in expected)/len(expected)
 triple_min=sum(decoded[i:i+3]==(-32768,-32768,-32768)for i in range(len(decoded)-2))
 return dict(samples=len(expected),peak_error=max(map(abs,errors)),rms_error=math.sqrt(mse),gaussian_overflow_minimum_triples=triple_min,
  snr_db=10*math.log10(signal/mse)if signal and mse else None,
  clipped_source_samples=sum(v in(-32768,32767)for v in expected))


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
 p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
 p.add_argument('--output',type=Path,required=True);p.add_argument('--frames',type=int,default=16384)
 p.add_argument('--channel-states',action='store_true',help='Retain actual C final channel state for joint native comparison')
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 if a.frames<=0 or a.frames%16:raise ValueError('BRR_BLOCK_ALIGNMENT')
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/source/gamelib/soundmix.c']).decode('latin1')
 names=('clearmixbuffer','mixaudio','update_sample','sound_play_sample');bodies={n:extract(raw,n)for n in names}
 typedefs=raw[raw.index('typedef struct'):raw.index('} musicchannelstruct;')+len('} musicchannelstruct;')]
 macros='\n'.join(re.search(r'^#define\s+'+n+r'[^\n]*',raw,re.M)[0]for n in('MIXSHIFT','MAXVOLUME','MAX_CHANNELS','INT_TO_FIX','FIX_TO_INT','CHANNEL_PLAYING','CHANNEL_LOOPING','MUSIC_NUM_BUFFERS','SOUND_MONO'))
 code='#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <fcntl.h>\n#include <io.h>\n'+macros+'\n'+typedefs+r'''
typedef signed int s32;
channelstruct vchannel[MAX_CHANNELS];musicchannelstruct musicchannel;
s_soundcache cache[12],*soundcache=cache;
int max_channels=12,playbits=16,playfrequency=11025,mixing_inited=1,sound_cached=12,sample_play_id;
unsigned samplesplayed;s32 *mixbuf;
int sound_reload_sample(int n){return 0;}
'''+ '\n'.join(bodies.values())+r'''
int main(void){int count,frames,i,j,header[3];unsigned short *output;
setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
if(fread(&count,4,1,stdin)!=1||fread(&frames,4,1,stdin)!=1||count>12)return 3;
mixbuf=calloc(frames*2,sizeof(s32));output=malloc(frames*4);
for(i=0;i<count;i++){
 if(fread(header,4,3,stdin)!=3)return 4;
 cache[i].sample.bits=header[0];cache[i].sample.frequency=header[1];cache[i].sample.soundlen=header[2];cache[i].sample.channels=1;
 j=header[2]*(header[0]/8);cache[i].sample.sampleptr=malloc(j);
 if(fread(cache[i].sample.sampleptr,1,j,stdin)!=j)return 5;
 if(sound_play_sample(i,1,64,64,100)<0)return 6;
}
update_sample((unsigned char*)output,frames*4);
if(fwrite(output,4,frames,stdout)!=frames)return 7;
return 0;}
'''
 if a.channel_states:
  before,after=code.rsplit('return 0;}',1)
  code=before+'for(i=0;i<12;i++){int state[4];state[0]=vchannel[i].active;state[1]=vchannel[i].fp_samplepos;state[2]=vchannel[i].fp_period;state[3]=vchannel[i].samplenum;if(fwrite(state,4,4,stdout)!=4)return 8;}\nreturn 0;}'+after
 (out/'mix.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 run=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','mix.c','-fe=mix.exe'],cwd=out,env=env,capture_output=True,text=True)
 (out/'build.log').write_text(run.stdout+run.stderr);run.check_returncode()
 tad=Path('out/byor-motu-tad-toolchain/crates/brr/src');pin='00215a2e9aaf327d620120a48b47d74f80d5b521';hashes={}
 for name in('encoder.rs','decoder.rs','lib.rs','gaussian_overflow_test.rs'):
  authority=subprocess.check_output(['git','-C','E:/gh/terrific-audio-driver','show',pin+':crates/brr/src/'+name])
  local=(tad/name).read_bytes()
  if local.replace(b'\r\n',b'\n')!=authority.replace(b'\r\n',b'\n'):raise ValueError('TAD_SOURCE_HASH:'+name)
  hashes[name]=dict(checkout_sha256=sha(local),git_blob_sha256=sha(authority),line_ending_normalized_equal=True)
 rust=r'''extern crate brr;
use std::{env,fs};
fn main(){let args:Vec<String>=env::args().collect();let raw=fs::read(&args[2]).unwrap();
let data=if args[1]=="encode"{let samples:Vec<i16>=raw.chunks_exact(2).map(|b|i16::from_le_bytes([b[0],b[1]])).collect();
let sample=brr::encode_brr(&samples,brr::DEFAULT_EVALUATOR,None,None,None).unwrap();
eprintln!("gaussian_overflow={}",sample.test_for_gaussian_overflow_glitch_autoloop());sample.brr_data().to_vec()
}else{brr::decode_brr_data(&raw).iter().flat_map(|s|s.to_le_bytes()).collect()};fs::write(&args[3],data).unwrap();}
'''
 (out/'codec.rs').write_text(rust)
 subprocess.run(['rustc',str((tad/'lib.rs').resolve()),'--crate-name','brr','--crate-type','rlib','--edition','2021','-O','-o',str(out/'libbrr.rlib')],check=True)
 subprocess.run(['rustc',str(out/'codec.rs'),'--extern','brr='+str(out/'libbrr.rlib'),'-O','-o',str(out/'codec.exe')],check=True)
 source=Source(a.source);manifest=json.loads((a.assets/'report.json').read_text());assets={};source_rows=[]
 for index in(4,6,16,26):
  row=next(r for r in manifest['compiled']if r['sound_index']==index);data=source.read(row['source_path'])
  if sha(data)!=row['source_sha256']:raise ValueError('SOURCE_WAV_HASH')
  with wave.open(io.BytesIO(data),'rb')as w:
   if w.getnchannels()!=1:raise ValueError('MONO_DOMAIN')
   pcm=w.readframes(w.getnframes());assets[index]=(w.getsampwidth()*8,w.getframerate(),w.getnframes(),pcm)
  source_rows.append({k:row[k]for k in('sound_index','source_path','source_sha256')})
 cases=[('sound-'+str(i),[i])for i in assets]+[('six-voice-stress',[6,4,16,16,16,26]),('twelve-voice-stress',[16]*9+[6,4,26])];results=[]
 for name,ids in cases:
  payload=struct.pack('<ii',len(ids),a.frames)
  for index in ids:
   bits,freq,length,pcm=assets[index];payload+=struct.pack('<iii',bits,freq,length)+pcm
  output=subprocess.check_output([str(out/'mix.exe')],input=payload,cwd=out);states=None
  if a.channel_states:
   stereo=output[:a.frames*4];state_values=struct.unpack('<48I',output[a.frames*4:]);states=[dict(slot=i,active=state_values[i*4],Q12_position=state_values[i*4+1],Q12_period=state_values[i*4+2],fixture_sample_index=state_values[i*4+3])for i in range(12)]
  else:stereo=output
  values=struct.unpack('<'+'h'*(a.frames*2),stereo)
  if values[::2]!=values[1::2]:raise ValueError('MONO_MIX_ASYMMETRY')
  samples=values[::2];mixed=struct.pack('<'+'h'*len(samples),*samples);base=out/name;base.with_suffix('.mixed').write_bytes(mixed)
  codecs={}
  for mode in('tad','peak-filter0','peak-filter1'):
   dest=out/(name+'.'+mode+'.brr')
   if mode=='tad':
    r=subprocess.run([str(out/'codec.exe'),'encode',str(base.with_suffix('.mixed')),str(dest)],capture_output=True,text=True,check=True)
    if 'gaussian_overflow=false'not in r.stderr:raise ValueError('TAD_GAUSSIAN_OVERFLOW')
   else:dest.write_bytes(compact_encode(samples,mode=='peak-filter1'))
   decoded=dest.with_suffix('.decoded');subprocess.run([str(out/'codec.exe'),'decode',str(dest),str(decoded)],check=True)
   reconstructed=struct.unpack('<'+'h'*a.frames,decoded.read_bytes());quality=metrics(samples,reconstructed)
   if quality['gaussian_overflow_minimum_triples']:raise ValueError('DECODED_GAUSSIAN_OVERFLOW:'+mode)
   codecs[mode]=dict(quality,brr_bytes=dest.stat().st_size,brr_sha256=sha(dest.read_bytes()))
  results.append(dict(name=name,sound_indices=ids,mixed_pcm_sha256=sha(mixed),actual_C_final_channels=states,codecs=codecs))
 report=dict(schema='BYOR_MIXED_BRR_QUALITY_V1',status='MEASURED',engine_commit=ENGINE_COMMIT,function_sha256={n:sha(b.encode('latin1'))for n,b in bodies.items()},tad_commit=pin,tad_source_sha256=hashes,source_assets=source_rows,output_rate=11025,frames=a.frames,source_output_rate_policy='ACCEPTED_COMPAT 11025; actual C nearest Q12 sampling and mixer',stress_is_authored_timing=False,source_pcm_copied=False,native_encoding_cost_proven=False,physical_polyphony_proven=False,production_admitted=False,no_color_reduction=True,results=results)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 for r in results:print(r['name'],{k:round(v['snr_db'],2)if v['snr_db']is not None else None for k,v in r['codecs'].items()})


if __name__=='__main__':main()
