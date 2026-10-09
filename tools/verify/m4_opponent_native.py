"""Bounded actual set_opponent writes, owner aliases, NULL and stale guards."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from source_opponent_authority import cases
from source_opponent_4086 import set_opponent
from source_opponent_native import emit
from source_foreign_state_layout import layout
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'))
    arena=layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES']);work=next(r['address']for r in arena['regions']if r['name']=='attack_chain_controls')
    rows=[dict(c,fault=0,bad='')for c in cases()if c['count']in (1,2,3,4,16,64,127,128)]
    for slot in range(1,127):
        for other in (None,0,127):rows.append(dict(count=128,ent=slot,other=other,owners=[None]*128,fault=0,bad=''))
    seed=dict(count=128,ent=0,other=127,owners=[None]*128,fault=0,bad='')
    for bad in ('ready','generation','canvas_generation','phase','time','count','ent_slot','other_slot','ent_token','other_token','ent_marker','other_marker','ent_cycle','other_cycle','owner_pointer'):
        rows.append(dict(seed,fault=1,bad=bad))
    lua=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={}, {},0
local ranges={{0x414000,10240},{0x409000,8192}}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);ctx=0
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do put(r[1]+j,165,1)end end
 for i=0,127 do
  local v=0x414000+80*i;local rel=0x409000+64*i
  put(v,v,4);put(v+4,i%2,4);put(rel+8,0,4);put(rel+12,0x414000+80*((i+1)%c.count),4);put(rel+58,0xb638)
  if i<c.count and c.owners[i+1]~=false then put(rel+8,0x414000+80*c.owners[i+1],4)end
 end
 put(W,0xb6a9);put(W+2,0);put(W+4,c.ent==false and 65535 or c.ent);put(W+6,c.other==false and 65535 or c.other);put(W+8,1,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',c.count);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);put(sy.VmSourceWorld_Time,48,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);put(sy.SourceWorldTick4086_TimeLo,48,4)
 set('SourceRetirement4086_Ready',0xb4f8);set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4)
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
 elseif c.bad=='ent_token'then put(0x414000,0x414001,4)
 elseif c.bad=='other_token'then put(0x414000+80*127,0x414001,4)
 elseif c.bad=='ent_marker'then put(0x40903a,0)
 elseif c.bad=='other_marker'then put(0x40903a+64*127,0)
 elseif c.bad=='ent_cycle'then put(0x409008,0x414000+80,4);put(0x409008+64,0x414000,4)
 elseif c.bad=='other_cycle'then put(0x409008+64*127,0x414000+80*126,4);put(0x409008+64*126,0x414000+80*127,4)
 elseif c.bad=='owner_pointer'then put(0x409008+64*127,0x414001,4)end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local differences=0;local actual={}
 for i=0,127 do actual[#actual+1]=word(0x40900c+64*i)|(word(0x40900e+64*i)<<16)end
 if c.fault==0 then for i,v in ipairs(c.expected)do for j=0,3 do before[0x40900c+64*(i-1)+j]=(v>>(8*j))&255 end end end
 for a,v in pairs(before)do if emu.read(a,mt)~=v then differences=differences+1 end end
 emu.log('OPPONENT|'..word(INDEX)..'|'..differences..'|'..ctx..'|'..word(W+2)..'|'..word(sy.SourceWorldTick4086_Phase)..'|'..word(sy.SourceWorldTick4086_Pending))
 emu.log('OPPONENTROWS|'..word(INDEX)..'|'..table.concat(actual,','))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    for c in rows:
        pool=[dict(owner=o,opponent=(i+1)%c['count'])for i,o in enumerate(c['owners'])]
        if not c['fault']:set_opponent(pool,c['ent'],c['other'])
        c['expected']=[0 if v['opponent']is None else 0x414000+80*v['opponent']for v in pool]
        c['expected'].extend(0x414000+80*((i+1)%c['count'])for i in range(c['count'],128))
        c['ent']=c['ent']if c['ent']is not None else False;c['other']=c['other']if c['other']is not None else False;c['owners']=[o if o is not None else False for o in c['owners']]
    extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'}
    lua='local opponentSymbols='+luav(extra)+'\nfor k,v in pairs(opponentSymbols)do sy[k]=v end\n'+re.sub(r'\bW\b',str(work),lua)
    asm='''OpponentProbe:
.a16
.i16
 php
 phx
 phy
 sed
 ldx #1
 ldy #0
 jsl SetOpponent_Run
OpponentProbe_Return:
.a16
.i16
 nop
 bcs OpponentProbe_Bad
 ply
 plx
 plp
 clc
 rtl
OpponentProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
    reporter=Reporter('M4-SOURCE-SET-OPPONENT',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'OpponentProbe','VmState_Error',0xb6a9,[],lua,reporter,append=asm+emit(work,sy),batch_size=4,frame_limit=7000,link_pcm=False)
    actual=[list(map(int,l.split('OPPONENT|',1)[1].split('|')))for l in log.splitlines()if 'OPPONENT|'in l]
    field_rows=[]
    for l in log.splitlines():
        if 'OPPONENTROWS|'in l:
            i,values=l.split('OPPONENTROWS|',1)[1].split('|');field_rows.append([int(i),[int(v)for v in values.split(',')]])
    expected=[[i,0,0,3 if c['fault']else 2,7 if c['bad']=='phase'else 8,1]for i,c in enumerate(rows)]
    wanted_rows=[[i,c['expected']]for i,c in enumerate(rows)]
    reporter.check('actual nullable opponent links, owner aliases, all physical rows, atomic guard rejection and CPU context',actual==expected and field_rows==wanted_rows)
    reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
    r=dict(schema='BYOR_SET_OPPONENT_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,results=actual,opponent_rows=field_rows,
        rom_sha256=hashlib.sha256(raw).hexdigest(),borrowed_control=[work,work+24],production_arena_union_bound=False,damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
