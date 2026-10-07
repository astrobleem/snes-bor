"""C-derived randf delays with real RNG, actual actor fields and unsigned time."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_attack_timing_4086 import derive,pack
from source_actor_numeric import random32_step
from m4_ai_owner_native import LUA as OWNER_LUA
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

SETUP=r'''
 set('SourceModelEntityCopy4086_Models',16);set('SourceAI4086_State',2);set('SourceAI4086_Slot',s);set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s);put(side,c.model);put(side+4,65535);put(side+6,65535)
 set('SourceAttackTiming4086_Ready',c.bad=='timing_ready'and 0 or 0xb603);set('SourceAttackTiming4086_Status',c.bad=='timing_busy'and 1 or 2);set('SourceAttackTiming4086_Models',c.bad=='timing_models'and 15 or 16)
 for j=0,11 do emu.write(0x438800+s*14+j,timingbytes[29+c.model*12+j],mt)end;put(0x438800+s*14+12,c.bad=='param_marker'and 0 or 0xb603)
 if c.bad=='aggression'then put(0x438800+s*14,1,4)end;if c.bad=='time_coefficient'then put(0x438800+s*14+8,1,4)end
 if c.zero then put(0x438800+s*14+8,c.zero_bits,4)end
 set('SourceAttackDelay4086_Ready',c.bad=='ready'and 0 or 0xb604);set('SourceAttackDelay4086_Status',c.bad=='busy'and 1 or 0);set('SourceAttackDelay4086_Kind',c.bad=='kind'and 2 or c.kind);set('SourceAttackDelay4086_Bank',c.bad=='bank'and 0 or 59);set('SourceAttackDelay4086_Base',c.bad=='base'and 0x7fff or c.bad=='extent'and 0xfff0 or 0x8000);set('SourceAttackDelay4086_Bytes',c.bad=='bytes'and 1 or TABLEBYTES);put(sy.SourceAttackDelay4086_Result,55,4)
 set('SourceRandom4086_Ready',c.bad=='rng_ready'and 0 or 0xb4d4);set('SourceRandom4086_Busy',c.bad=='rng_busy'and 1 or 0);put(sy.SourceRandom4086_SeedLo,c.seed,4);put(sy.SourceRandom4086_CallsLo,0xffffffff,4)
 for j=0,7 do emu.write(sy.VmNativeVariant_Result+j,0xa5,mt)end;put(sy.SourceModelEntityCopy4086_Lo,0x12345678,4)
 for j,value in ipairs(tablebytes)do emu.write(59*32768+j-1,value,emu.memType.snesPrgRom)end
 if c.patch>=0 then for j=0,1 do emu.write(59*32768+c.patch+j,(c.value>>(8*j))&255,emu.memType.snesPrgRom)end end
 if c.zero then for j=0,3 do emu.write(59*32768+20+j,(c.zero_bits>>(8*j))&255,emu.memType.snesPrgRom)end;emu.write(59*32768+28,0,emu.memType.snesPrgRom);emu.write(59*32768+29,0,emu.memType.snesPrgRom)end
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('rom','source','profile','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);table=a.profile.read_bytes();start=struct.unpack_from('<H',table,12)[0];rows=[]
 for model in range(16):
  for kind in (0,1):
   for time in (0,50,65535,0x1000001,0xffffffff):
    for seed in (0,1,65535,0xffffffff):
     after,value=random32_step(seed);delay=struct.unpack_from('<H',table,start+2*(value%10000))[0];i=len(rows)
     rows.append(dict(slot=(0,1,63,127)[i%4],model=model,kind=kind,time=time,seed=seed,seed_after=after,calls=1,delay=delay,expected=(time+delay)&0xffffffff,nextthink=time,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=1,animation=5,spawn=3,respawn=4,animating=1,exists=1,bad='',fault=0,patch=-1,value=0))
 base=rows[0]
 for zero_bits in (0,0x80000000):
  for kind in (0,1):
   for time in (0,50,0xffffffff):
    c=dict(base,zero=True,zero_bits=zero_bits,kind=kind,time=time,nextthink=time)
    if kind==0:c.update(calls=0,seed_after=c['seed'],delay=0,expected=time)
    else:c['expected']=(time+c['delay'])&0xffffffff
    rows.append(c)
 for bad in ('ready','busy','phase','timing_ready','timing_busy','timing_models','param_marker','aggression','time_coefficient','kind','bank','base','extent','bytes','rng_ready','rng_busy'):
  rows.append(dict(base,bad=bad,fault=1,expected=55,seed_after=base['seed'],calls=0))
 for at,value in ((0,0),(4,2),(6,0),(6,15),(8,12),(10,2),(12,1),(14,1),(16,1),(20,1),(24,1),(26,1),(28,0),(30,1)):
  rows.append(dict(base,patch=at,value=value,fault=1,expected=55,seed_after=base['seed'],calls=0))
 lua=OWNER_LUA[:OWNER_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')]
 lua='local timingbytes='+luav(list(pack(derive(Source(a.source)))))+'\nlocal tablebytes='+luav(list(table))+'\n'+lua.replace(' before={};',SETUP+' before={};').replace('TABLEBYTES',str(len(table))).replace('{{0x414000,18432}','{{0x438800,1792},{sy.VmNativeVariant_Result,8},{sy.SourceModelEntityCopy4086_Lo,4},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x437e00,2560},{0x40c000,12288},{0x414000,18432}')
 lua+=r'''
local beginclock,cost=0,0
emu.addMemoryCallback(function()local st=emu.getState();beginclock=st.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];for _,r in ipairs({{sy.SourceRandom4086_SeedLo,c.seed_after},{sy.SourceRandom4086_CallsLo,(0xffffffff+c.calls)&0xffffffff}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('ATTACKDELAY|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceAttackDelay4086_Status)..'|'..dw(sy.SourceAttackDelay4086_Result)..'|'..dw(sy.SourceRandom4086_SeedLo)..'|'..dw(sy.SourceRandom4086_CallsLo)..'|'..word(sy.SourceAttackDelay4086_Delay)..'|'..(emu.getState().masterClock-beginclock))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 reporter=Reporter('M4-ATTACK-DELAY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceAttackDelay4086_Execute','SourceAttackDelay4086_Ready',0xb604,[(59,0,table)],lua,reporter,batch_size=1,frame_limit=6000)
 actual=[list(map(int,l.split('ATTACKDELAY|',1)[1].split('|')))for l in log.splitlines()if 'ATTACKDELAY|'in l];expected=[[i,0,0,3 if c['fault']else 2,c['expected'],c['seed_after'],(0xffffffff+c['calls'])&0xffffffff]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v[:7]!=e or not c['fault']and v[7]!=c['delay']]
 reporter.check('C lookup identity, actual model timing guards, one actual full32 RNG draw, unsigned time wrap, CPU/stack/VM/CRT/entity retention',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ATTACK_DELAY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_cycles=max((v[8]for v in actual if not rows[v[0]]['fault']),default=None),timing_includes_runtime_interrupts=True,actual_timer_fields_mutated=False,normal_attack_caller_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
