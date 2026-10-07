"""Capture source VM context/slots with atomic dynamic-string ownership."""
import argparse, hashlib, json
from pathlib import Path
from source_native_continuation import unpack, SEGMENTS
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav
from m4_native_continuation_match import LUA as MATCH_LUA
from actor_s5_entity_fixture import symbols

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output','table'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    table=a.table.read_bytes();records,*_=unpack(table);rows=[]
    for i,c in enumerate(records):
        for depth in (0,6):rows.append(dict(c,index=i,callback_state=1,depth=depth,fault=0,guards=[],dynamic=0,refcount=1))
    base=next(c for c in rows if len(c['slots'])>=2)
    for count,ref in [(1,1),(1,254),(2,1),(2,253),(1,0),(1,255),(2,254)]:
        rows.append(dict(base,dynamic=count,refcount=ref,fault=int(ref==0 or ref+count>255)))
    for bad in ('snapshot_ready','occupied','handle_large','handle_flags','request','callback'):
        rows.append(dict(base,dynamic=1,refcount=1,bad=bad,fault=1))
    ranges=SEGMENTS+[(0x7fc000,8192),(0x7fe100,768),(0x40f000,4096),(0x43fd00,128),(0x7ffb50,528),(0x7fe400,4096)]
    lua='local ranges='+luav([list(x)for x in ranges])+'\nlocal segments='+luav([list(x)for x in SEGMENTS])+'\n'+MATCH_LUA
    setup=r'''
 local c=rows[word(INDEX)+1];set('SourceNativeSnapshot4086_Ready',c.bad=='snapshot_ready'and 0 or 0xb614);set('SourceNativeSnapshot4086_State',0)
 local tail=0x43fd00+(c.depth+1)*16;put(tail,c.bad=='occupied'and 0xb614 or 0)
 for i,s in ipairs(c.slots)do local addr=SLOTS+s*8;put(addr,1,4);put(addr+4,(s*987654321)&0xffffffff,4)end
 for j=1,c.dynamic do local addr=SLOTS+c.slots[j]*8;put(addr,6,4);put(addr+4,c.bad=='handle_large'and 64 or 3);put(addr+6,c.bad=='handle_flags'and 0x8001 or 0x8000)end
 put(0x7fe400+3*64,c.refcount,1)
 if c.bad=='request'then set('SourceNativeContinuation4086_Request',0)end
 if c.bad=='callback'then set('SourceAnimationCallback4086_State',3)end
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
  expect(tail,0xb614);expect(tail+2,c.index);expect(tail+4,c.snapshot_bytes);expect(tail+6,#c.frame_callsites);expect(tail+8,#c.slots);expect(tail+10,TABLECRC,4);expect(tail+14,0)
  want[0x7fe400+3*64]=c.refcount+c.dynamic
 end
 local changed=0;for addr,value in pairs(want)do if emu.read(addr,mt)~=value then changed=changed+1;if changed<=3 then emu.log('CAPTUREMISMATCH|'..word(INDEX)..'|'..addr..'|'..value..'|'..emu.read(addr,mt))end end end
 emu.log('NATIVECAPTURE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNativeSnapshot4086_State))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
    lua=lua[:start]+observer+lua[end:];sy=symbols(Path('src/main.sym'))
    import struct
    replacements=dict(TABLEBYTES=len(table),RECORDS=len(records),TABLECRC=struct.unpack_from('<I',table,16)[0],FRAMES=sy['VmFrames_Wram'],SLOTS=sy['VmSlots_Wram'])
    for k,v in replacements.items():lua=lua.replace(k,str(v))
    r=Reporter('M4-NATIVE-SNAPSHOT-CAPTURE',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceNativeSnapshot4086_Capture','SourceNativeSnapshot4086_Ready',0xb614,[(60,0,table)],lua,r,batch_size=4)
    actual=[list(map(int,l.split('NATIVECAPTURE|',1)[1].split('|')))for l in log.splitlines()if'NATIVECAPTURE|'in l]
    expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)]
    r.check('all source-native context/frame/slot snapshots; selected free row only; dynamic retain aliases; saturation/stale/invalid inputs reject before arena/refcount mutation',actual==expected)
    (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NATIVE_SNAPSHOT_CAPTURE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),frame_stack_depth_unchanged=True,native_request_instrumented=True,restore_bound=False,pair_push_bound=False,constructor_execution_bound=False,live_native_api_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
