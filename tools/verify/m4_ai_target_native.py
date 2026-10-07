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
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
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
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local n=0;')
 lua=lua[:start]+r'''
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('AITARGET|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceAITarget4086_Status)..'|'..(word(sy.SourceAITarget4086_Result)|(word(sy.SourceAITarget4086_Result+2)<<16))..'|'..word(sy.SourceAITarget4086_Selected))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 apply='SourceAITarget4086_Unbounded';ready='SourceAITarget4086_Ready';magic=0xb5f3
 if a.normal_selector:
  setup=r'''
 set('SourceTryNormalAttack4086_Ready',c.bad=='normal_ready'and 0 or 0xb5f4);set('SourceTryNormalAttack4086_Status',c.bad=='normal_busy'and 2 or 0)
 set('SourceNormalAttack4086_Ready',c.bad=='normal_owner'and 0 or 0xb5eb);set('SourceNormalAttack4086_State',c.bad=='normal_phase'and 4 or 5);set('SourceNormalAttack4086_Slot',c.bad=='normal_slot'and 1 or self);put(sy.SourceNormalAttack4086_Response,55,4)
 for j=0,11 do emu.write(sy.SourceRandom4086_Ready+j,0xa5,mt)end
 for j=0,17 do emu.write(sy.SourceCRandom4086_Ready+j,0x5a,mt)end
'''
  lua=lua.replace(' before={};',setup+' before={};').replace("end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)"," for j=0,11 do before[sy.SourceRandom4086_Ready+j]=0xa5 end\n for j=0,17 do before[sy.SourceCRandom4086_Ready+j]=0x5a end\nend,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)",1)
  lua=lua.replace("word(sy.SourceAITarget4086_Status)","word(sy.SourceTryNormalAttack4086_Status)").replace("..word(sy.SourceAITarget4086_Selected)","..(word(sy.SourceNormalAttack4086_Response)|(word(sy.SourceNormalAttack4086_Response+2)<<16))")
  apply='SourceTryNormalAttack4086_Execute';ready='SourceTryNormalAttack4086_Ready';magic=0xb5f4
 r=Reporter('M4-AI-TARGET',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,ready,magic,[(59,0,table)],lua,r,batch_size=1)
 results=[list(map(int,l.split('AITARGET|',1)[1].split('|')))for l in log.splitlines()if 'AITARGET|'in l]
 wanted=[[i,0,0,3 if c['fault']else 2,c['expected'],55 if c['fault']else (c['expected']-0x414000)//80 if c['expected']else 65535]for i,c in enumerate(rows)]
 if a.normal_selector:wanted=[[i,0,0,3 if c['fault']else 2,c['expected'],55 if c['fault']else 0]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,results,wanted)if v!=e]
 r.check('direct real source target selection without VM arguments/context; retired/dead self remains eligible to query; exact typed scratch/CPU/entities/order retained; guarded failures',len(results)==len(rows)and not failures)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_AI_TARGET_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16',normalattack_selector_bound=a.normal_selector,normalattack_present_target_body_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()
if __name__=='__main__':main()
