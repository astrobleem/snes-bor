"""Reject incomplete/stale default-init continuation tickets before entity writes."""
import argparse,hashlib,json
from pathlib import Path
from m4_default_init_tail_native import LUA as TAIL_LUA
from _source_leaf_fixture import run_fixture
from actor_s5_entity_fixture import symbols
from _harness import Reporter

LUA=TAIL_LUA.replace("set('SourceAnimationInit4086_Ready',0);set('SourceAnimationInit4086_State',0)","""set('SourceDefaultInit4086_Phase',c.phase);set('SourceDefaultInit4086_OwnerSlot',c.slot);put(MODE,c.mode)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',c.mode==1 and 1 or 0);set('SourceAnimationInit4086_Slot',c.slot);set('SourceAnimationInit4086_Issued',1)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',2);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Request',0);set('SourceUpdateFrame4086_Slot',c.slot)""")
LUA=LUA.replace("elseif c.bad=='empty'then","""elseif c.bad=='init_ready'then set('SourceAnimationInit4086_Ready',1)
 elseif c.bad=='init_pending'then set('SourceAnimationInit4086_State',1)
 elseif c.bad=='init_state'then set('SourceAnimationInit4086_State',c.value)
 elseif c.bad=='owner_slot'then set('SourceDefaultInit4086_OwnerSlot',c.slot+1)
 elseif c.bad=='issued'then set('SourceAnimationInit4086_Issued',0)
 elseif c.bad=='frame_ready'then set('SourceUpdateFrame4086_Ready',1)
 elseif c.bad=='frame_state'then set('SourceUpdateFrame4086_State',c.value)
 elseif c.bad=='frame_slot'then set('SourceUpdateFrame4086_Slot',c.slot+1)
 elseif c.bad=='frame_request'then set('SourceUpdateFrame4086_Request',1)
 elseif c.bad=='frame_pending'then set('SourceUpdateFrame4086_Pending',1)
 elseif c.bad=='empty'then""")
LUA=LUA.replace("..word(sy.SourceEmptyInitEnvironment4086_Status))","..word(sy.SourceDefaultInit4086_Phase))")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 base=dict(slot=0,level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=1,phase=0,mode=0,value=0)
 rows=[]
 for slot in(0,127):
  for phase in(1,2,3,4,5,7,65535):rows.append(dict(base,slot=slot,phase=phase))
  for bad in('ready','sticky','init_ready','init_pending','frame_ready','frame_pending'):rows.append(dict(base,slot=slot,bad=bad))
  for phase in(0,6,7,65535):rows.append(dict(base,slot=slot,mode=1,phase=phase))
  for phase in(1,2,3,4,5):
   for bad in('owner_slot','init_ready','issued','frame_ready','frame_slot','frame_request','frame_pending'):rows.append(dict(base,slot=slot,mode=1,phase=phase,bad=bad))
   for bad in('init_state','frame_state'):
    for value in(0,3,65535):rows.append(dict(base,slot=slot,mode=1,phase=phase,bad=bad,value=value))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88))
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 for label in('SourceDefaultInit4086_Begin','SourceDefaultInit4086_Continue'):
  lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-DEFAULT-OWNER-GUARDS',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultInit4086_Begin','SourceDefaultPlayer4086_Ready',0xb5d1,[],lua,r,finish='SourceDefaultInit4086_Continue')
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('pending/done/fault phases, paired actor and actual frame-zero retirement prerequisites reject without entity/context writes',results==[[i,0,0,3,7]for i in range(len(rows))])
 d=dict(schema='BYOR_4086_DEFAULT_INIT_OWNER_GUARDS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,full_constructor_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
