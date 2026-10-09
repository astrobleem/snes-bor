"""Real collision/block choice joined to one-time combat effects and facing."""
import argparse
import itertools
import json
from pathlib import Path
import re
import sys
import struct
from unittest.mock import patch
import m4_hit_block_native as block
import m4_attack_loop_native as loop
from compiler import Source
from source_combat_effects_requirements import derive
from source_combat_effects_native import emit as effects
from source_current_colourmap import layout as colour_layout
from source_current_colourmap_native import emit as colour_native
from source_damage_flip_native import emit as flip_native
from source_damage_flip_requirements import derive as flip_requirements
from source_foreign_state_layout import layout as arena
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from source_script_clone import derive as script_models
from source_hit_block_native import DAMAGE_REQUIRED


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--damagedrop',action='store_true');p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();src=Source(a.source);req=derive(src);plan=colour_layout();sy=symbols(Path('src/main.sym'));original=loop.run_fixture;w=plan['controls'];base=plan['base'];hw=loop.hits()['controls'];hc=loop.layout()['controls']
    flipw=next(r['address']for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls');fr=flip_requirements(src);sr=script_models(src);effect_results=[];cases=[]
    if a.damagedrop:
        from source_combat_drop_requirements import derive as drop_requirements
        from source_combat_drop_native import emit as drop_native
        dr=drop_requirements(src)
    def fb(v):return struct.unpack('<I',struct.pack('<f',v))[0]
    def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
        seed=next(c for c in rows if not c['fault']and c['valid_block']==0 and c['slot']==0)
        for model,attack,frozen,deadline,air,drop in itertools.product((0,8,14),((11,1,2),(47,4,16),(73,0,30)),range(2),(0,123),(0,6554),range(2)):
            handle,frame,index=attack;fm=req['models'][model]['frozen_map'];nodrop=req['models'][model]['nodrop'];fa=req['attacks'][index-1]['freeze'];finalfrozen=frozen;finaldeadline=deadline;finaldrop=drop;active=fm if frozen and 0<=fm<=req['models'][model]['maps_loaded']else 0
            if a.damagedrop and not finaldrop:finaldrop=req['attacks'][index-1]['attack_drop']
            if fa and not frozen:finalfrozen=1;finaldeadline=deadline or 648;finaldrop=0;active=fm if 1<=fm<=req['models'][model]['maps_loaded']else 0
            elif frozen:finalfrozen=0;finaldeadline=0;finaldrop=1;active=0
            if nodrop:finaldrop=0
            if air>=6554 and not finalfrozen and nodrop<2:finaldrop=1
            c=dict(seed,ap=[0,93*65536 if handle==47 else 0,0],handle=handle,frame=frame,target_model=model,knock_bits=0,ktime=0,expected_count=fb(-req['attacks'][index-1]['attack_drop']) if not drop else 0,expected_ktime=248 if not drop else 0,attack_index=index,valid_block=0,tfrozen=frozen,deadline=0,effect_deadline=deadline,air=air,effect_drop=drop,restore=0,active_map=fm if frozen and 0<=fm<=req['models'][model]['maps_loaded']else 0,tdir=0,adir=0,bomb_attacker=0,bomb_target=0,old_self=2,state=5,repeat=True,bad='',fault=0,ticket=DAMAGE_REQUIRED,expected_calls=0,expected_seed=seed['seed_value'],effect_frozen=finalfrozen,effect_time=finaldeadline,effect_finaldrop=finaldrop,effect_active=active,effect_direction=0 if finalfrozen else 1,effect_rise=0 if finaldrop else 11,effect_riseattack=0 if finaldrop else 12)
            cases.append(c)
        if a.damagedrop:
            seedcount=next(c for c in cases if c['target_model']==14 and c['attack_index']==2 and not c['tfrozen']and not c['air']and not c['effect_drop']and not c['effect_deadline'])
            counts=sorted({0,-1,-2**24}|{-2**e+d for e in range(1,24)for d in (-1,0,1)})
            for count,ktime in itertools.product(counts,(0,47,48,49)):
                beforecount=0 if ktime and ktime<48 else count
                aftercount=max(-2**24,beforecount-1)
                cases.append(dict(seedcount,knock_bits=fb(count),ktime=ktime,expected_count=fb(aftercount),expected_ktime=248))
        nominal=next(c for c in cases if c['target_model']==14 and c['handle']==47 and not c['tfrozen']and not c['air']and not c['effect_drop']and c['effect_deadline']==0)
        for bad in ('ready','time','attacker','target','identity','frame','attack_index','effect_ready','effect_marker','effect_model','combat_marker','palette_marker','palette_generation','palette_owner','palette_range'):
            cases.append(dict(nominal,bad='effect_'+bad,fault=1,ticket=-1,suspended_on_fault=True))
        if a.damagedrop:
            for bad in ('drop_ready','drop_factor','drop_model_count','drop_reserved','drop_positive','drop_fraction','drop_nan','drop_large'):
                cases.append(dict(seedcount,bad=bad,fault=1,ticket=-1,suspended_on_fault=True))
        rows[:]=cases
        lua=re.sub(r'\b47936\b',str(plan['chr_capacity']),lua)
        lua=lua.replace('(-50*65536)','(-20*65536)')
        lua=lua.replace('put(as,0);put(as+4,c.target_handle)','put(as,i==c.first and c.target_model or 0);put(as+4,c.target_handle)')
        lua=lua.replace('put(al+72,0);', 'put(al+64,0,4);put(al+72,i==c.first and c.target_model or 0);')
        lua=lua.replace('put(0x43b900+4*i,0);','put(0x43b900+4*i,i==c.first and c.target_model or 0);')
        sm={i:m['initialized_mask']for i,m in enumerate(sr['models'])}
        lua=lua.replace('for i=0,127 do local rel=0x409000+64*i;put(rel+44,', 'for i=0,127 do local rel=0x409000+64*i;put(rel+44,i==c.first and effectMasks[c.target_model] or ')
        lua='local effectMasks='+luav(sm)+'\n'+lua
        lua=lua.replace('if c.fault==0 then for _,i in ipairs({c.slot,c.first})','if c.fault==0 and c.bomb_target==1 then for _,i in ipairs({c.slot,c.first})')
        lua=lua.replace('local ranges={',f'local ranges={{{{{base},{plan["bytes"]}}},{{0x420000,{plan["chr_capacity"]}}},{{0x433800,8192}},{{0x7ef100,3072}},')
        if a.damagedrop:
            lua=lua.replace('local ranges={','local ranges={{0x7fb900,1536},{0x439000,10240},')
            lua=lua.replace('local target=c.first', 'local target=c.first;put(0x432808+32*target,0,4);put(0x43280a+32*target,0x3f80)',1)
        setup=f'''
 set('SourceDamageState4086_Ready',0xb62b);set('SourceCtorState4086_Ready',0xb5c2);set('SourceCtorState4086_Models',16);set('SourceFreeze4086_Ready',0xb5df);set('SourceDamageEffectsState4086_Ready',0xb62f)
 for i=0,127 do
  local m=i==c.first and c.target_model or 0;local row={base}+12*i;put(row,m);put(row+2,i==c.first and c.active_map or 0);put(row+4,1,4);put(row+8,0xb6ac);put(row+10,i)
  put(0x433830+64*i,i==c.first and c.restore or 0);put(0x433832+64*i,m);put(0x43383e+64*i,0xb5c2)
  local ef=0x7ef100+24*i;put(ef,3,4);put(ef+4,11,4);put(ef+8,12,4);put(ef+20,0xb62f);put(ef+22,m)
  put(0x437e00+20*i,i==c.first and c.effect_drop or 0,4);put(0x437e10+20*i,0xb5fb);put(0x437e12+20*i,0)
  put(0x7fb900+12*i,i==c.first and c.knock_bits or 0,4);put(0x7fb904+12*i,i==c.first and c.ktime or 0,4);put(0x7fb908+12*i,0,4)
 end
 put(0x42e004+40*c.first,c.effect_deadline,4)
 for j=0,63 do put({w}+j,0,1)end
 put({w},0xb6ab);put({w}+4,c.first);put({w}+8,1,4);put({w}+12,48,4);put({w}+16,{base}&65535);put({w}+18,0x42);put({w}+20,{plan['chr_capacity']});put({w}+22,128)
 put({w}+40,0xb6ad);put({w}+44,0);put({w}+46,c.slot);put({w}+48,c.first);put({w}+50,c.attack_index);put({w}+52,c.frame);put({w}+54,c.handle);put({w}+56,2,4)
 put({flipw},0xb6aa);put({flipw}+4,c.first);put({flipw}+6,c.slot);put({flipw}+8,1,4);put({flipw}+12,0,4);put({flipw}+16,c.attack_index==30 and -1 or 0,4)
 visited={{}};before={{}};for _,r in ipairs(ranges)
'''
        lua=lua.replace(' visited={};before={};for _,r in ipairs(ranges)',setup)
        expectation=f'''
 if c.fault==0 then
  local target=c.first
  for _,f in ipairs({{{{0x42e000+40*target,c.effect_frozen,4}},{{0x42e004+40*target,c.effect_time,4}},{{0x437e00+20*target,c.effect_finaldrop,4}},{{0x7ef100+24*target,0,4}},{{0x7ef104+24*target,c.effect_rise,4}},{{0x7ef108+24*target,c.effect_riseattack,4}},{{{base}+12*target+2,c.effect_active,2}},{{0x41401c+80*target,c.effect_direction,4}}}})do
   for j=0,f[3]-1 do before[f[1]+j]=(f[2]>>(8*j))&255 end
  end
 end
 local n=0;for a,v in pairs(before)
'''
        if a.damagedrop:
            expected_drop="""
 if c.fault==0 then
  for _,f in ipairs({{0x7fb900+12*c.first,c.expected_count},{0x7fb904+12*c.first,c.expected_ktime},{0x7fb908+12*c.first,c.attack_index==16 and 6 or 0}})do
   for j=0,3 do before[f[1]+j]=(f[2]>>(8*j))&255 end
  end
 end
"""
            expectation=expectation.replace(' local n=0;for a,v in pairs(before)',expected_drop+' local n=0;for a,v in pairs(before)')
        lua=lua.replace(' local n=0;for a,v in pairs(before)',expectation)
        lua+=f'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local target=c.first;local row={base}+12*target;local ef=0x7ef100+24*target
 if c.bad=='effect_ready'then put({w}+40,0)
 elseif c.bad=='effect_time'then put({w}+12,49,4)
 elseif c.bad=='effect_attacker'then put({w}+46,127)
 elseif c.bad=='effect_target'then put({w}+48,127)
 elseif c.bad=='effect_identity'then put({w}+56,3,4)
 elseif c.bad=='effect_frame'then put({w}+52,c.frame+1)
 elseif c.bad=='effect_attack_index'then put({w}+50,1)
 elseif c.bad=='effect_effect_ready'then set('SourceDamageEffectsState4086_Ready',0)
 elseif c.bad=='effect_effect_marker'then put(ef+20,0)
 elseif c.bad=='effect_effect_model'then put(ef+22,0)
 elseif c.bad=='effect_combat_marker'then put(0x437e10+20*target,0)
 elseif c.bad=='effect_palette_marker'then put(row+8,0)
 elseif c.bad=='effect_palette_generation'then put(row+4,2,4)
 elseif c.bad=='effect_palette_owner'then put(row,0)
 elseif c.bad=='effect_palette_range'then put(row+2,3)
 elseif c.bad=='drop_ready'then set('SourceDamageState4086_Ready',0)
 elseif c.bad=='drop_factor'then put(0x43280a+32*target,0x4000)
 elseif c.bad=='drop_model_count'then put(0x439040+80*target,0x3f800000,4)
 elseif c.bad=='drop_reserved'then put(0x437e12+20*target,1)
 elseif c.bad=='drop_positive'then put(0x7fb900+12*target,0x3f800000,4)
 elseif c.bad=='drop_fraction'then put(0x7fb900+12*target,0xbfc00000,4)
 elseif c.bad=='drop_nan'then put(0x7fb900+12*target,0xffc00000,4)
 elseif c.bad=='drop_large'then put(0x7fb900+12*target,0xcb800001,4)end
 for _,r in ipairs({{{{row,12}},{{ef,24}},{{0x437e00+20*target,20}}}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,EFFECTBEGIN,EFFECTBEGIN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local target=c.first
 emu.log('COMBATEFFECT|'..word(INDEX)..'|'..word({w}+42)..'|'..word({w}+44)..'|'..word(0x42e000+40*target)..'|'..word(0x42e004+40*target)..'|'..word(0x437e00+20*target)..'|'..word({base}+12*target+2)..'|'..word(0x433830+64*target))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
        if a.damagedrop:
            lua=lua.replace('for _,r in ipairs({{row,12}', 'for _,r in ipairs({{0x7fb900+12*target,12},{0x432800+32*target,32},{0x439000+80*target,80},{row,12}')
        extra={k:v for k,v in sy.items()if k.startswith(('SourceDamageState4086_','SourceCtorState4086_','SourceFreeze4086_','SourceDamageEffectsState4086_'))}
        lua='local effectSymbols='+luav(extra)+'\nfor k,v in pairs(effectSymbols)do sy[k]=v end\n'+lua
        body=kw['append'];start=body.index(' pha\n lda.l MODE',body.index('AttackGateProbe_BlockBegin:'));end=body.index('AttackGateProbe_Return:',start)
        replacement='''AttackGateProbe_EffectBegin:
.a16
.i16
 jsl CombatEffects_Run
 bcs AttackGateProbe_Return
 jsl CombatEffects_Run
 bcs AttackGateProbe_Return
 jsl DamageFlip_Run
 bcs AttackGateProbe_Return
AttackGateProbe_Retry:
.a16
.i16
 lda #33045
 clc
'''
        body=body[:start]+replacement+body[end:]
        effect_code=effects(req,sy,damagedrop=a.damagedrop)
        if a.damagedrop:
            replacement=replacement.replace(' jsl CombatEffects_Run',' jsl CombatDrop_Run\n bcs AttackGateProbe_Return\n jsl CombatEffects_Run')
            body=body[:body.index('AttackGateProbe_EffectBegin:')]+replacement+body[body.index('AttackGateProbe_Return:',body.index('AttackGateProbe_EffectBegin:')):]
        kw['append']=body+colour_native(req['palette_requirements'],plan,sy)+effect_code+flip_native(fr,flipw,sy)+(drop_native(dr,sy)if a.damagedrop else '')
        kw['probes'].update(EFFECTBEGIN='AttackGateProbe_EffectBegin')
        kw['probes'].update(GATERESET='CheckAttack_Reset',PREPDONE='DoAttackPrepare_Done')
        lua+="\nfor _,pc in ipairs({GATERESET,PREPDONE})do emu.addMemoryCallback(function()local s=emu.getState();emu.log('EFFECTINACTIVE|'..word(INDEX)..'|'..s['cpu.a']..'|'..word(sy.SourceCollisionFrame4086_Attack)..'|'..word(sy.SourceCollisionFrame4086_Handle)..'|'..word(sy.SourceCollisionFrame4086_Frame)..'|'..word(0x437e00)..'|'..word(0x42e000))end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,mt)end\n"
        for prefix in (('CombatDrop',)if a.damagedrop else ())+('CombatEffects','CurrentPalette','DamageFlip'):
            names=re.findall(r'^('+prefix+r'_Guard\d+):',kw['append'],re.M)
            kw['probes'][prefix+'BAD']=prefix+'_Bad'
            for i,name in enumerate(names):kw['probes'][prefix+'G'+str(i)]=name
            lua+='\nlocal '+prefix+'Last=-1\nfor i,pc in ipairs({'+','.join(prefix+'G'+str(i)for i in range(len(names)))+'})do emu.addMemoryCallback(function()'+prefix+'Last=i end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,mt)end\n'
            lua+=f"emu.addMemoryCallback(function()emu.log('{prefix.upper()}FAULT|'..word(INDEX)..'|'..{prefix}Last..'|'..word({w}+44))end,emu.callbackType.exec,{prefix}BAD,{prefix}BAD,emu.cpuType.snes,mt)\n"
        raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
        effect_results.extend([list(map(int,l.split('COMBATEFFECT|',1)[1].split('|')))for l in log.splitlines()if 'COMBATEFFECT|'in l]);wanted=[]
        for i,c in enumerate(rows):wanted.append([i,3 if c['fault']else 2,0 if c['fault']else 2,c['tfrozen']if c['fault']else c['effect_frozen'],c['effect_deadline']if c['fault']else c['effect_time'],c['effect_drop']if c['fault']else c['effect_finaldrop'],3 if c['bad']=='effect_palette_range'else c['active_map']if c['fault']else c['effect_active'],c['restore']])
        reporter.check('actual freeze/unfreeze palette and drop state, frozen deadline retention and exactly once effect execution under retry',effect_results==wanted)
        return raw,log
    args=['m4_hit_block_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
    with patch.object(loop,'run_fixture',fixture),patch.object(sys,'argv',args):
        try:block.main()
        except SystemExit as e:
            if e.code not in (None,0):raise
    path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_COMBAT_DROP_JOINED_NATIVE_V1'if a.damagedrop else'BYOR_COMBAT_EFFECTS_NATIVE_V1',chr_capacity=plan['chr_capacity'],combat_effect_results=effect_results,combat_effects_requirements=req,actual_effects_and_facing_bound=True,damagedrop_predecessor_bound=a.damagedrop,full_damage_callback_bound=False,CGRAM_presentation_bound=False,production_memory_owner_bound=False)
    if a.damagedrop:r.update(damage_drop_requirements=dr,exact_binary32_counter_observed=True,damage_drop_retry_bound=True)
    path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
