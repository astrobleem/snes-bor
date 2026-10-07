"""Atomic timing cache load and per-entity scalar copy; real/mutated C rows."""
import argparse,hashlib,json,struct
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from compiler import Source
from source_attack_timing_4086 import derive,pack
from m4_animation_init_native import luav

ASM='''
TimingProbe:
.a16
.i16
 jsl LOADTIMING
TimingProbe_LoadAfter:
.a16
.i16
 nop
 bcc TimingProbe_Copy
 sec
 rtl
TimingProbe_Copy:
.a16
.i16
 lda.l MODEL
 tax
 lda.l SLOT
 jsl COPYTIMING
TimingProbe_CopyAfter:
.a16
.i16
 nop
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu={},{}
local loadctx,copyctx=0,0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
local function capture()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end
local function context()local st=emu.getState();local n=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then n=n+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then n=n+1 end;return n end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(SLOT,c.slot);put(MODEL,c.model);copyctx=0
 set('SourceAttackTiming4086_Ready',c.bad=='ready'and 0 or 0xb603);set('SourceAttackTiming4086_Status',c.bad=='busy'and 1 or 0);set('SourceAttackTiming4086_Bank',c.bad=='bank'and 0 or 59);set('SourceAttackTiming4086_Base',c.bad=='base'and 0x7fff or c.bad=='extent'and 0xfff0 or 0x8000);set('SourceAttackTiming4086_Bytes',c.bad=='short'and 0 or TABLEBYTES);set('SourceAttackTiming4086_Models',55);set('SourceModelEntityCopy4086_Models',c.bad=='paired'and 15 or 16)
 local data=tables[c.synthetic+1];for j,value in ipairs(data)do emu.write(59*32768+j-1,value,emu.memType.snesPrgRom)end
 if c.patch>=0 then for j=0,1 do emu.write(59*32768+c.patch+j,(c.value>>(8*j))&255,emu.memType.snesPrgRom)end end
 for _,r in ipairs({{0x40bd00,192},{0x438800,1792}})do for j=0,r[2]-1 do emu.write(r[1]+j,0xa5,mt)end end
 before={};for _,r in ipairs({{0x40bd00,192},{0x438800,2048},{0x437e00,2560},{0x439000,10240},{0x40c000,12288},{0x414000,18432},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,LOADTIMING,LOADTIMING,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()loadctx=context()end,emu.callbackType.exec,LOADAFTER,LOADAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,COPYTIMING,COPYTIMING,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()copyctx=context()end,emu.callbackType.exec,COPYAFTER,COPYAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local data=tables[c.synthetic+1]
 if c.loaded then for j=0,191 do before[0x40bd00+j]=data[29+j]end end
 if c.fault==0 then local base=0x438800+c.slot*14;for j=0,11 do before[base+j]=data[29+c.model*12+j]end;before[base+12]=3;before[base+13]=0xb6 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('TIMINGSCALARS|'..word(INDEX)..'|'..loadctx..'|'..copyctx..'|'..changed..'|'..word(sy.SourceAttackTiming4086_Status)..'|'..word(sy.SourceAttackTiming4086_Models))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 profile=derive(Source(a.source));real=pack(profile);assert len(real)==220
 synthetic=real[:28]+b''.join(struct.pack('<iII',*v)for v in authority['actual'][16:32]);assert len(synthetic)==len(real)
 rows=[]
 for which in (0,1):
  for s in range(128):rows.append(dict(slot=s,model=(0,3,4,8,14,15)[s%6],synthetic=which,bad='',fault=0,loaded=True,patch=-1,value=0))
 for model in range(16):rows.append(dict(rows[0],slot=127,model=model,synthetic=1))
 for bad in ('ready','busy','bank','base','extent','short','paired','slot','model'):
  rows.append(dict(rows[0],bad=bad,slot=128 if bad=='slot'else 0,model=16 if bad=='model'else 0,fault=1,loaded=bad in ('paired','slot','model')))
 for at,value in ((0,0),(4,2),(6,0),(6,17),(8,16),(10,1),(12,1),(14,1),(18,0x7f80),(22,0xff80),(26,0x7fc0),(34,0x7f80),(38,0x7fc0),(214,0xff80),(218,0x7f80)):
  rows.append(dict(rows[0],patch=at,value=value,fault=1,loaded=False))
 from _source_leaf_fixture import REQUEST
 slotparam,modelparam=REQUEST+10,REQUEST+12;asm=ASM.replace('SLOT',str(slotparam)).replace('MODEL',str(modelparam));lua='local tables='+luav([list(real),list(synthetic)])+'\n'+LUA.replace('TABLEBYTES',str(len(real))).replace('SLOT',str(slotparam)).replace('MODEL',str(modelparam))
 reporter=Reporter('M4-ATTACK-TIMING',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'TimingProbe','SourceAttackTiming4086_Ready',0xb603,[(59,0,real)],lua,reporter,append=asm,bindings=dict(LOADTIMING='SourceAttackTiming4086_Load',COPYTIMING='SourceAttackTiming4086_CopyEntity'),probes=dict(LOADAFTER='TimingProbe_LoadAfter',COPYAFTER='TimingProbe_CopyAfter'),batch_size=1,frame_limit=6000)
 actual=[list(map(int,l.split('TIMINGSCALARS|',1)[1].split('|')))for l in log.splitlines()if 'TIMINGSCALARS|'in l];expected=[[i,0,0,0,2 if c['loaded']else 3,16 if c['loaded']else 55]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('literal C scalar identity, atomic cache/row publication, all physical slots/current models, siblings/sentinel/life/VM/engine+CRT RNG/CPU retention and guards',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ATTACK_TIMING_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),table_sha256=hashlib.sha256(real).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),cache_bytes=192,entity_row_bytes=14,entity_bytes=1792,actual_birth_and_model_copy_hook_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
