"""common_rise stopped mutations, real recovery rows and retained idle request."""
import argparse,json,sys,itertools
from pathlib import Path
from unittest.mock import patch
import m4_common_pain_native as parent
from source_common_rise_native import emit
from source_recovery_state_layout import layout
from m4_animation_init_native import luav
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--requirements',type=Path,required=True)
 a,rest=p.parse_known_args();req=json.loads(a.requirements.read_text());plan=layout();base=plan['base'];rw=plan['controls'];original=parent.run_fixture
 class RiseReporter(Reporter):
  def __init__(self,*args,**kw):super().__init__('M4-COMMON-RISE-PREFIX',**kw)
  def check(self,name,ok):
   if name.startswith('actual common_pain'):name='actual common_rise mutation, source invincibility deadlines, retained idle request and sibling/CPU preservation under retry'
   return super().check(name,ok)
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  seed=dict(rows[0]);rows[:]=[]
  for slot,model,anim,time in itertools.product((0,63,127),range(len(req['models'])),(0,1,2),(0,48,65535,0xffffffff)):
   c=dict(seed,slot=slot,model=model,animating=anim,time=time,fault=0,bad='',expected_inpain=-7,expected_action=27 if anim else 0,service=0 if anim else 1);rows.append(c)
  seed=next(c for c in rows if c['model']==3 and c['animating']==0 and c['time']==48)
  for bad in ('tag','generation','time','slot','world','life_marker','action','pointer','status','effect_ready','effect_marker','effect_model','recovery_ready','recovery_generation','recovery_marker','recovery_row_generation','recovery_slot','recovery_capacity'):
   rows.append(dict(seed,fault=1,bad=bad))
  # Animated rise reads neither effect nor recovery storage. Zero riseinv
  # requires no blink/time lease even after the animation stops.
  for bad in ('effect_ready','recovery_ready','recovery_marker'):
   rows.append(dict(seed,animating=1,service=0,expected_action=27,fault=0,bad=bad))
  rows.append(dict(seed,model=0,fault=0,bad='recovery_ready'))
  sy=parent.symbols(Path('src/main.sym'))
  lua='local riseSymbols='+luav({k:v for k,v in sy.items()if k.startswith('SourceDamageEffectsState4086_')})+'\nfor k,v in pairs(riseSymbols)do sy[k]=v end\n'+lua
  lua=lua.replace('0xb6b8','0xb6c2').replace('put(l+12,23,4)','put(l+12,27,4)')
  needle=' before={};for _,r in ipairs(';assert lua.count(needle)==1
  initialization=f"""
 set('SourceDamageEffectsState4086_Ready',0xb62f)
 put({rw},0xb6c0);put({rw}+8,1,4);put({rw}+16,{base&65535});put({rw}+18,0x42);put({rw}+20,{plan['chr_capacity']});put({rw}+22,128)
 for i=0,127 do
  put({base}+16*i,-3,4);put({base}+16*i+4,1234,4);put({base}+16*i+8,1,4);put({base}+16*i+12,0xb6c1);put({base}+16*i+14,i)
  put(0x7ef114+i*24,0xb62f);put(0x7ef116+i*24,3);put(0x7ef10c+i*24,19,4);put(0x439018+i*80,-7,4)
 end
 put(0x416800+c.slot*64,c.model);put(0x439048+c.slot*80,c.model);put(0x7ef116+c.slot*24,c.model)
 if c.bad=='effect_ready'then set('SourceDamageEffectsState4086_Ready',0)
 elseif c.bad=='effect_marker'then put(0x7ef114+c.slot*24,0)
 elseif c.bad=='effect_model'then put(0x7ef116+c.slot*24,(c.model+1)%16)
 elseif c.bad=='recovery_ready'then put({rw},0)
 elseif c.bad=='recovery_generation'then put({rw}+8,2,4)
 elseif c.bad=='recovery_marker'then put({base}+16*c.slot+12,0)
 elseif c.bad=='recovery_row_generation'then put({base}+16*c.slot+8,2,4)
 elseif c.bad=='recovery_slot'then put({base}+16*c.slot+14,(c.slot+1)%128)
 elseif c.bad=='recovery_capacity'then put({rw}+20,{plan['chr_capacity']+1})end
"""
  lua=lua.replace(needle,initialization+needle).replace('ipairs({{0x414000',f'ipairs({{{{{base},{plan["bytes"]}}},{{0x7ef100,3072}},{{0x414000')
  needle=' local n=0;for at,v in pairs(before)';assert lua.count(needle)==1
  wanted=f"""
 if c.fault==0 and c.animating==0 then
  local function expect(at,v,n)for j=0,n-1 do before[at+j]=(v>>(8*j))&255 end end
  expect(0x7ef10c+c.slot*24,0,4)
  local inv=({luav([m['fields']['riseinv']for m in req['models']])})[c.model+1]
  if inv~=0 then expect({base}+16*c.slot,inv>0 and 1 or 0,4);expect({base}+16*c.slot+4,(c.time+math.abs(inv))&0xffffffff,4);expect(0x439018+c.slot*80,1,4)end
 end
"""
  lua=lua.replace(needle,wanted+needle)
  kw['append']=kw['append'].replace('jsl CommonPain_Run','jsl CommonRise_Run')
  return original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
 with patch.object(parent,'run_fixture',fixture),patch.object(parent,'emit',lambda w,sy:emit(w,plan,req,sy)),patch.object(parent,'Reporter',RiseReporter),patch.object(sys,'argv',['m4_common_pain_native.py',*rest]):
  parent.main()
 out=Path(rest[rest.index('--output')+1]);p=out/'report.json';r=json.loads(p.read_text());r.update(schema='BYOR_COMMON_RISE_PREFIX_NATIVE_V1',native_common_pain_prefix_bound=False,native_common_rise_prefix_bound=True,numeric_policy='source int32 riseinv and uint32 invincibility time; no altitude or velocity conversion in this callback',immutable_recovery_policy_installed_by_fixture=True,recovery_storage_lease_installed_by_fixture=True,production_memory_lease=False,actual_idle_frame_child_bound=False,full_common_rise_bound=False);p.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
