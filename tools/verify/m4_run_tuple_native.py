"""Real model-data copy, cached inheritance and immutable RUN snapshot read."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_model_core_4086 import derive as cores, CACHED_FIELDS, FLOAT_FIELDS
from source_run_tuple_profile import derive, pack
from source_run_tuple_native import emit
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

WORK=0x7fa000
HANDLES=0x7fa100
ASM='''
TupleProbe:
.a16
.i16
 php
 sed
 jsl SourceRunTuple_Copy
TupleProbe_Copied:
 bcs TupleProbe_Bad
TupleProbe_Inherit:
 nop
 jsl INHERIT
TupleProbe_Inherited:
 bcs TupleProbe_Bad
TupleProbe_BeforeRead:
 nop
 jsl SourceRunTuple_Read
TupleProbe_Read:
 bcs TupleProbe_Bad
 plp
 clc
 rtl
TupleProbe_Bad:
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local cpu,baseline,snapshot,start,ctx={},{},{},0,0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function set(k,v)put(sy[k],v)end
local function blob(a,hex)for i=1,#hex,2 do emu.write(a+(i-1)//2,tonumber(hex:sub(i,i+1),16),mt)end end
local function snap()local t={};for _,r in ipairs({{0x414000,10240},{0x416800,8192},{0x40c000,12288}})do for i=0,r[2]-1 do t[r[1]+i]=emu.read(r[1]+i,mt)end end;return t end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs({{WORK,64},{HANDLES,256},{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x40ba00,512}})do for i=0,r[2]-1 do emu.write(r[1]+i,0,mt)end end
 for j=0,255 do emu.write(HANDLES+j,0xa5,mt)end
 blob(0x40b000,CACHE)
 for i=0,15 do put(0x40ba00+i*32,0xffff)end
 local v=0x414000+c.slot*80
 put(v,v,4);put(v+4,1);put(v+32,1);put(v+36,100,4);put(v+64,1);put(v+68,150,4)
 put(WORK,0xb678);put(WORK+4,c.slot);put(WORK+6,c.model)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',16)
 set('SourceModelCachedCopy4086_Ready',0xb4ee);set('SourceModelCachedCopy4086_Models',16)
 set('SourceModelCachedCopy4086_Flags',0);set('SourceModelCachedCopy4086_Status',0)
 for _,name in ipairs(OPTIONAL)do set(name,0)end
 if c.bad=='ready'then put(WORK,0)
 elseif c.bad=='busy'then put(WORK+2,1)
 elseif c.bad=='slot'then put(WORK+4,128)
 elseif c.bad=='model'then put(WORK+6,16)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='owner'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='count'then set('SourceModelEntityCopy4086_Models',15)
 elseif c.bad=='health'then put(v+32,2)
 elseif c.bad=='unknown'then put(0x40b000+c.model*160+4,0x3fc00000,4)
 end
 baseline=snap();snapshot={};local s=emu.getState();start=s.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 set('SourceModelCachedCopy4086_Old',3);set('SourceModelCachedCopy4086_New',c.model)
end,emu.callbackType.exec,INHERITPOINT,INHERITPOINT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()snapshot=snap()end,emu.callbackType.exec,BEFOREREAD,BEFOREREAD,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local errors=0
 local handle=c.fault~=0 and 0xa5a5 or c.handle
 for i=0,127 do local wanted=i==c.slot and handle or 0xa5a5;if word(HANDLES+i*2)~=wanted then errors=errors+1 end end
 if c.fault==0 then
  for i=1,#c.inherited,2 do if emu.read(0x40b000+c.model*160+4+(i-1)//2,mt)~=tonumber(c.inherited:sub(i,i+1),16)then errors=errors+1 end end
  for i=1,#c.raw,2 do if emu.read(WORK+20+(i-1)//2,mt)~=tonumber(c.raw:sub(i,i+1),16)then errors=errors+1 end end
  for a,v in pairs(snapshot)do if emu.read(a,mt)~=v then errors=errors+1 end end
  if word(sy.SourceModelEntityCopy4086_Status)~=1 then errors=errors+1 end
 else for a,v in pairs(baseline)do if emu.read(a,mt)~=v then errors=errors+1 end end end
 emu.log('RUNTUPLE|'..word(INDEX)..'|'..word(WORK+2)..'|'..errors..'|'..ctx..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('TUPLEFAULT|'..word(INDEX)..'|'..word(WORK)..'|'..word(WORK+4)..'|'..word(WORK+6)..'|'..word(sy.SourceModelEntityCopy4086_Status)..'|'..word(sy.SourceModelCachedCopy4086_Status))end,emu.callbackType.exec,FAULT,FAULT,emu.cpuType.snes,mt)
for _,a in ipairs({COPYRETURN,INHERITRETURN})do emu.addMemoryCallback(function()emu.log('TUPLESTEP|'..word(INDEX)..'|'..a..'|'..word(WORK+2)..'|'..word(sy.SourceModelEntityCopy4086_Status)..'|'..word(sy.SourceModelCachedCopy4086_Status)..'|'..word(sy.SourceModelCachedCopy4086_Ready)..'|'..word(sy.SourceModelCachedCopy4086_Models)..'|'..word(sy.SourceModelCachedCopy4086_Old)..'|'..word(sy.SourceModelCachedCopy4086_New))end,emu.callbackType.exec,a,a,emu.cpuType.snes,mt)end
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();source=Source(a.source);r=derive(source);core=cores(source)
    cache=b''.join(b''.join(struct.pack('<f'if f in FLOAT_FIELDS else'<i',m['fields'][f])for f in CACHED_FIELDS)+struct.pack('<i',m['fields']['type'])for m in core['models'])
    inherited=r['tuples'][r['models'][3]['initial_tuple']-1]
    rows=[dict(model=m['id'],slot=slot,handle=m['initial_tuple'],raw=r['tuples'][m['initial_tuple']-1],inherited=inherited,bad='',fault=0)
          for m in r['models']for slot in (0,1,7,31,95,96,126,127)]
    for bad in ('ready','busy','slot','model','world','owner','count','health','unknown'):rows.append(dict(rows[0],bad=bad,fault=1))
    sy=symbols(Path('src/main.sym'))
    # Disable optional foreign field owners in this isolated prefix fixture.
    names=('SourceModelAttackPolicy4086_Ready','SourceAttackTiming4086_Ready','SourceAttackBody4086_Ready',
           'SourceLifecycle4086_Ready','SourceOffscreenState4086_Ready','SourceAutokillState4086_Ready',
           'SourceMovementState4086_Ready','SourceAttackCostState4086_Ready','SourceDeathFields4086_Ready')
    names=[n for n in names if n in sy]
    extra={k:sy[k]for k in names}
    extra.update({k:v for k,v in sy.items()if k.startswith('SourceModelCachedCopy4086_')})
    lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+LUA
    import re
    for k,v in dict(WORK=WORK,HANDLES=HANDLES,CACHE=luav(cache.hex()),OPTIONAL=luav(names)).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    asm=ASM.replace('INHERIT',str(sy['SourceModelCachedCopy4086_Apply']))+emit(WORK,HANDLES,r,sy)
    reporter=Reporter('M4-RUN-TUPLE-SNAPSHOT',kind='GATE');folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw,log=run_fixture(a.rom,folder,rows,'TupleProbe','SourceModelEntityCopy4086_Ready',0xb4eb,[],lua,reporter,
                        append=asm,probes=dict(INHERITPOINT='TupleProbe_Inherit',BEFOREREAD='TupleProbe_BeforeRead',FAULT='SourceRunTuple_Fault',COPYRETURN='TupleProbe_Copied',INHERITRETURN='TupleProbe_Inherited'),
                        batch_size=2,frame_limit=600,link_pcm=False)
    actual=[list(map(int,line.split('RUNTUPLE|')[1].split('|')))for line in log.splitlines()if 'RUNTUPLE|'in line]
    errors=[dict(case=i,input=rows[i],actual=v)for i,v in enumerate(actual)if v[:4]!=[i,3 if rows[i]['fault']else 2,0,0]]
    reporter.check('real model-data copy, actual cached inheritance, stable exact RUN snapshot and sibling/CPU/guard retention',len(actual)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_RUN_TUPLE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),guards=9,errors=errors[:10],rom_sha256=hashlib.sha256(raw).hexdigest(),
                table_sha256=hashlib.sha256(pack(r)).hexdigest(),tuple_count=r['tuple_count'],entity_handle_bytes=256,
                actual_model_entity_copy_executed=True,actual_cached_inheritance_executed=True,source_float_bits_preserved=True,
                production_model_copy_binding=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()


if __name__=='__main__':main()
