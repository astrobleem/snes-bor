"""Actual NPC runoff through callback17 completion, with native shared RNG."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_frame_state_4086 import derive as frames,pack as pack_frames
from source_frame_effects_4086 import derive as effects,pack as pack_effects
from source_animation_init_4086 import derive as init,pack as pack_init
from source_adjust_walk_requirements import derive as walk_profile
from source_actor_numeric import random32_step
from m4_target_metadata_native import LUA as BASE
from m4_attack_finish_native import FINISH_SETUP,FRAMEZERO_SETUP
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--ai-dispatch',action='store_true');p.add_argument('--guards',action='store_true');p.add_argument('--complete-framezero',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);au=json.loads(a.authority.read_text());assert au['status']=='PASS';source=Source(a.source);ft=pack_frames(frames(source));fe=pack_effects(effects(source));it=pack_init(init(source));cap=walk_profile(source);roles=cap['roles'];seeds={}
 for seed in range(1000):
  after,value=random32_step(seed);seeds.setdefault(value&3,seed)
 assert len(seeds)==4
 rows=[]
 for i,(c,e)in enumerate(zip(au['inputs'],au['actual'])):
  slot=(0,1,95,96,127)[i%5];target=(slot+1)%128;seed=seeds[c['rand']];after,value=random32_step(seed)
  entities=[dict(slot=n,model=0,handle=1,frame=0,exists=1,type=t,hostile=1,dead=0,invincible=0,detect=-1,hide=-1)for n,t in [(slot,c['type']),(target,1)]]
  rows.append(dict(c,slot=slot,target_slot=target,count=128,model=0,entities=entities,bad='',fault=0,expected=e,seed=seed,after=after,value=value,calls=(0xffffffff,65536)[i%2]))
 if a.guards:
  assert not a.complete_framezero
  seed=next(c for c in rows if c['expected'][9]==1 and c['x']<c['target_x']);rows=[]
  for slot in (0,1,95,96,127):
   target=(slot+1)%128
   for bad in ('runoff_ready','runoff_busy','runoff_sticky','movement_ready','cost_ready','rng_ready','rng_busy','target_low','target_high','self_x_tag','self_x_reserved','target_x_tag','target_x_reserved','speed_marker','walkmode','walkmode_high','up_present','down_present','back_present','walk_id','self_z_tag','self_z_reserved','direction_tag','direction_reserved','speed_negation','coordinate_overflow'):
    rows.append(dict(seed,slot=slot,target_slot=target,entities=[dict(seed['entities'][0],slot=slot),dict(seed['entities'][1],slot=target)],bad=bad,fault=1))
 lua=BASE[:BASE.index('emu.addMemoryCallback(function()local s=emu.getState();cpu=')].replace('TABLESIZE',str(len(ft)))
 setup=FINISH_SETUP.replace('INITBASE',str(0x8000+len(ft))).replace('INITBYTES',str(len(it)))
 setup+=r"""
 put(0x42f404+s*24,c.running or 0,4);put(0x43c000+2*RUN,c.run_present==1 and 1 or 0);put(0x43c000+2,1);put(v+52,math.floor(c.x*65536),4);put(v+60,math.floor(c.z*65536),4);put(v+28,c.direction,4)
 put(0x414034+c.target_slot*80,math.floor(c.target_x*65536),4);put(0x41403c+c.target_slot*80,math.floor(c.target_z*65536),4)
 put(life+52,c.nomove,4);put(life+76,0xb508);put(side+60,math.floor(c.speed*65536),4);put(0x41f510+s*20,0)
 put(0x40900c+s*64,c.present==1 and 0x414000+c.target_slot*80 or 0,4)
 set('SourceAttackCostState4086_Ready',0xb609);set('SourceMovementState4086_Ready',0xb60b);set('SourceAttackRunoff4086_Ready',0xb60c);set('SourceAttackRunoff4086_Status',0);set('SourceAttackRunoff4086_Mode',0)
 put(0x43da00+s*8,111*65536,4);put(0x43da04+s*8,222*65536,4)
 set('SourceAttackRunoff4086_WalkID',WALK);set('SourceAttackRunoff4086_UpID',UP);set('SourceAttackRunoff4086_DownID',DOWN);set('SourceAttackRunoff4086_BackID',BACK);set('SourceAttackRunoff4086_RunID',RUN)
 set('SourceRetirement4086_Ready',0xb4f8);set('SourceRetirement4086_Status',0)
 set('SourceRandom4086_Ready',0xb4d4);set('SourceRandom4086_Busy',0);put(sy.SourceRandom4086_SeedLo,c.seed,4);put(sy.SourceRandom4086_CallsLo,c.calls,4)
 put(sy.VmNativeVariant_Result,2,4);put(sy.VmNativeVariant_Result+4,0x12345678,4)
 """
 if a.guards:
  setup+=r'''
 if c.bad=='runoff_ready'then set('SourceAttackRunoff4086_Ready',0)elseif c.bad=='runoff_busy'then set('SourceAttackRunoff4086_Status',1)elseif c.bad=='runoff_sticky'then set('SourceAttackRunoff4086_Status',3)elseif c.bad=='movement_ready'then set('SourceMovementState4086_Ready',0)elseif c.bad=='cost_ready'then set('SourceAttackCostState4086_Ready',0)elseif c.bad=='rng_ready'then set('SourceRandom4086_Ready',0)elseif c.bad=='rng_busy'then set('SourceRandom4086_Busy',1)elseif c.bad=='target_low'then put(0x40900c+s*64,0x414001+c.target_slot*80,4)elseif c.bad=='target_high'then put(0x40900e+s*64,0)elseif c.bad=='self_x_tag'then put(v+48,1)elseif c.bad=='self_x_reserved'then put(v+50,1)elseif c.bad=='target_x_tag'then put(0x414030+c.target_slot*80,1)elseif c.bad=='target_x_reserved'then put(0x414032+c.target_slot*80,1)elseif c.bad=='speed_marker'then put(life+76,0)elseif c.bad=='walkmode'then put(life+44,2,4)elseif c.bad=='walkmode_high'then put(life+46,1)elseif c.bad=='up_present'then put(0x43c000+2*UP,1)elseif c.bad=='down_present'then put(0x43c000+2*DOWN,1)elseif c.bad=='back_present'then put(0x43c000+2*BACK,1)elseif c.bad=='walk_id'then set('SourceAttackRunoff4086_WalkID',168)elseif c.bad=='self_z_tag'then put(v+56,1)elseif c.bad=='self_z_reserved'then put(v+58,1)elseif c.bad=='direction_tag'then put(v+24,2)elseif c.bad=='direction_reserved'then put(v+26,1)elseif c.bad=='speed_negation'then put(side+60,0x80000000,4)elseif c.bad=='coordinate_overflow'then put(v+52,-32760*65536,4);put(0x414034+c.target_slot*80,-32759*65536,4)end
 '''
 if a.ai_dispatch:
  assert a.complete_framezero and not a.guards
  setup+="\n set('SourceCommonAttackProc4086_Ready',0xb607);set('SourceCommonAttackProc4086_Status',0);set('SourceAttackCostPay4086_Ready',0xb60a);set('SourceAttackCostPay4086_Status',0);put(0x43de00+s*4,0,4);put(0x43fd94,0,4);put(flags+16,0,4);put(flags+28,0,4);put(v+8,2,4);put(v+12,0,4);put(side+48,0,4);set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);set('SourceAIRun4086_PendingKind',0);set('SourceAI4086_State',0);put(sy.SourceAI4086_Endgame,0,4);put(side+20,0,4);put(0x42e024+s*40,17,4)\n"
 for token,value in [('WALK',roles['walk']),('UP',roles['up']),('DOWN',roles['down']),('BACK',roles['backwalk']),('RUN',roles['run'])]:setup=setup.replace(token,str(value))
 tables=[(58,0,fe),(59,0,ft+it)]
 if a.complete_framezero:
  from script_callback_owner import derive as callbacks_profile,pack as pack_callbacks
  from source_script_clone import derive as clone_profile,pack as pack_clone
  from source_frame_effect_plan import derive as plan_profile,pack as pack_plan
  cb,*_=callbacks_profile(source);callbacks=pack_callbacks(cb);clone=pack_clone(clone_profile(source));plan=pack_plan(plan_profile(effects(source)))
  assert cb['models'][0]['program']==65535
  tables=[(58,0,fe+callbacks+clone),(59,0,ft+it+plan)]
  complete_setup=FRAMEZERO_SETUP
  for token,value in dict(PROGRAMS=cb['program_count'],CALLBACKBASE=0x8000+len(fe),CALLBACKBYTES=len(callbacks),EFFECTBYTES=len(fe),PLANBASE=0x8000+len(ft)+len(it),PLANBYTES=len(plan),PAIREDCRC=struct.unpack_from('<I',plan,24)[0],BODYCRC=struct.unpack_from('<I',plan,28)[0],CLONEBASE=0x8000+len(fe)+len(callbacks),CLONEBYTES=len(clone)).items():complete_setup=complete_setup.replace(token,str(value))
  setup+=complete_setup+"put(side+4,2);put(0x41f508+s*20,123,4);put(0x40c054+s*96,99,4)\n"
 lua=lua.replace(' before={};',setup+' before={};').replace('{{0x414000,18432}','{{0x43eb00,4096},{0x42e000,5120},{0x416800,8192},{0x41f500,2560},{0x43e000,512},{0x409000,8192},{0x438800,1792},{0x40b000,2560},{0x43c000,8192},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r"""
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local e=c.expected
 local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
 if c.fault==0 then
 expect(0x43900c+c.slot*80,0,4);expect(0x416824+c.slot*64,e[3],4);expect(0x416828+c.slot*64,e[4],4);expect(0x42e008+c.slot*40,e[8],4)
 expect(0x43eb00+c.slot*32,e[5],4);expect(0x41f510+c.slot*20,e[6],2);expect(0x43da00+c.slot*8,e[1],4);expect(0x43da04+c.slot*8,e[2],4)
 if e[11]==1 then expect(0x43eb04+c.slot*32,0,12);expect(0x40c058+c.slot*96,0,4)end
 if e[9]==1 then expect(sy.SourceRandom4086_SeedLo,c.after,4);expect(sy.SourceRandom4086_CallsLo,(c.calls+1)&0xffffffff,4);expect(sy.VmNativeVariant_Result,1,4);expect(sy.VmNativeVariant_Result+4,c.value,4)end
 end
 local changed=0;local details='';for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1;if changed<=12 then details=details..string.format('%06x:%02x/%02x,',a,emu.read(a,mt),v)end end end
 if changed~=0 then emu.log('RUNOFFDIAG|'..word(INDEX)..'|'..details)end
 emu.log('RUNOFFRESULT|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceCommonAttackFinish4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""
 lua+="for _,name in ipairs({'SourceAttackRunoff4086_Bad','SourceCommonAttackFinish4086_Bad','SourceAnimationInit4086_Bad','SourceAnimationInit4086_ResolveBad'})do emu.addMemoryCallback(function()emu.log('RUNOFFGUARD|'..name..'|row '..word(INDEX)..'|mode '..word(sy.SourceAttackRunoff4086_Mode)..'|status '..word(sy.SourceAttackRunoff4086_Status)..'|init '..word(sy.SourceAnimationInit4086_State)..'|num '..word(sy.SourceAnimationInit4086_Number)..'|slot '..word(sy.SourceAnimationInit4086_Slot))end,emu.callbackType.exec,sy[name],sy[name],emu.cpuType.snes,mt)end\n"
 append='';bindings={};apply='SourceCommonAttackFinish4086_Execute'
 if a.complete_framezero:
  lua=lua.replace('end\n local changed=0;local details=',"if e[11]==1 or(e[10]==1 and(not c.running or c.run_present==1))then expect(0x416804+c.slot*64,1,2);expect(0x416806+c.slot*64,0,2);expect(0x414014+c.slot*80,e[10]==1 and(c.running and 37 or 1)or 0,4);expect(0x416808+c.slot*64,c.time+8,4);expect(0x41f508+c.slot*20,0,4);expect(0x40c054+c.slot*96,0,4);expect(0x43e004,0,4);if e[11]==1 or c.running then expect(0x41f510+c.slot*20,1,2)end end\n end\n local changed=0;local details=")
  apply='RunoffFrameProbe';append='RunoffFrameProbe:\n.a16\n.i16\n php\n rep #$38\n jsl FINISH\n bcs RunoffFrameProbe_Bad\n cmp #0\n beq RunoffFrameProbe_Done\n cmp #1\n bne RunoffFrameProbe_Bad\n jsl STARTFRAME\n bcs RunoffFrameProbe_Bad\n jsl CALLBACKBEGIN\n bcs RunoffFrameProbe_Bad\n jsl CALLBACKRUN\n bcs RunoffFrameProbe_Bad\n cmp #4\n bne RunoffFrameProbe_Bad\n lda #1\n jsl FRAMEACK\n bcs RunoffFrameProbe_Bad\n jsl EFFECTRUN\n bcs RunoffFrameProbe_Bad\n cmp #0\n bne RunoffFrameProbe_Bad\n jsl CONTINUE\n bcs RunoffFrameProbe_Bad\nRunoffFrameProbe_Done:\n.a16\n.i16\n plp\n clc\n rtl\nRunoffFrameProbe_Bad:\n.a16\n.i16\n plp\n sec\n rtl\n';bindings=dict(FINISH='SourceCommonAttackFinish4086_Execute',STARTFRAME='SourceAnimationInit4086_StartFrame',CALLBACKBEGIN='SourceAnimationCallback4086_Begin',CALLBACKRUN='SourceAnimationCallback4086_Run',FRAMEACK='SourceUpdateFrame4086_Ack',EFFECTRUN='SourceFrameEffects4086_Run',CONTINUE='SourceCommonAttackFinish4086_Continue')
 if a.ai_dispatch:
  bindings.update(FINISH='SourceAIRun4086_Begin',CONTINUE='SourceAIRun4086_Continue')
  lua=lua.replace('if c.fault==0 then\n','if c.fault==0 then\n expect(0x40c058+c.slot*96,0,4);expect(0x42e024+c.slot*40,19,4)\n',1)
  lua+="emu.addMemoryCallback(function()emu.log('RUNOFFAI|'..word(INDEX)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAIRun4086_PendingKind))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 r=Reporter('M4-ATTACK-RUNOFF',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceCommonAttackFinish4086_Ready',0xb608,tables,lua,r,append=append,bindings=bindings,batch_size=2 if a.complete_framezero else 4,frame_limit=4000)
 actual=[list(map(int,l.split('RUNOFFRESULT|',1)[1].split('|')))for l in log.splitlines()if 'RUNOFFRESULT|'in l];expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 r.check('literal NPC live-opponent gate, true shared RNG/call wrap, exact destinations/velocities/idle/reverse playback; per-entity type and preserved siblings/context',actual==expected)
 ai=[list(map(int,l.split('RUNOFFAI|',1)[1].split('|')))for l in log.splitlines()if 'RUNOFFAI|'in l]
 if a.ai_dispatch:r.check('actual AI callback17 completes real live-opponent runoff and retires pending owner',ai==[[i,2,5,0]for i in range(len(rows))])
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_ATTACK_RUNOFF_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:10],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),derived_capability=cap,guards=a.guards,actual_ai_dispatch=a.ai_dispatch,ai_terminal=ai,source_animation_pointer_alias_fixture=True,actual_framezero_proven=a.complete_framezero,running_branch_proven=any(c.get('running',0)for c in rows),motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True),indent=2)+'\n');r.finish()
if __name__=='__main__':main()
