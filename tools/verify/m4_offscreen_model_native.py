"""Native immutable model-value replacement and pure admission of B4OS."""
import argparse, hashlib, itertools, json, struct
from pathlib import Path
from source_offscreen_inputs import pack, unpack
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ARG = 0x7ffd8a
ASM = '''OffscreenModelProbe:
.a16
.i16
 lda.l ARG+2
 tax
 lda.l ARG
 jsl MODELCALL
OffscreenModelProbe_After:
.a16
.i16
 nop
 rtl
'''
LUA = r'''
local mt=emu.memType.snesMemory
local before,cpu={},{}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(ARG,c.slot);put(ARG+2,c.model)
 set('SourceOffscreenState4086_Ready',c.ready);set('SourceOffscreenState4086_Base',c.base);set('SourceOffscreenState4086_Bank',c.bank);set('SourceOffscreenState4086_Bytes',c.size);set('SourceOffscreenState4086_Models',c.count)
 set('SourceAutokillState4086_Ready',c.bad=='autokill_lease'and 0 or 0xb60e)
 set('SourceMovementState4086_Ready',0xb60b);set('SourceAttackCostState4086_Ready',0xb609)
 set('VmSourceWorld_Ready',c.bad=='world'and 0 or 0xb4a3);set('VmSourceWorld_Count',128)
 set('SourceModelEntityCopy4086_Models',c.bad=='paired_models'and 15 or 16)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Bytes',c.bad=='cache_span'and 5634 or 5376)
 for j=0,8191 do emu.write(0x43c000+j,(j*17+91)&255,mt)end
 before={};for j=0,8191 do before[0x43c000+j]=emu.read(0x43c000+j,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,MODELCALL,MODELCALL,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local st=emu.getState();local ctx=0;for _,k in ipairs({'a','x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 if APPLY and c.ready==0xb610 and c.fault==0 then for j=0,3 do before[0x43d600+c.slot*4+j]=(c.value>>(8*j))&255 end end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('OFFSCREENMODEL|'..word(INDEX)..'|'..ctx..'|'..changed)
end,emu.callbackType.exec,MODELAFTER,MODELAFTER,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--preflight',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    values=[0,30,-1,-2147483648,2147483647,200,300,-200]*2
    table=pack(dict(models=[dict(id=i,offscreenkill=v)for i,v in enumerate(values)]));assert len(unpack(table))==16
    variants=[table]; bads=[]
    for offset,value in [(0,0),(2,0),(4,2),(6,4),(8,15),(10,1),(12,120),(14,1),(20,1),(22,1),(24,1),(26,1)]:
        raw=bytearray(table);struct.pack_into('<H',raw,offset,value);variants.append(bytes(raw));bads.append('table_'+str(offset))
    tables=[(60,i*160,t)for i,t in enumerate(variants)]
    base=dict(ready=0xb610,base=0x8000,bank=60,size=len(table),count=16,bad='',fault=0)
    rows=[dict(base,slot=s,model=i,value=values[i])for s,i in itertools.product((0,1,95,96,127),range(16))]
    rows.extend(dict(base,slot=s,model=0,value=0,ready=0)for s in (0,127,128,65535))
    for i,bad in enumerate(bads,1):rows.append(dict(base,slot=127,model=0,value=0,base=0x8000+i*160,bad=bad,fault=1))
    for bad,overrides in [('ready',dict(ready=0xb611)),('bank_zero',dict(bank=0)),('bank_large',dict(bank=64)),('base_low',dict(base=0x7fff)),('cross_bank',dict(base=0xff80)),('count_zero',dict(count=0)),('count_large',dict(count=17)),('bytes',dict(size=150)),('slot',dict(slot=128)),('model',dict(model=16)),('world',{}),('autokill_lease',{}),('cache_span',{}),('paired_models',{})]:
        row=dict(base,slot=127,model=0,value=0,bad=bad,fault=1);row.update(overrides);rows.append(row)
    call='SourceOffscreenState4086_PreflightModel'if a.preflight else'SourceOffscreenState4086_ApplyModel'
    r=Reporter('M4-OFFSCREEN-MODEL',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'OffscreenModelProbe','SourceOffscreenState4086_Ready',0xb610,tables,LUA.replace('ARG',str(ARG)).replace('APPLY','false'if a.preflight else'true'),r,append=ASM.replace('ARG',str(ARG)),bindings=dict(MODELCALL=call),probes=dict(MODELAFTER='OffscreenModelProbe_After'),batch_size=4)
    actual=[list(map(int,l.split('OFFSCREENMODEL|',1)[1].split('|')))for l in log.splitlines()if'OFFSCREENMODEL|'in l]
    expected=[[i,0,0]for i in range(len(rows))]
    r.check('full signed model value replaces only selected row; pure preflight writes no actor; rejected inputs preserve cache and CPU',actual==expected)
    (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_OFFSCREEN_MODEL_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,preflight=a.preflight,rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),native_full_model_hook_proven=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
