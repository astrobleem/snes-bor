"""Authored weapon arguments through every native synchronized model service.

Exclusive, installed source pool. Optional frame modes dispatch the authored
weapon event; graphics, audio, nested idle and frame completion remain outside
this proof. No service acknowledgement is written by the observer.
"""
import argparse,hashlib,itertools,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_model_transition_bundle import compile as compile_bundle
from source_model_switch_4086 import CACHED_FIELDS,ENTITY_CORE_FIELDS,copy_cached_defaults,copy_entity_uninitialized
from source_model_core_4086 import FLOAT_FIELDS
from source_binary32_q16 import project
from source_model_callback_service_native import emit as callbacks
from source_model_scalar_service_native import emit as scalars
from source_model_palette_service_native import emit as palettes
from source_model_scripts_service_native import emit as scripts
from source_model_pipeline_native import emit as pipeline
from source_run_tuple_native import emit as run,emit_entity_copy_bridge
from source_foreign_state_layout import layout
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def rows_for(reports,data):
    models=[];maximum=reports['requirements']['maximum_animations']
    for i,m in enumerate(reports['requirements']['models']):
        d={f:struct.unpack_from('<f'if f in FLOAT_FIELDS else'<i',data['core'],160*i+4*j)[0]for j,f in enumerate(CACHED_FIELDS)}
        d['type']=struct.unpack_from('<i',data['core'],160*i+156)[0]
        d.update(model_flag=m['model_flag'],weapon=m['weapon_ids'],numweapons=len(m['weapon_ids']or[]),animation={})
        for a in reports['animations']['animations']:
            if a['model']==m['identity']:d['animation'][a['engine_animation_id']]=dict(handle=a['handle'],numframes=a['numframes'],delay=[f['delay_ticks']for f in reports['effects']['animations'][a['handle']-1]['frames']])
        models.append(d)
    rows=[]
    for m in reports['requirements']['models']:
        for event in m['weapon_frame_events']:
            if event['keep']!=0 or not m['weapon_ids']or not 1<=event['weapon_number']<=len(m['weapon_ids']):raise ValueError('WEAPON_PIPELINE_REQUIRES_SYNCHRONIZED_SOURCE_EVENT')
            old=m['id'];new=m['weapon_ids'][event['weapon_number']-1]
            if old==new:raise ValueError('WEAPON_PIPELINE_SAME_MODEL_EVENT')
            role=reports['animations']['animations'][event['frame_handle']-1]['engine_animation_id']
            for slot,map_value,frame in itertools.product((0,1,127),(0,65535),(event['frame'],65535)):
                before=json.loads(json.dumps(models[old]));after=json.loads(json.dumps(models[new]));before['animation']={int(k):v for k,v in before['animation'].items()};after['animation']={int(k):v for k,v in after['animation'].items()}
                copy_cached_defaults(before,after)
                olddata=dict(before,type=1);hp=max(0,olddata['health']-1);mp=max(0,olddata['mp']-1)
                entity=dict(modeldata=dict(after),health=hp,mp=mp)
                copy_entity_uninitialized(entity,olddata);effective=entity['modeldata'];effective['type']=1
                animation=after['animation'].get(role)
                if not animation or not animation['numframes']:raise ValueError('WEAPON_PIPELINE_SYNCHRONIZED_ANIMATION_REQUIRED')
                wanted_frame=min(frame,animation['numframes']-1);wanted_cache=b''.join(struct.pack('<f'if f in FLOAT_FIELDS else'<i',after[f])for f in CACHED_FIELDS)+struct.pack('<i',after['type'])
                wanted_core=b''.join(struct.pack('<i',effective[f])for f in ENTITY_CORE_FIELDS)+struct.pack('<2i',1,entity['mp'])+struct.pack('<4i',11,321,1,64)
                initial_core=b''.join(struct.pack('<i',olddata[f])for f in ENTITY_CORE_FIELDS)+struct.pack('<2i',1,mp)+struct.pack('<4i',11,321,1,64)
                want_animation=bytearray(data['animation_cache'][new*maximum*2:(new+1)*maximum*2])
                for number,a in after['animation'].items():struct.pack_into('<H',want_animation,number*2,a['handle'])
                rows.append(dict(slot=slot,old=old,new=new,map=map_value,frame=frame,role=role,number=event['weapon_number'],keep=event['keep'],source_event=event,initial_core=list(initial_core),hp=hp,maxhp=olddata['health'],wanted_hp=entity['health'],wanted_maxhp=effective['health'],wanted_core=list(wanted_core),wanted_cache=list(wanted_cache),wanted_animation=list(want_animation),wanted_handle=animation['handle'],wanted_frame=wanted_frame,wanted_nextanim=48+animation['delay'][wanted_frame],speed_q16=project(struct.unpack('<I',struct.pack('<f',after['speed']))[0]),fault=0,bad=''))
    if not rows:raise ValueError('WEAPON_PIPELINE_NO_SOURCE_REQUESTS')
    rows.extend(dict(rows[0],slot=slot,bad=bad,fault=1)for slot,bad in itertools.product((0,127),('script_ready','script_sticky','script_models','script_table','callback_ready','callback_models','callback_program','vars','vars_bank','token','wide_instance','onkill','clear_entry','old_type')))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--generic-world-owner',action='store_true');p.add_argument('--world-issued-guards',action='store_true');p.add_argument('--world-issued-animation',action='store_true');p.add_argument('--timed-guards',action='store_true');p.add_argument('--timed-world-ack',action='store_true');p.add_argument('--generic-timed-owner',action='store_true');p.add_argument('--timed-weapon',action='store_true');p.add_argument('--fast-animation-inheritance',action='store_true');p.add_argument('--warm-parent',action='store_true');p.add_argument('--fast-animation-copy',action='store_true');p.add_argument('--generic-frame-owner',action='store_true');p.add_argument('--animated-parent',action='store_true');p.add_argument('--nested-idle',action='store_true');p.add_argument('--effects-owner',action='store_true');p.add_argument('--frame-prefix',action='store_true');p.add_argument('--frame-binding',action='store_true');p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    if a.generic_world_owner and (a.world_issued_guards or a.timed_guards):raise ValueError('WORLD_OWNER_GUARD_MODE_CONFLICT')
    if a.generic_world_owner:a.world_issued_animation=True
    if a.world_issued_guards:a.world_issued_animation=True
    if a.world_issued_animation:a.timed_world_ack=True
    if a.timed_guards and a.timed_world_ack:raise ValueError('TIMED_GUARD_ACK_CONFLICT')
    if a.timed_guards:a.generic_timed_owner=True
    if a.timed_world_ack:a.generic_timed_owner=True
    if a.generic_timed_owner:a.timed_weapon=True
    if a.timed_weapon:a.generic_frame_owner=True
    if a.timed_weapon and a.warm_parent:raise ValueError('TIMED_WEAPON_WARMUP_CONFLICT')
    if a.fast_animation_inheritance:a.fast_animation_copy=True
    if a.warm_parent:a.generic_frame_owner=True
    if a.generic_frame_owner:a.animated_parent=True
    if a.animated_parent:a.nested_idle=True
    if a.nested_idle:a.effects_owner=True
    if a.effects_owner:a.frame_prefix=True
    if a.frame_prefix:a.frame_binding=True
    source=Source(a.source);reports,data,manifest=compile_bundle(source);rows=rows_for(reports,data);sy=symbols(Path('src/main.sym'));arena=layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES']);regions={r['name']:r['address']for r in arena['regions']};styles=regions['entity_combostyle'];rw=regions['run_tuple_controls'];rh=regions['entity_run_tuple'];maximum=reports['requirements']['maximum_animations']
    small=bytearray();addresses={}
    for name in('scripts','callbacks','factors','lifecycle','weapon','body','offscreen','death','timing'):
        addresses[name]=0x8000+len(small);small.extend(data[name]);small.extend(bytes(len(small)%2))
    if a.frame_binding:
        from source_frame_effect_plan import derive as derive_plan,pack as pack_plan
        rows=[r for r in rows if r['frame']==r['source_event']['frame'] and (not a.animated_parent or not r['fault'])]
        addresses['plan']=0x8000+len(small);plan=pack_plan(derive_plan(reports['effects']));small.extend(plan)
        for r in rows:
            handle=r['source_event']['frame_handle'];r['effect_offset']=struct.unpack_from('<H',data['effects'],16+8*(handle-1)+4)[0]
            r['effect_count']=len(reports['effects']['animations'][handle-1]['frames'])
            r['wanted_idle_handle']=struct.unpack_from('<H',bytes(r['wanted_animation']))[0]
            r['new_cached_type']=struct.unpack_from('<i',bytes(r['wanted_cache']),156)[0]
    if a.timed_weapon:
        from source_animation_step import derive as derive_timing,pack as pack_timing,validate_update_frame_pairing
        from source_update_animation_inputs import derive as derive_update,pack as pack_update
        tt=pack_timing(derive_timing(source));validate_update_frame_pairing(tt,data['effects']);update_report=derive_update(source);up=pack_update(update_report)
        for r in rows:r['wanted_sleep_deadline']=(48+update_report['models'][r['old']]['fields']['sleepwait'])&0xffffffff
        for name,table in [('animation_timing',tt),('animation_prefix',up)]:
            addresses[name]=0x8000+len(small);small.extend(table)
    if a.timed_guards:
        base=rows[0];rows=[]
        for slot in (0,127):
            for bad in ('tick_ready','world_ready','world_fault','world_time','phase','pending','state','timed_ready','canvas_generation','captured_slot','captured_time','captured_side','captured_frame_slot','done_slot'):
                rows.append(dict(base,slot=slot,fault=1,bad='timed_'+bad))
    if a.world_issued_guards:
        base=rows[0];rows=[]
        for slot in (0,127):
            for bad in ('world_side','world_view','resume_side','resume_frame'):
                rows.append(dict(base,slot=slot,fault=1,bad=bad))
    script_tables=[]
    if a.nested_idle:
        from script_callback_owner import derive as derive_callbacks
        from source_model_registry import derive as derive_registry,pack as pack_registry
        owners,code,metadata,dispatch=derive_callbacks(source);registry=pack_registry(derive_registry(source))
        instructions=bytearray(code);script_address={}
        for name,table in [('dispatch',dispatch),('registry',registry)]:
            script_address[name]=0x8000+len(instructions);instructions.extend(table)
        if len(instructions)>32768:raise ValueError('MODEL_PIPELINE_SCRIPT_BANK_CAPACITY')
        script_tables=[(38,0,bytes(instructions))];offs=struct.unpack_from('<6I',metadata,24)
        for r in rows:
            idle=reports['effects']['animations'][r['wanted_idle_handle']-1]
            r['wanted_idle_nextanim']=48+idle['frames'][0]['delay_ticks']
    wrapper='''
ModelPipeline_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceAttackTiming4086_Load
 bcs ModelPipeline_EntryBad
 jsl SourceWeapon4086_Resolve
 bcs ModelPipeline_EntryBad
 lda.l SourceWeapon4086_Selected
 sta.l SourceModelTransition4086_New
 lda.l SourceWeapon4086_Sync
 sta.l SourceModelAnimation4086_Sync
 jsl SourceModelTransition4086_Begin
 bcs ModelPipeline_EntryBad
 ldx #1
 ldy #0
 jsl ModelPipeline_Resume
 bcs ModelPipeline_EntryBad
 ply
 plx
 plp
 clc
 rtl
ModelPipeline_EntryBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
    if a.frame_binding:
        start=wrapper.index(' jsl SourceWeapon4086_Resolve')
        end=wrapper.index(' ldx #1')
        wrapper=wrapper[:start]+''' jsl SourceFrameEffectPlan4086_Begin
 bcs ModelPipeline_EntryBad
 jsl SourceFrameEffectBinding4086_Begin
 bcs ModelPipeline_EntryBad
 lda.l SourceFrameEffectPlan4086_Service
 cmp #3
 bne ModelPipeline_EntryBad
 jsl SourceFrameEffectBinding4086_Begin
 bcs ModelPipeline_EntryBad
'''+wrapper[end:]
        wrapper=wrapper.replace(' jsl ModelPipeline_Resume\n bcs ModelPipeline_EntryBad', ' jsl ModelPipeline_Resume\n bcs ModelPipeline_EntryBad\n jsl SourceFrameEffectBinding4086_Finish\n bcs ModelPipeline_EntryBad')
    if a.frame_prefix:
        wrapper=wrapper.replace(' jsl SourceFrameEffectPlan4086_Begin',' jsl SourceUpdateFrame4086_Begin\n bcs ModelPipeline_EntryBad\n cmp #2\n bne ModelPipeline_EntryBad\n jsl SourceFrameEffectPlan4086_Begin')
    if a.effects_owner:
        start=wrapper.index(' jsl SourceFrameEffectPlan4086_Begin');end=wrapper.index(' ldx #1')
        wrapper=wrapper[:start]+''' jsl SourceFrameOwner4086_Run
 bcs ModelPipeline_EntryBad
 cmp #3
 bne ModelPipeline_EntryBad
'''+wrapper[end:]
        wrapper=wrapper.replace(' jsl SourceFrameEffectBinding4086_Finish\n bcs ModelPipeline_EntryBad',' jsl SourceFrameOwner4086_Run\n bcs ModelPipeline_EntryBad\n cmp #4\n bne ModelPipeline_EntryBad')
    if a.nested_idle:
        wrapper=wrapper.replace(' cmp #4\n bne ModelPipeline_EntryBad', ''' cmp #4
 bne ModelPipeline_EntryBad
 jsl SourceAnimationInit4086_StartNestedFrame
 bcs ModelPipeline_EntryBad
ModelPipeline_NestedLoop:
.a16
.i16
 jsl SourceFrameOwner4086_Run
 bcs ModelPipeline_EntryBad
 cmp #$8001
 beq ModelPipeline_NestedLoop
 cmp #0
 bne ModelPipeline_EntryBad
 jsl SourceAnimationInit4086_FinishNestedFrame
 bcs ModelPipeline_EntryBad
 jsl SourceFrameOwner4086_Run
 bcs ModelPipeline_EntryBad
 cmp #0
 bne ModelPipeline_EntryBad''')
    if a.animated_parent:
        wrapper=wrapper.replace(' jsl SourceUpdateFrame4086_Begin\n bcs ModelPipeline_EntryBad\n cmp #2',' jsl SourceUpdateFrame4086_Begin\n bcs ModelPipeline_EntryBad\n cmp #1')
        wrapper=wrapper.replace(' jsl SourceFrameOwner4086_Run\n bcs ModelPipeline_EntryBad\n cmp #3', '''ModelPipeline_ParentLoop:
.a16
.i16
 jsl SourceFrameOwner4086_Run
 bcs ModelPipeline_EntryBad
 cmp #$8001
 beq ModelPipeline_ParentLoop
 cmp #3''',1)
    if a.generic_frame_owner:
        start=wrapper.index('ModelPipeline_ParentLoop:');end=wrapper.index(' ply',start)
        wrapper=wrapper[:start]+''' ldx #1
 ldy #0
ModelPipeline_GenericLoop:
.a16
.i16
 jsl ModelFrameOwner_Run
 bcs ModelPipeline_EntryBad
 cmp #$8001
 beq ModelPipeline_GenericLoop
 cmp #0
 bne ModelPipeline_EntryBad
'''+wrapper[end:]
    if a.warm_parent:
        warm=''' lda.l SourceUpdateFrame4086_Request
 pha
 lda #0
 sta.l SourceUpdateFrame4086_Request
 jsl SourceUpdateFrame4086_Begin
 bcs ModelPipeline_WarmBad
 ldx #1
 ldy #0
ModelPipeline_WarmLoop:
.a16
.i16
 jsl ModelFrameOwner_Run
 bcs ModelPipeline_WarmBad
 cmp #$8001
 beq ModelPipeline_WarmLoop
 cmp #0
 bne ModelPipeline_WarmBad
 pla
 sta.l SourceUpdateFrame4086_Request
 jmp ModelPipeline_WarmComplete
ModelPipeline_WarmBad:
.a16
.i16
 pla
 jmp ModelPipeline_EntryBad
ModelPipeline_WarmComplete:
.a16
.i16
 nop
'''
        at=wrapper.index(' jsl SourceUpdateFrame4086_Begin')
        wrapper=wrapper[:at]+warm+wrapper[at:]
    if a.timed_weapon:
        wrapper=wrapper.replace(' jsl SourceUpdateFrame4086_Begin\n bcs ModelPipeline_EntryBad\n cmp #1',' jsl SourceUpdateAnimation4086_Begin\n bcs ModelPipeline_EntryBad\n cmp #1')
        end=wrapper.index(' ply',wrapper.index('ModelPipeline_GenericLoop:'))
        wrapper=wrapper[:end]+''' jsl SourceUpdateAnimation4086_Continue
 bcs ModelPipeline_EntryBad
'''+wrapper[end:]
    if a.generic_timed_owner:
        start=wrapper.index(' jsl SourceUpdateAnimation4086_Begin');end=wrapper.index(' ply',start)
        wrapper=wrapper[:start]+''' ldx #1
 ldy #0
ModelPipeline_TimedLoop:
.a16
.i16
 jsl ModelTimedFrameOwner_Run
 bcs ModelPipeline_EntryBad
 cmp #$8001
 beq ModelPipeline_TimedLoop
 cmp #0
 bne ModelPipeline_EntryBad
'''+wrapper[end:]
    if a.timed_world_ack:
        at=wrapper.index(' ldx #1',wrapper.index(' jsl SourceAttackTiming4086_Load'))
        wrapper=wrapper[:at]+''' jsl SourceUpdateAnimation4086_CheckWorldAck
 bcc ModelPipeline_EntryBad
'''+wrapper[at:]
        at=wrapper.index(' ply',wrapper.index('ModelPipeline_TimedLoop:'))
        wrapper=wrapper[:at]+''' lda #7
 jsl SourceWorldTick4086_Ack
 bcs ModelPipeline_EntryBad
'''+wrapper[at:]
    if a.world_issued_animation:
        at=wrapper.index(' jsl SourceUpdateAnimation4086_CheckWorldAck')
        wrapper=wrapper[:at]+''' jsl SourceWorldTick4086_Poll
 bcs ModelPipeline_EntryBad
 cmp #7
 bne ModelPipeline_EntryBad
 lda.l SourceUpdateAnimation4086_State
 bne ModelPipeline_EntryBad
ModelPipeline_WorldIssued:
.a16
.i16
 nop
'''+wrapper[at:]
    if a.generic_world_owner:
        wrapper=wrapper.replace(' jsl ModelTimedFrameOwner_Run',' jsl WorldModelOwner_Run')
        wrapper=wrapper.replace(' cmp #0\n bne ModelPipeline_EntryBad\n lda #7\n jsl SourceWorldTick4086_Ack\n bcs ModelPipeline_EntryBad',' cmp #8\n bne ModelPipeline_EntryBad')
    import re
    serial=[0]
    def relax(m):
        serial[0]+=1;label='ModelPipeline_EntryGuard'+str(serial[0])
        return ' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[m[1]]+' '+label+'\n jmp '+m[2]+'\n'+label+':\n.a16\n.i16'
    wrapper=re.sub(r'^ (beq|bne|bcc|bcs) (ModelPipeline_\w+)$',relax,wrapper,flags=re.M)
    wrapper=re.sub(r'^ bra (ModelPipeline_\w+)$',r' jmp \1',wrapper,flags=re.M)
    for name in sorted(sy,key=len,reverse=True):
        if name.startswith('Source'):wrapper=__import__('re').sub(r'\b'+name+r'\b',str(sy[name]),wrapper)
    assembly=wrapper+pipeline(sy)+callbacks(sy,1)+callbacks(sy)+scalars(reports['scalars'],styles,sy)+palettes(reports['palettes'],sy,3)+palettes(reports['palettes'],sy)+scripts(sy)+run(rw,rh,reports['run'],sy,copy_entry='SourceRunTuple_EntityCopyOriginal')+emit_entity_copy_bridge(rw,sy)+'\nModelPipeline_CodeEnd:\n.a16\n.i16\n'
    if a.generic_frame_owner:
        from source_frame_model_owner_native import emit as frame_models
        assembly+=frame_models(sy)
    if a.generic_timed_owner:
        from source_frame_model_owner_native import emit_timed
        assembly+=emit_timed(sy,world_relative=a.world_issued_animation)
    if a.generic_world_owner:
        from source_world_model_owner_native import emit as world_models
        assembly+=world_models(sy)
    if a.world_issued_animation:
        from source_timed_world_geometry_native import emit as timed_geometry
        assembly+=timed_geometry(sy)
    if a.fast_animation_copy:
        from source_model_animation_copy_fast_native import emit as fast_copy
        assembly+=fast_copy(sy,copy_loop=a.fast_animation_inheritance)
    lua='local data='+luav({k:list(v)for k,v in data.items()if k in('core','animation_cache','weapon_cache','policy','timing')})+'\nlocal reports='+luav({k:reports[k]for k in('scripts','factors','lifecycle','policy','timing','body','offscreen','death','scalars','run')})+'\nlocal address='+luav(addresses)+'\nlocal extra='+luav({k:v for k,v in sy.items()if k.startswith('SourceForeignWork_')or k.startswith(('StageFp_','StreamScrollFp_'))or k in('DmaQueue',)})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
    lua+=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(i*8))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local function bytes(a,b)for i,v in ipairs(b)do emu.write(a+i-1,v,mt)end end
local ranges={{0x40b000,2560},{0x40ba00,512},{0x40c000,12288},{0x414000,18432},{0x409000,8192},{0x418800,24576},{0x432800,4096},{0x433800,8192},{0x439000,10240},{0x43b900,512},{0x43c000,CACHEBYTES},{0x42f400,3072},{0x438800,1792},{0x435980,1056},{0x40bdcc,352},{0x43d600,512},{0x43e200,2048},{STYLES,512},{HANDLES,256}}
local before,cpu,trace,ctx={}, {},{},0;local begin_clock,begin_field=0,0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];trace={};put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,165,mt)end end
 bytes(0x40b000,data.core);bytes(0x40ba00,data.weapon_cache);bytes(0x43c000,data.animation_cache)
 for i=17,#data.policy do emu.write(0x40bc00+i-17,data.policy[i],mt)end
 for i=29,#data.timing do emu.write(0x40bd00+i-29,data.timing[i],mt)end
 local v=0x414000+c.slot*80;local side=0x416800+c.slot*64;local core=0x40c000+c.slot*96;local rel=0x409000+c.slot*64;local body=0x433800+c.slot*64
 put(v,v,4);put(v+4,1,4);put(v+16,1,4);put(v+20,c.role,4);put(v+32,1,4);put(v+36,c.hp,4);put(v+40,1,4);put(v+44,0,4);put(v+64,1,4);put(v+68,c.maxhp,4);bytes(core,c.initial_core)
 put(side,c.old);put(side+2,DEFAULTMODEL);put(side+4,c.source_event.frame_handle);put(side+6,c.frame)
 for i=0,63 do emu.write(rel+i,0,mt)end
 for i=0,3 do local r=0x418800+i*64;put(r,i<2 and v or 0x414000+((c.slot+1)%128)*80,4);put(r+4,i%2+1);put(r+6,3);put(r+8,1,4);put(r+12,100+i,4);for j=0,2 do emu.write(r+16+j,107+j,mt)end end
 put(rel+44,reports.scripts.models[c.old+1].initialized_mask,4)
 put(body+48,c.map);put(body+50,c.old);put(body+62,0xb5c2);put(side+30,reports.scalars.models[c.old+1].alpha)
 put(0x439048+c.slot*80,c.old);put(0x43904a+c.slot*80,0xb4fb)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_TemplateCount',16)
 set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,name in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do put(sy[name],0)end
 for i=0,7 do put(sy.DmaQueue+i*8+4,0)end
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',16);set('SourceModelEntityCopy4086_Entities',128)
 set('SourceModelCachedCopy4086_Ready',0xb4ee);set('SourceModelCachedCopy4086_Models',16)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',MAXIMUM);set('SourceModelAnimationCopy4086_Bytes',CACHEBYTES)
 set('SourceModelAnimation4086_Ready',0xb4ef);set('SourceModelAnimation4086_State',0);set('SourceModelAnimation4086_TimeLo',48);set('SourceModelAnimation4086_TimeHi',0);set('SourceModelAnimation4086_DelayPolicy',1)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',0x8000);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',AIBYTES);set('SourceAnimationInit4086_Issued',0)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',ANIMATIONS)
 set('SourceFrameStack4086_Ready',0);set('SourceWorldTick4086_Ready',0)
 set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Slot',c.slot);set('SourceScriptClone4086_Model',c.old);set('SourceScriptClone4086_Base',address.scripts);set('SourceScriptClone4086_Bank',58);set('SourceScriptClone4086_Bytes',SCRIPTBYTES);set('SourceScriptClone4086_Models',16)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_Base',address.callbacks);set('SourceAnimationCallback4086_Bank',58);set('SourceAnimationCallback4086_Bytes',CALLBACKBYTES);set('SourceAnimationCallback4086_Models',16);set('SourceAnimationCallback4086_Programs',PROGRAMS)
 set('SourceFactors4086_Ready',0xb5f1);set('SourceFactors4086_Status',0);set('SourceFactors4086_Base',address.factors);set('SourceFactors4086_Bank',58);set('SourceFactors4086_Bytes',FACTORBYTES);set('SourceFactors4086_Models',16);set('SourceFactors4086_Attacks',20)
 set('SourceCtorState4086_Ready',0xb5c2);set('SourceCtorState4086_Models',16)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',0);set('SourceLifecycle4086_Base',address.lifecycle);set('SourceLifecycle4086_Bank',58);set('SourceLifecycle4086_Bytes',LIFEBYTES);set('SourceLifecycle4086_Models',16)
 set('SourceModelAttackPolicy4086_Ready',0xb5f0);set('SourceModelAttackPolicy4086_Models',16);set('SourceModelAttackPolicy4086_Status',0)
 set('SourceAttackTiming4086_Ready',0xb603);set('SourceAttackTiming4086_Status',0);set('SourceAttackTiming4086_Models',16);set('SourceAttackTiming4086_Base',address.timing);set('SourceAttackTiming4086_Bank',58);set('SourceAttackTiming4086_Bytes',TIMINGBYTES)
 set('SourceAttackBody4086_Ready',0xb605);set('SourceAttackBody4086_Status',0);set('SourceAttackBody4086_Base',address.body);set('SourceAttackBody4086_Bank',58);set('SourceAttackBody4086_Bytes',BODYBYTES);set('SourceAttackBody4086_Models',16)
 set('SourceOffscreenState4086_Ready',0xb610);set('SourceOffscreenState4086_Base',address.offscreen);set('SourceOffscreenState4086_Bank',58);set('SourceOffscreenState4086_Bytes',OFFSCREENBYTES);set('SourceOffscreenState4086_Models',16)
 set('SourceAttackCostState4086_Ready',0xb609);set('SourceMovementState4086_Ready',0xb60b);set('SourceAutokillState4086_Ready',0xb60e)
 set('SourceDeathFields4086_Ready',0xb638);set('SourceDeathFields4086_Base',address.death);set('SourceDeathFields4086_Bank',58);set('SourceDeathFields4086_Bytes',DEATHBYTES);set('SourceDeathFields4086_Models',16)
 set('SourceModelTransition4086_Ready',0xb4f0);set('SourceModelTransition4086_State',0);set('SourceModelTransition4086_Service',0);set('SourceModelTransition4086_Slot',c.slot)
 set('SourceWeapon4086_Ready',0xb4f1);set('SourceWeapon4086_Status',0);set('SourceWeapon4086_Slot',c.slot);put(sy.SourceWeapon4086_NumberLo,c.number,4);put(sy.SourceWeapon4086_AnimFlagLo,c.keep,4);set('SourceWeapon4086_Base',address.weapon);set('SourceWeapon4086_Bank',58);set('SourceWeapon4086_Bytes',WEAPONBYTES);set('SourceWeapon4086_Models',16);set('SourceWeapon4086_Entities',128);set('SourceWeapon4086_Players',4);put(sy.SourceWeapon4086_LevelWeaponLo,0,4)
 for i=0,11 do emu.write(0x43e200+c.slot*16+i,data.weapon_cache[c.old*32+(i<4 and i or i+4)+1],mt)end
 put(0x43e20c+c.slot*16,0,4)
 put(RUNWORK,0xb678);put(RUNWORK+2,0);put(HANDLES+c.slot*2,reports.run.models[c.old+1].initial_tuple)
 if c.bad=='script_ready'then set('SourceScriptClone4086_Ready',0)
 elseif c.bad=='script_sticky'then set('SourceScriptClone4086_Status',3)
 elseif c.bad=='script_models'then set('SourceScriptClone4086_Models',15)
 elseif c.bad=='script_table'then set('SourceScriptClone4086_Base',address.scripts+2)
 elseif c.bad=='callback_ready'then set('SourceAnimationCallback4086_Ready',0)
 elseif c.bad=='callback_models'then set('SourceAnimationCallback4086_Models',15)
 elseif c.bad=='callback_program'then set('SourceAnimationCallback4086_Base',address.callbacks+16)
 elseif c.bad=='vars'then set('VmSourceVars_Ready',0)
 elseif c.bad=='vars_bank'then set('VmSourceVars_Bank',0x40)
 elseif c.bad=='token'then put(v,0,4)
 elseif c.bad=='wide_instance'then put(rel+44,2,4)
 elseif c.bad=='onkill'then put(rel+52,1,4)
 elseif c.bad=='clear_entry'then put(rel+48,1,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local function expect(a,b)for i,v in ipairs(b)do before[a+i-1]=v end end
 local function value(a,v,n)local b={};for i=0,n-1 do b[#b+1]=(v>>(8*i))&255 end;expect(a,b)end
 if c.fault==0 then
 expect(0x40b000+c.new*160,c.wanted_cache);expect(0x40c000+c.slot*96,c.wanted_core);expect(0x43c000+c.new*MAXIMUM*2,c.wanted_animation)
 local side=0x416800+c.slot*64;local view=0x414000+c.slot*80
 value(side,c.new,2);value(side+4,c.wanted_handle,2);value(side+6,c.wanted_frame,2);value(side+8,c.wanted_nextanim,4);value(side+60,c.speed_q16,4);value(side+30,reports.scalars.models[c.new+1].alpha,2)
 value(view+36,c.wanted_hp,4);value(view+68,c.wanted_maxhp,4);value(view+72,reports.death.models[c.new+1].score,4);value(view+76,word(0x40b04c+c.new*160)|(word(0x40b04e+c.new*160)<<16),4)
 value(0x433830+c.slot*64,0,2);value(0x433832+c.slot*64,c.new,2);value(STYLES+c.slot*4,reports.scalars.models[c.new+1].combostyle,4)
 value(0x40902c+c.slot*64,reports.scripts.models[c.new+1].initialized_mask,4);value(0x409038+c.slot*64,c.new,2);value(0x40903a+c.slot*64,0xb638,2)
 value(HANDLES+c.slot*2,reports.run.models[c.new+1].initial_tuple,2)
 local lf=reports.lifecycle.models[c.new+1].fields;local l=0x439000+c.slot*80
 value(l+48,lf.subtype,4);value(l+52,lf.nomove,4);value(l+56,lf.makeinv,4);value(l+60,lf.priority,4);expect(l+64,LIFE_KNOCKDOWN[c.new+1]);value(l+68,1,4);value(l+72,c.new,2);value(l+74,0xb4fb,2);value(l+76,0xb508,2)
 for i=0,15 do before[0x42f408+c.slot*24+i]=emu.read(0x40bc00+c.new*16+i,mt)end
 for i=0,11 do before[0x438800+c.slot*14+i]=emu.read(0x40bd00+c.new*12+i,mt)end;value(0x43880c+c.slot*14,0xb603,2)
 expect(0x432800+c.slot*32,FACTOR_VECTORS[c.new+1]);value(0x43b900+c.slot*4,c.new,2);value(0x43b902+c.slot*4,0xb5f1,2)
 local ab=c.slot<96 and 0x435980+c.slot*11 or 0x40bdcc+(c.slot-96)*11;expect(ab,BODY_ROWS[c.new+1]);value(ab+9,0xb605,2);value(0x43d600+c.slot*4,reports.offscreen.models[c.new+1].offscreenkill,4)
 for i=0,11 do before[0x43e200+c.slot*16+i]=data.weapon_cache[c.new*32+(i<4 and i or i+4)+1]end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1;if n<8 then emu.log('PIPELINEDIFF|'..word(INDEX)..'|'..a..'|'..emu.read(a,mt)..'|'..v)end end end
 emu.log('PIPELINERESULT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceModelTransition4086_State)..'|'..table.concat(trace,','))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();emu.log('PIPELINECOST|'..word(INDEX)..'|'..(state.masterClock-begin_clock)..'|'..(state['ppu.frameCount']-begin_field));ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=state['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(state['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();begin_clock=s.masterClock;begin_field=s['ppu.frameCount'];cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()trace[#trace+1]=word(sy.SourceModelTransition4086_Service);emu.log('PIPELINEPHASE|'..word(INDEX)..'|service'..word(sy.SourceModelTransition4086_Service)..'|'..(emu.getState().masterClock-begin_clock))end,emu.callbackType.exec,SERVICE,SERVICE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];if c.bad=='old_type'then put(sy.SourceModelTransition4086_OldTypeHi,1)end end,emu.callbackType.exec,SNAPSHOT,SNAPSHOT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local parts={};for _,name in ipairs({'SourceModelTransition4086_Service','SourceModelEntityCopy4086_Status','SourceModelCachedCopy4086_Status','SourceModelAnimationCopy4086_Status','SourceLifecycle4086_Status','SourceModelAttackPolicy4086_Status','SourceAttackTiming4086_Status','SourceAttackBody4086_Status'})do parts[#parts+1]=name..'='..word(sy[name])end
 emu.log('PIPELINEFAULT|'..table.concat(parts,','))
end,emu.callbackType.exec,FAULT,FAULT,emu.cpuType.snes,mt)
'''
    if a.frame_binding:
        lua=lua.replace(" before={};for _,r in ipairs(ranges)",''' put(sy.SourceWeapon4086_NumberLo,2147483647,4);set('SourceModelTransition4086_New',65535)
 set('SourceIdle4086_Ready',0xb4f3);put(0x43eb1c+c.slot*32,0,4)
 set('SourceFrameEffectBinding4086_Ready',0xb4f5)
 set('SourceFrameEffectPlan4086_Ready',0xb4f2);set('SourceFrameEffectPlan4086_State',0);set('SourceFrameEffectPlan4086_Base',address.plan);set('SourceFrameEffectPlan4086_Bank',58);set('SourceFrameEffectPlan4086_Bytes',PLANBYTES);set('SourceFrameEffectPlan4086_Animations',ANIMATIONS)
 set('SourceFrameEffectPlan4086_PairedCrcLo',PLANPAIREDLO);set('SourceFrameEffectPlan4086_PairedCrcHi',PLANPAIREDHI);set('SourceFrameEffectPlan4086_BodyCrcLo',PLANBODYLO);set('SourceFrameEffectPlan4086_BodyCrcHi',PLANBODYHI)
 set('SourceUpdateFrame4086_State',1);set('SourceUpdateFrame4086_Pending',2);set('SourceUpdateFrame4086_Slot',c.slot);set('SourceUpdateFrame4086_Handle',c.source_event.frame_handle);set('SourceUpdateFrame4086_Request',c.source_event.frame);set('SourceUpdateFrame4086_Count',c.effect_count);set('SourceUpdateFrame4086_AnimationData',0x8000+c.effect_offset)
 before={};for _,r in ipairs(ranges)''')
        lua=lua.replace(" emu.log('PIPELINERESULT|'",''' if c.fault==0 and (word(sy.SourceFrameEffectPlan4086_Index)~=2 or word(sy.SourceFrameEffectPlan4086_Service)~=4 or word(sy.SourceFrameEffectBinding4086_State)~=0)then n=n+1 end
 emu.log('PIPELINERESULT|' ''')
        for k,v in dict(PLANBYTES=len(plan),PLANPAIREDLO=struct.unpack_from('<H',plan,24)[0],PLANPAIREDHI=struct.unpack_from('<H',plan,26)[0],PLANBODYLO=struct.unpack_from('<H',plan,28)[0],PLANBODYHI=struct.unpack_from('<H',plan,30)[0]).items():lua=lua.replace(k,str(v))
    if a.frame_prefix:
        lua=lua.replace(" before={};for _,r in ipairs(ranges)",''' set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,0x414000+80*((c.slot+1)%128),4)
 emu.write(sy.VmState_Status,0,mt);set('VmState_Error',0);put(sy.VmSourceWorld_Time,48,4)
 put(0x41f510+c.slot*20,0);set('SourceFrameMotion4086_Ready',0)
 before={};for _,r in ipairs(ranges)''')
        lua=lua.replace(" if c.fault==0 and (word(sy.SourceFrameEffectPlan4086_Index)"," if word(sy.SourceSelf4086_Active)~=1 or word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*c.slot then n=n+1 end\n if c.fault==0 and (word(sy.SourceFrameEffectPlan4086_Index)")
    if a.effects_owner:
        lua=lua.replace('local ranges={{','local ranges={{0x41f500,2560},{0x43eb00,4096},{0x43e000,512},{')
        lua=lua.replace(" before={};for _,r in ipairs(ranges)",''' set('SourceFrameMotion4086_Ready',0xb4e8);set('VmSourceWorld_Level',0)
 put(v+24,1,4);put(v+28,1,4);for i=0,31 do emu.write(0x43eb00+c.slot*32+i,0,mt)end
 for i=0,19 do emu.write(0x41f500+c.slot*20+i,0,mt)end
 before={};for _,r in ipairs(ranges)''')
        lua=lua.replace(" value(side,c.new,2);",''' value(side+4,c.wanted_idle_handle,2);value(view+20,0,4);value(0x40c054+c.slot*96,11,4);value(0x40c058+c.slot*96,0,4)
 if c.new_cached_type~=0 then value(side+36,0,4);value(side+40,0,4)end
 value(0x43eb00+c.slot*32,3,4);for i=4,15 do before[0x43eb00+c.slot*32+i]=0 end
 value(0x43e000+(c.wanted_idle_handle-1)*4,0,4);value(0x41f510+c.slot*20,1,2)
 value(side,c.new,2);''')
        lua=lua.replace('value(side+4,c.wanted_handle,2);','')
        lua=lua.replace('word(sy.SourceFrameEffectBinding4086_State)~=0','word(sy.SourceFrameEffectBinding4086_State)~=2 or word(sy.SourceAnimationInit4086_State)~=1 or word(sy.SourceAnimationInit4086_Handle)~=c.wanted_idle_handle or word(sy.SourceUpdateFrame4086_Handle)~=c.source_event.frame_handle or word(sy.SourceUpdateFrame4086_Request)~=c.source_event.frame')
    if a.nested_idle:
        install=''' bytes(sy.VmCode_Wram,SCRIPTMETADATA)
 set('SourceFrameStack4086_Ready',0xb4ed);set('SourceFrameStack4086_Depth',0);set('SourceFrameStack4086_Fault',0)
 set('SourceAnimationCallback4086_State',0);set('SourceVMRun4086_Ready',0xb4d7);set('SourceVMRun4086_Busy',0)
 set('VmSourceCallback_Ready',0xb4a5);set('VmSourceCallback_Active',0);set('VmSourceCallback_Request',0)
 set('VmSourceFrame_Ready',0xb4fd);set('VmSourceFrame_Base',DISPATCHBASE);set('VmSourceFrame_Bank',38);set('VmSourceFrame_Bytes',DISPATCHBYTES);set('VmSourceFrame_Programs',PROGRAMS);set('VmSourceFrame_Handles',ANIMATIONS);set('VmSourceFrame_Pending',0)
 set('VmSourceModels_Ready',0xb4a1);set('VmSourceModels_Base',REGISTRYBASE);set('VmSourceModels_Bank',38);set('VmSourceModels_Count',16);set('VmSourceModels_Bytes',REGISTRYBYTES)
 for i=0,63 do emu.write(sy.VmSourceModels_Loaded+i,i<2 and 255 or 0,mt)end
 set('VmSourceEntity_Ready',0xb48b);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',128)
 set('VmSourceMutation_Ready',0xb4a2);set('VmNativeVariant_ContextValid',0)
 set('VmSourceInstr_Ready',0xb48e);set('VmSourceInstr_Base',0x8000);set('VmSourceInstr_Bank',38)
 set('VmPriv_InstrOff',0);set('VmCall_CallsitesOff',CALLSITES);set('VmCall_ArgSlotsOff',ARGS);set('VmStr_StringsOff',STRINGS)
 set('VmState_InstrCount',INSTRUCTIONS);set('VmState_SlotCount',SLOTS);set('VmState_FrameTop',0)
 set('SourceFrameEffectLeaf4086_Ready',0xb4f4)
 before={};for _,r in ipairs(ranges)'''
        vals=dict(SCRIPTMETADATA=luav(list(metadata)),DISPATCHBASE=script_address['dispatch'],DISPATCHBYTES=len(dispatch),REGISTRYBASE=script_address['registry'],REGISTRYBYTES=len(registry),CALLSITES=offs[2],ARGS=offs[3],STRINGS=offs[4],INSTRUCTIONS=len(code)//8,SLOTS=struct.unpack_from('<H',metadata,10)[0])
        import re
        for k,v in vals.items():install=re.sub(r'\b'+k+r'\b',str(v),install)
        lua=lua.replace(' bytes(0x40b000,data.core);',' for i=0,24575 do emu.write(0x418800+i,0,mt)end\n bytes(0x40b000,data.core);')
        lua=lua.replace(" before={};for _,r in ipairs(ranges)",install)
        lua=lua.replace(' value(side+4,c.wanted_idle_handle,2);', ''' for i,name in ipairs({'self','frame','animnum','animhandle'})do local at=0x418800+(i+3)*64;value(at,view,4);value(at+4,1,2);value(at+6,#name,2);for j=1,#name do before[at+15+j]=name:byte(j)end end
 value(side+4,c.wanted_idle_handle,2);''')
        for phase,label in [('callbackBegin','SourceAnimationCallback4086_Begin'),('callbackRun','SourceAnimationCallback4086_Run'),('callbackEnd','SourceAnimationCallback4086_Done'),('cachedCopy','SourceModelCachedCopy4086_Apply'),('animationCopy','SourceModelAnimationCopy4086_Apply'),('entityCopy','SourceModelEntityCopy4086_Apply'),('lifecycle','SourceLifecycle4086_Apply'),('attackPolicy','SourceModelAttackPolicy4086_Apply'),('attackTiming','SourceAttackTiming4086_CopyEntity'),('attackBody','SourceAttackBody4086_CopyEntity'),('offscreen','SourceOffscreenState4086_ApplyModel'),('deathFields','SourceDeathFields4086_Copy'),('weaponMetadata','SourceWeapon4086_InstallMetadata')]:
            lua+='\nemu.addMemoryCallback(function()emu.log("PIPELINEPHASE|"..word(INDEX).."|'+phase+'|"..(emu.getState().masterClock-begin_clock))end,emu.callbackType.exec,'+str(sy[label])+','+str(sy[label])+',emu.cpuType.snes,mt)\n'
        lua+='\nemu.addMemoryCallback(function()emu.log("NESTEDFAULT|"..word(INDEX).."|error="..word(sy.VmState_Error).."|callback="..word(sy.SourceAnimationCallback4086_Fault).."|vm="..word(sy.SourceVMRun4086_Status).."|context="..word(sy.VmNativeVariant_ContextValid))end,emu.callbackType.exec,'+str(sy['SourceAnimationCallback4086_Bad'])+','+str(sy['SourceAnimationCallback4086_Bad'])+',emu.cpuType.snes,mt)\n'
        lua=lua.replace('value(side+6,c.wanted_frame,2);value(side+8,c.wanted_nextanim,4);','value(side+6,0,2);value(side+8,c.wanted_idle_nextanim,4);')
        lua=lua.replace(" if word(sy.SourceSelf4086_Active)~=1 or word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*c.slot then n=n+1 end", " if c.fault==0 and (word(sy.SourceSelf4086_Active)~=0 or word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*((c.slot+1)%128) or word(sy.SourceFrameStack4086_Depth)~=0 or word(sy.SourceFrameStack4086_Fault)~=0)then n=n+1 end")
        start=lua.index(' if c.fault==0 and (word(sy.SourceFrameEffectPlan4086_Index)');end=lua.index(" emu.log('PIPELINERESULT|'",start)
        lua=lua[:start]+''' if c.fault==0 and (word(sy.SourceUpdateFrame4086_State)~=2 or word(sy.SourceUpdateFrame4086_Pending)~=0 or word(sy.SourceFrameEffectPlan4086_State)~=2 or word(sy.SourceFrameEffectPlan4086_Service)~=0 or word(sy.SourceUpdateFrame4086_Handle)~=c.source_event.frame_handle or word(sy.SourceUpdateFrame4086_Request)~=c.source_event.frame)then n=n+1 end
'''+lua[end:]
    if a.animated_parent:
        lua=lua.replace(' for i=0,19 do emu.write(0x41f500+c.slot*20+i,0,mt)end',' for i=0,19 do emu.write(0x41f500+c.slot*20+i,0,mt)end;put(0x41f510+c.slot*20,1)')
    if a.warm_parent:
        lua+='\nemu.addMemoryCallback(function()local s=emu.getState();emu.log("PIPELINEWARM|"..word(INDEX).."|"..(s.masterClock-begin_clock).."|"..(s["ppu.frameCount"]-begin_field));begin_clock=s.masterClock;begin_field=s["ppu.frameCount"]end,emu.callbackType.exec,WARM,WARM,emu.cpuType.snes,mt)\n'
    if a.timed_weapon:
        install=''' set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',7);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_View',0x4000+c.slot*80);set('SourceWorldTick4086_Side',0x6800+c.slot*64);put(sy.SourceWorldTick4086_TimeLo,48,4)
 put(sy.SourceSelf4086_GlobalLow,v,4);set('SourceFreeze4086_Ready',0xb5df)
 set('SourceUpdateAnimationPrefix4086_Ready',0xb60d);set('SourceUpdateAnimationPrefix4086_Status',0);set('SourceUpdateAnimationPrefix4086_Base',address.animation_prefix);set('SourceUpdateAnimationPrefix4086_Bank',58);set('SourceUpdateAnimationPrefix4086_Bytes',UPBYTES);set('SourceUpdateAnimationPrefix4086_Models',16);set('SourceUpdateAnimationPrefix4086_SleepID',SLEEPID)
 set('SourceUpdateAnimation4086_Ready',0xb60f);set('SourceUpdateAnimation4086_State',0);set('SourceUpdateAnimation4086_Base',address.animation_timing);set('SourceUpdateAnimation4086_Bank',58);set('SourceUpdateAnimation4086_Bytes',TTBYTES)
 put(side+6,c.source_event.frame-1);put(side+8,48,4);put(side+16,0,4)
 for i=0,47 do emu.write(0x439000+c.slot*80+i,0,mt)end
 for i=0,39 do emu.write(0x42e000+c.slot*40+i,0,mt)end
 put(0x43d800+c.slot*4,0,4)
 before={};for _,r in ipairs(ranges)'''
        install=install.replace('UPBYTES',str(len(up))).replace('TTBYTES',str(len(tt))).replace('SLEEPID',str(update_report['sleep_animation_id']))
        lua=lua.replace(" before={};for _,r in ipairs(ranges)",install)
        lua=lua.replace(' value(side+4,c.wanted_idle_handle,2);',' value(0x43eb18+c.slot*32,c.wanted_sleep_deadline,4);\n value(side+4,c.wanted_idle_handle,2);')
        lua=lua.replace('word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*((c.slot+1)%128)', 'word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*c.slot')
        lua=lua.replace(" if c.fault==0 and (word(sy.SourceUpdateFrame4086_State)"," if word(sy.SourceUpdateAnimation4086_State)~=2 or word(sy.SourceUpdateAnimation4086_Action)~=1 or word(sy.SourceWorldTick4086_Phase)~=7 or word(sy.SourceWorldTick4086_Pending)~=1 then n=n+1 end\n if c.fault==0 and (word(sy.SourceUpdateFrame4086_State)")
        lua+='\nemu.addMemoryCallback(function()emu.log("TIMEDFAULT|"..word(INDEX).."|prefix="..word(sy.SourceUpdateAnimationPrefix4086_Status).."|frame="..word(sy.SourceUpdateFrame4086_State))end,emu.callbackType.exec,'+str(sy['SourceUpdateAnimation4086_Bad'])+','+str(sy['SourceUpdateAnimation4086_Bad'])+',emu.cpuType.snes,mt)\n'
    if a.timed_world_ack:
        lua=lua.replace('word(sy.SourceWorldTick4086_Pending)~=1','word(sy.SourceWorldTick4086_Pending)~=0 or word(sy.SourceWorldTick4086_Fault)~=0')
    if a.world_issued_animation:
        lua=lua.replace(" before={};for _,r in ipairs(ranges)",''' set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Pending',0);set('SourceWorldTick4086_Index',0);set('SourceWorldTick4086_Maximum',1)
 set('SourceWorldTick4086_View',0xdead);set('SourceWorldTick4086_Side',0xbeef);put(0x41f200,c.slot)
 set('SourceUpdateAnimation4086_State',2);set('SourcePostStationary4086_Ready',0);set('SourcePostAir4086_Ready',0)
 before={};for _,r in ipairs(ranges)''')
    if a.timed_guards:
        lua=lua.replace(" before={};for _,r in ipairs(ranges)",''' set('SourceUpdateAnimation4086_Slot',c.slot);set('SourceUpdateAnimation4086_Side',0x6800+c.slot*64);put(sy.SourceUpdateAnimation4086_TimeLo,48,4)
 if c.bad=='timed_tick_ready'then set('SourceWorldTick4086_Ready',0)
 elseif c.bad=='timed_world_ready'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='timed_world_fault'then set('SourceWorldTick4086_Fault',1)
 elseif c.bad=='timed_world_time'then put(sy.SourceWorldTick4086_TimeLo,49,4)
 elseif c.bad=='timed_phase'then set('SourceWorldTick4086_Phase',6)
 elseif c.bad=='timed_pending'then set('SourceWorldTick4086_Pending',0)
 elseif c.bad=='timed_state'then set('SourceWorldTick4086_State',2)
 elseif c.bad=='timed_timed_ready'then set('SourceUpdateAnimation4086_Ready',0)
 elseif c.bad=='timed_canvas_generation'then put(sy.SourceForeignWork_Generation,2,4)
 elseif c.bad=='timed_captured_slot'then set('SourceUpdateAnimation4086_State',1);set('SourceUpdateAnimation4086_Slot',(c.slot+1)%128)
 elseif c.bad=='timed_captured_time'then set('SourceUpdateAnimation4086_State',1);put(sy.SourceUpdateAnimation4086_TimeLo,49,4)
 elseif c.bad=='timed_captured_side'then set('SourceUpdateAnimation4086_State',1);set('SourceUpdateAnimation4086_Side',0x6802+c.slot*64)
 elseif c.bad=='timed_captured_frame_slot'then set('SourceUpdateAnimation4086_State',1);set('SourceUpdateFrame4086_Slot',(c.slot+1)%128)
 elseif c.bad=='timed_done_slot'then set('SourceUpdateAnimation4086_State',2);set('SourceUpdateAnimation4086_Slot',(c.slot+1)%128)end
 before={};for _,r in ipairs(ranges)''')
        lua=lua.replace(' if word(sy.SourceUpdateAnimation4086_State)~=2 or word(sy.SourceUpdateAnimation4086_Action)~=1 or word(sy.SourceWorldTick4086_Phase)~=7 or word(sy.SourceWorldTick4086_Pending)~=1 then n=n+1 end','')
    if a.generic_world_owner:
        lua=lua.replace('word(sy.SourceWorldTick4086_Phase)~=7 or word(sy.SourceWorldTick4086_Pending)~=0','word(sy.SourceWorldTick4086_Phase)~=8 or word(sy.SourceWorldTick4086_Pending)~=1')
    if a.world_issued_guards:
        lua+='''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.bad=='world_side'then set('SourceWorldTick4086_Side',c.slot*64+2)
 elseif c.bad=='world_view'then set('SourceWorldTick4086_View',c.slot*80+2)
 elseif c.bad=='resume_side'then set('SourceUpdateAnimation4086_State',1);set('SourceUpdateAnimation4086_Slot',c.slot);put(sy.SourceUpdateAnimation4086_TimeLo,48,4);set('SourceUpdateAnimation4086_Side',0x6802+c.slot*64);set('SourceUpdateFrame4086_Slot',c.slot)
 elseif c.bad=='resume_frame'then set('SourceUpdateAnimation4086_State',1);set('SourceUpdateAnimation4086_Slot',c.slot);put(sy.SourceUpdateAnimation4086_TimeLo,48,4);set('SourceUpdateAnimation4086_Side',0x6800+c.slot*64);set('SourceUpdateFrame4086_Slot',(c.slot+1)%128)end
end,emu.callbackType.exec,ISSUED,ISSUED,emu.cpuType.snes,mt)
'''
        lua=lua.replace(' if word(sy.SourceUpdateAnimation4086_State)~=2 or word(sy.SourceUpdateAnimation4086_Action)~=1 or word(sy.SourceWorldTick4086_Phase)~=7 or word(sy.SourceWorldTick4086_Pending)~=0 or word(sy.SourceWorldTick4086_Fault)~=0 then n=n+1 end','')
    lua='local LIFE_KNOCKDOWN='+luav([list(struct.pack('<f',m['fields']['knockdowncount']))for m in reports['lifecycle']['models']])+'\nlocal FACTOR_VECTORS='+luav([list(bytes.fromhex(m['vector_hex']))for m in reports['factors']['models']])+'\nlocal BODY_ROWS='+luav([list(data['body'][16+i*9:25+i*9])for i in range(16)])+'\n'+lua
    values=dict(CACHEBYTES=len(data['animation_cache']),MAXIMUM=maximum,AIBYTES=len(data['animations']),FEBYTES=len(data['effects']),ANIMATIONS=len(reports['animations']['animations']),SCRIPTBYTES=len(data['scripts']),CALLBACKBYTES=len(data['callbacks']),PROGRAMS=reports['callbacks']['program_count'],FACTORBYTES=len(data['factors']),LIFEBYTES=len(data['lifecycle']),BODYBYTES=len(data['body']),OFFSCREENBYTES=len(data['offscreen']),DEATHBYTES=len(data['death']),TIMINGBYTES=len(data['timing']),WEAPONBYTES=len(data['weapon']),DEFAULTMODEL=rows[0]['old'],STYLES=styles,HANDLES=rh,RUNWORK=rw)
    import re
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    def hook(raw,linked):
        from m4_input_controller_native import offset
        if a.fast_animation_copy:
            at=offset(sy['SourceModelAnimationCopy4086_Preflight'])
            expected=b'\xaf'+struct.pack('<I',sy['SourceModelAnimationCopy4086_OldOffset'])[:3]+b'\x18'
            if raw[at:at+5]!=expected or linked['ModelAnimationFast_Done']>>16!=39:raise ValueError('ANIMATION_FAST_PREFLIGHT_HOOK')
            raw[at:at+5]=b'\x5c'+struct.pack('<I',linked['ModelAnimationFast_Preflight'])[:3]+b'\xea'
        if a.fast_animation_inheritance:
            at=offset(sy['SourceModelAnimationCopy4086_Copy'])
            if raw[at:at+5]!=b'\xaf'+struct.pack('<I',sy['SourceModelAnimationCopy4086_NewOffset'])[:3]+b'\x18' or linked['ModelAnimationFast_CopyDone']>>16!=39:raise ValueError('ANIMATION_FAST_COPY_HOOK')
            raw[at:at+5]=b'\x5c'+struct.pack('<I',linked['ModelAnimationFast_Copy'])[:3]+b'\xea'
        at=offset(sy['SourceModelEntityCopy4086_Apply'])
        if raw[at:at+5]!=bytes.fromhex('08 c2 38 da 5a'):raise ValueError('MODEL_PIPELINE_COPY_HOOK')
        raw[at:at+5]=b'\x5c'+struct.pack('<I',linked['SourceRunTuple_EntityCopyBridge'])[:3]+b'\xea'
        if a.generic_world_owner and linked['WorldModelOwner_Bad']>>16!=39:raise ValueError('WORLD_MODEL_OWNER_CODE_BANK')
        if a.world_issued_animation and linked['TimedWorldGeometry_CodeEnd']>>16!=39:raise ValueError('TIMED_GEOMETRY_CODE_BANK')
        if a.generic_timed_owner and linked['ModelTimedFrameOwner_Bad']>>16!=39:raise ValueError('MODEL_TIMED_FRAME_OWNER_BANK')
        if a.generic_frame_owner and linked['ModelFrameOwner_Bad']>>16!=39:raise ValueError('MODEL_FRAME_OWNER_CODE_BANK')
        if linked['SourceRunTuple_EntityCopyOriginal']>>16!=39 or linked['ModelPipeline_CodeEnd']>>16!=39:raise ValueError('MODEL_PIPELINE_CODE_BANK')
    r=Reporter('M4-MODEL-SERVICES-PIPELINE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'ModelPipeline_Apply','SourceModelTransition4086_Ready',0xb4f0,script_tables+[(58,0,bytes(small)),(59,0,data['animations']),(60,0,data['effects'])],lua,r,batch_size=4,append=assembly,rom_transform=hook,probes={**({'ISSUED':'ModelPipeline_WorldIssued'}if a.world_issued_guards else{}),**({'WARM':'ModelPipeline_WarmComplete'}if a.warm_parent else{}),'SERVICE':'ModelPipeline_Loop','FAULT':'ModelPipeline_Bad','SNAPSHOT':'ModelSnapshotService_BeginAbsent'},link_pcm=False)
    r.check('bank 0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768])
    results=[line.split('PIPELINERESULT|',1)[1].split('|')for line in log.splitlines()if 'PIPELINERESULT|'in line]
    r.check('actual weapon resolve, all six native services, exact copied source state and unchanged foreign rows/variables/CPU',results==[[str(i),'0','0','0'if a.timed_guards or a.world_issued_guards else'3'if c['fault']else'2',''if a.timed_guards or a.world_issued_guards else'1'if c['fault']else'1,2,3,5,6,7,0']for i,c in enumerate(rows)])
    costs=[list(map(int,line.split('PIPELINECOST|',1)[1].split('|')))for line in log.splitlines()if 'PIPELINECOST|'in line]
    phases=[line.split('PIPELINEPHASE|',1)[1].split('|')for line in log.splitlines()if 'PIPELINEPHASE|'in line]
    r.check('native cost samples complete',len(costs)==len(rows))
    warm_costs=[list(map(int,line.split('PIPELINEWARM|',1)[1].split('|')))for line in log.splitlines()if 'PIPELINEWARM|'in line]
    report=dict(generic_world_model_owner=a.generic_world_owner,unimplemented_attack_phase_returned=a.generic_world_owner,world_issued_geometry_guards=a.world_issued_guards,geometry_authority_sha256={n:hashlib.sha256(Path('src/core/vm/'+n+'.pasm').read_bytes()).hexdigest()for n in ('vm_source_update_animation','vm_source_update_animation_prefix','vm_source_world_tick')}if a.world_issued_animation else None,world_relative_geometry=a.world_issued_animation,private_geometry_operator=a.world_issued_animation,actual_world_phase7_issue=a.world_issued_animation,prior_world_phases_installed_by_fixture=a.world_issued_animation,timed_entry_guards=a.timed_guards,actual_world_phase7_ack=a.timed_world_ack,early_phase7_completion_guard_executed=a.timed_world_ack,full_world_tick_committed=False,generic_timed_frame_owner=a.generic_timed_owner,actual_timed_animation_owner=a.timed_weapon,world_phase_installed_by_fixture=a.timed_weapon and not a.world_issued_animation,native_frame_zero_warmup=a.warm_parent,warmup_costs=warm_costs,cpu_phases=phases,cpu_costs=costs,fast_animation_inheritance=a.fast_animation_inheritance,fast_animation_copy=a.fast_animation_copy,generic_frame_model_owner=a.generic_frame_owner,schema='BYOR_4086_MODEL_SERVICES_PIPELINE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,bundle=manifest,all_services_native=True,observer_acknowledgements=False,source_request_registers_poisoned=a.frame_binding,source_effect_cursor_after_weapon=4 if a.frame_binding else None,update_frame_completion_bound=a.nested_idle,actual_frame_event_dispatch=a.frame_binding,update_frame_prefix_instrumented=a.frame_binding and not a.frame_prefix,actual_update_frame_begin=a.frame_prefix,actual_frame_effect_owner=a.effects_owner,actual_set_idle_prepare=a.effects_owner,animation_callback_invoked=a.nested_idle,source_animating_zero_fixture=a.frame_prefix and not a.animated_parent,actual_parent_animation_callback=a.animated_parent,idle_frame_zero_bound=a.nested_idle,pool_and_leases_installed_by_fixture=True,full_gameplay_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
