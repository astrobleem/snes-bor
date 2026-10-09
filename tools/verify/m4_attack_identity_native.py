"""Native unsigned attack sequence and generation-bound entity assignment."""
import argparse,hashlib,itertools,json,re
from pathlib import Path
from m4_check_attack_native import ASM as BASE_ASM,LUA as BASE_LUA
from source_attack_identity_4086 import assign
from source_attack_identity_native import emit
from source_hit_state_native import emit as storage
from source_hit_state_layout import layout
from source_foreign_state_layout import layout as arena
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 plan=layout();sy=symbols(Path('src/main.sym'));ap=arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES']);seq=next(r['address']for r in ap['regions']if r['name']=='attack_identity_sequence')
 values=(0,1,2,65535,65536,0x7fffffff,0x80000000,0xfffffffe,0xffffffff)
 rows=[]
 for slot in (0,1,127):
  for actor,sequence in itertools.product(values,values[1:]):
   out,nextseq=assign(actor,sequence)
   rows.append(dict(slot=slot,actor=actor,sequence=sequence,out=out,nextseq=nextseq,op=0,fault=0))
 seed=dict(rows[0])
 for slot in (0,127):
  for bad in ('phase','pending','time','retired','token','hit_generation','canvas_generation','sequence_marker','zero_sequence','world_view','world_side'):
   rows.append(dict(seed,slot=slot,bad=bad,fault=1))
  rows.append(dict(seed,slot=slot,op=1,sequence=0,nextseq=1,out=seed['actor']))
  rows.append(dict(seed,slot=slot,op=1,bad='initialized',fault=1))
  rows.append(dict(seed,slot=slot,op=2,sequence=0,actor=0,out=2,nextseq=2))
  rows.append(dict(seed,slot=slot,op=3,actor=0,out=2,nextseq=2))
 for c in rows:c.update(handle=1,frame=0,falling=0,projectile=0,drop=0,frozen=0,deadline=0)
 asm=BASE_ASM.replace(' jsl CheckAttack_Run',f' lda.l {plan["controls"]}+24\n beq AttackIdentityProbe_Assign\n cmp #3\n beq AttackIdentityProbe_Twice\n jsl AttackIdentity_Initialize\n bcs AttackGateProbe_Return\n lda.l {plan["controls"]}+24\n cmp #2\n beq AttackIdentityProbe_Assign\n bra AttackGateProbe_Return\nAttackIdentityProbe_Twice:\n.a16\n.i16\n jsl AttackIdentity_Assign\n bcs AttackGateProbe_Return\nAttackIdentityProbe_Assign:\n.a16\n.i16\n jsl AttackIdentity_Assign')
 lua=BASE_LUA.replace('local ranges={','local ranges={{SEQ,6},')
 setup=""" put(hit,c.actor,4);put(HW+4,c.slot);put(HW+24,c.op)
 put(SEQ,c.sequence,4);put(SEQ+4,(c.op==1 or c.op==2)and 0 or 0xb6a2)
 if c.bad=='sequence_marker'then put(SEQ+4,0)elseif c.bad=='zero_sequence'then put(SEQ,0,4)elseif c.bad=='initialized'then put(SEQ+4,0xb6a2)end
 before={};for _,r in ipairs(ranges)"""
 lua=lua.replace(' before={};for _,r in ipairs(ranges)',setup)
 lua=lua.replace(' if c.fault==0 and c.ticket==0 then for i=0,3 do before[HB+16*c.slot+i]=0 end end'," if c.fault==0 then for i=0,3 do before[HB+16*c.slot+i]=(c.out>>(8*i))&255;before[SEQ+i]=(c.nextseq>>(8*i))&255 end;if c.op==1 or c.op==2 then before[SEQ+4]=0xa2;before[SEQ+5]=0xb6 end end")
 lua=lua.replace("'ATTACKGATE|'","'ATTACKIDENTITY|'").replace("..(c.fault==0 and ticket or -1)..","..(c.fault==0 and 0 or -1)..")
 for k,v in dict(HW=plan['controls'],HB=plan['base'],HC=plan['chr_capacity'],CB=0,SEQ=seq).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
 extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'};lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 reporter=Reporter('M4-SOURCE-ATTACK-IDENTITY',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'AttackGateProbe','VmState_Error',0xb6a0,[],lua,reporter,append=asm+storage(plan,sy)+emit(plan,sy),probes={'RETURN':'AttackGateProbe_Return'},batch_size=4,link_pcm=False)
 actual=[list(map(int,l.split('ATTACKIDENTITY|',1)[1].split('|')))for l in log.splitlines()if 'ATTACKIDENTITY|'in l]
 wanted=[[i,0,0,8,-1 if c['fault']else 0,7 if c.get('bad')=='phase'else 8,0 if c.get('bad')=='pending'else 1]for i,c in enumerate(rows)]
 reporter.check('unsigned assignment/reuse/wrap, initialization, exact sibling/hit-by preservation and stale guards',actual==wanted);reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_ATTACK_ID_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),results=actual,expected=wanted,inputs=rows,plan=ap,hit_plan=plan,rom_sha256=hashlib.sha256(raw).hexdigest(),memory_lease_installed_by_fixture=True,full_do_attack_bound=False,target_filter_bound=False,production_global_initialization_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
