"""Actual phase8 attack gate, physical owner traversal and identity preparation."""
import argparse,hashlib,itertools,json,re
from pathlib import Path
from m4_check_attack_native import ASM as BASE_ASM,LUA as BASE_LUA
from compiler import Source
from source_hit_state_layout import layout as hits
from source_hit_contact_layout import layout
from source_hit_state_native import emit as storage
from source_check_attack_native import emit as gate
from source_attack_identity_native import emit as ids
from source_do_attack_prepare_native import emit,TARGET_LOOP_REQUIRED
from source_attack_target_requirements import derive_requirements
from source_foreign_state_layout import layout as arena
from source_frame_state_4086 import derive as frames,pack,unpack
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 src=Source(a.source);req=derive_requirements(src);table=pack(frames(src));data=unpack(table);plan=layout();hp=hits();sy=symbols(Path('src/main.sym'));seq=next(r['address']for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_identity_sequence')
 active=next((anim['handle'],f,frame)for anim in data['animations']for f,frame in enumerate(anim['frames'])if frame['attack_index']);inactive=next((anim['handle'],f,frame)for anim in data['animations']for f,frame in enumerate(anim['frames'])if not frame['attack_index'])
 rows=[]
 for slot,depth,projectile,actor_id,sequence,completed in itertools.product((0,1,127),(0,1,3),(-65536,0,1,65536),(0,0x80000000),(1,0xffffffff),(0,1)):
  handle,frame,meta=active;force=data['attacks'][meta['attack_index']-1]['attack_force'];top=(slot+depth)%128;outid=actor_id or(2 if sequence==1 else 1);nextseq=sequence if actor_id else outid
  rows.append(dict(slot=slot,handle=handle,frame=frame,depth=depth,falling=0,projectile=projectile,drop=0,frozen=0,deadline=0,fault=0,actor_id=actor_id,sequence=sequence,completed=completed,ticket=0 if completed else TARGET_LOOP_REQUIRED,outid=actor_id if completed else outid,nextseq=sequence if completed else nextseq,record=[0x414000+80*top,0x80010001 if projectile>0 else 0x00010001,force&0xffffffff,handle|(frame<<16),outid,0xb6a4|(top<<16)]))
 seed=dict(rows[0]);rows.append(dict(seed,handle=inactive[0],frame=inactive[1],ticket=0,outid=0,nextseq=seed['sequence']))
 rows.append(dict(seed,depth=127,record=[0x414000+80*127,0x00010001,seed['record'][2],seed['record'][3],seed['outid'],0xb6a4|(127<<16)]))
 for bad in ('phase','pending','time','world_view','world_side','self','hit_generation','canvas_generation','retirement','relation_marker','owner_pointer','owner_cycle','sequence_marker','sequence_zero','contact_ready','contact_generation','contact_capacity','hit_capacity','table_bytes','table_bank'):
  rows.append(dict(seed,bad=bad,fault=1))
 setup=r"""
 for i=0,8191 do put(0x409000+i,0,1)end
 for i=0,127 do put(0x40903a+64*i,0xb638)end
 for i=0,c.depth-1 do put(0x409008+64*((c.slot+i)%128),0x414000+80*((c.slot+i+1)%128),4)end
 put(0x43fd9c,c.completed,4);set('SourceRetirement4086_Ready',0xb4f8)
 put(0x40c030+96*c.slot,0x00010001,4);put(0x40c034+96*c.slot,0x80010001,4)
 put(HW+20,HC);put(HW+4,c.slot);put(HB+16*c.slot,c.actor_id,4)
 put(SEQ,c.sequence,4);put(SEQ+4,0xb6a2)
 for i=0,63 do put(CW+i,0,1)end;put(CW,0xb6a3);put(CW+8,1,4);put(CW+20,HC)
 for i=0,23 do put(CW+32+i,165,1)end
 if c.bad=='retirement'then set('SourceRetirement4086_Ready',0)
 elseif c.bad=='relation_marker'then put(0x40903a+64*c.slot,0)
 elseif c.bad=='owner_pointer'then put(0x409008+64*c.slot,0x414001,4)
 elseif c.bad=='owner_cycle'then put(0x409008+64*c.slot,0x414000+80*c.slot,4)
 elseif c.bad=='sequence_marker'then put(SEQ+4,0)
 elseif c.bad=='sequence_zero'then put(SEQ,0,4)
 elseif c.bad=='contact_ready'then put(CW,0)
 elseif c.bad=='contact_generation'then put(CW+8,2,4)
 elseif c.bad=='contact_capacity'then put(CW+20,HC+2)
 elseif c.bad=='hit_capacity'then put(HW+20,HC+2)
 elseif c.bad=='table_bytes'then set('SourceCollisionFrame4086_Bytes',CB-2)
 elseif c.bad=='table_bank'then set('SourceCollisionFrame4086_Bank',59)end
 before={};for _,r in ipairs(ranges)
"""
 lua=BASE_LUA.replace('local ranges={','local ranges={{0x409000,8192},{CW+32,24},{SEQ,6},')
 lua=lua.replace(' before={};for _,r in ipairs(ranges)',setup)
 lua=lua.replace(' if c.fault==0 and c.ticket==0 then for i=0,3 do before[HB+16*c.slot+i]=0 end end'," if c.fault==0 then for i=0,3 do before[HB+16*c.slot+i]=(c.outid>>(8*i))&255;before[SEQ+i]=(c.nextseq>>(8*i))&255 end;if c.ticket==33040 then for n,v in ipairs(c.record)do for i=0,3 do before[CW+32+(n-1)*4+i]=(v>>(8*i))&255 end end end end")
 lua=lua.replace("'ATTACKGATE|'","'DOATTACKPREP|'")
 for k,v in dict(HW=hp['controls'],HB=hp['base'],HC=plan['chr_capacity'],CB=len(table),CW=plan['controls'],SEQ=seq).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
 extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'};lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 asm=BASE_ASM.replace('CheckAttack_Run','DoAttackPrepare_Run')+storage(hp,sy)+gate(hp,sy)+ids(hp,sy)+emit(req,plan,sy)
 reporter=Reporter('M4-SOURCE-DO-ATTACK-PREPARE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AttackGateProbe','VmState_Error',0xb6a0,[(58,0,table)],lua,reporter,append=asm,probes={'RETURN':'AttackGateProbe_Return'},batch_size=4,link_pcm=False)
 actual=[list(map(int,l.split('DOATTACKPREP|',1)[1].split('|')))for l in log.splitlines()if 'DOATTACKPREP|'in l];wanted=[[i,0,0,8,-1 if c['fault']else c['ticket'],7 if c.get('bad')=='phase'else 8,0 if c.get('bad')=='pending'else 1]for i,c in enumerate(rows)]
 reporter.check('real attack gate, owner chains, mask/ID/force/cursor capture, mandatory loop ticket and no fabricated world Ack',actual==wanted);reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_DO_ATTACK_PREPARE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,results=actual,expected=wanted,rom_sha256=hashlib.sha256(raw).hexdigest(),ready_ticket=TARGET_LOOP_REQUIRED,record_control_range=[plan['controls']+32,plan['controls']+56],memory_lease_installed_by_fixture=True,defense_threshold_expression_excluded=True,ordered_target_loop_bound=False,damage_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
