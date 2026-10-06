"""No-event/no-minion native kill leaf versus full pinned C retirement states."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_kill_authority import initial
from source_retirement_state import RELATIONS,SCALARS,pack_row
from source_script_variables import pack_record
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def packet(c,state=None,mapping=None,count=6):
    mapping=mapping or list(range(6))
    o=initial(c);es=o.entities
    if state is not None:
        s=state
        def ent(n):return None if n==-1 else es[n]
        o.ent_count=s[0];o.self_entity=ent(s[1]);o.smartbomber=ent(s[2]);o.textbox=ent(s[3]);o.players=[ent(n) for n in s[4:8]]
        for i,e in enumerate(es):
            r=s[8+15*i:8+15*(i+1)];e.exists=bool(r[0]);e.health=r[1];e.cantfire=r[2];e.cleared=r[3]
            for name,n in zip(('parent','subentity','owner','opponent','binding','landed','hithead','lasthit','link','grabbing','weapent'),r[4:]):setattr(e,name,ent(n))
    def token(e):return 0 if e is None else 0x414000+80*mapping[e.identity]
    packets=[];view=bytearray(6*80);core=bytearray(6*96);flags=bytearray(6*32);relations=bytearray()
    for i,e in enumerate(es):
        struct.pack_into('<IHH',view,80*i,token(e),int(e.exists),0)
        for at,n in ((16,0),(20,0),(24,1),(28,1),(32,1),(36,e.health),(64,1),(68,150)):
            struct.pack_into('<I',view,80*i+at,n)
        struct.pack_into('<I',core,96*i+72,e.type);struct.pack_into('<I',core,96*i+80,token(e.grabbing));struct.pack_into('<I',core,96*i+84,token(e.lasthit))
        struct.pack_into('<I',flags,32*i+28,token(e.weapent))
        row={f:token(getattr(e,f)) for f in RELATIONS};row.update(cantfire=e.cantfire,summonkill=e.summonkill,takedamage=int(e.takedamage),script_initialized=0 if e.cleared else 7,script_clear_entries=0,onkill_initialized=0)
        relations.extend(pack_row(row,count))
    roles=struct.pack('<i7I',o.ent_count,*map(token,o.players),token(o.smartbomber),token(o.textbox),int(o.level_completed))
    variables=b''.join(pack_record(token(es[owner]),scope,'persist'+str(i),bytes(8) if es[owner].cleared else struct.pack('<BBHI',1,0,0,0x87654321+i)) for i,(owner,scope) in enumerate(((1,1),(1,2),(0,1),(5,3))))
    for at,data in ((0x414000,view),(0x40c000,core),(0x43eb00,flags),(0x409000,relations),(0x43fd80,roles),(0x418800,variables),(0x7ffe38,struct.pack('<I',token(o.self_entity)))):
        if at in (0x414000,0x40c000,0x43eb00,0x409000):
            stride={0x414000:80,0x40c000:96,0x43eb00:32,0x409000:64}[at]
            for i in range(6):packets.append(dict(at=at+stride*mapping[i],data=list(data[stride*i:stride*(i+1)])))
        else:packets.append(dict(at=at,data=list(data)))
    return packets

LUA=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local start=0;local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
local ranges={{0x414000,10240},{0x409000,8192},{0x40c000,12288},{0x43eb00,4096},{0x43fd80,32},{0x418800,24576},{0x7ffe38,4}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 for _,r in ipairs({{0x414000,80},{0x40c000,96},{0x43eb00,32},{0x409000,64}})do for i=0,c.count*r[2]-1 do emu.write(r[1]+i,0,mt)end end
 -- Valid free variable rows outside the four named fixture records.
 for i=0,24575 do emu.write(0x418800+i,0,mt)end
 for _,p in ipairs(c.before)do for i,n in ipairs(p.data)do emu.write(p.at+i-1,n,mt)end end
 for _,p in ipairs({'SourceUpdateFrame','SourceAnimationInit','SourceModelAnimation','SourceModelTransition','SourceWorldTick','SourceFrameStack','SourceFrameEffectPlan'})do set(p..'4086_Ready',0)end
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0)
 set('SourceRetirement4086_Ready',0xb4f8);set('SourceRetirement4086_Status',0);set('SourceRetirement4086_Slot',c.slot)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',c.count)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',c.count);set('SourceModelEntityCopy4086_Models',1);set('SourceIdle4086_Ready',0xb4f3)
 set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Due',1);set('SourceClock4086_TimeLo',48,4);set('SourceClock4086_Fault',0)
 put(EXPECTFAULT,c.fault)
 if typed then
  set('VmCall_TargetId',0x20a);set('VmCall_Argc',c.argc or 1,1);set('VmCall_ArgListIndex',0);set('VmCall_ArgSlotsOff',0x200)
  put(sy.VmCode_Wram+0x200,0);put(sy.VmSlots_Wram,c.tag or 5);put(sy.VmSlots_Wram+2,0);put(sy.VmSlots_Wram+4,c.null and 0 or 0x414000+80*c.slot,4)
  for i=0,7 do emu.write(sy.VmNativeVariant_Result+i,0xa5,mt)end
 end
 if c.bad=='ready'then set('SourceRetirement4086_Ready',0)
 elseif c.bad=='sticky'then set('SourceRetirement4086_Status',3)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then if typed then put(sy.VmSlots_Wram+4,0x414000+80*c.count,4)else set('SourceRetirement4086_Slot',6)end
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='flags'then set('SourceIdle4086_Ready',0)
 elseif c.bad=='vars'then set('VmSourceVars_Ready',0)
 elseif c.bad=='var_count'then set('VmSourceVars_Count',385)
 elseif c.bad=='self'then set('SourceSelf4086_Ready',0)
 elseif c.bad=='pointer'then put(0x409008,0x414002,4)
 elseif c.bad=='role'then put(0x43fd84,0x424000,4)
 elseif c.bad=='reserved'then put(0x409038,1)
 elseif c.bad=='onkill'then put(0x409074,1,4)
 elseif c.bad=='clear_entry'then put(0x409070,1,4)
 elseif c.bad=='alive_count'then put(0x43fd80,99,4)
 elseif c.bad=='owner_count'then set('SourceModelEntityCopy4086_Entities',5)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();start=s.masterClock;cpu={};ctx=0
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,CAPTUREENTRY,CAPTUREENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('RETIRECOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 and not c.null then for _,p in ipairs(c.after)do for i,n in ipairs(p.data)do before[p.at+i-1]=n end end end
 local mismatch=0;for a,n in pairs(before)do if emu.read(a,mt)~=n then mismatch=mismatch+1 end end
 emu.log('RETIRERESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(sy.SourceRetirement4086_Status))
 if typed then
  local mismatch=0;local value=c.null and 0 or 1
  local wanted=c.fault==1 and {165,165,165,165,165,165,165,165} or {1,0,0,0,value,0,0,0}
  for i,n in ipairs(wanted)do if emu.read(sy.VmNativeVariant_Result+i-1,mt)~=n then mismatch=mismatch+1 end end
  emu.log('RETIREAPI|'..word(INDEX)..'|'..mismatch)
 end
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('RETIRECLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,POSTRESULT,POSTRESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--typed-api',action='store_true');a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS' and authority['cases']==144
    rows=[]
    for r in authority['results']:
        c=r['case']
        if c['mode']==2:continue # Initialized callback body is not this leaf.
        fault=int(c['mode']==0 and (c['summon']==1 and c['sub'] or c['summon']==2))
        for count,mapping in ((6,list(range(6))),(128,[0,1,2,3,4,127]),(128,list(range(122,128)))):
            rows.append(dict(case=c,before=packet(c,mapping=mapping,count=count),after=packet(c,r['actual']['state'],mapping,count),count=count,slot=mapping[1],fault=fault,bad=''))
    base=next(r for r in rows if r['fault']==0 and r['case']['mode']==0 and r['case']['summon']==0)
    for bad in ('ready','sticky','world','pool','count','slot','core','flags','vars','var_count','self','pointer','role','reserved','onkill','clear_entry','alive_count','owner_count'):
        rows.append(dict(base,fault=1,bad=bad))
    if a.typed_api:
        rows.extend(dict(base,tag=tag,null=True,fault=0,bad='') for tag in (0,1,5))
        rows.extend(dict(base,tag=tag,null=null,fault=1,bad='') for tag in (2,3) for null in (False,True))
        rows.append(dict(base,argc=0,fault=1,bad=''))
        rows.append(dict(base,argc=2,tag=1))
    reporter=Reporter('M4-SOURCE-RETIREMENT',kind='GATE')
    lua='local typed='+str(a.typed_api).lower()+'\n'+LUA
    raw,log=run_fixture(a.rom,folder,rows,'Vm_NativeVariantDispatch' if a.typed_api else 'SourceRetirement4086_ApplyNoEvents','SourceRetirement4086_Ready',0xb4f8,[],lua,reporter,post='SourceClock4086_Commit',bindings=dict(CAPTUREENTRY='Vm_SourceKill' if a.typed_api else 'SourceRetirement4086_ApplyNoEvents'))
    results=[];costs=[];clocks=[];api=[]
    for line in log.splitlines():
        for marker,target in [('RETIRERESULT|',results),('RETIRECOST|',costs),('RETIRECLOCK|',clocks),('RETIREAPI|',api)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('pinned C retirement state and full unrelated-byte/context preservation',len(results)==len(rows) and all(r==[i,0,0,3 if c['fault'] else 0 if c.get('null') else 2] for i,(r,c) in enumerate(zip(results,rows))))
    reporter.check('admitted retirement faults block source clock',len(clocks)==len(rows) and all(r==([i,1,48,1] if c['fault'] and c['bad']!='ready' else [i,0,49,0]) for i,(r,c) in enumerate(zip(clocks,rows))))
    if a.typed_api:reporter.check('typed API INTEGER result, dead pointer and error preservation',len(api)==len(rows) and all(r==[i,0] for i,r in enumerate(api)))
    report=dict(schema='BYOR_4086_NO_EVENT_RETIREMENT_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),authority_functions_sha256=authority['functions_sha256'],cases=len(rows),supported_c_cases=sum(not r['fault'] for r in rows),inputs=[{k:v for k,v in r.items() if k not in ('before','after')} for r in rows],results=results,costs=costs,clocks=clocks,api_results=api,script_clear_entry_and_onkill_bodies_bound=False,minion_damage_or_recursive_kill_bound=False,script_method1_value_cleanup_bound=True,relation_role_and_global_self_cleanup_bound=True,script_killentity_api_bound=a.typed_api,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
