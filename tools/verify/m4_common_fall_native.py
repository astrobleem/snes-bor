"""Closed native common_fall deadlines, speedup and retained doland ticket."""
import argparse,hashlib,itertools,json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_common_fall_native import emit
from source_common_damage_actions_4086 import run as reference
from source_foreign_water_retirement import emit as water,transform as retire_water
from source_model_switch_4086 import ENTITY_CORE_FIELDS
from m4_animation_init_native import luav
from m4_input_controller_native import offset
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','output','requirements'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=json.loads(a.requirements.read_text());sy=symbols(Path('src/main.sym'));regions=layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions'];work=next(r['address']for r in regions if r['name']=='common_idle_controls');speedup=next(r['address']for r in regions if r['name']=='global_fall_speedup');rows=[]
 seed=dict(slot=0,falling=0,y=0,vy=0,projectile=0,autoland=0,landing=0,boss=0,completed=0,speedup=0,model_rise=100,time=48,fault=0,bad='')
 for s,f,y,v in itertools.product((0,63,127),(0,1),(-6554,-6553,0,6553,6554),(0,65536)):rows.append(dict(seed,slot=s,falling=f,y=y,vy=v))
 for s,proj,auto,land in itertools.product((0,63,127),(-1,0,1,2,65536),(0,1,65537),(-2,-1,0,1)):rows.append(dict(seed,slot=s,projectile=proj,autoland=auto,landing=land))
 for s,b,c,r,t in itertools.product((0,63,127),(0,1),(0,1,-1),(-1,0,100),(48,4294967295)):rows.append(dict(seed,slot=s,boss=b,completed=c,model_rise=r,time=t,speedup=(s==63)))
 for bad in ('tag','generation','time','slot','world','life','action','pointer','alt_tag','physics','effects','frozen','ctor','landing_lease','completed_lease','effect_model','effect_marker','staydown','frozen_marker','rise','body_marker','speedup','state'):rows.append(dict(seed,fault=1,bad=bad))
 for c in rows:
  c['speedup']=int(c['speedup'])
  e,events=reference(dict(c,callback=1,action=2,air=int(abs(c['y'])>=6554),rise=0.,riseattack=0.,model_riseattack=0.,stall=123,rise_stall=19,inpain=-7,animating=0,link=0,blocking=0));c.update(wanted_action=21 if e['action']==5 else 22,wanted_stall=e['stall'],wanted_rise_stall=e['rise_stall'],wanted_speedup=e['speedup'],ticket=3 in events)
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_','SourceScrollerPrefix4086_','SourceCtorState4086_','SourceDamageEffectsState4086_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={},{},0;local aircalls=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);aircalls=0
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Time',c.time,4);set('SourceLifecycle4086_Ready',0xb4fb)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 set('SourcePhysicsState4086_Ready',0xb61c);set('SourceDamageEffectsState4086_Ready',0xb62f);set('SourceFreeze4086_Ready',0xb5df);set('SourceCtorState4086_Ready',0xb5c2);set('SourceLandingVelocity4086_Ready',0xb626);set('SourceLandingVelocity4086_Autoland',c.autoland,4);set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_Completed',c.completed,4);put(SPEEDUP,c.speedup)
 for i=0,127 do
  local v=0x414000+i*80;put(v,v,4);put(v+4,1,4);put(v+8,2,4);put(v+12,c.y,4)
  local s=0x416800+i*64;put(s,3);put(s+48,0,4);put(s+44,c.vy,4)
  local l=0x439000+i*80;put(l+12,22,4);put(l+72,3);put(l+74,0xb4fb)
  put(0x42d800+i*16,c.falling,4);put(0x42d80c+i*16,c.landing,4)
  local e=0x7ef100+i*24;put(e,c.projectile,4);put(e+4,0,4);put(e+8,0,4);put(e+12,19,4);put(e+20,0xb62f);put(e+22,3)
  local f=0x42e000+i*40;put(f+8,123,4);put(f+36,0xb5df)
  put(0x40c000+i*96+RISE,c.model_rise,4);put(0x433838+i*64,c.boss,4);put(0x43383e+i*64,0xb5c2)
 end
 for j=0,23 do put(CTRL+j,0,1)end;put(CTRL,0xb6bb);put(CTRL+4,c.slot);put(CTRL+8,1,4);put(CTRL+16,c.time,4)
 local slot=c.slot;local v=0x414000+slot*80
 if c.bad=='tag'then put(CTRL,0)elseif c.bad=='generation'then put(CTRL+8,2)elseif c.bad=='time'then put(CTRL+16,c.time+1,4)elseif c.bad=='slot'then put(CTRL+4,128)elseif c.bad=='world'then set('VmSourceWorld_Ready',0)elseif c.bad=='life'then put(0x43904a+slot*80,0)elseif c.bad=='action'then put(0x43900c+slot*80,0,4)elseif c.bad=='pointer'then put(v,v+1,4)elseif c.bad=='alt_tag'then put(v+8,1)elseif c.bad=='physics'then set('SourcePhysicsState4086_Ready',0)elseif c.bad=='effects'then set('SourceDamageEffectsState4086_Ready',0)elseif c.bad=='frozen'then set('SourceFreeze4086_Ready',0)elseif c.bad=='ctor'then set('SourceCtorState4086_Ready',0)elseif c.bad=='landing_lease'then set('SourceLandingVelocity4086_Ready',0)elseif c.bad=='completed_lease'then set('SourceScrollerPrefix4086_Ready',0)elseif c.bad=='effect_model'then put(0x7ef116+slot*24,4)elseif c.bad=='effect_marker'then put(0x7ef114+slot*24,0)elseif c.bad=='staydown'then put(0x7ef104+slot*24,1,4)elseif c.bad=='frozen_marker'then put(0x42e024+slot*40,0)elseif c.bad=='rise'then put(0x40c000+slot*96+RISE,101,4)elseif c.bad=='body_marker'then put(0x43383e+slot*64,0)elseif c.bad=='speedup'then put(SPEEDUP,2)elseif c.bad=='state'then put(CTRL+2,4)end
 before={};for _,r in ipairs({{0x414000,18432},{0x439000,10240},{0x42d800,2048},{0x7ef100,3072},{0x42e000,5120},{0x40c000,12288},{0x433800,8192},{SPEEDUP,2}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()aircalls=aircalls+1 end,emu.callbackType.exec,AIR,AIR,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then for _,f in ipairs({{0x43900c+c.slot*80,c.wanted_action,4},{0x42e008+c.slot*40,c.wanted_stall,4},{0x7ef10c+c.slot*24,c.wanted_rise_stall,4},{SPEEDUP,c.wanted_speedup,2}})do for j=0,f[3]-1 do before[f[1]+j]=(f[2]>>(8*j))&255 end end end
 local n=0;for at,v in pairs(before)do if emu.read(at,mt)~=v then n=n+1;if n<5 then emu.log('COMMONFALLDIFF|'..word(INDEX)..'|'..at..'|'..emu.read(at,mt)..'|'..v)end end end
 emu.log('COMMONFALLRESULT|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(CTRL+2)..'|'..word(CTRL+6)..'|'..aircalls)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 for k,v in dict(CTRL=work,SPEEDUP=speedup,RISE=ENTITY_CORE_FIELDS.index('risetime.rise')*4).items():lua=lua.replace(k,str(v))
 wrapper='''CommonFallProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl CommonFall_Run
 bcs CommonFallProbe_Bad
 jsl CommonFall_Run
 bcs CommonFallProbe_Bad
 ply
 plx
 plp
 clc
 rtl
CommonFallProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''+f'''CommonFallIsolatedReturn:
.a16
.i16
 php
 rep #$20
 pha
 lda #0
 sta.l {sy['VmSourceWorld_Ready']}
 sta.l {sy['SourceScrollerPrefix4086_Ready']}
 pla
 plp
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml {sy['Vm_SourceFrameGate']+5}
'''
 def isolate(raw,linked):
  retire_water(raw,linked);at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['CommonFallIsolatedReturn'].to_bytes(3,'little')
 r=Reporter('M4-COMMON-FALL-PREFIX',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'CommonFallProbe','SourceLifecycle4086_Ready',0xb4fb,[],lua,r,append=wrapper+emit(work,speedup,req,sy)+water(sy),rom_transform=isolate,batch_size=8,link_pcm=False,bindings={'AIR':'SourceInAir4086_Q16Compatibility'},frame_limit=600)
 actual=[list(map(int,l.split('COMMONFALLRESULT|')[1].split('|')))for l in log.splitlines()if'COMMONFALLRESULT|'in l];expected=[]
 for i,c in enumerate(rows):
  # Faults before inair do not enter it; later landed preflight faults do.
  early={'tag','generation','time','slot','world','life','action','pointer','alt_tag','physics','state'};calls=0 if c['falling']or(c['fault']and c['bad']in early)else 1
  expected.append([i,0,0,4 if c['fault']else 1 if c['ticket']else 2,0 if c['fault']or not c['ticket']else 1,calls])
 r.check('native source fall short-circuit, unsigned rise deadlines, speedup and retained doland request preserve all actor/CPU state under retry',actual==expected);r.check('bank0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768]);report=dict(schema='BYOR_COMMON_FALL_PREFIX_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),source_requirements_sha256=hashlib.sha256(a.requirements.read_bytes()).hexdigest(),source_speedup_bool_address=speedup,new_foreign_arena_bytes=2,foreign_arena_remaining_bytes=0,doland_child_executed=False,full_common_fall_admitted=False,production_stage_speedup_reset_bound=False,production_slowmotion_consumer_bound=False,numeric_policy=req['inair_policy'],motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
