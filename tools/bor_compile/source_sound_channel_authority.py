"""Pinned mixer admission at the actual openbor startup's twelve channels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def pinned(path):return subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':'+path]).decode('latin1')
 raw=pinned('engine/source/gamelib/soundmix.c');engine=pinned('engine/openbor.c');body=extract(raw,'sound_play_sample')
 startup=re.search(r'if\(savedata\.usesound && sound_init\((\d+)\)\)',engine);assert startup
 count=int(startup[1]);assert count==12
 typedefs=raw[raw.index('typedef struct'):raw.index('} s_soundcache;')+len('} s_soundcache;')]
 macros='\n'.join(re.search(r'^#define\s+'+name+r'[^\n]*',raw,re.M)[0]for name in('MAXVOLUME','MAX_CHANNELS','INT_TO_FIX','CHANNEL_PLAYING'))
 rows=[dict(mask=mask,priority=0,pattern=0,sample=0,speed=100,left=64,right=64,inited=1,reload=1)for mask in range(1<<count)]
 rows.extend(dict(mask=4095,priority=priority,pattern=pattern,sample=0,speed=100,left=64,right=64,inited=1,reload=1)for pattern in(1,2,3)for priority in(0,1,2,7,0xffffffff))
 undefined=[row for row in rows if row['mask']==4095 and row['pattern']==3 and row['priority']==0xffffffff]
 rows=[row for row in rows if row not in undefined]
 seed=rows[0]
 rows.extend(dict(seed,**changes)for changes in(dict(sample=-1),dict(sample=1),dict(inited=0),dict(reload=0),dict(speed=0),dict(speed=1),dict(speed=200),dict(left=-1,right=65),dict(left=37,right=37)))
 code='#include <stdio.h>\n#include <string.h>\n'+macros+'\n'+typedefs+r'''
channelstruct vchannel[MAX_CHANNELS];s_soundcache cache; s_soundcache *soundcache=&cache;
int mixing_inited,sound_cached=1,max_channels=12,playfrequency=44100,sample_play_id,reload_result;
int sound_reload_sample(int n){return reload_result;}
'''+body
 code+='\nstruct Case{unsigned mask,priority;int pattern,sample;unsigned speed;int left,right,inited,reload;}cases[]={\n'
 code+=',\n'.join('{'+','.join(str(v)+'u'if k in('mask','priority','speed')else str(v)for k,v in row.items())+'}'for row in rows)+'\n};\n'
 code+=r'''
int main(void){unsigned i;int j,channel,changed;channelstruct before[MAX_CHANNELS];struct Case*c;
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(vchannel,0,sizeof(vchannel));memset(&cache,0,sizeof(cache));sample_play_id=0;mixing_inited=c->inited;reload_result=c->reload;
cache.sample.sampleptr=c->reload?(void*)1:NULL;cache.sample.soundlen=257;cache.sample.frequency=11025;cache.sample.channels=1;
for(j=0;j<12;j++){vchannel[j].active=(c->mask>>j)&1;vchannel[j].priority=c->pattern==0?0:c->pattern==1?7:c->pattern==2?j%3:0xffffffff;vchannel[j].paused=1;}
memcpy(before,vchannel,sizeof(before));channel=sound_play_sample(c->sample,c->priority,c->left,c->right,c->speed);changed=0;
for(j=0;j<64;j++)if(memcmp(before+j,vchannel+j,sizeof(channelstruct)))changed++;
printf("CHANNEL|%u|%d,%d,%d",i,channel,changed,sample_play_id);
if(channel>=0){channelstruct*v=vchannel+channel;printf(",%d,%d,%d,%u,%u,%u,%d,%d,%d,%d",v->samplenum,v->volume[0],v->volume[1],v->priority,v->fp_samplepos,v->fp_period,v->channels,v->active,v->paused,v->playid);}puts("");
}return 0;}
'''
 (a.output/'channels.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','channels.c','-fe=channels.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('SOURCE_CHANNEL_C_BUILD:'+build.stdout+build.stderr)
 log=subprocess.check_output([str(a.output/'channels.exe')],cwd=a.output,text=True);actual=[];expected=[]
 for line,row in zip(log.splitlines(),rows):
  _,index,values=line.split('|');assert int(index)==len(actual);actual.append(list(map(int,values.split(','))))
  free=[i for i in range(count)if not row['mask']>>i&1];channel=free[-1]if free else -1
  if channel<0:
   priorities=[0 if row['pattern']==0 else 7 if row['pattern']==1 else i%3 if row['pattern']==2 else 0xffffffff for i in range(count)]
   minimum=min(priorities)
  # Pinned strict '< UINT_MAX' leaves channel -1 when every priority is max.
  # New priority UINT_MAX in that state reaches vchannel[-1] and is excluded.
   if minimum!=0xffffffff and minimum<=row['priority']:channel=priorities.index(minimum)
  if not row['inited']or row['sample']!=0 or not row['reload']:channel=-1
  result=[channel,int(channel>=0),int(channel>=0)]
  if channel>=0:
   speed=row['speed']or 100;period=(((4096*speed)&0xffffffff)//100*11025&0xffffffff)//44100
   result.extend((0,max(0,min(64,row['left'])),max(0,min(64,row['right'])),row['priority'],((channel*4)%257)*4096,period,1,1,0,1))
  expected.append(result)
 ok=actual==expected and len(actual)==len(rows)
 report=dict(schema='BYOR_4086_SOUND_CHANNEL_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,source_path='engine/source/gamelib/soundmix.c',function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),startup_channel_count=count,startup_expression=startup[0],cases=len(rows),inputs=rows,actual=actual,expected=expected,
  source_free_slot_policy='highest free index',source_preemption_policy='first strictly lowest unsigned priority; reject if greater than new priority',
  excluded_undefined_source_inputs=undefined,undefined_reason='all active priorities UINT_MAX plus new priority UINT_MAX leaves channel -1 and reaches vchannel[-1]; no defined source channel result claimed',
  phase_offset_policy='((channel*4)%soundlen)<<12',source_busy_queue_policy=False,single_stream_native_is_complete_source_channel_backend=False,
  native_channel_backend_proven=False,motu_gameplay_proven=False,no_pcm_copies=True,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'pinned twelve-channel admissions')
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
