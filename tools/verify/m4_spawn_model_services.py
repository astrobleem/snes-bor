"""Source-derived service bundle for an isolated constructor/spawn continuation.

The fixture installs leases and tables; this module does not register a profile
or supply production presentation/media ownership.
"""
import struct
from source_model_transition_bundle import compile as compile_bundle
from source_model_pipeline_native import emit as pipeline
from source_model_callback_service_native import emit as callbacks
from source_model_scalar_service_native import emit as scalars
from source_model_palette_service_native import emit as palettes
from source_model_scripts_service_native import emit as scripts
from source_run_tuple_native import emit as run,emit_entity_copy_bridge
from source_foreign_state_layout import layout
from source_model_switch_4086 import CACHED_FIELDS,ENTITY_CORE_FIELDS,ENTITY_NEGATIVE,copy_cached_defaults,copy_entity_uninitialized
from source_model_core_4086 import FLOAT_FIELDS
from m4_animation_init_native import luav


def compile(source,sy,default,number=1,role=0):
    reports,data,manifest=compile_bundle(source)
    models=reports['requirements']['models'];maximum=reports['requirements']['maximum_animations']
    ids=models[default]['weapon_ids']
    if not ids or not 1<=number<=len(ids) or ids[number-1]==default:
        raise ValueError('SPAWN_CHANGING_WEAPON_SOURCE_REQUIREMENT')
    new=ids[number-1]
    regions={r['name']:r['address'] for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']}
    small=bytearray();address={}
    for name in ('scripts','callbacks','factors','lifecycle','weapon','body','offscreen','death','timing'):
        address[name]=0x8000+len(small);small.extend(data[name]);small.extend(bytes(len(small)%2))
    if len(small)>32768:raise ValueError('SPAWN_MODEL_TABLE_BANK_CAPACITY')
    code=pipeline(sy)+callbacks(sy,1)+callbacks(sy)+scalars(reports['scalars'],regions['entity_combostyle'],sy)+palettes(reports['palettes'],sy,3)+palettes(reports['palettes'],sy)+scripts(sy)
    code+=run(regions['run_tuple_controls'],regions['entity_run_tuple'],reports['run'],sy,copy_entry='SourceRunTuple_EntityCopyOriginal')+emit_entity_copy_bridge(regions['run_tuple_controls'],sy)
    settings=dict(SourceModelAnimation4086_Ready=0xb4ef,SourceModelAnimation4086_State=0,SourceModelAnimation4086_TimeLo=48,SourceModelAnimation4086_TimeHi=0,SourceModelAnimation4086_DelayPolicy=1,SourceModelAnimation4086_Select=0,SourceModelAnimation4086_Idle=0,SourceModelAnimation4086_Spawn=23,SourceModelAnimation4086_Respawn=104,SourceModelAnimation4086_SelectAnimation=59,SourceAnimationInit4086_Issued=0,SourceModelAttackPolicy4086_Ready=0xb5f0,SourceModelAttackPolicy4086_Models=len(models),SourceModelAttackPolicy4086_Status=0,SourceAttackCostState4086_Ready=0xb609,SourceMovementState4086_Ready=0xb60b,SourceAutokillState4086_Ready=0xb60e)
    for prefix,name,magic in (('SourceScriptClone4086','scripts',0xb5c1),('SourceAnimationCallback4086','callbacks',0xb4e6),('SourceFactors4086','factors',0xb5f1),('SourceLifecycle4086','lifecycle',0xb4fb),('SourceAttackTiming4086','timing',0xb603),('SourceAttackBody4086','body',0xb605),('SourceOffscreenState4086','offscreen',0xb610),('SourceDeathFields4086','death',0xb638)):
        for suffix,value in dict(Ready=magic,Base=address[name],Bank=58,Bytes=len(data[name]),Models=len(models),Status=0).items():
            if prefix+'_'+suffix in sy:settings[prefix+'_'+suffix]=value
    settings['SourceFactors4086_Attacks']=20
    settings['SourceAnimationCallback4086_Programs']=reports['callbacks']['program_count']
    install='\n'.join(" set('"+k+"',"+str(v)+")" for k,v in settings.items())
    install+=f"\n put({regions['run_tuple_controls']},0xb678,2);put({regions['run_tuple_controls']}+2,0,2);put({regions['entity_run_tuple']}+2*slot,{reports['run']['models'][default]['initial_tuple']},2)\n"
    # Preserve actual construction/cache state. Only the source policy/timing
    # tables absent from the constructor fixture need their mutable installation.
    install+='\n copy(0x40bc00,spawn_policy);copy(0x40bd00,spawn_timing)\n'
    def model(i):
        return dict(reports['core']['models'][i]['fields'])|{'animation':{},'weapon':models[i]['weapon_ids'],'numweapons':len(models[i]['weapon_ids'] or [])}
    before=model(default);after=model(new);after['model_flag']=models[new]['model_flag'];copy_cached_defaults(before,after)
    wanted_cache=b''.join(struct.pack('<f' if f in FLOAT_FIELDS else '<i',after[f]) for f in CACHED_FIELDS)+struct.pack('<i',after['type'])
    # ent_set_model preserves the entity's original player type. Health/MP and
    # the dynamic core suffix are compared against actual pre-transition bytes.
    entity=dict(modeldata=dict(after),health=1,mp=1);copy_entity_uninitialized(entity,before)
    core={f:entity['modeldata'][f] for f in ENTITY_CORE_FIELDS};core['type']=1
    oracle=dict(model=new,cache=list(wanted_cache),core=list(b''.join(struct.pack('<i',core[f]) for f in ENTITY_CORE_FIELDS)),alpha=reports['scalars']['models'][new]['alpha'],score=reports['death']['models'][new]['score'],styles=regions['entity_combostyle'],combostyle=reports['scalars']['models'][new]['combostyle'],run=reports['run']['models'][new]['initial_tuple'],run_handles=regions['entity_run_tuple'])
    oracle['core_fallback_offsets']=[4*i for i,f in enumerate(ENTITY_CORE_FIELDS) if f in ENTITY_NEGATIVE and after[f]<0 or f in ('aimove','aiattack','risetime.rise') and after[f]==-1 or f in ('health','mp') and after[f]==0]
    animation_row=bytearray(data['animation_cache'][new*maximum*2:(new+1)*maximum*2])
    if not models[new]['model_flag']&1:
        for n in range(maximum):
            if not struct.unpack_from('<H',animation_row,2*n)[0]:
                struct.pack_into('<H',animation_row,2*n,struct.unpack_from('<H',data['animation_cache'],2*(default*maximum+n))[0])
    oracle['animation_row']=list(animation_row);oracle['maximum']=maximum
    oracle['animation_handle']=struct.unpack_from('<H',animation_row,2*role)[0]
    prelude='local spawn_policy='+luav(list(data['policy'][16:]))+'\nlocal spawn_timing='+luav(list(data['timing'][28:]))+'\nlocal spawn_wanted='+luav(oracle)+'\n'
    return dict(code=code,table=bytes(small),install=install,prelude=prelude,new=new,number=number,manifest=manifest,styles=regions['entity_combostyle'])


def transform(raw,sy,fs,offset):
    at=offset(sy['SourceModelEntityCopy4086_Apply'])
    if raw[at:at+5]!=bytes.fromhex('08 c2 38 da 5a'):raise ValueError('SPAWN_MODEL_COPY_HOOK')
    raw[at:at+5]=b'\x5c'+fs['SourceRunTuple_EntityCopyBridge'].to_bytes(3,'little')+b'\xea'
