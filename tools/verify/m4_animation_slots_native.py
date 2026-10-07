"""Release callback temporary slot string ownership before immutable initialization."""
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
    for count in (1,2,16,64):
        for dynamic in (0,1,count):
            for refs in (dynamic, min(255,dynamic+2)):
                rows.append(dict(slots=list(range(10,10+count)),slot_count=count,dynamic=dynamic,refcount=refs,index=0,callback_state=1,depth=0,fault=0,guards=[],program=records[0]['program'],resume_ip=records[0]['resume_ip'],native_id=records[0]['native_id'],callsite=records[0]['callsite'],frame_callsites=records[0]['frame_callsites']))
    base=rows[-1]
    for bad in ('dead','alias_ref','handle_large','handle_flags','range','empty'):
        rows.append(dict(base,bad=bad,fault=1))
    ranges=SEGMENTS+[(0x7fc000,8192),(0x7fe100,768),(0x40f000,4096),(0x43fd00,128),(0x7ffb50,528),(0x7fe400,4096)]
    lua='local ranges='+luav([list(x)for x in ranges])+'\nlocal segments='+luav([list(x)for x in SEGMENTS])+'\n'+MATCH_LUA
    setup=r'''
 local c=rows[word(INDEX)+1];set('SourceAnimationCallback4086_SlotBase',c.bad=='range'and 1023 or 10);set('SourceAnimationCallback4086_Slots',c.bad=='empty'and 0 or c.slot_count)
 for i,s in ipairs(c.slots)do local addr=SLOTS+s*8;put(addr,1,4);put(addr+4,42,4);if i<=c.dynamic then put(addr,6,4);put(addr+4,c.bad=='handle_large'and 64 or 3);put(addr+6,c.bad=='handle_flags'and 0x8001 or 0x8000)end end
 put(0x7fe400+3*64,c.bad=='dead'and 0 or c.bad=='alias_ref'and c.dynamic-1 or c.refcount,1)
'''
    lua=lua.replace(' before={};',setup+' before={};')
    # Replace the admission result observer with byte-exact capture observation.
    start=lua.index('emu.addMemoryCallback(function()\n local st=emu.getState();local ctx=0;')
    end=lua.index("emu.addMemoryCallback(function()\n set('VmState_Status'",start)
    observer=r'''
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local c=rows[word(INDEX)+1];local want={};for addr,value in pairs(before)do want[addr]=value end
 if c.fault==0 then want[0x7fe400+3*64]=c.refcount-c.dynamic end
 local changed=0;for addr,value in pairs(want)do if emu.read(addr,mt)~=value then changed=changed+1;if changed<=3 then emu.log('RELEASEMISMATCH|'..word(INDEX)..'|'..addr..'|'..value..'|'..emu.read(addr,mt))end end end
 emu.log('TEMPORARYRELEASE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..(st['cpu.ps']&1))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
    lua=lua[:start]+observer+lua[end:];sy=symbols(Path('src/main.sym'))
    import struct
    replacements=dict(TABLEBYTES=len(table),RECORDS=len(records),TABLECRC=struct.unpack_from('<I',table,16)[0],FRAMES=sy['VmFrames_Wram'],SLOTS=sy['VmSlots_Wram'])
    for k,v in replacements.items():lua=lua.replace(k,str(v))
    r=Reporter('M4-ANIMATION-SLOTS-RELEASE',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceAnimationSlots4086_Release','SourceAnimationCallback4086_Ready',0xb4e6,[(60,0,table)],lua,r,batch_size=4)
    actual=[list(map(int,l.split('TEMPORARYRELEASE|',1)[1].split('|')))for l in log.splitlines()if'TEMPORARYRELEASE|'in l]
    expected=[[i,0,0,c['fault']]for i,c in enumerate(rows)]
    r.check('temporary slot aliases released exactly once; slots and arena preserved; dead/invalid handles and insufficient ownership reject before pool mutation',actual==expected)
    (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_ANIMATION_SLOTS_RELEASE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),frame_stack_depth_unchanged=True,native_request_instrumented=True,restore_bound=False,pair_push_bound=False,constructor_execution_bound=False,live_native_api_bound=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
