"""Live source attack gate: every authored frame plus early exits and stale guards."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as _IMPORT_PATH
from compiler import Source
from source_hit_state_layout import layout
from source_hit_state_native import emit as storage
from source_check_attack_native import emit as gate,DO_ATTACK
from source_frame_state_4086 import derive,pack,unpack
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM="""AttackGateProbe:
.a16
.i16
 php
 phx
 phy
 sed
 ldx #1
 ldy #0
 jsl CheckAttack_Run
AttackGateProbe_Return:
.a16
.i16
 nop
 bcs AttackGateProbe_Bad
 ply
 plx
 plp
 clc
 rtl
AttackGateProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
"""
LUA=r"""
local mt=emu.memType.snesMemory;local before,cpu={},{};local ctx,ticket,decimal=0,0,0
local ranges={{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x42d800,2048},{0x437e00,2560},{0x7ef100,3072},{0x42e000,5120},{HB,2048}}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);ctx=0;ticket=0;decimal=0
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do put(r[1]+i,165,1)end end
 local v=0x414000+80*c.slot;local side=0x416800+64*c.slot;local phys=0x42d800+16*c.slot;local dmg=0x7ef100+24*c.slot;local combat=0x437e00+20*c.slot;local freeze=0x42e000+40*c.slot;local hit=HB+16*c.slot
 put(v,v,4);put(v+4,1,4);put(side+4,c.handle);put(side+6,c.frame);put(0x40c048+96*c.slot,1,4)
 put(phys,c.falling,4);put(dmg,c.projectile,4);put(dmg+20,0xb62f);put(combat,c.drop,4);put(combat+16,0xb5fb);put(freeze,c.frozen,4);put(freeze+4,c.deadline,4)
 put(hit,0xffffffff,4);put(hit+4,0x80000000,4);put(hit+8,1,4);put(hit+12,0xb6a1);put(hit+14,c.slot)
 for i=0,63 do put(HW+i,0,1)end;put(HW,0xb6a0);put(HW+8,1,4);put(HW+16,HB%65536);put(HW+18,0x42);put(HW+20,HC);put(HW+22,128)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);put(sy.VmSourceWorld_Time,48,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_View',80*c.slot);set('SourceWorldTick4086_Side',64*c.slot);put(sy.SourceWorldTick4086_TimeLo,48,4)
 set('SourcePhysicsState4086_Ready',0xb61c);set('SourceDamageEffectsState4086_Ready',0xb62f);set('SourceFreeze4086_Ready',0xb5df);put(0x43fd94,0,4);put(0x43fd98,0,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Fault',0);set('SourceSelf4086_Active',0);put(sy.SourceSelf4086_GlobalLow,v,4)
 set('SourceUpdateFrame4086_Ready',0);set('SourceFrameStack4086_Ready',0xb4ed);set('SourceFrameStack4086_Depth',0);set('SourceFrameStack4086_Fault',0)
 set('SourceCollisionFrame4086_Ready',0xb5ee);set('SourceCollisionFrame4086_Status',0);set('SourceCollisionFrame4086_Bank',58);set('SourceCollisionFrame4086_Bytes',CB)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 if c.bad=='phase'then set('SourceWorldTick4086_Phase',7)
 elseif c.bad=='pending'then set('SourceWorldTick4086_Pending',0)
 elseif c.bad=='time'then put(sy.SourceWorldTick4086_TimeLo,49,4)
 elseif c.bad=='world_side'then set('SourceWorldTick4086_Side',64*c.slot+2)
 elseif c.bad=='world_view'then set('SourceWorldTick4086_View',80*c.slot+2)
 elseif c.bad=='self'then put(sy.SourceSelf4086_GlobalLow,v+80,4)
 elseif c.bad=='retired'then put(v+4,0,4)
 elseif c.bad=='token'then put(v,v+1,4)
 elseif c.bad=='physics'then set('SourcePhysicsState4086_Ready',0)
 elseif c.bad=='damage'then set('SourceDamageEffectsState4086_Ready',0)
 elseif c.bad=='projectile_marker'then put(dmg+20,0)
 elseif c.bad=='drop_marker'then put(combat+16,0)
 elseif c.bad=='hit_generation'then put(hit+8,2,4)
 elseif c.bad=='canvas_generation'then put(sy.SourceForeignWork_Generation,2,4)
 elseif c.bad=='collision'then set('SourceCollisionFrame4086_Ready',0)
 elseif c.bad=='frame_busy'then set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',1);set('SourceUpdateFrame4086_Pending',1)
 elseif c.bad=='stack_busy'then set('SourceFrameStack4086_Depth',1)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ticket=s['cpu.a'];decimal=s['cpu.ps']&8 end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 and c.ticket==0 then for i=0,3 do before[HB+16*c.slot+i]=0 end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('ATTACKGATE|'..word(INDEX)..'|'..n..'|'..ctx..'|'..decimal..'|'..(c.fault==0 and ticket or -1)..'|'..word(sy.SourceWorldTick4086_Phase)..'|'..word(sy.SourceWorldTick4086_Pending))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);ir=derive(source);table=pack(ir);decoded=unpack(table);plan=layout();sy=symbols(Path('src/main.sym'));rows=[]
 for anim in decoded['animations']:
  for frame,f in enumerate(anim['frames']):rows.append(dict(slot=len(rows)%128,handle=anim['handle'],frame=frame,falling=0,projectile=0,drop=0,frozen=0,deadline=0,ticket=DO_ATTACK if f['attack_index']else 0,fault=0))
 active=next(r for r in rows if r['ticket']==DO_ATTACK)
 for slot in (0,1,127):
  for falling,projectile,drop,frozen,deadline in ((1,0,0,0,0),(0,0,-65536,0,0),(-65536,65536,-1,0,0),(65536,-1,1,0,0),(0,0,0,-65536,49),(0,0,0,65536,48),(0,0,0,1,0xffffffff)):
   inactive=bool(falling and not projectile or drop and not falling or frozen and deadline>48)
   rows.append(dict(active,slot=slot,falling=falling,projectile=projectile,drop=drop,frozen=frozen,deadline=deadline,ticket=0 if inactive else DO_ATTACK))
 for slot in (0,127):
  for bad in ('phase','pending','time','world_side','world_view','self','retired','token','physics','damage','projectile_marker','drop_marker','hit_generation','canvas_generation','collision','frame_busy','stack_busy'):
   rows.append(dict(active,slot=slot,bad=bad,fault=1))
 lua=LUA
 import re
 for k,v in dict(HW=plan['controls'],HB=plan['base'],HC=plan['chr_capacity'],CB=len(table)).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
 extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'}
 lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 reporter=Reporter('M4-SOURCE-CHECK-ATTACK-GATE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AttackGateProbe','VmState_Error',0xb6a0,[(58,0,table)],lua,reporter,append=ASM+storage(plan,sy)+gate(plan,sy),probes={'RETURN':'AttackGateProbe_Return'},batch_size=4,link_pcm=False)
 actual=[list(map(int,line.split('ATTACKGATE|',1)[1].split('|')))for line in log.splitlines()if 'ATTACKGATE|'in line]
 wanted=[[i,0,0,8,-1 if c['fault']else c['ticket'],7 if c.get('bad')=='phase'else 8,0 if c.get('bad')=='pending'else 1]for i,c in enumerate(rows)]
 reporter.check('every source frame, live native metadata query, exact inactive ID reset or mandatory attack ticket, stale guards and CPU',actual==wanted)
 reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_SOURCE_CHECK_ATTACK_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),source_frames=sum(len(x['frames'])for x in decoded['animations']),guard_cases=34,collision_table_sha256=hashlib.sha256(table).hexdigest(),source_models={x['model']:x['source_sha256']for x in ir['animations']},rom_sha256=hashlib.sha256(raw).hexdigest(),inputs=rows,results=actual,expected=wanted,plan=plan,world_phase_installed_by_fixture=True,memory_lease_installed_by_fixture=True,do_attack_bound=False,world_acknowledgements=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
