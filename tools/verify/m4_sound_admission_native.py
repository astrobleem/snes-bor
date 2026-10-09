"""Retained full native channel state versus pinned sound_play_sample."""
import argparse,hashlib,json,struct,re
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols
from source_sound_admission_native import emit
from m4_animation_init_native import luav
W=0x43f000;BASE=0x43f100
LUA=r'''local mt=emu.memType.snesMemory;local before={};local cpu={};local started=0;local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 put(sy.SourceForeignWork_Ready,0xb671);put(sy.SourceForeignWork_Generation,1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,name in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do put(sy[name],0)end
 for i=0,7 do put(sy.DmaQueue+i*8+4,0)end
 put(sy.SourceSoundChannels4086_Ready,0xb63a);put(sy.SourceSoundChannels4086_Count,12);put(sy.SourceSoundChannels4086_Priority,c.priority,4)
 for i=0,11 do
  local priority=c.pattern==0 and 0 or c.pattern==1 and 7 or c.pattern==2 and i%3 or 0xffffffff
  local active=(c.mask>>i)&1;local at=BASE+40*i
  for j,v in ipairs({active,1,25-i,priority,9,-7,8,2,12345,9})do put(at+(j-1)*4,v,4)end
  put(0x7eff88+8*i,priority,4);put(0x7eff8c+8*i,25-i);put(0x7eff8e+8*i,active)
 end
 for i=0,31 do put(W+i,0,1)end
 put(W,0xb63b);put(W+4,0);put(W+6,c.length>>16);put(W+8,c.length&65535);put(W+12,c.period,4);put(W+16,c.left,4);put(W+20,c.right,4);put(W+30,0xb63c)
 if c.bad=='backend'then put(W+30,0)elseif c.bad=='length'then put(W+8,0)elseif c.bad=='sample'then put(W+4,30)elseif c.bad=='generation'then put(sy.SourceForeignWork_Generation,2,4)elseif c.bad=='count'then put(sy.SourceSoundChannels4086_Count,11)elseif c.bad=='active'then put(0x7eff8e,3)elseif c.bad=='replay'then put(W+2,2);put(W+28,12)end
 before={};for i=0,479 do before[BASE+i]=emu.read(BASE+i,mt)end;for i=0,95 do before[0x7eff88+i]=emu.read(0x7eff88+i,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;started=s.masterClock end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if cpu.sp+3~=s['cpu.sp']or(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end;emu.log('SOUNDADMITCOST|'..word(INDEX)..'|'..(s.masterClock-started))end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local function expect(at,v,n)for i=0,(n or 4)-1 do before[at+i]=(v>>(8*i))&255 end end
 if c.selected>=0 and c.fault==0 then
  local at=BASE+40*c.selected
  for j,v in ipairs({1,0,0,c.priority,1,c.gainleft,c.gainright,1,c.phase,c.period})do expect(at+(j-1)*4,v)end
  expect(0x7eff88+8*c.selected,c.priority);expect(0x7eff8c+8*c.selected,0,2);expect(0x7eff8e+8*c.selected,1,2)
 end
 local mismatch=0;for at,v in pairs(before)do if emu.read(at,mt)~=v then mismatch=mismatch+1 end end
 emu.log('SOUNDADMITRESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(W+2)..'|'..word(W+24)..'|'..word(W+26))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','authority','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);r=json.loads(a.authority.read_text());assert r['status']=='PASS';rows=[]
 masks={4095,0,*[4095^(1<<i)for i in range(12)]}
 for c,result in zip(r['inputs'],r['actual']):
  if c['sample']!=0 or not c['inited']or not c['reload']:continue
  if c['mask']not in masks:continue
  rows.append(dict(c,selected=result[0],fault=0,length=257,period=result[-1]if result[0]>=0 else 1024,phase=result[7]if result[0]>=0 else 0,gainleft=result[4]if result[0]>=0 else 0,gainright=result[5]if result[0]>=0 else 0))
 # literal C result indexes: channel,changed,id,sample,L,R,priority,phase,
 # period,channels,active,paused,playid. Period is index 8.
 for c,result in zip(rows,[x for c,x in zip(r['inputs'],r['actual'])if c['sample']==0 and c['inited']and c['reload']and c['mask']in masks]):
  if result[0]>=0:c['period']=result[8]
 # Modulus boundaries not covered by authority's single sample length.
 for n in (1,2,3,4,7,43,44,45,65535,65536,1048575):
  c=dict(rows[0],length=n,selected=11,phase=((11*4)%n)<<12);rows.append(c)
 for bad in ('backend','length','sample','generation','count','active','replay'):rows.append(dict(rows[0],bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));wrapper='''SoundAdmissionFixture:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl SoundAdmission_Run
 bcs SoundAdmissionFixture_Bad
 jsl SoundAdmission_Run
 bcs SoundAdmissionFixture_Bad
 ply
 plx
 plp
 clc
 rtl
SoundAdmissionFixture_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 reporter=Reporter('M4-SOUND-ADMISSION',kind='GATE')
 lua='local admissionSymbols='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(admissionSymbols)do sy[k]=v end\n'+LUA
 lua=re.sub(r'\bW\b',str(W),re.sub(r'\bBASE\b',str(BASE),lua))
 lua+='''\nemu.addMemoryCallback(function()local s=emu.getState();emu.log("ADMISSIONFAULT|"..word(INDEX).."|"..word('''+str(W)+''').."|"..word('''+str(W+30)+''').."|"..word(sy.SourceSoundChannels4086_Status).."|"..s['cpu.x'].."|"..s['cpu.y'].."|"..word(sy.SourceForeignWork_Status))end,emu.callbackType.exec,FAULTPROBE,FAULTPROBE,emu.cpuType.snes,mt)\n'''
 raw,log=run_fixture(a.rom,a.output,rows,'SoundAdmissionFixture','SourceSoundChannels4086_Ready',0xb63a,[],lua,reporter,append=wrapper+emit(W,BASE,sy),probes={'FAULTPROBE':'SoundAdmission_Bad'},batch_size=32,frame_limit=2000,link_pcm=False)
 actual=[list(map(int,l.split('SOUNDADMITRESULT|')[1].split('|')))for l in log.splitlines()if'SOUNDADMITRESULT|'in l]
 expected=[[i,0,0,4 if c['fault']else 2 if c['selected']>=0 else 1,int(not c['fault']and c['selected']>=0),0]for i,c in enumerate(rows)]
 reporter.check('full source channel state commits once under replay; selection, clamps, phase modulus, rejection and leases preserve sibling rows and CPU',actual==expected)
 report=dict(schema='BYOR_SOUND_ADMISSION_NATIVE_V1',status='PASS'if all(v for _,v in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),native_logical_channel_state=True,physical_playback_bound=False,source_frame_ack_bound=False,production_memory_lease=False,private_channel_lease=[BASE,BASE+480],private_controls=[W,W+32],period_metadata_supplied_by_fixture=True,no_pcm_copies=True,no_color_reduction=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()
if __name__=='__main__':main()
