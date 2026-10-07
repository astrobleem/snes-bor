"""Native measured Win32 C rand compatibility, separate engine stream and CPU."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu,ctx,start={}, {},0,0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceCRandom4086_Ready',c.bad=='ready'and 0 or 0xb5ea);set('SourceCRandom4086_Profile',c.bad=='profile'and 2 or 1)
 set('SourceCRandom4086_SeedLo',c.seed_before,4);set('SourceCRandom4086_CallsLo',c.calls,4);set('SourceCRandom4086_Result',55,4);set('SourceCRandom4086_Busy',c.bad=='busy'and 1 or 0)
 before={};for j=0,11 do put(sy.SourceRandom4086_Ready+j,0xa5,1);before[sy.SourceRandom4086_Ready+j]=0xa5 end
 for j=0,17 do local a=sy.SourceCRandom4086_Ready+j;before[a]=emu.read(a,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3;start=s.masterClock
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then
  for _,r in ipairs({{sy.SourceCRandom4086_SeedLo,c.seed_after},{sy.SourceCRandom4086_CallsLo,(c.calls+1)&0xffffffff},{sy.SourceCRandom4086_Result,c.expected}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('CRAND|'..word(INDEX)..'|'..ctx..'|'..n..'|'..dw(sy.SourceCRandom4086_SeedLo)..'|'..dw(sy.SourceCRandom4086_CallsLo)..'|'..dw(sy.SourceCRandom4086_Result)..'|'..word(sy.SourceCRandom4086_Busy)..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'and authority['profile_id']==1
 rows=[dict(c,calls=(0,65535,0xfffffffe,0xffffffff)[i%4],fault=0,bad='')for i,c in enumerate(authority['inputs'])]
 for bad in ('ready','profile','busy'):rows.append(dict(rows[0],bad=bad,fault=1))
 lua=LUA
 r=Reporter('M4-C-RAND-WIN32',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCRandom4086_Next','SourceCRandom4086_Ready',0xb5ea,[],lua,r,batch_size=8)
 results=[list(map(int,l.split('CRAND|',1)[1].split('|')))for l in log.splitlines()if 'CRAND|'in l]
 wanted=[[i,0,0,c['seed_before']if c['fault']else c['seed_after'],c['calls']if c['fault']else(c['calls']+1)&0xffffffff,55 if c['fault']else c['expected'],int(c['bad']=='busy')]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v[:7],expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v[:7]!=e]
 r.check('measured CRT results/full32 seed and counter including wrap; independent engine stream/CPU; unknown profile and busy/disabled leases reject',len(results)==len(rows)and not failures)
 costs=[v[7]for c,v in zip(rows,results)if not c['fault']]
 report=dict(schema='BYOR_4086_C_RUNTIME_RAND_WIN32_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),profile=authority['profile'],inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),observed_master_clocks=dict(min=min(costs,default=0),max=max(costs,default=0),average=sum(costs)/len(costs)if costs else 0),clock_measurement_includes_fixture_return_and_any_interrupts=True,original_engine_binary_crt_verified=False,engine_rand32_stream_shared=False,world_owner_installed=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
