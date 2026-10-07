"""Unbound executable callback IDs fail explicitly in actual AI dispatcher."""
import argparse,hashlib,json,itertools
from pathlib import Path
from m4_ai_owner_native import LUA
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 rows=[]
 for slot,kind,identity in itertools.product((0,1,63,127),('action','think'),(1,2,6,99,65536,0xffffffff)):
  c=dict(time=48,nextthink=48,endgame=0,takeaction=identity if kind=='action'else 0,think=identity if kind=='think'else 0,noaicontrol=0,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,mutation=0,slot=slot,bad='',fault=1,kind=kind)
  c['expected']=[0,0,0,0,0,c['update_mark']|2,50 if kind=='think'else 48,c['think'],0,1,5,1];rows.append(c)
 lua=LUA.replace("set('SourceAI4086_Ready',0xb5e2)","set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);set('SourceAI4086_Ready',0xb5e2)")
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'));lua=lua[:start]+lua[end:]
 lua=lua.replace('if c.fault==0 then','if true then')
 lua=lua.replace("word(sy.SourceAI4086_State)..'|'..table.concat(trace,',')", "word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)")
 sy=symbols(Path('src/main.sym'));entry=sy['SourceAIRun4086_Begin'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-AI-UNBOUND',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceAIRun4086_Begin','SourceAIRun4086_Ready',0xb5e6,[],lua,r,batch_size=2)
 results=[list(map(int,l.split('AISEQUENCE|',1)[1].split('|')))for l in log.splitlines()if 'AISEQUENCE|'in l];wanted=[[i,0,0,3,1 if c['kind']=='action'else 2]for i,c in enumerate(rows)]
 r.check('unsupported action/think including authored player/enemy IDs fail; source mark/timer prefix and physical siblings/CPU preserved',results==wanted)
 d=dict(schema='BYOR_4086_AI_UNBOUND_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),unsupported_callback_body_skipped=False,world_tick_acknowledged=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
