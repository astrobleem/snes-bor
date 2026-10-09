"""Canonical fall marker, typed input binding and sibling preservation."""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_player_fall_native import emit
from source_player_run_4086 import KEYS
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

W,H,O=0x7fa400,0x7fa000,0x7fa418
ASM="""
FallProbe:
.a16
.i16
 php
 sed
 jsl PlayerFall_Execute
FallProbe_Return:
.a16
.i16
 nop
 bcs FallProbe_Bad
 plp
 clc
 rtl
FallProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
"""
LUA=r"""
local mt=emu.memType.snesMemory;local before={};local expected={};local failures=0;local cpu={};local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];failures=0;before={};expected={}
 for j=0,23 do put(W+j,0,1)end;put(W,0xb689);put(W+4,c.slot);put(W+8,c.autoland,4);put(O,0xb674)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128);put(sy.SourcePhysicsState4086_Ready,0xb61c)
 local view=0x414000+c.slot*80;put(view,view,4);put(view+40,1,4);put(view+44,c.port,4)
 for j=0,1023 do put(H+j,0x55,1)end;put(H+256*c.port+216,c.keys,4)
 for j=0,2047 do put(0x42d800+j,0xa5,1)end;put(0x42d80c+16*c.slot,c.marker,4)
 if c.bad=='ready'then put(W,0)elseif c.bad=='input'then put(O,0)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='count0'then put(sy.VmSourceWorld_Count,0)elseif c.bad=='count129'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='slot'then put(W+4,128)elseif c.bad=='physics'then put(sy.SourcePhysicsState4086_Ready,0)
 elseif c.bad=='token_low'then put(view,0x4001)elseif c.bad=='token_high'then put(view+2,0x42)
 elseif c.bad=='port_tag'then put(view+40,2)elseif c.bad=='port_reserved'then put(view+42,1)
 elseif c.bad=='port_high'then put(view+46,1)elseif c.bad=='port'then put(view+44,4)end
 for _,r in ipairs({{0x414000,10240},{0x42d800,2048},{H,1024}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 if c.bad==''and c.autoland~=2 and c.keys&MASK==MASK then for j=0,3 do expected[0x42d80c+16*c.slot+j]=((-2)>>(8*j))&255 end end
 put(EXPECTFAULT,c.bad~=''and 1 or 0)
 local st=emu.getState();start=st.masterClock;cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then failures=failures+1 end end,emu.callbackType.exec,RETURNPOINT,RETURNPOINT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();for _,k in ipairs({'a','x','y','d','dbr','sp'})do if st['cpu.'..k]~=cpu[k]then failures=failures+1 end end
 if(st['cpu.ps']&254)~=(cpu.ps&254)then failures=failures+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];for a,v in pairs(before)do if emu.read(a,mt)~=(expected[a]or v)then failures=failures+1 end end
 if word(W+2)~=(c.bad==''and 2 or 4)then failures=failures+1 end
 emu.log('FALLBOUND|'..word(INDEX)..'|'..failures..'|'..word(W+2)..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();mask=KEYS['moveup']|KEYS['jump'];rows=[]
    for slot in range(128):
        for autoland in (0,2):
            for keys in (0,KEYS['moveup'],KEYS['jump'],mask,0xffffffff):
                rows.append(dict(slot=slot,port=slot%4,autoland=autoland,keys=keys,marker=(-2147483648,0,7,2147483647)[slot%4],bad=''))
    for autoland in (-2147483648,-1,1,65538):rows.append(dict(rows[-1],autoland=autoland))
    guards=('ready','input','world','pool','count0','count129','slot','physics','token_low','token_high','port_tag','port_reserved','port_high','port')
    rows += [dict(rows[0],bad=g)for g in guards]
    sy=symbols(Path('src/main.sym'));folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    (folder/'report.json').write_text(json.dumps(dict(status='RUNNING'))+'\n');reporter=Reporter('M4-PLAYER-FALL',kind='GATE')
    lua=LUA
    for n,v in dict(W=W,H=H,O=O,MASK=mask).items():lua=re.sub(r'\b'+n+r'\b',str(v),lua)
    raw,log=run_fixture(a.rom,folder,rows,'FallProbe','SourcePhysicsState4086_Ready',0xb61c,[],lua,reporter,
        append=ASM+emit(W,H,O,0xb674,sy),probes=dict(RETURNPOINT='FallProbe_Return'),batch_size=8,frame_limit=1500,link_pcm=False)
    results=[list(map(int,line.split('FALLBOUND|',1)[1].split('|')))for line in log.splitlines()if 'FALLBOUND|'in line]
    errors=[r for r in results if r[1]]
    reporter.check('canonical marker writes only its selected physics field, retains sibling/input/view bytes and CPU, guards invalid bindings',len(results)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_PLAYER_FALL_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guards=len(guards),observed=len(results),errors=errors[:8],
        rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max((r[-1]for r in results),default=0),autoland_context_instrumented=True,
        native_marker_bound=True,active_gravity_or_landing_bound=False,full_player_think_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish();assert report['status']=='PASS'


if __name__=='__main__':main()
