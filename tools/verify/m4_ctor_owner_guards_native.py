"""Constructor ownership guards reject stale/nested work before entity mutation."""
import argparse
import hashlib
import json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from m4_default_owner_guards_native import LUA as DEFAULT_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA = DEFAULT_LUA.replace(
    "local ranges={{0x40c000,12288},{0x414000,18432},{0x439000,10240}}",
    "local ranges={{0x409000,24576},{0x414000,18432},{0x432800,12288},{0x439000,10240}}")
LUA = LUA.replace("local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)",
    "local c=rows[word(INDEX)+1];emu.log('CTORGUARDINIT|'..word(INDEX));put(EXPECTFAULT,c.fault);selected=0")
LUA = LUA.replace("if c.bad=='ready'then", """
 set('SourceCtorOwner4086_Phase',c.ctor_phase);set('SourceCtorOwner4086_Model',0)
 set('SourceVMRun4086_Busy',0);set('VmSourceCallback_Active',0);set('VmState_Status',4)
 put(0x416800+c.slot*64,0)
 if c.bad=='ctor_model'then set('SourceCtorOwner4086_Model',1)
 elseif c.bad=='ctor_world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='ctor_side'then set('VmSourceWorld_SideBase',0x6802)
 elseif c.bad=='ctor_count'then set('VmSourceWorld_Count',c.slot)
 elseif c.bad=='ctor_busy'then set('SourceVMRun4086_Busy',1)
 elseif c.bad=='ctor_callback'then set('VmSourceCallback_Active',1)
 elseif c.bad=='ctor_vm'then set('VmState_Status',c.value)
 elseif c.bad=='ready'then""")
LUA = LUA.replace("emu.log('TAILRESULT|'", "emu.log('CTORGUARD|'" )
LUA = LUA.replace("..word(sy.SourceDefaultInit4086_Phase))",
                  "..word(sy.SourceCtorOwner4086_Phase)..'|'..selected)")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    base=dict(slot=0,level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=1,phase=0,mode=0,value=0,ctor_phase=0)
    rows=[]
    for slot in (0,127):
        for phase in (1,3,65535):rows.append(dict(base,slot=slot,ctor_phase=phase))
        for phase in (1,2,3,4,5,7,65535):rows.append(dict(base,slot=slot,phase=phase))
        for phase in (0,2):
            for bad in ('ctor_busy','ctor_callback','init_ready','init_pending','frame_ready','frame_pending'):
                rows.append(dict(base,slot=slot,ctor_phase=phase,bad=bad))
            for value in (2,3,5):rows.append(dict(base,slot=slot,ctor_phase=phase,bad='ctor_vm',value=value))
        for phase in (0,2,3,65535):rows.append(dict(base,slot=slot,mode=1,ctor_phase=phase))
        for phase in (0,6,7,65535):rows.append(dict(base,slot=slot,mode=1,ctor_phase=1,phase=phase))
        for phase in (1,2,3,4,5):
            for bad in ('ctor_model','ctor_world','ctor_side','ctor_count','owner_slot','init_ready','issued','frame_ready','frame_slot','frame_request','frame_pending'):
                rows.append(dict(base,slot=slot,mode=1,ctor_phase=1,phase=phase,bad=bad))
            for bad in ('init_state','frame_state'):
                for value in (0,3,65535):rows.append(dict(base,slot=slot,mode=1,ctor_phase=1,phase=phase,bad=bad,value=value))
    sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88))
    lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
    for label in ('SourceCtorOwner4086_Begin','SourceCtorOwner4086_Continue'):
        lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)\n"
    lua+=f"emu.addMemoryCallback(function()selected=selected+1 end,emu.callbackType.exec,{sy['SourceSpawnSlot4086_Select']},{sy['SourceSpawnSlot4086_Select']},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-CTOR-OWNER-GUARDS',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceCtorOwner4086_Begin','SourceDefaultPlayer4086_Ready',0xb5c3,[],lua,r,finish='SourceCtorOwner4086_Continue',batch_size=2)
    results=[list(map(int,line.split('CTORGUARD|',1)[1].split('|')))for line in log.splitlines()if 'CTORGUARD|'in line]
    r.check('stale tickets, active interpreter, mismatched actor and incomplete frame work reject without entity/context writes or allocation',
            len(results)==len(rows) and all(v[0:3]==[i,0,0] and v[4:]==[3,0] for i,v in enumerate(results)))
    d=dict(schema='BYOR_4086_CTOR_OWNER_GUARDS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,active_script_constructor_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
