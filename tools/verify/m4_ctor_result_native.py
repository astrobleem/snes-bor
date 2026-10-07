"""Native constructor return publication, including dead/null and stale tickets."""
import argparse
import hashlib
import json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from m4_default_init_tail_native import LUA as TAIL_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=TAIL_LUA.replace("set('SourceAnimationInit4086_Ready',0);set('SourceAnimationInit4086_State',0)","""
 set('SourceAnimationInit4086_Ready',0);set('SourceAnimationInit4086_State',0)
 set('SourceUpdateFrame4086_Ready',0);set('SourceUpdateFrame4086_State',0)
 set('SourceCtorOwner4086_Phase',c.phase);set('SourceCtorOwner4086_Model',c.model)
 set('SourceDefaultInit4086_Phase',6);set('SourceDefaultInit4086_OwnerSlot',c.model==65535 and 65535 or c.slot)
 put(0x416800+c.slot*64,0)
 for i=0,7 do emu.write(sy.VmNativeVariant_Result+i,165,mt)end
 if c.model==65535 then set('VmSourceWorld_Ready',0)end
""")
LUA=LUA.replace('put(v+4,c.alive)','put(v+4,c.alive,4)')
LUA=LUA.replace("elseif c.bad=='empty'then","""
 elseif c.bad=='owner_phase'then set('SourceDefaultInit4086_Phase',c.value)
 elseif c.bad=='owner_slot'then set('SourceDefaultInit4086_OwnerSlot',128)
 elseif c.bad=='model_pair'then put(0x416800+c.slot*64,1)
 elseif c.bad=='model_range'then set('SourceCtorOwner4086_Model',16)
 elseif c.bad=='null_slot'then set('SourceDefaultInit4086_OwnerSlot',0)
 elseif c.bad=='frame_ready'then set('SourceUpdateFrame4086_Ready',1)
 elseif c.bad=='frame_pending'then set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',1)
 elseif c.bad=='exists_high'then put(v+6,1)
 elseif c.bad=='exists_range'then put(v+4,2)
 elseif c.bad=='empty'then""")
LUA=LUA.replace("before={};for _,r in ipairs(ranges)","before={};for i=0,7 do before[sy.VmNativeVariant_Result+i]=emu.read(sy.VmNativeVariant_Result+i,mt)end;for _,r in ipairs(ranges)")
LUA=LUA.replace(" local n=0;for a,v in pairs(before)","""
 local c=rows[word(INDEX)+1]
 if c.fault==0 then
  local values=c.model==65535 and {0,0,0,0,0,0,0,0} or {5,0,0,0,(0x4000+c.slot*80)&255,(0x4000+c.slot*80)>>8,0x41,0}
  for i=0,7 do before[sy.VmNativeVariant_Result+i]=values[i+1]end
 end
 local n=0;for a,v in pairs(before)""")
LUA=LUA.replace("emu.log('TAILRESULT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceDefaultPlayer4086_Status)..'|'..word(sy.SourceEmptyInitEnvironment4086_Status))",
                "local v='';for i=0,7 do v=v..string.format('%02x',emu.read(sy.VmNativeVariant_Result+i,mt))end;emu.log('CTORRESULT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceCtorOwner4086_Phase)..'|'..v)")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    base=dict(slot=0,level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0,phase=2,model=0,value=0)
    rows=[dict(base,slot=slot,alive=alive)for slot in (0,1,127)for alive in (0,1)]
    rows.append(dict(base,model=65535))
    for slot in (0,127):
        for phase in (0,1,3,65535):rows.append(dict(base,slot=slot,phase=phase,fault=1))
        for value in (0,1,2,3,4,5,7,65535):rows.append(dict(base,slot=slot,bad='owner_phase',value=value,fault=1))
        for bad in ('world','pool','side','owner_slot','model_pair','model_range','token','token_high','pending','frame_ready','frame_pending','exists_high','exists_range'):
            rows.append(dict(base,slot=slot,bad=bad,fault=1))
    rows.append(dict(base,model=65535,bad='null_slot',fault=1))
    sy=symbols(Path('src/main.sym'));lua=LUA.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
    entry=sy['SourceCtorOwner4086_Result'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-CTOR-RESULT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCtorOwner4086_Result','SourceDefaultPlayer4086_Ready',0xb5c4,[],lua,r,batch_size=2)
    results=[line.split('CTORRESULT|',1)[1].split('|')for line in log.splitlines()if 'CTORRESULT|'in line]
    r.check('exact live/dead/null result, stale ownership rejection, untouched entities/result on fault and CPU context',len(results)==len(rows)and all(list(map(int,v[:4]))==[i,0,0,3 if c['fault']else 2]for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_CTOR_RESULT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,constructor_completion_ticket_instrumented=True,active_script_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
