"""Actual native zeroed landing-attack effects and required frozen service."""
import argparse
import hashlib
import json
from pathlib import Path
from source_damage_inputs_4086 import pack
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory;local before={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(LEREADY,0xb630);put(LESLOT,c.slot);put(LESTATUS,0)
 local slot=c.slot%128;local view=0x414000+slot*80;local side=0x416800+slot*64;local life=0x439000+slot*80;local combat=0x437e00+slot*20;local state=0x7ef100+slot*24;local freeze=0x42e000+slot*40
 put(sy.SourceDamageEffectsState4086_Ready,0xb62f);put(sy.SourceLifecycle4086_Ready,0xb4fb);put(sy.SourceFreeze4086_Ready,0xb5df)
 put(sy.SourceLandingDrop4086_Ready,0xb62e);put(sy.SourceLandingDrop4086_Base,0x8000);put(sy.SourceLandingDrop4086_Bank,0x3a);put(sy.SourceLandingDrop4086_Bytes,TABLEBYTES);put(sy.SourceLandingDrop4086_Models,5)
 put(life+72,c.model);put(life+74,0xb4fb);put(side,c.model);put(side+48,c.base,4)
 put(view+8,2);put(view+10,0);put(view+12,c.a,4);put(combat,c.drop,4);put(combat+16,0xb5fb);put(combat+18,0)
 put(state,3,4);put(state+4,11,4);put(state+8,12,4);put(state+12,13,4);put(state+16,14,4);put(state+20,0xb62f);put(state+22,c.model)
 put(freeze,c.frozen,4);put(freeze+4,123,4);put(0x433830+slot*64,7)
 local changes={ready={LEREADY,0},state_ready={sy.SourceDamageEffectsState4086_Ready,0},life_ready={sy.SourceLifecycle4086_Ready,0},freeze_ready={sy.SourceFreeze4086_Ready,0},input_ready={sy.SourceLandingDrop4086_Ready,0},life_marker={life+74,0},side_model={side,15},effect_marker={state+20,0},effect_model={state+22,15},combat_marker={combat+16,0},combat_reserved={combat+18,1},models_zero={sy.SourceLandingDrop4086_Models,0},models_large={sy.SourceLandingDrop4086_Models,17},bytes={sy.SourceLandingDrop4086_Bytes,TABLEBYTES-1},base={sy.SourceLandingDrop4086_Base,0x7fff},bank={sy.SourceLandingDrop4086_Bank,0x40},bank_high={sy.SourceLandingDrop4086_Bank,0x13a},position_tag={view+8,1},position_reserved={view+10,1}}
 if c.bad and changes[c.bad]then local r=changes[c.bad];put(r[1],r[2])end
 before={};local ranges={{0x7ef100,3072},{0x437e00,2560},{view,80},{side,64},{life,80},{freeze,40},{0x433800+slot*64,64},{0x7fb900,1536}}
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local state=0x7ef100+(c.slot%128)*24;local combat=0x437e00+(c.slot%128)*20
 if c.status==4 then
  for _,r in ipairs({{state,0},{state+4,c.staydown0},{state+8,c.staydown1},{combat,c.expected_drop}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('LANDEFFECT|'..word(INDEX)..'|'..n..'|'..word(LESTATUS))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    rows=[];nodrops=(-1,0,1,2,3)
    for case in authority['results']:
        r=case['case']
        if r['mode']!=0:continue
        for slot in(0,63,127):
            rows.append(dict(slot=slot,model=nodrops.index(r['nodrop']),a=round(r['y']*65536)&0xffffffff,base=round(r['base']*65536)&0xffffffff,
                             frozen=r['frozen'],drop=r['drop'],fault=0,status=1 if r['frozen']else 4,
                             expected_drop=case['expected'][0],staydown0=case['expected'][4],staydown1=case['expected'][5]))
    seed=next(r for r in rows if r['model']==1 and r['frozen']==0 and r['drop']==0 and r['a']==0 and r['base']==0)
    for bad in('ready','state_ready','life_ready','freeze_ready','input_ready','life_marker','side_model','effect_marker','effect_model','combat_marker','combat_reserved','models_zero','models_large','bytes','base','bank','bank_high','position_tag','position_reserved'):
        rows.append(dict(seed,bad=bad,fault=1,status=3))
    rows.extend(dict(seed,slot=slot,fault=1,status=3)for slot in(128,65535))
    for slot in(0,63,127):
        for field in('a','base'):
            for value in(256*65536,-256*65536-1):rows.append(dict(seed,slot=slot,**{field:value&0xffffffff},status=2))
    table=pack(dict(models=[dict(id=i,fields=dict(animal=0,nodrop=nd,guardpoints=0))for i,nd in enumerate(nodrops)]))
    reporter=Reporter('M4-LANDING-EFFECTS',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceLandingEffects4086_Execute','SourceLandingEffects4086_Ready',0xb630,[(58,0,table)],LUA.replace('TABLEBYTES',str(len(table))),reporter,
                        bindings=dict(LEREADY='SourceLandingEffects4086_Ready',LESLOT='SourceLandingEffects4086_Slot',LESTATUS='SourceLandingEffects4086_Status'))
    actual=[list(map(int,l.split('LANDEFFECT|',1)[1].split('|')))for l in log.splitlines()if'LANDEFFECT|'in l]
    expected=[[i,0,r['status']]for i,r in enumerate(rows)];ok=actual==expected
    reporter.check('pinned source drop/projectile/staydown behavior across slots and absolute-height threshold; preserves stall/guard; frozen colourmap and wider coordinate domains remain required; fault atomicity',ok)
    report=dict(schema='BYOR_4086_LANDING_EFFECTS_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
                authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
                native_domain='zeroed source landing attack; unfrozen; Q16 position/base in[-256,256), exactly representable binary32; abs height difference threshold>=6554 Q16 units',
                frozen_policy='required unfrozen/colourmap service, no state mutation or fabricated completion',
                current_riseattack_stall_preserved=True,full_damage_callback_bound=False,world_post_acknowledgement_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
