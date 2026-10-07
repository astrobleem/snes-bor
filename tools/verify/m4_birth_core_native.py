"""Native B4BI augmentation of existing NONE/idle birth policies, isolated."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_birth_core import unpack,HEADER,STRIDE
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(i*8))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(n,v)put(sy[n],v)end
local ranges={{0x437e00,2560},{0x409000,8192},{0x40c000,12288},{0x43eb00,4096},{0x43fd80,32},{0x414000,10240},{0x418800,24576}}
local before,cpu,start,ctx={},{},0,0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,(r[1]==0x40c000 or r[1]==0x43eb00)and 165 or 0,mt)end end
 for i=0,127 do put(0x414000+i*80,0x414000+i*80,4)end
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128);set('VmSourceWorld_TemplateCount',16)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',16);set('SourceIdle4086_Ready',0xb4f3)
 for _,p in ipairs({'SourceUpdateFrame','SourceAnimationInit','SourceModelAnimation','SourceModelTransition','SourceWorldTick','SourceFrameStack','SourceFrameEffectPlan'})do set(p..'4086_Ready',0)end
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_GlobalLow',0);set('SourceSelf4086_GlobalHigh',0);set('SourceSelf4086_Fault',0);set('SourceSelf4086_Active',0)
 set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 set('SourceRetirement4086_Ready',0xb4f8);set('SourceRetirement4086_Status',0)
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Due',1);set('SourceClock4086_TimeLo',48);set('SourceClock4086_TimeHi',0);set('SourceClock4086_Fault',0)
 set('SourceBirthCore4086_Ready',0xb4f9);set('SourceBirthCore4086_Status',0);set('SourceBirthCore4086_Slot',c.slot);set('SourceBirthCore4086_Model',c.model);set('SourceBirthCore4086_Base',0x8000);set('SourceBirthCore4086_Bank',60);set('SourceBirthCore4086_Bytes',TABLEBYTES);set('SourceBirthCore4086_Models',16)
 if c.bad=='ready'then set('SourceBirthCore4086_Ready',0xffff)
 elseif c.bad=='sticky'then set('SourceBirthCore4086_Status',3)
 elseif c.bad=='models'then set('SourceBirthCore4086_Models',17)
 elseif c.bad=='paired'then set('VmSourceWorld_TemplateCount',15)
 elseif c.bad=='base'then set('SourceBirthCore4086_Base',0x7fff)
 elseif c.bad=='bytes'then set('SourceBirthCore4086_Bytes',20)
 elseif c.bad=='bank'then set('SourceBirthCore4086_Bank',0x40)
 elseif c.bad=='slot'then set('SourceBirthCore4086_Slot',128)
 elseif c.bad=='model'then set('SourceBirthCore4086_Model',16)
 elseif c.bad=='alive'then put(0x414004+c.slot*80,1)
 elseif c.bad=='token'then put(0x414000+c.slot*80,0)
 elseif c.bad=='retire'then set('SourceRetirement4086_Ready',0)
 elseif c.bad=='vars'then put(0x418800,0x414000+c.slot*80,4)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Entities',127)
 elseif c.bad=='flags'then set('SourceIdle4086_Ready',0)
 elseif c.bad=='self'then set('SourceSelf4086_Fault',1)
 elseif c.bad=='count'then put(0x43fd80,1,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 local state=emu.getState();start=state.masterClock;cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp~=s['cpu.sp'] or(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('BIRTHCORECOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then
  for i,n in ipairs(c.core)do before[0x40c000+c.slot*96+i-1]=n end
  for i,n in ipairs(c.flags)do before[0x43eb00+c.slot*32+i-1]=n end
  for i,n in ipairs(c.relation)do before[0x409000+c.slot*64+i-1]=n end
  for j=0,19 do before[0x437e00+c.slot*20+j]=0 end;before[0x437e10+c.slot*20]=0xfb;before[0x437e11+c.slot*20]=0xb5
  before[0x43fd80]=1
 end
 local mismatch=0;for a,n in pairs(before)do if emu.read(a,mt)~=n then mismatch=mismatch+1 end end
 emu.log('BIRTHCORERESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(sy.SourceBirthCore4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('BIRTHCORECLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,POSTRESULT,POSTRESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--table',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--attack-timing',type=Path);p.add_argument('--attack-cost',action='store_true');p.add_argument('--attack-body',type=Path);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);table=a.table.read_bytes();count=unpack(table);assert count==16;rows=[]
    for model in range(count):
        data=table[HEADER+model*STRIDE:HEADER+(model+1)*STRIDE];cap=int.from_bytes(data[2:4],'little')
        for slot in ((0,1,95,96,127)if a.attack_body else(0,1,127)):rows.append(dict(model=model,slot=slot,fault=int(not cap),bad='',core=list(data[16:112]),flags=list(data[112:144]),relation=list(data[144:208])))
    base=next(r for r in rows if not r['fault'])
    for bad in ('ready','sticky','models','paired','base','bytes','bank','slot','model','alive','token','retire','vars','core','flags','self','count'):
        for slot in (0,127):rows.append(dict(base,slot=slot,fault=1,bad=bad))
    lua=LUA.replace('TABLEBYTES',str(len(table)))
    if a.attack_timing:
        from m4_animation_init_native import luav
        import struct
        data=a.attack_timing.read_bytes();assert len(data)==220 and struct.unpack_from('<4s6H',data)==(b'B4AT',1,16,12,0,0,0)
        for c in rows:c['wanttiming']=list(data[28+c['model']*12:40+c['model']*12])+[3,0xb6]
        lua='local timingbytes='+luav(list(data))+'\n'+lua.replace('local ranges={{0x437e00','local ranges={{0x438800,1984},{0x40bd00,192},{0x437e00')
        lua=lua.replace(' before={};'," set('SourceAttackTiming4086_Ready',0xb603);set('SourceAttackTiming4086_Status',2);set('SourceAttackTiming4086_Models',16);for j=0,191 do emu.write(0x40bd00+j,timingbytes[29+j],mt)end\n before={};")
        lua=lua.replace('if c.fault==0 then\n', 'if c.fault==0 then\n for j,value in ipairs(c.wanttiming)do before[0x438800+c.slot*14+j-1]=value end\n',1)
    else:lua=lua.replace(' before={};'," set('SourceAttackTiming4086_Ready',0)\n before={};")
    tables=[(60,0,table)]
    if a.attack_body:
        from m4_animation_init_native import luav
        import struct
        body=a.attack_body.read_bytes();assert len(body)==160 and struct.unpack_from('<4s6H',body)==(b'B4BC',1,16,9,12,4,0);tables.append((59,0,body))
        for c in rows:c['wantbody']=list(body[16+c['model']*9:25+c['model']*9])+[5,0xb6]
        lua=lua.replace('local ranges={{','local ranges={{0x435800,1536},{0x40bdcc,352},{')
        lua=lua.replace(' before={};'," set('SourceAttackBody4086_Ready',0xb605);set('SourceAttackBody4086_Status',0);set('SourceAttackBody4086_Bank',59);set('SourceAttackBody4086_Base',0x8000);set('SourceAttackBody4086_Bytes',160)\n before={};")
        lua=lua.replace('if c.fault==0 then\n','if c.fault==0 then\n local b=c.slot<96 and 0x435980+c.slot*11 or 0x40bdcc+(c.slot-96)*11;for j,value in ipairs(c.wantbody)do before[b+j-1]=value end\n',1)
    else:lua=lua.replace(' before={};'," set('SourceAttackBody4086_Ready',0)\n before={};")
    if a.attack_cost:
        for bad in ('cost_ready','cost_cache_ready','cost_cache_size'):rows.append(dict(rows[0],bad=bad,fault=1))
        lua=lua.replace('local ranges={{','local ranges={{0x43c000,8192},{')
        lua=lua.replace(' before={};'," set('SourceAttackCostState4086_Ready',c.bad=='cost_ready'and 0xb60a or 0xb609);set('SourceModelAnimationCopy4086_Ready',c.bad=='cost_cache_ready'and 0 or 0xb4e9);set('SourceModelAnimationCopy4086_Bytes',c.bad=='cost_cache_size'and 8192 or 5376)\n for j=0,8191 do emu.write(0x43c000+j,(j*17+91)&255,mt)end\n before={};")
        lua=lua.replace('if c.fault==0 then\n','if c.fault==0 then\n for j=0,3 do before[0x43de00+c.slot*4+j]=0 end\n',1)
    else:lua=lua.replace(' before={};'," set('SourceAttackCostState4086_Ready',0)\n before={};")
    reporter=Reporter('M4-BIRTH-CORE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceBirthCore4086_Apply','SourceBirthCore4086_Ready',0xb4f9,tables,lua,reporter,post='SourceClock4086_Commit');results=[];costs=[];clocks=[]
    for line in log.splitlines():
        for marker,target in [('BIRTHCORERESULT|',results),('BIRTHCORECOST|',costs),('BIRTHCORECLOCK|',clocks)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('exact source-derived core/flags/relations and preserved unrelated bytes/context',len(results)==len(rows) and all(r==[i,0,0,3 if c['fault'] else 2] for i,(r,c) in enumerate(zip(results,rows))))
    reporter.check('admitted birth fault blocks clock retirement',len(clocks)==len(rows) and all(r==([i,1,48,1] if c['fault'] else [i,0,49,0]) for i,(r,c) in enumerate(zip(clocks,rows))))
    report=dict(schema='BYOR_4086_NONE_IDLE_BIRTH_CORE_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),cases=len(rows),inputs=[{k:v for k,v in r.items() if k not in ('core','flags','relation')} for r in rows],results=results,costs=costs,clocks=clocks,combat_birth_fields_zeroed=True,attack_timing_actual_birth_copy_bound=bool(a.attack_timing),attack_body_actual_birth_copy_bound=bool(a.attack_body),attack_cost_actual_birth_clear_bound=a.attack_cost,alive_publication_bound=False,full_constructor_cleanup_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
