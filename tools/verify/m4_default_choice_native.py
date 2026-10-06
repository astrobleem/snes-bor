"""Native default-init first animation selection from complete pinned C proof."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_default_choice_4086 import choose
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x40c000,12288},{0x414000,10240},{0x416800,8192},{0x43c000,8192}}
local before,cpu,start,ctx={},{},0,0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0,mt)end end
 for i=0,127 do
  local a=0x414000+i*80;put(a,a,4);put(a+4,1)
  for n,tag in ipairs({2,1,1,1,1,2,2,1})do put(a+n*8,tag,4)end
 end
 put(0x40c048+c.slot*96,c.type,4)
 for n=1,3 do put(0x43c000+n*2,(c.mask&(1<<n))~=0 and n or 0)end
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_Count',128)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',1)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',1);set('SourceModelAnimationCopy4086_Maximum',6);set('SourceModelAnimationCopy4086_Bytes',12)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',3)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',0x8000);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',AIBYTES);set('SourceAnimationInit4086_Handles',3)
 set('SourceDefaultChoice4086_Ready',0xb4fa);set('SourceDefaultChoice4086_Status',0);set('SourceDefaultChoice4086_Slot',c.slot);set('SourceDefaultChoice4086_Select',c.select);put(sy.SourceDefaultChoice4086_TimeLo,c.time,4)
 set('SourceDefaultChoice4086_Spawn',1);set('SourceDefaultChoice4086_Respawn',2);set('SourceDefaultChoice4086_Selection',3)
 if c.bad=='ready'then set('SourceDefaultChoice4086_Ready',0)
 elseif c.bad=='sticky'then set('SourceDefaultChoice4086_Status',3)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourceDefaultChoice4086_Slot',128)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='core_count'then set('SourceModelEntityCopy4086_Entities',127)
 elseif c.bad=='cache'then set('SourceModelAnimationCopy4086_Ready',0)
 elseif c.bad=='pending'then set('SourceAnimationInit4086_State',1)
 elseif c.bad=='table'then set('SourceAnimationInit4086_Base',0x8002)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 local s=emu.getState();start=s.masterClock;cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp~=s['cpu.sp'] or(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('CHOICECOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local mismatch=0;for a,n in pairs(before)do if emu.read(a,mt)~=n then mismatch=mismatch+1 end end
 emu.log('CHOICERESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(sy.SourceDefaultChoice4086_Status)..'|'..word(sy.SourceDefaultChoice4086_Service)..'|'..word(sy.SourceDefaultChoice4086_Chosen))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';rows=[];seen={}
    for r in authority['results']:
        c=r['case'];key=(c['type'],c['select'],c['time'],c['mask']&14);trace=r['actual']['trace'];expected=trace[1] if len(trace)>1 and trace[0]==1 and trace[1] in (1,2,3) else None
        wanted=choose(c['type'],c['select'],c['time'],lambda n:c['mask']&(1<<n),1,2,3);assert wanted==expected
        if key in seen:assert seen[key]==wanted;continue
        seen[key]=wanted
        for slot in (0,1,127):rows.append(dict(type=c['type'],select=c['select'],time=c['time'],mask=c['mask']&14,slot=slot,chosen=0xffff if wanted is None else wanted,service=int(wanted is not None),fault=0,bad=''))
    base=next(r for r in rows if r['service'])
    for bad in ('ready','sticky','world','count','slot','core','core_count','cache','pending','table'):
        for slot in (0,127):rows.append(dict(base,slot=slot,fault=1,bad=bad))
    ai=pack_ai(dict(maximum_animations=6,animations=[dict(handle=n,numframes=1,sync=-1,engine_animation_id=n) for n in (1,2,3)]))
    fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=n,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)]) for n in (1,2,3)]))
    reporter=Reporter('M4-DEFAULT-CHOICE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultChoice4086_Prepare','SourceDefaultChoice4086_Ready',0xb4fa,[(59,0,ai),(60,0,fe)],LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))),reporter);results=[];costs=[]
    for line in log.splitlines():
        for marker,target in [('CHOICERESULT|',results),('CHOICECOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('source first-animation choice with real resolver and preserved physical state/context',len(results)==len(rows) and all(r[:4]==[i,0,0,3 if c['fault'] else 2] and (c['fault'] or r[4:]==[c['service'],c['chosen']]) for i,(r,c) in enumerate(zip(results,rows))))
    report=dict(schema='BYOR_4086_DEFAULT_INIT_FIRST_CHOICE_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),authority_function_sha256=authority['function_sha256'],distinct_source_cases=len(seen),cases=len(rows),inputs=rows,results=results,costs=costs,first_animation_preparation_only=True,actual_ent_set_anim_called=False,remaining_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
