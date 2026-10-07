"""Actual animating common_spawn return, isolated owner and physical guards."""
import argparse,hashlib,json,itertools
from pathlib import Path
from m4_ai_owner_native import LUA
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 base=dict(time=48,nextthink=48,endgame=0,takeaction=4,think=2,noaicontrol=0,update_mark=0x12340001,animation=3,spawn=3,respawn=4,exists=1,mutation=0,bad='',fault=0)
 rows=[dict(base,slot=s,animating=anim,idling=idle)for s,anim,idle in itertools.product((0,1,63,127),(-1,1),(0,1,3))]
 for slot in (0,127):
  for bad in ('ready','busy','world','pool','side','count','slot','tick','phase','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model','actionid','actionwide','commonready','idlelease'):
   rows.append(dict(rows[0],slot=slot,bad=bad,fault=1))
 for c in rows:c['expected']=[0,0,0,0,0,c['update_mark'],c['nextthink'],c['think'],c['noaicontrol']&0xffffffff,c['exists'],c['animation'],c['animating']&0xffffffff]
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',1);set('SourceAI4086_Slot',s)")
 lua=lua.replace(" local faults=", " set('SourceCommonSpawn4086_Ready',0xb5e3);set('SourceCommonSpawn4086_State',0);set('SourceIdle4086_Ready',0xb4f3);put(flags,c.idling)\n local faults=")
 lua=lua.replace(" if c.bad=='token'", " if c.bad=='actionid'then put(life+12,99,4)elseif c.bad=='actionwide'then put(life+14,1)elseif c.bad=='commonready'then set('SourceCommonSpawn4086_Ready',0)elseif c.bad=='idlelease'then set('SourceIdle4086_Ready',0)end\n if c.bad=='token'")
 # 'ready' and 'busy' retain checks on parent AI capability and state.
 lua=lua.replace("busy={'SourceAI4086_State',1}","busy={'SourceAI4086_State',2}")
 lua=lua.replace(" if c.fault==0 then", " if c.fault==0 then before[0x43eb00+c.slot*32]=0;before[0x43eb01+c.slot*32]=0;")
 lua=lua.replace("word(sy.SourceAI4086_State)..'|'..table.concat(trace,',')", "word(sy.SourceCommonSpawn4086_State)..'|'..table.concat(trace,',')")
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'));lua=lua[:start]+lua[end:]
 sy=symbols(Path('src/main.sym'));entry=sy['SourceCommonSpawn4086_Begin']
 lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-COMMON-SPAWN',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCommonSpawn4086_Begin','SourceCommonSpawn4086_Ready',0xb5e3,[],lua,r,probes=dict(BODY='LeafFixture_Result'),batch_size=2)
 # No body request is issued by this leaf; remove its instrumentation callback.
 results=[list(map(int,line.split('AISEQUENCE|',1)[1].split('|')[:4]))for line in log.splitlines()if 'AISEQUENCE|'in line]
 wanted=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)];failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('animating return clears idling only; actual callback unchanged, full siblings and CPU/owner guards',len(results)==len(rows)and not failures)
 d=dict(schema='BYOR_4086_COMMON_SPAWN_ANIMATING_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),native_animating_domain=[-1,1],motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
