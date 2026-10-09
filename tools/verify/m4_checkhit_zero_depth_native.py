"""Live native source rectangle collision through paired current-frame readers."""
import argparse,hashlib,json,struct
from pathlib import Path
from m4_check_attack_native import ASM as BASE_ASM,LUA as BASE_LUA
from compiler import Source
from source_hit_state_layout import layout
from source_hit_state_native import emit as storage
from source_checkhit_zero_depth import derive
from source_checkhit_zero_depth_native import emit
from source_frame_state_4086 import pack,derive as frame_ir,unpack
from source_checkhit_q16 import checkhit,q16
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case-index',type=int);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);requirements=derive(source);table=pack(frame_ir(source));data=unpack(table);plan=layout();sy=symbols(Path('src/main.sym'));rows=[];active={};boxed={}
 for anim in data['animations']:
  for f,frame in enumerate(anim['frames']):
   if frame['attack_index']:active.setdefault(frame['attack_index'],(anim['handle'],f,frame))
   if frame['bbox_index']:boxed.setdefault(frame['bbox_index'],(anim['handle'],f,frame))
 poses=[((0,0,0),(0,0,0)),((80.5,0,12.25),(80.5,0,12.25)),((-.9999847412109375,.0000152587890625,0),(.9999847412109375,-.0000152587890625,0)),((200.5,0,30.25),(201.5,0,42.25)),((200.5,.5,30.25),(201.5,.5,100.25)),((-80.5,-1.5,-12.25),(-80.5,1.5,-12.25))]
 cursors=list(boxed.values())+[v for v in active.values()if v[2]['bbox_index']]
 for n,target in enumerate(cursors):
  ah,af,arf=active[n%len(active)+1];th,tf,trf=target
  for ad,td in ((0,0),(0,1),(1,0),(1,1)):
   for pi,(ap,tp)in enumerate(poses):
    for counter in (0,1):
     slot=(0,1,127)[len(rows)%3];target_slot=(slot+1)%128
     attacker=dict(token=slot,position=ap,direction=ad,grabdistance=requirements['models'][0]['grabdistance'],attack_table=True,attack=data['attacks'][arf['attack_index']-1])
     defender=dict(token=target_slot,position=tp,direction=td,bbox_table=True,vulnerable=bool(trf['bbox_index']),bbox=data['boxes'][trf['bbox_index']-1],attack_table=bool(trf['attack_index']),attack=data['attacks'][trf['attack_index']-1]if trf['attack_index']else None)
     hit=checkhit(attacker,defender,counter)
     rows.append(dict(slot=slot,target_slot=target_slot,handle=ah,frame=af,target_handle=th,target_frame=tf,ap=[q16(v)&0xffffffff for v in ap],tp=[q16(v)&0xffffffff for v in tp],ad=ad,td=td,counter=counter,hit=int(hit is not None),contact=[hit[k]&0xffffffff for k in ('x','y','z','type','confirm')]if hit else None,falling=0,projectile=0,drop=0,frozen=0,deadline=0,fault=0))
 seed=next(r for r in rows if r['hit'])
 for anim in data['animations']:
  for f,frame in enumerate(anim['frames']):
   if not frame['bbox_index']:
    rows.append(dict(seed,target_handle=anim['handle'],target_frame=f,hit=0,contact=None))
    break
 for bad in ('phase','pending','time','world_side','world_view','self','retired','token','hit_generation','canvas_generation','collision','coordinate_tag','direction_tag','counter','table_bank','table_bytes','collision_sticky','target_retired','target_token','target_coordinate_tag','target_direction_tag','rectangle_overflow','altitude_overflow'):
  if bad in ('world_side','world_view','self'):continue
  rows.append(dict(seed,bad=bad,fault=1))
 rows.append(dict(seed,target_slot=seed['slot'],hit=0,contact=None))
 if a.case_index is not None:rows=[rows[a.case_index]]
 setup=r"""
 local tv=0x414000+80*c.target_slot;local ts=0x416800+64*c.target_slot
 put(tv,tv,4);put(tv+4,1,4);put(ts+4,c.target_handle);put(ts+6,c.target_frame)
 for _,pair in ipairs({{v,c.ap,c.ad},{tv,c.tp,c.td}})do local at=pair[1];local pose=pair[2]
  put(at+8,2,4);put(at+12,pose[2],4);put(at+48,2,4);put(at+52,pose[1],4);put(at+56,2,4);put(at+60,pose[3],4);put(at+24,1,4);put(at+28,pair[3],4)
 end
 put(HW+4,c.slot);put(HW+24,c.counter);put(HW+26,c.target_slot);for i=0,19 do put(HW+44+i,165,1)end
 if c.bad=='coordinate_tag'then put(v+48,1,4)
 elseif c.bad=='direction_tag'then put(tv+24,2,4)
 elseif c.bad=='counter'then put(HW+24,2)
 elseif c.bad=='table_bank'then set('SourceCollisionFrame4086_Bank',59)
 elseif c.bad=='table_bytes'then set('SourceCollisionFrame4086_Bytes',CB-2)
 elseif c.bad=='target_retired'then put(tv+4,0,4)
 elseif c.bad=='target_token'then put(tv,tv+1,4)
 elseif c.bad=='target_coordinate_tag'then put(tv+56,1,4)
 elseif c.bad=='target_direction_tag'then put(tv+26,1)
 elseif c.bad=='rectangle_overflow'then put(v+52,0x7fffffff,4);put(tv+52,0x7fffffff,4);put(v+28,1,4);put(tv+28,1,4)
 elseif c.bad=='altitude_overflow'then put(v+12,0x80000000,4);put(v+60,0x7fffffff,4);put(tv+60,0x7fffffff,4)
 elseif c.bad=='collision_sticky'then set('SourceCollisionFrame4086_Status',3)end
 before={};for _,r in ipairs(ranges)
"""
 lua=BASE_LUA.replace('local ranges={','local ranges={{HW+44,20},')
 lua=lua.replace(' before={};for _,r in ipairs(ranges)',setup)
 lua=lua.replace(' if c.fault==0 and c.ticket==0 then for i=0,3 do before[HB+16*c.slot+i]=0 end end'," if c.fault==0 and c.hit==1 then for n,value in ipairs(c.contact)do for i=0,3 do before[HW+44+(n-1)*4+i]=(value>>(8*i))&255 end end end")
 lua=lua.replace("'ATTACKGATE|'","'CHECKHIT|'")
 import re
 for k,v in dict(HW=plan['controls'],HB=plan['base'],HC=plan['chr_capacity'],CB=len(table)).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
 extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'};lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 lua+='\nemu.addMemoryCallback(function()local s=emu.getState();emu.log("GEOMETRYBAD|"..word(INDEX).."|a="..s["cpu.a"].."|ps="..s["cpu.ps"].."|x="..s["cpu.x"].."|collision="..word(sy.SourceCollisionFrame4086_Status).."|slot="..word(HW+4).."|target="..word(HW+26));local b=s["cpu.d"];for _,off in ipairs({24,26,28,30,32,34,36,38,40,42,44,46,48,50,88,90,96,98,100,102,52,54,56,58,60,62,64,66})do emu.log("GEODP|"..off.."|"..word(b+off))end end,emu.callbackType.exec,GEOBAD,GEOBAD,emu.cpuType.snes,mt)\n'
 lua=re.sub(r'\bHW\b',str(plan['controls']),lua)
 asm=BASE_ASM.replace('CheckAttack_Run','CheckHit_Run')+storage(plan,sy)+emit(requirements,plan,sy,58)
 reporter=Reporter('M4-SOURCE-CHECKHIT-ZERO-DEPTH',kind='GATE')
 def hook(raw,linked):
  if linked['CheckHit_CodeEnd']>>16!=39:raise ValueError('CHECKHIT_PRIVATE_CODE_BANK')
 raw,log=run_fixture(a.rom,a.output,rows,'AttackGateProbe','VmState_Error',0xb6a0,[(58,0,table)],lua,reporter,append=asm,probes={'RETURN':'AttackGateProbe_Return','GEOBAD':'CheckHit_Bad'},rom_transform=hook,batch_size=4,frame_limit=10000,link_pcm=False)
 actual=[list(map(int,l.split('CHECKHIT|',1)[1].split('|')))for l in log.splitlines()if 'CHECKHIT|'in l]
 wanted=[[i,0,0,8,-1 if c['fault']else c['hit'],7 if c.get('bad')=='phase'else 8,0 if c.get('bad')=='pending'else 1]for i,c in enumerate(rows)]
 reporter.check('actual current-frame query, every source box/attack identity, source numeric adaptation, contact/no-hit preservation and CPU',actual==wanted)
 reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_CHECKHIT_ZERO_DEPTH_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,results=actual,expected=wanted,requirements=requirements,plan=plan,rom_sha256=hashlib.sha256(raw).hexdigest(),numeric_policy='EXISTING_Q16_COORDINATE_ADAPTATION',source_binary32_equivalence_claim=False,memory_lease_installed_by_fixture=True,world_phase_installed_by_fixture=True,do_attack_bound=False,world_acknowledgements=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
