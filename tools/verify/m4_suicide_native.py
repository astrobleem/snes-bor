"""Native suicide deadline/completion joined to actual no-event kill cleanup."""
import copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_retirement_native as parent
from actor_s5_entity_fixture import symbols
from source_foreign_state_layout import layout
from source_suicide_native import emit
from source_engine_function_ids import function_id
from source_foreign_water_retirement import emit as water,transform as retire_water
from m4_animation_init_native import luav
from m4_input_controller_native import offset
from _harness import Reporter

def main():
 sy=symbols(Path('src/main.sym'));w=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls');original=parent.run_fixture;seen={}
 class SuicideReporter(Reporter):
  def __init__(self,*args,**kw):super().__init__('M4-SUICIDE-KILL',**kw)
  def check(self,name,ok):
   if name.startswith('pinned C retirement state'):
    actual=[list(map(int,l.split('RETIRERESULT|')[1].split('|')))for l in seen['log'].splitlines()if'RETIRERESULT|'in l]
    expected=[[i,0,0,3 if c['fault']else 0 if c['early']else 2]for i,c in enumerate(seen['rows'])];ok=actual==expected;name='source suicide deadline and boss OR with literal kill relation/role/variable cleanup and full actor/CPU preservation'
   return super().check(name,ok)
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  base=[c for c in rows if not c['fault']and c['case']['mode']==0 and c['case']['summon']==0]
  faults=[c for c in rows if c['bad']]
  rows[:]=[]
  for c in base:
   for boss,stall in ((0,48),(2,48),(0,49)):
    r=copy.deepcopy(c);r.update(boss=boss,stall=stall,early=stall>48)
    if r['early']:r['after']=copy.deepcopy(r['before'])
    else:
     for packet in r['after']:
      if packet['at']==0x43fd80:packet['data'][28]|=boss
    for packet in r['after']:
     if packet['at']==0x7ffe38:packet['data']=list((0x414000+80*c['slot']).to_bytes(4,'little'))
    rows.append(r)
  rows.extend(dict(copy.deepcopy(c),boss=2,stall=48,early=False)for c in faults)
  seen['rows']=rows
  extra={k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','SourceLifecycle4086_','SourceFreeze4086_','SourceCtorState4086_','SourceScrollerPrefix4086_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'}
  lua='local suicideSymbols='+luav(extra)+'\nfor k,v in pairs(suicideSymbols)do sy[k]=v end\n'+lua
  lua=lua.replace('local ranges={','local ranges={{0x439000,10240},{0x433800,8192},{0x42e000,5120},{'+str(sy['SourceScrollerPrefix4086_Completed'])+',4},')
  needle=' before={};for _,r in ipairs(ranges)';assert lua.count(needle)==1
  initialization=f''' set('SourceForeignWork_Ready',0xb671);set('SourceForeignWork_Generation',1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({{'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'}})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceFreeze4086_Ready',0xb5df);set('SourceCtorState4086_Ready',0xb5c2);set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_Completed',c.case.completed,4);set('VmSourceWorld_Time',48,4)
 set('SourceSelf4086_GlobalLow',0x414000+80*c.slot,4)
 put(0x43900c+c.slot*80,{function_id('suicide')},4);put(0x43904a+c.slot*80,0xb4fb);put(0x439048+c.slot*80,0);put(0x416800+c.slot*64,0);put(0x43383e+c.slot*64,0xb5c2);put(0x433838+c.slot*64,c.boss,4);put(0x42e024+c.slot*40,0xb5df);put(0x42e008+c.slot*40,c.stall,4)
 for i=0,23 do put({w}+i,0,1)end;put({w},0xb6c5);put({w}+4,c.slot);put({w}+8,1,4);put({w}+16,48,4)
'''
  # Keep the parent's deliberately invalid caller pointer rejection.
  initialization+=" if c.bad=='self'then set('SourceSelf4086_Ready',0)end\n"
  initialization+=f" if c.bad=='slot'then put({w}+4,c.count)end\n"
  lua=lua.replace(needle,initialization+needle)
  needle=' local mismatch=0;for a,n in pairs(before)';assert lua.count(needle)==1
  expected=f''' if c.fault==0 and not c.early then local at=sy.SourceScrollerPrefix4086_Completed;local v=c.case.completed|c.boss;for i=0,3 do before[at+i]=(v>>(8*i))&255 end end
'''
  lua=lua.replace(needle,expected+needle)
  wrapper='''SuicideProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 ldx #1
 ldy #0
 jsl Suicide_Run
 bcs SuicideProbe_Bad
 jsl Suicide_Run
 bcs SuicideProbe_Bad
 ply
 plx
 plp
 clc
 rtl
SuicideProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
  wrapper+=f'''SuicideFixtureReturn:
.a16
.i16
 php
 rep #$20
 pha
 lda #0
 sta.l {sy['VmSourceWorld_Ready']}
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
   retire_water(raw,linked);at=offset(linked['LeafFixture_Return']);assert raw[at:at+4]==bytes.fromhex('7a fa 28 08');raw[at:at+4]=b'\x5c'+linked['SuicideFixtureReturn'].to_bytes(3,'little')
  kw.update(append=wrapper+emit(w,sy)+water(sy),rom_transform=isolate,link_pcm=False,batch_size=4);kw['bindings'].pop('CAPTUREENTRY');kw.setdefault('probes',{})['CAPTUREENTRY']='SuicideProbe'
  raw,log=original(rom,folder,rows,'SuicideProbe',ready,magic,tables,lua,reporter,**kw);seen['log']=log;reporter.check('bank0 remains byte-identical',raw[:32768]==rom.read_bytes()[:32768]);return raw,log
 args=sys.argv[1:]
 with patch.object(parent,'run_fixture',fixture),patch.object(parent,'Reporter',SuicideReporter),patch.object(sys,'argv',['m4_retirement_native.py',*args]):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 p=Path(args[args.index('--output')+1])/'report.json';r=json.loads(p.read_text());r.update(schema='BYOR_SUICIDE_KILL_NATIVE_V1',actual_source_suicide_bound=True,actual_no_event_retirement_bound=True,actual_check_ai_dispatch_bound=False,full_kill_callbacks_bound=False,production_memory_lease=False,new_foreign_arena_bytes=0);p.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
