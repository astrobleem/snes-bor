"""Join active palette reset before real model-transition colour acknowledgement."""
import argparse,json,re,sys
from pathlib import Path
from unittest.mock import patch
import m4_model_palette_service_native as parent
from compiler import Source
from source_current_colourmap import derive,layout
from source_current_colourmap_native import emit as current
from source_model_palette_service_native import emit as palette
from source_hit_state_layout import layout as hits
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--first-colour',action='store_true');a=p.parse_args();src=Source(a.source);req=derive(src);plan=layout();h=hits();sy=symbols(Path('src/main.sym'));w=plan['controls'];base=plan['base'];original=parent.run_fixture
    def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
        rows.extend(dict(rows[0],bad=bad,fault=1)for bad in ('current_ready','current_capacity','current_generation','current_old','current_row_owner','current_row_map','current_row_marker','current_row_generation','current_row_slot','current_hit_marker','current_hit_generation','current_phase','current_time'))
        for c in rows:c['old_model']=(c['model']+1)%16;c['old_active']=req['models'][c['old_model']]['maps_loaded']
        extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_','SourceCtorState4086_','SourceWorldTick4086_'))or k=='DmaQueue'}
        lua='local currentSymbols='+luav(extra)+'\nfor k,v in pairs(currentSymbols)do sy[k]=v end\n'+lua
        lua=lua.replace('local ranges={',f'local ranges={{{{{base},{plan["bytes"]}}},{{0x420000,{plan["chr_capacity"]}}},{{{h["base"]},2048}},')
        setup=f'''
 for i=0,127 do
  local row={base}+12*i;put(row,c.old_model);put(row+2,c.old_active);put(row+4,1,4);put(row+8,0xb6ac);put(row+10,i)
  put({h['base']}+16*i+8,1,4);put({h['base']}+16*i+12,0xb6a1);put({h['base']}+16*i+14,i)
 end
 for i=0,63 do put({w}+i,0,1);put({h['controls']}+i,0,1)end
 put({w},0xb6ab);put({w}+4,c.slot);put({w}+8,1,4);put({w}+16,{base}&65535);put({w}+18,0x42);put({w}+20,{plan['chr_capacity']});put({w}+22,128);put({w}+24,5)
 put({h['controls']},0xb6a0);put({h['controls']}+8,1,4);put({h['controls']}+16,{h['base']}&65535);put({h['controls']}+18,0x42);put({h['controls']}+20,{plan['chr_capacity']});put({h['controls']}+22,128)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);put(sy.SourceWorldTick4086_TimeLo,48,4);put(sy.VmSourceWorld_Time,48,4)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({{'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'}})do set(n,0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 local cr={base}+12*c.slot
 if c.bad=='current_ready'then put({w},0)
 elseif c.bad=='current_capacity'then put({w}+20,{plan['chr_capacity']}+2)
 elseif c.bad=='current_generation'then put({w}+8,2,4)
 elseif c.bad=='current_old'then set('SourceModelTransition4086_Old',c.model)
 elseif c.bad=='current_row_owner'then put(cr,16)
 elseif c.bad=='current_row_map'then put(cr+2,3)
 elseif c.bad=='current_row_marker'then put(cr+8,0)
 elseif c.bad=='current_row_generation'then put(cr+4,2,4)
 elseif c.bad=='current_row_slot'then put(cr+10,128)
 elseif c.bad=='current_hit_marker'then put({h['base']}+16*c.slot+12,0)
 elseif c.bad=='current_hit_generation'then put({h['base']}+16*c.slot+8,2,4)
 elseif c.bad=='current_phase'then set('SourceWorldTick4086_Phase',7)
 elseif c.bad=='current_time'then put(sy.SourceWorldTick4086_TimeLo,49,4)end
'''
        anchor=' before={};for _,r in ipairs(ranges)'
        if lua.count(anchor)!=1:raise ValueError('CURRENT_TRANSITION_FIXTURE_SETUP_SHAPE')
        lua=lua.replace(anchor,setup+anchor)
        expected=f'''before[row+50]=c.model;before[row+51]=0
 local cr={base}+12*c.slot;before[cr]=c.model;before[cr+1]=0;before[cr+2]=c.selected&255;before[cr+3]=(c.selected>>8)&255'''
        lua=lua.replace('before[row+50]=c.model;before[row+51]=0',expected)
        service=3 if a.first_colour else 6
        palette_code=palette(parent.derive(src),sy,service,current_palette=plan)
        palette_code=palette_code.replace(' jsl CurrentPalette_Run\n',' jsl CurrentPalette_Run\n bcs CurrentResetProbe_ChildBad\n jsl CurrentPalette_Run\nCurrentResetProbe_ChildBad:\n.a16\n.i16\n')
        kw['append']=palette_code+current(req,plan,sy)
        kw['probes']=dict(kw.get('probes',{}),CURRENTBAD='CurrentPalette_Bad',CURRENTENTRY='CurrentPalette_Run')
        guards=re.findall(r'^(CurrentPalette_Guard\d+):',kw['append'],re.M)
        for i,n in enumerate(guards):kw['probes']['CG'+str(i)]=n
        lua+='\nlocal last=-1\nfor i,pc in ipairs({'+','.join('CG'+str(i)for i in range(len(guards)))+'})do emu.addMemoryCallback(function()last=i end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,mt)end\n'
        lua+="\nemu.addMemoryCallback(function()emu.log('CURRENTTRANSITIONFAULT|'..word(INDEX)..'|'..last)end,emu.callbackType.exec,CURRENTBAD,CURRENTBAD,emu.cpuType.snes,mt)\n"
        lua+="\nemu.addMemoryCallback(function()emu.log('CURRENTRESETENTRY|'..word(INDEX))end,emu.callbackType.exec,CURRENTENTRY,CURRENTENTRY,emu.cpuType.snes,mt)\n"
        raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
        entries=[int(l.split('CURRENTRESETENTRY|',1)[1])for l in log.splitlines()if 'CURRENTRESETENTRY|'in l]
        reporter.check('two actual reset calls on accepted publication, one on a current-state rejection, none on a preceding parent rejection',entries==[i for i,c in enumerate(rows)for _ in range(1 if c['bad'].startswith('current_')else 2 if not c['fault']or c['bad'].startswith('animation_')else 0)])
        reporter.check('bank zero unchanged',raw[:32768]==rom.read_bytes()[:32768])
        return raw,log
    args=['m4_model_palette_service_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]+(['--first-colour']if a.first_colour else [])
    with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',args):
        try:parent.main()
        except SystemExit as e:
            if e.code not in (None,0):raise
    path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_MODEL_CURRENT_PALETTE_TRANSITION_JOIN_V1',independent_active_palette_reset_bound=True,active_owner_reset_before_real_ack=True,repeated_reset_calls_observed=True,chr_capacity=plan['chr_capacity'],world_phase=8,full_transition_bound=False,CGRAM_presentation_bound=False,production_memory_owner_bound=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
