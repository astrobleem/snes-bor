"""Copied death modeldata and current cached sound across every physical slot."""
import argparse
import hashlib
import json
from pathlib import Path
from source_death_fields_4086 import pack,unpack
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''DeathFieldsFixture_Run:
.a16
.i16
 lda.l DFMODEL
 tax
 lda.l DFSLOT
 jsl DFCOPY
 rtl
DeathFieldsFixture_Birth:
.a16
.i16
 lda.l DFMODEL
 tax
 lda.l DFSLOT
 jsl DFBIRTH
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(sy.SourceDeathFields4086_Ready,c.disabled and 0 or 0xb638)
 put(sy.SourceDeathFields4086_Base,0x8000);put(sy.SourceDeathFields4086_Bank,0x3a);put(sy.SourceDeathFields4086_Bytes,TABLEBYTES);put(sy.SourceDeathFields4086_Models,16)
 put(sy.SourceModelEntityCopy4086_Ready,0xb4eb);put(sy.SourceModelEntityCopy4086_Models,16);put(sy.SourceModelEntityCopy4086_Entities,128)
 put(sy.SourceDeathFields4086_Slot,c.slot);put(sy.SourceDeathFields4086_Model,c.model)
 if c.synthetic then put(sy.SourceDeathFields4086_Base,0x8500)end
 put(0x40b04c+c.model*160,c.sound,4)
 before={}
 for _,s in ipairs({(c.slot+127)%128,c.slot,(c.slot+1)%128})do
  for _,r in ipairs({{0x414000+s*80,80},{0x409000+s*64,64}})do
   for j=0,r[2]-1 do local v=(j+s*11+37)&255;emu.write(r[1]+j,v,mt);before[r[1]+j]=v end
  end
 end
 local controls={ready={sy.SourceDeathFields4086_Ready,1},core={sy.SourceModelEntityCopy4086_Ready,0},entities={sy.SourceModelEntityCopy4086_Entities,c.slot},models={sy.SourceDeathFields4086_Models,15},bank={sy.SourceDeathFields4086_Bank,0x40},bank_high={sy.SourceDeathFields4086_Bank,0x13a},base={sy.SourceDeathFields4086_Base,0x7fff},extent={sy.SourceDeathFields4086_Bytes,TABLEBYTES-1},spill={sy.SourceDeathFields4086_Base,0xff80},header={sy.SourceDeathFields4086_Base,0x8100},reserved={sy.SourceDeathFields4086_Base,0x8200},row={sy.SourceDeathFields4086_Base,0x8300},row_reserved={sy.SourceDeathFields4086_Base,0x8400}}
 if c.bad then local r=controls[c.bad];put(r[1],r[2])end
 if c.fault==0 and not c.disabled then
  local view=0x414000+c.slot*80;local rel=0x409000+c.slot*64
  for _,r in ipairs({{view+72,c.score,4},{view+76,c.sound,4},{rel+56,c.model,2},{rel+58,0xb638,2}})do for j=0,r[3]-1 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
  if BIRTH then for j=0,3 do before[rel+60+j]=0 end end
 end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('DEATHFIELDS|'..word(INDEX)..'|'..n)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--table',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--birth',action='store_true');a=p.parse_args()
 a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);data=a.table.read_bytes();models=unpack(data)['models'];assert len(models)==16
 rows=[]
 for slot in range(128):
  for sound in(-1,17,18,0x7fffffff):
   model=(slot+sound)%16;rows.append(dict(slot=slot,model=model,sound=sound&0xffffffff,score=models[model]['score']&0xffffffff,fault=0))
 for slot in(0,63,127):
  seed=next(r for r in rows if r['slot']==slot)
  rows.append(dict(seed,disabled=True))
  rows.extend(dict(seed,bad=bad,fault=1)for bad in('ready','core','entities','models','bank','bank_high','base','extent','spill','header','reserved','row','row_reserved'))
 tables=[(58,0,data)]
 for number,bad in enumerate(('header','reserved','row','row_reserved'),1):
  altered=bytearray(data)
  if bad=='header':altered[0]=0
  elif bad=='reserved':altered[12]=1
  else:
   for model in range(16):altered[24+model*8+(2 if bad=='row_reserved'else 0)]=99
  tables.append((58,number*256,bytes(altered)))
 values=(-2147483648,-65537,-1,0,1,65537,999999999,2147483647)
 synthetic=pack(dict(models=[dict(id=i,score=values[i%8])for i in range(16)]));tables.append((58,0x500,synthetic))
 for slot in(0,63,127):
  rows.extend(dict(slot=slot,model=i,sound=18,score=values[i%8]&0xffffffff,fault=0,synthetic=True)for i in range(16))
 lua=LUA.replace('TABLEBYTES',str(len(data))).replace('BIRTH','true'if a.birth else'false')
 reporter=Reporter('M4-DEATH-FIELDS',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'DeathFieldsFixture_Birth'if a.birth else'DeathFieldsFixture_Run','SourceDeathFields4086_Ready',0xb638,tables,lua,reporter,append=ASM,
  bindings=dict(DFMODEL='SourceDeathFields4086_Model',DFSLOT='SourceDeathFields4086_Slot',DFCOPY='SourceDeathFields4086_Copy',DFBIRTH='SourceDeathFields4086_Birth'))
 actual=[[int(v)for v in line.split('DEATHFIELDS|',1)[1].split('|')]for line in log.splitlines()if'DEATHFIELDS|'in line];expected=[[i,0]for i in range(len(rows))]
 ok=actual==expected;reporter.check('all physical slots, source score, current copied signed32 diesound, item ownership, disabled static path and malformed lease preservation',ok)
 report=dict(schema='BYOR_4086_DEATH_FIELDS_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,birth_item_null=a.birth,copy_item_preserved=not a.birth,
  source_table_sha256=hashlib.sha256(data).hexdigest(),synthetic_signed_score_cases=48,synthetic_table_sha256=hashlib.sha256(synthetic).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),native_death_service_proven=False,ctor_integration_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
