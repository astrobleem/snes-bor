"""Native full32 grab predicate and actual null-victim early return."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,mutation=0,bad='')
 rows=[]
 for c,e in zip(authority['inputs'],authority['expected']):
  for slot in (0,1,63,127):rows.append(dict(base,**c,slot=slot,fault=int(bool(e[0]and c['link'])),result=e[0]))
 valid=next(c for c in rows if c['result']==1 and not c['fault'])
 for bad in ('ready','repeat','world','pool','side','count','slot','tick','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model','commonready','commonphase','commonslot','relations','core'):
  rows.append(dict(valid,bad=bad,fault=1))
 for c in rows:c['expected']=[0,0,0,0,0,c['update_mark'],48,6,0,1,5,1]
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 lua=lua.replace(' local faults='," set('SourceAIReadonly4086_Ready',0xb5e8);set('SourceAIReadonly4086_Status',0);set('SourceAIReadonly4086_Result',55);set('SourceRetirement4086_Ready',0xb4f8);set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',4);set('SourceCommonThink4086_Slot',s);set('SourceCommonThink4086_Response',55,4);put(0x40c050+s*96,c.grabbing,4);put(0x40c058+s*96,c.attacking,4);put(0x40901c+s*64,c.link==1 and 0x414000 or 0,4)\n local faults=")
 lua=lua.replace(" if c.bad=='token'"," if c.bad=='ready'then set('SourceAIReadonly4086_Ready',0)elseif c.bad=='repeat'then set('SourceAIReadonly4086_Status',2)elseif c.bad=='commonready'then set('SourceCommonThink4086_Ready',0)elseif c.bad=='commonphase'then set('SourceCommonThink4086_State',8)elseif c.bad=='commonslot'then set('SourceCommonThink4086_Slot',(s+1)%128)elseif c.bad=='relations'then set('SourceRetirement4086_Ready',0)elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)end\n if c.bad=='token'")
 lua=lua.replace('{{0x414000,18432}', '{{0x409000,8192},{0x40c000,12288},{0x414000,18432}')
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'));lua=lua[:start]+lua[end:]
 lua=lua.replace("word(sy.SourceAI4086_State)..'|'..table.concat(trace,',')","word(sy.SourceAIReadonly4086_Status)..'|'..word(sy.SourceAIReadonly4086_Result)..'|'..dw(sy.SourceCommonThink4086_Response)")
 entry=symbols(Path('src/main.sym'))['SourceAIReadonly4086_Execute'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-AI-GRAB',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceAIReadonly4086_Execute','SourceAIReadonly4086_Ready',0xb5e8,[],lua,r,batch_size=2)
 results=[list(map(int,l.split('AISEQUENCE|',1)[1].split('|')))for l in log.splitlines()if 'AISEQUENCE|'in l]
 wanted=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else c['result'],55 if c['fault']else c['result']]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('full32 grab/attack truth and literal no-victim return; linked execution and invalid ownership reject without response/live mutation',len(results)==len(rows)and not failures)
 d=dict(schema='BYOR_4086_AI_GRAB_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),linked_grab_handler_bound=False,common_think_dispatch_integrated=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
