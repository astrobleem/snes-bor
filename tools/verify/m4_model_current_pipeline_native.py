"""Join independent palette identity and scoped controls to model services."""
import argparse,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_model_services_pipeline_native as parent
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_current_colourmap import derive,layout
from source_current_colourmap_native import emit as current
from source_hit_state_layout import layout as hit
from source_model_palette_service_native import emit as palette,derive as models
from source_scoped_control_stack import layout as stack,emit_frame_owner
from source_foreign_water_retirement import emit as water,transform as retire_water


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',required=True)
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--nested-idle',action='store_true');p.add_argument('--unsynchronized-model-frame',action='store_true');p.add_argument('--missing-model-animation-frame',action='store_true');p.add_argument('--fast-animation-inheritance',action='store_true');a=p.parse_args();a.output=a.output.resolve();src=Source(a.source);req=derive(src);plan=layout();h=hit();sc=stack();sy=symbols(Path('src/main.sym'));original=parent.run_fixture
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  for c in rows:c['old_active']=req['models'][c['old']]['maps_loaded']
  for service in (3,6):
   old=palette(models(src),sy,service);assert kw['append'].count(old)==1
   kw['append']=kw['append'].replace(old,palette(models(src),sy,service,current_palette=plan))
  kw['append']+=current(req,plan,sy,chr_capacity=sc['chr_capacity'])+emit_frame_owner(sc,sy,Path('src/core/vm/vm_source_frame_stack.pasm'))+water(sy)
  old_transform=kw.get('rom_transform')
  def transform(raw,linked):
   if old_transform:old_transform(raw,linked)
   retire_water(raw,linked)
   from m4_input_controller_native import offset
   for op in ('Push','PushNative','Pop'):
    at=offset(linked['SourceFrameStack4086_'+op]);assert raw[at:at+5]==bytes.fromhex('08 c2 38 8b da')
    raw[at:at+5]=b'\x5c'+linked['ScopedFrameStack4086_'+op].to_bytes(3,'little')+b'\xea'
  kw['rom_transform']=transform
  anchor='local ranges={';assert lua.count(anchor)==1
  lua=lua.replace(anchor,f'local ranges={{{{{plan["base"]},1536}},{{{h["base"]},2048}},{{0x420000,{sc["chr_capacity"]}}},')
  setup=f'''
 for i=0,127 do
  local row={plan['base']}+12*i;put(row,c.old);put(row+2,c.old_active);put(row+4,1,4);put(row+8,0xb6ac);put(row+10,i)
  put({h['base']}+16*i+8,1,4);put({h['base']}+16*i+12,0xb6a1);put({h['base']}+16*i+14,i)
 end
 for i=0,63 do put({plan['controls']}+i,0,1);put({h['controls']}+i,0,1)end
 put({plan['controls']},0xb6ab);put({plan['controls']}+4,c.slot);put({plan['controls']}+8,1,4);put({plan['controls']}+16,{plan['base']}&65535);put({plan['controls']}+18,0x42);put({plan['controls']}+20,{sc['chr_capacity']});put({plan['controls']}+22,128)
 put({h['controls']},0xb6a0);put({h['controls']}+8,1,4);put({h['controls']}+16,{h['base']}&65535);put({h['controls']}+18,0x42);put({h['controls']}+20,{sc['chr_capacity']});put({h['controls']}+22,128)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);put(sy.SourceWorldTick4086_TimeLo,48,4);put(sy.VmSourceWorld_Time,48,4)
 put({sc['controls']},0xb6ae);put({sc['controls']}+8,1,4);put({sc['controls']}+16,{sc['base']}&65535);put({sc['controls']}+18,0x42);put({sc['controls']}+20,{sc['chr_capacity']});put({sc['controls']}+22,8);put({sc['controls']}+24,{sc['stride']})
 for d=0,7 do put({sc['base']}+d*{sc['stride']},0)end
'''
  anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1;lua=lua.replace(anchor,setup+anchor)
  anchor=' value(0x433830+c.slot*64,0,2);';assert lua.count(anchor)==1
  lua=lua.replace(anchor,f' value({plan["base"]}+12*c.slot,c.new,2);value({plan["base"]}+12*c.slot+2,0,2);'+anchor)
  return original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
 args=['m4_model_services_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]+(['--nested-idle']if a.nested_idle else [])+(['--fast-animation-inheritance']if a.fast_animation_inheritance else [])+(['--unsynchronized-model-frame']if a.unsynchronized_model_frame else [])+(['--missing-model-animation-frame']if a.missing_model_animation_frame else [])
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_MODEL_CURRENT_PALETTE_PIPELINE_JOIN_V1',current_palette_reset_bound=True,scoped_control_frame_owner_installed=True,chr_capacity=sc['chr_capacity'],full_damage_callback_bound=False,production_memory_owner_bound=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
