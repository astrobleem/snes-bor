"""Native normal_attack ordering/running mutation; selector bodies instrumented."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA,ASM
from source_normal_attack_authority import reference
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());assert au['status']=='PASS'
 base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,bad='',fault=0)
 rows=[dict(base,**c,slot=(0,1,63,127)[i%4],expected=reference(c))for i,c in enumerate(au['inputs'])]
 for bad in ('ready','busy','world','pool','side','count','slot','tick','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model','commonready','commonphase','commonslot'):
  rows.append(dict(rows[0],bad=bad,fault=1))
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 lua=lua.replace(' local faults='," set('SourceNormalAttack4086_Ready',0xb5eb);set('SourceNormalAttack4086_State',0);set('SourceNormalAttack4086_Result',55);set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s);put(0x42f404+s*24,c.running,4)\n local faults=")
 lua=lua.replace(" if c.bad=='token'"," if c.bad=='ready'then set('SourceNormalAttack4086_Ready',0)elseif c.bad=='busy'then set('SourceNormalAttack4086_State',8)elseif c.bad=='commonready'then set('SourceCommonThink4086_Ready',0)elseif c.bad=='commonphase'then set('SourceCommonThink4086_State',6)elseif c.bad=='commonslot'then set('SourceCommonThink4086_Slot',(s+1)%128)end\n if c.bad=='token'")
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'))
 lua=lua[:start]+"""emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local phase=word(sy.SourceNormalAttack4086_State);trace[#trace+1]=phase
 if c.mutation==1 then put(0x414004+c.slot*80,0,4)elseif c.mutation==2 then put(0x42f404+c.slot*24,0xffffffff,4)end
 set('SourceNormalAttack4086_Response',(c.mask&(1<<(phase-1)))~=0 and c.value or 0,4)
end,emu.callbackType.exec,BODY,BODY,emu.cpuType.snes,mt)
"""+lua[end:]
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local s=c.slot;local e=c.expected');lua=lua[:start]+"""emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local e=c.expected
 if c.fault==0 then for _,r in ipairs({{0x42f404+c.slot*24,e[8]},{0x414004+c.slot*80,e[9]}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('NORMALATTACK|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceNormalAttack4086_State)..'|'..word(sy.SourceNormalAttack4086_Result)..'|'..table.concat(trace,','))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
"""
 r=Reporter('M4-NORMAL-ATTACK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'AIProbe_Begin','SourceNormalAttack4086_Ready',0xb5eb,[],lua,r,append=ASM,bindings=dict(AIBEGIN='SourceNormalAttack4086_Begin',AICONTINUE='SourceNormalAttack4086_Continue',AISTATE='SourceNormalAttack4086_State'),probes=dict(BODY='AIProbe_Body'),batch_size=2)
 results=[]
 for l in log.splitlines():
  if 'NORMALATTACK|'in l:
   v=l.split('NORMALATTACK|',1)[1].split('|');results.append([*map(int,v[:5]),list(map(int,v[5].split(',')))if v[5]else []])
 wanted=[[i,0,0,8 if c['fault']else 7,55 if c['fault']else c['expected'][9],[]if c['fault']else c['expected'][1:1+c['expected'][0]]]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('pinned selector order, full32 true response/running clear, no inserted exists recheck, parent guards and physical siblings/CPU',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_NORMAL_ATTACK_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),selector_bodies_instrumented=True,common_enemy_grounded_attack_integrated=False,world_tick_acknowledged=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
