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
    p.add_argument('--frame-owner',action='store_true',help='Use the generic native callback/effects owner; requires effects runner; external sound remains instrumented.')
    p.add_argument('--birth-core',action='store_true',help='Execute actual B4BI core/flags/relation birth augmentation.')
    p.add_argument('--initial-select',action='store_true',help='Initialize authored player SELECT through real default-choice/ent_set_anim/frame-zero owners.')
    p.add_argument('--costmove-model',help='Execute actual costmove and frame-zero owner for this source identity, in an exclusive instrumented payload lease.')
    p.add_argument('--costmove-role',default='freespecial4',help='Authored animation role for the costmove continuation proof.')
    p.add_argument('--source-command',action='store_true',help='Select costmove from actual source command/history; finish clears fresh post-callback playkeys.')
    p.add_argument('--attack-chain-model',help='Execute actual authored player attack chain and frame-zero continuation.')
    p.add_argument('--attack-chain-step',type=int,default=1,help='One-based next authored chain step for the isolated proof.')
    p.add_argument('--attack-chain-post-mutation',action='store_true',help='Instrument state changes after actual callback; prove chain cleanup and timer use fresh fields.')
    p.add_argument('--initial-jump',action='store_true',help='Run real default choice/action/JUMP frame zero and current makeinv fields, isolated.')
    p.add_argument('--ai-run',action='store_true',help='execute actual generic AI dispatcher through common_spawn and real authored idle frame, then absent think script')
    p.add_argument('--common-spawn',action='store_true',help='Execute actual common_spawn idle transition through existing non-idle animation; isolated AI action, no world clock commit')
    p.add_argument('--initial-idle',action='store_true',help='Execute generic missing-animation set_idle and actual authored idle frame zero.')
    p.add_argument('--initial-walk',action='store_true',help='Execute generic default walk selection and actual authored walk frame zero.')
    p.add_argument('--initial-none-walk',action='store_true',help='Prepare authored TYPE_NONE walker from current speed, then execute real walk frame zero.')
    p.add_argument('--initial-enemy',help='Source identity for normal enemy initialization through actual authored frame zero.')
    p.add_argument('--drop-context',type=Path,help='Compiled readonly horizontal drop context bundle.')
    p.add_argument('--default-owner',action='store_true',help='Use generic source-order default-init Begin/Continue instead of direct leaf sequencing.')
    p.add_argument('--initial-none-model',help='Authored TYPE_NONE identity without WALK, through default owner and actual IDLE frame zero.')
    p.add_argument('--ctor-owner',action='store_true',help='Execute slot selection and complete generic constructor continuation instead of fixture leaf sequencing.')
    p.add_argument('--queue-producer',action='store_true',help='Execute actual native queue request and acknowledgement; leave the full world tick uncommitted.')
    p.add_argument('--scroller-owner',action='store_true',help='Resume a terminal authored spawn through the complete scroller owner; no player/camera motion or full world tick claim.')
    p.add_argument('--freeze-state',action='store_true',help='Enable canonical freeze rows and observe actual constructor reset before alive publication.')
    p.add_argument('--ai-state-birth',action='store_true',help='Observe stale AI scalar reset before constructor alive publication and retain the sibling row.')
    p.add_argument('--player-state-birth',action='store_true',help='Execute the checked VM-tail lease and actual constructor state clearing through an opt-in birth bridge.')
    p.add_argument('--run-tuple-birth',action='store_true',help='Capture exact RUN snapshot after actual constructor model-data copy; requires player-state birth bridge.')
    p.add_argument('--ground-walk',action='store_true',help='After actual SELECT construction, run canonical ground movement and real WALK frame-zero services.')
    p.add_argument('--emit-only',action='store_true',help='Emit the private source-derived fixture and observer without launching or certifying it.')
    p.add_argument('--smartspawn',action='store_true',help='Apply source-derived stage properties after the complete constructor; boss music remains an explicit pending service.')
    p.add_argument('--stage-queue-index',type=int,help='Read constructor inputs from an authored stage spawn record; post-constructor overrides remain separate.')
    p.add_argument('--ctor-state',action='store_true',help='Run real reset/setup/model/script body owner before authored default initialization.')
    p.add_argument('--ctor-factors',action='store_true',help='Copy source-derived exact uniform defense/offense factors before model installation.')
    p.add_argument('--ctor-model',action='store_true',help='Install fresh fields from the current shared cached model before script bind.')
    p.add_argument('--script-clone',action='store_true',help='Run real constructor method-1 clear/bind before default initialization.')
    p.add_argument('--physics-state-birth',action='store_true',help='native physics row reset before exists publication; requires complete constructor')
    p.add_argument('--damage-state-birth',action='store_true',help='native exact damage state after source model copy and before constructor script/default callbacks')
    p.add_argument('--damage-effects-state-birth',action='store_true',help='native source projectile/staydown/guard state after fresh model copy')
    p.add_argument('--death-fields-birth',action='store_true',help='copy actual source score/current cached diesound and calloc item before constructor callbacks')
    p.add_argument('--adjust-base-empty',action='store_true',help='execute source empty-world base adjustment through stationary post, using actual current-frame lookup')
    p.add_argument('--stationary-post',action='store_true',help='checked source-derived stationary post-update after complete NONE constructor; phase owner context supplied')
    p.add_argument('--ctor-altitude-q16',type=int,default=0,help='generic explicit constructor altitude input')
    a=p.parse_args();a.initial_walk=a.initial_walk or a.initial_none_walk;folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);source=Source(a.source)
    (folder/'report.json').write_text(json.dumps(dict(schema='BYOR_NATIVE_ANIMATION_CALLBACK_OWNER_V1',status='RUNNING'))+'\n')
    if a.player_state_birth and not(a.ctor_owner and a.ctor_state):raise ValueError('PLAYER_STATE_BIRTH_REQUIRES_ACTUAL_CONSTRUCTOR')
    if a.player_state_birth and(a.costmove_model or a.attack_chain_model):raise ValueError('PLAYER_STATE_BIRTH_FIXTURE_MODE_CONFLICT')
    if a.run_tuple_birth and not(a.player_state_birth and a.ctor_model):raise ValueError('RUN_TUPLE_BIRTH_REQUIRES_MODEL_CONSTRUCTOR_AND_STATE_BRIDGE')
    if a.ground_walk and not(a.run_tuple_birth and a.initial_select and a.frame_owner and a.effects_runner):raise ValueError('GROUND_WALK_REQUIRES_CONSTRUCTOR_RUN_AND_FRAME_OWNERS')
    if a.costmove_model or a.attack_chain_model:
        if not a.frame_owner or not a.effects_runner:raise ValueError('COSTMOVE_REQUIRES_REAL_FRAME_OWNER')
        a.initial_select=True
    if a.attack_chain_model and (a.costmove_model or a.source_command):raise ValueError('ATTACK_CHAIN_FIXTURE_MODE_CONFLICT')
    if a.attack_chain_post_mutation and not a.attack_chain_model:raise ValueError('ATTACK_CHAIN_POST_REQUIRES_CHAIN_MODE')
    if a.attack_chain_model:
        from source_attack_body_profile import derive as derive_chain,pack_runtime as pack_chain
        chain_report=derive_chain(source);chain_table=pack_chain(chain_report)
        chain_model=next(m for m in chain_report['models']if m['identity']==a.attack_chain_model)
        chain_fields=chain_model['fields'];chain_step=a.attack_chain_step
        if not 1<=chain_step<=chain_fields['chainlength']:raise ValueError('ATTACK_CHAIN_FIXTURE_STEP')
        chain_role='attack'+str(chain_fields['atchain'][chain_step-1])
    if a.source_command and not a.costmove_model:raise ValueError('SOURCE_COMMAND_REQUIRES_COSTMOVE_MODEL')
    cost_work=0x7fa000;cost_tail=0x7fa040
    if a.source_command:
        from source_foreign_state_layout import layout
        from source_player_combo_4086 import derive as derive_combos
        controller_layout=layout(0x7fa000,6400)
        controller={r['name']:r['address'] for r in controller_layout['regions']}
        cost_work=controller['costmove_controls'];cost_tail=controller['entity_combo_tail']
        command_report=derive_combos(source)
    if a.common_spawn and (not a.initial_idle or a.default_owner or a.ctor_owner):raise ValueError('COMMON_SPAWN_FIXTURE_REQUIRES_ISOLATED_INITIAL_IDLE')
    if a.ai_run and(not a.common_spawn or not a.script_clone):raise ValueError('AI_RUN_FRAME_REQUIRES_COMMON_SPAWN_SCRIPT_CLONE')
    if a.physics_state_birth and not(a.ctor_owner and a.ctor_state):raise ValueError('PHYSICS_BIRTH_REQUIRES_COMPLETE_CONSTRUCTOR')
    if a.damage_state_birth and not(a.ctor_owner and a.ctor_state):raise ValueError('DAMAGE_BIRTH_REQUIRES_COMPLETE_CONSTRUCTOR')
    if a.damage_effects_state_birth and not(a.ctor_owner and a.ctor_state and a.ctor_model):raise ValueError('DAMAGE_EFFECTS_BIRTH_REQUIRES_COMPLETE_MODEL_CONSTRUCTOR')
    if a.death_fields_birth and not(a.ctor_owner and a.ctor_state and a.ctor_model):raise ValueError('DEATH_FIELDS_BIRTH_REQUIRES_COMPLETE_MODEL_CONSTRUCTOR')
    if a.adjust_base_empty and not(a.stationary_post and a.physics_state_birth):raise ValueError('ADJUST_BASE_EMPTY_REQUIRES_STATIONARY_POST_AND_PHYSICS_STATE')
    if a.stationary_post and not(a.initial_none_model and a.ctor_owner and a.ctor_state and a.ctor_model and a.ctor_factors and a.script_clone and a.freeze_state and a.default_owner):raise ValueError('STATIONARY_POST_REQUIRES_COMPLETE_NONE_SOURCE_CONSTRUCTOR')
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
    if a.costmove_model:default=next(m['id'] for m in registry['models'] if m['identity']==a.costmove_model)
    if a.attack_chain_model:default=chain_model['index']
    stage_row=None;queue_table=b'';stage_queue_report=None
    if a.stage_queue_index is not None:
        from source_stage_queue_4086 import derive as queue_inputs,pack as queue_pack,unpack as queue_unpack
        stage_queue_report=queue_inputs(source);queue_table=queue_pack(stage_queue_report);queue_rows=queue_unpack(queue_table,len(registry['models']))
        if not 0<=a.stage_queue_index<len(queue_rows):raise ValueError('STAGE_QUEUE_FIXTURE_INDEX')
        stage_row=queue_rows[a.stage_queue_index]
        if stage_row['kind']!='spawn'or not a.ctor_owner:raise ValueError('STAGE_QUEUE_FIXTURE_REQUIRES_ACTUAL_SPAWN_CTOR')
        model=registry['models'][stage_row['model']]
        if model['declared_type']!='enemy':raise ValueError('STAGE_QUEUE_FIXTURE_ENEMY_INIT_CAPABILITY')
        a.initial_enemy=model['identity']
    if a.queue_producer and not a.smartspawn:raise ValueError('QUEUE_PRODUCER_REQUIRES_POST_PROPERTIES')
    if a.freeze_state and not a.ctor_owner:raise ValueError('FREEZE_BIRTH_REQUIRES_CTOR_OWNER')
    if a.scroller_owner and not a.queue_producer:raise ValueError('SCROLLER_OWNER_REQUIRES_QUEUE_PRODUCER')
    spawn_caps=None;boss_music_present=False
    if a.smartspawn:
        if stage_row is None:raise ValueError('SMARTSPAWN_REQUIRES_SOURCE_STAGE_ROW')
        from source_spawn_capabilities_4086 import derive as spawn_capabilities
        spawn_caps=spawn_capabilities(source)
        stage_doc=document(source,stage_queue_report['stages'][stage_row['stage_id']-1]['source_path'])
        boss_music_present=any(r['directive']=='bossmusic' and r['values'] and r['values'][0] for r in stage_doc['directives'])
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
    if a.stationary_post:
        from source_stationary_gravity_capability import derive as stationary_capability
        cap=stationary_capability(source)
        if not cap['models'][default]['non_gravitating_hover_requirements']:raise ValueError('SOURCE_NON_GRAVITATING_HOVER_CAPABILITY_REQUIRED')
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
        actor=default;animation=next(h for h in compile_source(source)['animation_handles'] if h['model']==registry['models'][default]['identity'] and h['role']==(chain_role if a.attack_chain_model else a.costmove_role if a.costmove_model else enemy_role if a.initial_enemy else 'jump'if a.initial_jump else'idle'if a.initial_idle else'walk'if a.initial_walk else'select'))
        docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')};structure=discover(source,docs);config=configure(docs[key(structure['models_path'])]['directives'])
        init_report=init_inputs(source);initializers_table=pack_init(init_report);cache=bytearray(16*init_report['maximum_animations']*2)
        for row in init_report['animations']:
            model=next(m['id'] for m in registry['models'] if m['identity']==row['model']);struct.pack_into('<H',cache,(model*init_report['maximum_animations']+row['engine_animation_id'])*2,row['handle'])
        animation_cache=bytes(cache);rows=[dict(f=0,direction=d,default=default,fault=0) for d in (0,1)]
        if a.ground_walk:
            from source_player_run_4086 import KEYS
            rows=[dict(f=0,direction=d,default=default,fault=0,ground_keys=mask)for d in (0,1)
                  for mask in (KEYS['moveleft']if d==0 else KEYS['moveright'],KEYS['moveup'],KEYS['movedown'],
                               (KEYS['moveleft']if d==0 else KEYS['moveright'])|KEYS['moveup'])]
    if a.common_spawn:
        previous_animation=next(h for h in compile_source(source)['animation_handles']if h['model']==registry['models'][default]['identity'] and h['role']!='idle')
    sy=symbols(Path('src/main.sym'));raw=bytearray(a.rom.read_bytes());entry=sy['Vm_SourceFrameGate']
    if a.player_state_birth:
        from source_foreign_slot_tail import derive_plan
        from source_player_state_native import emit as emit_player_state,emit_birth_bridge
        from source_foreign_state_layout import layout as state_layout
        player_state_plan=derive_plan(source)
        player_state_work=next(r['address']for r in state_layout(0x7fa000,6400)['regions']if r['name']=='player_state_controls')
        if a.run_tuple_birth:
            from source_run_tuple_profile import derive as derive_run_tuples
            from source_run_tuple_native import emit as emit_run_tuples,emit_ctor_model_bridge
            run_tuple_report=derive_run_tuples(source)
            run_regions={r['name']:r['address']for r in state_layout(0x7fa000,6400)['regions']}
            run_work=run_regions['run_tuple_controls'];run_handles=run_regions['entity_run_tuple']
    physics_table=b''
    if a.adjust_base_empty:
        from source_animation_physics_4086 import derive as physics_inputs,pack as pack_physics
        physics_table=pack_physics(physics_inputs(source))
        if a.drop_context or raw[58*32768:59*32768]!=bytes(32768):raise ValueError('ADJUST_BASE_PRIVATE_PHYSICS_BANK_OWNERSHIP')
        raw[58*32768:58*32768+len(physics_table)]=physics_table
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
    if a.damage_effects_state_birth:
        from source_damage_inputs_4086 import derive as damage_inputs,pack as pack_damage_inputs,unpack as unpack_damage_inputs
        damage_inputs_report=damage_inputs(source);damage_inputs_table=pack_damage_inputs(damage_inputs_report);unpack_damage_inputs(damage_inputs_table)
        locations['damageinputs']=base+cursor;raw[at+cursor:at+cursor+len(damage_inputs_table)]=damage_inputs_table;cursor+=len(damage_inputs_table)
    if a.death_fields_birth:
        from source_death_fields_4086 import derive as death_inputs,pack as pack_death
        from source_sound_namespace_4086 import derive as sound_inputs
        death_report=death_inputs(source);death_table=pack_death(death_report);locations['deathfields']=base+cursor;raw[at+cursor:at+cursor+len(death_table)]=death_table;cursor+=len(death_table)
        sounds=sound_inputs(source)
        for m in sounds['models']:
            binding=m['bindings'].get('diesound')
            if binding is not None:struct.pack_into('<i',ctor_cache,m['id']*160+76,binding['sound_index'])
    if cursor>32768:raise ValueError('CALLBACK_NATIVE_IMMUTABLE_BANK_CAPACITY')
    raw[60*32768:60*32768+len(frames)]=frames
    if a.effects_runner:
        if raw[59*32768:60*32768]!=bytes(32768):raise ValueError('CALLBACK_PLAN_PRIVATE_BANK')
        raw[59*32768:59*32768+len(plan)]=plan
    if a.costmove_model:
        from source_animation_energy_4086 import derive as derive_energy,pack as pack_energy
        cost_energy=derive_energy(source);cost_energy_table=pack_energy(cost_energy)
        if raw[58*32768:59*32768]!=bytes(32768):raise ValueError('COSTMOVE_ENERGY_ROM_RESERVATION')
        raw[58*32768:58*32768+len(cost_energy_table)]=cost_energy_table
    if a.attack_chain_model:
        if raw[58*32768:59*32768]!=bytes(32768):raise ValueError('ATTACK_CHAIN_ROM_RESERVATION')
        raw[58*32768:58*32768+len(chain_table)]=chain_table
    if queue_table:
        if len(plan)+len(queue_table)>32768:raise ValueError('STAGE_QUEUE_PRIVATE_ROM_CAPACITY')
        locations['stagequeue']=(59<<16)+0x8000+len(plan)
        raw[59*32768+len(plan):59*32768+len(plan)+len(queue_table)]=queue_table
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
    if a.frame_owner:
        if not a.effects_runner:raise ValueError('FRAME_OWNER_REQUIRES_EFFECTS_RUNNER')
        begin=asm.index(' jsl CALLBACKBEGIN');end=asm.index('CallbackFixture_Effects:',begin)
        asm=asm[:begin]+'''CallbackFixture_Run:
.a16
.i16
 jsl FRAMEOWNER
 bcs CallbackFixture_ExpectedFault
 cmp #$8001
 beq CallbackFixture_Run
CallbackFixture_AfterScript:
.a16
.i16
 nop
 cmp #0
 beq CallbackFixture_EffectsDone
 cmp #9
 beq CallbackFixture_AudioService
 jmp CallbackFixture_Bad
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
    if a.costmove_model:
        from source_costmove_native import emit as emit_costmove
        begin_name='SourceCombo_Begin' if a.source_command else 'SourceCostMove_Begin'
        finish_name='SourceCombo_Finish' if a.source_command else 'SourceCostMove_Finish'
        asm=asm.replace(' jsl DEFAULTBEGIN\n bcs CallbackFixture_Bad\n jsl STARTFRAME',f' jsl {begin_name}\n bcs CallbackFixture_Bad\n lda.l {cost_work+2}\n cmp #3\n bne CallbackFixture_Bad\n jsl STARTFRAME')
        asm=asm.replace(' jsl INITACK\n bcs CallbackFixture_Bad',f' jsl INITACK\n bcs CallbackFixture_Bad\n jsl {finish_name}\n bcs CallbackFixture_Bad')
        asm+=emit_costmove(cost_work,cost_tail,sy)
        if a.source_command:
            from source_costmove_native import emit_combo_energy_query
            from source_player_input_native import emit as emit_history
            from source_player_combo_native import emit as emit_command
            asm+=emit_history(controller['input_history'],controller['input_scratch'],controller['input_snapshot'],controller['combo_sequence'],controller['input_owner'],0xb674)
            asm+=emit_combo_energy_query(cost_work,sy)
            asm+=emit_command(command_report,controller['combo_controls'],cost_work,controller['input_history'],controller['combo_sequence'],controller['input_owner'],0xb674,sy)
    if a.attack_chain_model:
        from source_attack_chain_native import emit as emit_chain
        asm=asm.replace(' jsl DEFAULTBEGIN\n bcs CallbackFixture_Bad\n jsl STARTFRAME',' jsl SourceAttackChain_Begin\n bcs CallbackFixture_Bad\n lda.l $7FA002\n cmp #4\n bne CallbackFixture_Bad\n jsl STARTFRAME')
        asm=asm.replace(' jsl INITACK\n bcs CallbackFixture_Bad',' jsl INITACK\n bcs CallbackFixture_Bad\n jsl SourceAttackChain_Finish\n bcs CallbackFixture_Bad')
        asm+=emit_chain(0x7fa000,0x7fa100,config['arrays']['normal_attacks'],sy)
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
        if not(a.default_owner or a.ai_run):raise ValueError('SCRIPT_CLONE_REQUIRES_DEFAULT_OR_AI_OWNER_FIXTURE')
        asm=asm.replace('CallbackFixture_Init:\n.a16\n.i16\n nop','CallbackFixture_Init:\n.a16\n.i16\n nop\n jsl SCRIPTCLONECLEAR\n bcs CallbackFixture_Bad\n jsl SCRIPTCLONEBIND\n bcs CallbackFixture_Bad')
    if a.ctor_model:asm=asm.replace(' jsl SCRIPTCLONEBIND',' jsl CTORMODEL\n bcs CallbackFixture_Bad\n jsl SCRIPTCLONEBIND')
    if a.ctor_factors:asm=asm.replace(' jsl CTORMODEL',' jsl CTORFACTORS\n bcs CallbackFixture_Bad\n jsl CTORMODEL')
    if a.ctor_state:asm=asm.replace(' jsl CTORMODEL\n bcs CallbackFixture_Bad\n jsl SCRIPTCLONEBIND', ' jsl CTORSTATE')
    if a.ctor_owner:
        if not a.ctor_state:raise ValueError('CTOR_OWNER_REQUIRES_CTOR_STATE')
        asm=asm.replace(' jsl SCRIPTCLONECLEAR\n bcs CallbackFixture_Bad\n jsl CTORFACTORS\n bcs CallbackFixture_Bad\n jsl CTORSTATE\n bcs CallbackFixture_Bad','')
        asm=asm.replace(' jsl OWNERBEGIN',' jsl CTOROWNERBEGIN').replace(' jsl OWNERCONTINUE',' jsl CTOROWNERCONTINUE')
        asm=asm.replace('CallbackFixture_Result:\n.a16\n.i16\n nop','CallbackFixture_Result:\n.a16\n.i16\n nop\n jsl CTORRESULT\n bcs CallbackFixture_Bad\nCallbackFixture_ResultPublished:\n.a16\n.i16\n nop')
        if stage_row:
            needle=' lda #'+str(role_id(config,'walk'))+'\n ldx #$8000\n ldy #58\n jsl CTOROWNERBEGIN'
            if needle not in asm:raise ValueError('STAGE_QUEUE_CONSTRUCTOR_GATE')
            asm=asm.replace(needle,' jsl STAGEPREPARE\n bcs CallbackFixture_Bad\n'+needle)
            context_base=0x8000+32*(stage_row['stage_id']-1)
            asm=asm.replace(' ldx #$8000\n ldy #58',f' ldx #{context_base}\n ldy #58')
    if a.stationary_post:
        asm=asm.replace('CallbackFixture_ResultPublished:\n.a16\n.i16\n nop','CallbackFixture_ResultPublished:\n.a16\n.i16\n nop\nCallbackFixture_PostBefore:\n.a16\n.i16\n nop\n jsl POSTSTATIONARY\n bcs CallbackFixture_Bad\nCallbackFixture_PostAfter:\n.a16\n.i16\n nop')
    if a.smartspawn:
        asm=asm.replace('CallbackFixture_ResultPublished:\n.a16\n.i16\n nop','CallbackFixture_ResultPublished:\n.a16\n.i16\n nop\n jsl SMARTSPAWN\n bcs CallbackFixture_Bad\nCallbackFixture_PropertiesPublished:\n.a16\n.i16\n nop')
    if a.queue_producer:
        asm=asm.replace(' jsl STAGEPREPARE\n bcs CallbackFixture_Bad',' jsl QUEUENEXT\n bcs CallbackFixture_Bad\n cmp #1\n bne CallbackFixture_Bad')
        asm=asm.replace('CallbackFixture_PropertiesPublished:\n.a16\n.i16\n nop','CallbackFixture_PropertiesPublished:\n.a16\n.i16\n nop\n lda.l MUSICSTATUS\n cmp #1\n bne CallbackFixture_QueueAck\nCallbackFixture_InstrumentMusicService:\n.a16\n.i16\n nop\n jsl MUSICACK\n bcs CallbackFixture_Bad\nCallbackFixture_QueueAck:\n.a16\n.i16\n jsl QUEUEACK\n bcs CallbackFixture_Bad\nCallbackFixture_QueuePublished:\n.a16\n.i16\n nop')
        asm=asm.replace(' jsl CLOCKCOMMIT',' clc ; full queue/world tick intentionally remains uncommitted')
    if a.common_spawn:
        asm=asm.replace(' jsl IDLEBEGIN',' jsl COMMONBEGIN')
        asm=asm.replace(' jsl INITACK',' jsl COMMONCONTINUE')
        asm=asm.replace(' jsl DEFAULTTAIL\n bcs CallbackFixture_Bad\n','')
        asm=asm.replace(' jsl CLOCKCOMMIT\n bcs CallbackFixture_Bad\n',' nop\n')
    if a.ai_run:
        asm=asm.replace(' jsl COMMONBEGIN',' jsl AIRUNBEGIN').replace(' jsl COMMONCONTINUE',' jsl AIRUNCONTINUE')
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,FRAMEBEGIN=sy['SourceUpdateFrame4086_Begin'],
        FRAMEACK=sy['SourceUpdateFrame4086_Ack'],CALLBACKBEGIN=sy['SourceAnimationCallback4086_Begin'],
        CALLBACKRUN=sy['SourceAnimationCallback4086_Run'],CALLBACKREADY=sy['SourceAnimationCallback4086_Ready'],
        FRAMEREADY=sy['SourceUpdateFrame4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],
        CONTEXTVALID=sy['VmNativeVariant_ContextValid'],RESUME=entry+5,CASES=len(rows))
    values.update(EXPECTFAULT=0x7ffb86,CHECKIDLE=sy['SourceUpdateFrame4086_CheckIdle'],CLOCKCOMMIT=sy['SourceClock4086_Commit'])
    if a.effects_runner:values.update(EFFECTRUN=sy['SourceFrameEffects4086_Run'],EFFECTACK=sy['SourceFrameEffectPlan4086_Ack'],EFFECTACKWORD=sy['SourceFrameEffectPlan4086_Acknowledged'])
    if a.frame_owner:values['FRAMEOWNER']=sy['SourceFrameOwner4086_Run']
    if a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk:values.update(DEFAULTBEGIN=sy['SourceDefaultChoice4086_Begin'],STARTFRAME=sy['SourceAnimationInit4086_StartFrame'],INITACK=sy['SourceAnimationInit4086_Ack'])
    if a.initial_jump:values.update(DEFAULTPREPARE=sy['SourceDefaultChoice4086_Prepare'],PLAYERBEGIN=sy['SourceDefaultPlayer4086_BeginAction'],PLAYERINV=sy['SourceDefaultPlayer4086_ApplyInvincibility'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.ai_run:values.update(AIRUNBEGIN=sy['SourceAIRun4086_Begin'],AIRUNCONTINUE=sy['SourceAIRun4086_Continue'])
    if a.common_spawn:values.update(COMMONBEGIN=sy['SourceCommonSpawn4086_Begin'],COMMONCONTINUE=sy['SourceCommonSpawn4086_Continue'])
    if a.initial_idle:values.update(IDLEBEGIN=sy['SourceDefaultInit4086_BeginIdle'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.initial_walk:values.update(WALKBEGIN=sy['SourceWalk4086_BeginDefaultOnly'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.initial_none_walk:values.update(NONEWALKPREP=sy['SourceDefaultNone4086_PrepareWalk'])
    if a.initial_enemy:values.update(ENEMYPREP=sy['SourceDefaultEnemy4086_PrepareNormal'],ENEMYDROP=sy['SourceDefaultEnemy4086_BeginHorizontalDrop'],DEFAULTTAIL=sy['SourceDefaultInit4086_FinalizeEmpty'])
    if a.default_owner:values.update(OWNERBEGIN=sy['SourceDefaultInit4086_Begin'],OWNERCONTINUE=sy['SourceDefaultInit4086_Continue'])
    if a.script_clone:values.update(SCRIPTCLONECLEAR=sy['SourceScriptClone4086_Clear'],SCRIPTCLONEBIND=sy['SourceScriptClone4086_Bind'])
    if a.stationary_post:values['POSTSTATIONARY']=sy['SourcePostStationary4086_Execute']
    if a.ctor_owner:values.update(CTOROWNERBEGIN=sy['SourceCtorOwner4086_Begin'],CTOROWNERCONTINUE=sy['SourceCtorOwner4086_Continue'],CTORRESULT=sy['SourceCtorOwner4086_Result'])
    if a.queue_producer:values.update(QUEUENEXT=sy['SourceStageProducer4086_Next'],QUEUEACK=sy['SourceStageProducer4086_AckSpawn'],MUSICSTATUS=sy['SourceSmartSpawn4086_Status'],MUSICACK=sy['SourceSmartSpawn4086_AckMusic'])
    if a.scroller_owner:values.update(QUEUENEXT=sy['SourceScrollerOwner4086_Begin'],QUEUEACK=sy['SourceScrollerOwner4086_Continue'])
    if a.smartspawn:values['SMARTSPAWN']=sy['SourceSmartSpawn4086_Apply']
    if stage_row:values['STAGEPREPARE']=sy['SourceStageQueue4086_PrepareSpawn']
    if a.ctor_state:values.update(CTORSTATE=sy['SourceCtorState4086_Begin'])
    if a.ctor_factors:values.update(CTORFACTORS=sy['SourceFactors4086_Apply'])
    if a.ctor_model:values.update(CTORMODEL=sy['SourceCtorModel4086_Apply'])
    if a.player_state_birth:
        asm=asm.replace('CallbackFixture_Init:\n.a16\n.i16\n nop',
                        'CallbackFixture_Init:\n.a16\n.i16\n nop\n jsl SourcePlayerState_Init\n bcs CallbackFixture_Bad\nCallbackFixture_PlayerStatePoison:\n.a16\n.i16\n nop')
        asm+=emit_player_state(player_state_plan,player_state_work,sy)+emit_birth_bridge(player_state_work,sy)
        if a.run_tuple_birth:
            asm+=emit_run_tuples(run_work,run_handles,run_tuple_report,sy)+emit_ctor_model_bridge(run_work,sy)
    if a.ground_walk:
        from source_player_ground_native import emit as emit_ground
        from source_player_ground_binding import emit as emit_ground_binding
        from source_find_here_empty_native import emit as emit_empty
        from source_player_ground_services import emit as emit_ground_services
        gr=run_regions;g=gr['ground_controls'];b=gr['ground_binding_controls'];e=gr['find_here_empty_controls']
        # This serialized proof control is an explicit private lease, not a root allocation.
        service_work=gr['ground_services_controls']
        asm+=emit_ground(g)+emit_ground_binding(b,g,player_state_work,run_work,run_handles,model_core_inputs(source)['models'],run_tuple_report,sy)
        asm+=emit_empty(e,sy)+emit_ground_services(service_work,g,b,e,config,sy)
        needle='CallbackFixture_ResultPublished:\n.a16\n.i16\n nop'
        if needle not in asm:raise ValueError('GROUND_WALK_CONSTRUCTOR_RESULT_GATE')
        asm=asm.replace(needle,needle+'''
CallbackFixture_GroundPrepare:
.a16
.i16
 nop
 jsl GroundServices_Begin
 bcs CallbackFixture_Bad
CallbackFixture_GroundDispatch:
.a16
.i16
 cmp #0
 beq CallbackFixture_GroundDone
 cmp #1
 bne CallbackFixture_Bad
 jsl STARTFRAME
 bcs CallbackFixture_Bad
CallbackFixture_GroundFrame:
.a16
.i16
 jsl FRAMEOWNER
 bcs CallbackFixture_Bad
 cmp #$8001
 beq CallbackFixture_GroundFrame
 cmp #0
 bne CallbackFixture_Bad
 jsl GroundServices_FinishFrame
 bcs CallbackFixture_Bad
 jmp CallbackFixture_GroundDispatch
CallbackFixture_GroundDone:
.a16
.i16
 nop
''')
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
    if a.player_state_birth:
        bridge_at=offset(sy['SourceAIState4086_InitializeBirth'])
        if raw[bridge_at:bridge_at+5]!=bytes.fromhex('08 c2 38 da 5a'):raise ValueError('PLAYER_STATE_BIRTH_PROLOGUE')
        raw[bridge_at:bridge_at+5]=b'\x5c'+struct.pack('<I',fs['SourcePlayerState_BirthBridge'])[:3]+b'\xea'
        if a.run_tuple_birth:
            run_bridge_at=offset(sy['SourceCtorModel4086_Apply'])
            if raw[run_bridge_at:run_bridge_at+5]!=bytes.fromhex('08 c2 38 da 5a'):raise ValueError('RUN_TUPLE_CTOR_MODEL_PROLOGUE')
            raw[run_bridge_at:run_bridge_at+5]=b'\x5c'+struct.pack('<I',fs['SourceRunTuple_CtorModelBridge'])[:3]+b'\xea'
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['CallbackFixture_Gate'])[:3]+b'\xea'
    path=folder/'bor.sfc';path.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*(a.rom.parent.glob('bor-*.pcm') if not(a.costmove_model or a.attack_chain_model or a.player_state_birth) else ())]:
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
 set('SourceFreeze4086_Ready',FREEZESTATE)
 if FREEZESTATE~=0 then for j=0,79 do put(0x42e000+j,0xff,1)end;put(0x41f300,0xffffffff,4)end
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
 set('SourcePhysicsState4086_Ready',0)
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
    if a.frame_owner:
        values['RUNRETURN']=sy['SourceFrameOwner4086_AfterCallback']
        lua+=r'''
emu.addMemoryCallback(function(address,value)
 local s=emu.getState()
 if word(INDEX)<8 then emu.log('FRAMECTXWRITE|'..word(INDEX)..'|'..address..'|'..value..'|'..tostring(s['cpu.pc'])..'|'..tostring(s['cpu.k']))end
end,emu.callbackType.write,sy.VmNativeVariant_ContextValid,sy.VmNativeVariant_ContextValid+1,emu.cpuType.snes,mt)
'''
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
        if a.attack_chain_model:
            initialinstall+='\n for j=0,607 do put(0x7fa000+j,0,1)end;put(0x7fa000,0xb675,2);put(0x7fa03a,100,4);put(0x43904a,0xb4fb,2);put(0x437e10,0xb5fb,2);put(0x437e12,0,2);put(0x437e08,'+str(chain_step-1)+',4);put(0x437e0c,49,4)\n'
            initialinstall+=' put(0x7fa100,'+str(chain_fields['combostyle'])+',4)\n'
            for field,value in dict(SourceAttackBody4086_Ready=0xb605,SourceAttackBody4086_Status=0,SourceAttackBody4086_Bank=58,SourceAttackBody4086_Base=0x8000,SourceAttackBody4086_Bytes=len(chain_table)).items():initialinstall+=f' put({sy[field]},{value},2)\n'
            for i,value in enumerate(chain_table[16+default*9:25+default*9]):initialinstall+=f' put({0x435980+i},{value},1)\n'
            initialinstall+=' put(0x435989,0xb605,2)\n'
            lua+="emu.addMemoryCallback(function()emu.log('ATTACKCHAINCOMPLETE|'..word(INDEX)..'|'..word(0x7fa002)..'|'..dw(0x437e08)..'|'..dw(0x437e0c)..'|'..dw(0x43900c)..'|'..dw(0x40c058)..'|'..dw(0x43eb00)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.SourceUpdateFrame4086_State))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
        if a.costmove_model:
            cost_fields=next(an['fields'] for an in cost_energy['animations'] if an['handle']==animation['handle'])
            cost_settings=dict(SourceAnimationEnergy4086_Ready=0xb5fc,SourceAnimationEnergy4086_Bank=58,SourceAnimationEnergy4086_Bytes=len(cost_energy_table),SourceCheckEnergy4086_Ready=0xb5fa,SourceRetirement4086_Ready=0xb4f8,SourceRetirement4086_Status=0)
            initialinstall+='\n'+"\n".join(" set('"+n+"',"+str(v)+")" for n,v in cost_settings.items())
            initialinstall+='\n for j=0,2111 do put(0x7fa000+j,0,1)end;put(0x7fa000,0xb670,2);put(0x7fa006,'+str(animation['engine_animation_id'])+',2);put(0x7fa008,1,4);put(0x40c04c,100,4);put(0x437e04,0,4);put(0x437e10,0xb5fb,2);put(0x437e12,0,2);put(0x40901c,0,4)\n'
            lua+=f"emu.addMemoryCallback(function()emu.log('COSTMOVECOMPLETE|'..word(INDEX)..'|'..word(0x7fa002)..'|'..dw(0x40c04c)..'|'..dw(0x414024)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.SourceUpdateFrame4086_State))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
            if a.source_command:
                selected_command=next(c for m in command_report['models'] if m['model']==a.costmove_model for c in m['combos'] if c['anim']==animation['engine_animation_id'])
                initialinstall+=f"\n for j=0,1023 do put({controller['input_history']}+j,0,1)end;for j=0,95 do put({controller['combo_controls']}+j,0,1)end;put({controller['combo_controls']},0xb673,2);put({controller['input_owner']},0xb674,2);put({controller['input_history']+224},0x80001dfc,4);put(0x414028,1,2);put(0x41402a,0,2);put(0x41402c,0,4);put(0x414008,2,2);put(0x41400a,0,2);put(0x41400c,0,4);put(0x41f508,0,4);put(0x43eb00,1,4);put(0x43eb08,0,4)\n"
                for j,command_mask in enumerate(selected_command['input']):initialinstall+=f" put({controller['input_history']+108+4*((27-len(selected_command['input'])+j)%27)},{command_mask},4)\n"
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
        drop_required=enemy_role=='idle'and(stage_row is None or(-30<stage_row['coords'][0]<context_report['stages'][stage_row['stage_id']-1]['source_width']+30 and stage_row['coords'][2]==0))
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
        initialinstall+="\n put(0x414004,0,4);put(0x43fd80,0,4);put(sy.SourceCtorState4086_X,dw(0x414034),4);put(sy.SourceCtorState4086_Z,dw(0x41403c),4);put(sy.SourceCtorState4086_A,"+str(a.ctor_altitude_q16)+",4);put(sy.SourceCtorState4086_Direction,c.direction,4);put(sy.SourceCtorState4086_Time,48,4);put(sy.SourceCtorState4086_Player,0,4)\n"
        lua+="emu.addMemoryCallback(function()local name='';for j=0,47 do local ch=emu.read(0x433800+j,mt);if ch==0 then break end;name=name..string.char(ch)end;emu.log('CTORSTATEOWNER|'..word(INDEX)..'|'..word(sy.SourceCtorState4086_Status)..'|'..dw(0x41680c)..'|'..dw(0x416810)..'|'..word(0x41681e)..'|'..word(0x433830)..'|'..word(0x433832)..'|'..name)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.ctor_owner:
        initialinstall+="\n set('SourceTarget4086_OrderReady',0xb4d3);for i=0,127 do put(0x41f200+i*2,i,2)end\n"
        initialinstall+="\n set('SourceCtorOwner4086_Phase',0);set('SourceCtorOwner4086_Model',65535);set('SourceSpawnSlot4086_Ready',0xb5a1);set('SourceSpawnSlot4086_Status',0);set('SourceSpawnSlot4086_Model',"+str(default)+");put(sy.SourceSpawnSlot4086_OverrideLo,999999,4)\n"
        lua+="emu.addMemoryCallback(function()emu.log('CTOROWNER|'..word(INDEX)..'|'..word(sy.SourceCtorOwner4086_Phase)..'|'..word(sy.SourceCtorOwner4086_Model)..'|'..word(sy.SourceSpawnSlot4086_Slot)..'|'..word(sy.SourceSpawnSlot4086_NeedKill))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
        address=fs['CallbackFixture_ResultPublished']
        lua+=f"emu.addMemoryCallback(function()emu.log('CTORPUBLISHED|'..word(INDEX)..'|'..word(sy.VmNativeVariant_Result)..'|'..word(sy.VmNativeVariant_Result+2)..'|'..dw(sy.VmNativeVariant_Result+4))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if stage_row:
        initialinstall+='\n'+\
            '\n'.join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceStageQueue4086_Ready=0xb5d2,SourceStageQueue4086_Status=0,SourceStageQueue4086_Base=locations['stagequeue']&65535,SourceStageQueue4086_Bank=59,SourceStageQueue4086_Bytes=len(queue_table),SourceStageQueue4086_Records=len(queue_rows),SourceStageQueue4086_Stages=len(stage_queue_report['stages']),SourceStageQueue4086_Index=a.stage_queue_index,SourceStageQueue4086_Stage=stage_row['stage_id'],SourceEnvironment4086_Stage=stage_row['stage_id'],SourceEmptyInitEnvironment4086_Stage=stage_row['stage_id'],VmSourceWorld_ScrollAxis=0).items())
        initialinstall+='\n put(sy.VmSourceWorld_AdvanceX,'+str(stage_row['at']*65536)+',4);put(sy.VmSourceWorld_AdvanceY,0,4)\n'
        lua+="emu.addMemoryCallback(function()emu.log('STAGECTORINPUT|'..word(INDEX)..'|'..word(sy.SourceStageQueue4086_Status)..'|'..word(sy.SourceStageQueue4086_Model)..'|'..dw(sy.SourceCtorState4086_X)..'|'..dw(sy.SourceCtorState4086_Z)..'|'..dw(sy.SourceCtorState4086_A)..'|'..dw(sy.SourceCtorState4086_Direction))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.smartspawn:
        cap=spawn_caps['models'][default]
        initialinstall+='\n'+ '\n'.join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceSmartSpawn4086_Ready=0xb5d4,SourceSmartSpawn4086_Status=0,SourceSmartSpawn4086_MapModel=default,SourceSmartSpawn4086_MapsLoaded=cap['maps_loaded'],SourceSmartSpawn4086_BossMusic=int(bool(boss_music_present))).items())
        address=fs['CallbackFixture_PropertiesPublished']
        lua+=f"emu.addMemoryCallback(function()local name='';for i=0,47 do local ch=emu.read(0x433800+i,mt);if ch==0 then break end;name=name..string.char(ch)end;emu.log('SMARTCTOR|'..word(INDEX)..'|'..word(sy.SourceSmartSpawn4086_Status)..'|'..word(sy.SourceSmartSpawn4086_Players)..'|'..dw(0x414024)..'|'..dw(0x40c03c)..'|'..word(0x433830)..'|'..dw(0x433838)..'|'..word(0x43383c)..'|'..name)end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.queue_producer:
        first=sum(len(st['records'])for st in stage_queue_report['stages'][:stage_row['stage_id']-1]);limit=first+len(stage_queue_report['stages'][stage_row['stage_id']-1]['records'])
        initialinstall+='\n'+ '\n'.join(" set('"+name+"',"+str(value)+")"for name,value in dict(SourceStageProducer4086_Ready=0xb5d6,SourceStageProducer4086_State=0,SourceStageProducer4086_First=first,SourceStageProducer4086_Limit=limit,SourceStageProducer4086_GroupMin=100,SourceStageProducer4086_GroupMax=100,SourceStageProducer4086_Completed=0,SourceStageProducer4086_Waiting=0,SourceSmartSpawn4086_Status=0).items())
        initialinstall+='\n put(sy.SourceStageProducer4086_GroupMin,100,4);put(sy.SourceStageProducer4086_GroupMax,100,4);put(sy.SourceStageProducer4086_Position,'+str(stage_row['at'])+',4)\n'
        if a.scroller_owner:
            if a.stage_queue_index!=limit-1:raise ValueError('SCROLLER_CTOR_FIXTURE_REQUIRES_TERMINAL_SOURCE_RECORD')
            import io
            from PIL import Image
            stage_doc=document(source,stage_queue_report['stages'][stage_row['stage_id']-1]['source_path'])
            panels=[r['values'][0]for r in stage_doc['directives']if r['directive']=='panel']
            if len(panels)!=1:raise ValueError('SCROLLER_CTOR_FIXTURE_PANEL_SHAPE')
            with Image.open(io.BytesIO(source.read(panels[0])))as im:width,height=im.size
            controls=dict(SourceScrollerOwner4086_Ready=0xb5dd,SourceScrollerOwner4086_State=0,SourceScrollerPrefix4086_Ready=0xb5d7,SourceScrollerPrefix4086_State=0,SourceStageCompletion4086_Ready=0xb5d8,SourceWait4086_Ready=0xb5d9,SourceWait4086_Status=0,SourceCameraBounds4086_Ready=0xb5da,SourceCameraBounds4086_Status=0,SourceCameraBounds4086_MaxPlayers=4,SourceCameraBounds4086_CameraType=0,SourceCameraMotion4086_Ready=0xb5db,SourceCameraMotion4086_Status=0,SourceCameraMotion4086_Direction=2,SourceCameraMotion4086_Width=width,SourceCameraMotion4086_Height=height,SourceCameraMotion4086_HRes=320,SourceCameraMotion4086_VRes=240,SourceCameraMotion4086_Rocking=0)
            initialinstall+='\n'+'\n'.join(" set('"+n+"',"+str(v)+")"for n,v in controls.items())
            wide=dict(SourceScrollerPrefix4086_AdvanceTime=47,SourceScrollerPrefix4086_FreezeAll=0,SourceScrollerPrefix4086_Completed=0,SourceStageCompletion4086_LevelType=0,SourceWait4086_NoReset=0,SourceWait4086_SetTime=100,SourceWait4086_TimeLeft=-77,SourceCameraMotion4086_Speed=65536,SourceCameraMotion4086_OffsetX=0,SourceCameraMotion4086_OffsetZ=0,SourceCameraMotion4086_MinX=0,SourceCameraMotion4086_MaxX=(width-320)*65536,SourceCameraMotion4086_MinZ=0,SourceCameraMotion4086_MaxZ=height*65536,SourceCameraMotion4086_Blockade=0)
            initialinstall+='\n'+'\n'.join(" set('"+n+"',"+str(v)+",4)"for n,v in wide.items())+'\n for i=0,3 do put(0x43fd84+i*4,0,4)end\n'
        address=fs['CallbackFixture_QueuePublished']
        lua+=f"emu.addMemoryCallback(function()emu.log('QUEUECTOR|'..word(INDEX)..'|'..word(sy.SourceStageProducer4086_State)..'|'..word(sy.SourceStageQueue4086_Index)..'|'..word(sy.SourceSmartSpawn4086_Status)..'|'..word(sy.SourceClock4086_Due)..'|'..dw(sy.SourceClock4086_TimeLo))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
        if a.scroller_owner:
            lua+=f"emu.addMemoryCallback(function()emu.log('SCROLLERCTOR|'..word(INDEX)..'|'..word(sy.SourceScrollerOwner4086_State)..'|'..word(sy.SourceScrollerPrefix4086_State)..'|'..word(sy.SourceWait4086_Status)..'|'..word(sy.SourceCameraMotion4086_Status))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
        address=fs['CallbackFixture_InstrumentMusicService']
        lua+=f"emu.addMemoryCallback(function()emu.log('QUEUE_MUSIC_SERVICE_INSTRUMENTED|'..word(INDEX))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.physics_state_birth:
        initialinstall+="\n set('SourcePhysicsState4086_Ready',0xb61c);for j=0,2047 do emu.write(0x42d800+j,165,mt)end\n"
        address=sy['SourceCtorState4086_PhysicsStateBirthDone']
        lua+=f"emu.addMemoryCallback(function()local sum=0;for j=0,15 do sum=sum+emu.read(0x42d800+j,mt)end;local other=0;for j=0,15 do other=other+emu.read(0x42d810+j,mt)end;emu.log('CTORPHYSICS|'..word(INDEX)..'|'..sum..'|'..other..'|'..dw(0x414004))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.damage_state_birth:
        initialinstall+="\n set('SourceDamageState4086_Ready',0xb62b);for j=0,1535 do emu.write(0x7fb900+j,165,mt)end\n"
        address=sy['SourceCtorState4086_DamageStateBirthDone']
        lua+=f"emu.addMemoryCallback(function()local n=0;for j=0,11 do local wanted=j<4 and((dw(0x439040)>>(8*j))&255)or 0;if emu.read(0x7fb900+j,mt)~=wanted then n=n+1 end end;local other=0;for j=0,11 do other=other+emu.read(0x7fb90c+j,mt)end;emu.log('CTORDAMAGE|'..word(INDEX)..'|'..n..'|'..other..'|'..dw(0x414004))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.damage_effects_state_birth:
        settings=dict(SourceDamageEffectsState4086_Ready=0xb62f,SourceLandingDrop4086_Ready=0xb62e,SourceLandingDrop4086_Base=locations['damageinputs']&65535,SourceLandingDrop4086_Bank=base>>16,SourceLandingDrop4086_Bytes=len(damage_inputs_table),SourceLandingDrop4086_Models=len(damage_inputs_report['models']))
        initialinstall+='\n'+'\n'.join(" set('"+k+"',"+str(v)+")"for k,v in settings.items())+'\n for j=0,3071 do emu.write(0x7ef100+j,165,mt)end\n'
        guard=damage_inputs_report['models'][default]['fields']['guardpoints']&0xffffffff
        initialinstall+='\n for j=0,511 do emu.write(0x7efd00+j,165,mt)end\n'
        address=sy['SourceCtorState4086_DamageEffectsBirthDone']
        lua+=f"emu.addMemoryCallback(function()emu.log('CTORTOEXPLODE|'..word(INDEX)..'|'..dw(0x7efd00)..'|'..dw(0x7efd04)..'|'..dw(0x414004))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
        lua+=f"emu.addMemoryCallback(function()local n=0;local wanted={{}};for j=0,23 do wanted[j]=0 end;for j=0,3 do wanted[16+j]=({guard}>>(8*j))&255 end;wanted[20]=0x2f;wanted[21]=0xb6;wanted[22]={default};for j=0,23 do if emu.read(0x7ef100+j,mt)~=wanted[j]then n=n+1 end end;local other=0;for j=0,23 do other=other+emu.read(0x7ef118+j,mt)end;emu.log('CTORDAMAGEEFFECT|'..word(INDEX)..'|'..n..'|'..other..'|'..dw(0x414004))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.death_fields_birth:
        settings=dict(SourceDeathFields4086_Ready=0xb638,SourceDeathFields4086_Base=locations['deathfields']&65535,SourceDeathFields4086_Bank=base>>16,SourceDeathFields4086_Bytes=len(death_table),SourceDeathFields4086_Models=16)
        initialinstall+='\n'+'\n'.join(" set('"+k+"',"+str(v)+")"for k,v in settings.items())+'\n'
        initialinstall+='\n for j=0,7 do emu.write(0x414048+j,165,mt);emu.write(0x414098+j,165,mt);emu.write(0x409038+j,165,mt);emu.write(0x409078+j,165,mt)end\n'
        address=sy['SourceCtorModel4086_DeathCopied']
        lua+=f"emu.addMemoryCallback(function()emu.log('CTORDEATHFIELDS|'..word(INDEX)..'|'..dw(0x414048)..'|'..dw(0x41404c)..'|'..word(0x409038)..'|'..word(0x40903a)..'|'..dw(0x40903c)..'|'..dw(0x414098)..'|'..dw(0x409078))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.stationary_post:
        settings=dict(SourcePostStationary4086_Ready=0xb61a,SourcePostStationary4086_Status=0,SourcePostStationary4086_Slot=0,SourceGravityIdle4086_Ready=0xb619,SourceGravityIdle4086_Status=0,SourceCheckMove4086_Ready=0xb617,SourceCheckMove4086_Status=0,SourceWorldTick4086_Ready=0xb4d5,SourceWorldTick4086_State=2,SourceWorldTick4086_Pending=1,SourceWorldTick4086_Phase=11,SourceWorldTick4086_Slot=0,SourceWorldTick4086_Fault=0)
        if a.adjust_base_empty:
            settings.update(SourceAdjustBaseEmpty4086_Ready=0xb620,SourceAdjustBaseEmpty4086_Status=0,SourceAnimationPhysics4086_Ready=0xb61f,SourceAnimationPhysics4086_Status=0,SourceAnimationPhysics4086_Base=0x8000,SourceAnimationPhysics4086_Bank=58,SourceAnimationPhysics4086_Bytes=len(physics_table),SourceAnimationPhysics4086_Animations=struct.unpack_from('<H',physics_table,6)[0])
        install=';'.join(f'set("{k}",{v})'for k,v in settings.items())
        lua+=f"local post_before={{}};emu.addMemoryCallback(function(){install};set('SourceWorldTick4086_TimeLo',dw(sy.VmSourceWorld_Time),4);post_before={{}};for _,r in ipairs({{{{0x414000,18432}},{{0x41f300,512}},{{0x41f500,2560}},{{0x42e000,5120}},{{0x42d800,2048}},{{0x439000,10240}},{{0x40c000,12288}},{{sy.SourceSelf4086_GlobalLow,4}}}})do for i=0,r[2]-1 do post_before[r[1]+i]=emu.read(r[1]+i,mt)end end end,emu.callbackType.exec,{fs['CallbackFixture_PostBefore']},{fs['CallbackFixture_PostBefore']},emu.cpuType.snes,mt)\n"
        if a.adjust_base_empty:
            lua+=f"emu.addMemoryCallback(function()emu.log('CTORBASE|'..word(INDEX)..'|'..word({sy['SourceAdjustBaseEmpty4086_Status']})..'|'..word({sy['SourceAnimationPhysics4086_Status']}))end,emu.callbackType.exec,{fs['CallbackFixture_PostAfter']},{fs['CallbackFixture_PostAfter']},emu.cpuType.snes,mt)\n"
        lua+=f"emu.addMemoryCallback(function()local time=dw(sy.VmSourceWorld_Time);for _,r in ipairs({{{{0x41f300,(time+1)&0xffffffff}},{{0x416818,(time+1)&0xffffffff}},{{0x42e024,12}}}})do for i=0,3 do post_before[r[1]+i]=(r[2]>>(8*i))&255 end end;local n=0;for a,v in pairs(post_before)do if emu.read(a,mt)~=v then n=n+1 end end;emu.log('CTORPOST|'..word(INDEX)..'|'..n..'|'..word({sy['SourceGravityIdle4086_Status']})..'|'..word({sy['SourceCheckMove4086_Status']})..'|'..dw(0x41400c)..'|'..dw(0x416830)..'|'..dw(0x41682c)..'|'..word(0x41681e)..'|'..dw(0x40c014)..'|'..dw(0x40c024))end,emu.callbackType.exec,{fs['CallbackFixture_PostAfter']},{fs['CallbackFixture_PostAfter']},emu.cpuType.snes,mt)\n"
    lua=lua.replace('FREEZESTATE',str(0xb5df if a.freeze_state else 0))
    if a.costmove_model or a.attack_chain_model:
        lua=lua.replace("word(sy.SourceDefaultChoice4086_Chosen)..'|'..word(sy.SourceAnimationInit4086_State)","word(sy.SourceAnimationInit4086_Number)..'|'..word(sy.SourceAnimationInit4086_State)")
    if a.costmove_model:
        for label in ('SourceCostMove_Finish','SourceCostMove_Fault','SourceCostMove_Complete'):
            lua+=f"emu.addMemoryCallback(function()emu.log('COSTCONTINUE|{label}|'..word(0x7fa000)..'|'..word(0x7fa002)..'|'..word(0x7fa004)..'|'..word(0x7fa006)..'|'..word(sy.SourceAnimationInit4086_Slot)..'|'..word(sy.SourceAnimationInit4086_Number)..'|'..word(sy.SourceAnimationInit4086_State))end,emu.callbackType.exec,{fs[label]},{fs[label]},emu.cpuType.snes,mt)\n"
    if a.attack_chain_post_mutation:
        lua+=f"emu.addMemoryCallback(function()put(0x437e08,12,4);put(0x7fa100,2,4);put(0x7fa03a,37,4)end,emu.callbackType.exec,{fs['SourceAttackChain_Finish']},{fs['SourceAttackChain_Finish']},emu.cpuType.snes,mt)\n"
    if a.ai_state_birth:
        if not a.ctor_state:raise ValueError('AI_STATE_BIRTH_REQUIRES_CTOR_STATE')
        lua=lua.replace(" set('SourceVMRun4086_Ready',0xb4d7)"," for j=0,47 do put(0x42f400+j,0xff,1)end\n set('SourceVMRun4086_Ready',0xb4d7)")
        address=sy['SourceCtorState4086_AIStateBirthDone']
        lua+=f"emu.addMemoryCallback(function()local slot=word(sy.SourceScriptClone4086_Slot);local cleared=0;local sibling=0;for j=0,23 do cleared=cleared+emu.read(0x42f400+slot*24+j,mt);sibling=sibling+emu.read(0x42f400+(slot+1)*24+j,mt)end;emu.log('CTORAI|'..word(INDEX)..'|'..slot..'|'..cleared..'|'..sibling..'|'..dw(0x414004+slot*80))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.player_state_birth:
        tail=player_state_plan['base']
        lua=lua.replace(' put(0x7ffb86,c.fault,2)',
                        f' put(0x7ffb86,c.fault,2)\n for j=0,63 do put({player_state_work}+j,0,1)end\n put({player_state_work}+8,word(INDEX)+1,4)')
        poison=fs['CallbackFixture_PlayerStatePoison']
        address=sy['SourceCtorState4086_AIStateBirthDone']
        lua+=f"emu.addMemoryCallback(function()for j=0,23 do put({tail}+j,0xa5,1);put({tail}+127*24+j,0xa5,1)end end,emu.callbackType.exec,{poison},{poison},emu.cpuType.snes,mt)\n"
        lua+=f"emu.addMemoryCallback(function()local slot=word(sy.SourceScriptClone4086_Slot);local cleared=0;local sibling=0;for j=0,23 do cleared=cleared+emu.read({tail}+slot*24+j,mt);sibling=sibling+emu.read({tail}+127*24+j,mt)end;emu.log('CTORPLAYERSTATE|'..word(INDEX)..'|'..slot..'|'..cleared..'|'..sibling..'|'..dw(0x414004+slot*80)..'|'..word({player_state_work})..'|'..word(sy.VmState_SlotCount))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
        if a.run_tuple_birth:
            lua=lua.replace(' put(0x7ffb86,c.fault,2)',f' put(0x7ffb86,c.fault,2)\n for j=0,63 do put({run_work}+j,0,1)end\n put({run_work},0xb678,2)\n for j=0,255 do put({run_handles}+j,0xa5,1)end')
            run_done=fs['SourceRunTuple_CtorModelDone']
            lua+=f"emu.addMemoryCallback(function()local slot=word(sy.SourceScriptClone4086_Slot);emu.log('CTORRUNTUPLE|'..word(INDEX)..'|'..slot..'|'..word({run_handles}+slot*2)..'|'..word({run_handles}+127*2)..'|'..dw(0x414004+slot*80)..'|'..word({run_work}+2))end,emu.callbackType.exec,{run_done},{run_done},emu.cpuType.snes,mt)\n"
    if a.ground_walk:
        prepare=fs['CallbackFixture_GroundPrepare'];done=fs['CallbackFixture_GroundDone']
        lua+=f'''emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for _,r in ipairs({{{{{g},128}},{{{b},32}},{{{e},24}},{{{service_work},32}}}})do for j=0,r[2]-1 do put(r[1]+j,0,1)end end
 put({g},0xb679,2);put({b},0xb67c,2);put({e},0xb67d,2);put({service_work},0xb67e,2)
 put({g}+16,c.ground_keys,4);put({g}+20,1,2);put({g}+22,1,2);put({g}+40,48,4)
 set('SourceDefaultPlayer4086_Ready',0xb503);set('SourceDefaultPlayer4086_Status',0)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',2)
end,emu.callbackType.exec,{prepare},{prepare},emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('GROUNDWALK|'..word(INDEX)..'|'..word({service_work}+2)..'|'..word({g}+2)..'|'..dw(0x416824)..'|'..dw(0x416828)..'|'..dw(0x43900c)..'|'..dw(0x43eb00)..'|'..word(sy.SourceAnimationInit4086_Number)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.SourceUpdateFrame4086_State))
end,emu.callbackType.exec,{done},{done},emu.cpuType.snes,mt)
'''
    if a.freeze_state:
        address=sy['SourceCtorState4086_FreezeBirthDone']
        lua+=f"emu.addMemoryCallback(function()local slot=word(sy.SourceScriptClone4086_Slot);local cleared=0;local sibling=0;for j=0,39 do cleared=cleared+emu.read(0x42e000+slot*40+j,mt);sibling=sibling+emu.read(0x42e000+(slot+1)*40+j,mt)end;emu.log('CTORFREEZE|'..word(INDEX)..'|'..slot..'|'..cleared..'|'..sibling..'|'..dw(0x41f300+slot*4)..'|'..dw(0x414004+slot*80))end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    if a.common_spawn:
        settings=dict(SourceAI4086_Ready=0xb5e2,SourceAI4086_State=1,SourceAI4086_Slot=0,SourceAI4086_SpawnID=role_id(config,'spawn'),SourceAI4086_RespawnID=role_id(config,'respawn'),SourceCommonSpawn4086_Ready=0xb5e3,SourceCommonSpawn4086_State=0,SourceWorldTick4086_Ready=0xb4d5,SourceWorldTick4086_State=1,SourceWorldTick4086_Pending=1,SourceWorldTick4086_Phase=6,SourceWorldTick4086_Slot=0,SourceWorldTick4086_TimeLo=48,SourceWorldTick4086_TimeHi=0,SourceFreeze4086_Ready=0xb5df,SourceLifecycle4086_Ready=0xb4fb,SourceSelf4086_Ready=0xb4f6,SourceSelf4086_Active=0,SourceSelf4086_Fault=0,SourceSelf4086_GlobalLow=0x4000,SourceSelf4086_GlobalHigh=0x41)
        initialinstall+='\n'+'\n'.join(" set('"+k+"',"+str(v)+")"for k,v in settings.items())
        initialinstall+='\nput(0x43900c,4,4);put(0x43eb00,3,2);put(0x41f510,0,2);put(0x416804,'+str(previous_animation['handle'])+',2);put(0x414014,'+str(previous_animation['engine_animation_id'])+',4);put(0x414004,1,4)\n'
        lua+="emu.addMemoryCallback(function()emu.log('COMMONSPAWN|'..word(INDEX)..'|'..word(sy.SourceCommonSpawn4086_State)..'|'..dw(0x43900c)..'|'..word(0x43eb00)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceWorldTick4086_Pending)..'|'..dw(sy.VmSourceWorld_Time))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
    if a.ai_run:
        initialinstall+="\nset('SourceAI4086_State',0);set('SourceAI4086_Endgame',0,4);set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);put(0x439000,0,4);put(0x416814,48,4);put(0x42f400,0,4);put(0x42e024,0,4)\n"
        lua+="emu.addMemoryCallback(function()emu.log('AIRUNFRAME|'..word(INDEX)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)..'|'..dw(0x42e024)..'|'..dw(0x416814)..'|'..word(sy.SourceAIRun4086_PendingKind))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
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
    if a.source_command:
        # Relocate the existing cost proof's controls before adding history data.
        lua=re.sub(r'0x7fa0[0-3][0-9a-f]',lambda m:str(cost_work+int(m[0],16)-0x7fa000),lua)
        lua+=f"emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];put(0x41402c,c.direction,4);put({controller['input_history']}+c.direction*256+224,0xc0001dfc,4)end,emu.callbackType.exec,{fs['SourceCombo_Finish']},{fs['SourceCombo_Finish']},emu.cpuType.snes,mt)\n"
        lua+=f"emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];emu.log('COMMANDCOMPLETE|'..word(INDEX)..'|'..word({controller['combo_controls']+2})..'|'..word({controller['combo_controls']+8})..'|'..dw({controller['input_history']}+c.direction*256+224)..'|'..dw({controller['input_history']+224})..'|'..dw({controller['input_history']+480}))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
        for name,value in values.items():lua=re.sub(r'\b'+name+r'\b',str(value),lua)
    script=folder/'callback_owner.lua';script.write_text(lua)
    if a.emit_only:
        print('Private source-derived fixture emitted; native execution NOT performed:',path)
        return
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
        run_frames_exact(m,12)
        if a.costmove_model or a.attack_chain_model or a.player_state_birth:
            # Explicit isolated payload lease: retire ordinary producers. This
            # is not the previously proven whole-canvas production handoff.
            for n in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):m.write_u8(sy[n],0)
        # The request may precede the next foreground gate by more than one
        # field. Uninitialized fixture counters are not an early failure.
        m.write_u16(INDEX,0);m.write_u16(ERROR,0)
        m.write_u16(REQUEST,0xb4e7)
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
        expected_frame=[[i,1,0,1,0x4000,0x41,1,48,1] if c['fault'] else ([i,2,2,0,0x4000,0x41,1,48,0]if a.common_spawn else [i,2,2,0,0,0,1,48,0]if a.queue_producer else[i,2,2,0,0,0,0,49,0]) for i,c in enumerate(rows)]
        reporter.check('actual frame/effect completion with current self retained and world clock pending'if a.common_spawn else'actual callback birth followed by native captured effect retirement and clock',frame_results==expected_frame)
    if coretable:reporter.check('authored callback publishes exact native birth core and preserves parent role/type',core_results==[[i,0] for i in range(len(rows))])
    if a.costmove_model:
        cost_results=[list(map(int,s.split('COSTMOVECOMPLETE|')[1].strip().split('|'))) for s in (folder/'mesen.log').read_text().splitlines() if 'COSTMOVECOMPLETE|' in s]
        reporter.check('costmove debit and mandatory native callback completion precede success',cost_results==[[i,4,100-cost_fields['cost'],150,2,2] for i in range(len(rows))])
        if a.source_command:
            command_results=[list(map(int,line.split('COMMANDCOMPLETE|')[1].strip().split('|'))) for line in (folder/'mesen.log').read_text().splitlines() if 'COMMANDCOMPLETE|' in line]
            reporter.check('source command completes actual callback and clears fresh post-callback player keys',command_results==[[i,4,animation['engine_animation_id'],0xc0000000,0x80001dfc if c['direction'] else 0xc0000000,0xc0000000 if c['direction'] else 0] for i,c in enumerate(rows)])
    if a.attack_chain_model:
        chain_results=[list(map(int,line.split('ATTACKCHAINCOMPLETE|')[1].strip().split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'ATTACKCHAINCOMPLETE|'in line]
        reporter.check('actual authored attack chain completes real callback before source cleanup',chain_results==[[i,5,0 if a.attack_chain_post_mutation else chain_step,85 if a.attack_chain_post_mutation else 49,17,1,0,2,2]for i in range(len(rows))])
    if a.initial_select or a.initial_jump or a.initial_idle or a.initial_walk:reporter.check('authored '+(enemy_role.upper()if a.initial_enemy else'JUMP'if a.initial_jump else'IDLE'if a.initial_idle else'WALK'if a.initial_walk else'SELECT')+(' transition completes actual frame zero; world service remains pending'if a.common_spawn else' initialization completes actual frame-zero before clock retirement'),len(select_results)==len(rows)and all(r[0]==i and (a.initial_enemy or a.initial_idle or a.initial_walk or r[1]==(65535 if a.initial_jump else animation['engine_animation_id']))and r[2:]==[2,1,animation['engine_animation_id'],animation['handle'],0]for i,r in enumerate(select_results)))
    if a.initial_jump:reporter.check('real JUMP frame zero and post-callback source makeinv fields',jump_results==[[i,300*65536,2,1,3,5,1,1,848,1]for i in range(len(rows))])
    tail_results=[list(map(int,line.split('CALLBACKTAIL|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKTAIL|'in line]
    if a.initial_jump:reporter.check('source current-model tail after JUMP and before clock retirement',tail_results==[[i,max(0,rootcore['multiple']),2,2 if rootcore['subject_to_wall']>0 or rootcore['subject_to_platform']>0 else 0]for i in range(len(rows))])
    idle_results=[list(map(int,line.split('CALLBACKIDLE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKIDLE|'in line]
    if a.initial_idle:
        cached_none=model_core_inputs(source)['models'][default]['fields']['type']==0
        reporter.check('generic set_idle flags and cached-type movement plus authored idle frame zero',idle_results==[[i,3,0,65536 if cached_none and not a.ctor_state else 0,131072 if cached_none and not a.ctor_state else 0,0 if a.common_spawn else 2]for i in range(len(rows))])
    walk_results=[list(map(int,line.split('CALLBACKWALK|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKWALK|'in line]
    if a.initial_walk:reporter.check('source default walk mode retained through real authored frame zero',walk_results==[[i,0 if a.ctor_model else c['direction'],2]for i,c in enumerate(rows)])
    none_walk_results=[list(map(int,line.split('CALLBACKNONEWALK|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKNONEWALK|'in line]
    if a.initial_none_walk:reporter.check('authored TYPE_NONE walk setup retained through real frame-zero and final tail',none_walk_results==[[i,1,15,(current_speed_q16 if c['direction']==1 else-current_speed_q16)&0xffffffff,65536,max(1,rootcore['subject_to_gravity'])if rootcore['subject_to_gravity']<0 else rootcore['subject_to_gravity'],1 if rootcore['no_adjust_base']<0 else rootcore['no_adjust_base']]for i,c in enumerate(rows)])
    enemy_results=[list(map(int,line.split('CALLBACKENEMY|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CALLBACKENEMY|'in line]
    if a.initial_enemy:
        speed_expected=0 if life['nomove']else speed_q16 if speed_bits&0x7fffffff else 65536
        multiple=max(0,rootcore['multiple']or 5)
        reporter.check('authored normal enemy frame zero, default callbacks, source drop RNG and final current-model tail',enemy_results==[[i,6,10,9,(5 if drop_required else 0)if enemy_role=='idle'else 4,expected_drop if drop_required else 0,seed_after if drop_required else INITIAL_SEED,1 if drop_required else 0,speed_expected&0xffffffff,int(speed_expected!=0),0xb508,multiple,2]for i in range(len(rows))])
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
    if stage_row:
        stage_results=[list(map(int,line.split('STAGECTORINPUT|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'STAGECTORINPUT|'in line]
        x,z,height=stage_row['coords_q16']
        reporter.check('actual source queue row prepares model, original geometry, direction and scrolling advance before complete constructor',stage_results==[[i,2,default,(x+stage_row['at']*65536)&0xffffffff,z&0xffffffff,height&0xffffffff,stage_row['flip']&0xffffffff]for i in range(len(rows))])
    smart_results=[]
    if a.smartspawn:
        from source_smartspawn_4086 import post
        e=dict(name=ctor_state_report['models'][default]['display_name'],health=registry['models'][default]['maxhealth'],model_health=registry['models'][default]['maxhealth'],map=0,palette=0,boss=0,spawntype=0)
        trace=post(e,stage_row,1,spawn_caps['models'][default]['maps_loaded'],boss_music_present)
        smart_results=[line.split('SMARTCTOR|',1)[1].split('|')for line in (folder/'mesen.log').read_text().splitlines()if 'SMARTCTOR|'in line]
        expected=[[str(i),str(1 if 'BOSS_MUSIC'in trace else 2),'1',str(e['health']&0xffffffff),str(e['model_health']&0xffffffff),str(e['map']),str(e['boss']&0xffffffff),'1',e['name']]for i in range(len(rows))]
        reporter.check('actual completed authored constructor precedes source alias/health/map/boss properties and explicit music request',smart_results==expected)
    queue_results=[]
    scroller_results=[]
    if a.queue_producer:
        queue_results=[list(map(int,line.split('QUEUECTOR|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'QUEUECTOR|'in line]
        reporter.check('real queue request/constructor/properties and acknowledgement advance one source record without committing the world tick',queue_results==[[i,4 if a.scroller_owner else 2,a.stage_queue_index+1,2,1,48]for i in range(len(rows))])
        if a.scroller_owner:
            scroller_results=[list(map(int,line.split('SCROLLERCTOR|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'SCROLLERCTOR|'in line]
            reporter.check('actual scroller continuation retires terminal queue and executes WAIT/camera before its no-player return',scroller_results==[[i,4,2,2,2]for i in range(len(rows))])
    if a.script_clone:reporter.check('constructor script cleanup/binding survives actual authored frame zero with foreign instance intact',clone_results==[[i,2,script_clone_report['models'][default]['initialized_mask'],0,0,99,3]for i in range(len(rows))])
    r=dict(schema='BYOR_NATIVE_ANIMATION_CALLBACK_OWNER_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(raw).hexdigest(),source_pak_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        owner_table_sha256=hashlib.sha256(callbacks).hexdigest(),cases=rows,results=results,expected=expected,faults=faults,
        source_frame_handle=animation['handle'],script_programs=owners['program_count'],
        callback_cpu_costs=costs,cost_scope='Before native callback Begin through callback completion/fault and instrumented frame-service acknowledgement; includes intervening NMI/runtime, excludes debugger initialization',
        initializer_copy_checks=initializers,
        remaining_effect_service_instrumented=not a.effects_runner,native_effect_runner=a.effects_runner,native_frame_owner=a.frame_owner,sound_service_instrumented=a.effects_runner,frame_results=frame_results,player_initialization_bound=False,source_effect_presentation_proven=False,
        combat_proven=False,motu_gameplay_proven=False,no_pcm_copies=True,no_color_reduction=True)
    r.update(native_birth_core=a.birth_core,birth_core_results=core_results)
    r.update(initial_select=a.initial_select,initial_select_results=select_results,initial_jump=a.initial_jump,initial_jump_results=jump_results)
    if a.costmove_model:r.update(costmove_model=a.costmove_model,costmove_role=a.costmove_role,costmove_results=cost_results,costmove_payload_lease='instrumented exclusive retired producer cache; production canvas handoff certified separately',production_costmove_binding=False)
    if a.source_command:r.update(source_command=selected_command,source_command_results=command_results,controller_layout=controller_layout,post_callback_playerindex_and_playkeys_mutation_instrumented=True)
    if a.attack_chain_model:r.update(attack_chain_model=a.attack_chain_model,attack_chain_step=chain_step,attack_chain_results=chain_results,attack_chain_table_sha256=hashlib.sha256(chain_table).hexdigest(),attack_chain_frame_zero_callbacks_executed=True,attack_chain_post_callback_mutation_instrumented=a.attack_chain_post_mutation,production_attack_chain_binding=False,attack_chain_payload_lease='instrumented exclusive retired producer cache')
    r.update(empty_environment_tail_bound=a.initial_jump or a.initial_idle,tail_results=tail_results,initial_idle=a.initial_idle,initial_idle_results=idle_results)
    r.update(default_idle_registry_capability=idle_capability,default_walk_registry_capability=walk_capability,initial_walk=a.initial_walk,initial_walk_results=walk_results,initial_none_walk=a.initial_none_walk,initial_none_walk_results=none_walk_results)
    r.update(initial_none_model=a.initial_none_model,initial_none_model_results=no_walk_results)
    r.update(ctor_owner_bound=a.ctor_owner,ctor_state_bound=a.ctor_state,ctor_factors_bound=a.ctor_factors,ctor_model_bound=a.ctor_model,ctor_media_bindings_bound=False,script_clone_bound=a.script_clone,script_clone_results=clone_results,script_clone_table_sha256=hashlib.sha256(script_clone_table).hexdigest()if script_clone_table else None)
    r.update(default_owner_bound=a.default_owner,default_owner_results=owner_results)
    r.update(initial_enemy=a.initial_enemy,initial_enemy_role=enemy_role,initial_enemy_results=enemy_results,enemy_drop_context_instrumented=bool(a.initial_enemy),full_default_init_bound=False)
    r.update(stage_queue_index=a.stage_queue_index,stage_queue_row=stage_row,stage_queue_table_sha256=hashlib.sha256(queue_table).hexdigest()if queue_table else None,stage_queue_constructor_inputs_bound=stage_row is not None,stage_queue_post_constructor_properties_bound=a.smartspawn,smartspawn_results=smart_results,smartspawn_music_execution_bound=False,queue_producer_bound=a.queue_producer,queue_producer_results=queue_results,queue_music_service_instrumented=a.queue_producer)
    if a.freeze_state:
        freeze_birth_results=[list(map(int,line.split('CTORFREEZE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTORFREEZE|'in line]
        reporter.check('real constructor clears stale freeze row/toss before alive publication and retains next row',freeze_birth_results==[[i,0,0,10200,0,0]for i in range(len(rows))])
        r.update(freeze_constructor_initialization_bound=True,freeze_birth_results=freeze_birth_results)
    r.update(scroller_owner_bound=a.scroller_owner,scroller_no_player_return_only=a.scroller_owner,scroller_results=scroller_results)
    if a.common_spawn:
        common_results=[list(map(int,line.split('COMMONSPAWN|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'COMMONSPAWN|'in line]
        reporter.check('actual common_spawn clears action and forces authored idle frame zero, without acknowledging whole AI/world service',common_results==[[i,2,0,3,5 if a.ai_run else 1,1,48]for i in range(len(rows))])
        r.update(common_spawn_bound=True,common_spawn_results=common_results,prior_animation=previous_animation,world_clock_committed=False)
    if a.ai_run:
        ai_frame_results=[list(map(int,line.split('AIRUNFRAME|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'AIRUNFRAME|'in line]
        reporter.check('real check_ai action dispatch, real idle frame and uninitialized think method complete without consuming world clock',ai_frame_results==[[i,2,5,2,48,0]for i in range(len(rows))])
        r.update(ai_dispatch_frame_bound=True,ai_frame_results=ai_frame_results)
    if a.stationary_post:
        ctor_post_results=[list(map(int,line.split('CTORPOST|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if'CTORPOST|'in line]
        cm=model_core_inputs(source)['models'][default]['fields']
        reporter.check('actual source NONE constructor/frame-zero feeds stationary post without actor-field advancement injection',len(ctor_post_results)==len(rows)and all(v[0]==i and v[1:5]==[0,2,2,a.ctor_altitude_q16]and v[6:]==[0,ctor_state_report['models'][default]['alpha'],max(0,cm['subject_to_gravity']),1 if cm['no_adjust_base']<0 else cm['no_adjust_base']]for i,v in enumerate(ctor_post_results)))
        r.update(source_stationary_constructor_post_bound=True,stationary_post_results=ctor_post_results,stationary_post_owner_context_supplied=True,stationary_post_world_traversal_proven=False,constructor_altitude_q16=a.ctor_altitude_q16)
    if a.adjust_base_empty:
        base_results=[list(map(int,line.split('CTORBASE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if'CTORBASE|'in line]
        reporter.check('actual completed source constructor executes compiled current-frame base adjustment before stationary gravity',base_results==[[i,2,2]for i in range(len(rows))])
        r.update(source_constructor_base_adjustment_bound=True,base_adjustment_results=base_results,compiled_physics_table_sha256=hashlib.sha256(physics_table).hexdigest(),closed_empty_world_context_supplied=True)
    if a.physics_state_birth:
        physics_birth_results=[list(map(int,line.split('CTORPHYSICS|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if'CTORPHYSICS|'in line]
        reporter.check('native physics state clears before actual constructor exists publication and preserves sibling row',physics_birth_results==[[i,0,2640,0]for i in range(len(rows))])
        r.update(native_physics_birth_bound=True,physics_birth_results=physics_birth_results,native_active_gravity_or_landing_bound=False)
    if a.ground_walk:
        ground_results=[list(map(int,line.split('GROUNDWALK|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'GROUNDWALK|'in line]
        walk_id=role_id(config,'walk');speed=project_q16(struct.unpack('<I',struct.pack('<f',model_core_inputs(source)['models'][default]['fields']['speed']))[0])
        expected=[[i,2,2,(-speed if c['ground_keys']&KEYS['moveleft']else speed if c['ground_keys']&KEYS['moveright']else 0)&0xffffffff,
                   (-speed//2 if c['ground_keys']&KEYS['moveup']else speed//2 if c['ground_keys']&KEYS['movedown']else 0)&0xffffffff,0,1,walk_id,2,2]for i,c in enumerate(rows)]
        reporter.check('actual constructor RUN/state feeds ground movement, live item type scan and real WALK frame owner',ground_results==expected)
        r.update(canonical_ground_walk_bound=True,ground_walk_results=ground_results,ground_services_frame_callbacks_real=True,
                 ground_level_and_input_context_instrumented=True,production_full_player_think_bound=False)
    r['status']='PASS' if all(ok for _,ok in reporter.results) else 'FAIL'
    if a.damage_state_birth:
        damage_birth_results=[list(map(int,line.split('CTORDAMAGE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if'CTORDAMAGE|'in line]
        reporter.check('native damage state follows fresh source model copy before script bind/default callbacks, retaining sibling',damage_birth_results==[[i,0,1980,1]for i in range(len(rows))])
        r.update(native_damage_state_birth_bound=True,damage_birth_results=damage_birth_results,native_damage_callback_bound=False)
        r['status']='PASS' if all(ok for _,ok in reporter.results) else 'FAIL'
    if a.damage_effects_state_birth:
        damage_effect_results=[list(map(int,line.split('CTORDAMAGEEFFECT|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if'CTORDAMAGEEFFECT|'in line]
        toexplode_results=[list(map(int,line.split('CTORTOEXPLODE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if'CTORTOEXPLODE|'in line]
        reporter.check('actual constructor clears current source toexplode and preserves sibling before script/default callbacks',toexplode_results==[[i,0,0xa5a5a5a5,1]for i in range(len(rows))])
        r.update(native_toexplode_birth_bound=True,toexplode_birth_results=toexplode_results)
        reporter.check('native projectile/staydown/guard state follows actual constructor model copy before script/default callbacks and preserves sibling',damage_effect_results==[[i,0,3960,1]for i in range(len(rows))])
        r.update(native_damage_effect_state_birth_bound=True,damage_effect_birth_results=damage_effect_results,damage_inputs_table_sha256=hashlib.sha256(damage_inputs_table).hexdigest(),native_damage_callback_bound=False)
        r['status']='PASS' if all(ok for _,ok in reporter.results) else 'FAIL'
    if a.death_fields_birth:
        death_results=[list(map(int,line.split('CTORDEATHFIELDS|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTORDEATHFIELDS|'in line]
        score=death_report['models'][default]['score']&0xffffffff;diesound=struct.unpack_from('<I',ctor_cache,default*160+76)[0]
        reporter.check('actual constructor copies source score/current cached diesound, owns death extension and clears item before callbacks while preserving sibling',death_results==[[i,score,diesound,default,0xb638,0,0xa5a5a5a5,0xa5a5a5a5]for i in range(len(rows))])
        r.update(native_death_fields_birth_bound=True,death_fields_birth_results=death_results,death_fields_table_sha256=hashlib.sha256(death_table).hexdigest(),native_death_callback_bound=False)
        r['status']='PASS'if all(ok for _,ok in reporter.results)else'FAIL'
    if a.ai_state_birth:
        ai_birth_results=[list(map(int,line.split('CTORAI|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTORAI|'in line]
        reporter.check('real constructor clears all 24 stale AI bytes before exists publication and preserves sibling row',ai_birth_results==[[i,0,0,6120,0]for i in range(len(rows))])
        r.update(ai_constructor_initialization_bound=True,ai_birth_results=ai_birth_results)
        r['status']='PASS' if all(ok for _,ok in reporter.results) else 'FAIL'
    if a.player_state_birth:
        player_state_results=[list(map(int,line.split('CTORPLAYERSTATE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTORPLAYERSTATE|'in line]
        reporter.check('real constructor clears exact player-state row before exists publication and retains sibling',player_state_results==[[i,0,0,3960,0,0xb67b,player_state_plan['live_slot_count']]for i in range(len(rows))])
        r.update(actual_player_state_birth_bridge=True,player_state_birth_results=player_state_results,player_state_layout=player_state_plan,
                 player_state_payload_lease='instrumented isolated retired-producer controls; real native VM-tail extent/generation lease',
                 production_player_state_birth_binding=False,production_full_module_loader_binding=False)
        r['status']='PASS'if all(ok for _,ok in reporter.results)else'FAIL'
    if a.run_tuple_birth:
        run_birth_results=[list(map(int,line.split('CTORRUNTUPLE|',1)[1].split('|')))for line in (folder/'mesen.log').read_text().splitlines()if 'CTORRUNTUPLE|'in line]
        expected_run_handle=run_tuple_report['models'][default]['initial_tuple']
        reporter.check('real fresh model-data constructor captures exact RUN tuple before script binding and callbacks without another core copy',run_birth_results==[[i,0,expected_run_handle,0xa5a5,1,2]for i in range(len(rows))])
        r.update(actual_run_tuple_birth_capture=True,run_tuple_birth_results=run_birth_results,run_tuple_handle=expected_run_handle,
                 source_exists_set_before_model_copy=True,run_capture_before_script_binding=True,production_run_tuple_birth_binding=False)
        r['status']='PASS'if all(ok for _,ok in reporter.results)else'FAIL'
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
