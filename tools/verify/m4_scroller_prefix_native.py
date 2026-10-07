"""Native unsigned time/freeze prefix against the pinned C vectors."""
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
local cpu={};local ctx=0;local returned=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Level',1);set('VmSourceWorld_Time',c.time,4)
 set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_State',0);set('SourceScrollerPrefix4086_AdvanceTime',c.advancetime,4);set('SourceScrollerPrefix4086_FreezeAll',c.freezeall,4);set('SourceScrollerPrefix4086_Completed',c.completed,4);set('SourceScrollerPrefix4086_ScrollDX',123,4);set('SourceScrollerPrefix4086_ScrollDY',-77,4)
 set('SourceStageProducer4086_Ready',0xb5d6);set('SourceStageProducer4086_State',c.producer)
 if c.bad=='ready'then set('SourceScrollerPrefix4086_Ready',0)
 elseif c.bad=='producer_ready'then set('SourceStageProducer4086_Ready',0)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='level'then set('VmSourceWorld_Level',0)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();returned=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('SCROLLERPREFIX|'..word(INDEX)..'|'..ctx..'|'..word(sy.SourceScrollerPrefix4086_State)..'|'..dw(sy.SourceScrollerPrefix4086_AdvanceTime)..'|'..dw(sy.SourceScrollerPrefix4086_ScrollDX)..'|'..dw(sy.SourceScrollerPrefix4086_ScrollDY)..'|'..word(sy.SourceStageProducer4086_State)..'|'..word(sy.SourceStageProducer4086_Completed)..'|'..returned)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';rows=[]
    for i,(c,v)in enumerate(zip(authority['inputs'],authority['expected'])):
        rows.append(dict(c,producer=4 if i%2 else 0,bad='',fault=0,expected=[2 if v[0]else 4,v[1],0,0,0 if v[0]else 4,int(bool(c['completed'])),v[0]]))
    for bad in ('ready','producer_ready','world','level'):
        rows.append(dict(rows[0],bad=bad,fault=1))
    for producer in (1,2,3,65535):rows.append(dict(rows[0],producer=producer,fault=1))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceScrollerPrefix4086_Begin'];lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-SCROLLER-PREFIX',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceScrollerPrefix4086_Begin','SourceScrollerPrefix4086_Ready',0xb5d7,[],lua,r)
    results=[list(map(int,line.split('SCROLLERPREFIX|',1)[1].split('|')))for line in log.splitlines()if 'SCROLLERPREFIX|'in line]
    r.check('C-paired unsigned time, full-width freeze/completed truth, zero scroll delta and prior-queue/CPU guards',len(results)==len(rows)and all(v[:2]==[i,0]and(v[2]==3 and v[6]==3 if c['fault']else v[2:]==c['expected'])for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_SCROLLER_PREFIX_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),camera_motion_completion_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
