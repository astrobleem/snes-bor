"""Actual source damage facing over physical actor rows and guarded services."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
from compiler import Source
from source_damage_flip_native import emit
from source_damage_flip_requirements import derive
from source_foreign_state_layout import layout
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'));req=derive(Source(a.source))
    arena=layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES']);work=next(r['address']for r in arena['regions']if r['name']=='attack_chain_controls')
    base=dict(count=128,ent=0,other=127,fd=0,nopain=0,drop=0,frozen=0,x=0,other_x=65536,direction=7,other_direction=1,fault=0,bad='')
    rows=[]
    for ent,fd,frozen,nopain,drop in itertools.product((0,1,127),(-2,-1,0,1,2,3),range(2),range(2),range(2)):
        rows.append(dict(base,ent=ent,other=(ent+1)%128,fd=fd,frozen=frozen,nopain=nopain,drop=drop))
    for ent in range(128):rows.append(dict(base,ent=ent,other=(ent+1)%128))
    for x,other_x,direction in itertools.product((-2147483648,-65536,0,65536,2147483647),(-2147483648,-65536,0,65536,2147483647),(-2147483648,0,2147483647)):
        rows.append(dict(base,x=x,other_x=other_x,other_direction=direction));rows.append(dict(base,fd=1,x=x,other_x=other_x,other_direction=direction));rows.append(dict(base,fd=-1,x=x,other_x=other_x,other_direction=direction))
    for other in (None,0):rows.append(dict(base,other=other,bad='factor_ready'))
    for bad in ('ready','generation','canvas_generation','phase','time','count','ent_slot','other_slot','self','ent_token','other_token','x_tag','direction_tag','factor_ready','factor_marker','factor_model','model','pain','freeze_ready','combat_marker'):
        rows.append(dict(base,fault=1,bad=bad,nopain=1 if bad=='combat_marker'else 0))
    for c in rows:
        d=c['direction']
        if not c['fault'] and c['other']is not None and c['other']!=c['ent'] and not c['frozen'] and (not c['nopain']or c['drop']):
            if c['fd']==0:d=1 if c['x']<c['other_x']else 0 if c['x']>c['other_x']else d
            elif c['fd']==1:d=c['other_direction']
            elif c['fd']==-1:d=int(not c['other_direction'])
            elif c['fd']==2:d=1
            elif c['fd']==-2:d=0
        c['expected']=d;c['other']=c['other']if c['other']is not None else False
    lua=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={}, {},0
local ranges={{0x414000,10240},{0x416800,8192},{0x42e000,5120},{0x432800,4096},{0x43b900,512},{0x437e00,2560}}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);ctx=0
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do put(r[1]+j,165,1)end end
 for i=0,127 do
  local v=0x414000+80*i
  put(v,v,4);put(v+24,1,4);put(v+28,7,4);put(v+48,2,4);put(v+52,0,4)
  put(0x416800+64*i,0);put(0x43b900+4*i,0);put(0x43b902+4*i,0xb5f1)
  put(0x432814+32*i,0,4);put(0x42e000+40*i,0,4);put(0x437e00+20*i,0,4);put(0x437e10+20*i,0xb5fb)
 end
 local v=0x414000+80*c.ent;put(v+28,c.direction,4);put(v+52,c.x,4)
 if c.other~=false and c.other~=c.ent then put(0x414000+80*c.other+28,c.other_direction,4);put(0x414000+80*c.other+52,c.other_x,4)end
 put(0x42e000+40*c.ent,c.frozen,4);put(0x437e00+20*c.ent,c.drop,4)
 put(W,0xb6aa);put(W+2,0);put(W+4,c.ent);put(W+6,c.other==false and 65535 or c.other);put(W+8,1,4);put(W+12,c.nopain,4);put(W+16,c.fd,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',c.count);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);put(sy.VmSourceWorld_Time,48,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);put(sy.SourceWorldTick4086_TimeLo,48,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,v,4)
 set('SourceFreeze4086_Ready',0xb5df);set('SourceFactors4086_Ready',0xb5f1);set('SourceFactors4086_Models',MODELS)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 if c.bad=='ready'then put(W,0)
 elseif c.bad=='generation'then put(W+8,2,4)
 elseif c.bad=='canvas_generation'then put(sy.SourceForeignWork_Generation,2,4)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',7)
 elseif c.bad=='time'then put(sy.SourceWorldTick4086_TimeLo,49,4)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='ent_slot'then put(W+4,128)
 elseif c.bad=='other_slot'then put(W+6,128)
 elseif c.bad=='self'then put(sy.SourceSelf4086_GlobalLow,0,4)
 elseif c.bad=='ent_token'then put(v,0x414001,4)
 elseif c.bad=='other_token'then put(0x414000+80*c.other,0x414001,4)
 elseif c.bad=='x_tag'then put(v+48,1,4)
 elseif c.bad=='direction_tag'then put(v+24,2,4)
 elseif c.bad=='factor_ready'then set('SourceFactors4086_Ready',0)
 elseif c.bad=='factor_marker'then put(0x43b902+4*c.ent,0)
 elseif c.bad=='factor_model'then put(0x43b900+4*c.ent,1)
 elseif c.bad=='model'then put(0x416800+64*c.ent,MODELS)
 elseif c.bad=='pain'then put(0x432814+32*c.ent,0x3f800000,4)
 elseif c.bad=='freeze_ready'then set('SourceFreeze4086_Ready',0)
 elseif c.bad=='combat_marker'then put(0x437e10+20*c.ent,0)end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'cpu.x','cpu.y','cpu.d','cpu.sp','cpu.dbr'})do if cpu[k]~=s[k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local differences=0
 if c.fault==0 then for j=0,3 do before[0x41401c+80*c.ent+j]=(c.expected>>(8*j))&255 end end
 for a,v in pairs(before)do if emu.read(a,mt)~=v then differences=differences+1 end end
 emu.log('DAMAGEFLIP|'..word(INDEX)..'|'..differences..'|'..ctx..'|'..word(W+2)..'|'..word(sy.SourceWorldTick4086_Phase)..'|'..word(sy.SourceWorldTick4086_Pending))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_','SourceSelf4086_','SourceFreeze4086_','SourceFactors4086_'))or k=='DmaQueue'}
    lua='local flipSymbols='+luav(extra)+'\nfor k,v in pairs(flipSymbols)do sy[k]=v end\n'+lua
    for k,v in (('W',work),('MODELS',len(req['models']))):lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    asm='''DamageFlipProbe:
.a16
.i16
 php
 phx
 phy
 sed
 ldx #1
 ldy #0
 jsl DamageFlip_Run
DamageFlipProbe_Return:
.a16
.i16
 nop
 bcs DamageFlipProbe_Bad
 ply
 plx
 plp
 clc
 rtl
DamageFlipProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
    reporter=Reporter('M4-SOURCE-DAMAGE-FLIP',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'DamageFlipProbe','VmState_Error',0xb6aa,[],lua,reporter,append=asm+emit(req,work,sy),batch_size=4,frame_limit=10000,link_pcm=False)
    actual=[list(map(int,l.split('DAMAGEFLIP|',1)[1].split('|')))for l in log.splitlines()if 'DAMAGEFLIP|'in l]
    expected=[[i,0,0,3 if c['fault']else 2,7 if c['bad']=='phase'else 8,1]for i,c in enumerate(rows)]
    reporter.check('source facing, full signed coordinates/directions, all physical rows, guard rejection and CPU context',actual==expected)
    reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
    r=dict(schema='BYOR_DAMAGE_FLIP_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,results=actual,requirements=req,rom_sha256=hashlib.sha256(raw).hexdigest(),borrowed_control=[work,work+24],attack_descriptor_owner_bound=False,drop_and_effects_predecessor_bound=False,production_arena_union_bound=False,damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
