"""Native standalone model frame child with source-derived weapon arguments.

The caller supplies a synthetic sync or animation API input, an installed exclusive
pool and source tables. No parent frame is dispatched, no Ack is written by
the observer, and no spawnplayer/gameplay or production budget is claimed.
"""
import argparse,json,re,sys
from pathlib import Path
from unittest.mock import patch
import m4_model_current_pipeline_native as joined
from actor_s5_entity_fixture import symbols
from source_standalone_model_owner_native import emit


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--missing-model-animation',action='store_true')
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sy=symbols(Path('src/main.sym'));original=joined.parent.run_fixture
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  code=kw['append'];start=code.index('ModelPipeline_Apply:');end=code.index('ModelPipeline_EntryBad:',start)
  entry='''ModelPipeline_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl TIMING
 bcs ModelPipeline_EntryBad
 jsl RESOLVE
 bcs ModelPipeline_EntryBad
 lda.l SELECTED
 sta.l NEWMODEL
 lda.l SYNC
 sta.l MODELSYNC
 jsl BEGIN
 bcs ModelPipeline_EntryBad
StandaloneModelFixture_Loop:
.a16
.i16
 ldx #1
 ldy #0
 jsl StandaloneModelOwner_Resume
 bcs ModelPipeline_EntryBad
 cmp #$8001
 beq StandaloneModelFixture_Loop
 cmp #0
 bne ModelPipeline_EntryBad
 ply
 plx
 plp
 clc
 rtl
'''
  names=dict(TIMING='SourceAttackTiming4086_Load',RESOLVE='SourceWeapon4086_Resolve',SELECTED='SourceWeapon4086_Selected',NEWMODEL='SourceModelTransition4086_New',SYNC='SourceWeapon4086_Sync',MODELSYNC='SourceModelAnimation4086_Sync',BEGIN='SourceModelTransition4086_Begin')
  for name,target in names.items():entry=re.sub(r'\b'+name+r'\b',str(sy[target]),entry)
  kw['append']=code[:start]+entry+code[end:]+emit(sy)
  poison='put(sy.SourceWeapon4086_NumberLo,2147483647,4);';assert lua.count(poison)==1;lua=lua.replace(poison,'')
  old='word(sy.SourceUpdateFrame4086_Handle)~=c.source_event.frame_handle or word(sy.SourceUpdateFrame4086_Request)~=c.source_event.frame';assert lua.count(old)==1
  lua=lua.replace(old,'word(sy.SourceUpdateFrame4086_Handle)~=c.wanted_idle_handle or word(sy.SourceUpdateFrame4086_Request)~=0')
  # Pinned ent_set_anim restarts animation; it does not perform set_idle's
  # idling/velocity policy. This fixture dispatches no parent weapon/set_idle.
  old='if c.new_cached_type~=0 then value(side+36,0,4);value(side+40,0,4)end';assert lua.count(old)==1;lua=lua.replace(old,'')
  old='value(0x43eb00+c.slot*32,3,4);';assert lua.count(old)==1;lua=lua.replace(old,'value(0x43eb00+c.slot*32,0,4);')
  old_hook=kw.get('rom_transform')
  def hook(raw,linked):
   if old_hook:old_hook(raw,linked)
   assert linked['StandaloneModelOwner_Bad']>>16==39
  kw['rom_transform']=hook
  return original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
 args=['m4_model_current_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output),'--missing-model-animation-frame'if a.missing_model_animation else'--unsynchronized-model-frame']
 with patch.object(joined.parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:joined.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_STANDALONE_MODEL_FRAME_CHILD_NATIVE_V1',standalone_model_frame_child_bound=True,actual_parent_animation_callback=False,actual_frame_event_dispatch=False,actual_set_idle_prepare=False,source_request_registers_poisoned=False,source_effect_cursor_after_weapon=None,standalone_source_weapon_arguments=True,full_spawnplayer_bound=False,production_consumer_bound=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
