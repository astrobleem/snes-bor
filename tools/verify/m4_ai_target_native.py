"""Direct AI target query over real state, with invalid VM context/arguments."""
import argparse,hashlib,json,struct
from dataclasses import replace
from pathlib import Path
from m4_target_metadata_native import LUA
from m4_script_target_native import cases
from source_target_4086 import find
from source_frame_state_4086 import derive,pack
from compiler import Source
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--offset-only',action='store_true')
 p.add_argument('--normal-selector',action='store_true')
 p.add_argument('--normal-run',action='store_true')
 p.add_argument('--normal-timer-authority',type=Path)
 p.add_argument('--normal-picker',action='store_true')
 p.add_argument('--normal-chance',action='store_true')
 p.add_argument('--action-query',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 if a.normal_chance:a.normal_picker=True
 if a.normal_timer_authority or a.normal_picker:a.normal_selector=True
 ir=derive(Source(a.source));table=pack(ir)
 ids={m['identity']:m['index']for m in json.loads(Path('out/byor-motu-model-attack-policy/report.json').read_text())['models']};frames={}
 for an in ir['animations']:
  for i,f in enumerate(an['frames']):frames.setdefault(bool(f['vulnerable']),(ids[an['model']],an['handle'],i))
 rows=[]
 for name,targets,bad in cases():
  if bad:continue
  order=list(range(len(targets)))
  if name=='reordered_pointer_list':order=[0,2,1]
  entities=[]
  for i,t in enumerate(targets):
   model,handle,frame=frames[t.vulnerable];exists=int(t.alive)
   if name.startswith('source_exists_'):
    _,_,which,n=name.split('_',3)
    if which=='both'or which=='self'and i==0 or which=='target'and i==1:exists=int(n)&0xffffffff
   entities.append(dict(slot=i,model=model,handle=handle,frame=frame,exists=exists,type=t.type,hostile=t.hostile,dead=int(t.dead),invincible=t.invincible,detect=t.detect,hide=t.hide,x=t.x,z=t.z,direction=t.direction))
  rows.append(dict(name=name,count=len(targets),time=48,entities=entities,order=order,bad='',fault=0,expected=find(targets,targets[0].token,order=order)or 0))
 base=rows[0]
 offsets=[]
 for slot in (1,63,127):
  for model in range(16):
   entities=[dict(e)for e in base['entities']]
   for e,s in zip(entities,(slot,(slot+1)%128,(slot+2)%128)):e['slot']=s
   entities[0]['model']=model
   # Deliberately retain the actual current animation from another model.
   expected=0x414000+80*entities[1]['slot']
   offsets.append(dict(base,name='offset_'+str(slot)+'_'+str(model),self=slot,count=128,entities=entities,order=list(range(128)),expected=expected))
 # C does not test self.exists/dead; metadata producer skips its inactive row.
 # Use nonzero stealth to catch accidental use of neutral self metadata.
 for exists in (0,1,65536,0xffffffff):
  for dead in (0,65536):
   entities=[dict(e)for e in base['entities']];entities[0].update(exists=exists,dead=dead,detect=-1);entities[1]['hide']=-1;entities[2]['hide']=0
   rows.append(dict(base,name='self_truth_'+str(exists)+'_'+str(dead),entities=entities,expected=0x414050))
 for bad in ('query_ready','query_busy','common_ready','common_slot','ai_state','entity_lease','entity_base','entity_bank','entity_count','owner_tick','owner_self','self_coordinate','self_direction','ready','busy','world','pool','side','count_zero','count_large','core_ready','entities','core_models','policy','models_zero','models_large','life_ready','life_models','collision','order_ready','order_duplicate','order_range','token_low','token_high','coordinate','coordinate_reserved','direction','wide_type','life_marker','model_range','model_mismatch','handle','frame'):
  rows.append(dict(base,name=bad,bad=bad,fault=1,expected=55))
 if a.offset_only:rows=offsets
 if a.normal_selector:
  rows=[dict(c,fault=int(bool(c['fault']or c['expected'])))for c in rows]
  rows.extend(dict(base,name=b,bad=b,fault=1,expected=55)for b in ('normal_ready','normal_busy','normal_owner','normal_phase','normal_slot'))
 if a.normal_run:
  rows=[dict(c,time=50,fault=int(bool(c['expected'])),advance=1)for c in rows if not c['bad']]
  rows.extend(dict(base,time=50,name=b,bad=b,fault=1,expected=55,advance=int(b=='entry_ready'))for b in ('run_ready','run_busy','grab_ready','entry_ready'))
 if a.normal_timer_authority:
  au=json.loads(a.normal_timer_authority.read_text());assert au['status']=='PASS';timed=[]
  for index in sorted(set(range(0,len(au['inputs']),17))|{0,1,2,3,len(au['inputs'])-1}):
   t=au['inputs'][index];entities=[dict(e)for e in base['entities'][:2]];entities[0]['hostile']=1 if t['found']else 0;entities[1]['x']=65536
   model,handle,frame=frames[bool(t.get('vulnerable',1))];entities[1].update(model=model,handle=handle,frame=frame)
   timed.append(dict(base,name='source_timer_'+str(index),count=2,time=t['time'],entities=entities,order=[0,1],timing=t,bad='',fault=t['requires_body'],expected=0x414050 if t['found']else 0))
  rows=timed
 if a.normal_picker:
  import itertools
  from source_attack_choice_4086 import derive as choice_profile,pack as pack_choice
  from source_animation_range_4086 import derive as range_profile,pack as pack_range
  from source_actor_numeric import random32_step
  profile=choice_profile(Source(a.source));pt=pack_choice(profile);rt=pack_range(range_profile(Source(a.source)))
  rows=[]
  for i,(vulnerable,drop,attacking,action,choice)in enumerate(itertools.product((0,1),(0,1,65536,0xffffffff),(0,65536),(0,6),('absent','near','far'))):
   s=(0,1,63,127)[i%4];target=(s+1)%128;model=(0,4,8,15)[i%4]
   fm,fh,fp=frames[bool(vulnerable)];sm,sh,sf=frames[True]
   entities=[dict(base['entities'][0],slot=s,model=model,handle=sh,frame=sf,x=0,z=220*65536,type=2,hostile=1),dict(base['entities'][1],slot=target,model=fm,handle=fh,frame=fp,x=(1000 if choice=='far'else 1)*65536,z=220*65536,type=1,hostile=0)]
   rejected=not vulnerable and bool(drop or attacking);unbound=not vulnerable and not rejected and action!=0;positive=not rejected and not unbound and choice=='near'
   calls=int(positive);seed_after=random32_step(1)[0]if calls else 1
   rows.append(dict(base,name='picker_gate_'+str(i),self=s,count=128,time=50,entities=entities,order=list(range(128)),bad='',fault=int(unbound or positive),expected=0x414000+80*target,drop=drop,attacking=attacking,action=action,choice=choice,seed_after=seed_after,calls=calls,picker_calls=int(not rejected and not unbound)))
  if a.normal_chance:
   from source_normal_chance_profile import pack as pack_chance
   from source_attack_timing_4086 import derive as timing_profile,pack as pack_timing
   ct=pack_chance(Source(a.source),json.loads(Path('out/byor-motu-normal-chance-authority/report.json').read_text()));dt=Path('out/byor-motu-attack-delay-profile/profile.b4td').read_bytes();tb=pack_timing(timing_profile(Source(a.source)));delaystart=struct.unpack_from('<H',dt,12)[0]
   expanded=[]
   for original in rows:
    for active,seed in ((0,0),(0,1),(1,0),(1,1)):
     c=dict(original,entities=[dict(e)for e in original['entities']],combo_step=65536 if active else 0,combo_time=51,nextattack_after=0,seed=seed,seed_after=random32_step(seed)[0]if original['calls']else seed)
     for e in c['entities']:e['x']-=11*65536
     if original['calls']:
      after,value=random32_step(c['seed_after'])
      if not active:
       c['calls']+=1;c['seed_after']=after
       if value%10000>5000:
        after,value=random32_step(after);delay=struct.unpack_from('<H',dt,delaystart+2*(value%10000))[0];c.update(calls=3,seed_after=after,fault=0,nextattack_after=c['time']+delay)
     expanded.append(c)
   rows=expanded
 lua=LUA.replace('TABLESIZE',str(len(table))).replace('put(v+28,1,4)','put(v+28,e.direction,4)').replace('put(v+52,65536*e.slot,4)','put(v+52,e.x,4)').replace('put(v+60,220*65536,4)','put(v+60,e.z,4)')
 setup=r'''
 set('SourceAITarget4086_Ready',c.bad=='query_ready'and 0 or 0xb5f3);set('SourceAITarget4086_Status',c.bad=='query_busy'and 1 or 0);set('SourceAITarget4086_Result',55);put(sy.SourceAITarget4086_Result+2,0);set('SourceAITarget4086_Selected',55)
 local self=c.self or 0
 set('SourceCommonThink4086_Ready',c.bad=='common_ready'and 0 or 0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',c.bad=='common_slot'and 1 or self)
 set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',c.bad=='ai_state'and 1 or 2);set('SourceAI4086_Slot',self);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 set('SourceWorldTick4086_Ready',c.bad=='owner_tick'and 0 or 0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Slot',self);put(sy.SourceWorldTick4086_TimeLo,c.time,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,c.bad=='owner_self'and 0 or 0x414000+80*self,4)
 set('SourceFreeze4086_Ready',0xb5df);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',128);set('SourceModelAnimationCopy4086_Bytes',4096)
 set('VmSourceEntity_Base',c.bad=='entity_base'and 0x4002 or 0x4000);put(sy.VmSourceEntity_Bank,c.bad=='entity_bank'and 0x42 or 0x41,1);set('VmSourceEntity_Count',c.bad=='entity_count'and c.count+1 or c.count);set('VmSourceEntity_Ready',c.bad=='entity_lease'and 0xb48b or 0xb5ef)
 -- Invalid script-call state proves this entry is a direct native query.
 set('VmNativeVariant_ContextValid',0);put(sy.VmCall_Argc,0,1);set('VmSourceEntity_Index',65535)
 for j=0,7 do emu.write(sy.VmNativeVariant_Result+j,0xa5,mt)end
 for j,v in ipairs(c.order)do put(0x41f200+2*(j-1),v)end
 if c.bad=='order_duplicate'then put(0x41f202,0)elseif c.bad=='order_range'then put(0x41f202,c.count)elseif c.bad=='self_coordinate'then put(0x414030,1)elseif c.bad=='self_direction'then put(0x414018,2)end
'''
 lua=lua.replace(' before={};',setup+' before={};').replace("end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)"," for j=0,7 do before[sy.VmNativeVariant_Result+j]=0xa5 end\nend,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)",1)
 if a.action_query:
  assert not(a.normal_selector or a.normal_run or a.normal_picker)
  rows=[c for c in rows if c['bad']not in ('common_ready','common_slot')]
  lua=lua.replace("set('SourceAI4086_State',c.bad=='ai_state'and 1 or 2)","set('SourceAI4086_State',c.bad=='ai_state'and 2 or 1)")
  lua=lua.replace(' before={};'," set('SourceCommonThink4086_Ready',0);set('SourceCommonThink4086_State',0);set('SourceCommonThink4086_Slot',65535)\n before={};")
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local n=0;')
 lua=lua[:start]+r'''
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('AITARGET|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceAITarget4086_Status)..'|'..(word(sy.SourceAITarget4086_Result)|(word(sy.SourceAITarget4086_Result+2)<<16))..'|'..word(sy.SourceAITarget4086_Selected))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 apply='SourceAITarget4086_Unbounded';ready='SourceAITarget4086_Ready';magic=0xb5f3
 if a.action_query:apply='SourceAITarget4086_ActionUnbounded'
 if a.normal_selector:
  setup=r'''
 set('SourceTryNormalAttack4086_Ready',c.bad=='normal_ready'and 0 or 0xb5f4);set('SourceTryNormalAttack4086_Status',c.bad=='normal_busy'and 2 or 0)
 set('SourceNormalAttack4086_Ready',c.bad=='normal_owner'and 0 or 0xb5eb);set('SourceNormalAttack4086_State',c.bad=='normal_phase'and 4 or 5);set('SourceNormalAttack4086_Slot',c.bad=='normal_slot'and 1 or self);put(sy.SourceNormalAttack4086_Response,55,4)
 for j=0,11 do emu.write(sy.SourceRandom4086_Ready+j,0xa5,mt)end
 for j=0,17 do emu.write(sy.SourceCRandom4086_Ready+j,0x5a,mt)end
'''
  if a.normal_timer_authority:
   setup+=r'''
 set('SourceRecheckNextAttack4086_Ready',0xb5f6);set('SourceRecheckNextAttack4086_Status',0)
 put(0x40c05c,c.timing.timer,4);put(0x40c058+96,c.timing.attacking,4);put(0x43eb0c+32,c.timing.blocking,4);put(0x43eb08+32,c.timing.jumping,4)
'''
  if a.normal_picker:
   setup+=r'''
 set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_Bytes',5376);set('SourceModelAnimationCopy4086_Frames',80)
 for j=0,5375 do emu.write(0x43c000+j,0,mt)end
 local target=c.entities[2].slot;local model=c.entities[1].model
 set('VmSourceEntity_Bank',0x41)
 for _,e in ipairs(c.entities)do put(0x414008+e.slot*80,2,4)end
 if c.choice~='absent'then put(0x43c000+model*336+16,29)end
 set('SourceRecheckNextAttack4086_Ready',0xb5f6);set('SourceRecheckNextAttack4086_Status',0);put(0x40c05c+self*96,0,4);put(0x40c058+target*96,c.attacking,4)
 put(0x437e00+target*20,c.drop,4);put(0x437e10+target*20,0xb5fb);put(0x437e12+target*20,0);put(0x43900c+target*80,c.action,4)
 set('SourceAttackChoiceProfile4086_Ready',0xb5fe);set('SourceAttackChoiceProfile4086_Status',0);set('SourceAttackChoiceProfile4086_Bank',60);set('SourceAttackChoiceProfile4086_Base',PROFILEBASE);set('SourceAttackChoiceProfile4086_Bytes',PROFILEBYTES)
 set('SourceAttackPicker4086_Ready',0xb5ff);set('SourceAttackPicker4086_Status',0);set('SourceEntityRange4086_Ready',0xb5f9);set('SourceEntityRange4086_Status',0);set('SourceCheckRange4086_Ready',0xb5f7);set('SourceCheckRange4086_Status',0);set('SourceAnimationRange4086_Ready',0xb5f8);set('SourceAnimationRange4086_Status',0);set('SourceAnimationRange4086_Bank',60);set('SourceAnimationRange4086_Bytes',RANGEBYTES)
 -- No special roles are present in this mutable-cache domain. Prove the
 -- energy service is not silently executed by leaving its lease invalid.
 set('SourceEntityEnergy4086_Ready',0)
 set('SourceRandom4086_Ready',0xb4d4);put(sy.SourceRandom4086_SeedLo,1,4);put(sy.SourceRandom4086_CallsLo,0xffffffff,4);set('SourceRandom4086_Busy',0)
'''
   if a.normal_chance:
    setup+=r'''
 set('SourceModelEntityCopy4086_Models',16);put(0x437e10+self*20,0xb5fb);put(0x437e12+self*20,0);put(0x437e08+self*20,c.combo_step,4);put(0x437e0c+self*20,c.combo_time,4);put(0x40c038+self*96,0,4)
 set('SourceAttackTiming4086_Ready',0xb603);set('SourceAttackTiming4086_Status',2);set('SourceAttackTiming4086_Models',16)
 for j=0,11 do emu.write(0x438800+self*14+j,timingbytes[29+model*12+j],mt);emu.write(0x40bdc0+j,timingbytes[17+j],mt)end;put(0x438800+self*14+12,0xb603)
 set('SourceEntityNormalChance4086_Ready',0xb601);set('SourceEntityNormalChance4086_Status',0);set('SourceEntityNormalChance4086_Bank',60);set('SourceEntityNormalChance4086_Base',CHANCEBASE);set('SourceEntityNormalChance4086_Bytes',CHANCEBYTES);set('SourceNormalChance4086_Ready',0xb600);set('SourceNormalChance4086_Status',0)
 set('SourceCameraMotion4086_Ready',0xb5db);set('SourceCameraMotion4086_HRes',320);set('SourceCameraMotion4086_VRes',240);put(sy.VmSourceWorld_AdvanceX,0,4)
 set('SourceAttackDelay4086_Ready',0xb604);set('SourceAttackDelay4086_Status',0);set('SourceAttackDelay4086_Bank',60);set('SourceAttackDelay4086_Base',DELAYBASE);set('SourceAttackDelay4086_Bytes',DELAYBYTES)
 put(sy.SourceRandom4086_SeedLo,c.seed,4)
'''
  lua=lua.replace(' before={};',setup+' before={};').replace("end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)"," for j=0,11 do before[sy.SourceRandom4086_Ready+j]=0xa5 end\n for j=0,17 do before[sy.SourceCRandom4086_Ready+j]=0x5a end\nend,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)",1)
  lua=lua.replace("word(sy.SourceAITarget4086_Status)","word(sy.SourceTryNormalAttack4086_Status)").replace("..word(sy.SourceAITarget4086_Selected)","..(word(sy.SourceNormalAttack4086_Response)|(word(sy.SourceNormalAttack4086_Response+2)<<16))")
  apply='SourceTryNormalAttack4086_Execute';ready='SourceTryNormalAttack4086_Ready';magic=0xb5f4
  if a.normal_timer_authority:
   lua=lua.replace('local n=0;for a,v in pairs(before)',r'''local c=rows[word(INDEX)+1];for j=0,3 do before[0x40c05c+j]=(c.timing.after>>(8*j))&255 end
 local n=0;for a,v in pairs(before)''')
  if a.normal_picker:
   lua=lua.replace('local n=0;for a,v in pairs(before)',r'''local c=rows[word(INDEX)+1]
 for _,r in ipairs({{sy.SourceRandom4086_SeedLo,c.seed_after},{sy.SourceRandom4086_CallsLo,(0xffffffff+c.calls)&0xffffffff}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
 local n=0;for a,v in pairs(before)''')
 if a.normal_run:
  lua='local normaltrace={}\n'+lua.replace(' local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)',' local c=rows[word(INDEX)+1];normaltrace={};put(EXPECTFAULT,c.fault)')
  setup=r'''
 set('SourceNormalAttackRun4086_Ready',c.bad=='run_ready'and 0 or 0xb5f5);set('SourceNormalAttackRun4086_Status',c.bad=='run_busy'and 1 or 0)
 set('SourceNormalAttack4086_Ready',0xb5eb);set('SourceNormalAttack4086_State',0)
 set('SourceTryGrab4086_Ready',c.bad=='grab_ready'and 0 or 0xb5ec);set('SourceTryGrab4086_Status',0)
 set('SourceAttackEntry4086_Ready',c.bad=='entry_ready'and 0 or 0xb5ed);set('SourceAttackEntry4086_Status',0)
 set('SourceTryBlock4086_Ready',0xb5f1);set('SourceTryBlock4086_Status',0)
 set('SourceTryNormalAttack4086_Ready',0xb5f4);set('SourceTryNormalAttack4086_Status',0)
 set('SourceAIReadonly4086_Ready',0xb5e8);set('SourceAIReadonly4086_Status',0);put(sy.SourceCommonThink4086_Response,55,4)
 set('SourceRetirement4086_Ready',0xb4f8)
 for _,e in ipairs(c.entities)do put(0x414008+80*e.slot,2,4);put(0x41400c+80*e.slot,0,4)end
 -- Legal missing animations exercise real source absence, not responses.
 for model=0,15 do for _,id in ipairs({12,14,15,17,20,38})do put(0x43c000+256*model+id*2,0)end end
 set('SourceCRandom4086_Ready',0xb5ea);put(sy.SourceCRandom4086_SeedLo,1,4);put(sy.SourceCRandom4086_CallsLo,0xffffffff,4);set('SourceCRandom4086_Busy',0);put(sy.SourceCRandom4086_Result,55,4);set('SourceCRandom4086_Profile',1)
 for j=0,11 do emu.write(sy.SourceRandom4086_Ready+j,0xa5,mt)end
'''
  lua=lua.replace(' before={};',setup+' before={};').replace("end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)"," for j=0,11 do before[sy.SourceRandom4086_Ready+j]=0xa5 end\n for j=0,17 do before[sy.SourceCRandom4086_Ready+j]=emu.read(sy.SourceCRandom4086_Ready+j,mt)end\nend,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)",1)
  lua=lua.replace('local n=0;for a,v in pairs(before)',r'''local c=rows[word(INDEX)+1]
 if c.advance~=0 then for _,r in ipairs({{sy.SourceCRandom4086_SeedLo,2745024},{sy.SourceCRandom4086_CallsLo,0},{sy.SourceCRandom4086_Result,41}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end end
 local n=0;for a,v in pairs(before)''')
  lua=lua.replace("word(sy.SourceAITarget4086_Status)","word(sy.SourceAIReadonly4086_Status)").replace("..word(sy.SourceAITarget4086_Selected)","..(word(sy.SourceCommonThink4086_Response)|(word(sy.SourceCommonThink4086_Response+2)<<16))")
  apply='SourceAIReadonly4086_Execute';ready='SourceNormalAttackRun4086_Ready';magic=0xb5f5
  lua+=r'''
emu.addMemoryCallback(function()
 normaltrace[#normaltrace+1]=word(sy.SourceNormalAttack4086_State)
end,emu.callbackType.exec,sy.SourceNormalAttack4086_Continue,sy.SourceNormalAttack4086_Continue,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('NORMALTRACE|'..word(INDEX)..'|'..word(sy.SourceNormalAttack4086_State)..'|'..word(sy.SourceNormalAttackRun4086_Status)..'|'..table.concat(normaltrace,','))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 tables=[(59,0,table)];append='';bindings=None
 if a.normal_picker:
  tables.append((60,0,rt+pt+(ct+dt if a.normal_chance else b'')))
  if a.normal_chance:
   from m4_animation_init_native import luav
   lua='local timingbytes='+luav(list(tb))+'\n'+lua
   for token,value in dict(CHANCEBASE=0x8000+len(rt)+len(pt),CHANCEBYTES=len(ct),DELAYBASE=0x8000+len(rt)+len(pt)+len(ct),DELAYBYTES=len(dt)).items():lua=lua.replace(token,str(value))
   lua=lua.replace('{{0x437e00,2560}', '{{0x438800,1792},{0x40bdc0,12},{0x437e00,2560}')
   lua=lua.replace('local n=0;for a,v in pairs(before)',r'''for j=0,3 do before[0x40c05c+c.self*96+j]=(c.nextattack_after>>(8*j))&255 end
 local n=0;for a,v in pairs(before)''')
  lua=lua.replace('for j=0,11 do before[sy.SourceRandom4086_Ready+j]=0xa5 end','for j=0,11 do before[sy.SourceRandom4086_Ready+j]=emu.read(sy.SourceRandom4086_Ready+j,mt)end')
  lua=lua.replace('{{0x414000,18432},{0x40c000,12288},{0x42f400,3072},{0x439000,10240},{0x41f200,256}}','{{0x437e00,2560},{0x43c000,8192},{0x43eb00,4096},{0x414000,18432},{0x40c000,12288},{0x42f400,3072},{0x439000,10240},{0x41f200,256}}')
  for token,value in dict(PROFILEBASE=0x8000+len(rt),PROFILEBYTES=len(pt),RANGEBYTES=len(rt)).items():lua=lua.replace(token,str(value))
  append='''
NormalPickerProbe:
.a16
.i16
 jsl PROFILELOAD
 bcc NormalPickerProbe_Execute
 sec
 rtl
NormalPickerProbe_Execute:
.a16
.i16
 jsl NORMALCALL
 rtl
'''
  apply='NormalPickerProbe';bindings=dict(PROFILELOAD='SourceAttackChoiceProfile4086_Load',NORMALCALL='SourceTryNormalAttack4086_Execute')
  lua='local picker_calls=0\n'+lua.replace(' local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)',' local c=rows[word(INDEX)+1];picker_calls=0;put(EXPECTFAULT,c.fault)')
  lua+=r'''
emu.addMemoryCallback(function()picker_calls=picker_calls+1 end,emu.callbackType.exec,sy.SourceAttackPicker4086_Execute,sy.SourceAttackPicker4086_Execute,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('NORMALPICKCOUNT|'..word(INDEX)..'|'..picker_calls)
 emu.log('NORMALPICKSTATE|'..word(INDEX)..'|'..word(sy.SourceAttackPicker4086_Status)..'|'..word(sy.SourceAttackPicker4086_Result)..'|'..word(sy.SourceEntityRange4086_Status)..'|'..word(sy.SourceAnimationRange4086_Status)..'|'..word(sy.SourceCheckRange4086_Status)..'|'..(word(sy.SourceRandom4086_SeedLo)|(word(sy.SourceRandom4086_SeedLo+2)<<16)))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-AI-TARGET',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,ready,magic,tables,lua,r,batch_size=1,append=append,bindings=bindings,frame_limit=6000 if a.normal_chance else 2000)
 results=[list(map(int,l.split('AITARGET|',1)[1].split('|')))for l in log.splitlines()if 'AITARGET|'in l]
 wanted=[[i,0,0,3 if c['fault']else 2,c['expected'],55 if c['fault']else (c['expected']-0x414000)//80 if c['expected']else 65535]for i,c in enumerate(rows)]
 if a.normal_selector:wanted=[[i,0,0,3 if c['fault']else 2,c['expected'],55 if c['fault']else 0]for i,c in enumerate(rows)]
 if a.normal_run:wanted=[[i,0,0,3 if c['fault']else 2,c['expected'],55 if c['fault']else 0]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,results,wanted)if v!=e]
 traces=[]
 if a.normal_run:
  for line in log.splitlines():
   if 'NORMALTRACE|'not in line:continue
   q=line.split('NORMALTRACE|',1)[1].split('|');traces.append([int(q[0]),int(q[1]),int(q[2]),[int(n)for n in q[3].split(',')if n]])
  expected_traces=[]
  for i,c in enumerate(rows):
   state=0 if c['bad']in ('run_ready','run_busy')else 1 if c['bad']=='grab_ready'else 2 if c['bad']=='entry_ready'else 5 if c['fault']else 7
   trace=[]if state in (0,1)else [1]if state==2 else [1,2,3,4]if state==5 else [1,2,3,4,5,6]
   expected_traces.append([i,state,3 if c['fault']else 2,trace])
  r.check('real selector consumption order and native owner completion/fault state',traces==expected_traces)
 r.check('direct real source target selection without VM arguments/context; retired/dead self remains eligible to query; exact typed scratch/CPU/entities/order retained; guarded failures',len(results)==len(rows)and not failures)
 if a.normal_picker:
  picker_counts=[list(map(int,l.split('NORMALPICKCOUNT|',1)[1].split('|')))for l in log.splitlines()if 'NORMALPICKCOUNT|'in l]
  r.check('test-only picker executes exactly after the source rejection gates, with no choice returning false and positive body remaining explicit',picker_counts==[[i,c['picker_calls']]for i,c in enumerate(rows)])
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_AI_TARGET_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16',action_query_entry_bound=a.action_query,normalattack_selector_bound=a.normal_selector or a.normal_run,grounded_common_attack_path_executed=a.normal_run,selector_traces=traces,source_timer_delay_gate_bound=bool(a.normal_timer_authority or a.normal_picker),source_timer_authority_sha256=hashlib.sha256(a.normal_timer_authority.read_bytes()).hexdigest()if a.normal_timer_authority else None,source_vulnerability_attacking_false_gate_bound=bool(a.normal_timer_authority or a.normal_picker),source_testonly_picker_bound=a.normal_picker,source_chance_rejection_nextattack_bound=a.normal_chance,active_combo_skips_chance_bound=a.normal_chance,mutable_cache_domain='normal-role-only'if a.normal_picker else None,picker_call_counts=picker_counts if a.normal_picker else None,normalattack_present_target_body_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()
if __name__=='__main__':main()
