"""Native immutable animation energy table query over all source handles."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav
from compiler import Source
from source_animation_energy_4086 import derive,pack,FIELDS

ASM='''
AnimationEnergyProbe:
.a16
.i16
 php
 rep #$38
 lda.l RANGEHANDLE
 jsl RANGEQUERY
AnimationEnergyProbe_After:
.a16
.i16
 nop
 bcs AnimationEnergyProbe_Bad
 plp
 clc
 rtl
AnimationEnergyProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local before,cpu={},{}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceAnimationEnergy4086_Ready',c.bad=='ready'and 0 or 0xb5fc);set('SourceAnimationEnergy4086_Status',c.bad=='busy'and 1 or 0)
 set('SourceAnimationEnergy4086_Bank',c.bank);set('SourceAnimationEnergy4086_Bytes',c.bytes);set('SourceAnimationEnergy4086_Handle',c.handle)
 for i=0,11 do emu.write(sy.SourceCheckEnergy4086_Cost+i,0x55,mt)end
 for i,v in ipairs(tablebytes)do emu.write(59*32768+i-1,v,emu.memType.snesPrgRom)end
 if c.patch>=0 then for j=0,1 do emu.write(59*32768+c.patch+j,(c.value>>(8*j))&255,emu.memType.snesPrgRom)end end
 before={};for _,block in ipairs({{0x414000,18432},{0x40c000,12288},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18}})do for j=0,block[2]-1 do before[block[1]+j]=emu.read(block[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,RANGEQUERY,RANGEQUERY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 local values={};for i=0,2 do local a=sy.SourceCheckEnergy4086_Cost+i*4;values[#values+1]=word(a)|(word(a+2)<<16)end
 emu.log('ANIMENERGY|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceAnimationEnergy4086_Status)..'|'..table.concat(values,'|'))
end,emu.callbackType.exec,RANGEAFTER,RANGEAFTER,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ir=derive(Source(a.source));table=pack(ir)
 rows=[dict(handle=an['handle'],bank=59,bytes=len(table),bad='',patch=-1,value=0,fault=0,expected=[v&0xffffffff for v in [an['fields'][f]for f in FIELDS]])for an in ir['animations']]
 for bad,change in [('ready',{}),('busy',{}),('bank',dict(bank=64)),('bytes_zero',dict(bytes=0)),('bytes_small',dict(bytes=31)),('bytes_large',dict(bytes=32769)),('extent_short',dict(bytes=len(table)-1)),('extent_long',dict(bytes=len(table)+1)),('handle_zero',dict(handle=0)),('handle_end',dict(handle=len(rows)+1))]:rows.append(dict(rows[0],**change,bad=bad,fault=1))
 for label,at,value in [('magic1',0,0),('magic2',2,0),('version',4,2),('count_zero',6,0),('count_large',6,2048),('stride',8,15),('reserved1',10,1),('reserved2',12,1),('reserved3',14,1)]:rows.append(dict(rows[0],bad=label,patch=at,value=value,fault=1))
 for label,at in [('row_reserved_low',28),('row_reserved_high',30)]:rows.append(dict(rows[0],bad=label,patch=at,value=1,fault=1))
 reporter=Reporter('M4-ANIMATION-ENERGY',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AnimationEnergyProbe','SourceAnimationEnergy4086_Ready',0xb5fc,[(59,0,table)],'local tablebytes='+luav(list(table))+'\n'+LUA,reporter,batch_size=2,append=ASM,bindings=dict(RANGEHANDLE='SourceAnimationEnergy4086_Handle',RANGEQUERY='SourceAnimationEnergy4086_Query'),probes=dict(RANGEAFTER='AnimationEnergyProbe_After'))
 actual=[list(map(int,l.split('ANIMENERGY|',1)[1].split('|')))for l in log.splitlines()if 'ANIMENERGY|'in l]
 expected=[[i,0,0,3 if c['fault']else 2,*([0x55555555]*3 if c['fault']else c['expected'])]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('all source energy handles; invalid table/lease/extents preserve output; CPU/entity/VM/RNG retention',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ANIMATION_ENERGY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],source_table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),mutable_entity_animation_role_resolution_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
