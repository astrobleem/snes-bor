"""Common_pain idle child after real source model/cache and frame services."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
from unittest.mock import patch
import m4_model_current_pipeline_native as current
import m4_model_services_pipeline_native as parent
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_common_pain_native import emit as prefix
from source_common_pain_frame_native import emit as child
from source_engine_function_ids import function_id
from source_animation_ids import configure
from source_animation_init_4086 import derive as animations
from source_frame_effects_4086 import derive as effects
from m4_animation_init_native import luav
from m4_input_controller_native import offset

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--block-absent',action='store_true')
 p.add_argument('--grabbed',action='store_true')
 p.add_argument('--block-action-authority',type=Path)
 a=p.parse_args();a.output=a.output.resolve();source=Source(a.source);sy=symbols(Path('src/main.sym'));ids=configure([]);pain=ids['arrays']['pains'][0];work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls');directory=animations(source)['animations'];frames=effects(source)['animations'];original=parent.run_fixture
 if a.grabbed and a.block_absent:raise ValueError('COMMON_ACTION_FIXTURE_MODE')
 block_requirements=None
 if a.block_action_authority:
  if a.grabbed or a.block_absent:raise ValueError('COMMON_ACTION_FIXTURE_MODE')
  authority=json.loads(a.block_action_authority.read_text());assert authority['status']=='PASS';block_requirements=authority['requirements'];assert block_requirements['closed_zero_policy']
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  kw['frame_limit']=200
  rows[:]=[dict(c)for c in rows if not c['fault']]
  for c in rows:
   c['stopped_pain_handle']=struct.unpack_from('<H',bytes(c['wanted_animation']),pain*2)[0];assert c['stopped_pain_handle']
   c['new_idle_handle']=struct.unpack_from('<H',bytes(c['wanted_animation']),0)[0];f=frames[c['new_idle_handle']-1]['frames'][0];assert f['sound']is None;c['new_idle_nextanim']=48+f['delay_ticks']
   if a.block_absent:assert struct.unpack_from('<H',bytes(c['wanted_animation']),ids['authority']['enum']['ANI_BLOCK']*2)[0]==0
  needle=' ply\n plx\n plp\n clc\n rtl\nModelPipeline_EntryBad:';assert kw['append'].count(needle)==1
  # The parent has completed its real frame child; acknowledge that actual
  # initializer before supplying this independently stopped-pain snapshot.
  code=f''' lda.l {sy['SourceAnimationInit4086_State']}
 cmp #1
 bne CommonPainPriorAnimationDone
 jsl {sy['SourceAnimationInit4086_Ack']}
 bcc CommonPainPriorAnimationDone
 jmp ModelPipeline_EntryBad
CommonPainPriorAnimationDone:
.a16
.i16
 lda.l {work}+4
 asl a
 asl a
 asl a
 asl a
 sta.l {work}+6
 asl a
 asl a
 clc
 adc.l {work}+6
 tax
 lda #{pain}
 sta.l $414014,x
 lda #0
 sta.l $414016,x
 sta.l $41400C,x
 sta.l $41400E,x
 lda #2
 sta.l $414008,x
 lda #0
 sta.l $41400A,x
 lda #{function_id('common_pain')}
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
 lda.l {work}+4
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda #1
 sta.l $43EB04,x
 lda #0
 sta.l $43EB06,x
 sta.l $43EB14,x
 sta.l $43EB16,x
 lda.l {work}+4
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l {work}+20
 sta.l $416804,x
 lda #0
 sta.l $416830,x
 sta.l $416832,x
 sta.l $416824,x
 sta.l $416828,x
 sta.l $41682C,x
 lda #1
 sta.l $416826,x
 lda #2
 sta.l $41682A,x
 lda #3
 sta.l $41682E,x
 lda.l {work}+4
 asl a
 asl a
 sta.l {work}+6
 asl a
 asl a
 clc
 adc.l {work}+6
 tax
 lda #0
 sta.l $41F510,x
 lda #$B6B8
 sta.l {work}
 lda #0
 sta.l {work}+2
 sta.l {work}+6
 sta.l {work}+10
 sta.l {work}+12
 sta.l {work}+14
 sta.l {work}+20
 sta.l {work}+22
 lda #1
 sta.l {work}+8
 lda.l {sy['VmSourceWorld_Time']}
 sta.l {work}+16
 lda.l {sy['VmSourceWorld_Time']}+2
 sta.l {work}+18
'''
  for i in range(2):code+=f''' ldx #1
 ldy #0
 jsl CommonPainFrame_Run
 bcc CommonPainFrameProofGood{i}
 jmp ModelPipeline_EntryBad
CommonPainFrameProofGood{i}:
.a16
.i16
 cmp #0
 beq CommonPainFrameProofComplete{i}
 jmp ModelPipeline_EntryBad
CommonPainFrameProofComplete{i}:
.a16
.i16
'''
  code+='CommonPainFrameProofDone:\n.a16\n.i16\n nop\n'
  if a.block_absent:code=code.replace(' sta.l $43EB14,x\n sta.l $43EB16,x',' sta.l $43EB16,x\n lda #1\n sta.l $43EB14,x')
  if a.grabbed or block_requirements:
   from source_common_grabbed_native import emit as grabbed_prefix
   kind='common_grabbed'if a.grabbed else'common_block';name='CommonGrabbed'if a.grabbed else'CommonBlock';magic_tag='$B6B9'if a.grabbed else'$B6BA'
   code=code.replace(f'lda #{function_id("common_pain")}\n',f'lda #{function_id(kind)}\n').replace('lda #$B6B8','lda #'+magic_tag).replace('jsl CommonPainFrame_Run','jsl '+name+'Frame_Run')
   assembly=grabbed_prefix(work,sy,kind=kind,requirements=block_requirements)+child(work,sy,prefix=name)
  else:assembly=prefix(work,sy)+child(work,sy)
  kw['append']=kw['append'].replace(needle,code+needle)+assembly
  # Withdraw the fixture's fake world outside its foreground batch.
  kw['append']+=f'''CommonPainFrameIsolatedReturn:
.a16
.i16
 php
 rep #$20
 pha
 lda.l $7FFD80
 cmp #{magic}
 beq CommonPainFrameWithdrawWorld
 lda.l $7FFD82
 cmp #{len(rows)}
 bcc CommonPainFrameKeepWorld
CommonPainFrameWithdrawWorld:
.a16
.i16
 lda #0
 sta.l {sy['VmSourceWorld_Ready']}
CommonPainFrameKeepWorld:
.a16
.i16
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
  old_transform=kw.get('rom_transform')
  def isolate(raw,linked):
   if old_transform:old_transform(raw,linked)
   at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['CommonPainFrameIsolatedReturn'].to_bytes(3,'little')
  kw['rom_transform']=isolate
  lua='local actionSymbols='+luav({k:v for k,v in sy.items()if k.startswith(('SourceIdle4086_','SourceLifecycle4086_'))})+'\nfor k,v in pairs(actionSymbols)do sy[k]=v end\n'+lua
  lua=lua.replace('local ranges={',f'local ranges={{{{{work},24}},{{0x41f500,2560}},{{0x43e000,512}},')
  anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1;lua=lua.replace(anchor,f' put({work}+4,c.slot);put({work}+20,c.stopped_pain_handle);put(0x40901c+c.slot*64,0,4)\n'+anchor)
  if a.grabbed:
   lua=lua.replace('local ranges={','local ranges={{0x42e000,5120},')
   lua=lua.replace(anchor," set('SourceFreeze4086_Ready',0xb5df);put(0x42e024+c.slot*40,0xb5df);put(0x42e008+c.slot*40,123,4)\n"+anchor)
  # The final actor returns to its authored idle via actual set_idle. The
  # synthetic stopped-pain snapshot is only the input boundary to this proof.
  lua=lua.replace('word(sy.SourceUpdateFrame4086_Handle)~=c.source_event.frame_handle','word(sy.SourceUpdateFrame4086_Handle)~=c.new_idle_handle').replace('word(sy.SourceUpdateFrame4086_Request)~=c.source_event.frame','word(sy.SourceUpdateFrame4086_Request)~=0')
  anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
  extra=f''' for j=0,23 do before[{work}+j]=emu.read({work}+j,mt)end
 local side=0x416800+c.slot*64;local view=0x414000+c.slot*80
 value(view+8,2,4);value(view+12,0,4);value(side+48,0,4);value(side+36,c.new_cached_type~=0 and 0 or 65536,4);value(side+40,c.new_cached_type~=0 and 0 or 2*65536,4);value(side+44,3*65536,4);value(0x43900c+c.slot*80,0,4)
 value(0x41f508+c.slot*20,0,4);value(0x41f510+c.slot*20,1,2);value(0x43e000+(c.new_idle_handle-1)*4,0,4)
 value(0x43eb00+c.slot*32,3,4);value(0x43eb04+c.slot*32,0,4);value(0x43eb14+c.slot*32,0,4)
 if word({work}+2)~=2 or word({work}+6)~=1 or word({work}+20)~=c.new_idle_handle or word(sy.SourceAnimationInit4086_State)~=2 then before[{work}+2]=255 end
''';lua=lua.replace(anchor,extra+anchor)
  if a.block_absent:
   lua=lua.replace('value(view+8,2,4);',f'value(view+20,{pain},4);value(view+8,2,4);')
   lua=lua.replace('word(sy.SourceUpdateFrame4086_Handle)~=c.new_idle_handle','word(sy.SourceUpdateFrame4086_Handle)~=c.source_event.frame_handle').replace('word(sy.SourceUpdateFrame4086_Request)~=0','word(sy.SourceUpdateFrame4086_Request)~=c.source_event.frame')
   lua=lua.replace('value(side+4,c.wanted_idle_handle,2);',f'value(side+4,c.stopped_pain_handle,2);value(view+20,{pain},4);')
   lua=lua.replace('value(side+36,c.new_cached_type~=0 and 0 or 65536,4);value(side+40,c.new_cached_type~=0 and 0 or 2*65536,4);','value(side+36,65536,4);value(side+40,2*65536,4);')
   lua=lua.replace('value(0x43900c+c.slot*80,0,4)',f'value(0x43900c+c.slot*80,{function_id("common_block")},4)').replace('value(0x41f510+c.slot*20,1,2)','value(0x41f510+c.slot*20,0,2)').replace('value(0x43eb14+c.slot*32,0,4)','value(0x43eb14+c.slot*32,1,4)')
   lua=lua.replace(f'word({work}+6)~=1 or word({work}+20)~=c.new_idle_handle',f'word({work}+6)~=2 or word({work}+20)~=0 or word(sy.SourceAnimationInit4086_Count)~=0')
  kw.setdefault('probes',{})['ACTIONFINAL']='CommonPainFrameProofDone';kw.setdefault('bindings',{})['ACTIONSETIDLE']='SourceSetIdle4086_Begin';kw['bindings']['ACTIONSTARTFRAME']='SourceAnimationInit4086_StartFrame'
  kw['probes']['ACTIONBAD']='CommonPainFrame_Bad';kw['probes']['ACTIONPREFIXBAD']='CommonPain_Bad'
  if a.grabbed:
   kw['probes']['ACTIONBAD']='CommonGrabbedFrame_Bad';kw['probes']['ACTIONPREFIXBAD']='CommonGrabbed_Bad'
   lua=lua.replace('value(view+8,2,4);','value(0x42e008+c.slot*40,0,4);value(view+8,2,4);')
  if block_requirements:
   kw['probes']['ACTIONBAD']='CommonBlockFrame_Bad';kw['probes']['ACTIONPREFIXBAD']='CommonBlock_Bad'
  kw['probes']['ACTIONGATE']='LeafFixture_Gate'
  lua+='''
local actionStarted=false;local idleBegins=0;local frameBegins=0
local gateLogged=0
emu.addMemoryCallback(function()if word(0x7ffd80)==46320 and gateLogged<4 then gateLogged=gateLogged+1;emu.log('PAINFRAMEGATE|'..word(INDEX)..'|busy='..word(sy.SourceVMRun4086_Busy))end end,emu.callbackType.exec,ACTIONGATE,ACTIONGATE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()actionStarted=true end,emu.callbackType.exec,ACTIONENTRY,ACTIONENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();emu.log('PAINCHILDFAULT|'..word(INDEX)..'|a='..s['cpu.a']..'|x='..s['cpu.x']..'|y='..s['cpu.y'])end,emu.callbackType.exec,ACTIONBAD,ACTIONBAD,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();emu.log('PAINPREFIXFAULT|'..word(INDEX)..'|a='..s['cpu.a']..'|x='..s['cpu.x']..'|y='..s['cpu.y'])end,emu.callbackType.exec,ACTIONPREFIXBAD,ACTIONPREFIXBAD,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if actionStarted then idleBegins=idleBegins+1 end end,emu.callbackType.exec,ACTIONSETIDLE,ACTIONSETIDLE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if actionStarted then frameBegins=frameBegins+1 end end,emu.callbackType.exec,ACTIONSTARTFRAME,ACTIONSTARTFRAME,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log("COMMONPAINFRAME|"..word(INDEX).."|"..idleBegins.."|"..frameBegins.."|"..emu.getState()["cpu.a"]);actionStarted=false;idleBegins=0;frameBegins=0 end,emu.callbackType.exec,ACTIONFINAL,ACTIONFINAL,emu.cpuType.snes,mt)
''';kw['probes']['ACTIONENTRY']='CommonPainFrame_Run'
  if a.grabbed:kw['probes']['ACTIONENTRY']='CommonGrabbedFrame_Run'
  if block_requirements:kw['probes']['ACTIONENTRY']='CommonBlockFrame_Run'
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw);actual=[l.split('COMMONPAINFRAME|')[1]for l in log.splitlines()if'COMMONPAINFRAME|'in l];counts='0|0'if a.block_absent else'1|1';reporter.check('actual idle frame or absent block child completes common_pain request under retry',actual==[f'{i}|{counts}|0'for i in range(len(rows))]);return raw,log
 argv=['m4_model_current_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output),'--nested-idle']
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',argv):
  try:current.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_COMMON_PAIN_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=not a.block_absent,source_set_idle_bound=not a.block_absent,actual_animation_and_frame_owner_bound=not a.block_absent,stopped_pain_snapshot_installed_by_fixture=True,block_absence_branch_exercised=a.block_absent,block_frame_branch_exercised=False,full_common_pain_admitted=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,new_foreign_arena_bytes=0);path.write_text(json.dumps(r,indent=2)+'\n')
 if a.grabbed:
  r.update(schema='BYOR_COMMON_GRABBED_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=False,source_common_grabbed_idle_child_bound=True,source_unlinked_snapshot_installed_by_fixture=True,full_common_grabbed_admitted=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if block_requirements:
  r.update(schema='BYOR_COMMON_BLOCK_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=False,source_common_block_idle_child_bound=True,closed_zero_holdblock_model_policy=True,full_common_block_admitted=False);path.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
