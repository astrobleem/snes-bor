"""Native absent-hook player death prefix, real kill and no-lives tail.

Positive lives stop on the required SPAWN ticket. This is an isolated source
service proof, not a production dispatcher or complete respawn implementation.
"""
import copy,hashlib,itertools,json,struct,sys
from pathlib import Path
from unittest.mock import patch
import m4_retirement_native as parent
from actor_s5_entity_fixture import symbols
from compiler import Source
from source_foreign_slot_tail import derive_plan
from source_foreign_state_layout import layout as arena
from source_player_global_layout import layout
from source_player_global_native import emit as globals_code
from source_player_death_requirements import derive
from source_player_die_native import death_layout,emit_begin,emit_recovery_snapshot
from source_foreign_water_retirement import emit as water,transform as retire_water
from m4_animation_init_native import luav
from m4_input_controller_native import offset
from _harness import Reporter
import _source_leaf_fixture as leaf


def main():
    args=sys.argv[1:];at=args.index('--source');source=Source(args[at+1]);del args[at:at+2]
    tail=derive_plan(source);g=layout(tail);w=death_layout(tail)['base'];req=derive(source);sy=symbols(Path('src/main.sym'))
    state=next(r['address']for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='player_state_controls')
    original=parent.run_fixture;seen={}
    def exact(m,count):
        for attempt in range(8):
            r=m.run_frames(count)
            if r.get('framesAdvanced')==count and not r.get('timedOut'):return r
            if r.get('framesAdvanced')!=0 or not r.get('timedOut'):raise AssertionError('PLAYER_DIE_PARTIAL_FIELD')
            seen['zero_field_retries']=seen.get('zero_field_retries',0)+1
        raise AssertionError('PLAYER_DIE_BOUNDED_FIELD_STALL')
    class Checked(Reporter):
        def __init__(self,*args,**kw):super().__init__('M4-PLAYER-DIE-BEGIN',**kw)
        def check(self,name,ok):
            if name.startswith('pinned C retirement state'):
                actual=[list(map(int,l.split('RETIRERESULT|')[1].split('|')))for l in seen['log'].splitlines()if'RETIRERESULT|'in l]
                ok=actual==[[i,0,0,0 if c['fault']else 2]for i,c in enumerate(seen['rows'])];name='real kill relation/role/variable cleanup and exact player death globals with CPU preservation'
            elif name=='admitted retirement faults block source clock':
                actual=[list(map(int,l.split('RETIRECLOCK|')[1].split('|')))for l in seen['log'].splitlines()if'RETIRECLOCK|'in l]
                ok=actual==[[i,1,48,1]for i in range(len(seen['rows']))];name='source clock held while caller damage-phase lease remains outstanding'
            return super().check(name,ok)
    def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
        base=next(c for c in rows if c['count']==6 and not c['fault']and c['case']['mode']==0 and c['case']['summon']==0)
        rows[:]=[]
        for index,lives,cheat,other,credit,joining in itertools.product(range(4),(1,2),(0,1),(0,1),(0,1),(0,3)):
            c=copy.deepcopy(base);c.update(index=index,lives=lives,cheat=cheat,other=other,credit=credit,joining=joining,source_model=3 if index%2==0 else 4)
            for name in ('before','after'):
                def write(at,value,size=4):
                    for p in c[name]:
                        if p['at']<=at and at+size<=p['at']+len(p['data']):
                            p['data'][at-p['at']:at-p['at']+size]=list((value&((1<<(8*size))-1)).to_bytes(size,'little'));return
                    c[name].append(dict(at=at,data=list((value&((1<<(8*size))-1)).to_bytes(size,'little'))))
                write(0x414028+c['slot']*80,1);write(0x41402c+c['slot']*80,index)
                write(0x40c048+c['slot']*96,1);write(0x40c03c+c['slot']*96,150);write(0x40c040+c['slot']*96,80)
                write(0x7ffe38,0x414000+80*c['slot'])
                if name=='after':write(0x409020,1)
                for i in range(4):write(0x43fd84+4*i,(0x414000+80*c['slot'])if name=='before'and i==index else 0x414000 if other and i==(index+1)%4 else 0)
            rows.append(c)
        for guard in ('foreign','global','generation','ready','phase','time','owner_count','self','type','type_high','role','model','model_tag','player_tag'):
            rows.append(dict(copy.deepcopy(rows[0]),fault=1,guard=guard))
        rows.append(copy.deepcopy(rows[127])) # Withdraw deliberately invalid fixture state before host return.
        seen['rows']=copy.deepcopy(rows)
        extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_','SourceWorldTick4086_','SourceLifecycle4086_','SourceWeapon4086_'))or k in('DmaQueue','VmState_SlotCount','VmState_FrameTop','VmState_Status','SourceVMRun4086_Busy')}
        lua='local dieSymbols='+luav(extra)+'\nfor k,v in pairs(dieSymbols)do sy[k]=v end\n'+lua
        setup=f'''
 for i=0,8207 do put(0x7fc000+i,(i*13+91)&255,1)end
 for i=0,63 do put({state}+i,0,1)end
 put({state},0xb67b);put({state}+8,1,4);put({state}+12,{tail['live_slot_count']});put({state}+14,1,4)
 put(sy.VmState_SlotCount,{tail['live_slot_count']});put(sy.VmState_FrameTop,0);put(sy.VmState_Status,4,1);put(sy.SourceVMRun4086_Busy,0)
 for i=0,143 do put({g['controls']}+i,0,1)end
 put({g['controls']},0xb6c6);put({g['controls']}+8,1,4);put({g['controls']}+12,1,4);put({g['controls']}+16,{tail['live_slot_count']});put({g['controls']}+18,{tail['live_slot_count']})
 put({g['global_base']},0x414000+80*c.slot,4);put({g['global_base']}+4,c.cheat,4);put({g['global_base']}+16,c.credit,4)
 for i=0,3 do put(0x7fbfb0+4*i,i==c.index and c.lives or 9,4);put({g['player_base']}+20*i,c.credit,4);put({g['player_base']}+20*i+4,c.joining==i+1 and 1 or 0,4);put({g['player_base']}+20*i+8,-7,4);put({g['player_base']}+20*i+12,-8,4);put({g['player_base']}+20*i+16,21+i,4);put(0x43ea00+4*i,7,4)end
 for i=0,47 do put({w}+i,0,1)end
 put({w},0xb6c9);put({w}+4,c.slot);put({w}+8,1,4);put({w}+16,48,4)
 set('SourceForeignWork_Ready',0xb671);set('SourceForeignWork_Status',1);set('SourceForeignWork_Generation',1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({{'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'}})do set(n,0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 set('VmSourceWorld_Time',48,4);set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_TimeLo',48,4)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceModelEntityCopy4086_Models',{len(req['models'])});set('SourceWeapon4086_Ready',0xb4f1);set('SourceWeapon4086_LevelWeaponLo',5);set('SourceWeapon4086_LevelWeaponHi',0)
 put(0x43bbaa,0xb5d9);put(0x43bbb6,-77,4);put(0x416800+c.slot*64,c.source_model);put(0x439048+c.slot*80,c.source_model);put(0x43904a+c.slot*80,0xb4fb)
 if c.guard=='foreign'then set('SourceForeignWork_Ready',0)
 elseif c.guard=='global'then put({g['controls']},0)
 elseif c.guard=='generation'then put({w}+8,2,4)
 elseif c.guard=='ready'then put({w},0)
 elseif c.guard=='phase'then set('SourceWorldTick4086_Phase',6)
 elseif c.guard=='time'then put({w}+16,49,4)
 elseif c.guard=='owner_count'then set('SourceModelEntityCopy4086_Entities',5)
 elseif c.guard=='self'then put(0x7ffe38,0x414000,4)
 elseif c.guard=='type'then put(0x40c048+c.slot*96,0,4)
 elseif c.guard=='type_high'then put(0x40c04a+c.slot*96,1)
 elseif c.guard=='role'then put(0x43fd84,0x414000,4)
 elseif c.guard=='model'then put(0x416800+c.slot*64,15)
 elseif c.guard=='model_tag'then put(0x43904a+c.slot*80,0)
 elseif c.guard=='player_tag'then put(0x414028+c.slot*80,0,4)end
'''
        lua=lua.replace(' before={};for _,r in ipairs(ranges)',setup+'\n before={};for _,r in ipairs(ranges)',1)
        lua=lua.replace('local ranges={{0x414000', 'local ranges={{0x7fc000,8208},{0x7fbfb0,16},{0x43ea00,16},{0x43bbb6,4},{0x414000',1)
        expected=f'''
 if c.fault==0 then
  local function expect(a,v,n)for i=0,(n or 2)-1 do before[a+i]=(v>>(8*i))&255 end end
  local lives=c.cheat==0 and c.lives-1 or c.lives
  expect(0x7fbfb0+4*c.index,lives,4);expect({g['global_base']},0,4)
  expect({g['player_base']}+20*c.index+8,150,4);expect({g['player_base']}+20*c.index+12,80,4)
  expect({w}+6,c.index);expect({w}+24,0,4);expect({w}+28,3,4)
  if lives<=0 then
   expect({w}+2,2);expect({w}+20,0);expect({g['player_base']}+20*c.index+16,0,4);expect(0x43ea00+4*c.index,5,4)
   if c.other==0 then expect(0x43bbb6,c.credit==0 and 200 or 4000,4)end
  else expect({w}+2,1);expect({w}+20,3)end
 end
'''
        lua=lua.replace(' local mismatch=0;for a,n in pairs(before)',expected+'\n local mismatch=0;for a,n in pairs(before)',1)
        lua=lua.replace('if emu.read(a,mt)~=n then mismatch=mismatch+1 end','if emu.read(a,mt)~=n then mismatch=mismatch+1;if word(INDEX)==0 then emu.log("DIEMISMATCH|"..a.."|"..n.."|"..emu.read(a,mt))end end',1)
        wrapper=f'''PlayerDieProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl PlayerDie_Begin
 bcs PlayerDieProbe_Bad
 jsl PlayerDie_Begin
 bcs PlayerDieProbe_Bad
 ply
 plx
 plp
 clc
 rtl
PlayerDieProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
PlayerDieFixtureReturn:
.a16
.i16
 php
 rep #$20
 pha
 lda #0
 sta.l {sy['VmSourceWorld_Ready']}
 sta.l {sy['SourceWorldTick4086_Ready']}
 sta.l {sy['SourceLifecycle4086_Ready']}
 sta.l {sy['SourceSelf4086_Ready']}
 sta.l {sy['SourceModelEntityCopy4086_Ready']}
 pla
 plp
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml {sy['Vm_SourceFrameGate']+5}
'''
        def isolate(raw,linked):
            retire_water(raw,linked);at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['PlayerDieFixtureReturn'].to_bytes(3,'little')
        kw.update(append=wrapper+globals_code(tail,state,sy)+emit_recovery_snapshot(tail,sy)+emit_begin(tail,sy,req)+water(sy),rom_transform=isolate,link_pcm=False,batch_size=32)
        kw['bindings'].pop('CAPTUREENTRY');kw.setdefault('probes',{})['CAPTUREENTRY']='PlayerDieProbe'
        for name in sy:
            if name.startswith('SourceRetirement4086_')and any(x in name for x in ('Branch_','Mutate','Scan','Done','Clear')):
                token='RETTRACE_'+name;kw['bindings'][token]=name
                lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==#rows-1 then emu.log("DIERETIRE|{name}")end end,emu.callbackType.exec,{token},{token},emu.cpuType.snes,mt)\n'
        import re
        for name in re.findall(r'^(PlayerDie_Guard\d+):',emit_begin(tail,sy,req),re.M):
            token='TRACE_'+name
            kw['probes'][token]=name
            lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 or word(INDEX)==#rows-1 then emu.log("DIEGUARD|"..word(INDEX).."|{name}")end end,emu.callbackType.exec,{token},{token},emu.cpuType.snes,mt)\n'
        raw,log=original(rom,folder,rows,'PlayerDieProbe',ready,magic,tables,lua,reporter,**kw);seen['log']=log
        reporter.check('production bank0 byte identity',raw[:32768]==rom.read_bytes()[:32768]);return raw,log
    with patch.object(parent,'run_fixture',fixture),patch.object(parent,'Reporter',Checked),patch.object(leaf,'run_frames_exact',exact),patch.object(sys,'argv',['m4_retirement_native.py',*args]):
        try:parent.main()
        except SystemExit as e:
            if e.code not in(None,0):raise
    path=Path(args[args.index('--output')+1])/'report.json';r=json.loads(path.read_text())
    r.update(schema='BYOR_PLAYER_DIE_BEGIN_NATIVE_V1',actual_player_die_prefix_bound=True,actual_no_event_kill_bound=True,
             actual_no_lives_tail_bound=True,positive_lives_spawn_ticket_required=True,full_spawnplayer_bound=False,
             initialized_global_hook_bodies_bound=False,production_consumer_bound=False,full_world_tick_completed=False,
             player_die_control_layout=death_layout(tail),source_requirement_sha256=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest())
    r.update(zero_field_timeout_retries=seen.get('zero_field_retries',0),negative_guard_cases=14,successful_service_cases=129)
    path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
