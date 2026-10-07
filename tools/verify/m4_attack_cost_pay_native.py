"""Actual tocost payment: cached-role eligibility and current-animation debit."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as OWNER_LUA
from m4_entity_energy_native import SETUP
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from compiler import Source
from source_animation_energy_4086 import derive,pack,check

ASM="""AttackCostPayProbe:
.a16
.i16
 jsl PAY
 bcs AttackCostPayProbe_Return
 jsl PAY ; actual cleared field prevents a second debit
AttackCostPayProbe_Return:
.a16
.i16
 rtl
"""
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 ir=derive(Source(a.source));table=pack(ir);rows=[]
 for i,an in enumerate(ir['animations']):
  for variant in range(6):
   fields=an['fields'];cost=fields['cost'];t=(0,1,2,512,65536,3)[variant];seal=0;mp=cost-1 if variant%2==0 else cost;health=cost+1
   live=ir['animations'][(i+variant+1)%len(ir['animations'])];actualcost=live['fields']['cost']
   absent=variant==4;tocost=(0,1,65536,0xffffffff,1,1)[variant]
   eligible=not absent and check(1,fields,t,seal,mp,health)
   rows.append(dict(time=50,nextthink=50,endgame=0,takeaction=17,think=0,noaicontrol=0,reactive=1,update_mark=1,animation=5,spawn=3,respawn=4,animating=0,exists=1,bad='',mutation=0,fault=0,slot=(0,1,95,96,127)[i%5],type=t,seal=seal,mp=mp,health=health,fields=fields,handle=an['handle'],role=(0,12,15,38,49,104)[i%6],model=i*7%16,which=1,absent=absent,tocost=tocost,livehandle=live['handle'],livecost=actualcost,expectedmp=(mp-actualcost if tocost and eligible else mp)&0xffffffff,expectedhealth=(health-actualcost if tocost and not eligible else health)&0xffffffff))
 for bad in ('pay_ready','pay_busy','cost_ready','cost_cache_overlap','callback','callback_high','action_state','energy_ready','energy_busy','entity_ready','entity_base','entity_bank','entity_count','role','core_ready','core_count','numeric_ready','numeric_busy','table_ready','table_busy','handle','health_tag','health_reserved','combat_marker','combat_reserved','world','cache','model','token','phase','animation_tag','animation_reserved','animation_high','live_handle'):
  rows.append(dict(rows[1],bad=bad,fault=1))
 # Literal tocost=0 reads no animation/resource descriptors.
 for bad in ('table_ready','animation_tag','health_tag','live_handle'):
  rows.append(dict(rows[0],bad=bad,tocost=0,fault=0))
 lua=OWNER_LUA[:OWNER_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')]
 setup=SETUP.replace("set('SourceAI4086_State',2)","set('SourceAI4086_State',c.bad=='action_state'and 2 or 1)")
 setup+="""
 set('SourceAI4086_Callback',c.bad=='callback'and 16 or 17,4);if c.bad=='callback_high'then put(sy.SourceAI4086_Callback+2,1)end
 set('SourceAttackCostPay4086_Ready',c.bad=='pay_ready'and 0 or 0xb60a);set('SourceAttackCostPay4086_Status',c.bad=='pay_busy'and 1 or 0)
 set('SourceAttackCostState4086_Ready',c.bad=='cost_ready'and 0 or 0xb609)
 if c.bad=='cost_cache_overlap'then set('SourceModelAnimationCopy4086_Bytes',8192)end
 put(0x43de00+s*4,c.tocost,4)
 put(side+4,c.bad=='live_handle'and 81 or c.livehandle)
 put(v+16,c.bad=='animation_tag'and 2 or 1,4);put(v+20,c.bad=='role'and 128 or c.role,4)
 if c.bad=='animation_reserved'then put(v+18,1)elseif c.bad=='animation_high'then put(v+22,1)end
 """
 lua=lua.replace(' before={};',setup+' before={};').replace('{{0x414000,18432}','{{0x437e00,2560},{0x40c000,12288},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r"""
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 if c.fault==0 then
  for _,r in ipairs({{0x40c04c+c.slot*96,c.expectedmp},{0x414024+c.slot*80,c.expectedhealth},{0x43de00+c.slot*4,0}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('ACTUALCOSTPAY|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceAttackCostPay4086_Status))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
"""
 reporter=Reporter('M4-ATTACK-COST-PAY',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AttackCostPayProbe','SourceAttackCostPay4086_Ready',0xb60a,[(59,0,table)],lua,reporter,append=ASM,bindings=dict(PAY='SourceAttackCostPay4086_Execute'),batch_size=2)
 actual=[list(map(int,l.split('ACTUALCOSTPAY|',1)[1].split('|')))for l in log.splitlines()if 'ACTUALCOSTPAY|'in l]
 expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('actual cached-role eligibility/current-animation cost; full32 nonzero tocost; MP or health subtraction exactly once; no unrelated mutation; pre-mutation guards',len(actual)==len(rows)and not failures)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_ATTACK_COST_PAY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),finished_attack_proc_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');reporter.finish()
if __name__=='__main__':main()
