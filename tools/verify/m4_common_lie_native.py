"""Closed common_lie deadline/coordinate gate and real persistent death blink."""
import argparse,itertools,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_common_pain_native as parent
from source_common_lie_native import emit
from source_recovery_requirements import derive
from source_recovery_state_layout import layout
from source_recovery_4086 import common_lie
from source_model_core_4086 import derive as core
from compiler import Source
from m4_animation_init_native import luav
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);a,rest=p.parse_known_args();source=Source(a.source);req=derive(source);model_types=[m['fields']['type']for m in core(source)['models']];plan=layout();rb=plan['base'];rw=plan['controls'];original=parent.run_fixture
 class LieReporter(Reporter):
  def __init__(self,*args,**kw):super().__init__('M4-COMMON-LIE-PREFIX',**kw)
  def check(self,name,ok):
   if name.startswith('actual common_pain'):name='actual common_lie deadline, projected coordinate equality, retained rise request, source death action and blink preserve sibling/CPU state under retry'
   return super().check(name,ok)
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  seed=dict(rows[0]);rows[:]=[]
  states=((0,0,0,0),(48,47,0,0),(48,48,0,0),(48,49,0,0),(48,48,1,0),(48,48,0,1),(65535,65535,0,0),(0xffffffff,0xffffffff,0,0))
  for slot,model,hp,values in itertools.product((0,63,127),range(16),(-1,0,100),states):
   time,stall,y,vy=values;state=dict(health=hp,falldie=0,nodieblink=0,type=model_types[model],animating=0,damagetype=1,blink=-3,stall=stall,noai=0,ko=0,kotype=0,colourmap=0,y=y,base=0,vy=vy,action=1)
   events=common_lie(state,time);service=int(bool(events));action={1:21,2:28,3:29}[state['action']]
   rows.append(dict(seed,slot=slot,model=model,hp=hp,time=time,stall=stall,y=y,vy=vy,fault=0,bad='',expected_inpain=-7,expected_action=action,service=service,expected_stall=state['stall'],expected_blink=state['blink']))
  ready_case=next(c for c in rows if c['hp']==100 and c['time']==48 and c['stall']==48 and c['y']==0 and c['vy']==0)
  dead_case=next(c for c in rows if c['hp']==0 and c['time']==48)
  for bad in ('tag','generation','time','slot','world','life_marker','action','pointer','status','alt_tag','stall_ready','stall_marker','damage_ready'):
   rows.append(dict(ready_case,fault=1,bad=bad))
  for bad in ('ctor_ready','ctor_marker','model','recovery_ready','recovery_generation','recovery_marker','recovery_row_generation','recovery_slot','recovery_capacity'):
   rows.append(dict(dead_case,fault=1,bad=bad))
  sy=parent.symbols(Path('src/main.sym'));lua='local lieSymbols='+luav({k:v for k,v in sy.items()if k.startswith(('SourceFreeze4086_','SourceCtorState4086_','SourceDamageState4086_'))})+'\nfor k,v in pairs(lieSymbols)do sy[k]=v end\n'+lua
  lua=lua.replace('0xb6b8','0xb6c4').replace('put(l+12,23,4)','put(l+12,21,4)')
  needle=' before={};for _,r in ipairs(';assert lua.count(needle)==1
  initialization=f"""
 set('SourceFreeze4086_Ready',0xb5df);set('SourceCtorState4086_Ready',0xb5c2);set('SourceDamageState4086_Ready',0xb62b)
 put({rw},0xb6c0);put({rw}+8,1,4);put({rw}+16,{rb&65535});put({rw}+18,0x42);put({rw}+20,{plan['chr_capacity']});put({rw}+22,128)
 for i=0,127 do
  put({rb}+16*i,-3,4);put({rb}+16*i+4,1234,4);put({rb}+16*i+8,1,4);put({rb}+16*i+12,0xb6c1);put({rb}+16*i+14,i)
  put(0x42e024+i*40,0xb5df);put(0x42e008+i*40,c.stall,4);put(0x43383e+i*64,0xb5c2)
 end
 put(view+32,1,4);put(view+36,c.hp,4);put(0x41682c+c.slot*64,c.vy,4)
 put(0x416800+c.slot*64,c.model);put(0x439048+c.slot*80,c.model);put(0x40c048+c.slot*96,({luav(model_types)})[c.model+1],4);put(0x7fb908+c.slot*12,1)
 if c.bad=='stall_ready'then set('SourceFreeze4086_Ready',0)
 elseif c.bad=='stall_marker'then put(0x42e024+c.slot*40,0)
 elseif c.bad=='damage_ready'then set('SourceDamageState4086_Ready',0)
 elseif c.bad=='ctor_ready'then set('SourceCtorState4086_Ready',0)
 elseif c.bad=='ctor_marker'then put(0x43383e+c.slot*64,0)
 elseif c.bad=='model'then put(0x439048+c.slot*80,(c.model+1)%16)
 elseif c.bad=='recovery_ready'then put({rw},0)
 elseif c.bad=='recovery_generation'then put({rw}+8,2,4)
 elseif c.bad=='recovery_marker'then put({rb}+16*c.slot+12,0)
 elseif c.bad=='recovery_row_generation'then put({rb}+16*c.slot+8,2,4)
 elseif c.bad=='recovery_slot'then put({rb}+16*c.slot+14,(c.slot+1)%128)
 elseif c.bad=='recovery_capacity'then put({rw}+20,{plan['chr_capacity']+1})end
"""
  lua=lua.replace(needle,initialization+needle).replace('ipairs({{0x414000',f'ipairs({{{{{rb},{plan["bytes"]}}},{{0x42e000,5120}},{{0x40c000,12288}},{{0x414000')
  needle=' local n=0;for at,v in pairs(before)';assert lua.count(needle)==1
  expected=f""" if c.fault==0 then local function expect(at,v,n)for j=0,n-1 do before[at+j]=(v>>(8*j))&255 end end;expect({rb}+16*c.slot,c.expected_blink,4);expect(0x42e008+c.slot*40,c.expected_stall,4)end
"""
  lua=lua.replace(needle,expected+needle)
  kw['append']=kw['append'].replace('jsl CommonPain_Run','jsl CommonLie_Run')
  return original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
 with patch.object(parent,'run_fixture',fixture),patch.object(parent,'emit',lambda w,sy:emit(w,plan,req,sy)),patch.object(parent,'Reporter',LieReporter),patch.object(sys,'argv',['m4_common_pain_native.py',*rest]):parent.main()
 out=Path(rest[rest.index('--output')+1]);p=out/'report.json';r=json.loads(p.read_text());r.update(schema='BYOR_COMMON_LIE_PREFIX_NATIVE_V1',native_common_pain_prefix_bound=False,native_common_lie_prefix_bound=True,numeric_policy='source uint32 deadline; equality within existing ACCEPTED_COMPAT_Q16_16 altitude/base projection',recovery_storage_lease_installed_by_fixture=True,actual_set_rise_child_bound=False,player_blink_suicide_children_bound=False,full_common_lie_bound=False,production_memory_lease=False);p.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
