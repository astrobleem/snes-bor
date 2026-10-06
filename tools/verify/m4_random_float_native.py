"""Native unsigned modulo and every source-derived randf lookup ordinal."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_random_float_4086 import unpack
from _source_leaf_fixture import run_fixture,REQUEST
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local active=false;local writes,context,wrong=0,0,0;local saved={}
local function save()saved=emu.getState();active=true end
local function check(a)
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if s['cpu.'..k]~=saved['cpu.'..k]then context=context+1 end end
 if s['cpu.sp']~=saved['cpu.sp']+(a and 6 or 3) then context=context+1 end
 if (s['cpu.ps']&254)~=(saved['cpu.ps']&254)then context=context+1 end
 if a and s['cpu.a']~=saved['cpu.a']then context=context+1 end
 active=false
end
for _,r in ipairs({{0x409000,0x40efff},{0x414000,0x41ffff},{0x439000,0x43ffff}})do
 emu.addMemoryCallback(function()if active then writes=writes+1 end end,emu.callbackType.write,r[1],r[2],emu.cpuType.snes,mt)
end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(BASEPARAM,c.base);put(BANKPARAM,c.bank)
 put(sy.SourceModelEntityCopy4086_Lo,c.number,4);writes=0;context=0;wrong=0
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(save,emu.callbackType.exec,MODULO,MODULO,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 check(false);local c=rows[word(INDEX)+1]
 if emu.getState()['cpu.a']~=c.number%10000 then wrong=wrong+1 end
 if(word(sy.SourceModelEntityCopy4086_Lo)|(word(sy.SourceModelEntityCopy4086_Hi)<<16))~=c.number then wrong=wrong+1 end
end,emu.callbackType.exec,MODRESULT,MODRESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(save,emu.callbackType.exec,LOOKUP,LOOKUP,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 check(true);local c=rows[word(INDEX)+1]
 local value=word(sy.SourceModelEntityCopy4086_Lo)|(word(sy.SourceModelEntityCopy4086_Hi)<<16)
 if value~=(c.fault==0 and c.expected or c.number)then wrong=wrong+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('RANDFRESULT|'..word(INDEX)..'|'..writes..'|'..context..'|'..wrong)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--stride',type=int,default=1);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';tablepath=a.authority.parent/'randf.b5rf';table=(tablepath if tablepath.exists()else a.authority.parent/'randf40.b5rf').read_bytes();sourcepath=a.authority.parent/'source_values.json';sourcebits=json.loads(sourcepath.read_text())if sourcepath.exists()else None;projected=unpack(table,sourcebits)
 if not 1<=a.stride<=10000:raise ValueError('RANDF_NATIVE_STRIDE')
 ordinals=sorted(set(range(0,10000,a.stride))|{9999})
 rows=[dict(number=n,expected=projected[n%10000],base=0x8000,bank=59,fault=0)for n in ordinals]
 for n in(0x7fffffff,0x80000000,0xffffffff,0xffff0000,0x0000ffff,0x12345678):rows.append(dict(rows[0],number=n,expected=projected[n%10000]))
 for k,values in dict(base=(0,0x7fff,0x8ab9,0xffff),bank=(0,64,255)).items():
  for v in values:rows.append(dict(rows[0],**{k:v},fault=1))
 badtable=bytearray()
 for i,at in enumerate((0,2,4,6,8,10,16,18,20,22)):
  header=bytearray(table[:24]);header[at]^=1;badtable.extend(header);rows.append(dict(rows[0],base=0x8000+i*24,bank=60,fault=1))
 wrapper='''
RandomFloatFixture_Apply:
.a16
.i16
 jsl MODULO
RandomFloatFixture_ModuloResult:
.a16
.i16
 nop
 pha
 lda.l BASEPARAM
 tax
 lda.l BANKPARAM
 tay
 pla
 jsl LOOKUP
 rtl
'''
 baseparam=REQUEST+10;bankparam=REQUEST+12;wrapper=wrapper.replace('BASEPARAM',str(baseparam)).replace('BANKPARAM',str(bankparam));lua=LUA.replace('BASEPARAM',str(baseparam)).replace('BANKPARAM',str(bankparam))
 r=Reporter('M4-RANDOM-FLOAT-CONSTANT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'RandomFloatFixture_Apply','SourceModelEntityCopy4086_Ready',0xb509,[(59,0,table),(60,0,bytes(badtable))],lua,r,append=wrapper,bindings=dict(MODULO='SourceRandomFloat4086_Modulo10000',LOOKUP='SourceRandomFloat4086_LookupU24'),probes=dict(MODRESULT='RandomFloatFixture_ModuloResult'),batch_size=32)
 results=[list(map(int,line.split('RANDFRESULT|',1)[1].split('|')))for line in log.splitlines()if 'RANDFRESULT|'in line]
 r.check('C-derived source float projections, unsigned high-bit remainders, descriptor guards and context/no entity writes',results==[[i,0,0,0]for i in range(len(rows))])
 report=dict(schema='BYOR_4086_CONSTANT_RANDF_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),table_bytes=len(table),cases=len(rows),results=results,lookup_ordinals_checked=len(ordinals),all_10000_ordinals_proven=a.stride==1,numeric_policy='ACCEPTED_COMPAT_Q16_16',rng_draw_performed=False,world_rng_order_bound=False,drop_native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
