"""Pair parent frame and retained VM rows across an instrumented child callback."""
import argparse, hashlib, json
from pathlib import Path
from source_native_continuation import unpack, SEGMENTS
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav
from m4_native_continuation_match import LUA as MATCH_LUA
from actor_s5_entity_fixture import symbols

WRAPPER=r'''
NativePairFixture:
.a16
.i16
 php
 rep #$38
 jsl PUSHNATIVE
 bcs NativePairFixtureBad
NativePairChildSetup:
.a16
.i16
 nop
 jsl RELEASETEMP
 bcs NativePairFixtureBad
NativePairChildOverwrite:
.a16
.i16
 nop
 jsl POPPAIR
 bcs NativePairFixtureBad
 plp
 clc
 rtl
NativePairFixtureBad:
.a16
.i16
 plp
 sec
 rtl
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output','table'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    table=a.table.read_bytes();records,*_=unpack(table);rows=[]
    for i,c in enumerate(records):
        for depth in (0,6):rows.append(dict(c,index=i,callback_state=1,depth=depth,fault=0,guards=[],dynamic=0,refcount=1))
    base=next(c for c in rows if len(c['slots'])>=2)
    for depth in (0,2,4,6):rows.append(dict(base,depth=depth,dynamic=2,refcount=2))
    ranges=SEGMENTS+[(0x7fc000,8192),(0x7fe100,768),(0x40f000,4096),(0x43fd00,128),(0x7ffb50,528),(0x7fe400,4096)]
    lua='local ranges='+luav([list(x)for x in ranges])+'\nlocal segments='+luav([list(x)for x in SEGMENTS])+'\n'+MATCH_LUA
    setup=r'''
 local c=rows[word(INDEX)+1];set('SourceNativeSnapshot4086_Ready',0xb614);set('SourceNativeSnapshot4086_State',0)
 for _,k in ipairs({'SourceFrameMotion4086_Ready','SourceAnimationInit4086_Ready','SourceModelAnimation4086_Ready','SourceModelTransition4086_Ready','SourceFrameEffectPlan4086_Ready','SourceSelf4086_Ready'})do set(k,0)end
 local tail=0x43fd00+(c.depth+1)*16;put(tail,0)
 for j=0,1023 do put(SLOTS+j*8,1,4);put(SLOTS+j*8+4,j,4)end
 for j=1,c.dynamic do local addr=SLOTS+c.slots[j]*8;put(addr,6,4);put(addr+4,3);put(addr+6,0x8000)end
 for j=0,63 do put(0x7fe400+j*64,0,1)end
 put(0x7fe400+3*64,c.refcount,1)
'''
    lua=lua.replace(' before={};',setup+' before={};')
    # Replace the admission result observer with byte-exact capture observation.
    start=lua.index('emu.addMemoryCallback(function()\n local st=emu.getState();local ctx=0;')
    end=lua.index("emu.addMemoryCallback(function()\n set('VmState_Status'",start)
    observer=r'''
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local c=rows[word(INDEX)+1];local want={};for addr,value in pairs(before)do want[addr]=value end
 if c.fault==0 then
  local dest=0x40f000+(c.depth+1)*512;local cursor=0
  for _,r in ipairs(segments)do for j=0,r[2]-1 do want[dest+cursor+j]=before[r[1]+j]end;cursor=cursor+r[2]end
  for j=0,#c.frame_callsites*12-1 do want[dest+cursor+j]=before[FRAMES+j]end;cursor=cursor+#c.frame_callsites*12
  for _,s in ipairs(c.slots)do for j=0,7 do want[dest+cursor+j]=before[SLOTS+s*8+j]end;cursor=cursor+8 end
  local function expect(addr,value,n)for j=0,(n or 2)-1 do want[addr+j]=(value>>(8*j))&255 end end
  local tail=0x43fd00+(c.depth+1)*16
  expect(tail,0);expect(tail+2,c.index);expect(tail+4,c.snapshot_bytes);expect(tail+6,#c.frame_callsites);expect(tail+8,#c.slots);expect(tail+10,TABLECRC,4);expect(tail+14,0)
  want[0x7fe400+3*64]=c.refcount
  local parent=0x40f000+c.depth*512;for j=0,511 do want[parent+j]=before[0x7ffb50+j]end
  local ptail=0x43fd00+c.depth*16;for j=0,15 do want[ptail+j]=before[0x7ffd50+j]end
 end
 local changed=0;for addr,value in pairs(want)do if emu.read(addr,mt)~=value then changed=changed+1;if changed<=3 then emu.log('PAIRMISMATCH|'..word(INDEX)..'|'..addr..'|'..value..'|'..emu.read(addr,mt))end end end
 emu.log('NATIVEPAIR|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNativeSnapshot4086_State)..'|'..word(sy.SourceFrameStack4086_Depth)..'|'..word(sy.SourceFrameStack4086_Fault))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
    child=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];set('SourceAnimationCallback4086_SlotBase',c.slots[1]);set('SourceAnimationCallback4086_Slots',c.slots[#c.slots]-c.slots[1]+1)
end,emu.callbackType.exec,CHILDSETUP,CHILDSETUP,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for _,r in ipairs(segments)do for j=0,r[2]-1 do emu.write(r[1]+j,42,mt)end end
 for j=0,#c.frame_callsites*12-1 do emu.write(FRAMES+j,42,mt)end
 for _,s in ipairs(c.slots)do put(SLOTS+s*8,1,4);put(SLOTS+s*8+4,42,4)end
 if c.dynamic>0 then for j=1,2 do put(SLOTS+c.slots[j]*8,6,4);put(SLOTS+c.slots[j]*8+4,4);put(SLOTS+c.slots[j]*8+6,0x8000)end;put(0x7fe400+4*64,2,1)end
 set('SourceVMRun4086_Busy',0);set('VmState_Status',4,1);set('VmSourceCallback_Active',0);set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_State',3);set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',2);set('SourceUpdateFrame4086_Pending',0)
 for _,k in ipairs({'SourceAnimationInit4086_Ready','SourceModelAnimation4086_Ready','SourceModelTransition4086_Ready','SourceFrameEffectPlan4086_Ready','SourceSelf4086_Ready'})do set(k,0)end
end,emu.callbackType.exec,CHILDOVERWRITE,CHILDOVERWRITE,emu.cpuType.snes,mt)
'''
    lua=lua[:start]+observer+lua[end:]+child;sy=symbols(Path('src/main.sym'))
    import struct
    replacements=dict(TABLEBYTES=len(table),RECORDS=len(records),TABLECRC=struct.unpack_from('<I',table,16)[0],FRAMES=sy['VmFrames_Wram'],SLOTS=sy['VmSlots_Wram'])
    for k,v in replacements.items():lua=lua.replace(k,str(v))
    r=Reporter('M4-NATIVE-PAIR-ROUNDTRIP',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'NativePairFixture','SourceNativeSnapshot4086_Ready',0xb614,[(60,0,table)],lua,r,batch_size=4,append=WRAPPER,bindings={'PUSHNATIVE':'SourceFrameStack4086_PushNative','RELEASETEMP':'SourceAnimationSlots4086_Release','POPPAIR':'SourceNativeSnapshot4086_PopPair'},probes={'CHILDSETUP':'NativePairChildSetup','CHILDOVERWRITE':'NativePairChildOverwrite'})
    actual=[list(map(int,l.split('NATIVEPAIR|',1)[1].split('|')))for l in log.splitlines()if'NATIVEPAIR|'in l]
    expected=[[i,0,0,2,c['depth'],0]for i,c in enumerate(rows)]
    r.check('all source-native parent/VM paired roundtrips; actual temporary release; child context/slot overwrite; retained dynamic aliases transferred; depth restored; snapshot consumed',actual==expected)
    (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NATIVE_PAIR_ROUNDTRIP_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),frame_stack_depth_unchanged=True,native_request_instrumented=True,child_callback_body_instrumented=True,restore_bound=True,pair_push_bound=True,constructor_execution_bound=False,live_native_api_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
