"""Native suicide deadline/completion joined to actual no-event kill cleanup."""
import copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_retirement_native as parent
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_suicide_native import emit
from source_engine_function_ids import function_id
from source_foreign_water_retirement import emit as water,transform as retire_water
from m4_animation_init_native import luav
from m4_input_controller_native import offset
from _harness import Reporter

def main():
 args=sys.argv[1:];check_ai='--check-ai'in args;args=[v for v in args if v!='--check-ai'];source_path=None
 if '--source'in args:
  at=args.index('--source');source_path=args[at+1];del args[at:at+2]
 if check_ai and not source_path:raise ValueError('SUICIDE_AI_SOURCE_REQUIRED')
 if check_ai:
  from compiler import Source
  from source_model_switch_requirements import derive as models,pack_animation_cache
  from source_script_clone import derive as clones,pack as pack_clones
  from script_callback_owner import derive as callbacks,pack as pack_callbacks
  source=Source(source_path);model_report=models(source);cache=pack_animation_cache(model_report)
  clone_report=clones(source);clone_table=pack_clones(clone_report);callback_report,*_=callbacks(source);callback_table=pack_callbacks(callback_report)
 sy=symbols(Path('src/main.sym'));w=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls');original=parent.run_fixture;seen={}
 class SuicideReporter(Reporter):
  def __init__(self,*args,**kw):super().__init__('M4-SUICIDE-KILL',**kw)
  def check(self,name,ok):
   if name.startswith('pinned C retirement state'):
    actual=[list(map(int,l.split('RETIRERESULT|')[1].split('|')))for l in seen['log'].splitlines()if'RETIRERESULT|'in l]
    expected=[[i,0,0,3 if c['fault']else 0 if c['early']else 2]for i,c in enumerate(seen['rows'])];ok=actual==expected;name='source suicide deadline and boss OR with literal kill relation/role/variable cleanup and full actor/CPU preservation'
   if check_ai and name=='admitted retirement faults block source clock':
    actual=[list(map(int,l.split('RETIRECLOCK|')[1].split('|')))for l in seen['log'].splitlines()if 'RETIRECLOCK|'in l]
    ok=actual==[[i,1,48,1]for i in range(len(seen['rows']))];name='source clock remains blocked while isolated AI world lease is outstanding'
   return super().check(name,ok)
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  base=[c for c in rows if not c['fault']and c['case']['mode']==0 and c['case']['summon']==0]
  faults=[c for c in rows if c['bad']]
  rows[:]=[]
  for c in base:
   for boss,stall in ((0,48),(2,48),(0,49)):
    r=copy.deepcopy(c);r.update(boss=boss,stall=stall,early=stall>48)
    if r['early']:r['after']=copy.deepcopy(r['before'])
    else:
     for packet in r['after']:
      if packet['at']==0x43fd80:packet['data'][28]|=boss
    for packet in r['after']:
     if packet['at']==0x7ffe38:packet['data']=list((0x414000+80*c['slot']).to_bytes(4,'little'))
    rows.append(r)
  if not check_ai:rows.extend(dict(copy.deepcopy(c),boss=2,stall=48,early=False)for c in faults)
  if check_ai:
   for index,c in enumerate(rows):
    c['source_model']=index%len(clone_report['models'])
    for group in ('before','after'):
     for packet in c[group]:
      if packet['at']==0x409000+64*c['slot']:
       packet['data'][44:48]=list(clone_report['models'][c['source_model']]['initialized_mask'].to_bytes(4,'little'))if c['early']or group=='before'else[0]*4
  seen['rows']=rows
  extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','SourceLifecycle4086_','SourceFreeze4086_','SourceCtorState4086_','SourceScrollerPrefix4086_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'}
  lua='local suicideSymbols='+luav(extra)+'\nfor k,v in pairs(suicideSymbols)do sy[k]=v end\n'+lua
  lua=lua.replace('local ranges={','local ranges={{0x439000,10240},{0x433800,8192},{0x42e000,5120},{'+str(sy['SourceScrollerPrefix4086_Completed'])+',4},')
  needle=' before={};for _,r in ipairs(ranges)';assert lua.count(needle)==1
  initialization=f''' set('SourceForeignWork_Ready',0xb671);set('SourceForeignWork_Generation',1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({{'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'}})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceFreeze4086_Ready',0xb5df);set('SourceCtorState4086_Ready',0xb5c2);set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_Completed',c.case.completed,4);set('VmSourceWorld_Time',48,4)
 set('SourceSelf4086_GlobalLow',0x414000+80*c.slot,4)
 put(0x43900c+c.slot*80,{function_id('suicide')},4);put(0x43904a+c.slot*80,0xb4fb);put(0x439048+c.slot*80,0);put(0x416800+c.slot*64,0);put(0x43383e+c.slot*64,0xb5c2);put(0x433838+c.slot*64,c.boss,4);put(0x42e024+c.slot*40,0xb5df);put(0x42e008+c.slot*40,c.stall,4)
 for i=0,23 do put({w}+i,0,1)end;put({w},0xb6c5);put({w}+4,c.slot);put({w}+8,1,4);put({w}+16,48,4)
'''
  # Keep the parent's deliberately invalid caller pointer rejection.
  initialization+=" if c.bad=='self'then set('SourceSelf4086_Ready',0)end\n"
  initialization+=f" if c.bad=='slot'then put({w}+4,c.count)end\n"
  if check_ai:
   cache_init=','.join(map(str,cache))
   ai_symbols={k:v for k,v in sy.items()if k.startswith(('SourceAI4086_','SourceAIRun4086_','SourceWorldTick4086_','SourceModelAnimationCopy4086_','SourceScriptClone4086_','SourceAnimationCallback4086_','SourceUpdateFrame4086_'))}
   lua='local aiSymbols='+luav(ai_symbols)+'\nfor k,v in pairs(aiSymbols)do sy[k]=v end\nlocal suicideCalls=0;local scriptCalls=0;local cloneCalls=0\n'+lua
   initialization+=f''' suicideCalls=0;scriptCalls=0;cloneCalls=0
 set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',0);set('SourceAI4086_Endgame',0,4);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);set('SourceAIRun4086_PendingKind',0)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_TimeLo',48,4)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Maximum',{model_report['maximum_animations']});set('SourceModelAnimationCopy4086_Models',{len(model_report['models'])});set('SourceModelAnimationCopy4086_Bytes',{len(cache)})
 local animationCache={{{cache_init}}};for i,n in ipairs(animationCache)do put(0x43c000+i-1,n,1)end
 set('VmSourceWorld_TemplateCount',{len(clone_report['models'])});set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Base',0x8000);set('SourceScriptClone4086_Bank',59);set('SourceScriptClone4086_Bytes',{len(clone_table)});set('SourceScriptClone4086_Models',{len(clone_report['models'])})
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_Base',0x8000);set('SourceAnimationCallback4086_Bank',60);set('SourceAnimationCallback4086_Bytes',{len(callback_table)});set('SourceAnimationCallback4086_Models',{len(callback_report['models'])});set('SourceAnimationCallback4086_Programs',{callback_report['program_count']})
 set('SourceUpdateFrame4086_Ready',0);put(0x416800+c.slot*64,c.source_model);put(0x439048+c.slot*80,c.source_model);put(0x439000+c.slot*80,0,4);put(0x416814+c.slot*64,0,4);put(0x41f510+c.slot*20,1);put({w},0xb680)
'''

  lua=lua.replace(needle,initialization+needle)
  needle=' local mismatch=0;for a,n in pairs(before)';assert lua.count(needle)==1
  expected=f''' if c.fault==0 and not c.early then local at=sy.SourceScrollerPrefix4086_Completed;local v=c.case.completed|c.boss;for i=0,3 do before[at+i]=(v>>(8*i))&255 end end
'''
  lua=lua.replace(needle,expected+needle)
  wrapper='''SuicideProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl Suicide_Run
 bcs SuicideProbe_Bad
 jsl Suicide_Run
 bcs SuicideProbe_Bad
 ply
 plx
 plp
 clc
 rtl
SuicideProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
  wrapper+=f'''SuicideFixtureReturn:
.a16
.i16
 php
 rep #$20
 pha
 lda #0
 sta.l {sy['VmSourceWorld_Ready']}
 sta.l {sy['SourceScrollerPrefix4086_Ready']}
 pla
 plp
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml {sy['Vm_SourceFrameGate']+5}
'''
  if check_ai:
   from source_common_ai_run_native import emit as ai_bridge,ACTIONS
   wrapper=wrapper.replace(' jsl Suicide_Run',' jsl CommonAIRun_Begin',1)
   wrapper=wrapper.replace(' jsl Suicide_Run\n bcs SuicideProbe_Bad\n','',1)
   wrapper+=ai_bridge(w,sy,actions=(next(a for a in ACTIONS if a[0]=='suicide'),))
   wrapper=wrapper.replace(f" sta.l {sy['SourceScrollerPrefix4086_Ready']}\n",f" sta.l {sy['SourceScrollerPrefix4086_Ready']}\n sta.l {sy['SourceWorldTick4086_Ready']}\n")
   tables=list(tables)+[(59,0,clone_table),(60,0,callback_table)]
   lua+=f'''\nemu.addMemoryCallback(function()suicideCalls=suicideCalls+1 end,emu.callbackType.exec,SUICIDEENTRY,SUICIDEENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()scriptCalls=scriptCalls+1 end,emu.callbackType.exec,{sy['SourceAI4086_ThinkScriptAbsent']},{sy['SourceAI4086_ThinkScriptAbsent']},emu.cpuType.snes,mt)
emu.addMemoryCallback(function()cloneCalls=cloneCalls+1 end,emu.callbackType.exec,{sy['SourceScriptClone4086_CheckModelProgram']},{sy['SourceScriptClone4086_CheckModelProgram']},emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('SUICIDEAI|'..word(INDEX)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAIRun4086_State)..'|'..suicideCalls..'|'..scriptCalls..'|'..cloneCalls)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
   clone_labels={k:v for k,v in sy.items()if k.startswith('SourceScriptClone4086_')and ('Far_'in k or 'ProgramCheck_'in k)}
   lua+='\nlocal lastCloneLabel="none"\n'
   for name,address in clone_labels.items():
    lua+=f'emu.addMemoryCallback(function()lastCloneLabel="{name}"end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n'
   lua+=f'''emu.addMemoryCallback(function()local s=emu.getState();emu.log('CLONEBAD|'..lastCloneLabel..'|'..s['cpu.a']..'|'..word(sy.SourceScriptClone4086_Model)..'|'..word(sy.SourceScriptClone4086_Models)..'|'..word(sy.SourceScriptClone4086_Bytes))end,emu.callbackType.exec,{sy['SourceScriptClone4086_Bad']},{sy['SourceScriptClone4086_Bad']},emu.cpuType.snes,mt)\n'''
   kw.setdefault('probes',{})['SUICIDEENTRY']='Suicide_Run'
  def isolate(raw,linked):
   retire_water(raw,linked);at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['SuicideFixtureReturn'].to_bytes(3,'little')
  kw.update(append=wrapper+emit(w,sy)+water(sy),rom_transform=isolate,link_pcm=False,batch_size=4);kw['bindings'].pop('CAPTUREENTRY');kw.setdefault('probes',{})['CAPTUREENTRY']='SuicideProbe'
  raw,log=original(rom,folder,rows,'SuicideProbe',ready,magic,tables,lua,reporter,**kw);seen['log']=log
  if check_ai:
   actual=[list(map(int,l.split('SUICIDEAI|')[1].split('|')))for l in log.splitlines()if 'SUICIDEAI|'in l]
   reporter.check('real AI action dispatch and post-retirement cloned-model think-script absence',actual==[[i,5,2,1,1,1]for i in range(len(rows))]);seen['ai_results']=actual
  reporter.check('bank0 remains byte-identical',raw[:32768]==rom.read_bytes()[:32768]);return raw,log
 with patch.object(parent,'run_fixture',fixture),patch.object(parent,'Reporter',SuicideReporter),patch.object(sys,'argv',['m4_retirement_native.py',*args]):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 p=Path(args[args.index('--output')+1])/'report.json';r=json.loads(p.read_text());r.update(schema='BYOR_SUICIDE_KILL_NATIVE_V1',actual_source_suicide_bound=True,actual_no_event_retirement_bound=True,actual_check_ai_dispatch_bound=check_ai,actual_post_retirement_script_check_bound=check_ai,ai_results=seen.get('ai_results'),source_null_think_snapshot_supplied=check_ai,source_clock_held_during_isolated_world_lease=check_ai,full_kill_callbacks_bound=False,production_memory_lease=False,new_foreign_arena_bytes=0);
 if check_ai:r.update(source_model_identities=[m['identity']for m in clone_report['models']],source_script_table_sha256=hashlib.sha256(clone_table).hexdigest(),source_callback_table_sha256=hashlib.sha256(callback_table).hexdigest(),source_animation_cache_sha256=hashlib.sha256(cache).hexdigest(),production_check_ai_consumer_bound=False)
 p.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
