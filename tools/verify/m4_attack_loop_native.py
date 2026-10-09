"""Real preparation and ordered target scan; stop before mandatory hit services."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from compiler import Source
from source_hit_contact_layout import layout
from source_hit_state_layout import layout as hits
from source_move_contact_layout import layout as movement
from source_foreign_state_layout import layout as arena
from source_hit_state_native import emit as storage
from source_hit_contact_native import emit as contacts
from source_check_attack_native import emit as gate
from source_attack_identity_native import emit as identity
from source_do_attack_prepare_native import emit as prepare
from source_attack_target_native import emit as target
from source_attack_loop_native import emit, HIT_SERVICE_REQUIRED
from source_checkhit_zero_depth_native import emit as collision
from source_checkhit_zero_depth import derive as geometry
from source_attack_target_requirements import derive_requirements
from source_frame_state_4086 import derive as frames,pack
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from m4_check_attack_native import ASM as BASE_ASM,LUA as BASE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    src=Source(a.source);req=derive_requirements(src);gr=geometry(src);plan=layout();hp=hits();cap=movement()['chr_capacity'];table=pack(frames(src));sy=symbols(Path('src/main.sym'))
    previous=json.load(open('out/byor-motu-attack-target-native/report.json'))
    if previous['status']!='PASS':raise ValueError('ATTACK_LOOP_TARGET_PROOF')
    seed=next(c for c in previous['inputs'] if c['hit'] and not c.get('bad'))
    w=plan['controls'];h=hp['controls'];hb=hp['base'];pb=plan['base'];seq=next(r['address'] for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions'] if r['name']=='attack_identity_sequence')
    rows=[]
    for count in range(1,129):
        for slot in sorted(set((0,count-1))):
            for mode in ('empty','far','hit'):
                targets=[i for i in range(count) if i!=slot] if mode=='hit' else []
                first=targets[0] if targets else count
                rows.append(dict(seed,count=count,slot=slot,mode=mode,targets=targets,first=first,depth=0,falling=0,projectile=0,drop=0,frozen=0,deadline=0,
                    ticket=HIT_SERVICE_REQUIRED if targets else 0,hit=bool(targets),fault=0,state=2 if targets else 3,cursor=first,repeat=False))
    seedcase=dict(next(c for c in rows if c['mode']=='hit' and c['count']==128 and c['slot']==127))
    rows.append(dict(seedcase,repeat=True))
    for bad in ('phase','pending','time','world_view','world_side','canvas_generation','contact_generation','contact_ready','contact_capacity','table_bytes','table_bank','target_generation'):
        rows.append(dict(seedcase,bad=bad,fault=1,ticket=-1))
    setup=r'''
 set('VmSourceWorld_Count',c.count);set('VmSourceWorld_TemplateCount',16)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',16)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Models',16);set('SourceRetirement4086_Ready',0xb4f8)
 put(0x43fd9c,0,4)
 for i=0,127 do
  local av=0x414000+80*i;local as=0x416800+64*i;local al=0x439000+80*i
  put(av,av,4);put(av+4,0,4);put(as,0);put(as+4,c.target_handle);put(as+6,c.target_frame)
  put(al+4,10,4);put(al+12,0,4);put(al+20,0,4);put(al+24,0,4);put(al+72,0);put(al+74,0xb4fb)
  put(0x40c048+96*i,2,4);put(0x42d800+16*i,0,4)
  for _,r in ipairs({{8,c.tp[2]},{48,(c.tp[1]+(c.mode=='far' and 1000*65536 or 0))&0xffffffff},{56,c.tp[3]}})do put(av+r[1],2,4);put(av+r[1]+4,r[2],4)end
  put(av+24,1,4);put(av+28,c.td,4)
  put(HB+16*i,0,4);put(HB+16*i+4,0,4);put(HB+16*i+8,1,4);put(HB+16*i+12,0xb6a1);put(HB+16*i+14,i)
  put(PB+8*i,0,4);put(PB+8*i+4,0,4);put(0x409008+64*i,0,4);put(0x40903a+64*i,0xb638)
 end
 if c.mode=='far'then for i=0,c.count-1 do put(0x414004+80*i,1,4)end end
 for _,i in ipairs(c.targets)do put(0x414004+80*i,1,4)end
 put(v,v,4);put(v+4,1,4);put(side+4,c.handle);put(side+6,c.frame)
 for _,r in ipairs({{8,c.ap[2]},{48,c.ap[1]},{56,c.ap[3]}})do put(v+r[1],2,4);put(v+r[1]+4,r[2],4)end
 put(v+24,1,4);put(v+28,c.ad,4);put(0x40c048+96*c.slot,1,4);put(0x40c030+96*c.slot,2,4);put(0x40c034+96*c.slot,2,4)
 put(HW+4,c.slot);put(HW+20,CAPACITY);put(SEQ,1,4);put(SEQ+4,0xb6a2)
 for i=0,63 do put(CW+i,0,1)end
 put(CW,0xb6a3);put(CW+8,1,4);put(CW+16,PB&65535);put(CW+18,0x42);put(CW+20,CAPACITY);put(CW+22,128)
 if c.bad=='contact_generation'then put(CW+8,2,4)elseif c.bad=='contact_ready'then put(CW,0)
 elseif c.bad=='contact_capacity'then put(CW+20,CAPACITY+2)
 elseif c.bad=='table_bytes'then set('SourceCollisionFrame4086_Bytes',CB-2)
 elseif c.bad=='table_bank'then set('SourceCollisionFrame4086_Bank',59)
 elseif c.bad=='target_generation'then put(HB+16*c.targets[1]+8,2,4)end
 visited={};before={};for _,r in ipairs(ranges)
'''
    lua=BASE_LUA.replace('local ranges={','local visited={}\nlocal ranges={{PB,1024},').replace(' before={};for _,r in ipairs(ranges)',setup)
    lua=lua.replace(' if c.fault==0 and c.ticket==0 then for i=0,3 do before[HB+16*c.slot+i]=0 end end',
                    ' if c.fault==0 or c.bad==\'target_generation\'then for i=0,3 do before[HB+16*c.slot+i]=(2>>(8*i))&255 end end')
    lua=lua.replace("'ATTACKGATE|'","'ATTACKLOOP|'")
    lua=lua.replace("..word(sy.SourceWorldTick4086_Pending))", "..word(sy.SourceWorldTick4086_Pending)..'|'..word(CW+56)..'|'..word(CW+58)..'|'..word(CW+60))\n emu.log('ATTACKVISITS|'..word(INDEX)..'|'..table.concat(visited,','))")
    lua+=r'''
emu.addMemoryCallback(function()visited[#visited+1]=word(CW+56)end,emu.callbackType.exec,TRACE,TRACE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];if c['repeat'] then put(CW+62,1)end end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
'''
    # Probe calls real Begin and Poll in one source call, with an optional pending retry.
    asm=BASE_ASM.replace(' jsl CheckAttack_Run',f''' jsl AttackLoop_Begin
 bcs AttackGateProbe_Return
 cmp #0
 beq AttackGateProbe_Return
 jsl AttackLoop_Poll
 bcs AttackGateProbe_Return
 lda.l {w}+62
 beq AttackGateProbe_Keep
 jsl AttackLoop_Poll
 bra AttackGateProbe_Return
AttackGateProbe_Keep:
.a16
.i16
 lda.l {w}+60
 cmp #2
 bne AttackGateProbe_NoHit
 lda #{HIT_SERVICE_REQUIRED}
 clc
 bra AttackGateProbe_Return
AttackGateProbe_NoHit:
.a16
.i16
 lda #0
 clc''')
    native=storage(hp,sy)+contacts(plan,sy)+gate(hp,sy)+identity(hp,sy)+prepare(req,plan,sy)+collision(gr,hp,sy,58)+target(req,plan,sy)+emit(plan,sy)
    for k,v in dict(HW=h,HB=hb,HC=cap,CAPACITY=cap,CB=len(table),CW=w,PB=pb,SEQ=seq).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    extra={k:v for k,v in sy.items() if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_')) or k=='DmaQueue'}
    lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
    reporter=Reporter('M4-ORDERED-ATTACK-LOOP',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'AttackGateProbe','VmState_Error',0xb6a0,[(58,0,table)],lua,reporter,
        append=asm+native,probes=dict(RETURN='AttackGateProbe_Return',TRACE='AttackTarget_Run'),batch_size=4,frame_limit=7000,link_pcm=False)
    actual=[list(map(int,l.split('ATTACKLOOP|',1)[1].split('|'))) for l in log.splitlines() if 'ATTACKLOOP|' in l]
    visits=[]
    for l in log.splitlines():
        if 'ATTACKVISITS|' in l:
            idx,tail=l.split('ATTACKVISITS|',1)[1].split('|')
            visits.append([int(idx),[int(n) for n in tail.split(',') if n]])
    failures=[]
    for i,c in enumerate(rows):
        if c['fault']:
            expected=[i,0,0,8,-1,7 if c.get('bad')=='phase' else 8,0 if c.get('bad')=='pending' else 1]
            if i>=len(actual) or actual[i][:7]!=expected:failures.append(dict(index=i,actual=actual[i] if i<len(actual) else None,expected_prefix=expected))
        else:
            expected=[i,0,0,8,c['ticket'],8,1,c['cursor'],c['first'] if c['hit'] else 65535,c['state']]
            expected_visits=list(range(c['first']+1 if c['hit'] else c['count']))
            if i>=len(actual) or actual[i]!=expected or i>=len(visits) or visits[i]!=[i,expected_visits]:failures.append(dict(index=i,input=c,actual=actual[i] if i<len(actual) else None,expected=expected,visits=visits[i] if i<len(visits) else None,expected_visits=expected_visits))
    reporter.check('real ordered scan, all empty/far candidates, first admitted target, pending retry and unchanged actors/world',len(actual)==len(rows) and not failures)
    reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
    report=dict(schema='BYOR_ORDERED_ATTACK_LOOP_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',cases=len(rows),inputs=rows,results=actual,visits=visits,failures=failures,
        rom_sha256=hashlib.sha256(raw).hexdigest(),chr_capacity=cap,control_tail=[w+56,w+64],mandatory_hit_ticket=HIT_SERVICE_REQUIRED,
        actual_native_preparation_target_and_collision=True,ondoattack_and_hit_services_bound=False,defense_threshold_expression_excluded=True,
        source_float_equivalence=False,production_world_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
