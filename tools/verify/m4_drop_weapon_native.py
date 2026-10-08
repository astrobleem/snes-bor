"""Native actual dropweapon selectors and same-model transition early return."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory;local before={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(DWREADY,0xb635);put(DWSLOT,c.slot);put(DWSTATUS,0);put(DWPHASE,0)
 local slot=c.slot%128;local side=0x416800+slot*64;local life=0x439000+slot*80;local core=0x40c000+slot*96;local flags=0x43eb00+slot*32;local meta=0x43e200+slot*16
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128);put(sy.SourceLifecycle4086_Ready,0xb4fb)
 put(sy.SourceModelEntityCopy4086_Ready,0xb4eb);put(sy.SourceModelEntityCopy4086_Models,4)
 put(sy.SourceWeapon4086_Ready,0xb4f1);put(sy.SourceWeapon4086_Models,4);put(sy.SourceWeapon4086_Entities,128);put(sy.SourceWeapon4086_Players,4)
 put(sy.SourceWeapon4086_Base,0x8000);put(sy.SourceWeapon4086_Bank,0x3a);put(sy.SourceWeapon4086_Bytes,TABLEBYTES)
 put(sy.SourceWeapon4086_Status,0);put(sy.SourceWeapon4086_Selected,0xffff)
 put(sy.SourceModelTransition4086_Ready,0xb4f0);put(sy.SourceModelTransition4086_State,0);put(sy.SourceModelTransition4086_Service,0)
 put(side,c.model);put(side+2,c.default);put(life+72,c.model);put(life+74,0xb4fb);put(core+72,c.type,4);put(flags+28,c.attached,4)
 put(meta,c.owner==0 and 65535 or c.owner-1);put(meta+2,c.owner>1 and 2 or 0);put(meta+4,0,4);put(meta+8,c.loss&0xffffffff,4);put(meta+12,0,4)
 for i=0,3 do put(0x43ea00+i*4,5,4)end
 local changes={ready={DWREADY,0},life_ready={sy.SourceLifecycle4086_Ready,0},life_marker={life+74,0},life_model={life+72,15},model_ready={sy.SourceModelEntityCopy4086_Ready,0},models_mismatch={sy.SourceModelEntityCopy4086_Models,3},transition_ready={sy.SourceModelTransition4086_Ready,0},transition_busy={sy.SourceModelTransition4086_State,1},transition_fault={sy.SourceModelTransition4086_State,3},weapon_ready={sy.SourceWeapon4086_Ready,0},world_ready={sy.VmSourceWorld_Ready,0},pool={sy.VmSourceWorld_PoolBase,0},entities={sy.SourceWeapon4086_Entities,127},models_zero={sy.SourceWeapon4086_Models,0},players_zero={sy.SourceWeapon4086_Players,0},bank={sy.SourceWeapon4086_Bank,0x40},base={sy.SourceWeapon4086_Base,0x7fff},bytes={sy.SourceWeapon4086_Bytes,15},owner={meta,4},default={side+2,4}}
 if c.bad and changes[c.bad]then local r=changes[c.bad];put(r[1],r[2])end
 before={};for _,r in ipairs({{side,64},{life,80},{core,96},{flags,32},{meta,16},{0x43ea00,16},{0x40ba00,512},{0x7fbfa0,32}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('DROPWEAPON|'..word(INDEX)..'|'..n..'|'..word(DWSTATUS))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';rows=[]
    for r in authority['results']:
        c=r['case'];fault=int(r['source_invalid_model_selection']);status=4 if fault else 3 if r['model_transition_required']else 0
        for slot in(0,63,127):rows.append(dict(c,slot=slot,default=c['model'],attached=0,status=status,fault=fault))
    seed=next(r for r in rows if r['model']==3 and r['owner']==0 and r['loss']==0)
    for bad in('ready','life_ready','life_marker','life_model','model_ready','models_mismatch','transition_ready','transition_busy','transition_fault','weapon_ready','world_ready','pool','entities','models_zero','players_zero','bank','base','bytes','owner','default'):
        rows.append(dict(seed,bad=bad,status=4,fault=1))
    rows.extend(dict(seed,slot=slot,status=4,fault=1)for slot in(128,65535))
    for slot in(0,63,127):
        rows.append(dict(seed,slot=slot,attached=0x414000,status=1))
        rows.append(dict(seed,slot=slot,type=1,status=2))
        rows.append(dict(seed,slot=slot,default=0,status=3))
    # Generic B4MW: empty list and three different source index lists.
    table=struct.pack('<4s6H',b'B4MW',1,4,8,16,32,0)
    table+=b''.join(struct.pack('<4H',i,0 if i==0 else 2,48 if i<2 else 52 if i==2 else 56,0)for i in range(4))+struct.pack('<6h',2,0,0,1,-1,2)
    reporter=Reporter('M4-DROP-WEAPON-COMPONENT',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceDropWeapon4086_Execute','SourceDropWeapon4086_Ready',0xb635,[(58,0,table)],LUA.replace('TABLEBYTES',str(len(table))),reporter,
                        bindings=dict(DWREADY='SourceDropWeapon4086_Ready',DWSLOT='SourceDropWeapon4086_Slot',DWSTATUS='SourceDropWeapon4086_Status',DWPHASE='SourceDropWeapon4086_Phase'))
    actual=[list(map(int,l.split('DROPWEAPON|',1)[1].split('|')))for l in log.splitlines()if'DROPWEAPON|'in l]
    expected=[[i,0,r['status']]for i,r in enumerate(rows)];ok=actual==expected
    reporter.check('actual source set_weapon resolution and same-model early return, including second override; preserves all actor/player/cache bytes; attached/player/model-change services remain required; undefined selections and stale leases reject',ok)
    report=dict(schema='BYOR_4086_DROP_WEAPON_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
                authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
                actual_native_weapon_resolver_called=True,actual_native_same_model_transition_called=True,
                attached_item_and_player_and_different_model_services_proven=False,
                full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
