"""Native common_land clears motion before retaining or requesting idle."""
import argparse,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_common_pain_native as parent
from source_common_grabbed_native import emit
from source_engine_function_ids import function_id
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();original=parent.run_fixture
 class LandReporter(Reporter):
  def __init__(self,*args,**kw):super().__init__('M4-COMMON-LAND-PREFIX',**kw)
  def check(self,name,ok):
   if name.startswith('actual common_pain'):name='native common_land clears horizontal motion even while animating and retains idle request once stopped under retry'
   return super().check(name,ok)
 def oracle(c):return dict(c,action=1 if c['animating']else 0),[]if c['animating']else[2]
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  rows[:]=[c for c in rows if c['bad']!='alt_tag']
  lua=lua.replace('0xb6b8','0xb6bd').replace('local s=0x416800+i*64;','local s=0x416800+i*64;put(s+36,65536,4);put(s+40,2*65536,4);put(s+44,3*65536,4);')
  needle=' local n=0;for at,v in pairs(before)';assert lua.count(needle)==1
  lua=lua.replace(needle," if c.fault==0 then for _,a in ipairs({0x416824+c.slot*64,0x416828+c.slot*64})do for j=0,3 do before[a+j]=0 end end end\n"+needle)
  kw['append']=kw['append'].replace('CommonPainProbe','CommonLandProbe').replace('jsl CommonPain_Run','jsl CommonLand_Run')
  for c in rows:c.update(initial_action='common_land')
  return original(rom,folder,rows,'CommonLandProbe',ready,magic,tables,lua,reporter,**kw)
 argv=['m4_common_pain_native.py','--rom',str(a.rom),'--output',str(a.output)]
 with patch.object(parent,'emit',lambda w,s:emit(w,s,kind='common_land')),patch.object(parent,'reference',oracle),patch.object(parent,'function_id',lambda n:function_id('common_land'if n=='common_pain'else n)),patch.object(parent,'run_fixture',fixture),patch.object(parent,'Reporter',LandReporter),patch.object(sys,'argv',argv):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 f=a.output/'report.json';r=json.loads(f.read_text());r.update(schema='BYOR_COMMON_LAND_PREFIX_NATIVE_V1',numeric_policy='closed animating truth; exact zero horizontal motion and retained vertical motion',native_common_pain_prefix_bound=False,native_common_land_prefix_bound=True,full_common_land_admitted=False);f.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
