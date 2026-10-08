"""Actual source callback IDs through POST, landing services, movement and Ack."""
import argparse
import hashlib
import json
from pathlib import Path
from compiler import Source
from source_animation_physics_4086 import pack as pack_physics
from source_landing_plan_4086 import pack as pack_landing
from source_damage_inputs_4086 import pack as pack_damage
from source_script_clone import derive as clone,pack as pack_clone
from script_callback_owner import derive as callbacks,pack as pack_callbacks
from m4_gravity_landing_commit_native import LUA as BASE
from m4_post_air_pending_native import ASM
from _source_leaf_fixture import run_fixture
from _harness import Reporter

INSTALL=r'''
 set('SourcePostAir4086_Ready',0xb628);set('SourcePostAir4086_State',0);set('SourcePostAir4086_Service',0);set('SourcePostAir4086_Slot',s)
 set('SourcePostStationary4086_Ready',0);set('SourceCheckMove4086_Ready',0xb617);set('SourceCheckMove4086_Status',0)
 set('SourceWorldTick4086_Index',0)
 set('SourceLandingDamage4086_Ready',0xb629);set('SourceLandingDamage4086_Status',0);set('SourceLandingKill4086_Ready',0)
 set('SourceLandingCallback4086_Ready',0xb636);set('SourceLandingCallback4086_Status',0);set('SourceLandingCallback4086_State',0);set('SourceLandingCallback4086_InputsReady',0xb637)
 set('SourceLandingCallback4086_ReturnValue',0)
 set('SourceLandingCallback4086_HealthCheat',c.cheat,4);set('SourceLandingCallback4086_NoHurt',0,4)
 set('SourceLandingCallback4086_MagicType',0,4)
 set('SourceScore4086_Ready',0xb631);set('SourceScore4086_NoScriptsReady',0xb632);set('SourceScore4086_StatsReady',0xb633);set('SourceScore4086_LifeScore',50000,4);set('SourceScore4086_ScriptMask',0)
 for j=0,3 do put(0x7fbfa0+j*4,0,4);put(0x7fbfb0+j*4,5,4)end
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceWeapon4086_Ready',0xb4f1)
 set('SourceDamageState4086_Ready',0xb62b);set('SourceDamageEffectsState4086_Ready',0xb62f);set('SourceLandingEffects4086_Ready',0xb630)
 set('SourceBounceEffects4086_NoRumbleReady',0xb62d);set('SourceDropWeapon4086_Ready',0)
 set('SourceLandingDrop4086_Ready',0xb62e);set('SourceLandingDrop4086_Base',c.guardbreak==1 and 0x9000 or 0x8800);set('SourceLandingDrop4086_Bank',58);set('SourceLandingDrop4086_Bytes',DIBYTES);set('SourceLandingDrop4086_Models',16)
 set('SourceFactors4086_Ready',0xb5f1);put(0x43b900+s*4,0);put(0x43b902+s*4,0xb5f1)
 for _,o in ipairs({0,8,28})do put(0x432800+s*32+o,0x3f800000,4)end
 set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Base',0x8800);set('SourceScriptClone4086_Bank',60);set('SourceScriptClone4086_Bytes',CLONEBYTES);set('SourceScriptClone4086_Models',16)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_Base',0xa000);set('SourceAnimationCallback4086_Bank',60);set('SourceAnimationCallback4086_Models',16);set('SourceAnimationCallback4086_Programs',PROGRAMS)
 set('VmSourceWorld_TemplateCount',16);set('SourceModelEntityCopy4086_Models',16);set('SourceEmptyInitEnvironment4086_Models',16);set('SourceGravityAir4086_ZeroModels',16)
 set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 set('SourceSelf4086_GlobalLow',0,4);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Fault',0)
 put(aux,0,4);put(aux+4,0,4);put(aux+16,0);put(life+4,0,4);put(life+8,c.callback,4);put(life+16,0,4);put(life+20,0,4)
 put(life+64,0x40400000,4)
 put(core+72,c.callback==1 and 1 or 2,4)
 put(core,2,4);put(view+40,1);put(view+42,0);put(view+44,0,4)
 put(view+48,2);put(view+50,0);put(view+52,10*65536,4);put(view+56,2);put(view+58,0);put(view+60,20*65536,4);put(side+24,48,4)
 put(view+32,1);put(view+34,0);put(view+36,c.health,4);put(view+64,1);put(view+66,0);put(view+68,300,4)
 local rel=0x409000+s*64;for j=0,63 do emu.write(rel+j,0,mt)end
 if c.opponent==1 then put(rel+12,view,4)
 elseif c.opponent>1 then local other=(s+1)%128;local ov=0x414000+other*80;put(rel+12,ov,4);put(ov,ov,4);put(0x439048+other*80,0);put(0x43904a+other*80,0xb4fb);put(0x416800+other*64,0);put(ov+40,1);put(ov+42,0);put(ov+44,0,4);put(0x40c048+other*96,c.opponent==2 and 1 or 2,4)end
 local combat=0x437e00+s*20;put(combat,0,4);put(combat+16,0xb5fb);put(combat+18,0)
 local ds=0x7fb900+s*12;put(ds,0x40400000,4);put(ds+4,47,4);put(ds+8,0,4)
 local es=0x7ef100+s*24;for j=0,23 do emu.write(es+j,0,mt)end;put(es,3,4);put(es+4,11,4);put(es+8,12,4);put(es+12,13,4);put(es+20,0xb62f);put(es+22,0)
 put(0x7efd00+s*4,0,4);put(0x43e200+s*16,0);put(0x43e204+s*16,3,4)
 local ov=0x414000+((s+1)%128)*80
 local changes={owner_inputs={sy.SourceLandingCallback4086_InputsReady,0},core_ready={sy.SourceModelEntityCopy4086_Ready,0},weapon_ready={sy.SourceWeapon4086_Ready,0},weapon_owner={0x43e200+s*16,1},damage_inputs={sy.SourceLandingDrop4086_Ready,0},damage_bank={sy.SourceLandingDrop4086_Bank,0x40},damage_bank_high={sy.SourceLandingDrop4086_Bank,0x13a},damage_bytes={sy.SourceLandingDrop4086_Bytes,DIBYTES-1},effects_ready={sy.SourceDamageEffectsState4086_Ready,0},effects_marker={es+20,0},effects_model={es+22,1},rumble_ready={sy.SourceBounceEffects4086_NoRumbleReady,0},script_ready={sy.SourceScriptClone4086_Ready,0},script_mask={rel+44,2},factor_ready={sy.SourceFactors4086_Ready,0},factor_model={0x43b900+s*4,1},factor_marker={0x43b902+s*4,0},health_tag={view+32,2},max_tag={view+64,2},health_reserved={view+34,1},max_reserved={view+66,1},opponent_bank={rel+14,0x42},opponent_alignment={rel+12,0x4001},opponent_token={ov,0},opponent_life_marker={0x43904a+((s+1)%128)*80,0},opponent_model={0x416800+((s+1)%128)*64,1},opponent_player_tag={ov+40,2},magic_MP={sy.SourceLandingCallback4086_MagicType,1},nonunit_offense={0x43281e+s*32,0x4000},unknown_callback={life+8,65535},exploding={0x7efd00+s*4,2}}
 if c.bad and c.bad~='core_ready'and changes[c.bad]then local r=changes[c.bad];put(r[1],r[2])end
 emu.log('CALLBACKINIT|'..word(INDEX)..'|'..word(sy.SourcePostAir4086_Ready)..'|'..word(sy.SourceLandingCallback4086_Ready))
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--source',required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--score-body',action='store_true');p.add_argument('--guards',action='store_true');a=p.parse_args()
 a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'and authority['source_weaploss']==3 and authority['actual_empty_damage_script_dispatchers_proven']
 if a.score_body:assert authority['actual_addscore_and_SDL_rumble_bodies_proven']
 source=Source(a.source);cr=clone(source);ct=pack_clone(cr);cb,*_=callbacks(source);bt=pack_callbacks(cb)
 assert cr['models'][0]['initialized_mask']==0
 ph=pack_physics(dict(animations=[dict(handle=1,antigrav=0,dropframe=-1,landframe=-1,land_entity_index=-1,frames=[dict(movement=dict(base=-1,y=0))])]))
 lp=pack_landing(dict(plans=[dict(handle=1,model_index=0,animation_bounce=0.,model_bounce=0,noquake=0)]))
 tables=[pack_damage(dict(models=[dict(id=i,fields=dict(animal=0,nodrop=0,guardpoints=g if i==0 else 0))for i in range(16)]))for g in(0,1)]
 rows=[]
 for index,(c,state)in enumerate(zip(authority['inputs'],authority['actual'])):
  if (c['opponent']!=0 and not a.score_body)or c['invincible']!=0 or state['state'][2]!=0:continue
  for slot in(0,63,127):
   rows.append(dict(slot=slot,handle=1,a=0,base=0,altbase=0,vy=-65536,noadjust=1,hole=1,wall=1,platform=1,freeze=0,mark=0,time=48,toss=0,falling=1,hithead=1,gravity=0,minfall=-6*65536,maxtoss=100*65536,subject=0,
    damage=c['force'],dead=0,health=c['health'],callback=(10,1,8)[c['callback']],cheat=c['cheat'],guardbreak=c['guardbreak'],opponent=c['opponent'],score_after=state['parameters'][2],health_after=state['state'][1],return_value=state['state'][0],autoland=0,noquake=0,fault=0,bounced=0,pending=0,authority_case=index,expected=[0,0,0,0,0,49,12,11]))
 if a.guards:
  seed=next(r for r in rows if r['health']==100 and r['damage']==7 and r['callback']==10 and r['guardbreak']==0 and r['opponent']==0)
  rows=[]
  for slot in(0,63,127):
   for bad in('owner_inputs','core_ready','weapon_ready','weapon_owner','damage_inputs','damage_bank','damage_bank_high','damage_bytes','effects_ready','effects_marker','effects_model','rumble_ready','script_ready','script_mask','factor_ready','factor_model','factor_marker','health_tag','max_tag','health_reserved','max_reserved','opponent_bank','opponent_alignment','opponent_token','opponent_life_marker','opponent_model','opponent_player_tag','magic_MP','nonunit_offense','unknown_callback','exploding'):
    pending=bad in('magic_MP','nonunit_offense','unknown_callback','exploding')
    rows.append(dict(seed,slot=slot,bad=bad,fault=0 if pending else 1,pending=1,opponent=2 if bad.startswith('opponent_')or bad=='magic_MP'else 0,health_after=100,return_value=0,score_after=0,expected=[0,0,0,0,0,0,0,11]))
 lua=BASE[:BASE.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
 for token,value in dict(TABLEBYTES=len(ph),PLANBYTES=len(lp),PLANCOUNT=1,DIBYTES=len(tables[0]),CLONEBYTES=len(ct),PROGRAMS=cb['program_count']).items():lua=lua.replace(token,str(value))
 lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',1)")
 install=INSTALL
 for token,value in dict(DIBYTES=len(tables[0]),CLONEBYTES=len(ct),PROGRAMS=cb['program_count']).items():install=install.replace(token,str(value))
 lua=lua.replace(' before={};for',install+' before={};for')
 lua=lua.replace('{life-8,96}','{life-8,c.slot==127 and 88 or 96},{0x7fb900+s*12,12},{0x7ef100+s*24,24},{0x437e00+s*20,20},{0x409000+s*64,64},{0x7efd00+s*4,4},{0x7fbfa0,32}')
 lua=lua.replace(' local n=0;for a,v in pairs(before)',r'''
 for _,r in ipairs({{view+36,c.health_after},{phy+12,c.pending==1 and c.damage or 0},{side+24,c.pending==1 and 48 or 49},{0x7fb904+c.slot*12,c.pending==1 and 47 or 248},{0x7fb908+c.slot*12,c.pending==1 and 0 or 16}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
 for j=0,3 do before[0x7fbfa0+j]=(c.score_after>>(8*j))&255 end
 if c.guardbreak==0 and c.pending==0 then for j=0,3 do before[0x7ef100+c.slot*24+j]=0 end end
 if c.callback==8 and c.pending==0 then for _,r in ipairs({{0x40c004+c.slot*96,1},{0x40c008+c.slot*96,1},{0x40c010+c.slot*96,1},{0x40c014+c.slot*96,1},{0x40c024+c.slot*96,0}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end end
 local n=0;for a,v in pairs(before)''')
 lua=lua.replace("emu.log('GRAVITYCOMMIT|'","emu.log('LANDCALLBACK|'")
 lua=lua.replace("word(sy.SourceGravityLanding4086_Service))","word(sy.SourceGravityLanding4086_Service)..'|'..word(CALLSTATUS)..'|'..word(CALLRETURN)..'|'..word(sy.SourceWorldTick4086_Pending)..'|'..word(sy.SourceWorldTick4086_Index))")
 lua+=r'''
 emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];if c.bad=='core_ready'then set('SourceModelEntityCopy4086_Ready',0)end end,emu.callbackType.exec,sy.SourceLandingCallback4086_Execute,sy.SourceLandingCallback4086_Execute,emu.cpuType.snes,mt)
 emu.addMemoryCallback(function()emu.log('CALLBACKBEGIN|'..word(sy.SourcePostAir4086_Ready)..'|'..word(sy.SourceLandingCallback4086_Ready))end,emu.callbackType.exec,sy.SourcePostAir4086_Begin,sy.SourcePostAir4086_Begin,emu.cpuType.snes,mt)
 local lastPost='';local previousPost='';for name,address in pairs(sy)do if name:match('^SourcePostAir4086_')and address<0x400000 then emu.addMemoryCallback(function()previousPost=lastPost;lastPost=name end,emu.callbackType.exec,address,address,emu.cpuType.snes,mt)end end
 for _,name in ipairs({'SourcePostAir4086_Bad','SourceGravityAir4086_Bad','SourceGravityLanding4086_Bad','SourceLandingDamage4086_Bad','SourceLandingCallback4086_Bad','SourceCheckMove4086_Bad'})do
  local address=sy[name];assert(address,name);emu.addMemoryCallback(function()emu.log('CALLBACKFAULT|'..name..'|'..word(INDEX)..'|'..word(CALLSTATUS)..'|'..word(sy.SourceScriptClone4086_Status)..'|'..previousPost..'|'..emu.getState()['cpu.a']..'|'..word(sy.SourceWorldTick4086_State)..'|'..word(sy.SourceWorldTick4086_Phase))end,emu.callbackType.exec,address,address,emu.cpuType.snes,mt)
 end
'''
 asm=ASM.replace(' jsl POSTCHECK\n bcs PostPendingFixture_Bad',' jsl POSTCHECK\n bcs PostPendingFixture_Bad\n lda #11\n jsl WORLDACK\n bcs PostPendingFixture_Bad')
 reporter=Reporter('M4-LANDING-CALLBACK',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'PostPendingFixture_Run','SourcePostAir4086_Ready',0xb628,[(58,0,ph),(58,0x800,tables[0]),(58,0x1000,tables[1]),(59,0,lp),(60,0x800,ct),(60,0x2000,bt)],lua,reporter,append=asm,
  bindings=dict(POSTBEGIN='SourcePostAir4086_Begin',POSTCONTINUE='SourcePostAir4086_Continue',POSTCHECK='SourcePostAir4086_CheckAck',WORLDACK='SourceWorldTick4086_Ack',CALLSTATUS='SourceLandingCallback4086_Status',CALLRETURN='SourceLandingCallback4086_ReturnValue'),frame_limit=4000)
 actual=[[int(lpart)for lpart in l.split('LANDCALLBACK|',1)[1].split('|')]for l in log.splitlines()if'LANDCALLBACK|'in l]
 expected=[[i,0,0,3 if c['fault']else 1 if c['pending']else 2,1 if c['pending']else 2,2 if c['pending']else 0,3 if c['fault']else 1 if c['pending']else 2,c['return_value'],1 if c['pending']else 0,0 if c['pending']else 1]for i,c in enumerate(rows)]
 ok=actual==expected;reporter.check('actual callback IDs, services, source health and force, scalar guardbreak/cheat, source return, actor fences and real POST/world Ack',ok)
 report=dict(schema='BYOR_4086_LANDING_CALLBACK_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
  native_domain='positive self-landing; unit factors; nonlethal exact integer arithmetic; weaploss3; empty damage scripts; unfrozen; magic_type0; score below1up threshold',guard_matrix_only=a.guards,actual_callback_handler_ids=not a.guards,actual_post_and_world_ack=not a.guards,actual_native_score_service_proven=a.score_body and not a.guards and ok,source_weapon_service_called=False,lethal_callback_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
