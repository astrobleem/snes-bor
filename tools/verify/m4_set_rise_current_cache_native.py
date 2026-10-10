"""Actual set_rise typed cache selection and animation child, without rise flags."""
import json,sys
from pathlib import Path
from unittest.mock import patch
import m4_set_fall_current_cache_native as parent
from source_set_rise_select_native import derive,emit,emit_begin,emit_frame_prefix,emit_frame_owner

def main():
 original=parent.parent.run_fixture
 flags='--rise-flags'in sys.argv
 guards='--guard-flags'in sys.argv
 if guards:
  sys.argv.remove('--guard-flags')
  if not flags:raise ValueError('SET_RISE_GUARDS_REQUIRE_FLAGS')
 if flags:
  sys.argv.remove('--rise-flags')
  if '--frame-zero-owner'not in sys.argv:sys.argv.append('--frame-zero-owner')
  from compiler import Source
  from source_recovery_requirements import derive as recovery_policy
  from source_set_rise_flags_native import emit as flags_emit
  from source_hit_contact_layout import layout as contact_layout
  from source_hit_state_layout import layout as identity_layout
  from source_recovery_state_layout import layout as recovery_layout
  from source_foreign_state_layout import layout as foreign_layout
  from actor_s5_entity_fixture import symbols
  sy=symbols(Path('src/main.sym'));req=recovery_policy(Source(sys.argv[sys.argv.index('--source')+1]));cp=contact_layout();hp=identity_layout();cap=recovery_layout()['chr_capacity'];w=next(r['address']for r in foreign_layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls')
 def policy(source):
  r=derive(source);return dict(r,falls=r['rises'])
 def selection(w,r,sy):return emit(w,dict(r,rises=r['falls']),sy)
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  kw['append']=kw['append'].replace('SetFall','SetRise').replace('$B6B6','$B6C3')
  for key in ('probes','bindings'):
   kw[key]={n:v.replace('SetFall','SetRise')if isinstance(v,str)else v for n,v in kw.get(key,{}).items()}
  if flags:
   marker='FallFrameFlagsRequired:\n.a16\n.i16\n';assert kw['append'].count(marker)==1
   code=''
   if guards:
    tests=(('generation',' ldx #2\n ldy #0',''),('effect_marker',f' lda.l {w}+4\n asl a\n asl a\n asl a\n sta.l {w}+22\n asl a\n clc\n adc.l {w}+22\n tax\n lda #0\n sta.l $7EF114,x\n ldx #1\n ldy #0',f' lda.l {w}+22\n asl a\n clc\n adc.l {w}+22\n tax\n lda #$B62F\n sta.l $7EF114,x'),('self_pointer',f' lda #0\n sta.l {sy["SourceSelf4086_GlobalLow"]}+2\n ldx #1\n ldy #0',f' lda #$41\n sta.l {sy["SourceSelf4086_GlobalLow"]}+2'),('juggle_lease',f' lda #0\n sta.l {cp["controls"]}\n ldx #1\n ldy #0',f' lda #$B6A3\n sta.l {cp["controls"]}'))
    for i,(name,before,after)in enumerate(tests):
     code+=before+f'\nRiseGuardBefore{i}:\n.a16\n.i16\n nop\n jsl SetRiseFlags_Run\nRiseGuardAfter{i}:\n.a16\n.i16\n nop\n bcs RiseGuardRejected{i}\n jmp ModelPipeline_EntryBad\nRiseGuardRejected{i}:\n.a16\n.i16\n'+after+f'\n lda #5\n sta.l {w}+2\n'
     kw.setdefault('probes',{}).update({f'RISEGUARDBEFORE{i}':f'RiseGuardBefore{i}',f'RISEGUARDAFTER{i}':f'RiseGuardAfter{i}'})
    lua+='\nlocal riseGuardBad=0;local riseGuardCalls=0;local riseGuardBefore={};local riseGuardCpu={}\n'
    for i in range(len(tests)):
     lua+=f"""
emu.addMemoryCallback(function()riseGuardBefore={{}};for _,r in ipairs({{{{0x414000,18432}},{{0x439000,10240}},{{0x437e00,2560}},{{0x42d800,2048}},{{0x7ef100,3072}},{{{cp['base']},{cp['bytes']}}}}})do for j=0,r[2]-1 do riseGuardBefore[r[1]+j]=emu.read(r[1]+j,mt)end end;riseGuardCpu=emu.getState()end,emu.callbackType.exec,RISEGUARDBEFORE{i},RISEGUARDBEFORE{i},emu.cpuType.snes,mt)
emu.addMemoryCallback(function()for a,v in pairs(riseGuardBefore)do if emu.read(a,mt)~=v then riseGuardBad=riseGuardBad+1 end end;local s=emu.getState();for _,k in ipairs({{'x','y','d','dbr','sp'}})do if riseGuardCpu['cpu.'..k]~=s['cpu.'..k]then riseGuardBad=riseGuardBad+1 end end;if(s['cpu.ps']&254)~=(riseGuardCpu['cpu.ps']&254)or(s['cpu.ps']&1)~=1 or word({w}+2)~=4 then riseGuardBad=riseGuardBad+1 end;riseGuardCalls=riseGuardCalls+1 end,emu.callbackType.exec,RISEGUARDAFTER{i},RISEGUARDAFTER{i},emu.cpuType.snes,mt)
"""
    lua+="\nemu.addMemoryCallback(function()emu.log('RISEFLAGSREJECT|'..word(INDEX)..'|'..riseGuardCalls..'|'..riseGuardBad);riseGuardCalls=0;riseGuardBad=0 end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
   for i in range(2):code+=f' ldx #1\n ldy #0\n jsl SetRiseFlags_Run\n bcc RiseFlagsGood{i}\n jmp ModelPipeline_EntryBad\nRiseFlagsGood{i}:\n.a16\n.i16\n'
   kw['append']=kw['append'].replace(marker,marker+code)+flags_emit(w,req,sy)
   needle=' before={};for _,r in ipairs(ranges)';assert lua.count(needle)==1
   initialization=f""" set('SourcePhysicsState4086_Ready',0xb61c);set('SourceDamageEffectsState4086_Ready',0xb62f)
 put({cp['controls']},0xb6a3);put({cp['controls']}+8,1,4);put({cp['controls']}+16,{cp['base']&65535});put({cp['controls']}+18,0x42);put({cp['controls']}+20,{cap});put({cp['controls']}+22,128)
 put({hp['controls']}+20,{cap})
 put(0x437e10+c.slot*20,0xb5fb);put(0x437e12+c.slot*20,0);put(0x437e00+c.slot*20,7,4)
 put(0x42d800+c.slot*16,1,4);put(0x7ef114+c.slot*24,0xb62f);put(0x7ef116+c.slot*24,c.new);put(0x7ef100+c.slot*24,2,4);put(0x439010+c.slot*80,9,4)
 put({cp['base']}+8*c.slot+4,17,4)
"""
   # The current-cache installer subsequently initializes the hit controls;
   # change its declared CHR boundary as well as this contact owner's.
   from source_scoped_control_stack import layout as stack_layout
   palette_plan=parent.current.layout();colour_req=parent.current.derive(Source(sys.argv[sys.argv.index('--source')+1]))
   old_palette=parent.current.current(colour_req,palette_plan,sy,chr_capacity=stack_layout()['chr_capacity'])
   assert kw['append'].count(old_palette)==1
   kw['append']=kw['append'].replace(old_palette,parent.current.current(colour_req,palette_plan,sy,chr_capacity=cap))
   lua=lua.replace(f"put({hp['controls']}+20,{stack_layout()['chr_capacity']})",f"put({hp['controls']}+20,{cap})")
   lua=lua.replace(f"put({palette_plan['controls']}+20,{stack_layout()['chr_capacity']})",f"put({palette_plan['controls']}+20,{cap})")
   lua=lua.replace(needle,initialization+needle).replace('local ranges={',f'local ranges={{{{{cp["base"]},{cp["bytes"]}}},{{0x437e00,2560}},{{0x42d800,2048}},{{0x7ef100,3072}},')
   lua=lua.replace(f'word({w}+2)~=5',f'word({w}+2)~=6')
   needle=' local n=0;for a,v in pairs(before)';assert lua.count(needle)==1
   expected=f""" value(0x43900c+c.slot*80,27,4);value(0x439010+c.slot*80,0,4);value(0x437e00+c.slot*20,0,4);value(0x42d800+c.slot*16,0,4);value(0x7ef100+c.slot*24,0,4)
 value(0x416824+c.slot*64,0,4);local originalSelf=(c.slot+1)%128;value(0x416828+originalSelf*64,0,4);value(0x41682c+originalSelf*64,0,4);value({cp['base']}+8*c.slot+4,0,4)
"""
   lua=lua.replace(needle,expected+needle)
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  if guards:
   actual=[l.split('RISEFLAGSREJECT|')[1]for l in log.splitlines()if'RISEFLAGSREJECT|'in l]
   reporter.check('set_rise rejects stale generation, damaged effect, invalid self and missing juggle lease before actor writes with CPU preservation',actual==[f'{i}|4|0'for i in range(len(rows))])
  return raw,log
 if '--fall-flags'in sys.argv or '--finish-uninitialized-onfall'in sys.argv:raise ValueError('SET_RISE_FLAGS_NOT_BOUND')
 with patch.object(parent.parent,'run_fixture',fixture),patch.object(parent,'derive',policy),patch.object(parent,'emit',selection),patch.object(parent,'emit_begin',emit_begin),patch.object(parent,'emit_frame_prefix',emit_frame_prefix),patch.object(parent,'emit_frame_owner',emit_frame_owner):parent.main()
 out=Path(sys.argv[sys.argv.index('--output')+1]);p=out/'report.json';r=json.loads(p.read_text());r={k.replace('fall','rise'):v for k,v in r.items()};r.update(schema='BYOR_SET_RISE_CURRENT_CACHE_NATIVE_V1',full_set_rise_bound=False,source_set_rise_flags_bound=flags,source_global_self_velocity_asymmetry_bound=flags,native_guard_fault_cases=r['cases']*4 if guards else 0,source_missing_rise_branch_exercised=False,source_self_equals_target_exercised=False,source_zero_juggle_policy_bound=flags,production_memory_lease=False,motu_gameplay_proven=False);p.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
