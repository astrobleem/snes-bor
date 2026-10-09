"""Bounded VM-tail state lease, exact integer storage and collision guards."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_foreign_slot_tail import derive_plan
from source_player_state_native import emit
from compiler import Source
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

WORK=0x7fa000
ASM='''
StateProbe:
.a16
.i16
 php
 pha
 sed
 lda.l W+24
 beq StateProbe_Init
 cmp #1
 beq StateProbe_Write
 cmp #2
 beq StateProbe_Birth
 cmp #3
 beq StateProbe_Release
 jsl SourcePlayerState_Read
 bra StateProbe_Return
StateProbe_Init:
 jsl SourcePlayerState_Init
 bra StateProbe_Return
StateProbe_Write:
 jsl SourcePlayerState_Write
 bcs StateProbe_Return
 jsl SourcePlayerState_Read
 bra StateProbe_Return
StateProbe_Birth:
 jsl SourcePlayerState_ClearBirth
 bcs StateProbe_Return
 jsl SourcePlayerState_Read
 bra StateProbe_Return
StateProbe_Release:
 jsl SourcePlayerState_Release
StateProbe_Return:
 nop
 bcs StateProbe_Bad
 pla
 plp
 clc
 rtl
StateProbe_Bad:
 pla
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before,cpu={},{ };local context=0;local decimal=0;local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function long(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);context=0;decimal=0
 for j=0,63 do emu.write(WORK+j,0,mt)end
 for j=0,8191 do emu.write(0x7fc000+j,(j*13+91)&255,mt)end
 for j=0,15 do emu.write(0x7fe000+j,0x5a,mt)end
 put(WORK,c.op==0 and 0 or 0xb67b);put(WORK+4,c.slot);put(WORK+6,c.field)
 put(WORK+8,0x12345678,4);put(WORK+12,SLOTCOUNT);put(WORK+14,0x12345678,4)
 put(WORK+20,c.value,4);put(WORK+24,c.op)
 put(sy.VmState_SlotCount,SLOTCOUNT);put(sy.VmState_FrameTop,0);put(sy.SourceVMRun4086_Busy,0);put(sy.VmState_Status,4,1)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128)
 if c.bad=='owner'then put(WORK,0)
 elseif c.bad=='generation_low'then put(WORK+8,0)
 elseif c.bad=='generation_high'then put(WORK+10,0)
 elseif c.bad=='saved_count'then put(WORK+12,SLOTCOUNT-1)
 elseif c.bad=='loaded_count'then put(sy.VmState_SlotCount,SLOTCOUNT+1)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4001)
 elseif c.bad=='zero_count'then put(sy.VmSourceWorld_Count,0)
 elseif c.bad=='large_count'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='slot'then put(WORK+4,128)
 elseif c.bad=='field'then put(WORK+6,6)
 elseif c.bad=='zero_generation'then put(WORK+8,0,4)
 elseif c.bad=='reinit'then put(WORK,0xb67b)
 elseif c.bad=='busy'then put(sy.SourceVMRun4086_Busy,1)
 elseif c.bad=='frames'then put(sy.VmState_FrameTop,1)
 elseif c.bad=='running'then put(sy.VmState_Status,2,1)
 elseif c.bad=='yielded'then put(sy.VmState_Status,3,1)end
 before={};for j=0,8191 do before[0x7fc000+j]=emu.read(0x7fc000+j,mt)end
 for j=0,15 do before[0x7fe000+j]=emu.read(0x7fe000+j,mt)end
 local s=emu.getState();start=s.masterClock;cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if emu.getState()['cpu.ps']&8==0 then decimal=decimal+1 end
end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'a','x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then context=context+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then context=context+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local row=TAIL+c.slot*24;local changed=0;local readbad=0
 for a,v in pairs(before)do
  local expected=v
  if c.fault==0 then
   if c.op==0 and a>=TAIL and a<TAIL+STATEBYTES then expected=0
   elseif c.op==2 and a>=row and a<row+24 then expected=0
   elseif c.op==1 and a>=row+c.field*4 and a<row+c.field*4+4 then expected=(c.value>>(8*(a-row-c.field*4)))&255 end
  end
  if emu.read(a,mt)~=expected then changed=changed+1 end
 end
 if c.fault==0 and(c.op==1 or c.op==2 or c.op==4)then
  for j=0,23 do if emu.read(WORK+32+j,mt)~=emu.read(row+j,mt)then readbad=readbad+1 end end
 end
 emu.log('PLAYERSTATENATIVE|'..word(INDEX)..'|'..word(WORK+2)..'|'..word(WORK)..'|'..changed..'|'..readbad..'|'..context..'|'..decimal..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();plan=derive_plan(Source(a.source));sy=symbols(Path('src/main.sym'))
    rows=[];values=(-2147483648,2147483647,-1,0,65536,-2147483647)
    for slot in range(128):
        for field in range(6):rows.append(dict(op=1,slot=slot,field=field,value=values[(slot+field)%6],bad='',fault=0))
        rows.append(dict(op=2,slot=slot,field=0,value=0,bad='',fault=0))
    for op in (0,3,4):rows.append(dict(op=op,slot=127,field=0,value=0,bad='',fault=0))
    for op,bads in ((4,('owner','generation_low','generation_high','saved_count','loaded_count','world','pool','zero_count','large_count','slot')),
                    (1,('field',)),(0,('zero_generation','reinit','loaded_count','busy','frames','running','yielded')),
                    (3,('busy','frames','running','yielded'))):
        for bad in bads:rows.append(dict(op=op,slot=127,field=0,value=1,bad=bad,fault=1))
    reporter=Reporter('M4-PLAYER-STATE-NATIVE',kind='GATE');out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    lua=LUA
    for k,v in dict(WORK=WORK,TAIL=plan['base'],STATEBYTES=plan['entity_state_bytes'],SLOTCOUNT=plan['live_slot_count']).items():lua=lua.replace(k,str(v))
    raw,log=run_fixture(a.rom,out,rows,'StateProbe','SourceAnimationInit4086_Ready',0xb4ec,[],lua,reporter,
                        append=ASM.replace('W+',str(WORK)+'+')+emit(plan,WORK,sy),probes=dict(RETURN='StateProbe_Return'),
                        batch_size=16,frame_limit=2000,link_pcm=False)
    actual=[list(map(int,line.split('PLAYERSTATENATIVE|',1)[1].strip().split('|')))for line in log.splitlines()if 'PLAYERSTATENATIVE|'in line]
    errors=[]
    for i,row in enumerate(actual):
        c=rows[i];ready=0 if c['op']==3 and not c['fault']else 0xb67b if c['op']==0 and not c['fault']else None
        if row[:2]!=[i,3 if c['fault']else 2]or any(row[3:7])or ready is not None and row[2]!=ready:errors.append(dict(case=i,input=c,actual=row))
    reporter.check('exact integer rows, birth clearing, release, all live VM slots/guard/sibling bytes and CPU retained',len(actual)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_PLAYER_STATE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),observed_cases=len(actual),guards=sum(c['fault']for c in rows),errors=errors[:8],
                rom_sha256=hashlib.sha256(raw).hexdigest(),plan=plan,peak_master_clocks=max((v[7]for v in actual),default=0),
                integer_storage_lossless=True,live_vm_slots_preserved=True,all_sibling_state_bytes_preserved=True,
                loaded_module_count_instrumented=True,production_vm_loader_bound=False,production_birth_binding=False,
                production_property_binding=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
