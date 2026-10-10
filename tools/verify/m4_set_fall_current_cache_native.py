"""Native set_fall selection against actual source mutable cache transitions."""
import argparse,json,re,struct,sys
from pathlib import Path
from unittest.mock import patch
import m4_model_current_pipeline_native as current
import m4_model_services_pipeline_native as parent
from actor_s5_entity_fixture import symbols
from compiler import Source
from source_foreign_state_layout import layout
from source_set_fall_select_native import derive,emit,emit_begin,emit_frame_prefix,emit_frame_owner

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--begin-animation',action='store_true');p.add_argument('--frame-zero-owner',action='store_true');p.add_argument('--fall-flags',action='store_true');p.add_argument('--finish-uninitialized-onfall',action='store_true');a=p.parse_args();a.fall_flags=a.fall_flags or a.finish_uninitialized_onfall;a.frame_zero_owner=a.frame_zero_owner or a.fall_flags;a.begin_animation=a.begin_animation or a.frame_zero_owner;a.output=a.output.resolve();req=derive(Source(a.source));sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls');original=parent.run_fixture
 onfall_requirements=None
 if a.finish_uninitialized_onfall:
  from source_uninitialized_onfall import derive as derive_onfall
  onfall_requirements=derive_onfall(Source(a.source))
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  nominal=[c for c in rows if not c['fault']];rows[:]=[dict(c,fall_type=t)for c in nominal for t in (-3,-1,0,1,19,20,65536)]
  from source_animation_init_4086 import derive as animations
  directory=animations(Source(a.source))['animations']
  for row_index,c in enumerate(rows):
   c['frozen']=(-3,0,1)[row_index%3]
   t=c['fall_type'];t=t if 0<=t<len(req['falls'])else 0;requested=req['falls'][t];selected=65535;handle=count=0;effective=0
   for kind in (t,0):
    candidate=req['falls'][kind];h=struct.unpack_from('<H',bytes(c['wanted_animation']),candidate*2)[0]
    if h and directory[h-1]['numframes']:selected=candidate;handle=h;count=directory[h-1]['numframes'];effective=kind;break
   c.update(fall_requested=requested,fall_selected=selected,fall_handle=handle,fall_count=count,fall_effective=effective)
  if a.frame_zero_owner:
   from source_frame_effects_4086 import derive as frame_effects
   effects=frame_effects(Source(a.source))['animations']
   for c in rows:
    f=effects[c['fall_handle']-1]['frames'][0];assert f['sound']is None;c['fall_nextanim']=48+f['delay_ticks']
  needle=' ply\n plx\n plp\n clc\n rtl\nModelPipeline_EntryBad:';assert kw['append'].count(needle)==1
  call=f''' lda #$B6B6
 sta.l {work}
 lda #0
 sta.l {work}+2
 sta.l {work}+22
 lda #1
 sta.l {work}+10
'''
  for i in range(2):call+=f''' ldx #1
 ldy #0
 jsl SetFallSelect_Run
 bcc SetFallWrapperContinue{i}
 jmp ModelPipeline_EntryBad
SetFallWrapperContinue{i}:
.a16
.i16
'''
  # Stale-generation rejection followed by an ordinary fresh retry.
  call+=f''' ldx #2
 ldy #0
 jsl SetFallSelect_Run
 bcs SetFallWrapperStaleRejected
 jmp ModelPipeline_EntryBad
SetFallWrapperStaleRejected:
.a16
.i16
 lda #0
 sta.l {work}+2
 ldx #1
 ldy #0
 jsl SetFallSelect_Run
 bcc SetFallWrapperFinal
 jmp ModelPipeline_EntryBad
SetFallWrapperFinal:
.a16
.i16
'''
  kw['append']=kw['append'].replace(needle,call+needle)+emit(work,req,sy)
  if a.begin_animation:
   assert all(c['fall_handle']for c in rows)
   begin=f""" lda.l {sy['SourceAnimationInit4086_Side']}
 tax
 lda #0
 sta.l $410024,x
 sta.l $410028,x
 sta.l $41002C,x
 lda #1
 sta.l $410026,x
 lda #2
 sta.l $41002A,x
 lda #3
 sta.l $41002E,x
"""
   for i in range(2):begin+=f""" ldx #1
 ldy #0
 jsl SetFallBegin_Run
 bcc SetFallBeginContinue{i}
 jmp ModelPipeline_EntryBad
SetFallBeginContinue{i}:
.a16
.i16
 cmp #1
 beq SetFallBeginPending{i}
 jmp ModelPipeline_EntryBad
SetFallBeginPending{i}:
.a16
.i16
"""
   kw['append']=kw['append'].replace(needle,begin+needle)+emit_begin(work,sy)
   if a.frame_zero_owner:
    child=f""" ldx #1
 ldy #0
 jsl SetFallFrameOwner_Run
 bcc FallFrameOwnerGood
 jmp ModelPipeline_EntryBad
FallFrameOwnerGood:
.a16
.i16
 cmp #0
 beq FallFrameOwnerComplete
 jmp ModelPipeline_EntryBad
FallFrameOwnerComplete:
.a16
.i16
 jsl {sy['SourceAnimationInit4086_Ack']}
 bcc FallFrameAckGood
 jmp ModelPipeline_EntryBad
FallFrameAckGood:
.a16
.i16
 ldx #1
 ldy #0
 jsl SetFallBegin_Run
 bcc FallFrameBeginResumed
 jmp ModelPipeline_EntryBad
FallFrameBeginResumed:
.a16
.i16
 cmp #2
 beq FallFrameFlagsRequired
 jmp ModelPipeline_EntryBad
FallFrameFlagsRequired:
.a16
.i16
"""

    if a.fall_flags:
     from source_set_fall_flags_native import emit as flags
     from source_current_colourmap import layout as palette_layout
     kw['append']+=flags(work,palette_layout(),sy)
     for i in range(2):child+=f""" ldx #1
 ldy #0
 jsl SetFallFlags_Run
 bcc FallFlagsGood{i}
 jmp ModelPipeline_EntryBad
FallFlagsGood{i}:
.a16
.i16
"""
     child+='FallFlagsComplete:\n.a16\n.i16\n nop\n'
     if a.finish_uninitialized_onfall:
      from source_uninitialized_onfall import emit as finish_fall
      kw['append']+=finish_fall(work,onfall_requirements,sy)
      for i in range(2):child+=f""" ldx #1
 ldy #0
 jsl SetFallFinish_Run
 bcc FallFinishGood{i}
 jmp ModelPipeline_EntryBad
FallFinishGood{i}:
.a16
.i16
 cmp #1
 beq FallFinishReturn{i}
 jmp ModelPipeline_EntryBad
FallFinishReturn{i}:
.a16
.i16
"""
      child+='FallFinishComplete:\n.a16\n.i16\n nop\n'

    kw['append']=kw['append'].replace(needle,child+needle)+emit_frame_prefix(work,sy)+emit_frame_owner(sy)
    kw.setdefault('bindings',{})['FALLSTARTFRAME']='SourceAnimationInit4086_StartFrame'
    lua+='\nemu.addMemoryCallback(function()emu.log("FALLFRAMEISSUE|"..word(INDEX))end,emu.callbackType.exec,FALLSTARTFRAME,FALLSTARTFRAME,emu.cpuType.snes,mt)\n'

   kw.setdefault('bindings',{})['FALLANIMBEGIN']='SourceAnimationInit4086_Begin'
   kw.setdefault('probes',{})['FALLBEGINENTRY']='SetFallBegin_Run'
   lua=lua.replace('local ranges={','local ranges={{0x41f500,2560},{0x43e000,512},')
   lua+='\nlocal fallBeginActive=false\nemu.addMemoryCallback(function()fallBeginActive=true end,emu.callbackType.exec,FALLBEGINENTRY,FALLBEGINENTRY,emu.cpuType.snes,mt)\nemu.addMemoryCallback(function()fallBeginActive=false end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\nemu.addMemoryCallback(function()if fallBeginActive then emu.log("FALLINITIALIZER|"..word(INDEX))end end,emu.callbackType.exec,FALLANIMBEGIN,FALLANIMBEGIN,emu.cpuType.snes,mt)\n'

  anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1;lua=lua.replace(anchor,f' put({work}+4,c.slot);put({work}+6,c.fall_type,4)\n'+anchor)
  lua=lua.replace('local ranges={',f'local ranges={{{{{work},24}},')
  anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
  expected=f''' for j=0,23 do before[{work}+j]=emu.read({work}+j,mt)end
 if word({work}+2)~=2 or word({work}+12)~=c.fall_requested or word({work}+14)~=c.fall_selected or word({work}+16)~=c.fall_handle or word({work}+18)~=c.fall_count or word({work}+20)~=c.fall_effective then before[{work}+2]=255 end
'''
  lua=lua.replace(anchor,expected+anchor);kw.setdefault('probes',{})['FALLSELECT']='SetFallSelect_Run'
  if a.begin_animation:
   lua=lua.replace(f'word({work}+2)~=2',f'word({work}+2)~=3 or word(sy.SourceAnimationInit4086_State)~=1 or word(sy.SourceAnimationInit4086_Issued)~=0')
   lua=lua.replace('value(side+4,c.wanted_handle,2);','value(side+4,c.fall_handle,2);').replace('value(side+4,c.wanted_idle_handle,2);','value(side+4,c.fall_handle,2);')
   lua=lua.replace('value(view+36,c.wanted_hp,4);','value(view+20,c.fall_selected,4);value(view+36,c.wanted_hp,4);')
   extra=""" local side=0x416800+c.slot*64;local core=0x40c000+c.slot*96;value(core+84,11,4)
 for off=36,44,4 do value(side+off,(1+(off-36)//4)*65536,4)end
 value(0x41f508+c.slot*20,0,4);value(0x41f510+c.slot*20,1,2);value(0x43e000+(c.fall_handle-1)*4,0,4)
"""
   lua=lua.replace(' local n=0;for a,v in pairs(before)',extra+' local n=0;for a,v in pairs(before)')

  lua+='\nemu.addMemoryCallback(function()emu.log("FALLCACHE|"..word(INDEX))end,emu.callbackType.exec,FALLSELECT,FALLSELECT,emu.cpuType.snes,mt)\n'
  if a.frame_zero_owner:
   lua=lua.replace(f'word({work}+2)~=3',f'word({work}+2)~=5').replace('word(sy.SourceAnimationInit4086_State)~=1','word(sy.SourceAnimationInit4086_State)~=2').replace('word(sy.SourceAnimationInit4086_Issued)~=0','word(sy.SourceAnimationInit4086_Issued)~=1')
   lua=lua.replace('value(side+8,c.wanted_idle_nextanim,4);','value(side+8,c.fall_nextanim,4);')
   lua=lua.replace('word(sy.SourceUpdateFrame4086_Handle)~=c.source_event.frame_handle','word(sy.SourceUpdateFrame4086_Handle)~=c.fall_handle').replace('word(sy.SourceUpdateFrame4086_Request)~=c.source_event.frame','word(sy.SourceUpdateFrame4086_Request)~=0')
   lua=lua.replace('value(view+20,0,4);','value(view+20,c.fall_selected,4);')
   # Parent frame-zero completion expectations remain active. Native Ack,
   # rather than observer mutation, completes the fall frame and initializer.
  if a.fall_flags:
   from m4_animation_init_native import luav
   lua='local flagSymbols='+luav({k:v for k,v in sy.items()if k.startswith(('SourceFreeze4086_','SourcePhysicsState4086_'))})+'\nfor k,v in pairs(flagSymbols)do sy[k]=v end\n'+lua
   lua=lua.replace('local ranges={','local ranges={{0x42e000,5120},{0x42d800,2048},{0x437e00,2560},')
   anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
   init=""" put(0x42e000+c.slot*40,c.frozen,4);put(0x42e004+c.slot*40,0x12345678,4)
 put(sy.SourceFreeze4086_Ready,0xb5df);put(sy.SourcePhysicsState4086_Ready,0xb61c);put(0x437e10+c.slot*20,0xb5fb)
"""
   lua=lua.replace(anchor,init+anchor).replace(f'word({work}+2)~=5',f'word({work}+2)~=6')
   expected=""" local fl=0x43eb00+c.slot*32
 for _,off in ipairs({0,4,8,12,16,20})do value(fl+off,0,4)end
 value(0x42d800+c.slot*16,1,4);value(0x437e00+c.slot*20,1,4);value(0x40c058+c.slot*96,0,4);value(0x439010+c.slot*80,1,4)
 value(0x42e000+c.slot*40,0,4);value(0x42e004+c.slot*40,c.frozen==0 and 0x12345678 or 0,4)
"""
   lua=lua.replace(' local n=0;for a,v in pairs(before)',expected+' local n=0;for a,v in pairs(before)')
   kw['probes'].update(FALLFLAGSFINAL='FallFlagsComplete',FALLFLAGSCURRENT='CurrentPalette_Run')
   lua+='\nlocal restoreCalls=0\nemu.addMemoryCallback(function()restoreCalls=restoreCalls+1 end,emu.callbackType.exec,FALLFLAGSCURRENT,FALLFLAGSCURRENT,emu.cpuType.snes,mt)\nemu.addMemoryCallback(function()local c=rows[word(INDEX)+1];emu.log("FALLFLAGSDONE|"..word(INDEX).."|"..word(0x42e004+c.slot*40).."|"..restoreCalls);restoreCalls=0 end,emu.callbackType.exec,FALLFLAGSFINAL,FALLFLAGSFINAL,emu.cpuType.snes,mt)\n'
  if a.finish_uninitialized_onfall:
   lua=lua.replace(f'word({work}+2)~=6',f'word({work}+2)~=7')
   kw['probes']['FALLFINISH']='FallFinishComplete'
   lua+='\nemu.addMemoryCallback(function()emu.log("FALLFINISHED|"..word(INDEX).."|"..word('+str(work+2)+').."|"..emu.getState()["cpu.a"])end,emu.callbackType.exec,FALLFINISH,FALLFINISH,emu.cpuType.snes,mt)\n'
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw);calls=[int(l.split('FALLCACHE|')[1])for l in log.splitlines()if'FALLCACHE|'in l];reporter.check('fall selection retry and stale-generation rejection after real model/cache transitions',calls==[i for i in range(len(rows))for _ in range(5 if a.begin_animation else 4)])
  if a.begin_animation:
   calls=[int(l.split('FALLINITIALIZER|')[1])for l in log.splitlines()if'FALLINITIALIZER|'in l];reporter.check('fall initializer executes once under retry and preserves incoming Q16 velocities',calls==list(range(len(rows))))
  if a.frame_zero_owner:
   issued=[int(l.split('FALLFRAMEISSUE|')[1])for l in log.splitlines()if'FALLFRAMEISSUE|'in l];reporter.check('real fall frame-zero issues once and completes through native frame owner and initializer Ack',issued==list(range(len(rows))))
  if a.fall_flags:
   observed=[l.split('FALLFLAGSDONE|')[1]for l in log.splitlines()if'FALLFLAGSDONE|'in l];reporter.check('fall flags preserve nonfrozen deadline and restore palette only for frozen truth without retry replay',observed==[f'{i}|'+str(0x5678 if c['frozen']==0 else 0)+'|'+str(2+int(c['frozen']!=0))for i,c in enumerate(rows)])
  if a.finish_uninitialized_onfall:
   finished=[l.split('FALLFINISHED|')[1]for l in log.splitlines()if'FALLFINISHED|'in l];reporter.check('source uninitialized onfall completes set_fall and returns one under retry without child replay',finished==[str(i)+'|7|1'for i in range(len(rows))])
  return raw,log
 argv=['m4_model_current_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 if a.frame_zero_owner:argv+=['--nested-idle']
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',argv):
  try:current.main()
  except SystemExit as e:
   if e.code not in (None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_SET_FALL_CURRENT_CACHE_NATIVE_V1',fall_requirements=req,actual_mutable_model_cache_queried=True,source_animation_resolve_bound=True,new_foreign_arena_bytes=0,source_animation_begin_bound=a.begin_animation,source_fall_flags_bound=a.fall_flags,source_fall_frame_zero_bound=a.frame_zero_owner,full_set_fall_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True);path.write_text(json.dumps(r,indent=2)+'\n')
 if a.finish_uninitialized_onfall:
  r.update(schema='BYOR_SET_FALL_UNINITIALIZED_ONFALL_NATIVE_V1',source_set_fall_bound=True,source_onfall_uninitialized_branch_bound=True,onfall_requirements=onfall_requirements,source_onfall_initialized_branch_bound=False,full_set_fall_for_closed_source_capability=True,source_set_fall_return=1,production_memory_lease=False,proof_domain='available typed/fallback fall animation under actual mutable cache; full native frame zero, flags, conditional unfreeze, uninitialized onfall; missing-fall branch not exercised')
  path.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
