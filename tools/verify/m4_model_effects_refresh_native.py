"""Model scalar effect lease refresh with retained entity damage dynamics."""
import argparse,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_model_scalar_service_native as parent
from compiler import Source
from source_damage_inputs_4086 import derive


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--synthetic-guard-words',action='store_true')
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();effects=derive(Source(a.source));original=parent.run_fixture;emit=parent.emit
 if a.synthetic_guard_words:
  values=(0,1,65535,65536,-1,-65536,-2147483648,2147483647)
  for i,m in enumerate(effects['models']):m['fields']['guardpoints']=values[i%len(values)]
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  for c in rows:c['guard']=effects['models'][c['model']]['fields']['guardpoints']
  rows.extend(dict(rows[0],slot=s,bad=bad,fault=1)for s in(0,1,127)for bad in('effect_ready','effect_marker','effect_owner','effect_old'))
  lua=lua.replace('local ranges={','local ranges={{0x7ef100,3584},{0x7fb900,1536},')
  anchor=' before={};for';assert lua.count(anchor)==1
  setup="""
 set('SourceDamageEffectsState4086_Ready',0xb62f)
 set('SourceModelTransition4086_Old',(c.model+1)%16)
 local ef=0x7ef100+24*c.slot;put(ef+20,0xb62f);put(ef+22,(c.model+1)%16);put(ef+16,77,4)
 if c.bad=='effect_ready'then set('SourceDamageEffectsState4086_Ready',0)
 elseif c.bad=='effect_marker'then put(ef+20,0)
 elseif c.bad=='effect_owner'then put(ef+22,c.model)
 elseif c.bad=='effect_old'then set('SourceModelTransition4086_Old',65535);put(ef+22,65535)end
"""
  lua=lua.replace(anchor,setup+anchor)
  anchor=' if c.fault==0 then';assert lua.count(anchor)==1
  lua=lua.replace(anchor,anchor+"\n for j=0,3 do before[0x7ef110+24*c.slot+j]=(c.guard>>(8*j))&255 end\n before[0x7ef116+24*c.slot]=c.model;before[0x7ef117+24*c.slot]=0")
  return original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
 args=['m4_model_scalar_service_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
 with patch.object(parent,'emit',lambda r,s,y:emit(r,s,y,effects_report=effects)),patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_MODEL_EFFECTS_REFRESH_NATIVE_V1',synthetic_guard_word_fixture=a.synthetic_guard_words,damage_effect_model_refresh=True,damage_effect_dynamics_retained=True,damage_counters_and_toexplode_retained=True,damage_inputs=effects);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
