"""Bounded real-input prop/drop sample inside a native campaign traversal.

Approach uses compiler progression before this window. This window does not
invoke acceleration, write actor state, or initialize completion state.
"""
import os
import json
from pathlib import Path


def observer_script(symbols):
    if os.environ.get('BYOR_NATIVE_INTERACTION_SAMPLE')!='1':return ''
    path=Path(os.environ['BYOR_NATIVE_INTERACTION_JOURNAL']).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    address=symbols['Character_HitApply__ApplyPickup']
    return f'''
local _byor_pickup_events=assert(io.open({json.dumps(path.as_posix())},'w'))
emu.addMemoryCallback(function()
 local s=emu.getState()
 _byor_pickup_events:write(tostring(s['ppu.frameCount'] or -1)..'|'..tostring(s['cpu.a'] or -1)..'|'..
 tostring(emu.read({symbols['Spawn_Index']},emu.memType.snesMemory))..'\\n')
 _byor_pickup_events:flush()
end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,emu.memType.snesMemory)
'''


def sample(m, symbols, report):
    if os.environ.get('BYOR_NATIVE_INTERACTION_SAMPLE') != '1' or 'native_interaction_sample' in report:
        return
    import _harness as h
    def u8(name):
        return h.read_block(m,symbols[name],32)[0]
    def actors():
        rows=[]
        for slot in range(6):
            raw=bytes(h.read_block(m,0x7E0000+symbols['PlayerEntity_DpBase']+slot*symbols['CHAR_ZP_LEN'],symbols['CHAR_ZP_LEN']))
            rows.append(dict(slot=slot,roster=raw[symbols['CHAR_ROSTER_INDEX']],
                mode=raw[symbols['CHAR_INPUT_DRIVEN']],hp=raw[symbols['CHAR_HP']],
                pickup=raw[symbols['CHAR_PICKUP_TYPE']],
                x=int.from_bytes(raw[4:6],'little',signed=True),y=raw[6]))
        base=0x7E0000+symbols['PlayerEntity_DpBase']
        rows[0]['x']=int.from_bytes(bytes(h.read_block(m,base+symbols['CHAR_POS_X'],32)[:2]),'little',signed=True)
        rows[0]['y']=int.from_bytes(bytes(h.read_block(m,base+symbols['CHAR_POS_Y'],32)[:2]),'little',signed=True)
        return rows
    rows=actors()
    props=[a for a in rows[1:] if a['mode']==symbols['CHAR_INPUT_DRIVEN_PROP'] and a['hp']>1 and a['pickup']]
    if not props:return
    chosen=min(props,key=lambda a:abs(a['x']-rows[0]['x'])+abs(a['y']-rows[0]['y']))
    result=dict(verdict='INCOMPLETE',scope='bounded unaccelerated real input after compiler-owned approach',
        limit_fields=2400,source_prop_roster=chosen['roster'],slot=chosen['slot'],samples=[],writes='controller input only')
    report['native_interaction_sample']=result
    journal=Path(os.environ['BYOR_NATIVE_INTERACTION_JOURNAL'])
    baseline=journal.read_text().splitlines()
    initial_roster=chosen['roster']; saw_drop=False
    for field in range(result['limit_fields']):
        rows=actors();p=rows[0];target=rows[chosen['slot']]
        if field%20==0:result['samples'].append(dict(field=field,player=p,target=target,host_error=int.from_bytes(bytes(h.read_block(m,symbols['S6Host_Error'],32)[:2]),'little')))
        if target['roster']!=initial_roster and target['pickup'] and target['hp']:
            saw_drop=True;result['drop_roster']=target['roster']
        events=journal.read_text().splitlines()[len(baseline):]
        if events and target['roster']!=initial_roster and target['mode']==3 and not target['pickup']:
            result.update(verdict='PASS',fields=field,prop_damage=True,drop_observed=True,
                drop_roster=target['roster'],pickup_consumed=True,pickup_apply_events=events,journal=str(journal))
            break
        dx,dy=target['x']-p['x'],target['y']-p['y']
        buttons=0
        if u8('G13_P1Out') and u8('Game_Credits'):
            buttons=m.BTN_START if field%24==0 else 0
        elif abs(dy)>4:
            buttons=m.BTN_DOWN if dy>0 else m.BTN_UP
        elif abs(dx)>(4 if saw_drop else 32):
            buttons=m.BTN_RIGHT if dx>0 else m.BTN_LEFT
        elif not saw_drop:
            # Face the object before attacking, then let the authored move
            # finish. Repeated key edges are ordinary player input.
            if field%80<4:buttons=m.BTN_RIGHT if dx>=0 else m.BTN_LEFT
            elif field%80<40:buttons=m.BTN_Y
        m.hold_input(buttons)
        h.run_frames_exact(m,1)
    m.release_input()
    assert result['verdict']=='PASS','bounded native prop/drop/pickup sample did not complete'
    assert all(s['host_error']==0 for s in result['samples']),'worker fault during native interaction sample'
