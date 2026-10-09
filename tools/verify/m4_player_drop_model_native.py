"""Actual player dropweapon through synchronized source model services."""
import argparse,copy,itertools,json,struct,sys
from pathlib import Path
from unittest.mock import patch
import m4_model_current_pipeline_native as joined
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_player_drop_model_capability import derive
from source_player_drop_weapon_native import emit as drop
from source_damage_inputs_4086 import derive as damage_inputs
from source_model_scalar_service_native import emit as scalars,derive as scalar_inputs
from source_model_switch_4086 import CACHED_FIELDS,ENTITY_CORE_FIELDS,copy_cached_defaults,copy_entity_uninitialized
from source_model_core_4086 import FLOAT_FIELDS
from source_binary32_q16 import project


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--effects-state',action='store_true');p.add_argument('--fast-animation-inheritance',action='store_true')
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();source=Source(a.source);cap=derive(source);assert cap['all_declared_current_roles_synchronize'];sy=symbols(Path('src/main.sym'));original_rows=joined.parent.rows_for;original_fixture=joined.parent.run_fixture
 def rows_for(reports,data):
  models=[];maximum=reports['requirements']['maximum_animations']
  for i,m in enumerate(reports['requirements']['models']):
   d={f:struct.unpack_from('<f'if f in FLOAT_FIELDS else'<i',data['core'],160*i+4*j)[0]for j,f in enumerate(CACHED_FIELDS)};d['type']=struct.unpack_from('<i',data['core'],160*i+156)[0]
   d.update(model_flag=m['model_flag'],weapon=copy.deepcopy(m['weapon_ids']),numweapons=len(m['weapon_ids']or[]),animation={})
   for anim in reports['animations']['animations']:
    if anim['model']==m['identity']:d['animation'][anim['engine_animation_id']]=dict(handle=anim['handle'],numframes=anim['numframes'],delay=[f['delay_ticks']for f in reports['effects']['animations'][anim['handle']-1]['frames']])
   models.append(d)
  rows=[]
  for t in cap['transitions']:
   old,new=t['old_model'],t['new_model']
   for role in t['current_roles']:
    for slot,map_,last in itertools.product((0,1,127),(0,65535),(False,True)):
     before=copy.deepcopy(models[old]);copy_cached_defaults(models[t['default_model']],before);after=copy.deepcopy(models[new]);copy_cached_defaults(before,after);olddata=dict(before,type=1);hp=max(0,olddata['health']-1);mp=max(0,olddata['mp']-1);entity=dict(modeldata=dict(after),health=hp,mp=mp);copy_entity_uninitialized(entity,olddata);effective=entity['modeldata'];effective['type']=1
     anim=after['animation'][role];frame=before['animation'][role]['numframes']-1 if last else 0;wanted=min(frame,anim['numframes']-1)
     cache=b''.join(struct.pack('<f'if f in FLOAT_FIELDS else'<i',after[f])for f in CACHED_FIELDS)+struct.pack('<i',after['type'])
     core=b''.join(struct.pack('<i',effective[f])for f in ENTITY_CORE_FIELDS)+struct.pack('<2i',1,entity['mp'])+struct.pack('<4i',11,321,1,64)
     initial=b''.join(struct.pack('<i',olddata[f])for f in ENTITY_CORE_FIELDS)+struct.pack('<2i',1,mp)+struct.pack('<4i',11,321,1,64)
     animations=bytearray(data['animation_cache'][new*maximum*2:(new+1)*maximum*2])
     for number,v in after['animation'].items():struct.pack_into('<H',animations,number*2,v['handle'])
     rows.append(dict(slot=slot,old=old,new=new,default=t['default_model'],map=map_,frame=frame,role=role,number=0,keep=0,source_event=dict(frame_handle=before['animation'][role]['handle'],frame=frame),initial_core=list(initial),hp=hp,maxhp=olddata['health'],wanted_hp=entity['health'],wanted_maxhp=effective['health'],wanted_core=list(core),wanted_cache=list(cache),wanted_animation=list(animations),wanted_handle=anim['handle'],wanted_frame=wanted,wanted_nextanim=48+anim['delay'][wanted],speed_q16=project(struct.unpack('<I',struct.pack('<f',after['speed']))[0]),fault=0,bad=''))
     oldanimations=bytearray(data['animation_cache'][old*maximum*2:(old+1)*maximum*2])
     for number,v in before['animation'].items():struct.pack_into('<H',oldanimations,number*2,v['handle'])
     rows[-1].update(initial_old_cache=list(b''.join(struct.pack('<f'if f in FLOAT_FIELDS else'<i',before[f])for f in CACHED_FIELDS)+struct.pack('<i',before['type'])),initial_old_animations=list(oldanimations))
  # Parent guards remain an independent source request; the nominal matrix
  # below is the authored weapon/default-model closure, not a combat scene.
  rows.extend(c for c in original_rows(reports,data)if c['fault'])
  for c in rows:c.setdefault('default',c['new'])
  return rows
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  # Keep the real service dispatcher and observers. Replace its caller only.
  code=kw['append'];start=code.index('ModelPipeline_Apply:');end=code.index('ModelPipeline_EntryBad:',start)
  if a.effects_state:
   from source_foreign_state_layout import layout
   styles=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='entity_combostyle')
   sr=scalar_inputs(source);old=scalars(sr,styles,sy);assert code.count(old)==1
   code=code.replace(old,scalars(sr,styles,sy,effects_report=damage_inputs(source)))
  entry='''ModelPipeline_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl TIMINGLOAD
 bcs ModelPipeline_EntryBad
 jsl SourcePlayerDropWeapon4086_Execute
 bcs ModelPipeline_EntryBad
 cmp #0
 bne ModelPipeline_EntryBad
 ply
 plx
 plp
 clc
 rtl
'''
  entry=entry.replace('TIMINGLOAD',str(sy['SourceAttackTiming4086_Load']))
  kw['append']=code[:start]+entry+code[end:]+drop(sy,model_pipeline=True)
  anchor='local ranges={';assert lua.count(anchor)==1;lua=lua.replace(anchor,'local ranges={{0x43eb00,4096},{0x43ea00,16},')
  setup=f'''
 for i=0,4095 do put(0x43eb00+i,0,1)end
 for i=0,3 do put(0x43ea00+i*4,77,4)end
 put(0x43ea00,0,4);put(0x416802+64*c.slot,c.default)
 set('SourceDropWeapon4086_Ready',0xb635);set('SourceDropWeapon4086_Slot',c.slot);set('SourceDropWeapon4086_Status',0)
 if c.initial_old_cache then bytes(0x40b000+c.old*160,c.initial_old_cache);bytes(0x43c000+c.old*#c.initial_old_animations,c.initial_old_animations)end
'''
  anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1;lua=lua.replace(anchor,setup+anchor)
  if a.effects_state:
   lua=lua.replace('local ranges={','local ranges={{0x7ef100,3584},{0x7fb900,1536},')
   setup="""
 set('SourceDamageEffectsState4086_Ready',0xb62f)
 local ef=0x7ef100+24*c.slot;put(ef+20,0xb62f);put(ef+22,c.old);put(ef+16,77,4)
"""
   anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1;lua=lua.replace(anchor,setup+anchor)
   anchor=' if c.fault==0 then';assert lua.count(anchor)==1
   lua=lua.replace(anchor,anchor+'\n value(0x7ef110+24*c.slot,0,4);value(0x7ef116+24*c.slot,c.new,2)')
  # The real resolver changes player bookkeeping before native model guards.
  anchor=' local function value(a,v,n)';assert lua.count(anchor)==1
  at=lua.index('\n if c.fault==0 then',lua.index(anchor));lua=lua[:at]+"\n if c.bad~='token'then value(0x43ea00,0,4)end"+lua[at:]
  kw['frame_limit']=10000
  return original_fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
 args=['m4_model_current_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]+(['--fast-animation-inheritance']if a.fast_animation_inheritance else [])
 with patch.object(joined.parent,'rows_for',rows_for),patch.object(joined.parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:joined.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_PLAYER_DROP_MODEL_PIPELINE_NATIVE_V1',capability=cap,actual_player_dropweapon_called=True,damage_effect_model_refresh=a.effects_state,damage_effect_dynamics_retained=a.effects_state,role_matrix_is_combat_scene=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
