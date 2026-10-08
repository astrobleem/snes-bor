"""Readonly native twelve-channel selection versus actual pinned mixer."""
import argparse
import hashlib
import json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local started=0;local context=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(sy.SourceSoundChannels4086_Ready,0xb63a);put(sy.SourceSoundChannels4086_Count,12);put(sy.SourceSoundChannels4086_Priority,c.priority,4)
 put(sy.SourceSoundChannels4086_BackendReady,0);put(sy.SourceSoundChannels4086_Sample,0)
 for i=0,11 do
  local p=c.pattern==0 and 0 or c.pattern==1 and 7 or c.pattern==2 and i%3 or 0xffffffff
  put(0x7eff88+i*8,p,4);put(0x7eff8c+i*8,25-i);put(0x7eff8e+i*8,(c.mask>>i)&1)
 end
 if c.bad=='ready'then put(sy.SourceSoundChannels4086_Ready,1)elseif c.bad=='count'then put(sy.SourceSoundChannels4086_Count,11)elseif c.bad=='active'then put(0x7eff8e,3)end
 before={};for a=0x7eff00,0x7effe7 do before[a]=emu.read(a,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();started=s.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();context=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then context=context+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then context=context+1 end
 emu.log('CHANNELCOST|'..word(INDEX)..'|'..(s.masterClock-started))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('SOUNDCHANNEL|'..word(INDEX)..'|'..context..'|'..n..'|'..word(sy.SourceSoundChannels4086_Status)..'|'..word(sy.SourceSoundChannels4086_Selected))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'and authority['startup_channel_count']==12;rows=[]
 for source,result in zip(authority['inputs'],authority['actual']):
  if not source['inited']or source['sample']!=0 or not source['reload']:continue
  rows.append(dict(source,selected=result[0]&65535,status=int(result[0]<0),fault=0))
 rows.append(dict(mask=4095,priority=0xffffffff,pattern=3,sample=0,speed=100,left=64,right=64,inited=1,reload=1,selected=65535,status=3,fault=0,undefined_source_case=True))
 seed=rows[0]
 for bad in('ready','count','active'):rows.append(dict(seed,bad=bad,fault=1,status=2))
 reporter=Reporter('M4-SOUND-CHANNELS',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceSoundChannels4086_Offer','SourceSoundChannels4086_Ready',0xb63a,[],LUA,reporter,batch_size=32,frame_limit=4000)
 actual=[[int(v)for v in line.split('SOUNDCHANNEL|',1)[1].split('|')]for line in log.splitlines()if'SOUNDCHANNEL|'in line]
 expected=[[i,0,0,r['status'],r['selected']]for i,r in enumerate(rows)]
 # Faults have no selected-channel result contract; channel and actor state
 # still must remain readonly and caller CPU context must remain intact.
 for i,r in enumerate(rows):
  if r['fault']and i<len(actual):expected[i][4]=actual[i][4]
 clocks=[int(line.split('CHANNELCOST|',1)[1].split('|')[1])for line in log.splitlines()if'CHANNELCOST|'in line]
 ok=actual==expected;reporter.check('actual source highest-free/lowest-priority/tie policy; readonly all twelve channels and actor controllers; undefined source corner unavailable; malformed compact state faults; CPU context preserved',ok)
 report=dict(schema='BYOR_4086_SOUND_CHANNELS_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
  offer_only=True,channel_state_committed=False,physical_DSP_projection_proven=False,source_phase_offset_proven=False,native_sample_playback_bound=False,measured_offer_master_clocks=dict(min=min(clocks),max=max(clocks))if clocks else None,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
