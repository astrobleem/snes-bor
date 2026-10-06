"""Execute source quake/jump/reactive leaves and their exact cursor acknowledgement."""
import argparse, hashlib, json, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_frame_effects_4086 import ANIMATION_FIELDS, pack, unpack
from source_update_frame_authority import events
from source_frame_effect_plan import derive
from _harness import Reporter
from _source_leaf_fixture import run_fixture


def inputs(authority, authored, table):
    rows=[];seen=set()
    synthetic=pack(dict(models=['dust','effect'],animations=[dict(handle=1,events=events(),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6),dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=8)])]))
    for ar in authority['results']:
        c=ar['case'];state=ar['actual']['state'];trace=ar['actual']['trace']
        # Empty trace can be a valid nonanimating frame 0. Callback interruption
        # is the sole early escape; killed entities still complete their effects.
        if c['f']>1 or c['animating'] and c['mode'] in (1,2):continue
        key=(c['mode'],c['level'],c['f'],int(state[3]))
        if key in seen:continue
        seen.add(key)
        for op in ([17,19,22] if c['f']==1 else [17]):
            rows.append(dict(origin='PINNED_C',mode=c['mode'],level=c['level'],f=c['f'],direction=int(state[3]),handle=1,animation_data=0x8000+32000+24,base=0x8000+32000,bytes=len(synthetic),count=int(c['f']==1),op=op,wanted=[int(state[8]),int(state[9]),int(state[10]*65536),int(state[11]*65536),int(state[16])]))
    plan=derive(authored);decoded=unpack(table)
    for animation, schedule in zip(decoded['animations'],plan['animations']):
        at=struct.unpack_from('<4H',table,16+8*(animation['handle']-1))[2]
        e=animation['events']
        for frame in schedule['frames']:
            for op in frame['ops']:
                if op not in (17,19,22):continue
                counts=range(max(1,e['quake_repeat'])) if op==17 and e['quake_repeat'] else (0,)
                for count in counts:
                    f=frame['index'];q=99;nextcount=count
                    if e['quake_start']+count==f:
                        q=e['quake_value'] if count%2 or e['quake_value']>0 else -e['quake_value']
                        nextcount=count+1 if e['quake_repeat']-count>1 else 0
                    rows.append(dict(origin='AUTHORED',mode=0,level=1,f=f,direction=1,handle=animation['handle'],animation_data=0x8000+at,base=0x8000,bytes=len(table),count=count,op=op,wanted=[q,nextcount,e['jump_x'],e['jump_z'],1]))
    for i,row in enumerate(rows):row.update(slot=(0,1,127)[i%3],fault=0,bad='')
    base=next(r for r in rows if r['op']==17 and r['level']==1 and r['f']==0)
    for bad in ('ready','prefix','prefix_state','prefix_pending','cursor','cursor_state','stale_slot','stale_handle','stale_frame','world','pool','side','count','slot','handle','bank','base','bounds','view','cursor_count','cursor_index','cursor_bank','cursor_base','cursor_bytes','negative_count','unsupported'):
        rows.append(dict(base,fault=1,bad=bad))
    jump=next(r for r in rows if r['op']==19 and r['direction']==0)
    rows.append(dict(jump,fault=1,bad='jump_negation'))
    reactive=next(r for r in rows if r['op']==22)
    rows.append(dict(reactive,fault=1,bad='flags'))
    # Undefined signed C arithmetic is rejected before live writes.
    for bad in ('start_overflow','repeat_overflow','quake_negation'):
        rows.append(dict(base,fault=1,bad=bad))
    return rows,synthetic


LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0;local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function long(a,v)put(a,v&65535);put(a+2,(v>>16)&65535)end
local function set(p,k,v)put(sy[p..k],v)end
local ranges={{0x414000,10240},{0x416800,8192},{0x43eaf0,5392},{0x7ffe30,4}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local f=0x43eb00+32*c.slot;local q=0x43fb00+4*(c.handle-1)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 long(v+28,c.direction);long(s+36,0);long(s+40,0);long(f+16,0);long(q,c.count);long(sy.SourceFrameEffectLeaf4086_LevelQuakeLo,99)
 -- Current model/animation deliberately differ from the captured owner.
 put(s,15);put(s+4,79);put(s+6,65535)
 set('SourceFrameEffectLeaf4086_','Ready',0xb4f4);set('SourceIdle4086_','Ready',0xb4f3)
 set('SourceUpdateFrame4086_','Ready',0xb4e3);set('SourceUpdateFrame4086_','State',1);set('SourceUpdateFrame4086_','Pending',2);set('SourceUpdateFrame4086_','Slot',c.slot);set('SourceUpdateFrame4086_','Handle',c.handle);set('SourceUpdateFrame4086_','Request',c.f);set('SourceUpdateFrame4086_','View',0x4000+80*c.slot)
 set('SourceUpdateFrame4086_','Bank',60);set('SourceUpdateFrame4086_','Base',c.base);set('SourceUpdateFrame4086_','Bytes',c.bytes);set('SourceUpdateFrame4086_','AnimationData',c.animation_data);set('SourceUpdateFrame4086_','Animations',80)
 set('SourceFrameEffectPlan4086_','Ready',0xb4f2);set('SourceFrameEffectPlan4086_','State',1);set('SourceFrameEffectPlan4086_','Service',c.op);set('SourceFrameEffectPlan4086_','Acknowledged',0);set('SourceFrameEffectPlan4086_','Slot',c.slot);set('SourceFrameEffectPlan4086_','Handle',c.handle);set('SourceFrameEffectPlan4086_','Frame',c.f);set('SourceFrameEffectPlan4086_','Index',0);set('SourceFrameEffectPlan4086_','Count',2)
 set('SourceFrameEffectPlan4086_','Bank',59);set('SourceFrameEffectPlan4086_','Base',0x8000);set('SourceFrameEffectPlan4086_','Bytes',6);set('SourceFrameEffectPlan4086_','Pool',c.op==17 and 0 or c.op==19 and 2 or 4)
 set('VmSourceWorld_','Ready',0xb4a3);set('VmSourceWorld_','PoolBase',0x4000);set('VmSourceWorld_','SideBase',0x6800);set('VmSourceWorld_','Count',128);set('VmSourceWorld_','Level',c.level);put(EXPECTFAULT,c.fault)
 if c.bad=='ready'then set('SourceFrameEffectLeaf4086_','Ready',0)
 elseif c.bad=='prefix'then set('SourceUpdateFrame4086_','Ready',0)
 elseif c.bad=='prefix_state'then set('SourceUpdateFrame4086_','State',2)
 elseif c.bad=='prefix_pending'then set('SourceUpdateFrame4086_','Pending',1)
 elseif c.bad=='cursor'then set('SourceFrameEffectPlan4086_','Ready',0)
 elseif c.bad=='cursor_state'then set('SourceFrameEffectPlan4086_','State',2)
 elseif c.bad=='stale_slot'then set('SourceFrameEffectPlan4086_','Slot',c.slot+1)
 elseif c.bad=='stale_handle'then set('SourceFrameEffectPlan4086_','Handle',c.handle+1)
 elseif c.bad=='stale_frame'then set('SourceFrameEffectPlan4086_','Frame',c.f+1)
 elseif c.bad=='world'then set('VmSourceWorld_','Ready',0)
 elseif c.bad=='pool'then set('VmSourceWorld_','PoolBase',0x4002)
 elseif c.bad=='side'then set('VmSourceWorld_','SideBase',0x6802)
 elseif c.bad=='count'then set('VmSourceWorld_','Count',129)
 elseif c.bad=='slot'then set('SourceUpdateFrame4086_','Slot',128);set('SourceFrameEffectPlan4086_','Slot',128)
 elseif c.bad=='handle'then set('SourceUpdateFrame4086_','Handle',129);set('SourceFrameEffectPlan4086_','Handle',129)
 elseif c.bad=='bank'then set('SourceUpdateFrame4086_','Bank',64)
 elseif c.bad=='base'then set('SourceUpdateFrame4086_','Base',0x7ffe)
 elseif c.bad=='bounds'then set('SourceUpdateFrame4086_','Bytes',100)
 elseif c.bad=='view'then set('SourceUpdateFrame4086_','View',0x4002)
 elseif c.bad=='cursor_count'then set('SourceFrameEffectPlan4086_','Count',1)
 elseif c.bad=='cursor_index'then set('SourceFrameEffectPlan4086_','Index',1)
 elseif c.bad=='cursor_bank'then set('SourceFrameEffectPlan4086_','Bank',64)
 elseif c.bad=='cursor_base'then set('SourceFrameEffectPlan4086_','Base',0x7ffe)
 elseif c.bad=='cursor_bytes'then set('SourceFrameEffectPlan4086_','Bytes',0)
 elseif c.bad=='negative_count'then long(q,-1)
 elseif c.bad=='unsupported'then set('SourceFrameEffectPlan4086_','Service',7)
 elseif c.bad=='flags'then set('SourceIdle4086_','Ready',0)
 elseif c.bad=='start_overflow'then long(q,2147483647);set('SourceUpdateFrame4086_','AnimationData',0xfe00)
 elseif c.bad=='repeat_overflow'then long(q,1);set('SourceUpdateFrame4086_','Request',1);set('SourceFrameEffectPlan4086_','Frame',1);set('SourceUpdateFrame4086_','AnimationData',0xfe80)
 elseif c.bad=='quake_negation'then set('SourceUpdateFrame4086_','AnimationData',0xff00)
 elseif c.bad=='jump_negation'then set('SourceUpdateFrame4086_','AnimationData',0xff80)end
 if c.bad=='start_overflow' or c.bad=='repeat_overflow' or c.bad=='quake_negation' or c.bad=='jump_negation'then set('SourceUpdateFrame4086_','Base',0x8000);set('SourceUpdateFrame4086_','Bytes',32768)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();start=s.masterClock;ctx=0;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('EFFECTLEAFCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local w=c.wanted
 local function expect(a,n)for i=0,3 do before[a+i]=(n>>(8*i))&255 end end
 if c.fault==0 then
  if c.op==17 then expect(0x43fb00+4*(c.handle-1),w[2]);expect(sy.SourceFrameEffectLeaf4086_LevelQuakeLo,w[1])
  elseif c.op==19 then expect(0x416800+64*c.slot+36,w[3]);expect(0x416800+64*c.slot+40,w[4])
  elseif c.op==22 then expect(0x43eb00+32*c.slot+16,1)end
 end
 local mismatch=0;for addr,value in pairs(before)do if emu.read(addr,mt)~=value then mismatch=mismatch+1 end end
 local ack=0;if c.fault==0 and (word(sy.SourceFrameEffectPlan4086_Index)~=1 or word(sy.SourceFrameEffectPlan4086_Service)~=23 or word(sy.SourceFrameEffectPlan4086_State)~=1 or word(sy.SourceFrameEffectPlan4086_Acknowledged)~=0)then ack=1 end
 emu.log('EFFECTLEAFRESULT|'..word(INDEX)..'|'..word(sy.SourceFrameEffectLeaf4086_Status)..'|'..mismatch..'|'..ctx..'|'..ack)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['functions_sha256']!='72d75ee216c7c00ceb01f6f811b77184dda3a8f22f0174b7f0be6e35205183d7':raise ValueError('FRAME_EFFECT_C_AUTHORITY')
    source=Path('out/byor-motu-frame-effects/report.json');authored=json.loads(source.read_text());table=source.with_suffix('.b4fe').read_bytes();rows,synthetic=inputs(authority,authored,table)
    malformed=[]
    for field,value in (('quake_start',1),('quake_repeat',-2147483648),('quake_value',-2147483648),('jump_x',-2147483648)):
        data=bytearray(128);struct.pack_into('<i',data,4*ANIMATION_FIELDS.index(field),value);malformed.append(bytes(data))
    reporter=Reporter('M4-FRAME-EFFECT-LEAF',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'SourceFrameEffectLeaf4086_Apply','SourceFrameEffectLeaf4086_Ready',0xb4f4,[(59,0,bytes((17,23,19,23,22,23))),(60,0,table),(60,32000,synthetic),*( (60,32256+128*i,data) for i,data in enumerate(malformed))],LUA,reporter)
    results=[];costs=[]
    for line in log.splitlines():
        for marker,target in [('EFFECTLEAFRESULT|',results),('EFFECTLEAFCOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('source mutations and cursor acknowledgement preserve unrelated bytes/context',len(results)==len(rows) and all(r==[i,2 if c['fault'] else 1,0,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    r=dict(schema='BYOR_4086_FRAME_EFFECT_LEAF_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),source_c_cases=sum(r['origin']=='PINNED_C' and not r['fault'] for r in rows),authored_cases=sum(r['origin']=='AUTHORED' and not r['fault'] for r in rows),guard_cases=sum(r['fault'] for r in rows),results=results,cpu_costs=costs,source_table_sha256=hashlib.sha256(table).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cursor_publication_instrumented=True,native_cursor_ack_bound=True,level_quake_camera_presentation_bound=False,motu_gameplay_proven=False,live_presentation_contention_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
