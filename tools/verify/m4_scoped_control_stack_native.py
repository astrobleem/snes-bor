"""Native caller-control stack storage, liveness and byte-exact restoration."""
import argparse,hashlib,json,re
from pathlib import Path
from source_scoped_control_stack import layout,emit
from source_foreign_water_retirement import emit as water,transform as retire_water,ENTRIES
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 plan=layout();sy=symbols(Path('src/main.sym'));w=plan['controls'];base=plan['base'];stride=plan['stride'];rows=[]
 for op in (0,1):
  for d in range(8):
   for seed in (0,17,131,255):rows.append(dict(op=op,depth=d+op,seed=seed,bad='',fault=0))
 for seed in (17,131):
  rows.extend(dict(op=0,depth=d,seed=(seed+13*d)&255,bad='',fault=0,chain=1,step=d)for d in range(8))
  rows.extend(dict(op=1,depth=d,seed=(seed+7*d)&255,bad='',fault=0,chain=1,step=16-d)for d in range(8,0,-1))
 for op in (0,1):
  for bad in ('ready','base','bank','capacity','rows','stride','generation','foreign_ready','foreign_generation','water_marker','canvas','frontpanel','dma','depth'):
   rows.append(dict(op=op,depth=1,seed=31,bad=bad,fault=1))
  for bad in (('occupied',)if op==0 else('row_marker','row_depth','row_generation','row_stride')):
   rows.append(dict(op=op,depth=1,seed=31,bad=bad,fault=1))
 ranges=[(0x420000,0xb500),(0x42b500,1600),(0x7fa000,6400),(0x414000,10240),(0x7ffaec,52),(0x42bb40,0x10c0),(0x7ffae0,12)]
 lua='local plan='+luav(plan)+'\nlocal ranges='+luav([list(r)for r in ranges])+f'\nlocal W={w};local BASE={base};local STRIDE={stride};local foreignReady={sy["SourceForeignWork_Ready"]};local foreignGeneration={sy["SourceForeignWork_Generation"]}\n'
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu={},{};local cost=0;local waterhits=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function copy(a,n,t)for i=0,n-1 do t[a+i]=emu.read(a+i,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for _,r in ipairs(ranges)do if not(c.chain==1 and c.step>0 and r[1]==0x420000)then for i=0,r[2]-1 do emu.write(r[1]+i,(i*37+c.seed)&255,mt)end end end
 -- Fresh caller headers use unique bytes even across the chain.
 for _,r in ipairs(plan.regions)do for i=0,r.bytes-1 do emu.write(r.address+i,(i*53+c.seed)&255,mt)end end
 if c.chain~=1 or c.step==0 then for d=0,7 do put(BASE+d*STRIDE,c.op==0 and 0 or 0xb6af);put(BASE+d*STRIDE+2,d);put(BASE+d*STRIDE+4,1,4);put(BASE+d*STRIDE+8,STRIDE)end end
 put(W,0xb6ae);put(W+8,1,4);put(W+16,BASE&65535);put(W+18,0x42);put(W+20,plan.chr_capacity);put(W+22,8);put(W+24,STRIDE)
 put(foreignReady,0xb671);put(foreignGeneration,1,4);put(sy.SourceFrameStack4086_Depth,c.depth)
 put(sy.SourceFrameStack4086_Ready,0xb4ed);put(sy.SourceFrameStack4086_Fault,0)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do put(sy[n],0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 put(MODE,c.op);put(EXPECTFAULT,c.fault)
 local row=BASE+STRIDE*(c.depth-c.op)
 if c.bad=='ready'then put(W,0)elseif c.bad=='base'then put(W+16,0)elseif c.bad=='bank'then put(W+18,0x43)
 elseif c.bad=='capacity'then put(W+20,plan.chr_capacity+256)elseif c.bad=='rows'then put(W+22,7)elseif c.bad=='stride'then put(W+24,STRIDE+64)
 elseif c.bad=='generation'then put(W+8,0,4)elseif c.bad=='foreign_ready'then put(foreignReady,0)elseif c.bad=='foreign_generation'then put(foreignGeneration,2,4)
 elseif c.bad=='water_marker'then put(0x7ff866,0)
 elseif c.bad=='canvas'then put(0x7ff840,0)
 elseif c.bad=='frontpanel'then put(sy.StageFp_BG2Active,1,1)
 elseif c.bad=='dma'then put(sy.DmaQueue,2);put(sy.DmaQueue+4,0x40);put(sy.DmaQueue+5,0xa000);put(sy.DmaQueue+7,0x7f,1)
 elseif c.bad=='depth'then put(sy.SourceFrameStack4086_Depth,c.op==0 and 8 or 0)
 elseif c.bad=='occupied'then put(row,0xb6af)elseif c.bad=='row_marker'then put(row,0)
 elseif c.bad=='row_depth'then put(row+2,99)elseif c.bad=='row_generation'then put(row+4,2,4)elseif c.bad=='row_stride'then put(row+8,0)end
 before={};for _,r in ipairs(ranges)do copy(r[1],r[2],before)end
 -- Header itself and persistent row neighbors are included in the comparison.
 copy(plan.controls,plan.bytes,before)
 cpu=emu.getState();cost=cpu.masterClock;waterhits=0
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local st=emu.getState();local mismatch,ctx=0,0
 local want={};for k,v in pairs(before)do want[k]=v end
 local function expect(a,v,n)for i=0,(n or 2)-1 do want[a+i]=(v>>(8*i))&255 end end
 if c.fault==0 then
  local row=BASE+STRIDE*(c.depth-c.op)
  for _,r in ipairs(plan.regions)do for i=0,r.bytes-1 do if c.op==0 then want[row+r.offset+i]=before[r.address+i]else want[r.address+i]=before[row+r.offset+i]end end end
  if c.op==0 then expect(row,0xb6af);expect(row+2,c.depth);expect(row+4,1,4);expect(row+8,STRIDE)else expect(row,0)end
 end
 for k,v in pairs(want)do if emu.read(k,mt)~=v then mismatch=mismatch+1;if mismatch<=8 then emu.log('SCOPEDMISMATCH|'..word(INDEX)..'|'..k..'|'..v..'|'..emu.read(k,mt))end end end
 for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=st['cpu.'..k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('SCOPEDCONTROLS|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..(st['cpu.ps']&1)..'|'..(st.masterClock-cost)..'|'..waterhits)
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''
 asm=f"""ScopedControlsProbe:
.a16
.i16
 php
 rep #$38
 lda.l {0x7ffd88}
 bne ScopedControlsProbe_Restore
 plp
 jsl ScopedControls_Save
 bra ScopedControlsProbe_Water
ScopedControlsProbe_Restore:
.a16
.i16
 plp
 jsl ScopedControls_Restore
ScopedControlsProbe_Water:
.a16
.i16
"""+'\n'.join(' jsl ForeignWaterGate_'+op for op in ENTRIES)+'\n rtl\n'
 lua=lua.replace('MODE',str(0x7ffd88));reporter=Reporter('M4-SCOPED-CONTROLS',kind='GATE')
 lua+="\nfor _,pc in ipairs({ENTRY,SAVECOPY,GOOD,BAD})do emu.addMemoryCallback(function()local st=emu.getState();emu.log('SCOPEDTRACE|'..word(INDEX)..'|'..pc..'|'..st['cpu.d']..'|'..st['cpu.sp']..'|'..st['cpu.ps'])end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,mt)end\n"
 lua+="\nfor _,pc in ipairs({"+','.join('WG'+str(i)for i in range(len(ENTRIES)))+"})do emu.addMemoryCallback(function()waterhits=waterhits+1 end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,mt)end\n"
 raw,log=run_fixture(a.rom,a.output,rows,'ScopedControlsProbe','VmState_Error',0xb6ae,[],lua,reporter,append=asm+emit(plan,sy)+water(sy),rom_transform=retire_water,batch_size=4,frame_limit=2500,link_pcm=False,probes=dict(ENTRY='ScopedControls_Save',SAVECOPY='ScopedControls_CopySave',GOOD='ScopedControls_Good',BAD='ScopedControls_Bad',**{'WG'+str(i):'ForeignWaterGate_'+op+'_Retired'for i,op in enumerate(ENTRIES)}))
 actual=[list(map(int,l.split('SCOPEDCONTROLS|',1)[1].split('|')))for l in log.splitlines()if 'SCOPEDCONTROLS|'in l]
 failures=[dict(index=i,input=c,actual=v)for i,(c,v)in enumerate(zip(rows,actual))if v[:4]!=[i,0,0,c['fault']]]
 reporter.check('all caller bytes saved/restored, persistent rows retained, LIFO chains, stale guards and CPU context',len(actual)==len(rows)and not failures)
 reporter.check('all seven legacy water entries observe retirement, including invalid lease requests',len(actual)==len(rows)and all(v[5]>=7 for v in actual))
 reporter.check('bank zero unchanged',raw[:32768]==a.rom.read_bytes()[:32768])
 report=dict(schema='BYOR_SCOPED_CONTROL_STACK_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,results=actual,failures=failures,layout=plan,rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max((v[4]for v in actual),default=0),all_legacy_water_entries_called_retired=True,frame_owner_hook_bound=False,production_memory_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
