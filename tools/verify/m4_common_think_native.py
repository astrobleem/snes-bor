"""Native common enemy thinker sequencing; handler bodies instrumented."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as AI_LUA,ASM as AI_ASM
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);au=json.loads(a.authority.read_text());assert au['status']=='PASS'
 base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,mutation=0,bad='',fault=0)
 rows=[dict(base,**c,slot=(0,1,63,127)[i%4],expected_trace=au['expected'][i][1:1+au['expected'][i][0]])for i,c in enumerate(au['inputs'])]
 for bad in ('ready','busy','world','pool','side','count','slot','tick','phase','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model','commonready','commonbusy','thinkid','thinkwide'):
  rows.append(dict(rows[0],bad=bad,fault=1,expected_trace=[]))
 for c in rows:c['expected']=[0,0,0,0,0,c['update_mark'],48,6,0,1,5,1]
 lua=AI_LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 lua=lua.replace("busy={'SourceAI4086_State',1}","busy={'SourceAI4086_State',1}")
 lua=lua.replace(" local faults=", " set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',0);put(life+20,c.dead,4)\n local faults=")
 lua=lua.replace(" if c.bad=='token'", " if c.bad=='commonready'then set('SourceCommonThink4086_Ready',0)elseif c.bad=='commonbusy'then set('SourceCommonThink4086_State',1)elseif c.bad=='thinkid'then put(life,2,4)elseif c.bad=='thinkwide'then put(life+2,1)end\n if c.bad=='token'")
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'))
 lua=lua[:start]+r'''emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local phase=word(sy.SourceCommonThink4086_State);trace[#trace+1]=phase
 set('SourceCommonThink4086_Response',(c.mask&(1<<(phase-1)))~=0 and c.value or 0,4)
 if c.mutate_dead==1 then put(0x439014+c.slot*80,1,4)end
end,emu.callbackType.exec,BODY,BODY,emu.cpuType.snes,mt)
'''+lua[end:]
 lua=lua.replace("if c.fault==0 then\n  local values=", "if c.fault==0 then\n  if c.mutate_dead==1 and #c.expected_trace>0 then for j=0,3 do before[0x439014+c.slot*80+j]=j==0 and 1 or 0 end end\n  local values=")
 lua=lua.replace("word(sy.SourceAI4086_State)..'|'..table.concat(trace,',')", "word(sy.SourceCommonThink4086_State)..'|'..table.concat(trace,',')")
 lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
 asm=AI_ASM.replace('AIProbe','CommonThinkProbe')
 r=Reporter('M4-COMMON-THINK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'CommonThinkProbe_Begin','SourceCommonThink4086_Ready',0xb5e7,[],lua,r,append=asm,bindings=dict(AIBEGIN='SourceCommonThink4086_Begin',AICONTINUE='SourceCommonThink4086_Continue',AISTATE='SourceCommonThink4086_State'),probes=dict(BODY='CommonThinkProbe_Body'),batch_size=2)
 results=[]
 for l in log.splitlines():
  if 'AISEQUENCE|'in l:
   parts=l.split('AISEQUENCE|',1)[1].split('|');results.append([*map(int,parts[:4]),list(map(int,parts[4].split(',')))if parts[4]else []])
 wanted=[[i,0,0,10 if c['fault']else 9,c['expected_trace']]for i,c in enumerate(rows)];failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('complete pinned short-circuit order, full32 truth/dead fields, no inserted dead rechecks, physical/CPU and owner guards',len(results)==len(rows)and not failures)
 d=dict(schema='BYOR_4086_COMMON_THINK_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),handler_bodies_instrumented=True,common_enemy_thinker_executable=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
