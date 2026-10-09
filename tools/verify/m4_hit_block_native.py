"""Real ordered collision/prelude, then live block choice and source rand32."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch
import m4_attack_loop_native as loop
from compiler import Source
from source_hit_block_requirements import derive
from source_hit_block_native import emit,PASSIVE_BLOCK_REQUIRED,ACTIVE_BLOCK_REQUIRED,DAMAGE_REQUIRED
from source_hit_block_4086 import choose
from source_actor_numeric import random32_step
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();req=derive(Source(a.source));sy=symbols(Path('src/main.sym'));original=loop.run_fixture
    w=loop.layout()['controls'];h=loop.hits()['controls'];failures=[];observed=[];custom=[]
    def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
        seed=next(c for c in rows if c['slot']==0 and c['count']==128 and c['mode']=='hit' and not c.get('bad'))
        for slot,valid,mode,seed_value in itertools.product((0,1,127),(0,1),range(9),(0,1,0xffffffff)):
            target=(slot+1)%128
            c=dict(seed,slot=slot,count=128,first=target,cursor=target,targets=[target],state=5,repeat=True,bad='',fault=0,
                valid_block=valid,nopassive=0,blocking=0,tdir=1,adir=0,air=0,tfrozen=0,tidling=1,tattacking=0,tlink=0,odds=1,seed_value=seed_value,bomb_attacker=1,bomb_target=1)
            if mode==1:c.update(nopassive=1,blocking=1)
            elif mode==2:c.update(tdir=0)
            elif mode==3:c.update(air=6554)
            elif mode==4:c.update(tfrozen=-1)
            elif mode==5:c.update(tidling=0,tattacking=0)
            elif mode==6:c.update(tidling=0,tattacking=-1)
            elif mode==7:c.update(tlink=1)
            elif mode==8:c.update(odds=0)
            d=dict(nopassiveblock=c['nopassive'],guardmax=0,guardcurrent=0,link=c['tlink'],direction=c['tdir'],blockback=0,idling=c['tidling'],attacking=c['tattacking'],
                   frozen=c['tfrozen'],blockpower=0,blockodds=c['odds'],thold=0,type=2,blocking=c['blocking'],blockthreshold=0,counter_min=-1,counter_max=-1,animpos=c['target_frame'])
            next_seed,value=random32_step(seed_value);calls=[]
            result=choose(d,dict(direction=c['adir']),dict(no_block=0),c.get('force',0),0,lambda:valid,lambda:c['air']>=6554,lambda:calls.append(1) or value)
            c.update(ticket={'PASSIVE_BLOCK':PASSIVE_BLOCK_REQUIRED,'ACTIVE_BLOCK':ACTIVE_BLOCK_REQUIRED,'DAMAGE':DAMAGE_REQUIRED}[result],expected_seed=next_seed if calls else seed_value,expected_calls=len(calls))
            custom.append(c)
        nominal=next(c for c in custom if c['slot']==0 and c['valid_block']==1 and not c['nopassive'] and c['tdir']==1 and not c['tfrozen'] and not c['tlink'] and not c['air'] and c['tidling'] and c['odds']==1)
        for bad in ('factor_ready','factor_marker','factor_model','factor_power','initial_threshold','cache_bytes','cache_max','block_handle','attack_frame','random_ready','random_busy','direction_tag'):
            custom.append(dict(nominal,bad='block_'+bad,fault=1,ticket=-1,state=4,repeat=False,suspended_on_fault=True,expected_seed=nominal['seed_value'],expected_calls=0))
        skipped=next(c for c in custom if c['slot']==0 and c['valid_block']==0 and not c['nopassive'] and not c['tfrozen'] and not c['tlink'] and c['tidling'])
        custom.append(dict(skipped,bad='block_random_ready',repeat=True))
        rows[:]=custom
        block_setup=r'''
 set('SourceFactors4086_Ready',0xb5f1);set('SourceFactors4086_Models',16)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_RowBytes',336);set('SourceModelAnimationCopy4086_Bytes',5376)
 for i=0,5375 do put(0x43c000+i,0,1)end
 put(0x43c000+26,c.valid_block~=0 and BLOCKHANDLE or 0)
 for _,i in ipairs({c.slot,c.first})do put(0x43b900+4*i,0);put(0x43b902+4*i,0xb5f1);for j=0,31 do put(0x432800+32*i+j,0,1)end end
 local target=c.first
 put(0x42f408+24*target,c.nopassive,4);put(0x42f40c+24*target,c.odds,4)
 put(0x41401c+80*c.slot,c.adir,4);put(0x41401c+80*target,c.tdir,4)
 put(0x414034+80*target,(-50*65536)&0xffffffff,4)
 put(0x41400c+80*target,c.air,4);put(0x416830+64*target,0,4)
 put(0x42e000+40*target,c.tfrozen,4)
 put(0x43eb00+32*target,c.tidling,4);put(0x43eb0c+32*target,c.blocking,4);put(0x40c058+96*target,c.tattacking,4)
 put(0x40901c+64*target,c.tlink~=0 and 0x414000+80*c.slot or 0,4)
 put(0x7efd00+4*c.slot,c.bomb_attacker,4);put(0x7efd00+4*target,c.bomb_target,4)
 set('SourceRandom4086_Ready',0xb4d4);set('SourceRandom4086_Busy',0);put(sy.SourceRandom4086_SeedLo,c.seed_value,4);put(sy.SourceRandom4086_CallsLo,0,4)
 put(MODE,c['repeat'] and 1 or 0)
 visited={};before={};for _,r in ipairs(ranges)
'''
        lua=lua.replace(' visited={};before={};for _,r in ipairs(ranges)',block_setup)
        lua=lua.replace('local ranges={','local ranges={{0x7efd00,512},{0x432800,4096},{0x43b900,512},{0x43c000,5376},')
        lua=lua.replace(' local n=0;for a,v in pairs(before)'," for j=0,3 do before[HB+16*c.slot+j]=(2>>(8*j))&255 end\n if c.fault==0 then for _,i in ipairs({c.slot,c.first})do for j=0,3 do before[0x7efd00+4*i+j]=(2>>(8*j))&255 end end end\n local n=0;for a,v in pairs(before)")
        lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local target=c.first
 if c.bad=='block_factor_ready'then set('SourceFactors4086_Ready',0)
 elseif c.bad=='block_factor_marker'then put(0x43b902+4*target,0)
 elseif c.bad=='block_factor_model'then put(0x43b900+4*target,1)
 elseif c.bad=='block_factor_power'then put(0x432804+32*target,0x3f800000,4)
 elseif c.bad=='block_initial_threshold'then put(0x43280c+32*c.slot,0x3f800000,4)
 elseif c.bad=='block_cache_bytes'then set('SourceModelAnimationCopy4086_Bytes',5374)
 elseif c.bad=='block_cache_max'then set('SourceModelAnimationCopy4086_Maximum',167)
 elseif c.bad=='block_block_handle'then put(0x43c000+26,65535)
 elseif c.bad=='block_attack_frame'then put(0x416806+64*c.slot,c.frame+1)
 elseif c.bad=='block_random_ready'then set('SourceRandom4086_Ready',0)
 elseif c.bad=='block_random_busy'then set('SourceRandom4086_Busy',1)
 elseif c.bad=='block_direction_tag'then put(0x414018+80*target,2,4)end
 -- Deliberate fault injection changes are part of the fixture input snapshot.
 for _,base in ipairs({0x43b900+4*target,0x432800+32*target,0x432800+32*c.slot,0x416800+64*c.slot,0x414000+80*target})do
  for j=0,(base>=0x414000 and base<0x416800 and 79 or base>=0x416800 and base<0x418800 and 63 or base>=0x432800 and base<0x433800 and 31 or 3)do
   if before[base+j]~=nil then before[base+j]=emu.read(base+j,mt)end
  end
 end
 for j=0,1 do before[0x43c000+26+j]=emu.read(0x43c000+26+j,mt)end
end,emu.callbackType.exec,BLOCKBEGIN,BLOCKBEGIN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();emu.log('BLOCKRETURN|'..word(INDEX)..'|'..s['cpu.a']..'|'..(s['cpu.ps']&1)..'|'..word(CW+60))
end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('BLOCKRNG|'..word(INDEX)..'|'..word(sy.SourceRandom4086_SeedLo)..'|'..word(sy.SourceRandom4086_SeedHi)..'|'..word(sy.SourceRandom4086_CallsLo)..'|'..word(sy.SourceRandom4086_CallsHi)..'|'..word(sy.SourceRandom4086_Busy))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
        lua=re.sub(r'\bBLOCKHANDLE\b',str(next(v for m in req['models']for v in m['authored_block_handles'])),lua)
        extra={k:v for k,v in sy.items()if k.startswith(('SourceRandom4086_','SourceFactors4086_','SourceModelAnimationCopy4086_'))}
        lua='local blockSymbols='+luav(extra)+'\nfor k,v in pairs(blockSymbols)do sy[k]=v end\n'+lua
        body=kw['append'];start=body.index('AttackGateProbe:');end=body.index('HitState_',start)
        probe=r'''AttackGateProbe:
.a16
.i16
 php
 phx
 phy
 sed
 ldx #1
 ldy #0
 jsl AttackLoop_Begin
 bcs AttackGateProbe_Return
 jsl AttackLoop_Poll
 bcs AttackGateProbe_Return
AttackGateProbe_BlockBegin:
.a16
.i16
 jsl HitBlock_Run
 bcs AttackGateProbe_Return
 pha
 lda.l MODE
 beq AttackGateProbe_Keep
 pla
AttackGateProbe_Retry:
.a16
.i16
 jsl HitBlock_Run
 bra AttackGateProbe_Return
AttackGateProbe_Keep:
.a16
.i16
 pla
 clc
AttackGateProbe_Return:
.a16
.i16
 nop
 bcs AttackGateProbe_Bad
 ply
 plx
 plp
 clc
 rtl
AttackGateProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
        native=emit(req,loop.layout(),sy)
        kw['append']=body[:start]+probe+body[end:]+native
        guard_names=re.findall(r'^(HitBlock_Guard\d+):',native,re.M)
        kw['probes'].update(BLOCKBAD='HitBlock_Bad',BLOCKBEGIN='AttackGateProbe_BlockBegin',**{'BLOCKG'+str(i):n for i,n in enumerate(guard_names)})
        lua+='\nlocal blockLastGuard=-1\nfor i,pc in ipairs({'+','.join('BLOCKG'+str(i)for i in range(len(guard_names)))+'})do emu.addMemoryCallback(function()blockLastGuard=i end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,mt)end\n'
        lua+="emu.addMemoryCallback(function()emu.log('BLOCKFAULT|'..word(INDEX)..'|'..blockLastGuard..'|'..word(CW+60))end,emu.callbackType.exec,BLOCKBAD,BLOCKBAD,emu.cpuType.snes,mt)\n"
        lua=re.sub(r'\bCW\b',str(w),lua)
        lua=re.sub(r'\bHB\b',str(loop.hits()['base']),lua)
        raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
        observed.extend([list(map(int,l.split('BLOCKRNG|',1)[1].split('|')))for l in log.splitlines()if 'BLOCKRNG|'in l])
        expected=[[i,c['expected_seed']&65535,c['expected_seed']>>16,c['expected_calls'],0,1 if c.get('bad')=='block_random_busy' else 0]for i,c in enumerate(rows)]
        reporter.check('actual rand32 seed, call gating and one-time block selection under pending retry',observed==expected)
        return raw,log
    args=['m4_attack_loop_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output),'--hit-prelude']
    with patch.object(loop,'run_fixture',fixture),patch.object(sys,'argv',args):
        try:loop.main()
        except SystemExit as e:
            if e.code not in (None,0):raise
    path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_SOURCE_HIT_BLOCK_CHOICE_NATIVE_V1',block_choice_bound=True,blocking_damage_bodies_bound=False,
        actual_rand32_results=observed,requirements=req,mandatory_hit_ticket=None,required_action_tickets=[PASSIVE_BLOCK_REQUIRED,ACTIVE_BLOCK_REQUIRED,DAMAGE_REQUIRED])
    path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
