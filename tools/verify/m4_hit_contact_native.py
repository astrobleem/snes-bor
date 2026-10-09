"""Native pain/juggle row primitives with paired hit and foreign leases."""
import argparse,hashlib,json,re
from pathlib import Path
from m4_hit_state_native import ASM as BASE_ASM,LUA as BASE_LUA
from m4_check_attack_native import LUA as FOREIGN_LUA
from source_hit_state_layout import layout as hits
from source_hit_contact_layout import layout
from source_hit_state_native import emit as hit_storage
from source_hit_contact_native import emit
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 plan=layout();hp=hits();sy=symbols(Path('src/main.sym'))
 rows=[dict(slot=s,op=op,attack=(0xffffffff,0x80000000,0,0x7fffffff)[s%4],hitby=(0,1,0x80000001,0xffffffff)[s%4],fault=0)for s in range(128)for op in range(4)]
 seed=dict(rows[0]);rows.append(dict(seed,op=4))
 for slot in (0,127):
  for bad in ('ready','zero_generation','generation_low','generation_high','capacity','base','bank','world','zero_count','large_count','slot','entity_count','marker','row_generation','row_generation_high','row_slot','foreign_generation','foreign_ready','hit_capacity','hit_base','hit_slot'):
   rows.append(dict(seed,slot=slot,op=3,bad=bad,fault=1))
 rows.append(dict(seed,op=4,bad='initialized',fault=1))
 asm=BASE_ASM.replace('W+24','W+32').replace('HitState_ClearBirth','HitContact_Birth').replace('HitState_Write','HitContact_Write').replace('HitState_ResetAttack','HitContact_CopyModel').replace(' jsl HitState_Read',' cmp #4\n beq HitContactProbe_Init\n jsl HitContact_Read').replace('HitStateProbe_Return:\n','HitContactProbe_Init:\n.a16\n.i16\n jsl HitContact_Initialize\nHitStateProbe_Return:\n',1)
 asm=asm.replace(' jsl HitContact_CopyModel\nHitContactProbe_Init:', ' jsl HitContact_CopyModel\n bra HitStateProbe_Return\nHitContactProbe_Init:')
 # Normal Read must skip the initializer, while the selected Init branches to it.
 asm=asm.replace(' jsl HitContact_Read\n bra HitStateProbe_Return',' jsl HitContact_Read\n bra HitStateProbe_Return')
 lua=BASE_LUA.replace('local function put(a,v,n)', 'local function put(a,v,n)')
 lua=lua.replace('emu.addMemoryCallback(function()',"local function set(k,v)put(sy[k],v)end\nemu.addMemoryCallback(function()",1)
 # Hit rows use their own lease/control addresses; contact rows are separately compared.
 foreign=FOREIGN_LUA[FOREIGN_LUA.index(" set('SourceForeignWork_Ready'"):FOREIGN_LUA.index(" if c.bad=='phase'")]
 setup="""
 for j=0,63 do put(HW+j,0,1)end
 for j=0,2047 do put(HB+j,(j*11+17)&255,1)end
 local ha=HB+16*c.slot
 put(HW,0xb6a0);put(HW+4,c.slot);put(HW+8,0x12345678,4);put(HW+16,HB%65536);put(HW+18,0x42);put(HW+20,CAPACITY);put(HW+22,128)
 put(ha,0xffffffff,4);put(ha+4,0x80000000,4);put(ha+8,0x12345678,4);put(ha+12,0xb6a1);put(ha+14,c.slot)
 put(W, c.op==4 and 0 or 0xb6a3);put(W+24,c.attack,4);put(W+28,c.hitby,4);put(W+32,c.op)
 put(at,0xffffffff,4);put(at+4,0x80000000,4)
"""+foreign+"""
 put(sy.SourceForeignWork_Generation,0x12345678,4)
 if c.bad=='marker'then put(ha+12,0)elseif c.bad=='row_generation'then put(ha+8,0,4)
 elseif c.bad=='row_generation_high'then put(ha+10,0)elseif c.bad=='row_slot'then put(ha+14,(c.slot+1)%128)
 elseif c.bad=='foreign_generation'then put(sy.SourceForeignWork_Generation,2,4)
 elseif c.bad=='foreign_ready'then set('SourceForeignWork_Ready',0)
 elseif c.bad=='hit_capacity'then put(HW+20,CAPACITY+2)
 elseif c.bad=='hit_base'then put(HW+16,HB%65536+2)
 elseif c.bad=='hit_slot'then put(HW+4,(c.slot+1)%128)
 elseif c.bad=='initialized'then put(W,0xb6a3)end
 before={};for j=-8,SIZE+7 do before[BASE+j]=emu.read(BASE+j,mt)end
 for j=0,2047 do before[HB+j]=emu.read(HB+j,mt)end
 before[HW+2]=nil;before[HW+3]=nil;before[HW+6]=nil;before[HW+7]=nil
 cpu=emu.getState()
"""
 lua=lua.replace('BASE+16*c.slot','BASE+8*c.slot').replace('put(at+8,0x12345678,4);put(at+12,0xb6a1);put(at+14,c.slot)','')
 start=lua.index(' before={};for j=-8,SIZE+7');end=lua.index('end,emu.callbackType.exec,INIT',start)
 lua=lua[:start]+setup+lua[end:]
 # Seeded generic old marker is invalid for contact state; explicit mutations come after setup.
 lua=lua.replace("if c.bad=='ready'then put(W,0)","if c.bad=='ready'then put(W,1)")
 # Original faults affecting contact control remain; hit-row faults are applied by setup above.
 start=lua.index(' if c.fault==0 then');end=lua.index(' local n=0;',start)
 lua=lua[:start]+""" if c.fault==0 then
  if c.op==0 then expect(at,0,4);expect(at+4,c.hitby,4)
  elseif c.op==1 then expect(at,c.attack,4);expect(at+4,c.hitby,4)
  elseif c.op==2 then expect(at+4,c.hitby,4)
  elseif c.op==4 then for j=0,SIZE-1 do before[BASE+j]=0 end end
 end
"""+lua[end:]
 lua=lua.replace('W+28+j','W+24+j').replace("'HITSTATE|'","'HITCONTACT|'")
 # Restore control fault mutations that setup overrides or old row offsets would corrupt.
 start=lua.index(" if c.bad=='ready'");end=lua.index(' for j=0,63 do put(HW',start)
 lua=lua[:start]+lua[end:]
 mutations=""" if c.bad=='ready'then put(W,1)elseif c.bad=='zero_generation'then put(W+8,0,4)
 elseif c.bad=='generation_low'then put(W+8,0x12345679,4)elseif c.bad=='generation_high'then put(W+10,0)
 elseif c.bad=='capacity'then put(W+20,CAPACITY+2)elseif c.bad=='base'then put(W+16,BASE%65536+2)
 elseif c.bad=='bank'then put(W+18,0x43)elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='zero_count'then put(sy.VmSourceWorld_Count,0)elseif c.bad=='large_count'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='slot'then put(W+4,128)elseif c.bad=='entity_count'then put(W+22,127)end
"""
 lua=lua.replace(' before={};for j=-8,SIZE+7',mutations+' before={};for j=-8,SIZE+7',1)
 replacements=dict(W=plan['controls'],BASE=plan['base'],SIZE=plan['bytes'],CAPACITY=plan['chr_capacity'],HW=hp['controls'],HB=hp['base'])
 for n,v in replacements.items():asm=re.sub(r'\b'+n+r'\b',str(v),asm);lua=re.sub(r'\b'+n+r'\b',str(v),lua)
 extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'};lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 reporter=Reporter('M4-SOURCE-HIT-CONTACT-STORAGE',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'HitStateProbe','VmState_Error',0xb6a0,[],lua,reporter,append=asm+hit_storage(hp,sy)+emit(plan,sy),probes={'RETURN':'HitStateProbe_Return'},batch_size=4,link_pcm=False)
 actual=[list(map(int,l.split('HITCONTACT|',1)[1].split('|')))for l in log.splitlines()if 'HITCONTACT|'in l];wanted=[[i,3 if c['fault']else 2,0,0,0,8]for i,c in enumerate(rows)]
 reporter.check('all contact rows, unsigned values, birth/read/write/model-copy/init, hit identities, stale guards and CPU',actual==wanted);reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_SOURCE_HIT_CONTACT_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),results=actual,expected=wanted,plan=plan,rom_sha256=hashlib.sha256(raw).hexdigest(),constructor_values_installed_by_fixture=True,production_memory_lease=False,full_damage_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
