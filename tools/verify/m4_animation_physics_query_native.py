"""Native lookup of all authored animation physics rows, with guarded failure."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_animation_physics_4086 import unpack
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v)put(sy['SourceAnimationPhysics4086_'..k],v)end
local cpu={}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('Ready',0xb61f);set('Status',0);set('Base',c.base or 0x8000);set('Bank',c.bank or 58)
 set('Bytes',TABLEBYTES);set('Animations',ANIMATIONCOUNT);set('Handle',c.handle);set('Frame',c.frame)
 for a=0x41ff10,0x41ff29 do put(a,165,1)end
 for _,a in ipairs({0x41fef0,0x41ff50})do for i=0,15 do put(a+i,90,1)end end
 if c.bad then set(c.bad,c.value)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps','a'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
local ctx=0
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','a'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local mismatches=0
 for i=1,6 do local expected=c.fault==1 and 0xa5a5a5a5 or(c.expected[i]&0xffffffff);if dw(0x41ff10+(i-1)*4)~=expected then mismatches=mismatches+1 end end
 if word(0x41ff28)~=(c.fault==1 and 0xa5a5 or c.count)then mismatches=mismatches+1 end
 for _,a in ipairs({0x41fef0,0x41ff50})do for i=0,15 do if emu.read(a+i,mt)~=90 then mismatches=mismatches+1 end end end
 emu.log('ANIMPHYS|'..word(INDEX)..'|'..ctx..'|'..mismatches..'|'..word(0x41ff02))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--table',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    data=a.table.read_bytes();animations=unpack(data);rows=[]
    for animation in animations:
        for frame,f in enumerate(animation['frames']):
            rows.append(dict(handle=animation['handle'],frame=frame,count=len(animation['frames']),fault=0,
                expected=[animation['antigrav'],animation['dropframe'],animation['landframe'],
                          animation['land_entity_index'],f['base'],f['y']]))
    last=dict(rows[-1]);last.update(base=65536-len(data),bank=59);rows.append(last)
    for name,value in (('Ready',0),('Ready',0xb620),('Status',2),('Status',3),('Bank',64),
        ('Bank',126),('Bank',256),('Bytes',15),('Bytes',32769),('Bytes',len(data)-2),
        ('Animations',0),('Animations',129),('Animations',len(animations)-1),
        ('Handle',0),('Handle',len(animations)+1),('Frame',len(animations[-1]['frames'])),
        ('Base',0x7fff),('Base',0xfff1),('Base',0xff00)):
        r=dict(rows[-1]);r.update(base=0x8000,bank=58,bad=name,value=value,fault=1);rows.append(r)
    for base in (0xa200,0xc400):
        r=dict(rows[0]);r.update(base=base,fault=1);rows.append(r)
    bad_header=bytearray(data);bad_header[0]=0
    bad_antigrav=bytearray(data);struct.pack_into('<H',bad_antigrav,16+6,1)
    lua=LUA.replace('TABLEBYTES',str(len(data))).replace('ANIMATIONCOUNT',str(len(animations)))
    reporter=Reporter('M4-ANIMATION-PHYSICS-QUERY',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceAnimationPhysics4086_Query',
        'SourceAnimationPhysics4086_Ready',0xb61f,
        [(58,0,data),(58,0x2200,bad_header),(58,0x4400,bad_antigrav),(59,32768-len(data),data)],
        lua,reporter,batch_size=8)
    results=[list(map(int,line.split('ANIMPHYS|',1)[1].split('|')))for line in log.splitlines()if 'ANIMPHYS|'in line]
    reporter.check('all authored frame lookups exact, malformed inputs retain unpublished result, fences and CPU preserved',
        results==[[i,0,0,3 if r['fault'] else 2]for i,r in enumerate(rows)])
    report=dict(schema='BYOR_4086_ANIMATION_PHYSICS_QUERY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
        cases=len(rows),authored_frame_rows=len(rows)-22,inputs=rows,results=results,
        compiled_table_sha256=hashlib.sha256(data).hexdigest(),compiled_bytes=len(data),
        rom_sha256=hashlib.sha256(raw).hexdigest(),scratch_domain='41FF00..41FF4F',
        no_actor_state_mutation=True,native_active_gravity_or_landing_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
