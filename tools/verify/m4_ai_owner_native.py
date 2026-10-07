"""Native check_ai sequence; action/think/script/idle bodies instrumented."""
import argparse,hashlib,json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_ai_authority import reference
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter
ASM='''
AIProbe_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl AIBEGIN
 bcs AIProbe_Bad
AIProbe_Loop:
.a16
.i16
 cmp #0
 beq AIProbe_Good
AIProbe_Body:
.a16
.i16
 nop
 lda.l AISTATE
 jsl AICONTINUE
 bcs AIProbe_Bad
 bra AIProbe_Loop
AIProbe_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
AIProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local before,cpu,ctx,trace={}, {},0,{}
local function mutation(c)
 local s=c.slot;local side=0x416800+s*64;local life=0x439000+s*80;local flags=0x43eb00+s*32;local aux=0x41f500+s*20
 if c.mutation==1 then put(side+20,(c.time+20)&0xffffffff,4)
 elseif c.mutation==2 then put(life,0,4)
 elseif c.mutation==3 then put(0x42f400+s*24,0xffffffff,4)
 elseif c.mutation==4 then put(0x414004+s*80,0,4)
 elseif c.mutation==5 then put(side+4,c.spawn);put(aux+16,0)
 elseif c.mutation==6 then put(side+4,5);put(aux+16,0)
 elseif c.mutation==7 then put(life+12,0,4);put(side+20,0,4)
 elseif c.mutation==8 then put(life,2,4);put(0x42f400+s*24,0,4)end
end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);trace={}
 local s=c.slot;local v=0x414000+s*80;local side=0x416800+s*64;local life=0x439000+s*80;local flags=0x43eb00+s*32;local aux=0x41f500+s*20
 put(v,v,4);put(v+4,c.exists,4);put(side,s%16);put(side+4,c.animation);put(side+20,c.nextthink,4);put(life,c.think,4);put(life+12,c.takeaction,4);put(0x42f400+s*24,c.noaicontrol,4);put(flags+16,c.reactive or 0,4);put(aux+16,c.animating);put(0x42e024+s*40,c.update_mark,4)
 local cache=0x43c000+(s%16)*256;put(cache+46,c.spawn);put(cache+208,c.respawn)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128);set('VmSourceWorld_Time',c.time,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_TimeLo',c.time,4)
 set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',0);set('SourceAI4086_Endgame',c.endgame,4);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceFreeze4086_Ready',0xb5df);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);set('SourceSelf4086_GlobalLow',v,4)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',128);set('SourceModelAnimationCopy4086_Bytes',4096)
 local faults={ready={'SourceAI4086_Ready',0},busy={'SourceAI4086_State',1},world={'VmSourceWorld_Ready',0},pool={'VmSourceWorld_PoolBase',0x4002},side={'VmSourceWorld_SideBase',0x6802},count={'VmSourceWorld_Count',129},slot={'SourceWorldTick4086_Slot',128},tick={'SourceWorldTick4086_Ready',0},phase={'SourceWorldTick4086_Phase',5},state={'SourceWorldTick4086_State',3},pending={'SourceWorldTick4086_Pending',0},time={'SourceWorldTick4086_TimeLo',(c.time+1)&0xffff},self_lease={'SourceSelf4086_Ready',0},self_active={'SourceSelf4086_Active',1},self_fault={'SourceSelf4086_Fault',1},self_pointer={'SourceSelf4086_GlobalLow',0},life={'SourceLifecycle4086_Ready',0},freeze={'SourceFreeze4086_Ready',0},cache={'SourceModelAnimationCopy4086_Ready',0},cache_models={'SourceModelAnimationCopy4086_Models',0},cache_max={'SourceModelAnimationCopy4086_Maximum',1025},cache_bytes={'SourceModelAnimationCopy4086_Bytes',4094},spawn_id={'SourceAI4086_SpawnID',128},respawn_id={'SourceAI4086_RespawnID',128}}
 if faults[c.bad]then local f=faults[c.bad];set(f[1],f[2])end
 if c.bad=='token'then put(v,0,4)elseif c.bad=='model'then put(side,16)end
 before={};for _,r in ipairs({{0x414000,18432},{0x41f500,2560},{0x42e000,5120},{0x42f400,3072},{0x439000,10240},{0x43eb00,4096},{0x43c000,8192},{sy.SourceWorldTick4086_Ready,52},{sy.SourceSelf4086_GlobalLow,4}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local phase=word(sy.SourceAI4086_State);trace[#trace+1]=phase
 if phase==1 then mutation(c)
 elseif phase==4 then put(0x416804+c.slot*64,5);put(0x41f510+c.slot*20,1)end
end,emu.callbackType.exec,BODY,BODY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local s=c.slot;local e=c.expected
 if c.fault==0 then
  local values={{0x42e024+s*40,e[6],4},{0x416814+s*64,e[7],4},{0x439000+s*80,e[8],4},{0x42f400+s*24,e[9],4},{0x414004+s*80,e[10],4},{0x416804+s*64,e[11],2},{0x41f510+s*20,e[12],2}}
  if c.mutation==7 and c.takeaction~=0 and c.nextthink<=c.time and c.endgame==0 then values[#values+1]={0x43900c+s*80,0,4}end
  for _,r in ipairs(values)do for i=0,r[3]-1 do before[r[1]+i]=(r[2]>>(i*8))&255 end end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('AISEQUENCE|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceAI4086_State)..'|'..table.concat(trace,','))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 d=json.loads(a.authority.read_text());assert d['status']=='PASS';rng=random.Random(40866);selected=sorted(set(rng.sample(range(2880),220)))+list(range(2880,len(d['inputs'])));rows=[]
 for i,index in enumerate(selected):
  c=dict(d['inputs'][index],slot=(0,1,63,127)[i%4],fault=0,bad='');c['expected']=reference(c);c['reactive']=(0,1,-1,65536)[i%4];rows.append(c)
 for bad in ('ready','busy','world','pool','side','count','slot','tick','phase','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model'):
  rows.append(dict(rows[-1],bad=bad,fault=1))
 r=Reporter('M4-AI-SEQUENCE',kind='GATE');lua=LUA
 lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
 raw,log=run_fixture(a.rom,a.output,rows,'AIProbe_Begin','SourceAI4086_Ready',0xb5e2,[],lua,r,append=ASM,bindings=dict(AIBEGIN='SourceAI4086_Begin',AICONTINUE='SourceAI4086_Continue',AISTATE='SourceAI4086_State'),probes=dict(BODY='AIProbe_Body'),batch_size=2)
 results=[]
 for line in log.splitlines():
  if 'AISEQUENCE|'in line:
   parts=line.split('AISEQUENCE|',1)[1].split('|');results.append([*map(int,parts[:4]),list(map(int,parts[4].split(',')))if parts[4]else []])
 wanted=[[i,0,0,6 if c['fault']else 5,[]if c['fault']else c['expected'][1:1+c['expected'][0]]]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('pinned callback order, mutation rechecks, full unsigned timers, physical siblings, CPU and guards',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_AI_SEQUENCE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),callback_bodies_instrumented=True,world_owner_integrated=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
