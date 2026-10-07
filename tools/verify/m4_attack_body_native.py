"""Exact turn/chain actor-field installation across split physical WRAM rows."""
import argparse,hashlib,json
from pathlib import Path
from compiler import Source
from source_attack_body_profile import derive,pack_runtime
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture,REQUEST
from _harness import Reporter

ASM='''
BodyProbe:
.a16
.i16
 lda.l MODEL
 tax
 lda.l SLOT
 jsl COPYBODY
BodyProbe_After:
.a16
.i16
 nop
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu,ctx={}, {},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(SLOT,c.slot);put(MODEL,c.model)
 set('SourceAttackBody4086_Ready',c.bad=='ready'and 0 or 0xb605);set('SourceAttackBody4086_Status',c.bad=='busy'and 1 or 0);set('SourceAttackBody4086_Bank',c.bad=='bank'and 0 or 59);set('SourceAttackBody4086_Base',c.bad=='base'and 0x7fff or c.bad=='extent'and 0xfff0 or 0x8000);set('SourceAttackBody4086_Bytes',c.bad=='bytes'and 1 or TABLEBYTES);set('SourceAttackBody4086_Models',55);set('SourceModelEntityCopy4086_Models',c.bad=='paired'and 15 or 16)
 for j,value in ipairs(tables[c.synthetic+1])do emu.write(59*32768+j-1,value,emu.memType.snesPrgRom)end
 if c.patch>=0 then for j=0,1 do emu.write(59*32768+c.patch+j,(c.value>>(8*j))&255,emu.memType.snesPrgRom)end end
 for _,r in ipairs({{0x435980,1056},{0x40bdcc,352}})do for j=0,r[2]-1 do emu.write(r[1]+j,0xa5,mt)end end
 before={};for _,r in ipairs({{0x435800,1536},{0x40bd00,768},{0x438800,1792},{0x437e00,2560},{0x439000,10240},{0x40c000,12288},{0x414000,18432},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,COPYBODY,COPYBODY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'a','x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,COPYAFTER,COPYAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local data=tables[c.synthetic+1]
 if c.fault==0 then local base=c.slot<96 and 0x435980+c.slot*11 or 0x40bdcc+(c.slot-96)*11;for j=0,8 do before[base+j]=data[17+c.model*9+j]end;before[base+9]=5;before[base+10]=0xb6 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('BODYFIELDS|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceAttackBody4086_Status)..'|'..word(sy.SourceAttackBody4086_Models))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--preflight',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 profile=derive(Source(a.source));real=pack_runtime(profile);assert len(real)==160
 for i,m in enumerate(profile['models']):
  row=authority['actual'][16+i%13];m['fields']=dict(noflip=row[0],chainlength=row[1],atchain=row[2:])
 synthetic=pack_runtime(profile);rows=[]
 for which in (0,1):
  for slot in range(128):rows.append(dict(slot=slot,model=slot%16,synthetic=which,bad='',fault=0,patch=-1,value=0))
 for bad in ('ready','busy','bank','base','extent','bytes','paired','slot','model'):
  rows.append(dict(rows[0],bad=bad,slot=128 if bad=='slot'else 0,model=16 if bad=='model'else 0,fault=1))
 for at,value in ((0,0),(4,2),(6,0),(6,17),(8,8),(10,11),(12,0),(12,8),(14,1),(20,7),(24,0xd0)):
  rows.append(dict(rows[0],patch=at,value=value,fault=1))
 lua='local tables='+luav([list(real),list(synthetic)])+'\n'+LUA.replace('if c.fault==0 then','if c.fault==0 and not PREFLIGHT then').replace('PREFLIGHT','true'if a.preflight else'false').replace('TABLEBYTES',str(len(real))).replace('SLOT',str(REQUEST+10)).replace('MODEL',str(REQUEST+12));asm=ASM.replace('SLOT',str(REQUEST+10)).replace('MODEL',str(REQUEST+12))
 reporter=Reporter('M4-ATTACK-BODY-FIELDS',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'BodyProbe','SourceAttackBody4086_Ready',0xb605,[(59,0,real)],lua,reporter,append=asm,bindings=dict(COPYBODY='SourceAttackBody4086_PreflightEntity'if a.preflight else'SourceAttackBody4086_CopyEntity'),probes=dict(COPYAFTER='BodyProbe_After'),batch_size=1,frame_limit=6000)
 actual=[list(map(int,l.split('BODYFIELDS|',1)[1].split('|')))for l in log.splitlines()if 'BODYFIELDS|'in l];expected=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else 16]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('literal C turn/chain identity, both row regions/all slots, atomic marker, siblings/choice buffer/cache/globals/VM/RNG/CPU/stack retention and guards',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ATTACK_BODY_FIELDS_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),table_sha256=hashlib.sha256(real).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),entity_row_bytes=11,entity_bytes=1408,actual_birth_and_model_copy_bound=False,normal_prepare_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
