"""Real AI-owned health/MP/seal and mutable animation energy descriptors."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as OWNER_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from compiler import Source
from source_animation_energy_4086 import derive,pack,check

SETUP=r'''
 set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)
 set('SourceCommonThink4086_Ready',c.bad=='common_ready'and 0 or 0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',c.bad=='common_slot'and(s+1)%128 or s)
 set('SourceEntityEnergy4086_Ready',c.bad=='energy_ready'and 0 or 0xb5fd);set('SourceEntityEnergy4086_Status',c.bad=='energy_busy'and 1 or 0);put(sy.SourceEntityEnergy4086_Result,55,4);set('SourceEntityEnergy4086_Role',c.bad=='role'and 128 or c.role);put(sy.SourceEntityEnergy4086_Which,c.which,4)
 set('VmSourceEntity_Ready',c.bad=='entity_ready'and 0 or 0xb5ef);set('VmSourceEntity_Base',c.bad=='entity_base'and 0x4002 or 0x4000);set('VmSourceEntity_Bank',c.bad=='entity_bank'and 0 or 0x41);set('VmSourceEntity_Count',c.bad=='entity_count'and 127 or 128)
 set('SourceModelEntityCopy4086_Ready',c.bad=='core_ready'and 0 or 0xb4eb);set('SourceModelEntityCopy4086_Entities',c.bad=='core_count'and 127 or 128)
 set('SourceCheckEnergy4086_Ready',c.bad=='numeric_ready'and 0 or 0xb5fa);set('SourceCheckEnergy4086_Status',c.bad=='numeric_busy'and 1 or 0)
 set('SourceAnimationEnergy4086_Ready',c.bad=='table_ready'and 0 or 0xb5fc);set('SourceAnimationEnergy4086_Status',c.bad=='table_busy'and 1 or 0);set('SourceAnimationEnergy4086_Bank',59);set('SourceAnimationEnergy4086_Bytes',1296)
 put(side,c.bad=='model'and 16 or c.model);put(0x43c000+256*c.model+2*c.role,c.absent and 0 or c.bad=='handle'and 81 or c.handle);put(side+4,65535);put(side+6,65535)
 put(v+32,c.bad=='health_tag'and 2 or 1,4);put(v+36,c.health,4);put(v+64,1,4);put(v+68,c.health+100,4)
 if c.bad=='health_reserved'then put(v+34,1)end
 put(0x40c040+s*96,c.mp+100,4);put(0x40c048+s*96,c.type,4);put(0x40c04c+s*96,c.mp,4)
 put(0x437e00+s*20,123,4);put(0x437e04+s*20,c.seal,4);put(0x437e10+s*20,c.bad=='combat_marker'and 0 or 0xb5fb);put(0x437e12+s*20,c.bad=='combat_reserved'and 1 or 0)
 -- A contradictory SEALTIME proves that the scalar seal owns eligibility.
 put(0x42e020+s*40,0x7fffffff,4)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ir=derive(Source(a.source));table=pack(ir);rows=[]
 for i,an in enumerate(ir['animations']):
  for variant in range(4):
   fields=an['fields'];cost=fields['cost'];t=(0,1,2,512)[variant];which=variant%2;seal=(0,cost-1,cost,cost+1)[variant];mp=cost-1 if variant==0 else cost;health=cost+1 if variant==3 else cost
   rows.append(dict(time=50,nextthink=50,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=1,animation=5,spawn=3,respawn=4,animating=1,exists=(0,1,65536,0xffffffff)[variant],bad='',mutation=0,fault=0,slot=(0,1,63,127)[i%4],type=t,seal=seal,mp=mp,health=health,fields=fields,handle=an['handle'],role=(0,12,15,38,49,104)[i%6],model=i*7%16,which=which,absent=False,expected=int(check(which,fields,t,seal,mp,health))))
 for bad in ('energy_ready','energy_busy','common_ready','common_slot','entity_ready','entity_base','entity_bank','entity_count','role','core_ready','core_count','numeric_ready','numeric_busy','table_ready','table_busy','handle','health_tag','health_reserved','combat_marker','combat_reserved','world','cache','model','token','phase'):
  rows.append(dict(rows[0],bad=bad,fault=1))
 for c in rows[:16]:rows.append(dict(c,absent=True,expected=0))
 lua=OWNER_LUA[:OWNER_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')]
 lua=lua.replace(' before={};',SETUP+' before={};').replace('{{0x414000,18432}', '{{0x437e00,2560},{0x40c000,12288},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r'''
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('ENTITYENERGYPREDICATE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceEntityEnergy4086_Status)..'|'..dw(sy.SourceEntityEnergy4086_Result))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
 reporter=Reporter('M4-ENTITY-ENERGY',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'SourceEntityEnergy4086_Execute','SourceEntityEnergy4086_Ready',0xb5fd,[(59,0,table)],lua,reporter,batch_size=2)
 actual=[list(map(int,l.split('ENTITYENERGYPREDICATE|',1)[1].split('|')))for l in log.splitlines()if 'ENTITYENERGYPREDICATE|'in l]
 expected=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else c['expected']]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('actual current health/dynamic MP/scalar seal/current role handle; no birth-cursor/max-resource/timer substitution; CPU/entities/VM/RNG retained',len(actual)==len(rows)and not failures)
 r=dict(schema='BYOR_4086_ENTITY_ENERGY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),actual_entity_binding=True,current_mutable_animation_binding=True,combat_choice_body_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
