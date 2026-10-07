"""Literal normal_prepare absence/wait/empty-role domain on actual actor data."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_frame_state_4086 import derive as frames_profile,pack as pack_frames
from source_attack_choice_4086 import derive as choice_profile,pack as pack_choice
from source_attack_body_profile import derive as body_profile,pack_runtime
from source_actor_numeric import random32_step
from source_script_clone import derive as clone_profile,pack as pack_clone
from script_callback_owner import derive as callback_profile,pack as pack_callback
from m4_target_metadata_native import LUA as BASE_LUA
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''
PrepareProbe:
.a16
.i16
 jsl PROFILELOAD
 bcc PrepareProbe_Ready
 sec
 rtl
PrepareProbe_Ready:
.a16
.i16
 jsl PREPARE
PrepareProbe_After:
.a16
.i16
 nop
 rtl
'''
SETUP=r'''
 local self=c.slot;local v=0x414000+self*80;local side=0x416800+self*64;local life=0x439000+self*80;local flags=0x43eb00+self*32
 set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',1);set('SourceAI4086_Slot',self);put(sy.SourceAI4086_Callback,16,4);set('SourceCommonThink4086_Ready',0);set('SourceCommonThink4086_State',0)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Slot',self);put(sy.SourceWorldTick4086_TimeLo,c.time,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,v,4)
 set('SourceFreeze4086_Ready',0xb5df);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_Bytes',5376);set('SourceModelAnimationCopy4086_Frames',80)
 for j=0,5375 do emu.write(0x43c000+j,0,mt)end
 set('VmSourceEntity_Ready',0xb5ef);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',128);set('VmNativeVariant_ContextValid',0)
 set('SourceAITarget4086_Ready',0xb5f3);set('SourceAITarget4086_Status',0)
 set('SourceAttackBody4086_Ready',0xb605);set('SourceAttackBody4086_Status',0);set('SourceAttackBody4086_Bank',60);set('SourceAttackBody4086_Base',BODYBASE);set('SourceAttackBody4086_Bytes',160)
 local b=self<96 and 0x435980+self*11 or 0x40bdcc+(self-96)*11;for j=0,8 do emu.write(b+j,bodybytes[17+14*9+j],mt)end;put(b,c.noflip,4);put(b+9,0xb605)
 for j=0,3 do emu.write(60*32768+BODYOFFSET+16+14*9+j,(c.noflip>>(8*j))&255,emu.memType.snesPrgRom)end
 put(life+12,16,4);put(flags,55,4);put(flags+28,0,4);put(0x40c058+self*96,66,4);put(side+36,3*65536,4);put(side+40,4*65536,4);put(0x42e008+self*40,c.stalltime,4)
 set('SourceAttackChoiceProfile4086_Ready',0xb5fe);set('SourceAttackChoiceProfile4086_Status',0);set('SourceAttackChoiceProfile4086_Bank',60);set('SourceAttackChoiceProfile4086_Base',0x8000);set('SourceAttackChoiceProfile4086_Bytes',CHOICEBYTES)
 set('SourceNormalPrepare4086_Ready',0xb606);set('SourceNormalPrepare4086_Status',0);set('SourceNormalPrepare4086_TurnID',13)
 set('SourceRandom4086_Ready',0xb4d4);set('SourceRandom4086_Busy',0);put(sy.SourceRandom4086_SeedLo,1,4);put(sy.SourceRandom4086_CallsLo,0xffffffff,4)
 for j=0,7 do emu.write(sy.VmNativeVariant_Result+j,0xa5,mt)end
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--ai-dispatch',action='store_true');p.add_argument('--guards',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';fp=frames_profile(source);ft=pack_frames(fp);pt=pack_choice(choice_profile(source));body=pack_runtime(body_profile(source));ids={m['identity']:m['index']for m in body_profile(source)['models']};sample=next(an for an in fp['animations']if any(f['vulnerable']for f in an['frames']));frame=next(i for i,f in enumerate(sample['frames'])if f['vulnerable']);rows=[]
 for c,e in zip(authority['inputs'],authority['actual']):
  if c['turn']:continue
  i=len(rows);slot=(0,1,95,96,127)[i%5];target=(slot+1)%128;calls=int(c['found']and c['time']>=c['stalltime']);after,value=random32_step(1)
  def entity(s,m,x,t,exists=1,direction=1):return dict(slot=s,model=m,handle=sample['handle'],frame=frame,exists=exists,type=t,hostile=int(t==2),dead=0,invincible=0,detect=-1,hide=-1,x=x,z=220*65536,direction=direction)
  rows.append(dict(c,slot=slot,count=128,entities=[entity(slot,14,0,2,direction=c['direction']),entity(target,ids[sample['model']],c['target_x']*65536,1,exists=c['found'])],bad='',fault=0,expected=e,calls=calls,seed_after=after if calls else 1))
 if a.guards:
  assert not a.ai_dispatch
  base=next(c for c in rows if not c['found']);rows=[]
  for slot in (0,1,95,96,127):
   for bad in ('prepare_ready','prepare_busy','prepare_sticky','ai_state','callback_low','callback_high','action_low','action_high','tick_phase','self_active','self_fault','target_ready','target_busy'):
    c=dict(base,slot=slot,bad=bad,fault=1,calls=0,seed_after=1);c['entities']=[dict(base['entities'][0],slot=slot),dict(base['entities'][1],slot=(slot+1)%128)];rows.append(c)
 lua=BASE_LUA[:BASE_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local n=0;')]
 lua=lua[:lua.index('emu.addMemoryCallback(function()local s=emu.getState();cpu=')]
 lua=lua.replace('TABLESIZE',str(len(ft))).replace('put(v+28,1,4)','put(v+28,e.direction,4)').replace('put(v+52,65536*e.slot,4)','put(v+52,e.x,4)').replace('put(v+60,220*65536,4)','put(v+60,e.z,4)').replace(' before={};',SETUP+' before={};').replace('BODYBASE',str(0x8000+len(pt))).replace('BODYOFFSET',str(len(pt))).replace('CHOICEBYTES',str(len(pt)))
 tables=[(59,0,ft),(60,0,pt+body)]
 if a.ai_dispatch:
  clone=pack_clone(clone_profile(source));cb,*_=callback_profile(source);callbacks=pack_callback(cb);clone_offset=len(pt)+len(body);callback_offset=clone_offset+len(clone);tables=[(59,0,ft),(60,0,pt+body+clone+callbacks)]
  install="""
 set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);set('SourceAI4086_State',0);put(sy.SourceAI4086_Endgame,0,4);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 put(side+20,c.time,4);put(life,0,4);put(0x41f510+self*20,1);put(0x42e024+self*40,0,4)
 local rel=0x409000+self*64;put(0x410000+self*64,v,4);put(rel+44,0,4)
 set('VmSourceWorld_TemplateCount',16);set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 """
  for name,value in dict(SourceScriptClone4086_Ready=0xb5c1,SourceScriptClone4086_Status=0,SourceScriptClone4086_Base=0x8000+clone_offset,SourceScriptClone4086_Bank=60,SourceScriptClone4086_Bytes=len(clone),SourceScriptClone4086_Models=16,SourceAnimationCallback4086_Ready=0xb4e6,SourceAnimationCallback4086_Base=0x8000+callback_offset,SourceAnimationCallback4086_Bank=60,SourceAnimationCallback4086_Models=16,SourceAnimationCallback4086_Programs=cb['program_count']).items():install+=" set('"+name+"',"+str(value)+")\n"
  lua=lua.replace(' before={};',install+' before={};')
 if a.guards:
  guard="""
 local guards={prepare_ready={'SourceNormalPrepare4086_Ready',0},prepare_busy={'SourceNormalPrepare4086_Status',1},prepare_sticky={'SourceNormalPrepare4086_Status',3},ai_state={'SourceAI4086_State',2},callback_low={'SourceAI4086_Callback',15},callback_high={'SourceAI4086_Callback',1},tick_phase={'SourceWorldTick4086_Phase',5},self_active={'SourceSelf4086_Active',1},self_fault={'SourceSelf4086_Fault',1},target_ready={'SourceAITarget4086_Ready',0},target_busy={'SourceAITarget4086_Status',1}}
 local g=guards[c.bad];if g then if c.bad=='callback_high'then put(sy[g[1]]+2,g[2])else set(g[1],g[2])end end
 if c.bad=='action_low'then put(life+12,15)elseif c.bad=='action_high'then put(life+14,1)end
 """
  lua=lua.replace(' before={};',guard+' before={};')
 lua='local bodybytes='+luav(list(body))+'\nlocal choicebytes='+luav(list(pt))+'\n'+lua
 lua=lua.replace('{{0x414000,18432}','{{0x435800,1536},{0x40bdcc,352},{0x42e000,5120},{0x43eb00,4096},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r'''
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,PREPARE,PREPARE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,PREPAREAFTER,PREPAREAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local e=c.expected;local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
 if AIDISPATCH then expect(0x42e024+c.slot*40,2,4)end
 if c.fault==0 then
 expect(0x416824+c.slot*64,0,4);expect(0x416828+c.slot*64,0,4);expect(0x43eb00+c.slot*32,e[2],4);expect(0x41401c+c.slot*80,e[3],4);expect(0x43900c+c.slot*80,e[4]==0 and 0 or 16,4)
 end
 expect(sy.SourceRandom4086_SeedLo,c.seed_after,4);expect(sy.SourceRandom4086_CallsLo,(0xffffffff+c.calls)&0xffffffff,4)
 for j=17,#choicebytes do before[0x435900+j-17]=choicebytes[j]end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 if changed~=0 then local details='';local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v and n<12 then details=details..string.format('%06x:%02x/%02x,',a,emu.read(a,mt),v);n=n+1 end end;emu.log('PREPAREDIAG|'..word(INDEX)..'|'..details)end
 emu.log('PREPAREBODY|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNormalPrepare4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 lua=lua.replace('AIDISPATCH','true'if a.ai_dispatch else'false')
 reporter=Reporter('M4-NORMAL-PREPARE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'PrepareProbe','SourceNormalPrepare4086_Ready',0xb606,tables,lua,reporter,append=ASM,bindings=dict(PROFILELOAD='SourceAttackChoiceProfile4086_Load',PREPARE='SourceAIRun4086_Begin'if a.ai_dispatch else'SourceNormalPrepare4086_Execute'),probes=dict(PREPAREAFTER='PrepareProbe_After'),batch_size=1,frame_limit=6000)
 actual=[list(map(int,l.split('PREPAREBODY|',1)[1].split('|')))for l in log.splitlines()if 'PREPAREBODY|'in l];expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('literal C absence/wait/empty-role state, source direction/full32 noflip/unsigned timer, one real RNG only after wait, actual target query, CPU/VM/CRT/actor/sibling retention',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_NORMAL_PREPARE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:10],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),guard_cases=a.guards,domain='TURN absent, NULL held weapon, all normal/special cache roles absent, chainlength 1; synthetic noflip profile scalars from C domain',actual_ai_dispatcher_executed=a.ai_dispatch,present_attack_selection_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
