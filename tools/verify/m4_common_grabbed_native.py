"""Native common_grabbed link short-circuit and retained idle request."""
import json,sys
from pathlib import Path
from unittest.mock import patch
import m4_common_pain_native as parent
from source_common_grabbed_native import emit
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _harness import Reporter

def main():
 original=parent.run_fixture;reference=parent.reference;sy=symbols(Path('src/main.sym'))
 class GrabbedReporter(Reporter):
  def __init__(self,*args,**kw):super().__init__('M4-COMMON-GRABBED-PREFIX',**kw)
  def check(self,name,ok):
   if name.startswith('actual common_pain'):name='actual common_grabbed link short-circuit, stall/action writes and retained idle request preserve sibling/CPU state under retry'
   return super().check(name,ok)
 def oracle(c):return reference(dict(c,callback=2,action=3))
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  # A linked actor does not read the stalltime lease. Test lease failure only
  # on the parent's unlinked seed; altitude is not read by common_grabbed.
  lua='local grabSymbols='+luav({k:v for k,v in sy.items()if k.startswith('SourceFreeze4086_')})+'\nfor k,v in pairs(grabSymbols)do sy[k]=v end\n'+lua
  lua=lua.replace("for i=0,23 do put(","set('SourceFreeze4086_Ready',0xb5df);for i=0,127 do put(0x42e024+i*40,0xb5df);put(0x42e008+i*40,123,4)end\n for i=0,23 do put(")
  lua=lua.replace('0xb6b8','0xb6b9').replace("before={};for _,r in ipairs({{", "if c.bad=='alt_tag'then set('SourceFreeze4086_Ready',0)end\n before={};for _,r in ipairs({{0x42e000,5120},{")
  needle=' local n=0;for at,v in pairs(before)';assert lua.count(needle)==1
  lua=lua.replace(needle," if c.fault==0 and c.link==0 then for j=0,3 do before[0x42e008+c.slot*40+j]=0 end end\n"+needle)
  rows[:]=[dict(c)for c in rows]
  for c in rows:c.update(initial_action='common_grabbed',effective_bad='stall_lease'if c['bad']=='alt_tag'else c['bad'])
  # The parent initializes its action literal as common_pain; only the input
  # fixture changes. Expected actions come from the pinned grabbed oracle.
  lua=lua.replace('put(l+12,23,4)','put(l+12,24,4)')
  kw['append']=kw['append'].replace('CommonPainProbe','CommonGrabbedProbe').replace('jsl CommonPain_Run','jsl CommonGrabbed_Run')
  return original(rom,folder,rows,'CommonGrabbedProbe',ready,magic,tables,lua,reporter,**kw)
 with patch.object(parent,'emit',emit),patch.object(parent,'reference',oracle),patch.object(parent,'run_fixture',fixture),patch.object(parent,'Reporter',GrabbedReporter):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 folder=Path(sys.argv[sys.argv.index('--output')+1]);p=folder/'report.json';r=json.loads(p.read_text());r.update(schema='BYOR_COMMON_GRABBED_PREFIX_NATIVE_V1',native_common_pain_prefix_bound=False,native_common_grabbed_prefix_bound=True,numeric_policy='integer link truth, uint32 stalltime and action identity',full_common_grabbed_bound=False);p.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
