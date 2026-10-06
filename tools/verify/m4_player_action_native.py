"""Player source spawn/drop preparation; real JUMP service required next."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_default_choice_4086 import choose
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x438fc0,64},{0x439000,10240},{0x43b800,64},{0x40c000,12288},{0x414000,10240},{0x416800,8192},{0x43c000,8192},{0x41f500,2560},{0x43e000,512}}
local before,cpu,start,ctx={},{},0,0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0,mt)end end
 for i=0,127 do
  local a=0x414000+i*80;put(a,a,4);put(a+4,1)
  for n,tag in ipairs({2,1,1,1,1,2,2,1})do put(a+n*8,tag,4)end
 end
 put(0x40c048+c.slot*96,c.type,4)
 for i=0,127 do put(0x43904a+i*80,0xb4fb)end
 put(0x439038+c.slot*80,c.makeinv,4)
 put(0x416804+c.slot*64,c.chosen~=0xffff and c.chosen or c.existing==1 and 1 or 0)
 put(0x41400c+c.slot*80,c.a_raw,4)
 for i=0,3 do put(sy.SourcePlayerSpawnHeight4086_Heights+i*4,c.spawn_y<<16,4)end
 set('SourcePlayerSpawnHeight4086_Ready',0xb505);set('SourcePlayerSpawnHeight4086_Stage',1);set('SourcePlayerSpawnHeight4086_Status',0)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',1)
 set('SourceDefaultPlayer4086_Jump',4)
 set('VmSourceWorld_Level',1);set('VmSourceWorld_SideBase',0x6800)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',2)
 set('SourceDefaultPlayer4086_Ready',0xb503);set('SourceDefaultPlayer4086_Status',0);set('SourceDefaultPlayer4086_Slot',c.slot)
 put(0x40c050+c.slot*96,123,4);put(0x40c054+c.slot*96,77,4)
 for i=0,2559 do emu.write(0x41f500+i,165,mt)end
 for i=0,511 do emu.write(0x43e000+i,165,mt)end
 for n=1,4 do put(0x43c000+n*2,(c.mask&(1<<n))~=0 and n or 0)end
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_Count',128)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',1)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',1);set('SourceModelAnimationCopy4086_Maximum',6);set('SourceModelAnimationCopy4086_Bytes',12)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',4)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',c.service==1 and 2 or 0);set('SourceAnimationInit4086_Slot',c.slot);set('SourceAnimationInit4086_Base',0x8000);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',AIBYTES);set('SourceAnimationInit4086_Handles',4)
 set('SourceAnimationInit4086_Issued',0xa5a5)
 set('SourceDefaultChoice4086_Ready',0xb4fa);set('SourceDefaultChoice4086_Status',2);set('SourceDefaultChoice4086_Service',c.service);set('SourceDefaultChoice4086_Slot',c.slot);set('SourceDefaultChoice4086_Select',c.select);put(sy.SourceDefaultChoice4086_TimeLo,c.time,4)
 set('SourceDefaultChoice4086_Spawn',1);set('SourceDefaultChoice4086_Respawn',2);set('SourceDefaultChoice4086_Selection',3)
 if c.bad=='height_ready'then set('SourcePlayerSpawnHeight4086_Ready',0xffff)
 elseif c.bad=='height_stage'then set('SourcePlayerSpawnHeight4086_Stage',2)
 elseif c.bad=='height_fraction'then put(sy.SourcePlayerSpawnHeight4086_Heights,1)
 elseif c.bad=='player_tag'then put(0x414028+c.slot*80,2)
 elseif c.bad=='a_tag'then put(0x414008+c.slot*80,1)
 elseif c.bad=='a_reserved'then put(0x41400a+c.slot*80,1)
 elseif c.bad=='player_ready'then set('SourceDefaultPlayer4086_Ready',0xffff)
 elseif c.bad=='player_sticky'then set('SourceDefaultPlayer4086_Status',3)
 elseif c.bad=='life_ready'then set('SourceLifecycle4086_Ready',0xffff)
 elseif c.bad=='life_sticky'then set('SourceLifecycle4086_Status',3)
 elseif c.bad=='life_marker'then put(0x43904a+c.slot*80,0)
 elseif c.bad=='life_model'then put(0x439048+c.slot*80,1)
 elseif c.bad=='makeinv_min'then put(0x439038+c.slot*80,0x80000000,4)
 elseif c.bad=='empty_animation'then put(0x416804+c.slot*64,0)
 elseif c.bad=='type_high'then put(0x40c04a+c.slot*96,1)
 elseif c.bad=='type_mixed'then put(0x40c048+c.slot*96,3)
 elseif c.bad=='level'then set('VmSourceWorld_Level',0)
 elseif c.bad=='side'then set('VmSourceWorld_SideBase',0x6802)
 elseif c.bad=='token'then put(0x414000+c.slot*80,0)
 elseif c.bad=='alive'then put(0x414004+c.slot*80,0)
 elseif c.bad=='choice_pending'then set('SourceDefaultChoice4086_Status',1)
 elseif c.bad=='choice_slot'then set('SourceDefaultChoice4086_Slot',128)
 elseif c.bad=='init_not_finished'then set('SourceAnimationInit4086_State',0)
 elseif c.bad=='init_slot'then set('SourceAnimationInit4086_Slot',128)
 elseif c.bad=='ready'then set('SourceDefaultChoice4086_Ready',0)
 elseif c.bad=='sticky'then set('SourceDefaultChoice4086_Status',3)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourceDefaultChoice4086_Slot',128)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='core_count'then set('SourceModelEntityCopy4086_Entities',127)
 elseif c.bad=='cache'then set('SourceModelAnimationCopy4086_Ready',0)
 elseif c.bad=='pending'then set('SourceAnimationInit4086_State',1)
 elseif c.bad=='table'then set('SourceAnimationInit4086_Base',0x8002)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 local s=emu.getState();start=s.masterClock;cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then
  local function expect(a,v)for i=0,3 do before[a+i]=(v>>(8*i))&255 end end
  for _,r in ipairs(c.fields)do expect(0x439000+c.slot*80+r[1],r[2])end
  expect(0x41400c+c.slot*80,c.expected_a)
 end
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp~=s['cpu.sp'] or(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('CHOICECOST|'..word(INDEX)..'|'..(s.masterClock-start)..'|'..s['cpu.a'])
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local mismatch=0;for a,n in pairs(before)do if emu.read(a,mt)~=n then mismatch=mismatch+1 end end
 emu.log('CHOICERESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(sy.SourceDefaultPlayer4086_Status))

end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';rows=[];seen=set()
 for ar in authority['results']:
  c=ar['case']
  if c['type']!=1 or c['level']!=1 or c['mutation']or c['environment']:continue
  chosen=choose(1,c['select'],c['time'],lambda n:c['mask']&(1<<n),1,2,3)
  key=(c['mask']&30,c['time'],c['select'],chosen,c['existing'],c['spawn_y'],c['a_raw'])
  if key in seen:continue
  seen.add(key);state=ar['actual']['state'];fields=[[0,state[21]],[4,state[20]],[8,state[22]],[12,state[23]]]
  import struct
  expected_a=int(struct.unpack('<f',struct.pack('<I',state[15]))[0]*65536)
  needs_jump=int(any(ar['actual']['trace'][i:i+2]==[1,4]for i in range(0,len(ar['actual']['trace']),2)))
  # Interior source matrix is checked once; boundary slots also cover each
  # decision, height and direction through source-derived representative cases.
  slots=(0,1,127)if c['mask']in(0,16)and c['select']==0 and c['existing']==0 and c['a_raw']in(0,32768) else (0,)
  for slot in slots:rows.append(dict(type=1,slot=slot,mask=c['mask']&30,select=c['select'],time=c['time'],makeinv=c['makeinv'],chosen=chosen if chosen else 0xffff,service=int(chosen is not None),existing=c['existing'],a_raw=c['a_raw'],spawn_y=c['spawn_y'],expected_a=expected_a,needs_jump=needs_jump,fault=0,bad='',fields=fields))
 base=next(r for r in rows if r['needs_jump']and r['chosen']==0xffff and r['spawn_y']==300 and r['a_raw']==0)
 for bad in ('height_ready','height_stage','height_fraction','player_tag','a_tag','a_reserved','player_ready','player_sticky','life_ready','life_sticky','life_marker','life_model','makeinv_min','type_high','type_mixed','level','side','token','alive','choice_pending','choice_slot','ready','sticky','world','count','slot','core','core_count','cache','pending','table'):
  for slot in (0,127):rows.append(dict(base,slot=slot,fault=1,bad=bad))
 ai=pack_ai(dict(maximum_animations=6,animations=[dict(handle=n,numframes=1,sync=-1,engine_animation_id=n)for n in (1,2,3,4)]))
 fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=n,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)])for n in (1,2,3,4)]))
 reporter=Reporter('M4-PLAYER-ACTION',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultPlayer4086_PrepareAction','SourceDefaultPlayer4086_Ready',0xb503,[(59,0,ai),(60,0,fe)],LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))),reporter);results=[];costs=[]
 for line in log.splitlines():
  for marker,target in [('CHOICERESULT|',results),('CHOICECOST|',costs)]:
   if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
 reporter.check('source player callback/action fields and exact spawn-height projection; physical/context guards',len(results)==len(rows)and all(r==[i,0,0,3 if c['fault']else 2]for i,(r,c)in enumerate(zip(results,rows))))
 reporter.check('JUMP service only for actual source branch',len(costs)==len(rows)and all(c['fault']or r[2]==c['needs_jump']for r,c in zip(costs,rows)))
 r=dict(schema='BYOR_4086_PLAYER_ACTION_PREPARATION_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,costs=costs,first_animation_completion_instrumented=True,source_jump_service_prepared=True,actual_ent_set_anim_jump_bound=False,jump_frame_zero_bound=False,post_jump_makeinv_bound=False,final_idle_environment_bound=False,executable_callbacks_bound=False,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
