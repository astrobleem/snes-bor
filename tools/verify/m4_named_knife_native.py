"""Native named-knife post-step against literal pinned knife_spawn vectors.

Allocation, engine scalar acquisition and the live projectile VM API are separate
services. This test supplies their inputs and does not claim live combat.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from source_binary32_q16 import project

def q16(v):return project(struct.unpack('<I',struct.pack('<f',v))[0])&0xffffffff

LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu,ctx={},{},0
local ranges={{0x40c000,12288},{0x414000,10240},{0x416800,8192},{0x439000,10240},{0x409000,8192},{0x43eb00,4096},{0x43c000,8192},{0x433800,8192},{0x41f500,2560},{0x40b000,2560}}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do emu.write(r[1]+j,(j*17+91)&255,mt)end end
 for _,f in ipairs(c.initial)do put(f[1],f[2],f[3])end
 set('SourceNamedKnife4086_Ready',0xb611);set('SourceNamedKnife4086_State',0);set('SourceNamedKnife4086_Owner',c.owner);set('SourceNamedKnife4086_Child',c.fail==1 and 65535 or c.child)
 set('SourceNamedKnife4086_Altitude',c.altitude_q16,4);set('SourceNamedKnife4086_Map',0,4);set('SourceNamedKnife4086_EnergyCost',c.cost,4);set('SourceNamedKnife4086_NoCost',c.nocost,4);set('SourceNamedKnife4086_NoHit',c.nohit,4);set('SourceNamedKnife4086_SavedMode',c.mode,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',16);set('SourceModelEntityCopy4086_Entities',128)
 set('SourceOffscreenState4086_Ready',0xb610);set('SourceAutokillState4086_Ready',0xb60e);set('SourceMovementState4086_Ready',0xb60b);set('SourceAttackCostState4086_Ready',0xb609);set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Bytes',5376)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Models',16)
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_TimeLo',c.time&65535);set('SourceClock4086_TimeHi',c.time>>16)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Fault',0);set('SourceSelf4086_GlobalLow',(0x4000+c.owner*80));set('SourceSelf4086_GlobalHigh',0x41)
 for _,f in ipairs(c.guard)do put(sy[f[1]],f[2],f[3])end
 for _,f in ipairs(c.actor_guard)do put(f[1],f[2],f[3])end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 for j=0,7 do before[sy.SourceSelf4086_Ready+j]=emu.read(sy.SourceSelf4086_Ready+j,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then for _,f in ipairs(c.expected)do for j=0,f[3]-1 do before[f[1]+j]=(f[2]>>(8*j))&255 end end end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1;if changed<=3 then emu.log('KNIFEMISMATCH|'..word(INDEX)..'|'..a..'|'..v..'|'..emu.read(a,mt))end end end
 emu.log('KNIFEPOST|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNamedKnife4086_State))
 set('VmSourceWorld_Ready',0)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output','authority'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'and authority['source_function_unmodified']
    rows=[]
    for i,(c,v)in enumerate(zip(authority['inputs'],authority['actual'])):
        if c['remove']or c['map']:continue
        owner,child=[(0,127),(127,0),(1,95),(95,96),(96,1)][i%5]
        pc,cc=0x40c000+owner*96,0x40c000+child*96
        pr,cr=0x409000+owner*64,0x409000+child*64
        cv,cs,cl=0x414000+child*80,0x416800+child*64,0x439000+child*80
        ov=0x414000+owner*80;off=0x43d600+child*4;auto=0x43d800+child*4;body=0x433800+child*64
        initial=[[ov,ov,4],[ov+4,1,4],[cv,cv,4],[cv+4,1,4],[cs,0,2],[cl+72,0,2],[cl+74,0xb4fb,2],[cl+76,0xb508,2],
                 [pc+72,c['parent_type'],4],[pc+40,0x80000003,4],[pc+44,0x40000003,4],[pr+32,99,4],
                 [cc+72,123,4],[cv+8,2,4],[cv+12,q16(-9),4],[cs+60,q16(c['speed']),4],[cr+8,0,4],[cc+88,0,4],
                 [cs+20,0,4],[cc+52,0,4],[off,c['offscreenkill'],4],[cc+56,0,4],[auto,0,4],[cs+32,q16(3),4],[cs+48,q16(-10),4],
                 [cc+40,c['hostile'],4],[cc+44,c['candamage'],4],[body+48,0,2],
                 [cl+52,c['nomove'],4],[cl+68,int(bool(c['speed'])),4],
                 [0x40b000,struct.unpack('<I',struct.pack('<f',c['cached_speed']))[0],4]]
        for off0 in (4,8,16,20,36):initial.append([cc+off0,0,4])
        for off0 in (0,4,8,12,16):initial.append([cl+off0,0,4])
        expected=[]
        if not c['fail']:
            expected=[[cc+72,v[1],4],[cv+8,2,4],[cv+12,q16(v[3]),4],[cs+60,q16(v[4]),4],[cr+8,ov,4],[cl+16,v[6],4],[cc+88,v[7],4],
                      [cs+20,v[8],4],[cc+52,v[9],4],[off,v[10],4],[cc+56,v[11],4],[auto,v[13],4],[cs+32,q16(v[14]),4],[cs+48,q16(v[15]),4],
                      [cc+40,v[16],4],[cc+44,v[17],4],[body+48,v[23],2],[pr+32,v[24],4],[cl,6,4],[cl+8,8,4],[cl+4,0,4],[cl+12,0,4]]
            expected += [[cc+off0,v[j],4]for off0,j in zip((4,8,16,20,36),range(18,23))]
            if c['nomove']or not c['cached_speed']:expected += [[cl+68,int(bool(v[4])),4],[cl+76,0xb508,2]]
        rows.append(dict(c,authority_index=i,owner=owner,child=child,altitude_q16=q16(c['altitude']),fault=0,initial=initial,expected=expected,guard=[],actor_guard=[]))
    base=next(c for c in rows if not c['fail'])
    for field,value in [('Ready',0),('Ready',0xb612),('State',1),('State',3),('Map',1),('Map',65536),('Owner',128),('Child',128),('Child',base['owner'])]:
        rows.append(dict(base,fault=1,guard=[['SourceNamedKnife4086_'+field,value,4 if field=='Map'else 2]]))
    for field,value in [('VmSourceWorld_Ready',0),('VmSourceWorld_PoolBase',0),('VmSourceWorld_SideBase',0),('VmSourceWorld_Count',0),('VmSourceWorld_Count',129),('SourceModelEntityCopy4086_Ready',0),('SourceModelEntityCopy4086_Entities',127),('SourceModelEntityCopy4086_Models',0),('SourceModelEntityCopy4086_Models',17),('SourceLifecycle4086_Ready',0),('SourceLifecycle4086_Models',15),('SourceClock4086_Ready',0),('SourceSelf4086_Ready',0),('SourceSelf4086_Fault',1),('SourceSelf4086_GlobalLow',0),('SourceSelf4086_GlobalHigh',0),('SourceOffscreenState4086_Ready',0),('SourceAutokillState4086_Ready',0),('SourceModelAnimationCopy4086_Ready',0),('SourceModelAnimationCopy4086_Bytes',5634)]:
        rows.append(dict(base,fault=1,guard=[[field,value,2]]))
    for address,value in [(0x414004+base['owner']*80,0),(0x414002+base['child']*80,0),(0x414004+base['child']*80,2),(0x43904a+base['child']*80,0),(0x43904c+base['child']*80,0),(0x439048+base['child']*80,1),(0x416800+base['child']*64,16)]:
        rows.append(dict(base,fault=1,actor_guard=[[address,value,2]]))
    r=Reporter('M4-NAMED-KNIFE-POST',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceNamedKnife4086_Apply','SourceNamedKnife4086_Ready',0xb611,[],LUA,r,batch_size=2)
    actual=[list(map(int,l.split('KNIFEPOST|',1)[1].split('|')))for l in log.splitlines()if'KNIFEPOST|'in l]
    expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)]
    r.check('literal named knife mutations, source type/cached speed identity, signed nomove/offscreen/autokill, NULL no-op and guards; siblings/cache/idling/self/CPU preserved',actual==expected)
    (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NAMED_KNIFE_POST_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),source_numeric_policy='ACCEPTED_COMPAT_Q16_16',full_float_equivalence=False,allocation_instrumented=True,engine_scalar_inputs_instrumented=True,map_domain=[0],remove_on_attack_domain=[0],ptype_domain=[0],live_projectile_api_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
