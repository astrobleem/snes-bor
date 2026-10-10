"""Execute compiled initial-camera placement with native lease/stage guards."""
import argparse,hashlib,json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from source_player_spawn_inputs import emit_stage
from source_foreign_water_retirement import emit as water,transform as retire_water
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS':raise ValueError('SPAWN_INPUT_NATIVE_REQUIRES_C_PROOF')
    stage=authority['requirements']['stages'][0];sy=symbols(Path('src/main.sym'))
    rows=[dict(index=index,fault=0,bad='',wanted=stage['placements'][index&3])for index in range(-1,7)]
    for bad in ('foreign','generation','world','level','environment','stage','walls','ctor','sticky','axis','camera_x','camera_y','player','player_high'):
        rows.append(dict(rows[0],fault=1,bad=bad))
    asm='''SpawnInputsFixture_Apply:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l $7FFD90
 ldx #1
 ldy #0
 jsl SpawnInputs_Apply
 bcs SpawnInputsFixture_Bad
 ply
 plx
 pla
 plp
 clc
 rtl
SpawnInputsFixture_Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
'''+emit_stage(stage,sy)+water(sy)
    setup=';'.join(f"set('{k}',{v})"for k,v in dict(SourceForeignWork_Ready=0xb671,SourceForeignWork_Status=1,SourceForeignWork_Generation=1,VmSourceWorld_Ready=0xb4a3,VmSourceWorld_Level=1,VmSourceWorld_ScrollAxis=0,VmSourceWorld_AdvanceX=0,VmSourceWorld_AdvanceY=0,SourceEnvironment4086_Ready=0xb4d1,SourceEnvironment4086_Stage=stage['stage_id'],SourceEnvironment4086_WallCount=0,SourceCtorState4086_Ready=0xb5c2,SourceCtorState4086_Status=0).items())
    lua=f'''local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v,n)put(sy[k],v,n)end
local before={{}};local cpu={{}};local start=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(0x7ffd90,c.index)
 for i=-8,71 do put(sy.SourceCtorState4086_Ready+i,165,1)end
 {setup}
 set('SourceForeignWork_Generation',1,4);set('VmSourceWorld_AdvanceX',0,4);set('VmSourceWorld_AdvanceY',0,4);set('SourceCtorState4086_Player',c.index&3,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,k in ipairs({{'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'}})do set(k,0)end
 for i=0,7 do put(sy.DmaQueue+i*8+7,0,1)end
 local invalid={{foreign={{'SourceForeignWork_Ready',0}},generation={{'SourceForeignWork_Generation',2}},world={{'VmSourceWorld_Ready',0}},level={{'VmSourceWorld_Level',0}},environment={{'SourceEnvironment4086_Ready',0}},stage={{'SourceEnvironment4086_Stage',2}},walls={{'SourceEnvironment4086_WallCount',1}},ctor={{'SourceCtorState4086_Ready',0}},sticky={{'SourceCtorState4086_Status',3}},axis={{'VmSourceWorld_ScrollAxis',1}},camera_x={{'VmSourceWorld_AdvanceX',1}},camera_y={{'VmSourceWorld_AdvanceY',1}},player={{'SourceCtorState4086_Player',0}},player_high={{'SourceCtorState4086_Player',65539}}}}
 if invalid[c.bad]then local q=invalid[c.bad];set(q[1],q[2],q[1]=='SourceCtorState4086_Player'and 4 or 2)end
 before={{}};for i=-8,71 do local at=sy.SourceCtorState4086_Ready+i;before[at]=emu.read(at,mt)end
 cpu=emu.getState();start=cpu.masterClock
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local state=emu.getState();local mismatch=0;local context=0
 if c.fault==0 then
  for _,q in ipairs({{{{'X',c.wanted.x_q16}},{{'Z',c.wanted.z_q16}},{{'A',0}},{{'Direction',c.wanted.flip}}}})do local at=sy['SourceCtorState4086_'..q[1]];for i=0,3 do before[at+i]=(q[2]>>(8*i))&255 end end
 end
 for at,v in pairs(before)do if emu.read(at,mt)~=v then mismatch=mismatch+1 end end
 for _,k in ipairs({{'a','x','y','d','dbr','sp'}})do if state['cpu.'..k]~=cpu['cpu.'..k]then context=context+1 end end
 if(state['cpu.ps']&254)~=(cpu['cpu.ps']&254)then context=context+1 end
 emu.log('SPAWNINPUT|'..word(INDEX)..'|'..mismatch..'|'..context..'|'..(state.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
    supplied=[k for k in sy if k.startswith('SourceForeignWork_')or k in ('StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled','DmaQueue')]
    lua='\n'.join(f"sy['{k}']={sy[k]}"for k in supplied)+'\n'+lua
    reporter=Reporter('M4-PLAYER-SPAWN-INPUTS',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SpawnInputsFixture_Apply','SourceCtorState4086_Ready',0xb5c2,[],lua,reporter,append=asm,rom_transform=retire_water,link_pcm=False)
    results=[list(map(int,line.split('SPAWNINPUT|',1)[1].split('|')))for line in log.splitlines()if'SPAWNINPUT|'in line]
    reporter.check('exact authored descriptors, negative index masking and stale lease/stage/camera guards preserve scope',len(results)==len(rows)and all(r[:3]==[i,0,0]for i,r in enumerate(results)))
    reporter.check('placement proof preserves production bank zero',raw[:32768]==a.rom.read_bytes()[:32768])
    report=dict(schema='BYOR_NATIVE_PLAYER_SPAWN_INPUTS_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),source_stage=stage,initial_camera_only=True,actual_constructor_join=False,full_spawnplayer_bound=False,production_consumer_bound=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
