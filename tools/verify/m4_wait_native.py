"""Native scroller WAIT release against literal C with readonly pool observers."""
import argparse
import hashlib
import json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local cpu={};local before={};local ctx=0;local returned=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_Time',c.time,4)
 set('SourceWait4086_Ready',0xb5d9);set('SourceWait4086_Status',0);set('SourceWait4086_NoReset',c.noreset,4);set('SourceWait4086_SetTime',c.settime,4);set('SourceWait4086_TimeLeft',c.timeleft,4)
 set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_State',2)
 set('SourceStageProducer4086_Ready',0xb5d6);set('SourceStageProducer4086_State',4);set('SourceStageProducer4086_Waiting',c.waiting);set('SourceStageProducer4086_GoTime',c.go_time,4)
 for i=0,127 do put(0x414004+i*80,i==c.slot and c.enemies or 0,4);put(0x40c048+i*96,2,4)end
 if c.bad=='ready'then set('SourceWait4086_Ready',0)
 elseif c.bad=='prefix'then set('SourceScrollerPrefix4086_Ready',0)
 elseif c.bad=='prefix_state'then set('SourceScrollerPrefix4086_State',4)
 elseif c.bad=='producer'then set('SourceStageProducer4086_Ready',0)
 elseif c.bad=='producer_state'then set('SourceStageProducer4086_State',1)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)end
 before={};for _,r in ipairs({{0x414000,10240},{0x40c000,12288}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();returned=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('SOURCEWAIT|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceWait4086_Status)..'|'..word(sy.SourceStageProducer4086_Waiting)..'|'..dw(sy.SourceWait4086_TimeLeft)..'|'..dw(sy.SourceStageProducer4086_GoTime)..'|'..returned..'|'..word(sy.SourceStageProducer4086_State))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';rows=[]
    for i,(c,v)in enumerate(zip(authority['inputs'],authority['expected'])):
        rows.append(dict(c,slot=127 if i%2 else 0,bad='',fault=0,expected=[v[0],v[1]&0xffffffff,v[2],v[3]]))
    base=dict(rows[0],waiting=1,enemies=0,noreset=0,settime=100)
    for bad in ('ready','prefix','prefix_state','producer','producer_state','world','count','pool'):rows.append(dict(base,bad=bad,fault=1))
    for t in (-5368710,5368710,-2147483648,2147483647):rows.append(dict(base,settime=t,fault=1))
    # Overflowing unused settime must not fault when source does not reset.
    for t in (-2147483648,2147483647):rows.append(dict(base,settime=t,noreset=2,expected=[0,base['timeleft']&0xffffffff,(base['time']+600)&0xffffffff,1]))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceWait4086_Release'];lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-SOURCE-WAIT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceWait4086_Release','SourceWait4086_Ready',0xb5d9,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('SOURCEWAIT|',1)[1].split('|')))for line in log.splitlines()if 'SOURCEWAIT|'in line]
    r.check('literal C WAIT release, signed timer/noreset, unsigned deadline, readonly pool/CPU and explicit overflow guards',len(results)==len(rows)and all(v[:3]==[i,0,0]and(v[3]==3 and v[4:7]==[c['waiting'],c['timeleft']&0xffffffff,c['go_time']]and v[8]==3 if c['fault']else v[3]==2 and v[4:8]==c['expected']and v[8]==4)for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_WAIT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),camera_bound=False,combat_enemy_retirement_instrumented=True,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
