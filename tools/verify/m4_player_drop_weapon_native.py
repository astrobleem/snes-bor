"""Native source player weapon fallback and real same-model transition."""
import argparse,hashlib,itertools,json,struct,sys
from unittest.mock import patch
from pathlib import Path
import m4_drop_weapon_native as original
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols
from source_player_drop_weapon_native import emit
from source_player_drop_weapon_authority import selected


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--nonplayer-authority',type=Path);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';sy=symbols(Path('src/main.sym'));rows=[]
    for model,owner,number,level,loss0,loss,player in itertools.product((0,3),(0,2,3),(-2147483648,-1,0,1,2,2147483647),(0,2),(0,3),(0,1,2),(0,3)):
        n=number or level;first=selected(owner,n,model);second=selected(owner,loss,model)if first==model and loss>0 else model;final_number=loss if first==model and loss>0 else n;players=[77]*4;players[player]=final_number if loss0==3 else level
        rows.append(dict(type=1,model=model,default=model,owner=owner,loss=loss,loss0=loss0,number=number,level=level,player=player,slot=(0,63,127)[len(rows)%3],attached=0,status=3 if first!=model or second!=model else 0,fault=0,players=players))
    seed=next(c for c in rows if c['model']==3 and c['owner']==0 and not c['number']and not c['level']and not c['loss']and not c['loss0']and c['player']==0)
    for bad in ('player_tag','player_reserved','player_high','player_range','players_zero','players_large','ready','life_marker','life_model','transition_busy'):
        c=dict(seed,bad=bad,status=4,fault=1,players=[77]*4);c['players'][0]=c['number'];rows.append(c)
    table=struct.pack('<4s6H',b'B4MW',1,4,8,16,32,0)+b''.join(struct.pack('<4H',i,0 if i==0 else 2,48 if i<2 else 52 if i==2 else 56,0)for i in range(4))+struct.pack('<6h',2,0,0,1,-1,2)
    lua=original.LUA.replace('TABLEBYTES',str(len(table))).replace('put(meta+4,0,4)','put(meta+4,c.loss0,4)').replace('for i=0,3 do put(0x43ea00+i*4,5,4)end',"for i=0,3 do put(0x43ea00+i*4,77,4)end;put(0x43ea00+4*c.player,c.number,4);put(sy.SourceWeapon4086_LevelWeaponLo,c.level,4);put(0x414028+80*slot,1,4);put(0x41402c+80*slot,c.player,4)")
    guard="""
 local view=0x414000+80*slot
 local pc={player_tag={view+40,0},player_reserved={view+42,1},player_high={view+46,1},player_range={view+44,4},players_large={sy.SourceWeapon4086_Players,5}}
 if pc[c.bad]then put(pc[c.bad][1],pc[c.bad][2])end
"""
    lua=lua.replace(' before={};for _,r in ipairs',guard+' before={};for _,r in ipairs').replace('{{side,64}', '{{view,80},{side,64}')
    lua=lua.replace(' local c=rows[word(INDEX)+1];local n=0;', ' local c=rows[word(INDEX)+1];for i=0,3 do for j=0,3 do before[0x43ea00+4*i+j]=(c.players[i+1]>>(8*j))&255 end end;local n=0;')
    lua=lua.replace('before={}', 'before={};local cpu={};local context=0',1).replace('end,emu.callbackType.exec,INIT'," cpu=emu.getState();context=0\nend,emu.callbackType.exec,INIT",1)
    lua+="\nemu.addMemoryCallback(function()local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=s['cpu.'..k]then context=context+1 end end;if(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then context=context+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)\n"
    lua=lua.replace("..word(DWSTATUS))", "..word(DWSTATUS)..'|'..context)")
    r=Reporter('M4-PLAYER-DROP-WEAPON',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourcePlayerDropWeapon4086_Execute','SourceDropWeapon4086_Ready',0xb635,[(58,0,table)],lua,r,append=emit(sy),bindings=dict(DWREADY='SourceDropWeapon4086_Ready',DWSLOT='SourceDropWeapon4086_Slot',DWSTATUS='SourceDropWeapon4086_Status',DWPHASE='SourceDropWeapon4086_Phase'),link_pcm=False,frame_limit=4000)
    actual=[list(map(int,l.split('DROPWEAPON|',1)[1].split('|')))for l in log.splitlines()if 'DROPWEAPON|'in l];expected=[[i,0,c['status'],0]for i,c in enumerate(rows)];ok=actual==expected;r.check('source stored-weapon/level fallback, exact player bookkeeping, real native resolver and same-model transition, explicit different-model service and stale-player guards',ok);r.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
    report=dict(schema='BYOR_PLAYER_DROP_WEAPON_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=[dict(index=i,actual=actual[i]if i<len(actual)else None,expected=e)for i,e in enumerate(expected)if i>=len(actual)or actual[i]!=e],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),actual_native_weapon_resolver_called=True,actual_native_same_model_transition_called=True,different_model_body_bound=False,attached_item_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if a.nonplayer_authority:
        leaf=original.run_fixture
        def regression(rom,folder,cases,apply,ready,magic,tables,observer,reporter,**kw):
            cases[:]=[c for c in cases if not(c['type']&1)]
            kw.update(append=emit(sy),link_pcm=False)
            return leaf(rom,folder,cases,'SourcePlayerDropWeapon4086_Execute',ready,magic,tables,observer,reporter,**kw)
        args=['m4_drop_weapon_native.py','--rom',str(a.rom),'--authority',str(a.nonplayer_authority),'--output',str(a.output/'nonplayer-regression')]
        with patch.object(original,'run_fixture',regression),patch.object(sys,'argv',args):
            try:original.main()
            except SystemExit as e:
                if e.code not in (None,0):raise
    r.finish()


if __name__=='__main__':main()
