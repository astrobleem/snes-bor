"""Pinned twelve-channel PCM accumulation and final output, with music inactive.

This supplies mixer authority for a future physical backend. It does not turn
the existing one-voice stream into a twelve-channel implementation.
"""
import argparse
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import wave
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def trunc_div(value,divisor):
 return (abs(value)//divisor)*(-1 if value<0 else 1)


def engine_sound_calls(raw):
 """Keep offsets while removing comments; preserve each actual call's args."""
 text=re.sub(r'/\*.*?\*/|//[^\n]*',lambda m:''.join('\n'if c=='\n'else' 'for c in m[0]),raw,flags=re.S)
 calls=[]
 for match in re.finditer(r'\bsound_play_sample\s*\(',text):
  start=match.end();depth=1;args=[];part=start;end=start
  while end<len(text)and depth:
   c=text[end]
   if c=='(':depth+=1
   elif c==')':
    depth-=1
    if not depth:args.append(text[part:end].strip())
   elif c==','and depth==1:args.append(text[part:end].strip());part=end+1
   end+=1
  if depth or len(args)!=5:raise ValueError('ENGINE_SOUND_CALL_PARSE_DOMAIN')
  calls.append(dict(source_line=raw.count('\n',0,match.start())+1,arguments=args,
   left_right_equal=re.sub(r'\s','',args[2])==re.sub(r'\s','',args[3]),
   call_sha256=hashlib.sha256(raw[match.start():end].encode('latin1')).hexdigest()))
 return calls


def reference(row,frames=48,equal_volumes=False):
 count,bits,volume,period,length,active=row
 mixed=[32768<<3]*(2*frames);states=[]
 for channel in range(count):
  position=((channel*4)%length)<<12;live=active
  for sample in range(frames):
   index=position>>12
   value=(index*37+channel*13)&255 if bits==8 else (index*257+channel*1024)%65536-32768
   for side,gain in enumerate((volume,volume if equal_volumes else 64-volume)):
    contribution=((value<<8)*gain//64)-32768 if bits==8 else trunc_div(value*gain,64)
    mixed[2*sample+side]+=contribution
   position=(position+period)&0xffffffff
   if position>=length<<12:
    position%=length<<12
    if active!=2:live=0;break
  states.extend((live,position))
 return [max(0,min(65535,v>>3))^32768 for v in mixed]+states


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
 p.add_argument('--source',type=Path,required=True)
 p.add_argument('--assets',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--frames',type=int,choices=(48,184),default=48)
 p.add_argument('--equal-volumes',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/source/gamelib/soundmix.c']).decode('latin1')
 engine=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');calls=engine_sound_calls(engine)
 names=('clearmixbuffer','mixaudio','update_sample');bodies={n:extract(raw,n)for n in names}
 typedefs=raw[raw.index('typedef struct'):raw.index('} musicchannelstruct;')+len('} musicchannelstruct;')]
 macros='\n'.join(re.search(r'^#define\s+'+n+r'[^\n]*',raw,re.M)[0]for n in('MIXSHIFT','MAXVOLUME','MAX_CHANNELS','INT_TO_FIX','FIX_TO_INT','CHANNEL_PLAYING','CHANNEL_LOOPING','MUSIC_NUM_BUFFERS','SOUND_MONO'))
 rows=list(itertools.product((0,1,2,4,8,12),(8,16),(0,1,32,37,64),(1024,4096,8192),(17,257),(1,2)))
 code='#include <stdio.h>\n#include <string.h>\n#define OUTPUT_FRAMES '+str(a.frames)+'\n'+macros+'\n'+typedefs+r'''
typedef signed int s32;
channelstruct vchannel[MAX_CHANNELS];musicchannelstruct musicchannel;
s_soundcache cache[12],*soundcache=cache;
int max_channels,playbits=16;unsigned samplesplayed;
s32 storage[OUTPUT_FRAMES*2],*mixbuf=storage;
unsigned char pcm8[12][257];short pcm16[12][257];
'''+ '\n'.join(bodies.values())
 code+='\nint cases[][6]={'+','.join('{'+','.join(map(str,r))+'}'for r in rows)+'};\n'
 code+=r'''
int main(void){unsigned k;int j,i,*c;unsigned short output[OUTPUT_FRAMES*2];
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
c=cases[k];max_channels=c[0];memset(vchannel,0,sizeof(vchannel));memset(cache,0,sizeof(cache));
for(j=0;j<max_channels;j++){
 for(i=0;i<257;i++){pcm8[j][i]=(i*37+j*13)&255;pcm16[j][i]=(i*257+j*1024)%65536-32768;}
 cache[j].sample.sampleptr=c[1]==8?(void*)pcm8[j]:(void*)pcm16[j];cache[j].sample.bits=c[1];cache[j].sample.soundlen=c[4];
 vchannel[j].active=c[5];vchannel[j].samplenum=j;vchannel[j].channels=1;
 vchannel[j].volume[0]=c[2];vchannel[j].volume[1]=64-c[2];
 vchannel[j].fp_samplepos=((j*4)%c[4])<<12;vchannel[j].fp_period=c[3];
}
update_sample((unsigned char*)output,sizeof(output));printf("MIX|%u|",k);
for(i=0;i<OUTPUT_FRAMES*2;i++)printf("%s%u",i?",":"",output[i]);
for(j=0;j<max_channels;j++)printf(",%d,%u",vchannel[j].active,vchannel[j].fp_samplepos);puts("");
}return 0;}
'''
 if a.equal_volumes:code=code.replace('vchannel[j].volume[1]=64-c[2]','vchannel[j].volume[1]=c[2]')
 (a.output/'mixing.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 run=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','mixing.c','-fe=mixing.exe'],cwd=a.output,env=env,capture_output=True,text=True)
 (a.output/'build.log').write_text(run.stdout+run.stderr)
 if run.returncode:raise ValueError('PINNED_MIXING_C_BUILD:'+run.stdout+run.stderr)
 lines=subprocess.check_output([str(a.output/'mixing.exe')],cwd=a.output,text=True).splitlines();actual=[]
 for line in lines:
  _,index,values=line.split('|');assert int(index)==len(actual);actual.append(list(map(int,values.split(','))))
 expected=[reference(r,a.frames,a.equal_volumes)for r in rows];ok=actual==expected and len(actual)==len(rows)
 source=Source(a.source);manifest=json.loads((a.assets/'report.json').read_text());assets=[]
 for row in manifest['compiled']:
  data=source.read(row['source_path']);assert hashlib.sha256(data).hexdigest()==row['source_sha256']
  with wave.open(io.BytesIO(data),'rb')as w:
   assets.append(dict(sound_index=row['sound_index'],source_path=row['source_path'],bits=w.getsampwidth()*8,channels=w.getnchannels(),frequency=w.getframerate(),source_frames=w.getnframes()))
 report=dict(schema='BYOR_4086_SOUND_MIXING_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,
  source_path='engine/source/gamelib/soundmix.c',function_sha256={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},
  cases=len(rows),output_frames=a.frames,right_volume_policy='equal to left'if a.equal_volumes else'64 minus left',case_fields=['active_channels','bits','left_volume','Q12_period','sample_length','active_mode'],inputs=rows,actual=actual,expected=expected,
  source_assets=assets,source_mixshift=3,source_8bit_contribution='((unsigned_sample<<8)*volume/64)-32768',source_16bit_contribution='signed_sample*volume/64 with C truncation toward zero',
  engine_sound_calls=calls,engine_sound_calls_sha256=hashlib.sha256(engine.encode('latin1')).hexdigest(),all_engine_sound_calls_left_right_equal=bool(calls)and all(c['left_right_equal']for c in calls),script_sound_call_volume_policy_proven=False,
  output_16bit_policy='signed accumulator arithmetic >>3, clamp unsigned biased 0..65535, XOR 32768',
  mono_source_is_accumulated_into_both_output_sides=True,music_inactive=True,source_pcm_not_copied=True,
  source_channel_backend_bound=False,physical_DSP_polyphony_proven=False,native_mixing_budget_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'actual C mixer cases;',len(assets),'source WAV headers')
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
