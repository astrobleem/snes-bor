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
 p.add_argument('--doland',action='store_true')
 p.add_argument('--land-action',action='store_true')
 p.add_argument('--fall-land-requirements',type=Path)
 p.add_argument('--check-ai',action='store_true')
 p.add_argument('--rise-requirements',type=Path)
 p.add_argument('--lie-requirements',type=Path)
 a=p.parse_args();a.output=a.output.resolve();source=Source(a.source);sy=symbols(Path('src/main.sym'));ids=configure([]);pain=ids['arrays']['pains'][0];work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls');directory=animations(source)['animations'];frames=effects(source)['animations'];original=parent.run_fixture
 fall_requirements=None
 if a.fall_land_requirements:
  fall_requirements=json.loads(a.fall_land_requirements.read_text());a.doland=True
 speedup=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='global_fall_speedup')
 if a.grabbed and a.block_absent:raise ValueError('COMMON_ACTION_FIXTURE_MODE')
 if a.doland and(a.grabbed or a.block_absent or a.block_action_authority):raise ValueError('COMMON_ACTION_FIXTURE_MODE')
 if a.land_action and(a.grabbed or a.block_absent or a.block_action_authority or a.doland):raise ValueError('COMMON_ACTION_FIXTURE_MODE')
 block_requirements=None
 rise_requirements=None
 lie_requirements=None
 if a.lie_requirements:
  if a.rise_requirements or not a.check_ai:raise ValueError('COMMON_LIE_REQUIRES_CHECK_AI')
  a.rise_requirements=a.lie_requirements;lie_requirements=json.loads(a.lie_requirements.read_text())
 if a.rise_requirements:
  if a.grabbed or a.block_absent or a.block_action_authority or a.doland or a.land_action:raise ValueError('COMMON_ACTION_FIXTURE_MODE')
  from source_recovery_state_layout import layout as recovery_layout
  rise_requirements=json.loads(a.rise_requirements.read_text());recovery_plan=recovery_layout()
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
   if a.doland:
    c['land_handle']=struct.unpack_from('<H',bytes(c['wanted_animation']),ids['authority']['enum']['ANI_LAND']*2)[0];assert c['land_handle'];f=frames[c['land_handle']-1]['frames'][0];assert f['sound']is None;c['land_nextanim']=48+f['delay_ticks']
   if lie_requirements:
    from source_set_rise_select_native import derive as rise_selection
    rise_policy=rise_selection(source);c['rise_role']=rise_policy['rises'][1];c['rise_handle']=struct.unpack_from('<H',bytes(c['wanted_animation']),c['rise_role']*2)[0]
    if not c['rise_handle']:c['rise_role']=rise_policy['rises'][0];c['rise_handle']=struct.unpack_from('<H',bytes(c['wanted_animation']),c['rise_role']*2)[0]
    assert c['rise_handle'];f=frames[c['rise_handle']-1]['frames'][0];assert f['sound']is None;c['rise_nextanim']=48+f['delay_ticks']
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
  if a.doland:
   from source_doland_native import emit as doland_prefix
   code=code.replace(f'lda #{function_id("common_pain")}\n',f'lda #{function_id("common_fall")}\n').replace('lda #$B6B8','lda #$B6BC').replace('jsl CommonPainFrame_Run','jsl CommonDolandFrame_Run')
   boundary=f''' lda.l {work}+4
 asl a
 asl a
 asl a
 sta.l {work}+6
 asl a
 clc
 adc.l {work}+6
 tay
 lda.l {work}+4
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 sta.l {work}+6
 tyx
 lda.l {work}+6
 sta.l $7EF116,x
 lda #$B62F
 sta.l $7EF114,x
 lda #2
 sta.l $7EF100,x
 lda #0
 sta.l $7EF102,x
 sta.l {work}+6
'''
   code=code.replace(' ldx #1\n ldy #0\n jsl CommonDolandFrame_Run',boundary+' ldx #1\n ldy #0\n jsl CommonDolandFrame_Run',1)
   assembly=doland_prefix(work,sy)+child(work,sy,prefix='CommonDoland')
   if fall_requirements:
    from source_common_fall_native import emit as fall_prefix
    from source_common_fall_frame_native import emit as fall_frame
    code=code.replace('lda #$B6BC','lda #$B6BB').replace('jsl CommonDolandFrame_Run','jsl CommonFallFrame_Run').replace(' lda #3\n sta.l $41682E,x',' lda #0\n sta.l $41682E,x')
    assembly+=fall_prefix(work,speedup,fall_requirements,sy)+fall_frame(work)
  elif a.grabbed or block_requirements or a.land_action:
   from source_common_grabbed_native import emit as grabbed_prefix
   kind='common_land'if a.land_action else'common_grabbed'if a.grabbed else'common_block';name='CommonLand'if a.land_action else'CommonGrabbed'if a.grabbed else'CommonBlock';magic_tag='$B6BD'if a.land_action else'$B6B9'if a.grabbed else'$B6BA'
   code=code.replace(f'lda #{function_id("common_pain")}\n',f'lda #{function_id(kind)}\n').replace('lda #$B6B8','lda #'+magic_tag).replace('jsl CommonPainFrame_Run','jsl '+name+'Frame_Run')
   assembly=grabbed_prefix(work,sy,kind=kind,requirements=block_requirements)+child(work,sy,prefix=name)
  elif lie_requirements:
   from source_common_lie_native import emit as lie_prefix
   from source_common_lie_frame_native import emit as lie_frame
   from source_set_rise_select_native import emit as rise_select,emit_begin as rise_begin,emit_frame_prefix as rise_frame_prefix,emit_frame_owner as rise_frame_owner
   from source_set_rise_flags_native import emit as rise_flags
   from source_set_rise_frame_native import emit as rise_owner
   child_work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='pain_services_controls')
   code=code.replace(f'lda #{function_id("common_pain")}\n',f'lda #{function_id("common_lie")}\n').replace('lda #$B6B8','lda #$B6C4').replace('jsl CommonPainFrame_Run','jsl CommonLieFrame_Run').replace(' lda #3\n sta.l $41682E,x',' lda #0\n sta.l $41682E,x')
   assembly=lie_prefix(work,recovery_plan,lie_requirements,sy)+lie_frame(work,child_work,sy)+rise_select(child_work,rise_policy,sy)+rise_begin(child_work,sy)+rise_frame_prefix(child_work,sy)+rise_frame_owner(sy)+rise_flags(child_work,lie_requirements,sy)+rise_owner(child_work,sy)
  elif rise_requirements:
   from source_common_rise_native import emit as rise_prefix
   code=code.replace(f'lda #{function_id("common_pain")}\n',f'lda #{function_id("common_rise")}\n').replace('lda #$B6B8','lda #$B6C2').replace('jsl CommonPainFrame_Run','jsl CommonRiseFrame_Run')
   assembly=rise_prefix(work,recovery_plan,rise_requirements,sy)+child(work,sy,prefix='CommonRise')
  else:assembly=prefix(work,sy)+child(work,sy)
  if a.check_ai:
   if a.doland and not fall_requirements:raise ValueError('DOLAND_IS_NOT_A_SOURCE_ACTION')
   from source_common_ai_run_native import emit as ai_bridge,ACTIONS
   selected='common_lie'if lie_requirements else'common_rise'if rise_requirements else'common_fall'if fall_requirements else'common_grabbed'if a.grabbed else'common_block'if block_requirements else'common_land'if a.land_action else'common_pain'
   descriptor=next(r for r in ACTIONS if r[0]==selected)
   bridge_actions=(descriptor,)
   if fall_requirements:
    # doland changes takeaction to common_land. The next real check_ai call
    # must dispatch that successor rather than fault in the legacy owner.
    from source_common_grabbed_native import emit as successor_prefix
    assembly+=successor_prefix(work,sy,kind='common_land')+child(work,sy,prefix='CommonLand')
    bridge_actions+=(next(r for r in ACTIONS if r[0]=='common_land'),)
   if lie_requirements:
    from source_common_rise_native import emit as successor_rise
    assembly+=successor_rise(work,recovery_plan,lie_requirements,sy)+child(work,sy,prefix='CommonRise')
    bridge_actions+=(next(r for r in ACTIONS if r[0]=='common_rise'),)
   assembly+=ai_bridge(work,sy,actions=bridge_actions)
   call=descriptor[1];assert code.count('jsl '+call)==2;code=code.replace('jsl '+call,'jsl CommonAIRun_Begin')
   # Supply the scheduler's input boundary after real model/frame services.
   boundary=f""" lda #$B680
 sta.l {work}
 lda #0
 sta.l {work}+2
 sta.l {sy['SourceAI4086_State']}
 sta.l {sy['SourceAI4086_Endgame']}
 sta.l {sy['SourceAI4086_Endgame']}+2
 sta.l {sy['SourceAIRun4086_State']}
 sta.l {sy['SourceAIRun4086_PendingKind']}
 lda.l {work}+4
 sta.l {sy['SourceWorldTick4086_Slot']}
 lda #$B4D5
 sta.l {sy['SourceWorldTick4086_Ready']}
 lda #1
 sta.l {sy['SourceWorldTick4086_State']}
 sta.l {sy['SourceWorldTick4086_Pending']}
 lda #6
 sta.l {sy['SourceWorldTick4086_Phase']}
 lda.l {sy['VmSourceWorld_Time']}
 sta.l {sy['SourceWorldTick4086_TimeLo']}
 lda.l {sy['VmSourceWorld_Time']}+2
 sta.l {sy['SourceWorldTick4086_TimeHi']}
 lda #$B5E2
 sta.l {sy['SourceAI4086_Ready']}
 lda #$B5E6
 sta.l {sy['SourceAIRun4086_Ready']}
 lda #23
 sta.l {sy['SourceAI4086_SpawnID']}
 lda #104
 sta.l {sy['SourceAI4086_RespawnID']}
 lda.l {work}+4
 asl a
 asl a
 asl a
 asl a
 sta.l {work}+6
 asl a
 asl a
 tax
 lda #0
 sta.l $416814,x
 sta.l $416816,x
 txa
 clc
 adc.l {work}+6
 tax
 lda #0
 sta.l $439000,x
 sta.l $439002,x
 txa
 clc
 adc #$4000
 sta.l {sy['SourceSelf4086_GlobalLow']}
 lda #$41
 sta.l {sy['SourceSelf4086_GlobalLow']}+2
 lda #$B4F6
 sta.l {sy['SourceSelf4086_Ready']}
 lda #0
 sta.l {sy['SourceSelf4086_Active']}
 sta.l {sy['SourceSelf4086_Fault']}
"""
   code=code.replace(' ldx #1\n ldy #0\n jsl CommonAIRun_Begin',boundary+' ldx #1\n ldy #0\n jsl CommonAIRun_Begin',1)
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
  if a.check_ai:kw['append']=kw['append'].replace(f" sta.l {sy['VmSourceWorld_Ready']}\nCommonPainFrameKeepWorld:",f" sta.l {sy['VmSourceWorld_Ready']}\n sta.l {sy['SourceWorldTick4086_Ready']}\nCommonPainFrameKeepWorld:")
  if fall_requirements:kw['append']=kw['append'].replace(f" sta.l {sy['VmSourceWorld_Ready']}\nCommonPainFrameKeepWorld:",f" sta.l {sy['VmSourceWorld_Ready']}\n sta.l {sy['SourceScrollerPrefix4086_Ready']}\nCommonPainFrameKeepWorld:")
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
  if a.doland:
   lua=lua.replace('local ranges={','local ranges={{0x437e00,2560},{0x7ef100,3072},{0x42d800,2048},')
   lua=lua.replace(anchor," set('SourcePhysicsState4086_Ready',0xb61c);set('SourceDamageEffectsState4086_Ready',0xb62f);put(0x437e00+c.slot*20,7,4);put(0x437e10+c.slot*20,0xb5fb);put(0x437e12+c.slot*20,0);put(0x42d80c+c.slot*16,-2,4)\n"+anchor)
  if fall_requirements:
   lua=lua.replace('local ranges={',f'local ranges={{{{{speedup},2}},{{0x42e000,5120}},')
   lua=lua.replace(anchor,f" set('SourceFreeze4086_Ready',0xb5df);set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_Completed',0,4);set('SourceLandingVelocity4086_Ready',0xb626);set('SourceLandingVelocity4086_Autoland',1,4);put({speedup},0);put(0x42e024+c.slot*40,0xb5df);put(0x42e008+c.slot*40,123,4);put(0x42d800+c.slot*16,0,4);put(0x7ef104+c.slot*24,0,4);put(0x7ef108+c.slot*24,0,4)\n"+anchor)
  if rise_requirements:
   rb=recovery_plan['base'];rw=recovery_plan['controls']
   lua=lua.replace('local ranges={',f'local ranges={{{{{rb},{recovery_plan["bytes"]}}},{{0x7ef100,3072}},')
   initialization=f""" set('SourceDamageEffectsState4086_Ready',0xb62f)
 put({rw},0xb6c0);put({rw}+8,1,4);put({rw}+16,{rb&65535});put({rw}+18,0x42);put({rw}+20,{recovery_plan['chr_capacity']});put({rw}+22,128)
 for i=0,127 do put({rb}+16*i,-3,4);put({rb}+16*i+4,1234,4);put({rb}+16*i+8,1,4);put({rb}+16*i+12,0xb6c1);put({rb}+16*i+14,i)end
 put(0x7ef114+c.slot*24,0xb62f);put(0x7ef116+c.slot*24,c.new,2);put(0x7ef10c+c.slot*24,19,4)
"""
   lua=lua.replace(anchor,initialization+anchor)
  if lie_requirements:
   from source_hit_contact_layout import layout as contact_layout
   from source_hit_state_layout import layout as identity_layout
   from source_scoped_control_stack import layout as stack_layout
   cp=contact_layout();hp=identity_layout();sc=stack_layout();cap=recovery_plan['chr_capacity'];pal=current.layout();pal_req=current.derive(source)
   old_pal=current.current(pal_req,pal,sy,chr_capacity=sc['chr_capacity']);assert kw['append'].count(old_pal)==1
   kw['append']=kw['append'].replace(old_pal,current.current(pal_req,pal,sy,chr_capacity=cap))
   for owner in (pal['controls'],hp['controls']):lua=lua.replace(f'put({owner}+20,{sc["chr_capacity"]})',f'put({owner}+20,{cap})')
   lua=lua.replace('local ranges={',f'local ranges={{{{{cp["base"]},{cp["bytes"]}}},{{0x437e00,2560}},{{0x42d800,2048}},')
   initialization=f""" set('SourcePhysicsState4086_Ready',0xb61c);set('SourceDamageState4086_Ready',0xb62b);put(0x7fb908+c.slot*12,1)
 put({cp['controls']},0xb6a3);put({cp['controls']}+8,1,4);put({cp['controls']}+16,{cp['base']&65535});put({cp['controls']}+18,0x42);put({cp['controls']}+20,{cap});put({cp['controls']}+22,128)
 put(0x437e10+c.slot*20,0xb5fb);put(0x437e12+c.slot*20,0);put(0x437e00+c.slot*20,7,4);put(0x42d800+c.slot*16,1,4);put(0x7ef100+c.slot*24,2,4);put(0x439010+c.slot*80,9,4);put({cp['base']}+8*c.slot+4,17,4);put(0x42e008+c.slot*40,48,4)
"""
   lua=lua.replace(anchor,initialization+anchor)
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
  if a.doland:
   kw['probes']['ACTIONBAD']='CommonDolandFrame_Bad';kw['probes']['ACTIONPREFIXBAD']='CommonDoland_Bad'
   lua=lua.replace('value(view+8,2,4);',f'value(side+4,c.land_handle,2);value(side+8,c.land_nextanim,4);value(view+20,{ids["authority"]["enum"]["ANI_LAND"]},4);value(view+28,0,4);value(0x437e00+c.slot*20,0,4);value(0x42d80c+c.slot*16,0,4);value(0x7ef100+c.slot*24,0,4);value(0x7ef114+c.slot*24,0xb62f,2);value(0x7ef116+c.slot*24,c.new,2);value(0x43e000+(c.land_handle-1)*4,0,4);value(view+8,2,4);')
   lua=lua.replace('value(side+36,c.new_cached_type~=0 and 0 or 65536,4);value(side+40,c.new_cached_type~=0 and 0 or 2*65536,4);','value(side+36,0,4);value(side+40,0,4);').replace('value(0x43900c+c.slot*80,0,4)',f'value(0x43900c+c.slot*80,{function_id("common_land")},4)').replace('value(0x43eb04+c.slot*32,0,4)','value(0x43eb04+c.slot*32,1,4)')
   lua=lua.replace(f'word({work}+6)~=1 or word({work}+20)~=c.new_idle_handle',f'word({work}+6)~=2 or word({work}+20)~=c.land_handle').replace('word(sy.SourceUpdateFrame4086_Handle)~=c.new_idle_handle','word(sy.SourceUpdateFrame4086_Handle)~=c.land_handle')
  if a.land_action:
   kw['probes']['ACTIONBAD']='CommonLandFrame_Bad';kw['probes']['ACTIONPREFIXBAD']='CommonLand_Bad'
   lua=lua.replace('value(side+36,c.new_cached_type~=0 and 0 or 65536,4);value(side+40,c.new_cached_type~=0 and 0 or 2*65536,4);','value(side+36,0,4);value(side+40,0,4);')
  if fall_requirements:
   lua=lua.replace('value(side+44,3*65536,4)','value(side+44,0,4)').replace(f'word({work}+6)~=2 or word({work}+20)~=c.land_handle',f'word({work})~=0xb6bb or word({work}+6)~=0 or word({work}+20)~=c.land_handle')
  if lie_requirements:
   kw['probes']['ACTIONBAD']='CommonLieFrame_Bad';kw['probes']['ACTIONPREFIXBAD']='CommonLie_Bad'
   lua=lua.replace('value(side+44,3*65536,4)','value(side+44,0,4)').replace('value(side+36,c.new_cached_type~=0 and 0 or 65536,4);value(side+40,c.new_cached_type~=0 and 0 or 2*65536,4);','value(side+36,0,4);value(side+40,0,4);')
   lua=lua.replace('value(0x43900c+c.slot*80,0,4)',f'value(0x43900c+c.slot*80,{function_id("common_rise")},4)').replace('value(0x43eb00+c.slot*32,3,4);value(0x43eb04+c.slot*32,0,4);','value(0x43eb00+c.slot*32,3,4);value(0x43eb04+c.slot*32,1,4);')
   lua=lua.replace('value(view+20,0,4);','value(view+20,c.rise_role,4);').replace('value(side+4,c.new_idle_handle,2);','value(side+4,c.rise_handle,2);').replace('value(side+8,c.new_idle_nextanim,4);','value(side+8,c.rise_nextanim,4);')
   lua=lua.replace('value(side+4,c.wanted_idle_handle,2);','value(side+4,c.rise_handle,2);').replace('value(side+8,c.wanted_idle_nextanim,4);','value(side+8,c.rise_nextanim,4);')
   lua=lua.replace('word(sy.SourceUpdateFrame4086_Handle)~=c.new_idle_handle','word(sy.SourceUpdateFrame4086_Handle)~=c.rise_handle').replace('value(0x43e000+(c.new_idle_handle-1)*4,0,4)','value(0x43e000+(c.rise_handle-1)*4,0,4)')
   expected=f" value(0x439010+c.slot*80,0,4);value(0x437e00+c.slot*20,0,4);value(0x42d800+c.slot*16,0,4);value(0x7ef100+c.slot*24,0,4);value({cp['base']}+8*c.slot+4,0,4)\n"
   lua=lua.replace(' local n=0;for a,v in pairs(before)',expected+' local n=0;for a,v in pairs(before)')
  elif rise_requirements:
   kw['probes']['ACTIONBAD']='CommonRiseFrame_Bad';kw['probes']['ACTIONPREFIXBAD']='CommonRise_Bad'
   lua=lua.replace(' local n=0;for a,v in pairs(before)',f" value(0x7ef10c+c.slot*24,0,4)\n local inv=({luav([m['fields']['riseinv']for m in rise_requirements['models']])})[c.new+1]\n if inv~=0 then value({rb}+16*c.slot,inv>0 and 1 or 0,4);value({rb}+16*c.slot+4,48+math.abs(inv),4);value(0x439018+c.slot*80,1,4)end\n local n=0;for a,v in pairs(before)")
  if a.check_ai:
   lua=lua.replace('local ranges={','local ranges={{0x42e000,5120},')
   lua=lua.replace(' before={};for _,r in ipairs(ranges)'," set('SourceFreeze4086_Ready',0xb5df);put(0x42e024+c.slot*40,0xb5df)\n before={};for _,r in ipairs(ranges)")
   # This fixture deliberately supplies a null think pointer to isolate the
   # action->absent think script path, then uses the real check_ai dispatcher.
   lua=lua.replace(' local n=0;for a,v in pairs(before)'," value(0x439000+c.slot*80,0,4);value(0x416814+c.slot*64,0,4);value(sy.SourceSelf4086_GlobalLow,0x414000+c.slot*80,4)\n local n=0;for a,v in pairs(before)")
   start=lua.index(' if word('+str(work)+'+2)');end=lua.index(' end',start)+4
   lua=lua[:start]+f" if word({work})~=0xb680 or word({work}+2)~=0 or word(sy.SourceAnimationInit4086_State)~=2 or word(sy.SourceAI4086_State)~=5 or word(sy.SourceAIRun4086_State)~=2 then before[{work}+2]=255 end"+lua[end:]
  if a.check_ai:lua=lua.replace('word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*((c.slot+1)%128)','word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*c.slot')
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
  if a.doland:kw['probes']['ACTIONENTRY']='CommonDolandFrame_Run'
  if a.land_action:kw['probes']['ACTIONENTRY']='CommonLandFrame_Run'
  if rise_requirements:kw['probes']['ACTIONENTRY']='CommonRiseFrame_Run'
  if lie_requirements:kw['probes']['ACTIONENTRY']='CommonLieFrame_Run'
  if rise_requirements and not lie_requirements:
   kw['probes']['RISEMUTATE']='CommonRise_Blink'
   lua+=f"""
emu.addMemoryCallback(function()local d=emu.getState()['cpu.d'];emu.log('RISENATIVEINPUT|'..word(INDEX)..'|'..word({work}+16)..'|'..word({work}+18)..'|'..word(d+24)..'|'..word(d+26))end,emu.callbackType.exec,RISEMUTATE,RISEMUTATE,emu.cpuType.snes,mt)
"""
  if a.check_ai:
   lua+=f"""
emu.addMemoryCallback(function()emu.log('AIBRIDGESTATE|'..word(INDEX)..'|'..word({work})..'|'..word({work}+2)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAnimationInit4086_State))end,emu.callbackType.exec,ACTIONFINAL,ACTIONFINAL,emu.cpuType.snes,mt)
"""
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw);actual=[l.split('COMMONPAINFRAME|')[1]for l in log.splitlines()if'COMMONPAINFRAME|'in l];counts='0|0'if a.block_absent else'0|1'if a.doland or lie_requirements else'1|1';reporter.check('actual selected source action animation child completes once under retry',actual==[f'{i}|{counts}|0'for i in range(len(rows))]);
  return raw,log
 argv=['m4_model_current_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output),'--nested-idle']
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',argv):
  try:current.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_COMMON_PAIN_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=not a.block_absent,source_set_idle_bound=not a.block_absent,actual_animation_and_frame_owner_bound=not a.block_absent,stopped_pain_snapshot_installed_by_fixture=True,block_absence_branch_exercised=a.block_absent,block_frame_branch_exercised=False,full_common_pain_admitted=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,new_foreign_arena_bytes=0);path.write_text(json.dumps(r,indent=2)+'\n')
 if a.check_ai:
  r.update(actual_common_action_check_ai_bridge_bound=True,source_null_think_snapshot_installed_by_fixture=True,production_check_ai_consumer_bound=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if a.grabbed:
  r.update(schema='BYOR_COMMON_GRABBED_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=False,source_common_grabbed_idle_child_bound=True,source_unlinked_snapshot_installed_by_fixture=True,full_common_grabbed_admitted=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if block_requirements:
  r.update(schema='BYOR_COMMON_BLOCK_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=False,source_common_block_idle_child_bound=True,closed_zero_holdblock_model_policy=True,full_common_block_admitted=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if a.doland:
  r.update(schema='BYOR_DOLAND_LAND_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=False,source_set_idle_bound=False,source_doland_land_child_bound=True,land_presence_exercised=True,land_absence_exercised=False,full_common_fall_admitted=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if a.land_action:
  r.update(schema='BYOR_COMMON_LAND_IDLE_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=False,source_common_land_idle_child_bound=True,full_common_land_admitted=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if fall_requirements:
  r.update(schema='BYOR_COMMON_FALL_DOLAND_LAND_CHILD_NATIVE_V1',actual_common_fall_doland_tail_call_bound=True,actual_yield_resume_exercised=False,full_common_fall_admitted=False,production_unload_speedup_reset_bound=False,production_slowmotion_consumer_bound=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if rise_requirements:
  r.update(schema='BYOR_COMMON_RISE_IDLE_CHILD_NATIVE_V1',full_common_pain_admitted=False,actual_common_rise_idle_child_bound=True,recovery_storage_lease_installed_by_fixture=True,production_memory_lease=False,full_common_rise_admitted=False);path.write_text(json.dumps(r,indent=2)+'\n')
 if lie_requirements:
  r.update(schema='BYOR_COMMON_LIE_RISE_FRAME_CHILD_NATIVE_V1',source_common_pain_idle_child_bound=False,source_set_idle_bound=False,actual_common_rise_idle_child_bound=False,actual_common_lie_set_rise_child_bound=True,source_self_equals_target_exercised=True,source_missing_rise_branch_exercised=False,player_blink_suicide_children_bound=False,actual_yield_resume_exercised=False,full_common_lie_admitted=False);path.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
