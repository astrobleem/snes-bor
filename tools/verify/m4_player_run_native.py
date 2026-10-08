"""Bounded native source running predicate, every directional combination."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_player_run_authority import cases
from source_player_run_4086 import retain
from source_player_run_native import emit
from _source_leaf_fixture import run_fixture
from _harness import Reporter

WORK=0x7fa000
ASM='''
RunProbe:
.a16
.i16
 php
 sed
 jsl SourcePlayerRun_Execute
RunProbe_After:
 bcs RunProbe_Bad
 plp
 clc
 rtl
RunProbe_Bad:
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local cpu,before,start,ctx={},{},0,0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function long(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for j=0,47 do emu.write(WORK+j,0xa5,mt)end
 put(WORK,c.bad=='ready'and 0 or 0xb677);put(WORK+2,c.bad=='busy'and 1 or 0)
 for i,v in ipairs({c.running,c.old,c.flags,c.keys,c.vx,c.vz})do put(WORK+4+(i-1)*4,v,4)end
 before={};for j=0,47 do before[j]=emu.read(WORK+j,mt)end
 local s=emu.getState();start=s.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then emu.log('RUNDECIMALFAIL|'..word(INDEX))end end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local n=0
 for j=0,47 do if j<2 or(j>=4 and j<28)or(j>=44)or c.fault~=0 and j>=4 then if emu.read(WORK+j,mt)~=before[j]then n=n+1 end end end
 emu.log('RUNPOLICY|'..word(INDEX)..'|'..word(WORK+2)..'|'..long(WORK+28)..'|'..n..'|'..ctx..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();rows=[];seen=set()
    for i,c in enumerate(cases()):
        # Full key/sign/old-running/rule coverage with representative signed
        # running values, rather than repeating the entire literal C product.
        key=(c['flags'],c['old'],c['keys'],c['vx'],c['vz'],bool(c['running']))
        if key in seen:continue
        seen.add(key)
        c=dict(c,expected=retain(c['running'],c['old'],c['flags'],c['keys'],c['vx'],c['vz'])&0xffffffff,
               vx=int(c['vx']*65536)&0xffffffff,vz=int(c['vz']*65536)&0xffffffff,bad='',fault=0)
        if c['running'] and i%3:c['running']=(-1,65536)[i%2];c['expected']=c['running']&0xffffffff if c['expected'] else 0
        rows.append(c)
    for bad in ('ready','busy'):rows.append(dict(rows[1],bad=bad,fault=1,expected=0xa5a5a5a5))
    reporter=Reporter('M4-PLAYER-RUN-POLICY',kind='GATE');folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    lua=LUA.replace('WORK',str(WORK))
    raw,log=run_fixture(a.rom,folder,rows,'RunProbe','SourceAnimationInit4086_Ready',0xb4ec,[],lua,reporter,
                        append=ASM+emit(WORK),probes=dict(RETURN='RunProbe_After'),batch_size=64,frame_limit=2000,link_pcm=False)
    actual=[list(map(int,line.split('RUNPOLICY|')[1].split('|')))for line in log.splitlines()if 'RUNPOLICY|'in line]
    errors=[dict(case=i,input=rows[i],actual=v)for i,v in enumerate(actual)
            if v[:5]!=[i,3 if rows[i]['fault']else 2,rows[i]['expected'],0,0]]
    ok=len(actual)==len(rows)and not errors and 'RUNDECIMALFAIL|'not in log
    reporter.check('running predicate, operand retention, binary arithmetic/decimal flag, CPU/stack and admission guards',ok)
    report=dict(schema='BYOR_4086_PLAYER_RUN_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),errors=errors[:10],rom_sha256=hashlib.sha256(raw).hexdigest(),
                peak_master_clocks=max(v[5]for v in actual),decimal_entry_preserved=True,
                canonical_actor_storage_bound=False,velocity_abi='finite Q16; sign/zero queries only',
                full_player_think_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()


if __name__=='__main__':main()
