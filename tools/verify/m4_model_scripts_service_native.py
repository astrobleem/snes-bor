"""Ordered service-5 scripts/factors, real transition acknowledgement and guards."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_script_clone import derive as clone,pack as pack_clone
from script_callback_owner import derive,pack
from source_model_factors import derive as factors,pack as pack_factors
from source_model_scripts_service_native import emit
from m4_script_clone_native import LUA as CLONE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

LUA=CLONE_LUA.replace('local ranges={{0x40c000','local ranges={{0x432800,4096},{0x43b900,512},{0x40c000')
LUA=LUA.replace(" set('SourceDefaultPlayer4086_Ready',0xb503)","""
 set('SourceFactors4086_Ready',0xb5f1);set('SourceFactors4086_Status',0);set('SourceFactors4086_Base',0x8000+CLONEBYTES);set('SourceFactors4086_Bank',59);set('SourceFactors4086_Bytes',FACTORBYTES);set('SourceFactors4086_Models',16);set('SourceFactors4086_Attacks',20)
 set('SourceModelTransition4086_Ready',0xb4f0);set('SourceModelTransition4086_State',1);set('SourceModelTransition4086_Service',5);set('SourceModelTransition4086_Acknowledged',0);set('SourceModelTransition4086_Slot',c.slot);set('SourceModelTransition4086_New',c.model);set('SourceModelTransition4086_Old',(c.model+1)%16);set('SourceModelTransition4086_Side',0x6800+c.slot*64);set('SourceModelTransition4086_Core',0xc000+c.slot*96);set('SourceModelTransition4086_OldTypeLo',word(0x40c048+c.slot*96));set('SourceModelTransition4086_OldTypeHi',word(0x40c04a+c.slot*96));set('SourceModelTransition4086_Flags',c.flags)
 set('SourceDefaultPlayer4086_Ready',0xb503)""")
LUA=LUA.replace(" if c.bad=='ready'then", """ if c.bad=='transition_ready'then set('SourceModelTransition4086_Ready',0)
 elseif c.bad=='transition_state'then set('SourceModelTransition4086_State',2)
 elseif c.bad=='transition_service'then set('SourceModelTransition4086_Service',6)
 elseif c.bad=='transition_ack'then set('SourceModelTransition4086_Acknowledged',5)
 elseif c.bad=='transition_slot'then set('SourceModelTransition4086_Slot',128)
 elseif c.bad=='transition_side'then set('SourceModelTransition4086_Side',0x6802+c.slot*64)
 elseif c.bad=='transition_core'then set('SourceModelTransition4086_Core',0xc002+c.slot*96)
 elseif c.bad=='transition_type_low'then set('SourceModelTransition4086_OldTypeLo',1)
 elseif c.bad=='transition_type_high'then set('SourceModelTransition4086_OldTypeHi',1)
 elseif c.bad=='transition_flags'then set('SourceModelTransition4086_Flags',8)
 elseif c.bad=='factor_ready'then set('SourceFactors4086_Ready',0)
 elseif c.bad=='factor_sticky'then set('SourceFactors4086_Status',3)
 elseif c.bad=='factor_models'then set('SourceFactors4086_Models',15)
 elseif c.bad=='factor_attacks'then set('SourceFactors4086_Attacks',19)
 elseif c.bad=='factor_table'then set('SourceFactors4086_Base',0x8000)
 elseif c.bad=='factor_bank'then set('SourceFactors4086_Bank',0)
 elseif c.bad=='factor_bytes'then set('SourceFactors4086_Bytes',FACTORBYTES-2)
 elseif c.bad=='ready'then""")
start=LUA.index(' if c.fault==0 then');end=LUA.index(' local s=emu.getState()',start)
LUA=LUA[:start]+""" if c.fault==0 then
 local mask=c.mask~=0 and c.mask or((c.flags&4)~=0 and 0 or c.oldmask)
 for j=0,3 do before[0x40902c+c.slot*64+j]=(mask>>(j*8))&255 end
 for j,value in ipairs(c.vector)do before[0x432800+c.slot*32+j-1]=value end
 before[0x43b900+c.slot*4]=c.model;before[0x43b901+c.slot*4]=0;before[0x43b902+c.slot*4]=241;before[0x43b903+c.slot*4]=181
 end
"""+LUA[end:]
LUA=LUA.replace("..word(sy.SourceScriptClone4086_Status))","..word(sy.SourceModelTransition4086_State)..'|'..word(sy.SourceModelTransition4086_Service)..'|'..word(sy.SourceModelTransition4086_Acknowledged)..'|'..word(sy.SourceFactors4086_Status))")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);cr=clone(source);ct=pack_clone(cr);cb,*_=derive(source);bt=pack(cb);fr=factors(source);ft=pack_factors(fr)
 base=dict(level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0,mode=1)
 rows=[dict(base,slot=slot,model=m['id'],mask=m['initialized_mask'],oldmask=old,flags=flags,vector=list(bytes.fromhex(fr['models'][m['id']]['vector_hex'])))for slot,m,old,flags in itertools.product((0,1,127),cr['models'],(0,1),(0,4))]
 rows.extend(dict(rows[0],model=3,mask=1,slot=slot,flags=flags)for slot,flags in itertools.product((0,127),(1,2,3,5,6,7)))
 guardbase=next(r for r in rows if r['model']==3 and r['oldmask']==1 and r['flags']==0)
 guards=('transition_ready','transition_state','transition_service','transition_ack','transition_slot','transition_side','transition_core','transition_type_low','transition_type_high','transition_flags','side_model','ready','clone_sticky','world','pool','side','count','token','token_high','models','table','bank','bytes','vars','callback','callback_models','callback_program','old_wide','clear_entry','onkill','factor_ready','factor_sticky','factor_models','factor_attacks','factor_table','factor_bank','factor_bytes')
 rows.extend(dict(guardbase,slot=slot,bad=bad,fault=1)for slot,bad in itertools.product((0,127),guards))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88)).replace('CLONEBYTES',str(len(ct))).replace('FACTORBYTES',str(len(ft))).replace('CALLBACKBYTES',str(len(bt))).replace('PROGRAMS',str(cb['program_count']))
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
 r=Reporter('M4-MODEL-SCRIPTS-SERVICE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'ModelScriptsService_Apply','SourceModelTransition4086_Ready',0xb4f0,[(59,0,ct+ft),(60,0,bt)],lua,r,batch_size=4,append=emit(sy),link_pcm=False)
 results=[list(map(int,value.split('|')))for value in(logline.split('TAILRESULT|',1)[1]for logline in log.splitlines()if 'TAILRESULT|'in logline)]
 r.check('retained variables, exact factors, current physical actor, CPU context and real service-6 continuation',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 1] and (c['fault']or v[4:]==[6,0,2])for i,(v,c)in enumerate(zip(results,rows))))
 r.check('rejected services never acknowledge',len(results)==len(rows)and all(not c['fault']or v[5]==(5 if c['bad']=='transition_ack'else 0)for v,c in zip(results,rows)))
 d=dict(schema='BYOR_4086_MODEL_SCRIPTS_SERVICE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,script_table_sha256=hashlib.sha256(ct).hexdigest(),factor_table_sha256=hashlib.sha256(ft).hexdigest(),callback_table_sha256=hashlib.sha256(bt).hexdigest(),real_transition_ack=True,full_transition_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
