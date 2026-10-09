"""Actual freeze/movement callbacks, displacement, timer and blocked-path owner."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
from compiler import Source
from source_trymove_requirements import derive
from source_move_contact_layout import layout
from source_hit_state_layout import layout as hits
from source_foreign_state_layout import layout as arena
from source_check_move_callback_native import emit
from source_check_move_callback_authority import evaluate
from source_trymove_authority import cases
from actor_s5_entity_fixture import symbols
from m4_check_move_native import LUA as BASE_LUA
from m4_check_attack_native import LUA as FOREIGN_LUA
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter
import struct

ASM='''CallbackMoveProbe:
.a16
.i16
 php
 sed
 jsl CallbackCheckMove_Execute
CallbackMoveProbe_Return:
.a16
.i16
 bcs CallbackMoveProbe_Bad
 plp
 clc
 rtl
CallbackMoveProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    req=derive(Source(a.source));plan=layout();hp=hits();sy=symbols(Path('src/main.sym'))
    w=next(r['address'] for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions'] if r['name']=='attack_chain_controls');m=plan['controls'];b=plan['base'];h=hp['controls'];hb=hp['base']
    base=dict(cases()[0],throw=0,grab=0,found=0);rows=[]
    for slot,mark,frozen,time,nextmove,callback,position,motion in itertools.product((0,1,127),(0,4),(0,1),(48,49,0xffffffff),(48,0xffffffff),(0,1,2),((80.,220.),(9.,189.),(311.,241.)),((0.,0.),(1.5,-.25))):
        c=dict(base,x=position[0],z=position[1],xd=motion[0],zd=motion[1],mark=mark,frozen=frozen,time=time,nextmove=nextmove,callback=callback,
            idling=(0,1,-65536)[len(rows)%3],grabbing=0,grabwalking=(0,1,-65536)[len(rows)%3],pathblocked=(0,1,0xffffffff,0x80000000)[len(rows)%4])
        v=evaluate(c);q=lambda f:int(f*65536)&0xffffffff
        expected=[q(struct.unpack('<f',struct.pack('<I',u))[0]) for u in v[:4]]+v[4:6]
        rows.append(dict(slot=slot,time=time,freeze=frozen,mark=mark,nextmove=nextmove,callback=(0,3,9)[callback],x=q(c['x']),z=q(c['z']),mx=q(c['xd']),mz=q(c['zd']),expected=expected,
            blocked=c['pathblocked'],outblocked=v[6],grabwalking=c['grabwalking']&0xffffffff,grabbing=0,idling=c['idling']&0xffffffff,bad='',fault=0,world_state=1))
    seed=dict(rows[0],mark=0,freeze=0,time=49,nextmove=48,callback=3,mx=98304,mz=0,x=80*65536,z=220*65536,blocked=0,idling=1,grabwalking=0)
    for bad in ('ready','status','world','tick','state','phase','pending','tickfault','count','slot','time','self','selffault','selfactive','freeze','aux','platform','walls','stage','lifelease','modelrange','modelidentity','xtag','zreserved','token','exists','movelease','movegeneration','movecapacity','hitgeneration','callback','grablinked','candidate'):
        rows.append(dict(seed,bad=bad,fault=1,outblocked=seed['blocked'],expected=[seed['x'],seed['z'],seed['mx'],seed['mz'],seed['nextmove'],seed['mark']]))
    rows=[dict(c,world_state=s) for s in (1,2) for c in rows]
    lua=BASE_LUA.replace("set('VmSourceWorld_TemplateCount',1)","set('VmSourceWorld_TemplateCount',16)").replace("set('SourceModelEntityCopy4086_Models',1)","set('SourceModelEntityCopy4086_Models',16)").replace("set('SourceEmptyInitEnvironment4086_Models',1)","set('SourceEmptyInitEnvironment4086_Models',16)").replace('put(life+8,0,4)','put(life+8,c.callback,4)')
    foreign=FOREIGN_LUA[FOREIGN_LUA.index(" set('SourceForeignWork_Ready'"):FOREIGN_LUA.index(" if c.bad=='phase'")]
    setup=f'''
 for i=0,95 do put({w}+i,0,1)end
 put({w},0xb6a5);put({w}+6,1);put({w}+8,16);put({w}+10,s);put({w}+12,1,4)
 set('SourceWorldTick4086_View',80*s);set('SourceWorldTick4086_Side',64*s)
 set('SourceCameraMotion4086_Ready',0xb5db);set('SourceCameraMotion4086_HRes',320);set('SourceCameraMotion4086_MinZ',190*65536,4);set('SourceCameraMotion4086_MaxZ',240*65536,4);set('VmSourceWorld_AdvanceX',0,4)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_RowBytes',336)
 for i=0,5375 do put(0x43c000+i,0,1)end
 set('SourceCRandom4086_Ready',0xb5ea);set('SourceCRandom4086_Profile',1);set('SourceCRandom4086_Busy',0);set('SourceCRandom4086_SeedLo',1,4);set('SourceCRandom4086_CallsLo',0,4)
 for i=0,127 do put(0x414004+80*i,0,4);put(0x40c048+96*i,0,4)end
 put(v+4,1,4);put(0x40c048+96*s,1,4)
 put(0x40c00c+96*s,1,4);put(0x40c018+96*s,1,4);put(0x40c01c+96*s,1,4);put(0x40c020+96*s,1,4);put(0x40c050+96*s,c.grabbing,4);put(0x43eb00+32*s,c.idling,4)
 for i=0,63 do put({m}+i,0,1);put({h}+i,0,1)end
 put({m},0xb6a6);put({m}+8,1,4);put({m}+16,{b}&65535);put({m}+18,0x42);put({m}+20,47936);put({m}+22,128)
 put({b}+8*s,c.blocked,4);put({b}+8*s+4,c.grabwalking,4)
 put({h},0xb6a0);put({h}+8,1,4);put({h}+16,{hb}&65535);put({h}+18,0x42);put({h}+20,47936);put({h}+22,128)
 put({hb}+16*s+8,1,4);put({hb}+16*s+12,0xb6a1);put({hb}+16*s+14,s)
'''+foreign+f'''
 if c.bad=='movelease'then put({m},0)elseif c.bad=='movegeneration'then put({m}+8,2,4)elseif c.bad=='movecapacity'then put({m}+20,47938)
 elseif c.bad=='hitgeneration'then put({hb}+16*s+8,2,4)elseif c.bad=='callback'then put(life+8,8,4)
 elseif c.bad=='grablinked'then put(0x40c050+96*s,1,4);put({b}+8*s+4,1,4)
 elseif c.bad=='candidate'then local o=(s+1)%128;put(0x414004+80*o,1,4);put(0x40c048+96*o,8,4)end
'''
    # Set up core rows before the old fixture applies its admission mutations.
    anchor=" local faults={ready="
    if lua.count(anchor)!=1:raise ValueError('CALLBACK_MOVE_FIXTURE_SETUP')
    lua=lua.replace(anchor,setup+anchor)
    lua=lua.replace("{sy.SourceSelf4086_GlobalLow,4}",f"{{sy.SourceSelf4086_GlobalLow,4}},{{{b},1024}},{{{hb},2048}}")
    anchor=' local n=0;for a,v in pairs(before)do'
    update=f''' if c.fault==0 then for i=0,3 do before[{b}+8*s+i]=(c.outblocked>>(8*i))&255 end end
'''
    lua=lua.replace(anchor,update+anchor)
    lua=lua.replace("..dw(freeze+36))",f"..dw(freeze+36)..'|'..dw({b}+8*s))")
    extra={k:v for k,v in sy.items() if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_')) or k=='DmaQueue'}
    lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
    reporter=Reporter('M4-CHECK-MOVE-CALLBACK',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'CallbackMoveProbe','SourceCheckMove4086_Ready',0xb617,[],lua,reporter,append=ASM+emit(req,plan,sy),batch_size=4,frame_limit=6000,link_pcm=False)
    actual=[list(map(int,l.split('CHECKMOVE|',1)[1].split('|'))) for l in log.splitlines() if 'CHECKMOVE|' in l]
    expected=[[i,0,0,3 if c['fault'] else 2,*c['expected'],c['outblocked']] for i,c in enumerate(rows)]
    failures=[dict(index=i,input=rows[i],actual=actual[i] if i<len(actual) else None,expected=e) for i,e in enumerate(expected) if i>=len(actual) or actual[i]!=e]
    reporter.check('actual flat callback, freeze, displacement, nextmove, mark, pathblocked wrap and all sibling rows',not failures and len(actual)==len(rows))
    report=dict(schema='BYOR_4086_CHECK_MOVE_CALLBACK_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',cases=len(rows),inputs=rows,results=actual,failures=failures,
        rom_sha256=hashlib.sha256(raw).hexdigest(),plan=plan,coordinate_policy='ACCEPTED_COMPAT_Q16_16',linked_grabwalking_owner_bound=False,
        production_phase11_owner_bound=False,constructor_hooks_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
