"""Native cache boundary and real destx/destz fields birth-clear ownership."""
import argparse,hashlib,itertools,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ARG=0x7ffd8a
ASM='''CostStateProbe:
.a16
.i16
 lda.l ARG
 jsl COSTCALL
CostStateProbe_After:
.a16
.i16
 nop
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu={},{}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(ARG,c.value)
 set('SourceMovementState4086_Ready',c.ready);set('SourceAttackCostState4086_Ready',c.bad=='cost_lease'and 0 or 0xb609);set('VmSourceWorld_Ready',c.bad=='world'and 0 or 0xb4a3);set('VmSourceWorld_Count',c.bad=='count_zero'and 0 or c.bad=='count_large'and 129 or c.bad=='count_small'and c.value or 128)
 set('SourceModelAnimationCopy4086_Ready',c.bad=='cache_ready'and 0 or 0xb4e9);set('SourceModelAnimationCopy4086_Bytes',c.bytes)
 for j=0,8191 do emu.write(0x43c000+j,(j*17+91)&255,mt)end
 before={};for j=0,8191 do before[0x43c000+j]=emu.read(0x43c000+j,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,COSTCALL,COSTCALL,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 if CLEAR and c.ready==0xb60b and c.fault==0 then for j=0,7 do before[0x43da00+c.value*8+j]=0 end end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('COSTSTATE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..st['cpu.a'])
end,emu.callbackType.exec,COSTAFTER,COSTAFTER,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--birth-clear',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 if a.birth_clear:
  rows=[dict(ready=r,value=s,bytes=b,bad='',fault=int(r not in (0,0xb60b)or r==0xb60b and(s>=128 or not 0<b<=6656)))for r,s,b in itertools.product((0,0xb60b,0xb60c),(0,1,95,96,127,128,65535),(0,5376,6656,6658,8192))]
  rows.extend(dict(ready=0xb60b,value=s,bytes=5376,bad=bad,fault=1)for s,bad in itertools.product((0,127),('world','count_zero','count_large','count_small','cache_ready','cost_lease')))
 else:rows=[dict(ready=r,value=b,bytes=5376,bad='',fault=int(r not in(0,0xb60b)or r==0xb60b and b>6656))for r,b in itertools.product((0,0xb60b,0xb60c),(0,5376,6654,6656,6658,8192,65535))]
 call='SourceMovementState4086_BirthClear'if a.birth_clear else'SourceMovementState4086_CheckCacheSpan';r=Reporter('M4-MOVEMENT-STATE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'CostStateProbe','SourceMovementState4086_Ready',0xb60b,[],LUA.replace('ARG',str(ARG)).replace('CLEAR','true'if a.birth_clear else'false'),r,append=ASM.replace('ARG',str(ARG)),bindings=dict(COSTCALL=call),probes=dict(COSTAFTER='CostStateProbe_After'),batch_size=1,frame_limit=2000)
 actual=[list(map(int,l.split('COSTSTATE|',1)[1].split('|')))for l in log.splitlines()if 'COSTSTATE|'in l];expected=[[i,0,0,c['value']]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 r.check('movement-off no extra fence; active 6656-byte fence; full32 selected field clear only; cache/siblings/CPU/A unchanged; invalid world/slot/cache leases rejected',len(actual)==len(rows)and not failures)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_MOVEMENT_STATE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:10],rom_sha256=hashlib.sha256(raw).hexdigest(),birth_clear=a.birth_clear,active_cache_capacity=6656,cost_only_cache_capacity=7680,fully_disabled_cache_capacity=8192,span_probe_scope='movement fence only; combined cache writer tested separately',field_address=0x43da00,field_bytes=1024,actual_constructor_hook_proven=False,model_copy_retention_proven=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
