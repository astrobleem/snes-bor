"""Closed zero-holdblock native action with explicit retained idle request."""
import argparse,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_common_pain_native as parent
from source_common_grabbed_native import emit
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','output','authority'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';req=authority['requirements'];assert req['closed_zero_policy'];original=parent.run_fixture
 class BlockReporter(Reporter):
  def __init__(self,*args,**kw):super().__init__('M4-COMMON-BLOCK-PREFIX',**kw)
  def check(self,name,ok):
   if name.startswith('actual common_pain'):name='actual closed common_block animating short-circuit, blocking/action writes and retained idle request preserve sibling/CPU state under retry'
   return super().check(name,ok)
 def oracle(c):
  e=dict(c,action=4 if c['animating']else 0);return e,[]if c['animating']else[2]
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  lua=lua.replace('put(l+12,23,4)','put(l+12,25,4)').replace('0xb6b8','0xb6ba')
  lua=lua.replace('local s=0x416800+i*64;','local s=0x416800+i*64;put(s,3);')
  lua=lua.replace(" before={};for _,r in ipairs({{"," if c.bad=='alt_tag'then put(0x439048+c.slot*80,16)end\n before={};for _,r in ipairs({{")
  needle=' local n=0;for at,v in pairs(before)';assert lua.count(needle)==1
  lua=lua.replace(needle," if c.fault==0 and c.animating==0 then for j=0,3 do before[0x43eb14+c.slot*32+j]=0 end end\n"+needle)
  kw['append']=kw['append'].replace('CommonPainProbe','CommonBlockProbe').replace('jsl CommonPain_Run','jsl CommonBlock_Run')
  for c in rows:c.update(initial_action='common_block',holdblock=0,effective_bad='model_identity'if c['bad']=='alt_tag'else c['bad'])
  return original(rom,folder,rows,'CommonBlockProbe',ready,magic,tables,lua,reporter,**kw)
 argv=['m4_common_pain_native.py','--rom',str(a.rom),'--output',str(a.output)]
 with patch.object(parent,'emit',lambda w,s:emit(w,s,kind='common_block',requirements=req)),patch.object(parent,'reference',oracle),patch.object(parent,'run_fixture',fixture),patch.object(parent,'Reporter',BlockReporter),patch.object(sys,'argv',argv):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 f=a.output/'report.json';r=json.loads(f.read_text());r.update(schema='BYOR_COMMON_BLOCK_PREFIX_NATIVE_V1',numeric_policy='int32 animating truth, blocking and action identity',native_common_pain_prefix_bound=False,native_common_block_prefix_bound=True,closed_zero_holdblock_model_policy=True,full_common_block_admitted=False,source_authority=str(a.authority));f.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
