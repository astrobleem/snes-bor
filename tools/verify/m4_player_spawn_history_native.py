"""Native respawn ring reset with full history/CPU preservation and lease faults."""
import argparse,hashlib,itertools,json,re
from pathlib import Path
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_player_spawn_native import emit_history_reset
from source_foreign_water_retirement import emit as water,transform as retire_water
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM="""SpawnHistoryProbe:
.a16
.i16
 php
 pha
 phx
 phy
 lda.l $7FFD90
 ldx #$5678
 ldy #$1234
 sed
 jsl SpawnHistory_Reset
 bcs SpawnHistoryProbe_Bad
 jsl SpawnHistory_Reset
 bcs SpawnHistoryProbe_Bad
 ply
 plx
 pla
 plp
 clc
 rtl
SpawnHistoryProbe_Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
"""
LUA=r"""local mt=emu.memType.snesMemory;local before={};local cpu={};local cost=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(0x7ffd90,c.index)
 for i=0,1023 do put(HISTORY+i,(i*13+c.seed)&255,1)end
 set('SourceForeignWork_Ready',0xb671);set('SourceForeignWork_Status',1);set('SourceForeignWork_Generation',0x12345678,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 if c.bad=='ready'then set('SourceForeignWork_Ready',0)
 elseif c.bad=='generation'then set('SourceForeignWork_Generation',0x12345679,4)
 elseif c.bad=='zero'then set('SourceForeignWork_Generation',0,4)
 elseif c.bad=='canvas'then put(0x7ff840,0)
 elseif c.bad=='water'then put(0x7ff866,0)
 elseif c.bad=='frontpanel'then set('StageFp_BG2Loaded',1)end
 before={};for i=0,1023 do before[HISTORY+i]=emu.read(HISTORY+i,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cost=s.masterClock;cpu={};for _,k in ipairs({'a','x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,START,START,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local mismatch,ctx=0,0
 if c.fault==0 then for i=0,215 do before[HISTORY+c.index*256+i]=0 end;for i=232,235 do before[HISTORY+c.index*256+i]=0 end end
 for a,v in pairs(before)do if emu.read(a,mt)~=v then mismatch=mismatch+1 end end
 local s=emu.getState();for _,k in ipairs({'a','x','y','d','dbr'})do if s['cpu.'..k]~=cpu[k]then ctx=ctx+1 end end
 if s['cpu.sp']~=cpu.sp+3 or (s['cpu.ps']&254)~=(cpu.ps&254)then ctx=ctx+1 end
 emu.log('SPAWNHISTORY|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..(s.masterClock-cost))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
"""


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 sy=symbols(Path('src/main.sym'));history=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='input_history')
 rows=[dict(index=i,seed=seed,bad='',fault=0)for i,seed in itertools.product(range(4),(0,91,255))]
 rows += [dict(index=i,seed=91,bad=bad,fault=1)for i,bad in itertools.product(range(4),('ready','generation','zero','canvas','water','frontpanel'))]
 rows += [dict(index=i,seed=91,bad='index',fault=1)for i in (4,65535)]
 extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'}
 lua='local resetSymbols='+luav(extra)+'\nfor k,v in pairs(resetSymbols)do sy[k]=v end\n'+re.sub(r'\bHISTORY\b',str(history),LUA)
 reporter=Reporter('M4-SPAWN-HISTORY')
 raw,log=run_fixture(a.rom,a.output,rows,'SpawnHistoryProbe','SourceForeignWork_Ready',0xb6c7,[],lua,reporter,append=ASM+emit_history_reset(history,sy)+water(sy),probes={'START':'SpawnHistoryProbe'},rom_transform=retire_water,link_pcm=False,batch_size=4)
 results=[list(map(int,l.split('SPAWNHISTORY|')[1].split('|')))for l in log.splitlines()if 'SPAWNHISTORY|'in l]
 reporter.check('all rows reset only source rings/combostep or reject without any history writes',len(results)==len(rows) and all(row[:3]==[i,0,0]for i,row in enumerate(results)))
 reporter.check('production bank0 bytes unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 r=dict(schema='BYOR_PLAYER_SPAWN_HISTORY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),checks=reporter.results,ROM_sha256=hashlib.sha256(raw).hexdigest(),history_base=history,history_row_bytes=256,history_bytes_cleared_per_success=220,new_foreign_arena_bytes=0,peak_master_clocks=max((r[3]for r in results),default=0),full_spawnplayer_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
