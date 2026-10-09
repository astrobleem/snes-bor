"""Source map/owner identity publication and real transition service-6 Ack."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_model_palette_service_native import derive,emit,pack
from m4_default_init_tail_native import LUA as TAIL_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

LUA=TAIL_LUA.replace('local ranges={{0x40c000','local ranges={{0x433800,8192},{0x40c000')
LUA=LUA.replace(" set('SourceDefaultPlayer4086_Ready',0xb503)","""
 local row=0x433800+c.slot*64;put(row+48,c.map);put(row+50,(c.model+1)%16);put(row+62,0xb5c2);put(0x416800+c.slot*64,c.model)
 set('SourceCtorState4086_Ready',0xb5c2);set('SourceCtorState4086_Models',16)
 set('SourceModelTransition4086_Ready',0xb4f0);set('SourceModelTransition4086_State',1);set('SourceModelTransition4086_Service',6);set('SourceModelTransition4086_Acknowledged',0);set('SourceModelTransition4086_Slot',c.slot);set('SourceModelTransition4086_New',c.model);set('SourceModelTransition4086_Old',(c.model+1)%16);set('SourceModelTransition4086_Side',0x6800+c.slot*64);set('SourceModelTransition4086_Core',0xc000+c.slot*96);set('SourceModelTransition4086_OldTypeLo',word(0x40c048+c.slot*96));set('SourceModelTransition4086_OldTypeHi',word(0x40c04a+c.slot*96))
 set('SourceDefaultPlayer4086_Ready',0xb503)""")
LUA=LUA.replace(" if c.bad=='ready'then", """ if c.bad=='transition_ready'then set('SourceModelTransition4086_Ready',0)
 elseif c.bad=='transition_state'then set('SourceModelTransition4086_State',2)
 elseif c.bad=='transition_service'then set('SourceModelTransition4086_Service',3)
 elseif c.bad=='transition_ack'then set('SourceModelTransition4086_Acknowledged',6)
 elseif c.bad=='transition_slot'then set('SourceModelTransition4086_Slot',128)
 elseif c.bad=='transition_side'then set('SourceModelTransition4086_Side',0x6802+c.slot*64)
 elseif c.bad=='transition_core'then set('SourceModelTransition4086_Core',0xc002+c.slot*96)
 elseif c.bad=='transition_type_low'then set('SourceModelTransition4086_OldTypeLo',1)
 elseif c.bad=='transition_type_high'then set('SourceModelTransition4086_OldTypeHi',1)
 elseif c.bad=='transition_model'then set('SourceModelTransition4086_New',16)
 elseif c.bad=='side_model'then put(0x416800+c.slot*64,(c.model+1)%16)
 elseif c.bad=='template'then set('VmSourceWorld_TemplateCount',15)
 elseif c.bad=='copy_models'then set('SourceModelEntityCopy4086_Models',15)
 elseif c.bad=='ctor_ready'then set('SourceCtorState4086_Ready',0)
 elseif c.bad=='ctor_models'then set('SourceCtorState4086_Models',15)
 elseif c.bad=='row_lease'then put(row+62,0)
 elseif c.bad=='row_owner'then put(row+50,16)
 elseif c.bad=='token'then put(v,0,4)
 elseif c.bad=='token_high'then put(v+2,0)
 elseif c.bad=='ready'then""")
start=LUA.index(' if c.fault==0 and');end=LUA.index(' local s=emu.getState()',start)
LUA=LUA[:start]+""" if c.fault==0 then
 local row=0x433800+c.slot*64
 before[row+48]=c.selected&255;before[row+49]=(c.selected>>8)&255
 before[row+50]=c.model;before[row+51]=0
 end
"""+LUA[end:]
LUA=LUA.replace("..word(sy.SourceDefaultPlayer4086_Status)..'|'..word(sy.SourceEmptyInitEnvironment4086_Status))","..word(sy.SourceModelTransition4086_State)..'|'..word(sy.SourceModelTransition4086_Service)..'|'..word(sy.SourceModelTransition4086_Acknowledged))")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);report=derive(Source(a.source))
 base=dict(level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0)
 rows=[dict(base,slot=slot,model=m['id'],map=value,selected=value if value<=m['maps_loaded']else 0)for slot,m,value in itertools.product((0,1,127),report['models'],(0,1,2,3,255,32768,65535))]
 guards=('transition_ready','transition_state','transition_service','transition_ack','transition_slot','transition_side','transition_core','transition_type_low','transition_type_high','transition_model','side_model','template','copy_models','ctor_ready','ctor_models','row_lease','row_owner','token','token_high','world','pool','side','count','core','entities')
 rows.extend(dict(rows[0],slot=slot,bad=bad,fault=1)for slot,bad in itertools.product((0,127),guards))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
 r=Reporter('M4-MODEL-PALETTE-SERVICE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'ModelPaletteService_Apply6','SourceModelTransition4086_Ready',0xb4f0,[],lua,r,batch_size=4,append=emit(report,sy),link_pcm=False)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('source alternate maps, per-entity identity, untouched row bytes and CPU context',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 1]and(c['fault']or v[4:]==[7,0])for i,(v,c)in enumerate(zip(results,rows))))
 r.check('stale requests never acknowledge',len(results)==len(rows)and all(not c['fault']or v[5]==(6 if c['bad']=='transition_ack'else 0)for v,c in zip(results,rows)))
 table=pack(report);(a.output/'palettes.b5mp').write_bytes(table)
 d=dict(schema='BYOR_4086_MODEL_PALETTE_SERVICE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,palette_identities=report,palette_table_sha256=hashlib.sha256(table).hexdigest(),palette_table_bytes=len(table),real_transition_ack=True,cgram_admission_bound=False,first_colour_service_bound=False,full_transition_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
