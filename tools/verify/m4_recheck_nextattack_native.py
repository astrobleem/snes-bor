"""Native source timer mutation pairs with actual flags and unsigned edges."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

ASM='''
RecheckPairProbe:
.a16
.i16
 php
 rep #$38
 lda.l TARGET
 jsl RECHECK
RecheckPairProbe_First:
.a16
.i16
 nop
 bcs RecheckPairProbe_Bad
 lda.l TARGET
 jsl RECHECK
RecheckPairProbe_Second:
.a16
.i16
 nop
 bcs RecheckPairProbe_Bad
 plp
 clc
 rtl
RecheckPairProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--existing-log',action='store_true',help='Reprocess the retained completed fixture after a parser-only correction')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());assert au['status']=='PASS';rows=[]
 base=dict(time=50,nextthink=50,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=1,animation=5,spawn=3,respawn=4,animating=1,exists=1,bad='',mutation=0)
 for i,(c,e)in enumerate(zip(au['inputs'],au['actual'])):rows.append(dict(base,**c,slot=(0,1,63,127)[i%4],targetslot=(1,63,127,0)[i%4],targetexists=(0,65536,0xffffffff)[i%3],fault=0,pair=e[:2]))
 for bad in ('recheck_ready','recheck_busy','normal_ready','normal_phase','normal_slot','core_ready','core_count','target_slot','target_token','target_bank'):
  rows.append(dict(rows[0],bad=bad,fault=1,pair=[55,55]))
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 setup=r'''
 local t=c.targetslot;local target=0x414000+80*t
 put(target,target,4);put(target+4,c.targetexists,4);put(0x43eb0c+32*t,c.blocking,4);put(0x43eb08+32*t,c.jumping,4);put(0x40c058+96*t,c.attacking,4);put(0x40c05c+96*s,c.timer,4)
 set('SourceRecheckNextAttack4086_Ready',c.bad=='recheck_ready'and 0 or 0xb5f6);set('SourceRecheckNextAttack4086_Status',c.bad=='recheck_busy'and 1 or 0);put(sy.SourceRecheckNextAttack4086_Result,55,4);set('SourceRecheckNextAttack4086_Target',c.bad=='target_slot'and 128 or t)
 set('SourceNormalAttack4086_Ready',c.bad=='normal_ready'and 0 or 0xb5eb);set('SourceNormalAttack4086_State',c.bad=='normal_phase'and 8 or 5);set('SourceNormalAttack4086_Slot',c.bad=='normal_slot'and(s+1)%128 or s)
 set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s)
 set('SourceModelEntityCopy4086_Ready',c.bad=='core_ready'and 0 or 0xb4eb);set('SourceModelEntityCopy4086_Entities',c.bad=='core_count'and 127 or 128)
 if c.bad=='target_token'then put(target,target+1)elseif c.bad=='target_bank'then put(target+2,0)end
'''
 lua=lua.replace(' local faults=',setup+' local faults=')
 lua=lua.replace('{{0x414000,18432}', '{{0x40c000,12288},{0x414000,18432}')
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+30);lua=lua[:start]+lua[end:]
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local s=c.slot;local e=c.expected')
 lua=lua[:start]+r'''
local nativecpu,context,first,second={},0,55,55
emu.addMemoryCallback(function()local st=emu.getState();nativecpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do nativecpu[k]=st['cpu.'..k]end;nativecpu.sp=nativecpu.sp+3 end,emu.callbackType.exec,sy.SourceRecheckNextAttack4086_Execute,sy.SourceRecheckNextAttack4086_Execute,emu.cpuType.snes,mt)
local function returned()
 local st=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if nativecpu[k]~=st['cpu.'..k]then context=context+1 end end;if(nativecpu.ps&254)~=(st['cpu.ps']&254)then context=context+1 end
 return dw(sy.SourceRecheckNextAttack4086_Result)
end
emu.addMemoryCallback(function()context=0;second=55;first=returned()end,emu.callbackType.exec,FIRST,FIRST,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()second=returned()end,emu.callbackType.exec,SECOND,SECOND,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then for j=0,3 do before[0x40c05c+96*c.slot+j]=(c.pair[2]>>(8*j))&255 end end
 local n=0;for addr,v in pairs(before)do if emu.read(addr,mt)~=v then n=n+1 end end
 emu.log('RECHECKPAIR|'..word(INDEX)..'|'..context..'|'..n..'|'..word(sy.SourceRecheckNextAttack4086_Status)..'|'..first..'|'..second..'|'..dw(0x40c05c+96*c.slot))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-RECHECK-NEXTATTACK',kind='GATE')
 if a.existing_log:
  raw=(a.output/'bor.sfc').read_bytes();prior=json.loads((a.output/'report.json').read_text());assert prior['rom_sha256']==hashlib.sha256(raw).hexdigest()
  assert 'native leaf batch completed: PASS'in a.output.with_suffix('.log').read_text()
  log=(a.output/'mesen.log').read_text();r.check('retained completed native fixture and ROM identity',True)
 else:raw,log=run_fixture(a.rom,a.output,rows,'RecheckPairProbe','SourceRecheckNextAttack4086_Ready',0xb5f6,[],lua,r,append=ASM,bindings=dict(TARGET='SourceRecheckNextAttack4086_Target',RECHECK='SourceRecheckNextAttack4086_Execute'),probes=dict(FIRST='RecheckPairProbe_First',SECOND='RecheckPairProbe_Second'),batch_size=2)
 prefix=str(symbols(Path('src/main.sym'))['SourceRecheckNextAttack4086_Execute'])+'|'if a.existing_log else'RECHECKPAIR|'
 results=[list(map(int,l.split(prefix,1)[1].split('|')))for l in log.splitlines()if prefix in l]
 wanted=[[i,0,0,3 if c['fault']else 2,*c['pair'],c['timer']if c['fault']else c['pair'][1]]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,results,wanted)if v!=e]
 r.check('literal full32 flags/unsigned thresholds/borrow and two calls; inactive target accepted; only actual self timer changes; CPU and siblings retained; checked pointers/owners',len(results)==len(rows)and not failures)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_RECHECK_NEXTATTACK_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),results=results,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),timer_address='40C000 + physical_slot * 96 + 92',observer_parser_recovery=a.existing_log,normalattack_body_integrated=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()
if __name__=='__main__':main()
