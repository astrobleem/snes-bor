"""Compile paired inputs for source model transitions; no runtime admission.

Images and sounds have separate source identity namespaces. The sound indices
reuse the existing frame/model/engine namespace; image identities require an
explicit presentation provider before a foreign profile can be admitted.
"""
import hashlib
from compiler import key
from source_model_core_4086 import derive as core,pack as pack_core
from source_model_switch_requirements import derive as requirements,pack_animation_cache,pack_weapon_metadata
from source_sound_namespace_4086 import derive as sounds
from source_script_clone import derive as scripts,pack as pack_scripts
from script_callback_owner import derive as callbacks,pack as pack_callbacks
from source_model_factors import derive as factors,pack as pack_factors
from source_lifecycle_inputs import derive as lifecycle,pack as pack_lifecycle
from source_model_attack_policy import derive as policy,pack as pack_policy
from source_attack_timing_4086 import derive as timing,pack as pack_timing
from source_attack_body_profile import derive as body,pack_runtime as pack_body
from source_offscreen_inputs import derive as offscreen,pack as pack_offscreen
from source_death_fields_4086 import derive as death,pack as pack_death
from source_animation_init_4086 import derive as animations,pack as pack_animations
from source_frame_effects_4086 import derive as effects,pack as pack_effects
from source_run_tuple_profile import derive as run
from source_model_scalar_service_native import derive as scalars
from source_model_palette_service_native import derive as palettes,pack as pack_palettes


def compile(source):
    cr=core(source);sr=sounds(source);mr=requirements(source);images=[]
    names=sorted({key(name):name for m in cr['models']for field,name in m['media_bindings'].items()if field.startswith('icon.')}.items())
    media={key(name):i for i,name in enumerate(sr['namespace'])}
    for i,(canonical,name)in enumerate(names):
        path=source.image_path(name);raw=source.read(path)
        images.append(dict(image_index=i,source_path=path,source_sha256=hashlib.sha256(raw).hexdigest()))
        if canonical in media:raise ValueError('MODEL_MEDIA_KIND_COLLISION')
        media[canonical]=i
    reports=dict(core=cr,requirements=mr,sounds=sr,images=images,scripts=scripts(source),
                 callbacks=callbacks(source)[0],factors=factors(source),lifecycle=lifecycle(source),
                 policy=policy(source),timing=timing(source),body=body(source),offscreen=offscreen(source),
                 death=death(source),animations=animations(source),effects=effects(source),run=run(source),
                 scalars=scalars(source),palettes=palettes(source))
    identities=[(m['id'],m['identity'],m['source_sha256'])for m in cr['models']]
    for name in('scripts','factors','lifecycle','offscreen','death','scalars','palettes','run'):
        if [(m['id'],m['identity'],m['source_sha256'])for m in reports[name]['models']]!=identities:
            raise ValueError('MODEL_TRANSITION_SOURCE_PAIR:'+name)
    for name in('policy','timing','body'):
        if [(m['index'],m['identity'],m['source_sha256'])for m in reports[name]['models']]!=identities:
            raise ValueError('MODEL_TRANSITION_SOURCE_PAIR:'+name)
    weapon_cache,weapon_table=pack_weapon_metadata(mr)
    data=dict(core=pack_core(cr,media),animation_cache=pack_animation_cache(mr),weapon_cache=weapon_cache,weapon=weapon_table)
    for name,pack in dict(scripts=pack_scripts,callbacks=pack_callbacks,factors=pack_factors,lifecycle=pack_lifecycle,
                          policy=pack_policy,timing=pack_timing,body=pack_body,offscreen=pack_offscreen,death=pack_death,
                          animations=pack_animations,effects=pack_effects,palettes=pack_palettes).items():
        data[name]=pack(reports[name])
    manifest=dict(schema='BYOR_4086_MODEL_TRANSITION_BUNDLE_V1',models=identities,
                  tables={name:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())for name,raw in data.items()},
                  image_namespace=images,sound_namespace=sr,image_provider_bound=False,audio_provider_bound=False,
                  native_transition_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
    return reports,data,manifest
