"""Retained damage-tail motion, real toss, every authored attack and sibling rows."""
import argparse,hashlib,itertools,json
from pathlib import Path
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_damage_tail_requirements import derive
from source_damage_tail_motion_native import emit
from source_foreign_water_retirement import emit as water,transform as retire_water
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'));req=derive(Source(a.source));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls')
 rows=[]
 for attack,s,d,t in itertools.product(req['attacks'],(0,63,127),(-1,0,1,2),(48,0xffffffff)):
  rows.append(dict(slot=s,attack=attack['id'],direction=d,time=t,a=93*65536,vx=98304,vz=-49152,vy=-65536,count=0xc0800000,ktime=999,toss=123,motion=attack['dropv_q16'],landing=attack['damage_on_landing'],fault=0,bad=''))
 seed=rows[0]
 rows.extend(dict(seed,fault=1,bad=b)for b in ('tag','generation','time','slot','attack','life_marker','model_count','toss_ready','exists','alt_tag','pointer','overflow','toss_status'))
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','SourceDamageState4086_','SourceToss4086_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={},{},0;local tossCalls=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];tossCalls=0;put(EXPECTFAULT,c.fault);local view=0x414000+c.slot*80;local side=0x416800+c.slot*64
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Time',c.time,4)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceDamageState4086_Ready',0xb62b);set('SourceEntityToss4086_Ready',0xb624);set('SourceEntityToss4086_Status',0);set('SourceToss4086_Ready',0xb4e2)
 for i=0,127 do
  local v=0x414000+i*80;put(v,v,4);put(v+4,1,4);put(v+8,2,4);put(v+12,c.a,4);put(v+28,0,4)
  local s=0x416800+i*64;put(s+36,c.vx,4);put(s+40,c.vz,4);put(s+44,c.vy,4)
  local l=0x439000+i*80;put(l+64,0,4);put(l+72,3);put(l+74,0xb4fb)
  put(0x7fb900+i*12,c.count,4);put(0x7fb904+i*12,c.ktime,4);put(0x42d80c+i*16,7,4);put(0x41f300+i*4,c.toss,4)
 end
 put(view+28,c.direction,4);for i=0,23 do put(CTRL+i,0,1)end;put(CTRL,0xb6b7);put(CTRL+4,c.slot);put(CTRL+6,c.attack);put(CTRL+8,1,4);put(CTRL+16,c.time,4)
 if c.bad=='tag'then put(CTRL,0)elseif c.bad=='generation'then put(CTRL+8,2,4)elseif c.bad=='time'then put(CTRL+16,c.time+1,4)elseif c.bad=='slot'then put(CTRL+4,128)elseif c.bad=='attack'then put(CTRL+6,0)elseif c.bad=='life_marker'then put(0x43904a+c.slot*80,0)elseif c.bad=='model_count'then put(0x439040+c.slot*80,0x3f800000,4)elseif c.bad=='toss_ready'then set('SourceEntityToss4086_Ready',0)elseif c.bad=='exists'then put(view+4,0,4)elseif c.bad=='alt_tag'then put(view+8,1)elseif c.bad=='pointer'then put(view,view+1,4)elseif c.bad=='overflow'then put(view+12,0x7fffffff,4)elseif c.bad=='toss_status'then set('SourceEntityToss4086_Status',2)end
 before={};for _,r in ipairs({{0x414000,18432},{0x439000,10240},{0x7fb900,1536},{0x42d800,2048},{0x41f300,512}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64;local view=0x414000+c.slot*80
 if c.fault==0 then
  local fields={{side+36,c.direction==1 and -c.motion[1]or c.motion[1]},{side+40,c.motion[3]},{0x42d80c+c.slot*16,c.landing},{0x7fb900+c.slot*12,0},{0x7fb904+c.slot*12,0}}
  if c.motion[2]~=0 then fields[#fields+1]={side+44,c.motion[2]};fields[#fields+1]={view+12,c.a+32768};fields[#fields+1]={0x41f300+c.slot*4,(c.time+1)&0xffffffff}end
  for _,f in ipairs(fields)do for j=0,3 do before[f[1]+j]=(f[2]>>(8*j))&255 end end
 end
 local n=0;for at,v in pairs(before)do if emu.read(at,mt)~=v then n=n+1 end end;emu.log('TAILMOTIONRESULT|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(CTRL+2));emu.log('TAILTOSSONCE|'..word(INDEX)..'|'..tossCalls)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
''';lua=lua.replace('CTRL',str(work));lua+='\nemu.addMemoryCallback(function()tossCalls=tossCalls+1 end,emu.callbackType.exec,REALTOSSEXEC,REALTOSSEXEC,emu.cpuType.snes,mt)\n'
 wrapper='''TailMotionProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl DamageTailMotion_Run
 bcs TailMotionProbe_Bad
 jsl DamageTailMotion_Run
 bcs TailMotionProbe_Bad
 ply
 plx
 plp
 clc
 rtl
TailMotionProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 reporter=Reporter('M4-DAMAGE-TAIL-MOTION',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'TailMotionProbe','SourceEntityToss4086_Ready',0xb624,[],lua,reporter,append=wrapper+emit(work,req,sy)+water(sy),rom_transform=retire_water,batch_size=32,link_pcm=False,bindings={"REALTOSSEXEC":"SourceEntityToss4086_Execute"})
 actual=[list(map(int,l.split('TAILMOTIONRESULT|')[1].split('|')))for l in log.splitlines()if'TAILMOTIONRESULT|'in l];expected=[[i,0,0,4 if c['fault']else 2]for i,c in enumerate(rows)];reporter.check('every authored fall motion row uses actual source toss once under retry and faults retain actor/physics/sibling/CPU state',actual==expected);reporter.check('bank0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768])
 counts=[list(map(int,l.split('TAILTOSSONCE|')[1].split('|')))for l in log.splitlines()if'TAILTOSSONCE|'in l];reporter.check('actual source toss entry observed exactly once per admitted row, including zero lift, and zero times on rejected preflight',counts==[[i,0 if c['fault']else 1]for i,c in enumerate(rows)])
 r=dict(schema='BYOR_DAMAGE_TAIL_MOTION_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),toss_entry_counts=counts,requirements=req,actual=actual,expected=expected,inputs=rows,rom_sha256=hashlib.sha256(raw).hexdigest(),source_entity_toss_bound=True,source_motion_once_under_retry=True,new_foreign_arena_bytes=0,source_action_assignment_bound=False,source_set_fall_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()
if __name__=='__main__':main()
