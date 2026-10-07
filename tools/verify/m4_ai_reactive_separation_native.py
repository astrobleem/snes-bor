"""Real reactive frame leaf followed by isolated pinned AI sequencing."""
import argparse,hashlib,itertools,json
from pathlib import Path
from m4_ai_owner_native import ASM,LUA
from source_ai_authority import reference
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 rows=[]
 for slot,noai,mutation in itertools.product((0,1,63,127),(0,1,3,-1,65536),(0,3,8)):
  c=dict(slot=slot,noaicontrol=noai,reactive=65536,time=48,nextthink=48,endgame=0,takeaction=1,think=2,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,mutation=mutation,bad='',fault=0)
  c['expected']=reference(c);rows.append(c)
 asm=ASM.replace(' jsl AIBEGIN',' jsl REACTIVELEAF\n bcs AIProbe_Bad\nAIReactiveProbe_AfterEffect:\n.a16\n.i16\n nop\n jsl AIBEGIN')
 lua=LUA.replace(' local faults=',""" set('SourceFrameEffectLeaf4086_Ready',0xb4f4);set('SourceIdle4086_Ready',0xb4f3)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',1);set('SourceUpdateFrame4086_Pending',2);set('SourceUpdateFrame4086_Slot',s);set('SourceUpdateFrame4086_Handle',5);set('SourceUpdateFrame4086_Request',0);set('SourceUpdateFrame4086_View',0x4000+s*80);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bytes',128);set('SourceUpdateFrame4086_AnimationData',0x8000);set('SourceUpdateFrame4086_Animations',80)
 set('SourceFrameEffectPlan4086_Ready',0xb4f2);set('SourceFrameEffectPlan4086_State',1);set('SourceFrameEffectPlan4086_Service',22);set('SourceFrameEffectPlan4086_Acknowledged',0);set('SourceFrameEffectPlan4086_Slot',s);set('SourceFrameEffectPlan4086_Handle',5);set('SourceFrameEffectPlan4086_Frame',0);set('SourceFrameEffectPlan4086_Index',0);set('SourceFrameEffectPlan4086_Count',2);set('SourceFrameEffectPlan4086_Bank',59);set('SourceFrameEffectPlan4086_Base',0x8000);set('SourceFrameEffectPlan4086_Bytes',2);set('SourceFrameEffectPlan4086_Pool',0)
 local faults=""")
 lua=lua.replace(' if c.fault==0 then\n  local values='," if c.fault==0 then\n  for j=0,3 do before[0x43eb10+s*32+j]=(1>>(j*8))&255 end\n  local values=")
 lua+="""
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 emu.log('REACTIVEAI|'..word(INDEX)..'|'..dw(0x43eb10+c.slot*32)..'|'..dw(0x42f400+c.slot*24)..'|'..word(sy.SourceFrameEffectLeaf4086_Status)..'|'..word(sy.SourceFrameEffectPlan4086_Index)..'|'..word(sy.SourceFrameEffectPlan4086_Service))
 -- Isolated owner boundary: whole frame rendering/ack is instrumented here.
 set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
end,emu.callbackType.exec,EFFECTAFTER,EFFECTAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
"""
 r=Reporter('M4-AI-REACTIVE-SEPARATION',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AIProbe_Begin','SourceAI4086_Ready',0xb5e2,[(59,0,bytes((22,23))),(60,0,bytes(128))],lua,r,append=asm,bindings=dict(AIBEGIN='SourceAI4086_Begin',AICONTINUE='SourceAI4086_Continue',AISTATE='SourceAI4086_State',REACTIVELEAF='SourceFrameEffectLeaf4086_Apply'),probes=dict(BODY='AIProbe_Body',EFFECTAFTER='AIReactiveProbe_AfterEffect'),batch_size=2)
 results=[]
 for line in log.splitlines():
  if 'AISEQUENCE|'in line:
   parts=line.split('AISEQUENCE|',1)[1].split('|');results.append([*map(int,parts[:4]),list(map(int,parts[4].split(',')))if parts[4]else []])
 wanted=[[i,0,0,5,c['expected'][1:1+c['expected'][0]]]for i,c in enumerate(rows)]
 reactive=[list(map(int,l.split('REACTIVEAI|',1)[1].split('|')))for l in log.splitlines()if 'REACTIVEAI|'in l]
 r.check('actual reactive leaf changes reactive only, retains full32 noaicontrol and acknowledges its cursor operation',reactive==[[i,1,c['noaicontrol']&0xffffffff,1,1,23]for i,c in enumerate(rows)])
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('source AI decisions depend on noaicontrol, including callback changes, independently of actual reactive effect; CPU and all physical siblings retained',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_AI_REACTIVE_SEPARATION_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,reactive_results=reactive,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),reactive_frame_leaf_real=True,whole_frame_completion_instrumented=True,ai_callback_bodies_instrumented=True,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
