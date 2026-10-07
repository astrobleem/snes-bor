"""Execute authored He_ManB frame callbacks through the native world owner.

Exclusive source pool after ordinary bootstrap; subsequent effect/audio service
is instrumented. This certifies callback ownership and source birth, not MOTU
player initialization, effect presentation, combat or Demo completion.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source,key
from source_profile import document,discover
from source_animation_ids import configure,role_id
from script_callback_owner import derive,pack,validate_pair
from source_frame_effects_4086 import derive as frame_effects,pack as pack_effects
from source_model_registry import derive as model_registry,pack as pack_registry
from source_birth_templates import derive as birth_templates,pack as pack_birth
from source_birth_core import derive as birth_core,pack as pack_core,STRIDE as CORE_STRIDE
from source_animation_init_4086 import derive as init_inputs,pack as pack_init
from source_lifecycle_inputs import derive as lifecycle_inputs
from source_animation_ids import derive as animation_identities
from source_model_core_4086 import derive as model_core_inputs
from source_idle_4086 import default_idle_capability
from source_walk_animation_4086 import default_walk_capability
from source_binary32_q16 import project as project_q16
from source_world_pool import empty_pool
from source_script_variables import descriptor
from script_dispatch_4086 import compile_source
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffb80,0x7ffb82,0x7ffb84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--effects-runner',action='store_true',help='Use real paired B4EP/motion/quake/self retirement; sound service instrumented.')
    p.add_argument('--birth-core',action='store_true',help='Execute actual B4BI core/flags/relation birth augmentation.')
    p.add_argument('--initial-select',action='store_true',help='Initialize authored player SELECT through real default-choice/ent_set_anim/frame-zero owners.')
    p.add_argument('--initial-jump',action='store_true',help='Run real default choice/action/JUMP frame zero and current makeinv fields, isolated.')
    p.add_argument('--initial-idle',action='store_true',help='Execute generic missing-animation set_idle and actual authored idle frame zero.')
    p.add_argument('--initial-walk',action='store_true',help='Execute generic default walk selection and actual authored walk frame zero.')
    p.add_argument('--initial-none-walk',action='store_true',help='Prepare authored TYPE_NONE walker from current speed, then execute real walk frame zero.')
    p.add_argument('--initial-enemy',help='Source identity for normal enemy initialization through actual authored frame zero.')
    p.add_argument('--drop-context',type=Path,help='Compiled readonly horizontal drop context bundle.')
    p.add_argument('--default-owner',action='store_true',help='Use generic source-order default-init Begin/Continue instead of direct leaf sequencing.')
    p.add_argument('--initial-none-model',help='Authored TYPE_NONE identity without WALK, through default owner and actual IDLE frame zero.')
    p.add_argument('--ctor-owner',action='store_true',help='Execute slot selection and complete generic constructor continuation instead of fixture leaf sequencing.')
    p.add_argument('--ctor-state',action='store_true',help='Run real reset/setup/model/script body owner before authored default initialization.')
    p.add_argument('--ctor-factors',action='store_true',help='Copy source-derived exact uniform defense/offense factors before model installation.')
    p.add_argument('--ctor-model',action='store_true',help='Install fresh fields from the current shared cached model before script bind.')
    p.add_argument('--script-clone',action='store_true',help='Run real constructor method-1 clear/bind before default initialization.')
    a=p.parse_args();a.initial_walk=a.initial_walk or a.initial_none_walk;folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);source=Source(a.source)
    owners,code,metadata,dispatch=derive(source);callbacks=pack(owners)
    registry=model_registry(source);models=pack_registry(registry);births=pack_birth(birth_templates(source))
    coretable=pack_core(birth_core(source)) if a.birth_core else b''
    if a.birth_core and not a.effects_runner:raise ValueError('BIRTH_CORE_REQUIRES_REAL_SELF_OWNER')
    validate_pair(callbacks,models,code,metadata,dispatch)
    effects=frame_effects(source);frames=pack_effects(effects)
    if a.effects_runner:
        from source_frame_effect_plan import derive as derive_plan,pack as pack_plan,unpack as unpack_plan
        plan=pack_plan(derive_plan(effects));unpack_plan(plan,frames)
    actor=next(m['id'] for m in registry['models'] if m['identity']=='He_ManB')
    default=next(m['id'] for m in registry['models'] if m['identity']=='He_Man')
    enemy_role=None
    if a.initial_enemy:
        default=next(m['id'] for m in registry['models'] if m['identity']==a.initial_enemy)
        if registry['models'][default]['declared_type']!='enemy':raise ValueError('INITIAL_ENEMY_TYPE')
        authored=[h for h in compile_source(source)['animation_handles'] if h['model']==a.initial_enemy]
        enemy_role='spawn'if any(h['role']=='spawn'for h in authored)else'idle'
        a.initial_idle=enemy_role=='idle';a.initial_select=enemy_role=='spawn'
        if not a.drop_context:raise ValueError('INITIAL_ENEMY_CONTEXT_REQUIRED')
    if a.initial_none_model:
        default=next(m['id'] for m in registry['models'] if m['identity']==a.initial_none_model)
        if model_core_inputs(source)['models'][default]['fields']['type']!=0:raise ValueError('INITIAL_NONE_TYPE')
        if any(h['model']==a.initial_none_model and h['role']=='walk'for h in compile_source(source)['animation_handles']):raise ValueError('INITIAL_NONE_HAS_WALK')
        if not a.default_owner:raise ValueError('INITIAL_NONE_REQUIRES_DEFAULT_OWNER')
        a.initial_idle=True
    if a.initial_none_walk:default=actor
    breath=next(m['id'] for m in registry['models'] if m['identity']=='HBreath')
    animation=next(h for h in compile_source(source)['animation_handles'] if h['model']=='He_ManB' and h['role']=='freespecial4')
    rows=[dict(f=f,direction=d,default=default,fault=0) for f in (3,4) for d in (0,1)]
    rows += [dict(f=4,direction=1,default=actor,fault=0),dict(f=4,direction=1,default=default,fault=1)]
    rows.insert(1,dict(f=3,direction=0,default=default,fault=0,warm=1))
    rows.insert(5,dict(f=4,direction=1,default=default,fault=0,warm=1))
    initializers_table=b'';animation_cache=b''
    idle_capability=default_idle_capability(animation_identities(source),model_core_inputs(source))if a.initial_idle else None
    walk_capability=default_walk_capability(animation_identities(source))if a.initial_walk else None
    if a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk:
        if not a.effects_runner or a.birth_core:raise ValueError('INITIAL_SELECT_REQUIRES_EFFECTS_RUNNER_WITHOUT_BIRTH_AUGMENTATION')
        actor=default;animation=next(h for h in compile_source(source)['animation_handles'] if h['model']==registry['models'][default]['identity'] and h['role']==(enemy_role if a.initial_enemy else 'jump'if a.initial_jump else'idle'if a.initial_idle else'walk'if a.initial_walk else'select'))
        docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')};structure=discover(source,docs);config=configure(docs[key(structure['models_path'])]['directives'])
        init_report=init_inputs(source);initializers_table=pack_init(init_report);cache=bytearray(16*init_report['maximum_animations']*2)
        for row in init_report['animations']:
            model=next(m['id'] for m in registry['models'] if m['identity']==row['model']);struct.pack_into('<H',cache,(model*init_report['maximum_animations']+row['engine_animation_id'])*2,row['handle'])
        animation_cache=bytes(cache);rows=[dict(f=0,direction=d,default=default,fault=0) for d in (0,1)]
    sy=symbols(Path('src/main.sym'));raw=bytearray(a.rom.read_bytes());entry=sy['Vm_SourceFrameGate']
    first=39*32768
    if raw[first:first+32768]!=bytes(32768) or raw[60*32768:61*32768]!=bytes(32768):raise ValueError('CALLBACK_NATIVE_RESERVED_ROM')
    base=sy['SourceVM_InstructionReservation'];at=offset(base)
    if raw[at:at+32768]!=b'\xff'*32768:raise ValueError('CALLBACK_NATIVE_SCRIPT_RESERVATION')
    cursor=0;locations={}
    for name,data in [('code',code),('dispatch',dispatch),('models',models),('births',births),('callbacks',callbacks)]:
        locations[name]=base+cursor;raw[at+cursor:at+cursor+len(data)]=data;cursor+=len(data)
    if coretable:
        locations['birthcore']=base+cursor;raw[at+cursor:at+cursor+len(coretable)]=coretable;cursor+=len(coretable)
    if initializers_table:
        locations['initializers']=base+cursor;raw[at+cursor:at+cursor+len(initializers_table)]=initializers_table;cursor+=len(initializers_table)
    script_clone_table=b''
    if a.script_clone:
        from source_script_clone import derive as clone_inputs,pack as pack_clone
        script_clone_report=clone_inputs(source);script_clone_table=pack_clone(script_clone_report);locations['scriptclone']=base+cursor;raw[at+cursor:at+cursor+len(script_clone_table)]=script_clone_table;cursor+=len(script_clone_table)
    if a.ctor_model:
        if not a.script_clone:raise ValueError('CTOR_MODEL_REQUIRES_SCRIPT_CLONE')
        from source_lifecycle_inputs import pack as pack_lifecycle
        ctor_life=pack_lifecycle(lifecycle_inputs(source));locations['ctorlife']=base+cursor;raw[at+cursor:at+cursor+len(ctor_life)]=ctor_life;cursor+=len(ctor_life)
        from source_model_core_4086 import CACHED_FIELDS,FLOAT_FIELDS
        ctor_cache=bytearray()
        for m in model_core_inputs(source)['models']:
            for field in CACHED_FIELDS:ctor_cache.extend(struct.pack('<f'if field in FLOAT_FIELDS else'<i',m['fields'][field]))
            ctor_cache.extend(struct.pack('<i',m['fields']['type']))
        # Scalar cache only: media bindings are not exercised by this fixture.
    if a.ctor_factors:
        if not a.ctor_model:raise ValueError('CTOR_FACTORS_REQUIRES_CTOR_MODEL')
        from source_model_factors import derive as factor_inputs,pack as pack_factors
        factor_report=factor_inputs(source);factor_table=pack_factors(factor_report);locations['factors']=base+cursor;raw[at+cursor:at+cursor+len(factor_table)]=factor_table;cursor+=len(factor_table)
    if a.ctor_state:
        if not a.ctor_factors:raise ValueError('CTOR_STATE_REQUIRES_FACTORS')
        from source_ctor_state import derive as ctor_inputs,pack as pack_ctor_state
        ctor_state_report=ctor_inputs(source);ctor_state_table=pack_ctor_state(ctor_state_report);locations['ctorstate']=base+cursor;raw[at+cursor:at+cursor+len(ctor_state_table)]=ctor_state_table;cursor+=len(ctor_state_table)
    if cursor>32768:raise ValueError('CALLBACK_NATIVE_IMMUTABLE_BANK_CAPACITY')
    raw[60*32768:60*32768+len(frames)]=frames
    if a.effects_runner:
        if raw[59*32768:60*32768]!=bytes(32768):raise ValueError('CALLBACK_PLAN_PRIVATE_BANK')
        raw[59*32768:59*32768+len(plan)]=plan
    if a.initial_enemy:
        context_report=json.loads((a.drop_context/'report.json').read_text());assert context_report['status']=='PASS'
        context_bundle=bytearray((a.drop_context/'bundle.bin').read_bytes())
        if raw[58*32768:59*32768]!=bytes(32768):raise ValueError('ENEMY_CONTEXT_PRIVATE_BANK')
        for i in range(len(context_report['stages'])):
            pointer=struct.unpack_from('<I',context_bundle,i*32+24)[0];struct.pack_into('<I',context_bundle,i*32+24,(58<<16)|(pointer&65535))
        raw[58*32768:58*32768+len(context_bundle)]=context_bundle
    asm='''.snes
.bank 39
.org $8000
CallbackFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4E7
 bne CallbackFixture_Return
 lda #0
 sta.l REQUEST
 sta.l INDEX
 sta.l ERROR
CallbackFixture_Init:
.a16
.i16
 nop
 jsl FRAMEBEGIN
 bcs CallbackFixture_Bad
 cmp #1
 bne CallbackFixture_Bad
CallbackFixture_BeforeOwner:
.a16
.i16
 nop
 jsl CALLBACKBEGIN
 bcs CallbackFixture_Bad
CallbackFixture_Run:
.a16
.i16
 jsl CALLBACKRUN
 bcs CallbackFixture_ExpectedFault
 cmp #3
 beq CallbackFixture_Run
 cmp #4
 bne CallbackFixture_Bad
 lda #1
 jsl FRAMEACK
 bcs CallbackFixture_Bad
 cmp #2
 bne CallbackFixture_Bad
CallbackFixture_AfterScript:
.a16
.i16
 nop
 ; Subsequent audio/effect service remains instrumented in this proof.
 lda #2
 jsl FRAMEACK
 bcs CallbackFixture_Bad
 jmp CallbackFixture_Result
CallbackFixture_ExpectedFault:
.a16
.i16
 lda.l EXPECTFAULT
 beq CallbackFixture_Bad
 jsl CHECKIDLE
 bcc CallbackFixture_Bad
 jsl CLOCKCOMMIT
 bcc CallbackFixture_Bad
CallbackFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcc CallbackFixture_Init
 bra CallbackFixture_Done
CallbackFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
CallbackFixture_Done:
.a16
.i16
 lda #0
 sta.l CALLBACKREADY
 sta.l FRAMEREADY
 sta.l WORLDREADY
 sta.l CONTEXTVALID
CallbackFixture_Return:
.a16
.i16
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml RESUME
'''
    if a.effects_runner:
        begin=asm.index(' ; Subsequent audio/effect service');end=asm.index(' jmp CallbackFixture_Result',begin)
        asm=asm[:begin]+'''CallbackFixture_Effects:
.a16
.i16
 jsl EFFECTRUN
 bcs CallbackFixture_Bad
 cmp #0
 beq CallbackFixture_EffectsDone
 cmp #9
 bne CallbackFixture_Bad
CallbackFixture_AudioService:
.a16
.i16
 nop
 lda #9
 sta.l EFFECTACKWORD
 jsl EFFECTACK
 bcs CallbackFixture_Bad
 jmp CallbackFixture_Effects
CallbackFixture_EffectsDone:
.a16
.i16
 jsl CLOCKCOMMIT
 bcs CallbackFixture_Bad
'''+asm[end:]
    if a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk:
        if a.initial_walk:
            asm=asm.replace(' jsl FRAMEBEGIN',' jsl WALKBEGIN\n bcs CallbackFixture_Bad\n cmp #1\n bne CallbackFixture_Bad\n jsl STARTFRAME')
        elif a.initial_idle:
            asm=asm.replace(' jsl FRAMEBEGIN',' jsl IDLEBEGIN\n bcs CallbackFixture_Bad\n cmp #1\n bne CallbackFixture_Bad\n jsl STARTFRAME')
        elif a.initial_jump:
            asm=asm.replace(' jsl FRAMEBEGIN',' jsl DEFAULTPREPARE\n bcs CallbackFixture_Bad\n jsl PLAYERBEGIN\n bcs CallbackFixture_Bad\n cmp #1\n bne CallbackFixture_Bad\n jsl STARTFRAME')
        else:asm=asm.replace(' jsl FRAMEBEGIN',' jsl DEFAULTBEGIN\n bcs CallbackFixture_Bad\n jsl STARTFRAME')
        asm=asm.replace(' jsl CLOCKCOMMIT',' jsl INITACK\n bcs CallbackFixture_Bad\n'+(' jsl PLAYERINV\n bcs CallbackFixture_Bad\n jsl DEFAULTTAIL\n bcs CallbackFixture_Bad\n'if a.initial_jump else'')+(' jsl DEFAULTTAIL\n bcs CallbackFixture_Bad\n'if a.initial_idle or a.initial_walk else'')+' jsl CLOCKCOMMIT')
    if a.initial_none_walk:asm=asm.replace(' jsl WALKBEGIN',' jsl NONEWALKPREP\n bcs CallbackFixture_Bad\n jsl WALKBEGIN')
    if a.initial_enemy:
        if enemy_role=='idle':
            asm=asm.replace(' jsl IDLEBEGIN',' jsl ENEMYPREP\n bcs CallbackFixture_Bad\n cmp #1\n bne CallbackFixture_Bad\n ldx #$8000\n ldy #58\n jsl ENEMYDROP\n bcs CallbackFixture_Bad\n cmp #0\n bne CallbackFixture_Bad\n jsl IDLEBEGIN')
        else:
            asm=asm.replace(' jsl CLOCKCOMMIT',' jsl ENEMYPREP\n bcs CallbackFixture_Bad\n cmp #0\n bne CallbackFixture_Bad\n jsl DEFAULTTAIL\n bcs CallbackFixture_Bad\n jsl CLOCKCOMMIT')
    if a.default_owner:
        if not(a.initial_enemy or a.initial_jump or a.initial_none_walk or a.initial_none_model or a.initial_select):raise ValueError('DEFAULT_OWNER_FIXTURE_MODE')
        start=asm.index(' nop\n',asm.index('CallbackFixture_Init:'))+len(' nop\n');end=asm.index('CallbackFixture_BeforeOwner:',start)
        asm=asm[:start]+" lda #"+str(role_id(config,'walk'))+"\n ldx #$8000\n ldy #58\n jsl OWNERBEGIN\n bcs CallbackFixture_Bad\n cmp #1\n bne CallbackFixture_Bad\nCallbackFixture_OwnerFrame:\n.a16\n.i16\n jsl STARTFRAME\n bcs CallbackFixture_Bad\n cmp #1\n bne CallbackFixture_Bad\n"+asm[end:]
        start=asm.index(' jsl INITACK',asm.index('CallbackFixture_EffectsDone:'));end=asm.index(' jsl CLOCKCOMMIT',start)
        asm=asm[:start]+" ldx #$8000\n ldy #58\n jsl OWNERCONTINUE\n bcs CallbackFixture_Bad\n cmp #1\n beq CallbackFixture_OwnerFrame\n cmp #0\n bne CallbackFixture_Bad\n"+asm[end:]
    if a.script_clone:
        if not a.default_owner:raise ValueError('SCRIPT_CLONE_REQUIRES_DEFAULT_OWNER_FIXTURE')
        asm=asm.replace('CallbackFixture_Init:\n.a16\n.i16\n nop','CallbackFixture_Init:\n.a16\n.i16\n nop\n jsl SCRIPTCLONECLEAR\n bcs CallbackFixture_Bad\n jsl SCRIPTCLONEBIND\n bcs CallbackFixture_Bad')
    if a.ctor_model:asm=asm.replace(' jsl SCRIPTCLONEBIND',' jsl CTORMODEL\n bcs CallbackFixture_Bad\n jsl SCRIPTCLONEBIND')
    if a.ctor_factors:asm=asm.replace(' jsl CTORMODEL',' jsl CTORFACTORS\n bcs CallbackFixture_Bad\n jsl CTORMODEL')
    if a.ctor_state:asm=asm.replace(' jsl CTORMODEL\n bcs CallbackFixture_Bad\n jsl SCRIPTCLONEBIND', ' jsl CTORSTATE')
    if a.ctor_owner:
        if not a.ctor_state:raise ValueError('CTOR_OWNER_REQUIRES_CTOR_STATE')
        asm=asm.replace(' jsl SCRIPTCLONECLEAR\n bcs CallbackFixture_Bad\n jsl CTORFACTORS\n bcs CallbackFixture_Bad\n jsl CTORSTATE\n bcs CallbackFixture_Bad','')
        asm=asm.replace(' jsl OWNERBEGIN',' jsl CTOROWNERBEGIN').replace(' jsl OWNERCONTINUE',' jsl CTOROWNERCONTINUE')
        asm=asm.replace('CallbackFixture_Result:\n.a16\n.i16\n nop','CallbackFixture_Result:\n.a16\n.i16\n nop\n jsl CTORRESULT\n bcs CallbackFixture_Bad\nCallbackFixture_ResultPublished:\n.a16\n.i16\n nop')
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,FRAMEBEGIN=sy['SourceUpdateFrame4086_Begin'],
        FRAMEACK=sy['SourceUpdateFrame4086_Ack'],CALLBACKBEGIN=sy['SourceAnimationCallback4086_Begin'],
        CALLBACKRUN=sy['SourceAnimationCallback4086_Run'],CALLBACKREADY=sy['SourceAnimationCallback4086_Ready'],
        FRAMEREADY=sy['SourceUpdateFrame4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],
        CONTEXTVALID=sy['VmNativeVariant_ContextValid'],RESUME=entry+5,CASES=len(rows))
    values.update(EXPECTFAULT=0x7ffb86,CHECKIDLE=sy['SourceUpdateFrame4086_CheckIdle'],CLOCKCOMMIT=sy['SourceClock4086_Commit'])
    if a.effects_runner:values.update(EFFECTRUN=sy['SourceFrameEffects4086_Run'],EFFECTACK=sy['SourceFrameEffectPlan4086_Ack'],EFFECTACKWORD=sy['SourceFrameEffectPlan4086_Acknowledged'])
    if a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk:values.update(DEFAULTBEGIN=sy['SourceDefaultChoice4086_Begin'],STARTFRAME=sy['SourceAnimationInit4086_StartFrame'],INITACK=sy['SourceAnimationInit4086_Ack'])
    if a.initial_jump:values.update(DEFAULTPREPARE=sy['SourceDefaultChoice4086_Prepare'],PLAYERBEGIN=sy['SourceDefaultPlayer4086_BeginAction'],PLAYERINV=sy['SourceDefaultPlayer4086_ApplyInvincibility'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.initial_idle:values.update(IDLEBEGIN=sy['SourceDefaultInit4086_BeginIdle'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.initial_walk:values.update(WALKBEGIN=sy['SourceWalk4086_BeginDefaultOnly'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.initial_none_walk:values.update(NONEWALKPREP=sy['SourceDefaultNone4086_PrepareWalk'])
    if a.initial_enemy:values.update(ENEMYPREP=sy['SourceDefaultEnemy4086_PrepareNormal'],ENEMYDROP=sy['SourceDefaultEnemy4086_BeginHorizontalDrop'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.default_owner:values.update(OWNERBEGIN=sy['SourceDefaultInit4086_Begin'],OWNERCONTINUE=sy['SourceDefaultInit4086_Continue'])
    if a.script_clone:values.update(SCRIPTCLONECLEAR=sy['SourceScriptClone4086_Clear'],SCRIPTCLONEBIND=sy['SourceScriptClone4086_Bind'])
    if a.ctor_owner:values.update(CTOROWNERBEGIN=sy['SourceCtorOwner4086_Begin'],CTOROWNERCONTINUE=sy['SourceCtorOwner4086_Continue'],CTORRESULT=sy['SourceCtorOwner4086_Result'])
    if a.ctor_state:values.update(CTORSTATE=sy['SourceCtorState4086_Begin'])
    if a.ctor_factors:values.update(CTORFACTORS=sy['SourceFactors4086_Apply'])
    if a.ctor_model:values.update(CTORMODEL=sy['SourceCtorModel4086_Apply'])
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    branch=[0]
    def relax(m):
        branch[0]+=1;label='CallbackFixture_Branch_'+str(branch[0])
        return ' '+dict(bcc='bcs',bcs='bcc',beq='bne',bne='beq')[m[1]]+' '+label+'\n jmp '+m[2]+'\n'+label+':\n.a16\n.i16'
    asm=re.sub(r'^ (bcc|bcs|beq|bne) (CallbackFixture_\w+)$',relax,asm,flags=re.M)
    pasm=folder/'callback_fixture.pasm';pasm.write_text(asm)
    built=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm),'--output',str(folder/'callback_fixture.bin'),'--symbols',str(folder/'callback_fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError('CALLBACK_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'callback_fixture.sym');fixture=(folder/'callback_fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a') or len(fixture)>32768:raise ValueError('CALLBACK_FIXTURE_GATE')
    raw[first:first+len(fixture)]=fixture
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['CallbackFixture_Gate'])[:3]+b'\xea'
    path=folder/'bor.sfc';path.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    pool,sides=empty_pool(128)
    initial_meta=metadata
    lua='local rows={'+','.join('{'+','.join(k+'='+str(v) for k,v in c.items())+'}' for c in rows)+'}\n'
    lua+='local sy={'+','.join(k+'='+str(v) for k,v in sy.items() if k.startswith(('Source','Vm'))) +'}\n'
    lua+='local metadata={'+','.join(map(str,initial_meta))+'}\n'
    lua+='local pool={'+','.join(map(str,pool))+'}\n'
    lua+='local vars_descriptor={'+','.join(map(str,descriptor(0x414000,count=384)))+'}\n'
    if coretable:lua+='local birthcore={'+','.join(map(str,coretable[24+breath*CORE_STRIDE+16:24+(breath+1)*CORE_STRIDE]))+'}\n'
    if animation_cache:lua+='local animation_cache={'+','.join(map(str,animation_cache))+'}\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local spans=0;local context_faults=0;local before_call={};local owner_start=0;local owner_field=0
local init_faults=0;local copy_checks=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,n-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n or 2)end
local function copy(a,data)for i,v in ipairs(data)do emu.write(a+i-1,v,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];spans=0;context_faults=0;init_faults=0;copy_checks=0
 put(0x7ffb86,c.fault,2)
 copy(sy.VmCode_Wram,metadata);copy(0x414000,pool)
 for j=0,8191 do emu.write(0x416800+j,0,mt)end
 if not c.warm then for j=0,24575 do emu.write(0x418800+j,0,mt)end end
 for j=0,2815 do emu.write(0x41f500+j,0,mt)end
 copy(sy.VmSourceVars_Ready,vars_descriptor)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_State',0)
 set('SourceAnimationCallback4086_Base',CALLBACKBASE);set('SourceAnimationCallback4086_Bank',CODEBANK)
 set('SourceAnimationCallback4086_Bytes',CALLBACKBYTES)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceUpdateFrame4086_Slot',0);set('SourceUpdateFrame4086_Request',c.f)
 set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FRAMEBYTES)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800)
 set('VmSourceWorld_Count',128);set('VmSourceWorld_Level',1);set('VmSourceWorld_Time',48,4)
 set('VmSourceWorld_TemplateBase',BIRTHBASE);set('VmSourceWorld_TemplateBank',CODEBANK)
 set('VmSourceWorld_TemplateCount',MODELCOUNT);set('VmSourceWorld_TemplateBytes',BIRTHBYTES)
 set('VmSourceWorld_Players',1);set('VmSourceWorld_AdvanceX',0,4);set('VmSourceWorld_AdvanceY',0,4);set('VmSourceWorld_ScrollAxis',0)
 set('VmSourceModels_Ready',0xb4a1);set('VmSourceModels_Base',MODELBASE);set('VmSourceModels_Bank',CODEBANK)
 set('VmSourceModels_Count',MODELCOUNT);set('VmSourceModels_Bytes',MODELBYTES)
 for j=0,63 do emu.write(sy.VmSourceModels_Loaded+j,j<2 and 255 or 0,mt)end
 set('VmSourceEntity_Ready',0xb48b);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',128)
 set('VmSourceMutation_Ready',0xb4a2);set('SourceToss4086_Ready',0xb4e2)
 set('SourceVMRun4086_Ready',0xb4d7);set('SourceVMRun4086_Busy',0)
 set('VmSourceCallback_Ready',0xb4a5);set('VmSourceCallback_Active',0);set('VmSourceCallback_Request',0)
 set('VmSourceFrame_Ready',0xb4fd);set('VmSourceFrame_Base',DISPATCHBASE);set('VmSourceFrame_Bank',CODEBANK)
 set('VmSourceFrame_Bytes',DISPATCHBYTES);set('VmSourceFrame_Programs',PROGRAMCOUNT);set('VmSourceFrame_Handles',80);set('VmSourceFrame_Pending',0)
 set('VmSourceInstr_Ready',0xb48e);set('VmSourceInstr_Base',0x8000);set('VmSourceInstr_Bank',CODEBANK)
 set('VmPriv_InstrOff',0);set('VmCall_CallsitesOff',CALLSITES);set('VmCall_ArgSlotsOff',ARGS);set('VmStr_StringsOff',STRINGS)
 set('VmState_InstrCount',INSTRUCTIONS);set('VmState_SlotCount',SLOTS);set('VmState_FrameTop',0);set('VmState_Error',0);set('VmState_Status',0,1)
 set('VmNativeVariant_ContextValid',0);set('SourceWorldTick4086_Ready',0);set('SourceClock4086_Ready',0)
 set('SourceFrameEffectPlan4086_Ready',0);set('SourceSelf4086_Ready',0);set('SourceFrameMotion4086_Ready',0)
 set('SourceAnimationInit4086_Ready',0);set('SourceModelAnimation4086_Ready',0);set('SourceModelTransition4086_Ready',0);set('SourceFrameStack4086_Ready',0)
 set('SourceRetirement4086_Ready',0)
 set('SourceLifecycle4086_Ready',0)
 set('SourceBirthCore4086_Ready',0)
 INSTALL_EFFECT_RUNNER
 INSTALL_BIRTH_CORE
 put(0x414004,1,2)
 for n,tag in ipairs({2,1,1,1,1,2,2,1})do put(0x414000+8*n,tag,4)end
 put(0x414014,ANIMATIONID,4);put(0x41401c,c.direction,4);put(0x414024,150,4)
 put(0x414034,80*65536,4);put(0x41403c,220*65536,4);put(0x414044,150,4)
 put(0x416800,ACTORID,2);put(0x416802,c.default,2);put(0x416804,HANDLE,2)
 put(0x41f510,1,2)
 INSTALL_INITIAL_SELECT
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local state=emu.getState();owner_start=state.masterClock;owner_field=state['ppu.frameCount']
 if c.fault==1 then
  set('VmSourceWorld_TemplateBase',BIRTHBASE+2)
  set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Due',1);set('SourceClock4086_TimeLo',48,4)
 end
end,emu.callbackType.exec,BEFOREOWNER,BEFOREOWNER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();before_call={}
 if emu.read(sy.VmState_Status,mt)==1 then
  local source=sy.VmCode_Wram+word(sy.SourceAnimationCallback4086_Initializers)
  local target=sy.VmSlots_Wram+8*word(sy.SourceAnimationCallback4086_SlotBase)
  local bytes=8*word(sy.SourceAnimationCallback4086_Slots)
  for i=0,bytes-1 do if emu.read(source+i,mt)~=emu.read(target+i,mt)then init_faults=init_faults+1 end end
  copy_checks=copy_checks+1
 end
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do before_call[k]=s['cpu.'..k]end
end,emu.callbackType.exec,RUNENTRY,RUNENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();spans=spans+1
 for _,k in ipairs({'x','y','d','dbr'})do if before_call[k]~=s['cpu.'..k]then context_faults=context_faults+1 end end
 if before_call.sp+3~=s['cpu.sp'] or (before_call.ps&254)~=(s['cpu.ps']&254)then context_faults=context_faults+1 end
end,emu.callbackType.exec,RUNRETURN,RUNRETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local live=0;local local_faults=0
 for j=0,127 do live=live+word(0x414004+80*j)end
 for j=0,3 do for k=0,7 do if emu.read(0x418808+64*j+k,mt)~=0 then local_faults=local_faults+1 end end end
 emu.log('CALLBACKOWNER|'..word(INDEX)..'|'..word(sy.SourceAnimationCallback4086_State)..'|'..word(sy.SourceAnimationCallback4086_Status)..'|'..word(sy.VmSourceCallback_Active)..'|'..word(sy.VmNativeVariant_ContextValid)..'|'..word(sy.SourceUpdateFrame4086_Pending)..'|'..live..'|'..dw(0x414050+12)..'|'..dw(0x414050+52)..'|'..dw(0x414050+60)..'|'..spans..'|'..context_faults..'|'..local_faults..'|'..word(0x416840)..'|'..dw(0x41684c))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState()
 emu.log('CALLBACKCOST|'..word(INDEX)..'|'..(state.masterClock-owner_start)..'|'..owner_field..'|'..state['ppu.frameCount'])
 for i,v in ipairs(metadata)do if emu.read(sy.VmCode_Wram+i-1,mt)~=v then init_faults=init_faults+1 end end
 emu.log('CALLBACKINIT|'..word(INDEX)..'|'..init_faults..'|'..copy_checks)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log('CALLBACKBAD|'..word(INDEX)..'|'..s['cpu.a']..'|'..word(sy.SourceAnimationCallback4086_State)..'|'..word(sy.SourceAnimationCallback4086_Fault)..'|'..emu.read(sy.VmState_Status,mt)..'|'..word(sy.VmState_Error)..'|'..word(sy.VmCall_TargetId))
 emu.log('CALLBACKSELECTBAD|'..word(sy.SourceDefaultChoice4086_Status)..'|'..word(sy.SourceDefaultChoice4086_Chosen)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.SourceAnimationInit4086_Handle)..'|'..word(sy.SourceAnimationInit4086_Count)..'|'..word(sy.SourceUpdateFrame4086_State)..'|'..word(sy.SourceUpdateFrame4086_Fault))
end,emu.callbackType.exec,BAD,BAD,emu.cpuType.snes,mt)
'''
    offs=struct.unpack_from('<6I',metadata,24)
    values=dict(INDEX=INDEX,CODEBANK=base>>16,CALLBACKBASE=locations['callbacks']&65535,CALLBACKBYTES=len(callbacks),
        FRAMEBYTES=len(frames),BIRTHBASE=locations['births']&65535,BIRTHBYTES=len(births),MODELCOUNT=len(registry['models']),
        MODELBASE=locations['models']&65535,MODELBYTES=len(models),DISPATCHBASE=locations['dispatch']&65535,DISPATCHBYTES=len(dispatch),
        PROGRAMCOUNT=owners['program_count'],CALLSITES=offs[2],ARGS=offs[3],STRINGS=offs[4],INSTRUCTIONS=len(code)//8,
        SLOTS=struct.unpack_from('<H',metadata,10)[0],ANIMATIONID=animation['engine_animation_id'],ACTORID=actor,HANDLE=animation['handle'],
        INIT=fs['CallbackFixture_Init'],RUNENTRY=sy['SourceAnimationCallback4086_Run'],RUNRETURN=fs['CallbackFixture_Run']+4,
        RESULT=fs['CallbackFixture_Result'],BAD=fs['CallbackFixture_Bad'],BEFOREOWNER=fs['CallbackFixture_BeforeOwner'])
    install=''
    if a.effects_runner:
        h=struct.unpack_from('<4s6H4I',plan)
        install="\n".join(" set('"+name+"',"+str(value)+")" for name,value in dict(SourceFrameMotion4086_Ready=0xb4e8,SourceFrameMotion4086_Status=0,SourceFrameEffectLeaf4086_Ready=0xb4f4,SourceSelf4086_Ready=0xb4f6,SourceSelf4086_GlobalLow=0,SourceSelf4086_GlobalHigh=0,SourceSelf4086_Active=0,SourceSelf4086_Fault=0,SourceFrameEffectPlan4086_Ready=0xb4f2,SourceFrameEffectPlan4086_State=0,SourceFrameEffectPlan4086_Service=0,SourceFrameEffectPlan4086_Base=0x8000,SourceFrameEffectPlan4086_Bank=59,SourceFrameEffectPlan4086_Bytes=len(plan),SourceFrameEffectPlan4086_Animations=80,SourceFrameEffectPlan4086_PairedCrcLo=h[-2]&65535,SourceFrameEffectPlan4086_PairedCrcHi=h[-2]>>16,SourceFrameEffectPlan4086_BodyCrcLo=h[-1]&65535,SourceFrameEffectPlan4086_BodyCrcHi=h[-1]>>16,SourceClock4086_Ready=0xb4c5,SourceClock4086_Due=1,SourceClock4086_TimeLo=48,SourceClock4086_TimeHi=0,SourceClock4086_Fault=0).items())
        install+='\n for j=0,511 do emu.write(0x43fb00+j,0,mt)end\n'
        lua+=r'''
emu.addMemoryCallback(function()
 emu.log('CALLBACKFRAME|'..word(INDEX)..'|'..word(sy.SourceUpdateFrame4086_State)..'|'..word(sy.SourceFrameEffectPlan4086_State)..'|'..word(sy.SourceSelf4086_Active)..'|'..word(sy.SourceSelf4086_GlobalLow)..'|'..word(sy.SourceSelf4086_GlobalHigh)..'|'..word(sy.SourceClock4086_Due)..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    lua=lua.replace('INSTALL_EFFECT_RUNNER',install)
    coreinstall=''
    if coretable:
        coreinstall="\n".join(" set('"+name+"',"+str(value)+")" for name,value in dict(SourceModelEntityCopy4086_Ready=0xb4eb,SourceModelEntityCopy4086_Entities=128,SourceModelEntityCopy4086_Models=16,SourceIdle4086_Ready=0xb4f3,SourceRetirement4086_Ready=0xb4f8,SourceRetirement4086_Status=0,SourceBirthCore4086_Ready=0xb4f9,SourceBirthCore4086_Status=0,SourceBirthCore4086_Base=locations['birthcore']&65535,SourceBirthCore4086_Bank=base>>16,SourceBirthCore4086_Bytes=len(coretable),SourceBirthCore4086_Models=16).items())
        coreinstall+='\n for _,r in ipairs({{0x409000,8192,0},{0x40c000,12288,165},{0x43eb00,4096,165},{0x43fd80,32,0}})do for j=0,r[2]-1 do emu.write(r[1]+j,r[3],mt)end end\n put(0x40c048,1,4);put(0x43fd80,1,4);put(0x43fd84,0x414000,4)\n'
        lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local born=c.f==4 and c.fault==0;local bad=0
 for n,r in ipairs({{0x40c060,96},{0x43eb20,32},{0x409040,64}})do
  local base=n==1 and 0 or n==2 and 96 or 128
  for j=0,r[2]-1 do local expected=born and birthcore[base+j+1] or n==3 and 0 or 165;if emu.read(r[1]+j,mt)~=expected then bad=bad+1 end end
 end
 if dw(0x43fd80)~=(born and 2 or 1) or dw(0x43fd84)~=0x414000 or dw(0x40c048)~=1 then bad=bad+1 end
 emu.log('CALLBACKBIRTHCORE|'..word(INDEX)..'|'..bad)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    lua=lua.replace('INSTALL_BIRTH_CORE',coreinstall)
    initialinstall=''
    if a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk:
        initialinstall="\n".join(" set('"+name+"',"+str(value)+")" for name,value in dict(SourceUpdateFrame4086_Animations=len(effects['animations']),SourceModelEntityCopy4086_Ready=0xb4eb,SourceModelEntityCopy4086_Entities=128,SourceModelEntityCopy4086_Models=16,SourceModelAnimationCopy4086_Ready=0xb4e9,SourceModelAnimationCopy4086_Models=16,SourceModelAnimationCopy4086_Maximum=init_report['maximum_animations'],SourceModelAnimationCopy4086_Bytes=len(animation_cache),SourceAnimationInit4086_Ready=0xb4ec,SourceAnimationInit4086_State=0,SourceAnimationInit4086_Base=locations['initializers']&65535,SourceAnimationInit4086_Bank=base>>16,SourceAnimationInit4086_Bytes=len(initializers_table),SourceAnimationInit4086_Handles=len(init_report['animations']),SourceDefaultChoice4086_Ready=0xb4fa,SourceDefaultChoice4086_Status=0,SourceDefaultChoice4086_Slot=0,SourceDefaultChoice4086_Select=1,SourceDefaultChoice4086_TimeLo=48,SourceDefaultChoice4086_TimeHi=0,SourceDefaultChoice4086_Spawn=role_id(config,'spawn'),SourceDefaultChoice4086_Respawn=role_id(config,'respawn'),SourceDefaultChoice4086_Selection=animation['engine_animation_id'],VmSourceWorld_Level=0).items())
        initialinstall+='\n copy(0x43c000,animation_cache);for j=0,12287 do emu.write(0x40c000+j,0,mt)end;put(0x40c048,1,4);put(0x414014,0,4);put(0x416804,0,2)\n'
        lua+=r'''
emu.addMemoryCallback(function()
 emu.log('CALLBACKSELECTINIT|'..word(INDEX)..'|'..word(sy.SourceDefaultChoice4086_Chosen)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.SourceAnimationInit4086_Issued)..'|'..word(0x414014)..'|'..word(0x416804)..'|'..word(sy.SourceUpdateFrame4086_Request))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    if a.initial_jump:
        life=lifecycle_inputs(source)['models'][default]['fields']
        rootcore=birth_core(source)['models'][default]['core']
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceDefaultChoice4086_Select=0,SourceDefaultChoice4086_Selection=role_id(config,'select'),VmSourceWorld_Level=1,SourceLifecycle4086_Ready=0xb4fb,SourceLifecycle4086_Status=2,SourceDefaultPlayer4086_Ready=0xb503,SourceDefaultPlayer4086_Status=0,SourceDefaultPlayer4086_Slot=0,SourceDefaultPlayer4086_Jump=animation['engine_animation_id'],SourceDefaultPlayer4086_TimeLo=48,SourceDefaultPlayer4086_TimeHi=0,SourcePlayerSpawnHeight4086_Ready=0xb505,SourcePlayerSpawnHeight4086_Stage=1,SourcePlayerSpawnHeight4086_Status=0,SourceEnvironment4086_Ready=0xb4d1,SourceEnvironment4086_WallCount=0,SourceEnvironment4086_Stage=1).items())
        initialinstall+='\n for j=0,10239 do emu.write(0x439000+j,0,mt)end;put(0x439038,'+str(life['makeinv'])+',4);put(0x439048,'+str(default)+',2);put(0x43904a,0xb4fb,2);for j=0,3 do put(sy.SourcePlayerSpawnHeight4086_Heights+j*4,300*65536,4)end\n'
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceEmptyInitEnvironment4086_Ready=0xb504,SourceEmptyInitEnvironment4086_Models=len(registry['models']),SourceEmptyInitEnvironment4086_Stage=1,SourceEmptyInitEnvironment4086_Status=0).items())
        initialinstall+='\n put(0x40c000,'+str(rootcore['multiple']&0xffffffff)+',4);put(0x40c004,'+str(rootcore['subject_to_wall']&0xffffffff)+',4);put(0x40c008,'+str(rootcore['subject_to_platform']&0xffffffff)+',4)\n'
        lua+=r'''
emu.addMemoryCallback(function()
 emu.log('CALLBACKJUMP|'..word(INDEX)..'|'..dw(0x41400c)..'|'..dw(0x439000)..'|'..dw(0x439004)..'|'..dw(0x439008)..'|'..dw(0x43900c)..'|'..dw(0x439018)..'|'..dw(0x43901c)..'|'..dw(0x439020)..'|'..dw(0x439024))
 emu.log('CALLBACKTAIL|'..word(INDEX)..'|'..dw(0x40c000)..'|'..word(sy.SourceDefaultPlayer4086_Status)..'|'..word(sy.SourceEmptyInitEnvironment4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    if a.initial_idle:
        rootcore=birth_core(source)['models'][default]['core']
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceDefaultPlayer4086_Ready=0xb503,SourceDefaultPlayer4086_Status=0,SourceDefaultPlayer4086_Slot=0,SourceIdle4086_Ready=0xb4f3,SourceIdle4086_Status=0,SourceEmptyInitEnvironment4086_Ready=0xb504,SourceEmptyInitEnvironment4086_Models=len(registry['models']),SourceEmptyInitEnvironment4086_Stage=1,SourceEmptyInitEnvironment4086_Status=0).items())
        initialinstall+='\n for j=0,4095 do emu.write(0x43eb00+j,0,mt)end;put(0x40b000+'+str(default*160+156)+','+str(birth_core(source)['models'][default]['type'])+',4);put(0x40c058,7,4);put(0x416824,65536,4);put(0x416828,131072,4)\n'
        lua+=r"""
emu.addMemoryCallback(function()
 emu.log('CALLBACKIDLE|'..word(INDEX)..'|'..word(0x43eb00)..'|'..dw(0x40c058)..'|'..dw(0x416824)..'|'..dw(0x416828)..'|'..word(sy.SourceDefaultPlayer4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""
    if a.initial_walk:
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceDefaultPlayer4086_Ready=0xb503,SourceDefaultPlayer4086_Status=0,SourceDefaultPlayer4086_Slot=0,SourceLifecycle4086_Ready=0xb4fb,SourceLifecycle4086_Status=2,SourceAnimationInit4086_Number=walk_capability['default_animation_id']).items())
        initialinstall+='\n for j=0,10239 do emu.write(0x439000+j,0,mt)end;put(0x439048,'+str(default)+',2);put(0x43904a,0xb4fb,2);put(0x43902c,c.direction,4)\n'
        lua+=r"""
emu.addMemoryCallback(function()
 emu.log('CALLBACKWALK|'..word(INDEX)..'|'..dw(0x43902c)..'|'..word(sy.SourceDefaultPlayer4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""
    if a.initial_none_walk:
        import struct as native_struct
        rootcore=model_core_inputs(source)['models'][default]['fields']
        current_speed_q16=project_q16(native_struct.unpack('<I',native_struct.pack('<f',rootcore['speed']))[0])
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(VmSourceWorld_Level=1,SourceEmptyInitEnvironment4086_Ready=0xb504,SourceEmptyInitEnvironment4086_Models=len(registry['models']),SourceEmptyInitEnvironment4086_Stage=1,SourceEmptyInitEnvironment4086_Status=0,SourceEnvironment4086_Ready=0xb4d1,SourceEnvironment4086_WallCount=0,SourceEnvironment4086_Stage=1).items())
        initialinstall+='\n put(0x40c048,0,4);put(0x40c000,'+str(rootcore['multiple']&0xffffffff)+',4);put(0x40c004,'+str(rootcore['subject_to_wall']&0xffffffff)+',4);put(0x40c008,'+str(rootcore['subject_to_platform']&0xffffffff)+',4);put(0x40c014,'+str(rootcore['subject_to_gravity']&0xffffffff)+',4);put(0x40c024,'+str(rootcore['no_adjust_base']&0xffffffff)+',4);put(0x416820,65536,4);put(0x41683c,'+str(current_speed_q16&0xffffffff)+',4)\n'
        lua+=r"""
emu.addMemoryCallback(function()
 emu.log('CALLBACKNONEWALK|'..word(INDEX)..'|'..dw(0x439010)..'|'..dw(0x439000)..'|'..dw(0x416824)..'|'..dw(0x416820)..'|'..dw(0x40c014)..'|'..dw(0x40c024))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""
    if a.initial_enemy:
        from source_actor_numeric import random32_step,INITIAL_SEED
        life=lifecycle_inputs(source)['models'][default]['fields'];rootcore=model_core_inputs(source)['models'][default]['fields']
        if life['subtype']in(1,3):raise ValueError('INITIAL_ENEMY_SUBTYPE')
        speed_bits=struct.unpack('<I',struct.pack('<f',rootcore['speed']))[0];speed_q16=project_q16(speed_bits)
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(VmSourceWorld_Level=1,SourceDefaultChoice4086_Select=0,SourceDefaultChoice4086_Selection=role_id(config,'select'),SourceDefaultPlayer4086_Ready=0xb503,SourceDefaultPlayer4086_Status=0,SourceDefaultPlayer4086_Slot=0,SourceDefaultPlayer4086_Jump=role_id(config,'jump'),SourceLifecycle4086_Ready=0xb4fb,SourceLifecycle4086_Status=2,SourceRandom4086_Ready=0xb4d4,SourceRandom4086_Busy=0,SourceEnvironment4086_Ready=0xb4d1,SourceEnvironment4086_Stage=1,SourceEnvironment4086_WallCount=0,SourceEmptyInitEnvironment4086_Ready=0xb504,SourceEmptyInitEnvironment4086_Models=len(registry['models']),SourceEmptyInitEnvironment4086_Stage=1,SourceEmptyInitEnvironment4086_Status=0).items())
        initialinstall+='\n for j=0,10239 do emu.write(0x439000+j,0,mt)end;put(0x439048,'+str(default)+',2);put(0x43904a,0xb4fb,2);put(0x43904c,0xb508,2);put(0x439044,'+str(int(speed_bits&0x7fffffff!=0))+',4);put(0x439030,'+str(life['subtype']&0xffffffff)+',4);put(0x439034,'+str(life['nomove']&0xffffffff)+',4);put(0x41683c,'+str(speed_q16&0xffffffff)+',4);put(sy.SourceRandom4086_SeedLo,'+str(INITIAL_SEED)+',4);put(sy.SourceRandom4086_CallsLo,0,4);put(0x40c048,2,4);put(0x41400c,0,4);put(0x416830,0,4)\n'
        for off,name in((0,'multiple'),(4,'subject_to_wall'),(8,'subject_to_platform')):initialinstall+=' put(0x40c000+'+str(off)+','+str(rootcore[name]&0xffffffff)+',4)\n'
        seed_after,draw=random32_step(INITIAL_SEED);tableoff=(context_report['table_address']&65535)-0x8000;expected_drop=(240<<16)+int.from_bytes(context_bundle[tableoff+24+(draw%10000)*3:tableoff+27+(draw%10000)*3],'little')
        lua+=r"""
emu.addMemoryCallback(function()
 emu.log('CALLBACKENEMY|'..word(INDEX)..'|'..dw(0x439000)..'|'..dw(0x439004)..'|'..dw(0x439008)..'|'..dw(0x43900c)..'|'..dw(0x41400c)..'|'..dw(sy.SourceRandom4086_SeedLo)..'|'..dw(sy.SourceRandom4086_CallsLo)..'|'..dw(0x41683c)..'|'..dw(0x439044)..'|'..word(0x43904c)..'|'..dw(0x40c000)..'|'..word(sy.SourceDefaultPlayer4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""
    if a.initial_none_model:
        rootcore=model_core_inputs(source)['models'][default]['fields']
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(VmSourceWorld_Level=1,SourceDefaultChoice4086_Select=0,SourceLifecycle4086_Ready=0xb4fb,SourceLifecycle4086_Status=2,SourceEnvironment4086_Ready=0xb4d1,SourceEnvironment4086_Stage=1,SourceEnvironment4086_WallCount=0).items())
        initialinstall+='\n for j=0,10239 do emu.write(0x439000+j,0,mt)end;put(0x439048,'+str(default)+',2);put(0x43904a,0xb4fb,2);put(0x40c048,0,4);put(0x416820,65536,4)\n'
        for off,name in((0,'multiple'),(4,'subject_to_wall'),(8,'subject_to_platform'),(20,'subject_to_gravity'),(36,'no_adjust_base')):initialinstall+=' put(0x40c000+'+str(off)+','+str(rootcore[name]&0xffffffff)+',4)\n'
        lua+=r"""
emu.addMemoryCallback(function()emu.log('DEFAULTNONE|'..word(INDEX)..'|'..dw(0x439010)..'|'..dw(0x416820)..'|'..dw(0x40c014)..'|'..dw(0x40c024)..'|'..dw(0x40c000))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
"""
    if a.default_owner:
        initialinstall+="\n set('SourceDefaultInit4086_Phase',0);set('SourceDefaultPlayer4086_Ready',0xb503);set('SourceDefaultPlayer4086_Status',0)\n"
        lua+="emu.addMemoryCallback(function()emu.log('DEFAULTOWNER|'..word(INDEX)..'|'..word(sy.SourceDefaultInit4086_Phase)..'|'..word(sy.SourceDefaultInit4086_OwnerSlot)..'|'..word(sy.SourceDefaultInit4086_Walk))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.script_clone:
        initialinstall+='\n'+"\n".join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceAnimationCallback4086_Models=16,SourceAnimationCallback4086_Programs=owners['program_count'],SourceScriptClone4086_Ready=0xb5c1,SourceScriptClone4086_Status=0,SourceScriptClone4086_Slot=0,SourceScriptClone4086_Model=default,SourceScriptClone4086_Base=locations['scriptclone']&65535,SourceScriptClone4086_Bank=base>>16,SourceScriptClone4086_Bytes=len(script_clone_table),SourceScriptClone4086_Models=16).items())
        initialinstall+='\n for i=0,63 do emu.write(0x409000+i,0,mt)end;put(0x40902c,1,4);for i=0,1 do local r=0x418800+(8+i)*64;put(r,0x414000+i*80,4);put(r+4,1,2);put(r+6,3,2);put(r+8,1,4);put(r+12,i==0 and 77 or 99,4);for j=0,2 do emu.write(r+16+j,97+i,mt)end end\n'
        lua+="emu.addMemoryCallback(function()emu.log('SCRIPTCLONEOWNER|'..word(INDEX)..'|'..word(sy.SourceScriptClone4086_Status)..'|'..dw(0x40902c)..'|'..dw(0x418a08)..'|'..dw(0x418a0c)..'|'..dw(0x418a4c)..'|'..word(0x418a06))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.ctor_model:
        lua='local ctor_cache={'+','.join(map(str,ctor_cache))+'}\n'+lua
        initialinstall+='\n copy(0x40b000,ctor_cache);for j=0,95 do emu.write(0x40c000+j,165,mt)end;for j=0,79 do emu.write(0x439000+j,165,mt)end\n'
        initialinstall+='\n'+\
            '\n'.join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceLifecycle4086_Ready=0xb4fb,SourceLifecycle4086_Status=0,SourceLifecycle4086_Base=locations['ctorlife']&65535,SourceLifecycle4086_Bank=base>>16,SourceLifecycle4086_Bytes=len(ctor_life),SourceLifecycle4086_Models=16).items())
        lua+="emu.addMemoryCallback(function()emu.log('CTORMODELOWNER|'..word(INDEX)..'|'..word(sy.SourceCtorModel4086_Status)..'|'..dw(0x414024)..'|'..dw(0x414044)..'|'..dw(0x40c04c))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.ctor_factors:
        initialinstall+='\n'+\
            '\n'.join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceFactors4086_Ready=0xb5f1,SourceFactors4086_Status=0,SourceFactors4086_Base=locations['factors']&65535,SourceFactors4086_Bank=base>>16,SourceFactors4086_Bytes=len(factor_table),SourceFactors4086_Models=16,SourceFactors4086_Attacks=factor_report['attack_types']).items())
        lua+="emu.addMemoryCallback(function()local v='';for j=0,31 do v=v..string.format('%02x',emu.read(0x432800+j,mt))end;emu.log('CTORFACTORSOWNER|'..word(INDEX)..'|'..word(sy.SourceFactors4086_Status)..'|'..word(0x43b900)..'|'..word(0x43b902)..'|'..v)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.ctor_state:
        initialinstall+='\n'+\
            '\n'.join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceCtorState4086_Ready=0xb5c2,SourceCtorState4086_Status=0,SourceCtorState4086_Base=locations['ctorstate']&65535,SourceCtorState4086_Bank=base>>16,SourceCtorState4086_Bytes=len(ctor_state_table),SourceCtorState4086_Models=16,SourceCtorState4086_NoHit=0,SourceCtorState4086_SavedMode=0,SourceWorldTick4086_Maximum=0).items())
        initialinstall+="\n put(0x414004,0,4);put(0x43fd80,0,4);put(sy.SourceCtorState4086_X,dw(0x414034),4);put(sy.SourceCtorState4086_Z,dw(0x41403c),4);put(sy.SourceCtorState4086_A,0,4);put(sy.SourceCtorState4086_Direction,c.direction,4);put(sy.SourceCtorState4086_Time,48,4);put(sy.SourceCtorState4086_Player,0,4)\n"
        lua+="emu.addMemoryCallback(function()local name='';for j=0,47 do local ch=emu.read(0x433800+j,mt);if ch==0 then break end;name=name..string.char(ch)end;emu.log('CTORSTATEOWNER|'..word(INDEX)..'|'..word(sy.SourceCtorState4086_Status)..'|'..dw(0x41680c)..'|'..dw(0x416810)..'|'..word(0x41681e)..'|'..word(0x433830)..'|'..word(0x433832)..'|'..name)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.ctor_owner:
        initialinstall+="\n set('SourceTarget4086_OrderReady',0xb4d3);for i=0,127 do put(0x41f200+i*2,i,2)end\n"
        initialinstall+="\n set('SourceCtorOwner4086_Phase',0);set('SourceCtorOwner4086_Model',65535);set('SourceSpawnSlot4086_Ready',0xb5a1);set('SourceSpawnSlot4086_Status',0);set('SourceSpawnSlot4086_Model',"+str(default)+");put(sy.SourceSpawnSlot4086_OverrideLo,999999,4)\n"
        lua+="emu.addMemoryCallback(function()emu.log('CTOROWNER|'..word(INDEX)..'|'..word(sy.SourceCtorOwner4086_Phase)..'|'..word(sy.SourceCtorOwner4086_Model)..'|'..word(sy.SourceSpawnSlot4086_Slot)..'|'..word(sy.SourceSpawnSlot4086_NeedKill))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
        address=fs['CallbackFixture_ResultPublished']
        lua+=f"emu.addMemoryCallback(function()emu.log('CTORPUBLISHED|'..word(INDEX)..'|'..word(sy.VmNativeVariant_Result)..'|'..word(sy.VmNativeVariant_Result+2)..'|'..dw(sy.VmNativeVariant_Result+4))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    lua=lua.replace('INSTALL_INITIAL_SELECT',initialinstall)
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    for label in ('Vm_SourceCallbackScan','Vm_SourceCallbackPoll__save','Vm_SourceCallbackPoll__ok',
                  'SourceAnimationCallback4086_Prepare','SourceAnimationCallback4086_Prepare__copy',
                  'Vm_SourceFrameGate','SourceAnimationCallback4086_Run__span',
                  'SourceAnimationCallback4086_Close'):
        if label.endswith('__copy'):continue
        lua+=f'''emu.addMemoryCallback(function()
 local state=emu.getState()
 emu.log('CALLBACKSEGMENT|{label}|'..word({INDEX})..'|'..(state.masterClock-owner_start))
end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)
'''
    if a.initial_enemy:
        for label in ('SourceDefaultEnemy4086_PrepareNormal','SourceDefaultEnemy4086_ResolveSpawn','SourceDefaultEnemy4086_SpawnResolved','SourceDefaultEnemy4086_RespawnResolved','SourceDefaultEnemy4086_Done','SourceDefaultEnemy4086_BeginHorizontalDrop','SourceDefaultInit4086_BeginIdle','SourceDefaultPlayer4086_Bad','SourceAnimationInit4086_ResolveBad'):
            lua+=f"emu.addMemoryCallback(function() emu.log('ENEMYSEG|{label}|'..emu.getState()['cpu.a']..'|'..word(sy.SourceDefaultPlayer4086_Status)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.SourceAnimationInit4086_Handle)..'|'..word(sy.SourceAnimationInit4086_Count)) end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)\n"
    script=folder/'callback_owner.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-ANIMATION-CALLBACK-OWNER',kind='GATE')
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold callback owner disabled',startup.u16(m,sy['SourceAnimationCallback4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('CALLBACK_OWNER_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(REQUEST,0xb4e7)
        for _ in range(24):
            run_frames_exact(m,60)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native authored callback batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];faults=[];costs=[];initializers=[];frame_results=[];core_results=[];select_results=[];jump_results=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('CALLBACKOWNER|',results),('CALLBACKBAD|',faults),('CALLBACKCOST|',costs),('CALLBACKINIT|',initializers),('CALLBACKFRAME|',frame_results),('CALLBACKBIRTHCORE|',core_results),('CALLBACKSELECTINIT|',select_results),('CALLBACKJUMP|',jump_results)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    expected=[]
    for i,c in enumerate(rows):
        born=c['f']==4 and not c['fault']
        expected.append([i,4 if c['fault'] else 3,5 if c['fault'] else 4,0,0,1 if c['fault'] else 0,2 if born else 1,93*65536 if born else 0,
            (80+(18 if c['direction'] else -18))*65536 if born else 0,220*65536 if born else 0,
            None,0,0,breath if born else 0,48 if born else 0])
    reporter.check('source birth position and cleared shared callback boundary',len(results)==len(expected) and
        all(all(e is None or g==e for g,e in zip(got,want)) and len(got)==len(want) for got,want in zip(results,expected)))
    reporter.check('foreground callback entry preserves CPU context',bool(results) and all(((a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk) or r[10]>=1) and r[11]==0 for r in results))
    reporter.check('nonempty initializer copy is exact and metadata stays immutable',len(initializers)==len(rows) and
        all(r[1]==0 for r in initializers) and ((a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk) or sum(r[2] for r in initializers)>=4))
    if a.effects_runner:
        expected_frame=[[i,1,0,1,0x4000,0x41,1,48,1] if c['fault'] else [i,2,2,0,0,0,0,49,0] for i,c in enumerate(rows)]
        reporter.check('actual callback birth followed by native captured effect retirement and clock',frame_results==expected_frame)
    if coretable:reporter.check('authored callback publishes exact native birth core and preserves parent role/type',core_results==[[i,0] for i in range(len(rows))])
    if a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk:reporter.check('authored '+(enemy_role.upper()if a.initial_enemy else'JUMP'if a.initial_jump else'IDLE'if a.initial_idle else'WALK'if a.initial_walk else'SELECT')+' initialization completes actual frame-zero before clock retirement',len(select_results)==len(rows)and all(r[0]==i and (a.initial_enemy or a.initial_idle or a.initial_walk or r[1]==(65535 if a.initial_jump else animation['engine_animation_id']))and r[2:]==[2,1,animation['engine_animation_id'],animation['handle'],0]for i,r in enumerate(select_results)))
    if a.initial_jump:reporter.check('real JUMP frame zero and post-callback source makeinv fields',jump_results==[[i,300*65536,2,1,3,5,1,1,848,1]for i in range(len(rows))])
    tail_results=[list(map(int,line.split('CALLBACKTAIL|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKTAIL|'in line]
    if a.initial_jump:reporter.check('source current-model tail after JUMP and before clock retirement',tail_results==[[i,max(0,rootcore['multiple']),2,2 if rootcore['subject_to_wall']>0 or rootcore['subject_to_platform']>0 else 0]for i in range(len(rows))])
    idle_results=[list(map(int,line.split('CALLBACKIDLE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKIDLE|'in line]
    if a.initial_idle:
        cached_none=model_core_inputs(source)['models'][default]['fields']['type']==0
        reporter.check('generic set_idle flags and cached-type movement plus authored idle frame zero',idle_results==[[i,3,0,65536 if cached_none and not a.ctor_state else 0,131072 if cached_none and not a.ctor_state else 0,2]for i in range(len(rows))])
    walk_results=[list(map(int,line.split('CALLBACKWALK|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKWALK|'in line]
    if a.initial_walk:reporter.check('source default walk mode retained through real authored frame zero',walk_results==[[i,0 if a.ctor_model else c['direction'],2]for i,c in enumerate(rows)])
    none_walk_results=[list(map(int,line.split('CALLBACKNONEWALK|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKNONEWALK|'in line]
    if a.initial_none_walk:reporter.check('authored TYPE_NONE walk setup retained through real frame-zero and final tail',none_walk_results==[[i,1,15,(current_speed_q16 if c['direction']==1 else-current_speed_q16)&0xffffffff,65536,max(1,rootcore['subject_to_gravity'])if rootcore['subject_to_gravity']<0 else rootcore['subject_to_gravity'],1 if rootcore['no_adjust_base']<0 else rootcore['no_adjust_base']]for i,c in enumerate(rows)])
    enemy_results=[list(map(int,line.split('CALLBACKENEMY|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKENEMY|'in line]
    if a.initial_enemy:
        speed_expected=0 if life['nomove']else speed_q16 if speed_bits&0x7fffffff else 65536
        multiple=max(0,rootcore['multiple']or 5)
        reporter.check('authored normal enemy frame zero, default callbacks, source drop RNG and final current-model tail',enemy_results==[[i,6,10,9,5 if enemy_role=='idle'else 4,expected_drop if enemy_role=='idle'else 0,seed_after if enemy_role=='idle'else INITIAL_SEED,1 if enemy_role=='idle'else 0,speed_expected&0xffffffff,int(speed_expected!=0),0xb508,multiple,2]for i in range(len(rows))])
    owner_results=[list(map(int,line.split('DEFAULTOWNER|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'DEFAULTOWNER|'in line]
    if a.default_owner:reporter.check('generic default-init continuation completes before source clock retirement',owner_results==[[i,6,0,role_id(config,'walk')]for i in range(len(rows))])
    no_walk_results=[list(map(int,line.split('DEFAULTNONE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'DEFAULTNONE|'in line]
    if a.initial_none_model:reporter.check('authored TYPE_NONE no-WALK defaults retained after real IDLE frame zero',no_walk_results==[[i,1,131072,1 if rootcore['subject_to_gravity']<0 else rootcore['subject_to_gravity'],1 if rootcore['no_adjust_base']<0 else rootcore['no_adjust_base'],max(0,rootcore['multiple'])]for i in range(len(rows))])
    clone_results=[list(map(int,line.split('SCRIPTCLONEOWNER|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'SCRIPTCLONEOWNER|'in line]
    if a.ctor_model:
        ctor_results=[list(map(int,line.split('CTORMODELOWNER|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTORMODELOWNER|'in line]
        cm=model_core_inputs(source)['models'][default]['fields']
        reporter.check('current cached model fields installed before actual authored initialization',ctor_results==[[i,2,cm['health']&0xffffffff,cm['health']&0xffffffff,cm['mp']&0xffffffff]for i in range(len(rows))])
    if a.ctor_factors:
        factor_results=[line.split('CTORFACTORSOWNER|',1)[1].strip().split('|')for line in (folder/'mesen.log').read_text().splitlines()if 'CTORFACTORSOWNER|'in line]
        reporter.check('independent source defense/offense snapshot retained through actual authored initialization',factor_results==[[str(i),'2',str(default),str(0xb5f1),factor_report['models'][default]['vector_hex']]for i in range(len(rows))])
    if a.ctor_state:
        state_results=[line.split('CTORSTATEOWNER|',1)[1].strip().split('|')for line in (folder/'mesen.log').read_text().splitlines()if 'CTORSTATEOWNER|'in line]
        cs=ctor_state_report['models'][default]
        reporter.check('source constructor body reset/name/time/lifespan/map and alpha identity retained through real authored initialization',state_results==[[str(i),'2','48',str(cs['lifespan']&0xffffffff),str(cs['alpha']),'0',str(default),cs['display_name']]for i in range(len(rows))])
    if a.ctor_owner:
        ctor_owner_results=[list(map(int,line.split('CTOROWNER|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTOROWNER|'in line]
        reporter.check('generic source constructor slot/cleanup/factors/body and real default-init continuation completes before clock retirement',ctor_owner_results==[[i,2,default,0,0]for i in range(len(rows))])
        published=[list(map(int,line.split('CTORPUBLISHED|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTORPUBLISHED|'in line]
        reporter.check('actual completed constructor publishes the stable source pointer variant',published==[[i,5,0,0x414000]for i in range(len(rows))])
    if a.script_clone:reporter.check('constructor script cleanup/binding survives actual authored frame zero with foreign instance intact',clone_results==[[i,2,script_clone_report['models'][default]['initialized_mask'],0,0,99,3]for i in range(len(rows))])
    r=dict(schema='BYOR_NATIVE_ANIMATION_CALLBACK_OWNER_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(raw).hexdigest(),source_pak_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        owner_table_sha256=hashlib.sha256(callbacks).hexdigest(),cases=rows,results=results,expected=expected,faults=faults,
        source_frame_handle=animation['handle'],script_programs=owners['program_count'],
        callback_cpu_costs=costs,cost_scope='Before native callback Begin through callback completion/fault and instrumented frame-service acknowledgement; includes intervening NMI/runtime, excludes debugger initialization',
        initializer_copy_checks=initializers,
        remaining_effect_service_instrumented=not a.effects_runner,native_effect_runner=a.effects_runner,sound_service_instrumented=a.effects_runner,frame_results=frame_results,player_initialization_bound=False,source_effect_presentation_proven=False,
        combat_proven=False,motu_gameplay_proven=False,no_pcm_copies=True,no_color_reduction=True)
    r.update(native_birth_core=a.birth_core,birth_core_results=core_results)
    r.update(initial_select=a.initial_select,initial_select_results=select_results,initial_jump=a.initial_jump,initial_jump_results=jump_results)
    r.update(empty_environment_tail_bound=a.initial_jump or a.initial_idle,tail_results=tail_results,initial_idle=a.initial_idle,initial_idle_results=idle_results)
    r.update(default_idle_registry_capability=idle_capability,default_walk_registry_capability=walk_capability,initial_walk=a.initial_walk,initial_walk_results=walk_results,initial_none_walk=a.initial_none_walk,initial_none_walk_results=none_walk_results)
    r.update(initial_none_model=a.initial_none_model,initial_none_model_results=no_walk_results)
    r.update(ctor_owner_bound=a.ctor_owner,ctor_state_bound=a.ctor_state,ctor_factors_bound=a.ctor_factors,ctor_model_bound=a.ctor_model,ctor_media_bindings_bound=False,script_clone_bound=a.script_clone,script_clone_results=clone_results,script_clone_table_sha256=hashlib.sha256(script_clone_table).hexdigest()if script_clone_table else None)
    r.update(default_owner_bound=a.default_owner,default_owner_results=owner_results)
    r.update(initial_enemy=a.initial_enemy,initial_enemy_role=enemy_role,initial_enemy_results=enemy_results,enemy_drop_context_instrumented=bool(a.initial_enemy),full_default_init_bound=False)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
