"""Isolated post-constructor recovery against literal spawnplayer C outputs."""
import copy,hashlib,itertools,json,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import m4_player_global_native as parent
import source_player_die_native as snapshot
from compiler import Source
from source_foreign_slot_tail import derive_plan
from source_foreign_state_layout import layout as arena
from source_player_global_layout import layout
from source_player_spawn_native import emit_recovery,emit_history_reset
from actor_s5_entity_fixture import symbols
from _harness import Reporter


def main():
    args=sys.argv[1:];source=Source(args[args.index('--source')+1]);tail=derive_plan(source);g=layout(tail);sy=symbols(Path('src/main.sym'))
    history=next(r['address']for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='input_history')
    authority=Path('out/byor-motu-player-spawn-authority');auth=json.loads((authority/'report.json').read_text());assert auth['status']=='PASS'and auth['cases']==5634
    assert hashlib.sha256((authority/'spawnplayer.c').read_text().encode()).hexdigest()==auth['fixture_sha256']
    original=parent.run_fixture;seen={}
    class Checked(Reporter):
        def __init__(self,*a,**kw):super().__init__('M4-SPAWN-RECOVERY',**kw)
    def code(tail,sy):return 'PlayerDieSnapshot_Run:\n.a16\n.i16\n jml SpawnRecovery_Apply\n'+emit_recovery(tail,sy)+emit_history_reset(history,sy)
    def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
        base=copy.deepcopy(rows[0]);rows[:]=[]
        pairs=((-2147483648,-2147483648),(-8,-3),(0,0),(100,40),(146,79),(2147483642,2147483645))
        for player,slot,(hp,mp)in itertools.product(range(4),(0,1,127),pairs):
            rows.append(dict(base,player=player,slot=slot,health=150,mp=80,saved_hp=hp,saved_mp=mp,bad='',fault=0))
        inputs=b''.join(struct.pack('<15I',*(v&0xffffffff for v in (c['player'],0,256,100,100,0,0,0,0,0,c['saved_hp'],c['saved_mp'],0,5,0)))for c in rows)
        output=subprocess.check_output([str((authority/'spawnplayer.exe').resolve())],input=inputs)
        assert len(output)==80*len(rows)
        seen['c_input_sha256']=hashlib.sha256(inputs).hexdigest();seen['c_output_sha256']=hashlib.sha256(output).hexdigest()
        for i,c in enumerate(rows):c.update(expected_hp=struct.unpack_from('<i',output,80*i+44)[0],expected_mp=struct.unpack_from('<i',output,80*i+48)[0])
        for bad in ('parent','tag','generation','self_header','entity_count','model_ready','foreign_generation','player_index','role','type','health_overflow','mp_overflow','rush'):
            rows.append(dict(copy.deepcopy(rows[0]),fault=1,bad=bad))
        rows.append(copy.deepcopy(rows[71]));seen['rows']=copy.deepcopy(rows)
        setup=f'''
 if c.op==5 then
  put({g['global_base']}+8,0,4)
  put({g['player_base']}+20*c.player+8,c.saved_hp,4);put({g['player_base']}+20*c.player+12,c.saved_mp,4)
  put(0x43fd84+4*c.player,0x414000+80*c.slot,4)
  put(0x414020+80*c.slot,1,4);put(0x414024+80*c.slot,150,4);put(0x414004+80*c.slot,1)
  put(0x40c048+96*c.slot,1,4);put(0x40c04c+96*c.slot,80,4)
  for i=0,1023 do put({history}+i,(i*7+91)&255,1)end
  if c.bad=='role'then put(0x43fd84+4*c.player,0,4)
  elseif c.bad=='type'then put(0x40c048+96*c.slot,0,4)
  elseif c.bad=='health_overflow'then put({g['player_base']}+20*c.player+8,2147483643,4)
  elseif c.bad=='mp_overflow'then put({g['player_base']}+20*c.player+12,2147483646,4)
  elseif c.bad=='rush'then put({g['global_base']}+8,1,4)end
 end
'''
        lua=lua.replace(' before={};for i=0,8207',setup+'\n before={};for i=0,8207',1)
        lua=lua.replace(' local s=emu.getState();cpu={};',f' for i=0,1023 do before[{history}+i]=emu.read({history}+i,mt)end\n local s=emu.getState();cpu={{}};',1)
        old='expect('+str(g['controls'])+'+64+c.player*20+8,c.health,4);expect('+str(g['controls'])+'+64+c.player*20+12,c.mp,4)'
        assert old in lua
        new=f'''expect(0x414028+80*c.slot,1,4);expect(0x41402c+80*c.slot,c.player,4)
   expect(0x414024+80*c.slot,c.expected_hp,4);expect(0x40c04c+96*c.slot,c.expected_mp,4)
   for i=0,215 do expect({history}+c.player*256+i,0,1)end
   expect({history}+c.player*256+232,0,4)'''
        lua=lua.replace(old,new,1)
        lua='local recoveryCost=0\n'+lua
        lua+='\nemu.addMemoryCallback(function()recoveryCost=emu.getState().masterClock end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)\n'
        lua+='\nemu.addMemoryCallback(function()emu.log("SPAWNRECOVERYCOST|"..word(INDEX).."|"..(emu.getState().masterClock-recoveryCost))end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)\n'
        # Both adjacent entity records and all history rows remain observed.
        raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
        seen['log']=log;return raw,log
    asm=parent.ASM.replace(' jsl PlayerDieSnapshot_Run',' jsl PlayerDieSnapshot_Run\n bcs PlayerGlobalProbe_Return\n jsl PlayerDieSnapshot_Run')
    with patch.object(parent,'run_fixture',fixture),patch.object(parent,'Reporter',Checked),patch.object(parent,'ASM',asm),patch.object(snapshot,'emit_recovery_snapshot',code),patch.object(sys,'argv',['m4_player_global_native.py',*args,'--recovery-snapshot']):
        try:parent.main()
        except SystemExit as e:
            if e.code not in(None,0):raise
    p=Path(args[args.index('--output')+1])/'report.json';r=json.loads(p.read_text())
    r.update(schema='BYOR_PLAYER_SPAWN_RECOVERY_NATIVE_V1',literal_c_recovery_outputs_compared=True,c_authority_function_sha256=auth['source_body_sha256'],
             post_constructor_recovery_bound=True,actual_input_history_reset_bound=True,full_spawnplayer_bound=False,constructor_bound=False,
             weapon_child_bound=False,production_consumer_bound=False,source_integer_overflow_rejected=True)
    r.update(c_input_sha256=seen['c_input_sha256'],c_output_sha256=seen['c_output_sha256'],native_inputs=seen['rows'],actual_player_die_bound=False,recovery_snapshot_bound=False)
    costs=[list(map(int,line.split('SPAWNRECOVERYCOST|')[1].split('|')))for line in seen['log'].splitlines()if'SPAWNRECOVERYCOST|'in line]
    assert len(costs)==len(seen['rows']);r.update(native_wrapper_costs=costs,maximum_two_call_wrapper_master_clocks=max(c[1]for c in costs))
    p.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
