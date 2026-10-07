"""Actual registered common_attack_proc animating branch and owner guards."""
import argparse,hashlib,itertools,json
from pathlib import Path
from m4_ai_owner_native import LUA as OWNER_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--ai-dispatch',action='store_true');p.add_argument('--source',type=Path)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);au=json.loads(a.authority.read_text());assert au['status']=='PASS'
 base=dict(time=50,nextthink=50,endgame=0,takeaction=17,think=6,noaicontrol=0,reactive=1,update_mark=55,animation=5,spawn=3,respawn=4,exists=1,mutation=0,bad='',fault=0)
 rows=[dict(base,slot=s,animating=v)for s,v in itertools.product((0,1,95,96,127),(-32768,-1,1,32767))]
 for slot in (0,127):
  for bad in ('proc_ready','proc_busy','proc_sticky','ai_state','callback_low','callback_high','live_low','live_high','tick','phase','self_active','self_fault','token','model','animating_zero'):rows.append(dict(rows[0],slot=slot,bad=bad,fault=1))
 if a.ai_dispatch:rows=[c for c in rows if c['bad']in ('','proc_ready','proc_busy','proc_sticky','animating_zero')]
 lua=OWNER_LUA[:OWNER_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')]
 setup=r'''
 set('SourceAI4086_State',c.bad=='ai_state'and 2 or 1);set('SourceAI4086_Slot',s);put(sy.SourceAI4086_Callback,c.bad=='callback_low'and 16 or 17,4);if c.bad=='callback_high'then put(sy.SourceAI4086_Callback+2,1)end
 set('SourceCommonAttackProc4086_Ready',c.bad=='proc_ready'and 0 or 0xb607);set('SourceCommonAttackProc4086_Status',c.bad=='proc_busy'and 1 or c.bad=='proc_sticky'and 3 or 0)
 if c.bad=='live_low'then put(life+12,16)elseif c.bad=='live_high'then put(life+14,1)elseif c.bad=='animating_zero'then put(aux+16,0)end
 -- Source's first predicate must avoid even the Y coordinate/resource path.
 put(v+8,1,4);put(v+12,0x7fffffff,4);put(0x40c058+s*96,66,4)
 '''
 if a.ai_dispatch:
  assert a.source is not None
  from compiler import Source
  from source_script_clone import derive as clone_profile,pack as pack_clone
  from script_callback_owner import derive as callback_profile,pack as pack_callback
  source=Source(a.source);clone=pack_clone(clone_profile(source));cb,*_=callback_profile(source);callbacks=pack_callback(cb)
  setup+='''
 set('SourceAI4086_State',0);set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);put(life,0,4);put(0x410000+s*64,v,4);put(0x40902c+s*64,0,4)
 set('VmSourceWorld_TemplateCount',16);set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Base',0x8000);set('SourceScriptClone4086_Bank',59);set('SourceScriptClone4086_Bytes',CLONEBYTES);set('SourceScriptClone4086_Models',16)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_Base',0x8000);set('SourceAnimationCallback4086_Bank',60);set('SourceAnimationCallback4086_Models',16);set('SourceAnimationCallback4086_Programs',PROGRAMS)
 '''
  setup=setup.replace('CLONEBYTES',str(len(clone))).replace('PROGRAMS',str(cb['program_count']))
 lua=lua.replace(' before={};',setup+' before={};').replace('{{0x414000,18432}', '{{0x40c000,12288},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r'''
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('ATTACKPROCPREFIX|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceCommonAttackProc4086_Status))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
 if a.ai_dispatch:
  lua+="emu.addMemoryCallback(function()emu.log('ATKDISPATCH|'..word(INDEX)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 r=Reporter('M4-ATTACK-PROC-PREFIX',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceAIRun4086_Begin'if a.ai_dispatch else'SourceCommonAttackProc4086_Execute','SourceCommonAttackProc4086_Ready',0xb607,[(59,0,clone),(60,0,callbacks)]if a.ai_dispatch else[],lua,r,batch_size=2);actual=[list(map(int,l.split('ATTACKPROCPREFIX|',1)[1].split('|')))for l in log.splitlines()if 'ATTACKPROCPREFIX|'in l];expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 r.check('actual animating early return, no resource/coordinate service, unchanged entities/VM/RNG/CPU and explicit unfinished/owner faults',len(actual)==len(rows)and not failures)
 if a.ai_dispatch:
  dispatch=[list(map(int,l.split('ATKDISPATCH|',1)[1].split('|')))for l in log.splitlines()if'ATKDISPATCH|'in l]
  r.check('actual callback 17 dispatch and AI completion/explicit body failure',dispatch==[[i,3 if c['fault']else 2,1 if c['fault']else 5]for i,c in enumerate(rows)])
 report=dict(schema='BYOR_4086_ATTACK_PROC_PREFIX_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:10],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),stable_callback_id=17,actual_ai_dispatcher_executed=a.ai_dispatch,finished_attack_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
