"""Source commands through real model/energy/history/costmove owners."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_player_combo_4086 import derive as derive_combo,select
from source_player_combo_native import emit as emit_combo
from source_player_input_native import emit as emit_history
from source_player_input_4086 import empty_player
from source_costmove_native import emit as emit_cost,emit_combo_energy_query
from source_animation_energy_4086 import derive as derive_energy,pack as pack_energy,check
from source_animation_init_4086 import derive as derive_init,pack as pack_init
from source_frame_effects_4086 import derive as derive_effects,pack as pack_effects
from source_model_switch_requirements import derive as derive_models,pack_animation_cache
from source_foreign_state_layout import layout
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_costmove_native import LUA


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','source','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);sy=symbols(Path('src/main.sym'))
    combos=derive_combo(source);energy=derive_energy(source);ai=derive_init(source);fe=derive_effects(source);models=derive_models(source)
    energytable=pack_energy(energy);aitable=pack_init(ai);fetable=pack_effects(fe);cache=pack_animation_cache(models)
    arena=layout(0x7fa000,6400);addresses={r['name']:r['address'] for r in arena['regions']}
    cost=addresses['costmove_controls'];tail=addresses['entity_combo_tail'];work=addresses['combo_controls'];history=addresses['input_history'];seq=addresses['combo_sequence'];owner=addresses['input_owner']
    handles={(an['model'],an['engine_animation_id']):an for an in ai['animations']}
    fields={an['handle']:an['fields'] for an in energy['animations']}
    rows=[]
    for model_id,m in enumerate(combos['models']):
        for command in m['combos']:
            for step in (0,1,26):
                player=empty_player();player['combostep']=step;player['playkeys']=0x80001dfc
                for j,key in enumerate(command['input']):player['combokey'][(step-len(command['input'])+j)%27]=key
                chosen=select(m['combos'],player,dict(cancel=0,animnum=0,animpos=0,animhits=0,idling=1,alt=0,base=0),
                    lambda role:(m['model'],role) in handles,
                    lambda which,role:check(which,fields[handles[m['model'],role]['handle']],1,0,100,150))
                an=handles[m['model'],chosen];f=fields[an['handle']]
                row=dict(slot=(0,1,127)[step%3],role=chosen,model=model_id,handle=an['handle'],fs=1,jump=0,bad='',fault=0,linked=False,
                    original=dict(health=150,mp=100,type=1,seal=0,fields=f),context=dict(nospecial=0,nocost=0,healthcheat=0),wanted=[0]*20,
                    player=player,expected_role=chosen,expected_state=3,expected_length=max(len(c['input']) for c in m['combos'] if c['anim']==chosen),combo_bad='')
                rows.append(row)
    base=rows[0]
    for bad in ('playkeys','idling','altitude','input_owner','combo_ready','combo_pending','world','slot','player_tag','player_high','player_bounds','altitude_tag','role_tag','model','cost_pending'):
        false=bad in ('playkeys','idling','altitude')
        rows.append(dict(base,combo_bad=bad,fault=0 if false else 1,expected_state=2 if false else 5,expected_role=0 if bad in ('input_owner','combo_ready','combo_pending') else 65535))
    lua=LUA
    begin=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local s=c.slot;local p=(s+1)%128;local w=c.wanted;')
    end=lua.index('emu.addMemoryCallback(function()',begin+1)
    lua=lua[:begin]+lua[end:]
    # Keep the actual source descriptor table intact: these are authored moves.
    begin=lua.index(' local at=58*32768+16+(c.handle-1)*16')
    end=lua.index(" if c.bad=='ready'",begin)
    lua=lua[:begin]+lua[end:]
    lua=lua.replace(' before={};for _,r in ipairs(', ' COMBO_SETUP\n before={};for _,r in ipairs(',1)
    setup=r'''
 local h=HISTORY;local w=COMBOWORK
 for i=0,1023 do emu.write(h+i,0,mt)end
 for i=0,95 do emu.write(w+i,0,mt)end
 local player=(word(INDEX)%4);local at=h+player*256
 for i=0,26 do dword(at+108+4*i,c.player.combokey[i+1])end
 dword(at+232,c.player.combostep);dword(at+224,c.player.playkeys)
 put(INPUTOWNER,0xb674);put(w,0xb673);put(w+4,s)
 dword(v+44,player);put(v+40,1);put(v+42,0)
 put(v+8,2);put(v+10,0);dword(v+12,0);dword(aux+8,0)
 dword(core+72,1);dword(core+76,100);dword(v+36,150)
 put(sy.SourceRetirement4086_Status,0)
 if c.combo_bad=='playkeys'then dword(at+224,0)
 elseif c.combo_bad=='idling'then dword(fl,0)
 elseif c.combo_bad=='altitude'then dword(v+12,131072)
 elseif c.combo_bad=='input_owner'then put(INPUTOWNER,0)
 elseif c.combo_bad=='combo_ready'then put(w,0)
 elseif c.combo_bad=='combo_pending'then put(w+2,3)
 elseif c.combo_bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.combo_bad=='slot'then put(w+4,128)
 elseif c.combo_bad=='player_tag'then put(v+40,2)
 elseif c.combo_bad=='player_high'then put(v+46,1)
 elseif c.combo_bad=='player_bounds'then put(v+44,4)
 elseif c.combo_bad=='altitude_tag'then put(v+8,1)
 elseif c.combo_bad=='role_tag'then put(v+16,2)
 elseif c.combo_bad=='model'then put(0x416800+s*64,16)
 elseif c.combo_bad=='cost_pending'then put(COSTWORK+2,3)end
'''
    lua=lua.replace('COMBO_SETUP',setup)
    lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local p=word(COMBOWORK+6);local at=HISTORY+p*256
 emu.log('COMBOSEG|'..word(INDEX)..'|'..word(COMBOWORK+12)..'|'..word(COMBOWORK+20)..'|'..word(COMBOWORK+22)..'|'..word(COMBOWORK+24)..'|'..word(at+232)..'|'..long(at+108+26*4)..'|'..word(sy.SourceAnimationInit4086_Handle)..'|'..word(sy.SourceCheckEnergy4086_Result))
end,emu.callbackType.exec,SELECTED,SELECTED,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local s=c.slot;local at=HISTORY+(word(INDEX)%4)*256
 local changed=0;if c.combo_bad~='' then for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end end
 emu.log('SOURCECOMBO|'..word(INDEX)..'|'..word(COMBOWORK+2)..'|'..word(COMBOWORK+8)..'|'..word(COMBOWORK+10)..'|'..word(COSTWORK+2)..'|'..long(at+224)..'|'..long(0x40c04c+s*96)..'|'..long(0x414024+s*80)..'|'..changed)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    for k,v in dict(WORKADDR=cost,TAILADDR=tail,AIBYTES=len(aitable),FEBYTES=len(fetable),HANDLES=len(ai['animations']),AEBYTES=len(energytable),HISTORY=history,COMBOWORK=work,COSTWORK=cost,INPUTOWNER=owner).items():lua=lua.replace(k,str(v))
    lua=lua.replace('CACHE',json.dumps(cache.hex()))
    asm=emit_history(history,addresses['input_scratch'],addresses['input_snapshot'],seq,owner,0xb674)+emit_cost(cost,tail,sy)+emit_combo_energy_query(cost,sy)+emit_combo(combos,work,cost,history,seq,owner,0xb674,sy)
    reporter=Reporter('M4-PLAYER-COMBO-NATIVE',kind='GATE')
    def before(m,sy):
        for n in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):m.write_u8(sy[n],0)
    raw,log=run_fixture(a.rom,folder,rows,'SourceCombo_Begin','VmSourceInput_Ready',0xb673,[(58,0,energytable),(59,0,aitable),(60,0,fetable)],lua,reporter,append=asm,probes=dict(SELECTED='SourceCombo_Selected'),batch_size=2,frame_limit=700,before_start=before,link_pcm=False)
    actual=[list(map(int,line.split('SOURCECOMBO|')[1].strip().split('|'))) for line in log.splitlines() if 'SOURCECOMBO|' in line]
    errors=[]
    for i,row in enumerate(actual):
        c=rows[i]
        if row[0:3]!=[i,c['expected_state'],c['expected_role']]:errors.append(row);continue
        if not c['combo_bad'] and row[3:]!=[c['expected_length'],3,c['player']['playkeys'],100,150,0]:errors.append(row)
        if c['combo_bad'] and row[-1]!=0:errors.append(row)
    reporter.check('all source commands select from live models and preserve playkeys while costmove frame zero is pending',len(actual)==len(rows) and not errors)
    report=dict(schema='BYOR_4086_PLAYER_COMBO_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',cases=len(rows),authored_commands=sum(len(m['combos']) for m in combos['models']),errors=errors[:12],rom_sha256=hashlib.sha256(raw).hexdigest(),controller_layout=arena,source_energy_descriptors_unmodified=True,source_frame_zero_execution_bound=False,production_player_owner_bound=False,motu_gameplay_proven=False,no_pcm_copies=True,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()


if __name__=='__main__':main()
