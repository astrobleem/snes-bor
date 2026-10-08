"""Native empty-world adjust_base compared to retained independent source C."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_animation_physics_4086 import pack
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
local before,cpu,ctx={},{},0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 local s=c.slot;local view=0x414000+s*80;local side=0x416800+s*64;local core=0x40c000+s*96;local aux=0x41f500+s*20;local phy=0x42d800+s*16;local freeze=0x42e000+s*40;local life=0x439000+s*80
 set('SourceAdjustBaseEmpty4086_Ready',0xb620);set('SourceAdjustBaseEmpty4086_Status',0)
 set('SourcePhysicsState4086_Ready',0xb61c);set('SourceFreeze4086_Ready',0xb5df)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Level',1);set('VmSourceWorld_TemplateCount',1);set('VmSourceWorld_Time',48,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',2);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',11);set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_TimeLo',48,4)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceLifecycle4086_Ready',0xb4fb);set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);set('SourceSelf4086_GlobalLow',view,4)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',1)
 set('SourceEmptyInitEnvironment4086_Ready',0xb504);set('SourceEmptyInitEnvironment4086_Status',0);set('SourceEmptyInitEnvironment4086_Models',1);set('SourceEmptyInitEnvironment4086_Stage',1)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',1);set('SourceEnvironment4086_WallCount',0)
 set('SourceAnimationPhysics4086_Ready',0xb61f);set('SourceAnimationPhysics4086_Status',0);set('SourceAnimationPhysics4086_Base',0x8000);set('SourceAnimationPhysics4086_Bank',58);set('SourceAnimationPhysics4086_Bytes',TABLEBYTES);set('SourceAnimationPhysics4086_Animations',6)
 put(view,view,4);put(view+4,1,4);put(view+8,2);put(view+10,0);put(view+12,c.a,4)
 put(side,0);put(side+4,c.handle);put(side+6,0);put(side+36,98304,4);put(side+40,-49152,4);put(side+44,c.vy,4);put(side+48,c.base,4)
 put(core+36,c.noadjust,4);put(core+16,c.hole,4);put(core+4,c.wall,4);put(core+8,c.platform,4)
 put(aux+8,c.altbase,4);put(phy,1,4);put(phy+4,123,4);put(phy+8,0,4);put(phy+12,99,4)
 put(freeze,c.freeze or 0,4);put(freeze+36,c.mark or 0,4);put(life+72,0);put(life+74,0xb4fb)
 local faults={ready={'SourceAdjustBaseEmpty4086_Ready',0},status={'SourceAdjustBaseEmpty4086_Status',3},phase={'SourceWorldTick4086_Phase',10},self={'SourceSelf4086_GlobalLow',0},physics={'SourcePhysicsState4086_Ready',0},metadata={'SourceAnimationPhysics4086_Ready',0},empty={'SourceEmptyInitEnvironment4086_Ready',0},walls={'SourceEnvironment4086_WallCount',1},slot={'SourceWorldTick4086_Slot',128}}
 if faults[c.bad]then local f=faults[c.bad];set(f[1],f[2])end
 if c.bad=='landed'then put(phy+8,1,4)elseif c.bad=='frame'then put(side+6,1)elseif c.bad=='atag'then put(view+8,1)end
 before={};for _,r in ipairs({{view-16,112},{side-16,96},{core-16,128},{aux-8,28},{phy-16,48},{freeze-8,56},{life-8,96}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64
 if c.fault==0 and not((c.mark or 0)&8~=0)then for _,r in ipairs({{side+48,c.expected[1]},{side+36,c.expected[2]},{side+40,c.expected[3]}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('ADJUSTBASE|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceAdjustBaseEmpty4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    def q(bits):return round(struct.unpack('<f',struct.pack('<I',bits))[0]*65536)
    table=pack(dict(animations=[dict(handle=i+1,antigrav=0,dropframe=-1,landframe=-1,land_entity_index=-1,
        frames=[dict(movement=dict(base=base,y=y))])for i,(base,y)in enumerate((b,y)for b in (-1,0,40)for y in (0,1))]))
    rows=[]
    for i,(c,e)in enumerate(zip(authority['inputs'],authority['actual'])):
        handle=(-1,0,40).index(c['frame_base'])*2+c['frame_y']+1
        rows.append(dict(slot=(0,63,127)[i%3],handle=handle,a=round(c['a']*65536),base=round(c['base']*65536),
            altbase=round(c['altbase']*65536),vy=round(c['velocity_y']*65536),noadjust=c['noadjust'],
            hole=c['hole'],wall=c['wall'],platform=c['platform'],fault=0,expected=[q(e[0]),q(e[2]),q(e[3])]))
    seed=dict(slot=127,handle=5,a=93*65536,base=34*65536,altbase=-50*65536,vy=0,
        noadjust=0,hole=1,wall=1,platform=1,fault=0,expected=[0,98304,-49152])
    rows.append(dict(seed,freeze=1));rows.append(dict(seed,mark=8))
    for bad in ('ready','status','phase','self','physics','metadata','empty','walls','slot','landed','frame','atag'):
        rows.append(dict(seed,bad=bad,fault=1))
    rows.append(dict(seed,altbase=0x7fffffff,fault=1))
    reporter=Reporter('M4-ADJUST-BASE-EMPTY',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceAdjustBaseEmpty4086_Execute','SourceAdjustBaseEmpty4086_Ready',
        0xb620,[(58,0,table)],LUA.replace('TABLEBYTES',str(len(table))),reporter,batch_size=8)
    results=[list(map(int,line.split('ADJUSTBASE|',1)[1].split('|')))for line in log.splitlines()if 'ADJUSTBASE|'in line]
    reporter.check('native source base/velocity output agrees with independent C; faults retain actor state and CPU',
        results==[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)])
    report=dict(schema='BYOR_4086_EMPTY_WORLD_ADJUST_BASE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
        cases=len(rows),independent_c_cases=len(authority['inputs']),inputs=rows,results=results,
        authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
        compiled_frame_metadata_lookup_executed=True,numeric_policy='ACCEPTED_COMPAT_Q16_16; signed zero collapses to zero',
        empty_geometry_compiler_contract_required=True,native_active_gravity_or_landing_bound=False,
        motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
