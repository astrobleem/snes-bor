"""Source-derived constructor fixture resources and foreground service glue."""
import struct
from m4_animation_init_native import luav
from source_script_clone import derive as clone,pack as pack_clone
from source_lifecycle_inputs import derive as life,pack as pack_life
from source_model_factors import derive as factors,pack as pack_factors
from source_ctor_state import derive as state,pack as pack_state
from source_animation_init_4086 import derive as init,pack as pack_init
from source_offscreen_inputs import derive as offscreen,pack as pack_offscreen
from source_frame_effect_plan import derive as plan,pack as pack_plan
from source_model_core_4086 import derive as core,CACHED_FIELDS,FLOAT_FIELDS
from source_animation_ids import configure,role_id
from source_profile import document,discover
from compiler import key
from source_model_attack_policy import derive as policy,FIELDS as POLICY_FIELDS

def resources(source,er,bundle,locations):
 ir=init(source);fr=factors(source);mr=core(source)
 for name,data in [('clone',pack_clone(clone(source))),('life',pack_life(life(source))),('factors',pack_factors(fr)),('state',pack_state(state(source))),('init',pack_init(ir)),('offscreen',pack_offscreen(offscreen(source)))]:
  locations[name]=0x8000+len(bundle);bundle.extend(data);locations[name+'_bytes']=len(data)
 assert len(bundle)<=32768
 p=pack_plan(plan(er));cache=bytearray(5376);scalars=bytearray()
 for an in ir['animations']:
  m=next(m['id']for m in mr['models']if m['identity']==an['model'])
  struct.pack_into('<H',cache,2*(m*ir['maximum_animations']+an['engine_animation_id']),an['handle'])
 for m in mr['models']:
  for field in CACHED_FIELDS:scalars.extend(struct.pack('<f'if field in FLOAT_FIELDS else'<i',m['fields'][field]))
  scalars.extend(struct.pack('<i',m['fields']['type']))
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};d=discover(source,docs);cfg=configure(docs[key(d['models_path'])]['directives'])
 values=dict(SourceModelEntityCopy4086_Ready=0xb4eb,SourceModelEntityCopy4086_Entities=128,SourceModelEntityCopy4086_Models=16,SourceModelAnimationCopy4086_Ready=0xb4e9,SourceModelAnimationCopy4086_Models=16,SourceModelAnimationCopy4086_Maximum=ir['maximum_animations'],SourceModelAnimationCopy4086_Bytes=len(cache),SourceAnimationInit4086_Ready=0xb4ec,SourceAnimationInit4086_State=0,SourceAnimationInit4086_Issued=0,SourceAnimationInit4086_Handles=80,SourceDefaultChoice4086_Ready=0xb4fa,SourceDefaultChoice4086_Status=0,SourceDefaultChoice4086_Select=0,SourceDefaultChoice4086_TimeLo=48,SourceDefaultChoice4086_TimeHi=0,SourceDefaultChoice4086_Spawn=role_id(cfg,'spawn'),SourceDefaultChoice4086_Respawn=role_id(cfg,'respawn'),SourceDefaultChoice4086_Selection=role_id(cfg,'select'),SourceDefaultPlayer4086_Ready=0xb503,SourceDefaultPlayer4086_Status=0,SourceDefaultInit4086_Phase=0,SourceIdle4086_Ready=0xb4f3,SourceIdle4086_Status=0,SourceEmptyInitEnvironment4086_Ready=0xb504,SourceEmptyInitEnvironment4086_Models=16,SourceEmptyInitEnvironment4086_Stage=1,SourceEmptyInitEnvironment4086_Status=0,SourceEnvironment4086_Ready=0xb4d1,SourceEnvironment4086_Stage=1,SourceEnvironment4086_WallCount=0,SourceCtorOwner4086_Phase=0,SourceCtorOwner4086_Model=65535,SourceSpawnSlot4086_Status=0,SourceFactors4086_Ready=0xb5f1,SourceFactors4086_Status=0,SourceFactors4086_Models=16,SourceFactors4086_Attacks=fr['attack_types'],SourceLifecycle4086_Ready=0xb4fb,SourceLifecycle4086_Status=0,SourceLifecycle4086_Models=16,SourceScriptClone4086_Ready=0xb5c1,SourceScriptClone4086_Status=0,SourceScriptClone4086_Models=16,SourceCtorState4086_Status=0,SourceCtorState4086_Models=16,SourceCtorState4086_NoHit=0,SourceCtorState4086_SavedMode=0,SourceWorldTick4086_Maximum=0,SourceFrameMotion4086_Ready=0xb4e8,SourceFrameMotion4086_Status=0,SourceFrameEffectLeaf4086_Ready=0xb4f4,SourceSelf4086_Ready=0xb4f6,SourceSelf4086_Active=0,SourceSelf4086_Fault=0,SourceFrameEffectPlan4086_Ready=0xb4f2,SourceFrameEffectPlan4086_State=0,SourceFrameEffectPlan4086_Service=0,SourceFrameEffectPlan4086_Base=0x8000,SourceFrameEffectPlan4086_Bank=59,SourceFrameEffectPlan4086_Bytes=len(p),SourceFrameEffectPlan4086_Animations=80,SourceFrameEffectPlan4086_PairedCrcLo=struct.unpack_from('<I',p,24)[0]&65535,SourceFrameEffectPlan4086_PairedCrcHi=struct.unpack_from('<I',p,24)[0]>>16,SourceFrameEffectPlan4086_BodyCrcLo=struct.unpack_from('<I',p,28)[0]&65535,SourceFrameEffectPlan4086_BodyCrcHi=struct.unpack_from('<I',p,28)[0]>>16,SourceClock4086_Ready=0xb4c5,SourceClock4086_Due=1,SourceClock4086_TimeLo=48,SourceClock4086_TimeHi=0,SourceClock4086_Fault=0,SourceAttackCostState4086_Ready=0xb609,SourceMovementState4086_Ready=0xb60b,SourceAutokillState4086_Ready=0xb60e,SourceOffscreenState4086_Ready=0xb610,SourceOffscreenState4086_Models=16,SourceNamedKnife4086_State=0)
 for prefix,name in [('SourceAnimationInit4086','init'),('SourceScriptClone4086','clone'),('SourceLifecycle4086','life'),('SourceFactors4086','factors'),('SourceCtorState4086','state'),('SourceOffscreenState4086','offscreen')]:
  values.update({prefix+'_Base':locations[name],prefix+'_Bank':38,prefix+'_Bytes':locations[name+'_bytes']})
 values.update(SourceFreeze4086_Ready=0xb5df,SourceToss4086_Ready=0xb4e2,SourceModelAttackPolicy4086_Ready=0xb5f0,SourceModelAttackPolicy4086_Models=16,SourceAttackTiming4086_Ready=0,SourceAttackBody4086_Ready=0)
 setup='\n'.join(" set('"+k+"',"+str(v)+")"for k,v in values.items())
 policies=b''.join(struct.pack('<4i',*(m['fields'][f]for f in POLICY_FIELDS))for m in policy(source)['models'])
 setup+='\n copy(0x40bc00,'+luav(list(policies))+')\n'
 setup+='''
 copy(0x43c000,animation_cache);copy(0x40b000,scalar_cache)
 for _,r in ipairs({{0x40f000,4096},{0x43fd00,128},{0x40c000,12288},{0x439000,10240},{0x409000,8192},{0x43eb00,4096},{0x43d600,2560},{0x43fb00,512},{0x43fd80,32}})do for j=0,r[2]-1 do emu.write(r[1]+j,0,mt)end end
 put(0x43fd80,1,4);set('SourceTarget4086_OrderReady',0xb4d3);for j=0,127 do put(0x41f200+j*2,j)end
 put(sy.SourceSelf4086_GlobalLow,v,4);put(0x40c048+c.slot*96,2,4);put(0x439048+c.slot*80,MODEL);put(0x43904a+c.slot*80,0xb4fb);put(0x43904c+c.slot*80,0xb508)
 set('SourceCtorState4086_Time',48,4);set('SourceCtorState4086_Player',0,4);set('SourceSpawnSlot4086_OverrideLo',999999,4)
'''
 return p,'local animation_cache='+luav(list(cache))+'\nlocal scalar_cache='+luav(list(scalars))+'\n',setup,role_id(cfg,'walk')

CONSTRUCT=r'''
 lda.l PARENTSLOT
 sta.l KNIFEOWNER
 jsl NATIVEPUSH
 bcs ScriptedProjectileFixtureBad
 lda #WALKID
 ldx #$8000
 ldy #58
 jsl CTORBEGIN
 bcs ScriptedProjectileFixtureBad
 cmp #1
 bne ScriptedProjectileFixtureBad
ScriptedProjectileChildFrame:
.a16
.i16
 jsl STARTFRAME
 bcs ScriptedProjectileFixtureBad
 cmp #1
 bne ScriptedProjectileFixtureBad
 jsl CALLBACKBEGIN
 bcs ScriptedProjectileFixtureBad
ScriptedProjectileChildRun:
.a16
.i16
 jsl CALLBACKRUN
 bcs ScriptedProjectileFixtureBad
 cmp #3
 beq ScriptedProjectileChildRun
 cmp #4
 bne ScriptedProjectileFixtureBad
 lda #1
 jsl FRAMEACK
 bcs ScriptedProjectileFixtureBad
 jsl EFFECTRUN
 bcs ScriptedProjectileFixtureBad
 cmp #0
 bne ScriptedProjectileFixtureBad
 ldx #$8000
 ldy #58
 jsl CTORCONTINUE
 bcs ScriptedProjectileFixtureBad
 cmp #1
 beq ScriptedProjectileChildFrame
 cmp #0
 bne ScriptedProjectileFixtureBad
 lda.l CHILDSLOT
 sta.l KNIFECHILD
 lda.l CTORALTITUDE
 sta.l KNIFEALTITUDE
 lda.l CTORALTITUDE+2
 sta.l KNIFEALTITUDE+2
 lda #0
 sta.l KNIFEMAP
 sta.l KNIFEMAP+2
 sta.l KNIFECOST
 sta.l KNIFECOST+2
 sta.l KNIFENOCOST
 sta.l KNIFENOCOST+2
 sta.l KNIFENOHIT
 sta.l KNIFENOHIT+2
 sta.l KNIFESAVEDMODE
 sta.l KNIFESAVEDMODE+2
 jsl KNIFEAPPLY
 bcs ScriptedProjectileFixtureBad
 lda.l CHILDSLOT
 pha
 jsl NATIVEPOP
 bcs ScriptedProjectileFixtureBadStack
 pla
 jsl PUBLISHRESULT
 bcs ScriptedProjectileFixtureBad
ScriptedProjectileAfterChild:
.a16
.i16
 nop
ScriptedProjectileResumeCaller:
.a16
.i16
 jsl CALLBACKRUN
 bcs ScriptedProjectileFixtureBad
 cmp #3
 beq ScriptedProjectileResumeCaller
 cmp #4
 bne ScriptedProjectileFixtureBad
 lda #1
 jsl FRAMEACK
 bcs ScriptedProjectileFixtureBad
 jmp ScriptedProjectileConstructorDone
ScriptedProjectileFixtureBadStack:
.a16
.i16
 pla
 jmp ScriptedProjectileFixtureBad
ScriptedProjectileConstructorDone:
.a16
.i16
'''

BINDINGS=dict(PARENTSLOT='SourceUpdateFrame4086_Slot',KNIFEOWNER='SourceNamedKnife4086_Owner',NATIVEPUSH='SourceFrameStack4086_PushNative',CTORBEGIN='SourceCtorOwner4086_Begin',STARTFRAME='SourceAnimationInit4086_StartFrame',FRAMEACK='SourceUpdateFrame4086_Ack',EFFECTRUN='SourceFrameEffects4086_Run',CTORCONTINUE='SourceCtorOwner4086_Continue',CHILDSLOT='SourceDefaultInit4086_OwnerSlot',KNIFECHILD='SourceNamedKnife4086_Child',CTORALTITUDE='SourceCtorState4086_A',KNIFEALTITUDE='SourceNamedKnife4086_Altitude',KNIFEMAP='SourceNamedKnife4086_Map',KNIFECOST='SourceNamedKnife4086_EnergyCost',KNIFENOCOST='SourceNamedKnife4086_NoCost',KNIFENOHIT='SourceNamedKnife4086_NoHit',KNIFESAVEDMODE='SourceNamedKnife4086_SavedMode',KNIFEAPPLY='SourceNamedKnife4086_Apply',NATIVEPOP='SourceNativeSnapshot4086_PopPair',PUBLISHRESULT='SourceNativeResult4086_Publish')
