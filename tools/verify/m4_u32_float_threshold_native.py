"""Bounded native threshold primitive, CPU/decimal entry and input retention."""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_u32_float_threshold_native import emit
from source_u32_float_threshold_4086 import compare
from source_u32_float_threshold_authority import cases
from _source_leaf_fixture import run_fixture
from _harness import Reporter
W=0x7fa000
ASM="""
ThresholdProbe:
.a16
.i16
 php
 sed
 jsl U32FloatThreshold_Execute
ThresholdProbe_Return:
.a16
.i16
 nop
 bcs ThresholdProbe_Bad
 plp
 clc
 rtl
ThresholdProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
"""
LUA=r"""
local mt=emu.memType.snesMemory;local cpu={};local before={};local failed=0;local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];failed=0;before={};for j=0,63 do put(W+j,0,1)end
 put(W,c.bad=='ready'and 0 or 0xb68e);put(W+4,c.stall,4);put(W+8,c.time,4);put(W+12,c.delay,4);put(W+16,0x55aa)
 for j=0,15 do if j<2 or j>3 then before[W+j]=emu.read(W+j,mt)end end
 put(EXPECTFAULT,c.fault);local st=emu.getState();start=st.masterClock;cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then failed=failed+1 end end,emu.callbackType.exec,RETURNPOINT,RETURNPOINT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();for _,k in ipairs({'a','x','y','d','dbr','sp'})do if st['cpu.'..k]~=cpu[k]then failed=failed+1 end end;if(st['cpu.ps']&254)~=(cpu.ps&254)then failed=failed+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];for a,v in pairs(before)do if emu.read(a,mt)~=v then failed=failed+1 end end
 if word(W+2)~=(c.fault==1 and 4 or 2)or word(W+16)~=c.result then failed=failed+1 end
 emu.log('THRESHOLD|'..word(INDEX)..'|'..failed..'|'..word(W+16)..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--evaluation',choices=('WIN32_X87_EXTENDED','BINARY32'),default='WIN32_X87_EXTENDED');a=p.parse_args()
    rows=[dict(c,bad='',result=compare(c['stall'],c['time'],c['delay'],a.evaluation))for c in cases()[::7]]
    rows+=[dict(rows[0],bad='ready',fault=1,result=0x55aa),dict(rows[0],bad='duration_high',delay=65536,fault=1,result=0x55aa)]
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);(folder/'report.json').write_text('{"status":"RUNNING"}\n')
    reporter=Reporter('M4-U32-FLOAT-THRESHOLD',kind='GATE');lua=re.sub(r'\bW\b',str(W),LUA)
    raw,log=run_fixture(a.rom,folder,rows,'ThresholdProbe','VmSourceInput_Ready',0xb68e,[],lua,reporter,append=ASM+emit(W,a.evaluation),probes=dict(RETURNPOINT='ThresholdProbe_Return'),batch_size=64,frame_limit=1000,link_pcm=False)
    observed=[list(map(int,l.split('THRESHOLD|',1)[1].split('|')))for l in log.splitlines()if 'THRESHOLD|'in l];errors=[r for r in observed if r[1]]
    reporter.check('source evaluation policy preserves threshold result, input words and CPU/decimal state; unsupported duration rejects',len(observed)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_U32_FLOAT_THRESHOLD_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',evaluation_policy=a.evaluation,cases=len(rows),guards=2,observed=len(observed),errors=errors[:8],rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max((r[-1]for r in observed),default=0),release_attack_body_bound=False,full_player_think_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish();assert report['status']=='PASS'
if __name__=='__main__':main()
