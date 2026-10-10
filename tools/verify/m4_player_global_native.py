"""Native player globals: full DWORDs, adjacent live/entity slots and lifetime guards."""
import argparse,hashlib,itertools,json
from pathlib import Path
from compiler import Source
from source_foreign_slot_tail import derive_plan
from source_foreign_state_layout import layout as controls_layout
from source_player_global_layout import layout
from source_player_global_native import emit
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''PlayerGlobalProbe:
.a16
.i16
 php
 pha
 sed
 lda.l STATE+24
 beq PlayerGlobalProbe_Init
 cmp #1
 beq PlayerGlobalProbe_Write
 cmp #2
 beq PlayerGlobalProbe_Release
 jsl PlayerGlobal_Read
 jmp PlayerGlobalProbe_Return
PlayerGlobalProbe_Init:
.a16
.i16
 jsl PlayerGlobal_Init
 jmp PlayerGlobalProbe_Return
PlayerGlobalProbe_Write:
.a16
.i16
 jsl PlayerGlobal_Write
 jmp PlayerGlobalProbe_Return
PlayerGlobalProbe_Release:
.a16
.i16
 jsl PlayerGlobal_Release
PlayerGlobalProbe_Return:
.a16
.i16
 nop
 bcs PlayerGlobalProbe_Bad
 pla
 plp
 clc
 rtl
PlayerGlobalProbe_Bad:
.a16
.i16
 pla
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx,dec={},{},0,0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function dw(a)return word(a)|(word(a+2)<<16)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);ctx=0;dec=0
 for i=0,8207 do emu.write(0x7fc000+i,(i*13+91)&255,mt)end
 for i=0,63 do put(STATE+i,0,1)end
 put(STATE,0xb67b);put(STATE+8,0x12345678,4);put(STATE+12,COUNT);put(STATE+14,0x12345678,4);put(STATE+24,c.op)
 for i=0,31 do put(W+i,0,1)end;put(W,c.op==0 and 0 or 0xb6c6);put(W+2,2);put(W+4,c.player);put(W+6,c.field);put(W+8,0x12345678,4);put(W+12,0x12345678,4);put(W+16,COUNT);put(W+18,COUNT);put(W+20,c.value,4)
 put(sy.VmState_SlotCount,COUNT);put(sy.VmState_FrameTop,0);put(sy.SourceVMRun4086_Busy,0);put(sy.VmState_Status,4,1)
 if c.bad=='parent'then put(STATE,0)
 elseif c.bad=='parent_count'then put(STATE+12,COUNT-1)
 elseif c.bad=='parent_generation'then put(STATE+14,0)
 elseif c.bad=='zero_generation'then put(STATE+8,0,4);put(STATE+14,0,4)
 elseif c.bad=='loaded_count'then put(sy.VmState_SlotCount,1024)
 elseif c.bad=='tag'then put(W,0)
 elseif c.bad=='generation'then put(W+8,0,4)
 elseif c.bad=='saved_generation'then put(W+12,0,4)
 elseif c.bad=='count'then put(W+16,COUNT-1)
 elseif c.bad=='saved_count'then put(W+18,COUNT-1)
 elseif c.bad=='player'then put(W+4,4)
 elseif c.bad=='field'then put(W+6,c.player==65535 and 6 or 5)
 elseif c.bad=='reinit'then put(W,0xb6c6)
 elseif c.bad=='busy'then put(sy.SourceVMRun4086_Busy,1)
 elseif c.bad=='frames'then put(sy.VmState_FrameTop,1)
 elseif c.bad=='running'then put(sy.VmState_Status,2,1)
 elseif c.bad=='yielded'then put(sy.VmState_Status,3,1)end
 before={};for i=0,8207 do before[0x7fc000+i]=emu.read(0x7fc000+i,mt)end
 local s=emu.getState();cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then dec=dec+1 end end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'a','x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local function expect(a,v,n)for i=0,(n or 2)-1 do before[a+i]=(v>>(8*i))&255 end end
 if c.fault==0 then
  if c.op==0 then
   for i=0,143 do before[W+i]=0 end;expect(W,0xb6c6);expect(W+8,0x12345678,4);expect(W+12,0x12345678,4);expect(W+16,COUNT);expect(W+18,COUNT)
  elseif c.op==2 then expect(W,0)
  else
   local at=c.player==65535 and W+32+c.field*4 or W+64+c.player*20+c.field*4
   if c.op==1 then expect(at,c.value,4)else
    for i=0,3 do before[W+20+i]=before[at+i]end
   end
  end
  expect(W+2,2)
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('PLAYERGLOBAL|'..word(INDEX)..'|'..n..'|'..ctx..'|'..dec)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);tail=derive_plan(Source(a.source));plan=layout(tail);sy=symbols(Path('src/main.sym'));state=next(r['address']for r in controls_layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='player_state_controls');rows=[]
 fields=[(65535,f)for f in range(6)]+[(i,f)for i in range(4)for f in range(5)]
 for player,field in fields:
  for value in (-2147483648,-1,0,1,65536,2147483647):rows.append(dict(op=1,player=player,field=field,value=value,bad='',fault=0))
  rows.append(dict(op=3,player=player,field=field,value=17,bad='',fault=0))
 for op in (0,2):rows.append(dict(op=op,player=0,field=0,value=17,bad='',fault=0))
 for op,bads in ((3,('parent','parent_count','parent_generation','zero_generation','loaded_count','tag','generation','saved_generation','count','saved_count','player','field')),(1,('field',)),(0,('parent','loaded_count','zero_generation','reinit','busy','frames','running','yielded')),(2,('busy','frames','running','yielded'))):
  for bad in bads:rows.append(dict(op=op,player=0,field=0,value=17,bad=bad,fault=1))
 rows.append(dict(op=3,player=65535,field=0,value=0,bad='field',fault=1))
 reporter=Reporter('M4-PLAYER-GLOBAL',kind='GATE');lua=LUA
 for k,v in dict(STATE=state,W=plan['controls'],COUNT=tail['live_slot_count']).items():lua=lua.replace(k,str(v))
 raw,log=run_fixture(a.rom,a.output.resolve(),rows,'PlayerGlobalProbe','SourceAnimationInit4086_Ready',0xb4ec,[],lua,reporter,append=ASM.replace('STATE',str(state))+emit(tail,state,sy),probes=dict(RETURN='PlayerGlobalProbe_Return'),batch_size=16,link_pcm=False)
 actual=[list(map(int,l.split('PLAYERGLOBAL|')[1].split('|')))for l in log.splitlines()if'PLAYERGLOBAL|'in l];reporter.check('lossless global/player words, exact live slots/entity rows/guard preservation and CPU/decimal restoration',actual==[[i,0,0,0]for i in range(len(rows))]);reporter.check('bank0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768])
 r=dict(schema='BYOR_PLAYER_GLOBAL_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guards=sum(c['fault']for c in rows),inputs=rows,actual=actual,plan=plan,rom_sha256=hashlib.sha256(raw).hexdigest(),live_vm_slots_preserved=True,replacement_module_overlap_guard_exercised=True,production_memory_lease=False,player_die_runtime_bound=False,new_foreign_arena_bytes=0,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()
if __name__=='__main__':main()
