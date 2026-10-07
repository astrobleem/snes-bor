"""Actual world-phase7 update_animation prefix, separately from timed advance."""
import argparse,hashlib,json
from pathlib import Path
from compiler import Source
from source_update_animation_inputs import derive,pack
from m4_target_metadata_native import LUA as BASE
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--guards',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);au=json.loads(a.authority.read_text());assert au['status']=='PASS';profile=derive(Source(a.source));table=pack(profile);rows=[]
 for i,(c,e)in enumerate(zip(au['inputs'],au['actual'])):
  slot=(0,1,95,96,127)[i%5];model=i%16;entity=dict(slot=slot,model=model,handle=1,frame=0,exists=1,type=(0,1,2)[i%3],hostile=1,dead=0,invincible=0,detect=-1,hide=-1)
  rows.append(dict(c,slot=slot,model=model,count=128,entities=[entity],expected=e,bad='',fault=0))
 if a.guards:
  seed=next(c for c in rows if c['sealtime']and c['sealtime']<=c['time']);rows=[]
  for slot in (0,1,95,96,127):
   for bad in ('ready','busy','sticky','tick','phase','phase_script','pending','state','time_low','time_high','frame_pending','frame_ready','life_models','self_low','self_high','self_active','self_fault','view','side','models','model_marker','prefix_model_mismatch','core_entities','table_bytes','table_base','table_bank','thaw','map','seal_marker','seal_reserved','sleep_tag','sleep_reserved'):
    rows.append(dict(seed,slot=slot,entities=[dict(seed['entities'][0],slot=slot)],bad=bad,fault=1))
 lua=BASE[:BASE.index('emu.addMemoryCallback(function()local s=emu.getState();cpu=')].replace('TABLESIZE','0')
 setup=r'''
 local s=c.slot;local v=0x414000+s*80;local life=0x439000+s*80;local flags=0x43eb00+s*32;local freeze=0x42e000+s*40
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',7);set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_View',0x4000+s*80);set('SourceWorldTick4086_Side',0x6800+s*64);put(sy.SourceWorldTick4086_TimeLo,c.time,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,v,4);set('SourceFreeze4086_Ready',0xb5df);set('SourceIdle4086_Ready',0xb4f3)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceUpdateAnimationPrefix4086_Ready',0xb60d);set('SourceUpdateAnimationPrefix4086_Status',0);set('SourceUpdateAnimationPrefix4086_Base',0x8000);set('SourceUpdateAnimationPrefix4086_Bank',59);set('SourceUpdateAnimationPrefix4086_Bytes',TABLEBYTES);set('SourceUpdateAnimationPrefix4086_Models',16);set('SourceUpdateAnimationPrefix4086_SleepID',80)
 put(v+16,1,4);put(v+20,c.animnum,4);put(v+28,1,4);put(0x41f510+s*20,c.animating);put(flags,c.idling,4);put(flags+4,0,4);put(flags+24,123,4);put(life+24,c.invincible,4);put(life+28,55,4);put(life+32,c.invinctime,4);put(life+36,66,4);put(life+40,0,4);put(freeze+4,0,4);put(freeze+32,c.sealtime,4);put(0x437e04+s*20,77,4);put(0x437e10+s*20,0xb5fb);put(0x437e12+s*20,0);set('VmSourceWorld_Level',c.level)
 if c.bad=='ready'then set('SourceUpdateAnimationPrefix4086_Ready',0)elseif c.bad=='busy'then set('SourceUpdateAnimationPrefix4086_Status',1)elseif c.bad=='sticky'then set('SourceUpdateAnimationPrefix4086_Status',3)elseif c.bad=='tick'then set('SourceWorldTick4086_Ready',0)elseif c.bad=='phase_script'then set('SourceWorldTick4086_Phase',5)elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',6)elseif c.bad=='pending'then set('SourceWorldTick4086_Pending',0)elseif c.bad=='state'then set('SourceWorldTick4086_State',2)elseif c.bad=='time_low'then put(sy.SourceWorldTick4086_TimeLo,c.time~1,4)elseif c.bad=='time_high'then put(sy.SourceWorldTick4086_TimeLo,c.time~65536,4)elseif c.bad=='frame_ready'then set('SourceUpdateFrame4086_Ready',0)elseif c.bad=='life_models'then set('SourceLifecycle4086_Models',15)elseif c.bad=='frame_pending'then set('SourceUpdateFrame4086_Pending',1)elseif c.bad=='self_low'then put(sy.SourceSelf4086_GlobalLow,0)elseif c.bad=='self_high'then put(sy.SourceSelf4086_GlobalHigh,0)elseif c.bad=='self_active'then set('SourceSelf4086_Active',1)elseif c.bad=='self_fault'then set('SourceSelf4086_Fault',1)elseif c.bad=='view'then set('SourceWorldTick4086_View',0x4001+s*80)elseif c.bad=='side'then set('SourceWorldTick4086_Side',0x6801+s*64)elseif c.bad=='models'then set('SourceUpdateAnimationPrefix4086_Models',15)elseif c.bad=='model_marker'then put(life+74,0)elseif c.bad=='prefix_model_mismatch'then put(life+72,(c.model+1)%16)elseif c.bad=='core_entities'then set('SourceModelEntityCopy4086_Entities',127)elseif c.bad=='table_bytes'then set('SourceUpdateAnimationPrefix4086_Bytes',24+c.model*16+15)elseif c.bad=='table_base'then set('SourceUpdateAnimationPrefix4086_Base',0x7fff)elseif c.bad=='table_bank'then set('SourceUpdateAnimationPrefix4086_Bank',64)elseif c.bad=='thaw'then put(freeze+4,c.time,4)elseif c.bad=='map'then put(life+40,c.time,4)elseif c.bad=='seal_marker'then put(0x437e10+s*20,0)elseif c.bad=='seal_reserved'then put(0x437e12+s*20,1)elseif c.bad=='sleep_tag'then put(v+16,2)elseif c.bad=='sleep_reserved'then put(v+18,1)end
 '''.replace('TABLEBYTES',str(len(table)))
 lua=lua.replace(' before={};',setup+' before={};').replace('{{0x414000,18432}', '{{0x41f500,2560},{0x42e000,5120},{0x43eb00,4096},{0x437e00,2560},{0x414000,18432}')
 lua+=r'''
 emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
 emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
 emu.addMemoryCallback(function()
  local c=rows[word(INDEX)+1];local e=c.expected;local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
  if c.fault==0 then expect(0x43eb18+c.slot*32,e[1],4);for i=2,5 do expect(0x439018+c.slot*80+(i-2)*4,e[i],4)end;expect(0x437e04+c.slot*20,e[6],4)end
  local changed=0;local details='';for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1;if changed<=12 then details=details..string.format('%06x:%02x/%02x,',a,emu.read(a,mt),v)end end end
  if changed~=0 then emu.log('PREFIXDIAG|'..word(INDEX)..'|'..details)end
  emu.log('PREFIXRESULT|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceUpdateAnimationPrefix4086_Status))
 put(sy.VmSourceWorld_Ready,0);put(sy.SourceWorldTick4086_Ready,0)
 end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
 '''
 r=Reporter('M4-UPDATE-ANIMATION-PREFIX',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceUpdateAnimationPrefix4086_Execute','SourceUpdateAnimationPrefix4086_Ready',0xb60d,[(59,0,table)],lua,r,batch_size=4,frame_limit=2000)
 actual=[list(map(int,l.split('PREFIXRESULT|',1)[1].split('|')))for l in log.splitlines()if 'PREFIXRESULT|'in l];expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)];r.check('literal prefix timer/flag updates; actual phase7 owner, unchanged siblings and CPU context',actual==expected)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_UPDATE_ANIMATION_PREFIX_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,guards=a.guards,private_world_leases_parked_after_observation=True,rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),derived_profile=profile,timed_advance_bound=False,thaw_and_palette_restore_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()
if __name__=='__main__':main()
