"""Music acknowledgement control only; does not claim physical audio playback."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local before={};local cpu={};local ctx=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 put(sy.SourceSmartSpawn4086_Ready,c.ready);put(sy.SourceSmartSpawn4086_Status,c.status);put(sy.SourceSmartSpawn4086_BossMusic,c.music)
 before={};for i=0,8191 do before[i]=emu.read(0x433800+i,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for i,v in pairs(before)do if emu.read(0x433800+i,mt)~=v then n=n+1 end end
 emu.log('SMARTACK|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceSmartSpawn4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    rows=[dict(ready=ready,status=status,music=music,fault=int((ready,status,music)!=(0xb5d4,1,1)))for ready,status,music in itertools.product((0,0xb5d4),(0,1,2,3),(0,1,2))]
    sy=symbols(Path('src/main.sym'));entry=sy['SourceSmartSpawn4086_AckMusic'];lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-SMARTSPAWN-MUSIC-ACK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceSmartSpawn4086_AckMusic','SourceSmartSpawn4086_Ready',0xb5d4,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('SMARTACK|',1)[1].split('|')))for line in log.splitlines()if 'SMARTACK|'in line]
    r.check('only pending admitted music may be acknowledged; body bytes and CPU context preserved',len(results)==len(rows)and all(v==[i,0,0,3 if c['fault']else 2]for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_SMARTSPAWN_MUSIC_ACK_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),actual_music_service_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
