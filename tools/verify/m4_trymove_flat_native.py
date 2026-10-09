"""Bounded real-row flat movement callback, bounds and CRT random proof."""
import argparse
import hashlib
import itertools
import re
import json
from pathlib import Path
from compiler import Source
from source_trymove_requirements import derive
from source_trymove_flat_native import emit
from source_trymove_authority import cases, evaluate, bits
from source_foreign_state_layout import layout
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from m4_check_attack_native import LUA as FOREIGN_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''FlatTrymoveProbe:
.a16
.i16
 php
 phx
 phy
 sed
 ldx #1
 ldy #0
 jsl FlatTrymove_Execute
FlatTrymoveProbe_Return:
.a16
.i16
 bcs FlatTrymoveProbe_Bad
 ply
 plx
 plp
 clc
 rtl
FlatTrymoveProbe_Bad:
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
local before,cpu={},{};local ctx,ticket,decimal=0,0,0
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(n,v,b)put(assert(sy[n],n),v,b)end
local ranges={{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x41f500,2560},{0x439000,10240},{0x43c000,5376},{0x43eb00,4096}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);ctx=0;ticket=0;decimal=0
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do put(r[1]+i,0,1)end end
 local s=c.slot;local v=0x414000+80*s;local side=0x416800+64*s;local core=0x40c000+96*s;local aux=0x41f500+20*s;local life=0x439000+80*s
 for i=0,95 do put(W+i,0,1)end
 put(W,0xb6a5);put(W+6,1);put(W+8,16);put(W+10,s);put(W+12,1,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Level',1);set('VmSourceWorld_TemplateCount',16);set('VmSourceWorld_Time',48,4);set('VmSourceWorld_AdvanceX',c.camera,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',c.world_state);set('SourceWorldTick4086_Phase',11);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_View',80*s);set('SourceWorldTick4086_Side',64*s);set('SourceWorldTick4086_TimeLo',48,4)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',16);set('SourceModelEntityCopy4086_Entities',128)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);set('SourceSelf4086_GlobalLow',v,4)
 set('SourceEmptyInitEnvironment4086_Ready',0xb504);set('SourceEmptyInitEnvironment4086_Status',0);set('SourceEmptyInitEnvironment4086_Models',16);set('SourceEmptyInitEnvironment4086_Stage',1)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_WallCount',0);set('SourceEnvironment4086_Stage',1)
 set('SourceCameraMotion4086_Ready',0xb5db);set('SourceCameraMotion4086_HRes',320);set('SourceCameraMotion4086_MinZ',c.minz,4);set('SourceCameraMotion4086_MaxZ',c.maxz,4)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_RowBytes',336)
 set('SourceCRandom4086_Ready',0xb5ea);set('SourceCRandom4086_Profile',1);set('SourceCRandom4086_Busy',0);set('SourceCRandom4086_SeedLo',c.seed,4);set('SourceCRandom4086_CallsLo',0,4)
 put(v,v,4);put(v+4,1,4);put(v+48,2);put(v+52,c.x,4);put(v+56,2);put(v+60,c.z,4)
 put(side,c.model);put(life+72,c.model);put(life+74,0xb4fb);put(life+8,c.callback,4)
 put(aux,c.mx,4);put(aux+4,c.mz,4);put(core+72,c.type,4)
 put(core+12,c.obstacle,4);put(core+24,c.screen,4);put(core+28,c.min,4);put(core+32,c.max,4)
 FOREIGN_SETUP
 local faults={phase={'SourceWorldTick4086_Phase',10},pending={'SourceWorldTick4086_Pending',0},time={'SourceWorldTick4086_TimeLo',49},world={'VmSourceWorld_Ready',0},slot={'SourceWorldTick4086_Slot',128},count={'VmSourceWorld_Count',129},self={'SourceSelf4086_GlobalLow',0},camera={'SourceCameraMotion4086_Ready',0},walls={'SourceEnvironment4086_WallCount',1},platform={'SourceEmptyInitEnvironment4086_Ready',0},rand={'SourceCRandom4086_Profile',2},cache={'SourceModelAnimationCopy4086_Maximum',20},view={'SourceWorldTick4086_View',80*s+2},side={'SourceWorldTick4086_Side',64*s+2}}
 if faults[c.bad]then local f=faults[c.bad];set(f[1],f[2])end
 if c.bad=='ready'then put(W,0)elseif c.bad=='generation'then put(W+12,2,4)elseif c.bad=='holes'then put(W+16,1)elseif c.bad=='scripts'then put(W+18,1)
 elseif c.bad=='callback'then put(life+8,8,4)elseif c.bad=='callback_high'then put(life+10,1)elseif c.bad=='tag'then put(v+48,1)elseif c.bad=='model'then put(life+72,(c.model+1)%16)
 elseif c.bad=='grab'then put(0x43c022+336*c.model,1)elseif c.bad=='throw'then put(0x43c028+336*c.model,1)
 elseif c.bad=='candidate'then local o=(s+1)%128;put(0x414004+o*80,1,4);put(0x40c048+o*96,8,4)
 elseif c.bad=='dead_candidate'then local o=(s+1)%128;put(0x414004+o*80,0,4);put(0x40c048+o*96,8,4)
 elseif c.bad=='other_type'then local o=(s+1)%128;put(0x414004+o*80,65536,4);put(0x40c048+o*96,0x10000,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&0x7c)~=(s['cpu.ps']&0x7c)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ticket=s['cpu.a'];decimal=s['cpu.ps']&8 end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot
 if c.fault==0 then for _,r in ipairs({{v+52,c.ex},{v+60,c.ez}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end end
 local n=0;for a,b in pairs(before)do if emu.read(a,mt)~=b then n=n+1 end end
 emu.log('FLATMOVE|'..word(INDEX)..'|'..ctx..'|'..decimal..'|'..n..'|'..word(W+2)..'|'..word(W+4)..'|'..dw(v+52)..'|'..dw(v+60)..'|'..dw(sy.SourceCRandom4086_SeedLo)..'|'..dw(sy.SourceCRandom4086_CallsLo)..'|'..word(sy.SourceWorldTick4086_Pending))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    req=derive(Source(a.source));sy=symbols(Path('src/main.sym'))
    region=next(r for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions'] if r['name']=='attack_chain_controls');work=region['address']
    base=cases()[0];rows=[]
    positions=((80.,220.),(9.,190.),(311.,240.),(10.,189.),(310.,241.),(-80.,220.))
    for slot,(x,z),(mx,mz),kind in itertools.product((0,1,127),positions,((0.,0.),(1.5,-.25),(-1.5,2.),(-20.,-50.),(20.,50.)),(1,2)):
        row=dict(base,type=kind,x=x,z=z,xd=mx,zd=mz,throw=0,grab=0,random=0,found=0)
        result=evaluate(row);seed=(1,8,17,0xffffffff)[len(rows)%4];calls_count=int(bool(mx or mz) and kind&1);newseed=(seed*214013+2531011)&0xffffffff if calls_count else seed
        import struct
        ex,ez=(struct.unpack('<f',struct.pack('<I',u))[0] for u in result[1:3])
        q=lambda n:int(n*65536)&0xffffffff
        rows.append(dict(slot=slot,x=q(x),z=q(z),mx=q(mx),mz=q(mz),ex=q(ex),ez=q(ez),result=result[0],seed=seed,nextseed=newseed,calls=calls_count,
            model=len(rows)%16,callback=3 if kind==1 else 9,type=kind,min=1,max=1,screen=1,obstacle=1,minz=q(190),maxz=q(240),camera=0,status=2,bad='',fault=0,world_state=1))
    seed=dict(rows[1],mx=98304,mz=0,x=80*65536,z=220*65536,ex=81*65536+32768,ez=220*65536,result=1,seed=1,nextseed=2745024,calls=1,type=1,callback=3)
    for bad in ('ready','generation','phase','pending','time','world','slot','count','self','camera','walls','platform','rand','cache','view','side','holes','scripts','callback','callback_high','tag','model','grab','throw','candidate'):
        rows.append(dict(seed,bad=bad,fault=1,status=4 if bad=='candidate' else 3,result=0,ex=seed['x'],ez=seed['z'],nextseed=seed['seed'],calls=0))
    for bad in ('dead_candidate','other_type'):
        rows.append(dict(seed,bad=bad))
    rows=[dict(c,world_state=s) for s in (1,2) for c in rows]
    foreign=FOREIGN_LUA[FOREIGN_LUA.index(" set('SourceForeignWork_Ready'"):FOREIGN_LUA.index(" if c.bad=='phase'")]
    lua=re.sub(r'\bW\b',str(work),LUA.replace('FOREIGN_SETUP',foreign))
    extra={k:v for k,v in sy.items() if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_')) or k=='DmaQueue'}
    lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
    reporter=Reporter('M4-FLAT-TRYMOVE',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'FlatTrymoveProbe','SourceCheckMove4086_Ready',0xb617,[],lua,reporter,
        append=ASM+emit(req,work,sy),probes=dict(RETURN='FlatTrymoveProbe_Return'),batch_size=4,frame_limit=4000,link_pcm=False)
    results=[list(map(int,l.split('FLATMOVE|',1)[1].split('|'))) for l in log.splitlines() if 'FLATMOVE|' in l]
    expected=[[i,0,8,0,c['status'],c['result'],c['ex'],c['ez'],c['nextseed'],c['calls'],0 if c['bad']=='pending' else 1] for i,c in enumerate(rows)]
    fail=[dict(index=i,input=rows[i],actual=results[i] if i<len(results) else None,expected=e) for i,e in enumerate(expected) if i>=len(results) or results[i]!=e]
    reporter.check('real source bounds, adjusted returns, signed callback identity, random stream, live type scan, CPU and actor preservation',not fail and len(results)==len(rows))
    report=dict(schema='BYOR_4086_FLAT_TRYMOVE_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',cases=len(rows),inputs=rows,results=results,failures=fail,
        rom_sha256=hashlib.sha256(raw).hexdigest(),requirements=req,borrowed_region=region,production_region_union_bound=False,
        coordinate_policy='ACCEPTED_COMPAT_Q16_16',check_move_pathblocked_and_link_owner_bound=False,native_world_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
