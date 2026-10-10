"""Native closed completion-clock filter and unload speedup projection."""
import argparse,hashlib,json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_completion_clock_policy import emit
from source_clock_4086 import Clock,FIELD_CLOCKS,SHORT_CLOCKS,GAME_SPEED,MASTER_HZ
from source_foreign_water_retirement import emit as water,transform as retire_water
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_input_controller_native import offset
from m4_animation_init_native import luav


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','authority','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--observe-join',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=json.loads(a.authority.read_text());assert req['status']=='PASS';sy=symbols(Path('src/main.sym'));w=req['policy_controls'];speedup=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='global_fall_speedup');rows=[dict(c,wanted_due=e[0],wanted_counter=e[1],fault=0,bad='',initialize=0)for c,e in zip(req['inputs'],req['actual'])]
 rows.extend(dict(rows[0],pause=0,completed=c,speedup=1,interval=i,counter=0,wanted_due=i,wanted_counter=1,initialize=1)for c,i in ((0,1),(0,50),(1,1),(1,50)))
 for bad in (()if a.observe_join else('policy','clock','foreign','completed','counter','running','interval','speedup')):rows.append(dict(rows[0],fault=1,bad=bad))
 lua='local more='+luav({k:v for k,v in sy.items()if k.startswith('SourceForeignWork_')})+'\nfor k,v in pairs(more)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx,resultA={},{},0,0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(0x7ffd8e,c.initialize);set('VmSourceWorld_Ready',0);set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Running',1-c.pause);set('SourceClock4086_Due',c.pause==1 and 0 or c.interval);set('SourceClock4086_LastFieldsLo',word(INDEX)+10,4)
 set('SourceForeignWork_Ready',0xb671);set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_Completed',c.completed,4);put(SPEEDUP,c.speedup)
 put(POLICY,0xb6be);put(POLICY+2,c.counter);put(POLICY+4,word(INDEX)+9,4);if c.initialize==1 then put(POLICY,0);put(POLICY+2,0xa5a5);put(POLICY+4,0xa5a5a5a5,4)end
 if c.bad=='policy'then put(POLICY,0)elseif c.bad=='clock'then set('SourceClock4086_Ready',0)elseif c.bad=='foreign'then set('SourceForeignWork_Ready',0)elseif c.bad=='completed'then set('SourceScrollerPrefix4086_Ready',0)elseif c.bad=='counter'then put(POLICY+2,3)elseif c.bad=='running'then set('SourceClock4086_Running',2)elseif c.bad=='interval'then set('SourceClock4086_Due',51)elseif c.bad=='speedup'then put(SPEEDUP,2)end
 before={};for _,r in ipairs({{POLICY,8},{SPEEDUP,2},{sy.SourceClock4086_Due,2},{sy.SourceClock4086_LastFieldsLo,8},{sy.SourceClock4086_TimeLo,4}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();resultA=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local function value(a,v,n)for j=0,(n or 2)-1 do before[a+j]=(v>>(8*j))&255 end end
 if c.fault==0 then value(POLICY,0xb6be);value(POLICY+2,c.wanted_counter);value(POLICY+4,word(INDEX)+10,4);value(sy.SourceClock4086_Due,c.wanted_due);value(SPEEDUP,0)end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end;emu.log('COMPLETIONCLOCKRESULT|'..word(INDEX)..'|'..ctx..'|'..n..'|'..resultA)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''.replace('POLICY',str(w)).replace('SPEEDUP',str(speedup))
 if a.observe_join:
  lua=lua.replace('local before,cpu,ctx,resultA={},{},0,0','local before,cpu,ctx,resultA={},{},0,0;local observedDue=0;local observedLast={}').replace("set('SourceClock4086_Due',c.pause==1 and 0 or c.interval);","set('SourceClock4086_Due',0);set('SourceClock4086_Initialized',0xb4c6);set('SourceClock4086_PreviousShort',0);set('SourceClock4086_FieldsLo',c.interval==0 and 0 or c.interval==1 and 61 or c.interval==3 and 1 or 20,4);set('SourceClock4086_ShortsLo',0,4);set('SourceClock4086_LastShortsLo',0,4);set('SourceClock4086_PhaseLo',0,4);").replace("set('SourceClock4086_LastFieldsLo',word(INDEX)+10,4)","set('SourceClock4086_LastFieldsLo',0,4)").replace('put('+str(w)+'+4,word(INDEX)+9,4)','put('+str(w)+'+4,0xffffffff,4)')
  lua=lua.replace("if c.fault==0 then value(","if c.fault==0 then c.wanted_due=(c.pause==1 or(c.completed~=0 and c.speedup==0 and c.counter~=2))and 0 or observedDue;for j=0,7 do before[sy.SourceClock4086_LastFieldsLo+j]=observedLast[j+1]end; value(").replace('value('+str(w)+'+4,word(INDEX)+10,4)','for j=0,3 do before['+str(w)+'+4+j]=observedLast[j+1]end')
  lua+='''
emu.addMemoryCallback(function()observedDue=word(sy.SourceClock4086_Due);observedLast={};for j=0,7 do observedLast[j+1]=emu.read(sy.SourceClock4086_LastFieldsLo+j,mt)end;local function long(a)return word(a)|(word(a+2)<<16)end;emu.log('COMPLETIONCLOCKOBSERVED|'..word(INDEX)..'|'..long(sy.SourceClock4086_Snapshot)..'|'..long(sy.SourceClock4086_Snapshot+4)..'|'..long(sy.SourceClock4086_PhaseLo)..'|'..long(sy.SourceClock4086_RawLo)..'|'..observedDue..'|'..word(sy.SourceClock4086_Running))end,emu.callbackType.exec,CLOCKOBSERVED,CLOCKOBSERVED,emu.cpuType.snes,mt)
'''
 wrapper='''CompletionClockProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l $7FFD8E
 beq CompletionClockProbeReady
 jsl CompletionClock_Start
 bcs CompletionClockProbeBad
CompletionClockProbeReady:
.a16
.i16
 jsl CompletionClock_Filter
 bcs CompletionClockProbeBad
 jsl CompletionClock_Filter
 bcs CompletionClockProbeBad
 jsl CompletionClock_UnloadSpeedup
 ply
 plx
 plp
 clc
 rtl
CompletionClockProbeBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 if a.observe_join:
  wrapper=wrapper.replace(' jsl CompletionClock_Filter',f' lda.l {sy["SourceClock4086_Running"]}\n jsl {sy["SourceClock4086_Observe"]}\n bcs CompletionClockProbeBad\nCompletionClockObserved:\n.a16\n.i16\n nop\n jsl CompletionClock_Filter',1)
 wrapper+=f'''CompletionClockIsolatedReturn:
.a16
.i16
 php
 rep #$20
 pha
 lda #0
 sta.l {sy['SourceClock4086_Ready']}
 sta.l {sy['SourceScrollerPrefix4086_Ready']}
 pla
 plp
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml {sy['Vm_SourceFrameGate']+5}
'''
 def isolate(raw,linked):
  retire_water(raw,linked);at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['CompletionClockIsolatedReturn'].to_bytes(3,'little')
 r=Reporter('M4-COMPLETION-CLOCK-POLICY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'CompletionClockProbe','SourceLifecycle4086_Ready',0xb4fb,[],lua,r,append=wrapper+emit(req,speedup,sy)+water(sy),rom_transform=isolate,probes={'CLOCKOBSERVED':'CompletionClockObserved'}if a.observe_join else{},batch_size=8,link_pcm=False)
 actual=[list(map(int,l.split('COMPLETIONCLOCKRESULT|')[1].split('|')))for l in log.splitlines()if'COMPLETIONCLOCKRESULT|'in l];r.check('literal C completion filter and unload flag, once per observation under retry, preserve clock neighbors and CPU',len(actual)==len(rows)and all(v[:3]==[i,0,0]and(c['fault']or v[3]==c['wanted_due'])for i,(c,v)in enumerate(zip(rows,actual))));
 if a.observe_join:
  observations=[list(map(int,l.split('COMPLETIONCLOCKOBSERVED|')[1].split('|')))for l in log.splitlines()if 'COMPLETIONCLOCKOBSERVED|'in l];good=len(observations)==len(rows)
  for i,f,short,phase,rawticks,due,running in observations:
   c=Clock();expected_due=c.observe(f,short,bool(running));expected_raw=(f*FIELD_CLOCKS-short*SHORT_CLOCKS)*GAME_SPEED//MASTER_HZ;good=good and phase==c.phase and rawticks==expected_raw and due==expected_due
  r.check('actual source clock field observation, backlog and pause precede completion filter',good)
 r.check('bank0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768]);result=dict(schema='BYOR_COMPLETION_CLOCK_POLICY_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),policy_controls=w,policy_bytes=8,within_existing_clock_reservation=True,new_foreign_arena_bytes=0,source_observation_boundary_installed_by_fixture=not a.observe_join,source_field_epoch_installed_by_fixture=a.observe_join,actual_source_clock_observe_join_proven=a.observe_join,closed_toggle_duration_noslow_policy=True,unload_speedup_projection_only=True,full_unload_bound=False,production_clock_consumer_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True);(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
