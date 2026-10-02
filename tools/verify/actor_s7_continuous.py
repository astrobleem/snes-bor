"""Opt-in continuation of the SAME private world fixture; no production patch.

Only LDA #4 (observer stop mode) becomes LDA #1. Same instruction length/cost.
No actor state, input, numeric or scheduler semantics are changed.
"""
import json
from actor_s5_entity_fixture import symbols
from actor_s5_isolated import sha

EPOCH=103979218
HORIZON=EPOCH+128*357368-64*4


def offset(a):
    return (a>>16)*32768+(a&65535)-32768


def disable_stop(folder):
    sym=symbols(folder/'world.sym')
    path=folder/'bor.sfc'
    original_sha=sha(path)
    data=bytearray(path.read_bytes())
    a=sym['S6Clock_HostSourceTick'];b=sym['S6Clock_HostSourceTick__done']
    code=data[offset(a):offset(b)]
    needle=bytes.fromhex('a904008f60177e')
    if code.count(needle)==1:
        at=offset(a)+code.index(needle)+1
        data[at]=1
        before=4; after=1
    else:
        # Current fixture revision uses the source-owned stop predicate and
        # BRL continuation: BEQ skips the stop body when no hit is present.
        # Convert that conditional skip to unconditional, preserving every
        # source tick and callback while disabling only the bounded observer
        # stop for a continuation run.
        current=bytes.fromhex('f003822c00')
        assert code.count(current)==1,code.hex()
        at=offset(a)+code.index(current)
        data[at]=0x80
        before='f003822c00'; after='8003822c00'
    path.write_bytes(data)
    (folder/'continuous.json').write_text(json.dumps(dict(original_sha256=original_sha,
        fixture_sha256=sha(path),changed_byte_offset=at,before=before,after=after,
        epoch=EPOCH,horizon_master_clock=HORIZON,physical_fields=128,
        input='neutral: no additional button writes after existing fixture initialization',
        stop='first domain error or first NMI completion at/after horizon; no source-tick stop'),indent=2)+'\n')


def observer(sym,source_tick_horizon=0):
    text='''
local completed=0
local activeTick=false
local preparedTick=0
local consumedTick=0
local preparedID=0
local consumedID=0
local committing=false
local fault=false
local finished=false
local horizonPending=false
local function observe(name,pc)
 local s=emu.getState();local clock=s["masterClock"]
 if clock<103979218 or finished then return end
 if name=="S6Host_Tick" then activeTick=true end
 if name=="S6Host_Tick__return" and activeTick then
  if w(0x7e1764)==0 then completed=w(0x7e173c) end
  activeTick=false
  if SOURCE_TICK_HORIZON>0 and completed>=SOURCE_TICK_HORIZON then
   emu.log(table.concat({"S7CONT","TICK_HORIZON",clock,s["ppu.frameCount"],completed,w(0x7e173c),w(0x7e1772),w(0x7e5023)},"|"))
   horizonPending=true
  end
 end
 if name=="Core_Nmi_Play__do_commit" and horizonPending then emu.write(0x7e1760,4,mt) end
 if name=="Core_Oam_Play__done" and w(0x7e53a2)~=0 then preparedTick=completed;preparedID=preparedID+1 end
 if name=="Core_Nmi_Play__do_commit" then committing=true end
 if name=="Core_Dma_ProcessQueue__done" and committing and w(0x7e53a2)~=0 then consumedTick=preparedTick;consumedID=preparedID end
 local row={"S7CONT",name,clock,s["ppu.frameCount"],s["ppu.scanline"],pc,
 w(0x7e1760),w(0x7e1764),w(0x7e1772),w(0x7e177a),w(0x7e173a),
 tostring(s["cpu.a"]),tostring(s["cpu.ps"]),w(0x7e5023),w(0x7e1772),
 completed,w(0x7e178c),w(0x7e1784)+65536*w(0x7e1786),
 w(0x7e5023),w(0x7e1772),w(0x7e177a),w(0x7e175e),
 preparedTick,consumedTick,preparedID,consumedID,w(0x7e047a),w(0x7e53a2),w(0x7e1764),w(0x7e173a)}
 for slot=0,5 do
  local a=0x7e1900+slot*256
  for _,o in ipairs({0xf6,0xf0,0x70,0xe4,0x06,0xe6,0xfc,0x14,0x16,0x34}) do row[#row+1]=w(a+o) end
 end
 local pending=0
 for a=0x7e0484,0x7e04bc,8 do if (emu.read(a,mt)&64)~=0 then pending=pending+1 end end
 row[#row+1]=pending
 emu.log(table.concat(row,"|"))
 if name=="Core_Nmi_Play__done" then
  committing=false
 local due=w(0x7e173c)
  emu.log(table.concat({"S7DEBT",s["ppu.frameCount"],clock,due,completed,due-completed},"|"))
  emu.log(table.concat({"S7CLOCK",s["ppu.frameCount"],clock,w(0x7e178c),
   w(0x7e1784)+65536*w(0x7e1786),w(0x7e5023),w(0x7e1772),completed},"|"))
  if (SOURCE_TICK_HORIZON>0 and completed>=SOURCE_TICK_HORIZON) or
     (SOURCE_TICK_HORIZON==0 and clock>=HORIZON_VALUE) then
   row[2]="HORIZON";emu.log(table.concat(row,"|"));finished=true
  end
 end
end
'''.replace('HORIZON_VALUE',str(HORIZON)).replace('SOURCE_TICK_HORIZON',str(source_tick_horizon))
    for name in ('S6Host_Tick','S6Host_Tick__return','S6Game_PlayRender__load',
                 'S6Game_PlayRender__tick','S6Game_PlayRender__running',
                 'S6Game_PlayRender__check_error','S6Game_PlayRender__measure',
                 'S6Game_PlayRender__has_elapsed',
                 'S6Game_PlayRender__field','S6Clock_ClockAdvance',
                 'S6Game_PlayRender__return','S7Resident_Flush','Core_Oam_Play__done',
                 'Core_Nmi_Play__do_commit','Core_Dma_ProcessQueue__done','Core_Nmi_Play__done',
                 'Core_Input_Poll','Tad_StreamFrameService','Tad_StreamLatePump','Core_StreamScroll_Play'):
        a=sym[name];o=offset(a)
        text+=f'emu.addMemoryCallback(function() observe("{name}",{a}) end,emu.callbackType.exec,{o},{o},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    # Error writes are observed at their FIRST source instruction. Never clear them.
    for a in [0x1764,0x173a]+[0x19fc+256*s for s in range(6)]:
        text+=f'''emu.addMemoryCallback(function(a,v)
 if v~=0 and not fault and emu.getState()["masterClock"]>=103979218 then
  fault=true;observe("FAULT",a);emu.log("S7CONT|FAULT_VALUE|"..a.."|"..v)
 end
end,emu.callbackType.write,{a},{a+1},emu.cpuType.snes,emu.memType.snesWorkRam)
'''
    return text
