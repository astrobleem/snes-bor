"""Bounded active palette birth/select/read/restore over canonical entity rows."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from compiler import Source
from source_current_colourmap import derive,layout
from source_current_colourmap_native import emit
from source_hit_state_layout import layout as hits
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path('src/main.sym'));req=derive(Source(a.source));plan=layout();h=hits();w=plan['controls'];base=plan['base'];rows=[]
    values=(0,1,2,3,32768,0x7fffffff,0xffffffff)
    for model in req['models']:
        for slot in (0,1,127):
            for op in (1,2,3,4):
                for value in values if op in (2,4)else (1,):
                    rows.append(dict(model=model['id'],slot=slot,op=op,request=value,restore=value if op in (1,4)else 1,old_map=0,fault=0,bad=''))
    for slot in range(128):
        for op in (1,3):rows.append(dict(model=slot%16,slot=slot,op=op,request=0,restore=0,old_map=0,fault=0,bad=''))
    seed=dict(model=14,slot=127,op=2,request=2,restore=1,old_map=1,fault=0,bad='')
    for bad in ('ready','generation','foreign_generation','phase','time','slot','capacity','hit_capacity','hit_generation','hit_marker','hit_slot','view_token','side_model','body_marker','body_owner','active_marker','active_generation','active_slot','active_owner','active_map','operation','birth_live'):
        rows.append(dict(seed,fault=1,bad=bad,op=1 if bad=='birth_live'else 2))
    for c in rows:
        maps=req['models'][c['model']]['maps_loaded'];requested=c['restore']if c['op']in (1,4)else c['request'];selected=requested if 1<=requested<=maps else 0
        c['selected']=c['old_map']if c['op']==3 else selected
        c['final_restore']=selected if c['op']==4 else c['restore']
    lua=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={}, {},0
local ranges={{0x420000,CAP},{BASE,SIZE},{0x414000,10240},{0x416800,8192},{0x433800,8192},{HB,2048}}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];ctx=0;put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do put(r[1]+j,165,1)end end
 for i=0,127 do
  put(0x414000+80*i,0x414000+80*i,4);put(0x414004+80*i,1,4)
  put(0x416800+64*i,c.model);put(0x433830+64*i,c.restore);put(0x433832+64*i,c.model);put(0x43383e+64*i,0xb5c2)
  local row=BASE+12*i;put(row,c.model);put(row+2,c.old_map);put(row+4,1,4);put(row+8,0xb6ac);put(row+10,i)
  put(HB+16*i+8,1,4);put(HB+16*i+12,0xb6a1);put(HB+16*i+14,i)
 end
 if c.op==1 then
  put(0x414004+80*c.slot,0,4)
  for j=0,11 do put(BASE+12*c.slot+j,165,1)end
 end
 for j=0,63 do put(W+j,0,1);put(HW+j,0,1)end
 put(W,0xb6ab);put(W+4,c.slot);put(W+8,1,4);put(W+16,BASE&65535);put(W+18,0x42);put(W+20,CAP);put(W+22,128);put(W+24,c.op);put(W+28,c.request,4)
 put(HW,0xb6a0);put(HW+8,1,4);put(HW+16,HB&65535);put(HW+18,0x42);put(HW+20,CAP);put(HW+22,128)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_TemplateCount',16);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);put(sy.VmSourceWorld_Time,48,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);put(sy.SourceWorldTick4086_TimeLo,48,4)
 set('SourceCtorState4086_Ready',0xb5c2);set('SourceCtorState4086_Models',16)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 local row=BASE+12*c.slot;local body=0x433800+64*c.slot
 if c.bad=='ready'then put(W,0)
 elseif c.bad=='generation'then put(W+8,2,4)
 elseif c.bad=='foreign_generation'then put(sy.SourceForeignWork_Generation,2,4)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',7)
 elseif c.bad=='time'then put(sy.SourceWorldTick4086_TimeLo,49,4)
 elseif c.bad=='slot'then put(W+4,128)
 elseif c.bad=='capacity'then put(W+20,CAP+2)
 elseif c.bad=='hit_capacity'then put(HW+20,CAP+2)
 elseif c.bad=='hit_generation'then put(HB+16*c.slot+8,2,4)
 elseif c.bad=='hit_marker'then put(HB+16*c.slot+12,0)
 elseif c.bad=='hit_slot'then put(HB+16*c.slot+14,0)
 elseif c.bad=='view_token'then put(0x414000+80*c.slot,0x414001,4)
 elseif c.bad=='side_model'then put(0x416800+64*c.slot,16)
 elseif c.bad=='body_marker'then put(body+62,0)
 elseif c.bad=='body_owner'then put(body+50,0)
 elseif c.bad=='active_marker'then put(row+8,0)
 elseif c.bad=='active_generation'then put(row+4,2,4)
 elseif c.bad=='active_slot'then put(row+10,0)
 elseif c.bad=='active_owner'then put(row,0)
 elseif c.bad=='active_map'then put(row+2,3)
 elseif c.bad=='operation'then put(W+24,5)
 elseif c.bad=='birth_live'then put(0x414004+80*c.slot,1,4)end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local row=BASE+12*c.slot;local differences=0
 if c.fault==0 then
  if c.op==1 then
   for _,f in ipairs({{0,c.model,2},{4,1,4},{8,0xb6ac,2},{10,c.slot,2}})do
    for j=0,f[3]-1 do before[row+f[1]+j]=(f[2]>>(8*j))&255 end
   end
  end
  for j=0,1 do before[row+2+j]=(c.selected>>(8*j))&255 end
  if c.op==4 then for j=0,1 do before[0x433830+64*c.slot+j]=(c.selected>>(8*j))&255 end end
 end
 for a,v in pairs(before)do if emu.read(a,mt)~=v then differences=differences+1 end end
 emu.log('CURRENTPALETTE|'..word(INDEX)..'|'..differences..'|'..ctx..'|'..word(W+2)..'|'..word(W+34)..'|'..word(W+36)..'|'..word(sy.SourceWorldTick4086_Phase)..'|'..word(sy.SourceWorldTick4086_Pending))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_','SourceCtorState4086_'))or k=='DmaQueue'}
    lua='local colourSymbols='+luav(extra)+'\nfor k,v in pairs(colourSymbols)do sy[k]=v end\n'+lua
    for k,v in dict(W=w,BASE=base,SIZE=plan['bytes'],CAP=plan['chr_capacity'],HW=h['controls'],HB=h['base']).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    asm='''CurrentPaletteProbe:
.a16
.i16
 php
 phx
 phy
 sed
 ldx #1
 ldy #0
 jsl CurrentPalette_Run
 bcs CurrentPaletteProbe_Bad
 ply
 plx
 plp
 clc
 rtl
CurrentPaletteProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
    reporter=Reporter('M4-CURRENT-COLOURMAP',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'CurrentPaletteProbe','VmState_Error',0xb6ab,[],lua,reporter,append=asm+emit(req,plan,sy),batch_size=4,frame_limit=10000,link_pcm=False)
    actual=[list(map(int,l.split('CURRENTPALETTE|',1)[1].split('|')))for l in log.splitlines()if 'CURRENTPALETTE|'in l];failures=[]
    for i,(c,v) in enumerate(zip(rows,actual)):
        e=[i,0,0,3 if c['fault']else 2,0 if c['fault']else c['selected'],0 if c['fault']else c['model'],7 if c['bad']=='phase'else 8,1]
        if v!=e:failures.append(dict(index=i,input=c,actual=v,expected=e))
    reporter.check('independent active/restore maps, exact source unsigned selection, birth and stale guards, all actor/CHR rows and CPU context',len(actual)==len(rows)and not failures)
    reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
    report=dict(schema='BYOR_CURRENT_COLOURMAP_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,results=actual,failures=failures,layout=plan,requirements=req,rom_sha256=hashlib.sha256(raw).hexdigest(),restore_map_representation='inherited BODY uint16; closed ent_set_colourmap producers clamp to maps_loaded<=65535; direct wider map mutation is unadmitted',birth_overwrites_stale_row=True,CGRAM_presentation_bound=False,production_CHR_producer_lease=False,model_transition_reset_bound=False,freeze_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
