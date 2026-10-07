"""Restore caller context after a child overwrites slots, transferring string ownership."""
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
    for saved_count,live_count,same in [(1,0,False),(2,1,False),(1,2,True),(2,2,True)]:
        rows.append(dict(base,dynamic=saved_count,live_dynamic=live_count,same=same))
    for bad in ('snapshot_ready','table_ready','occupied','crc','payload','frames','slots','reserved','record','saved_handle','live_handle','saved_flags','live_flags','saved_ref','live_ref','aggregate_ref','depth','saved_ip','saved_program','saved_target','saved_frame','saved_slotcount','saved_top'):
        rows.append(dict(base,dynamic=2,live_dynamic=2,same=bad=='aggregate_ref',bad=bad,fault=1))
    ranges=SEGMENTS+[(0x7fc000,8192),(0x7fe100,768),(0x40f000,4096),(0x43fd00,128),(0x7ffb50,528),(0x7fe400,4096)]
    lua='local saved={}\nlocal ranges='+luav([list(x)for x in ranges])+'\nlocal segments='+luav([list(x)for x in SEGMENTS])+'\n'+MATCH_LUA
    setup=r'''
 local c=rows[word(INDEX)+1];set('SourceNativeSnapshot4086_Ready',c.bad=='snapshot_ready'and 0 or 0xb614);set('SourceNativeSnapshot4086_State',0)
 local tail=0x43fd00+(c.depth+1)*16;local dest=0x40f000+(c.depth+1)*512;local cursor=0
 saved={}
 for _,r in ipairs(segments)do for j=0,r[2]-1 do saved[r[1]+j]=emu.read(r[1]+j,mt);emu.write(dest+cursor+j,saved[r[1]+j],mt)end;cursor=cursor+r[2]end
 for j=0,#c.frame_callsites*12-1 do saved[FRAMES+j]=emu.read(FRAMES+j,mt);emu.write(dest+cursor+j,saved[FRAMES+j],mt)end;cursor=cursor+#c.frame_callsites*12
 local slot_start=cursor
 for i,s in ipairs(c.slots)do
  local addr=SLOTS+s*8;put(addr,1,4);put(addr+4,(s*987654321)&0xffffffff,4)
  if i<=c.dynamic then put(addr,6,4);put(addr+4,3);put(addr+6,0x8000)end
  for j=0,7 do saved[addr+j]=emu.read(addr+j,mt);emu.write(dest+cursor+j,saved[addr+j],mt)end;cursor=cursor+8
 end
 put(tail,0xb614);put(tail+2,c.index);put(tail+4,c.snapshot_bytes);put(tail+6,#c.frame_callsites);put(tail+8,#c.slots);put(tail+10,TABLECRC,4);put(tail+14,0)
 for _,r in ipairs(segments)do for j=0,r[2]-1 do emu.write(r[1]+j,(j*31+42)&255,mt)end end
 for j=0,#c.frame_callsites*12-1 do emu.write(FRAMES+j,123,mt)end
 for i,s in ipairs(c.slots)do local addr=SLOTS+s*8;put(addr,1,4);put(addr+4,42,4);if i<=(c.live_dynamic or 0)then put(addr,6,4);put(addr+4,c.same and 3 or 4);put(addr+6,0x8000)end end
 for j=0,63 do put(0x7fe400+j*64,0,1)end
 put(0x7fe400+3*64,2+c.dynamic+(c.same and(c.live_dynamic or 0)or 0),1);put(0x7fe400+4*64,2+(c.live_dynamic or 0),1)
 if c.bad=='table_ready'then set('SourceNativeContinuation4086_Ready',0)end
 if c.bad=='occupied'then put(tail,0)end
 if c.bad=='crc'then put(tail+10,TABLECRC~1,4)end
 if c.bad=='payload'then put(tail+4,c.snapshot_bytes+1)end
 if c.bad=='frames'then put(tail+6,#c.frame_callsites+1)end
 if c.bad=='slots'then put(tail+8,#c.slots+1)end
 if c.bad=='reserved'then put(tail+14,1)end
 if c.bad=='record'then put(tail+2,RECORDS)end
 if c.bad=='saved_handle'then put(dest+slot_start+4,64)end
 if c.bad=='live_handle'then put(SLOTS+c.slots[1]*8+4,64)end
 if c.bad=='saved_flags'then put(dest+slot_start+6,0x8001)end
 if c.bad=='live_flags'then put(SLOTS+c.slots[1]*8+6,0x8001)end
 if c.bad=='saved_ref'then put(0x7fe400+3*64,0,1)end
 if c.bad=='live_ref'then put(0x7fe400+4*64,0,1)end
 if c.bad=='aggregate_ref'then put(0x7fe400+3*64,3,1)end
 if c.bad=='saved_ip'then put(dest+3,65535)end
 if c.bad=='saved_program'then put(dest+111,65535)end
 if c.bad=='saved_target'then put(dest+233,65535)end
 if c.bad=='saved_frame'then put(dest+241,65535)end
 if c.bad=='saved_slotcount'then put(dest+14,c.slots[1])end
 if c.bad=='saved_top'then put(dest+10,65535)end
 if c.bad=='depth'then set('SourceFrameStack4086_Depth',7)end
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
  for addr,value in pairs(saved)do want[addr]=value end
  local tail=0x43fd00+(c.depth+1)*16;want[tail]=0;want[tail+1]=0
  local handle=c.same and 3 or 4;local refaddr=0x7fe400+handle*64;want[refaddr]=before[refaddr]-(c.live_dynamic or 0)
 end
 local changed=0;for addr,value in pairs(want)do if emu.read(addr,mt)~=value then changed=changed+1;if changed<=3 then emu.log('RESTOREMISMATCH|'..word(INDEX)..'|'..addr..'|'..value..'|'..emu.read(addr,mt))end end end
 emu.log('NATIVERESTORE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNativeSnapshot4086_State))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
    lua=lua[:start]+observer+lua[end:];sy=symbols(Path('src/main.sym'))
    import struct
    replacements=dict(TABLEBYTES=len(table),RECORDS=len(records),TABLECRC=struct.unpack_from('<I',table,16)[0],FRAMES=sy['VmFrames_Wram'],SLOTS=sy['VmSlots_Wram'])
    for k,v in replacements.items():lua=lua.replace(k,str(v))
    r=Reporter('M4-NATIVE-SNAPSHOT-RESTORE',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceNativeSnapshot4086_Restore','SourceNativeSnapshot4086_Ready',0xb614,[(60,0,table)],lua,r,batch_size=4)
    actual=[list(map(int,l.split('NATIVERESTORE|',1)[1].split('|')))for l in log.splitlines()if'NATIVERESTORE|'in l]
    expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)]
    r.check('caller context/frame/slot restore after child overwrite; retained strings transferred once; live aliases released; invalid ownership rejects without VM/arena/refcount mutation',actual==expected)
    (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NATIVE_SNAPSHOT_RESTORE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),frame_stack_depth_unchanged=True,native_request_instrumented=True,restore_bound=True,pair_push_bound=False,constructor_execution_bound=False,live_native_api_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
