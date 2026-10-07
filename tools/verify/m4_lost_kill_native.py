"""Execute lost-entity kill requests through real no-event native retirement.

Full relation/role/variable expectations come from pinned kill authority.
Changing its original caller self to the victim changes only the restored self
pointer: the literal source ends with self = tempent, even for a retired row.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from m4_retirement_native import packet
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''
LostKillFixture_Run:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl LOSTBEGIN
 bcs LostKillFixture_Bad
LostKillFixture_AfterBegin:
.a16
.i16
 nop
 jsl LOSTKILL
 bcs LostKillFixture_Bad
 ply
 plx
 plp
 clc
 rtl
LostKillFixture_Bad:
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
local ranges={{0x414000,10240},{0x409000,8192},{0x40c000,12288},{0x43eb00,4096},{0x43fd80,32},{0x418800,24576},{0x7ffe38,4},{0x416800,8192},{0x439000,10240},{0x42e000,5120}}
local before={};local cpu={};local ctx=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0,mt)end end
 for _,p in ipairs(c.before)do for i,v in ipairs(p.data)do emu.write(p.at+i-1,v,mt)end end
 set('SourceLost4086_Ready',0xb5e0);set('SourceLost4086_Status',0);set('SourceLost4086_OffscreenKill',0,4);set('SourceLost4086_DefaultOffscreenKill',3000,4);set('SourceLost4086_Direction',2,4);set('SourceLost4086_HRes',320);set('SourceLost4086_VRes',240)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',c.count);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Level',1);set('VmSourceWorld_Time',48,4);set('VmSourceWorld_AdvanceX',0,4);set('VmSourceWorld_AdvanceY',0,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',2);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_TimeLo',48,4)
 set('SourceFreeze4086_Ready',0xb5df);put(LIFEREADY,0xb4fb)
 set('SourceRetirement4086_Ready',0xb4f8);set('SourceRetirement4086_Status',0);set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',c.count);set('SourceModelEntityCopy4086_Models',1);set('SourceIdle4086_Ready',0xb4f3)
 set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 put(0x416810+c.slot*64,c.path==3 and 0xffffffff or 0x7fffffff,4)
 if c.bad=='retirement'then set('SourceRetirement4086_Ready',0)
 elseif c.bad=='self'then set('SourceSelf4086_GlobalLow',0);set('SourceSelf4086_GlobalHigh',0)
 elseif c.bad=='onkill'then put(0x409034+c.slot*64,1,4)
 elseif c.bad=='clear_entry'then put(0x409030+c.slot*64,1,4)
 elseif c.bad=='player_request'then put(0x40c048+c.slot*96,1,4)
 elseif c.bad=='damage_request'then put(0x439004+c.slot*80,1,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.bad=='slot_changed'then set('SourceWorldTick4086_Slot',(c.slot+1)%128)
 elseif c.bad=='time_changed'then set('VmSourceWorld_Time',49,4)end
end,emu.callbackType.exec,BEGINAFTER,BEGINAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then for _,p in ipairs(c.after)do for i,v in ipairs(p.data)do before[p.at+i-1]=v end end end
 local changed=0;for address,value in pairs(before)do if emu.read(address,mt)~=value then changed=changed+1 end end
 emu.log('LOSTKILL|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceLost4086_Status)..'|'..word(sy.SourceRetirement4086_Status)..'|'..word(sy.SourceWorldTick4086_Pending)..'|'..dw(sy.VmSourceWorld_Time))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def prepared(c, state, mapping, count, path):
    packets=packet(c,state,mapping,count);slot=mapping[1];target=0x414000+slot*80
    for row in packets:
        if row['at']==0x7ffe38:row['data']=list(struct.pack('<I',target))
        if row['at']==target:
            data=bytearray(row['data']);x=-4000 if path==0 else 80;y=-300 if path==1 else -600 if path==2 else 0
            for at,value in ((8,2),(12,y*65536),(48,2),(52,x*65536),(56,2),(60,220*65536)):struct.pack_into('<I',data,at,value&0xffffffff)
            row['data']=list(data)
    return packets


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'and authority['cases']==144;rows=[]
    for r in authority['results']:
        c=r['case']
        if c['mode']!=0 or c['summon'] not in (0,1) or c['sub']:continue
        for count,mapping in ((6,list(range(6))),(128,[0,127,1,2,3,4]),(128,list(range(122,128)))):
            for path in range(4):rows.append(dict(before=prepared(c,None,mapping,count,path),after=prepared(c,r['actual']['state'],mapping,count,path),count=count,slot=mapping[1],path=path,fault=0,bad=''))
    base=rows[0]
    for bad in ('retirement','self','onkill','clear_entry','player_request','slot_changed','time_changed'):
        rows.append(dict(base,fault=1,bad=bad))
    rows.append(dict(next(c for c in rows if c['path']==3),fault=1,bad='damage_request'))
    sy=symbols(Path('src/main.sym'));asm=ASM.replace('LOSTBEGIN',str(sy['SourceLost4086_Begin'])).replace('LOSTKILL',str(sy['SourceLost4086_ApplyNoEventKill']))
    lua=LUA.replace('LIFEREADY',str(sy['SourceLifecycle4086_Ready']))+"emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,CAPTUREENTRY,CAPTUREENTRY,emu.cpuType.snes,mt)\n"
    r=Reporter('M4-LOST-KILL',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'LostKillFixture_Run','SourceLost4086_Ready',0xb5e0,[],lua,r,append=asm,probes=dict(CAPTUREENTRY='LostKillFixture_Run',BEGINAFTER='LostKillFixture_AfterBegin'),batch_size=2)
    results=[list(map(int,line.split('LOSTKILL|',1)[1].split('|')))for line in log.splitlines()if 'LOSTKILL|'in line];failures=[]
    for i,(c,v)in enumerate(zip(rows,results)):
        if v[:4]!=[i,0,0,3 if c['fault']else 2]or(not c['fault']and v[4:]!=[2,1,48]):failures.append(dict(index=i,input={k:x for k,x in c.items()if k not in ('before','after')},result=v))
    r.check('actual scrolling/pit/lifespan kills match pinned retirement state, retain dead self pointer, and reject unbound requests before mutation',len(results)==len(rows)and not failures)
    report=dict(schema='BYOR_4086_LOST_KILL_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=[{k:v for k,v in r.items()if k not in ('before','after')}for r in rows],results=results,failures=failures[:20],rom_sha256=hashlib.sha256(rom).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),authority_functions_sha256=authority['functions_sha256'],caller_self_policy='Pinned kill tempent restores the current victim pointer even after retirement',no_event_retirement_bound=True,world_tick_acknowledged=False,player_die_bound=False,damage_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
