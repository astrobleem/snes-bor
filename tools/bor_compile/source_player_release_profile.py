"""Derive immutable animation charge durations and final source chain roles."""
from source_profile import document
from source_animation_ids import configure
from source_attack_body_profile import derive as attack_body
from script_dispatch_4086 import compile_source
from source_model_core_4086 import binary32
from source_player_release_4086 import duration

def derive(source):
    config=configure(document(source,'data/models.txt')['directives']);attacks=config['arrays']['normal_attacks'];handles=compile_source(source)['animation_handles'];models=[]
    for m in attack_body(source)['models']:
        roles={a['role']:a for a in handles if a['model']==m['identity']};active=None;charge=2.0;durations={}
        for row in document(source,m['source_path'])['directives']:
            if row['directive']=='anim':
                active=' '.join(row['values']).lower();charge=2.0
            elif row['directive']=='chargetime':
                if active is None:raise ValueError('PLAYER_RELEASE_CHARGETIME_WITHOUT_ANIMATION')
                charge=binary32(row['values'][0])
            if active in roles:durations[roles[active]['engine_animation_id']]=duration(dict(chargetime=charge))
        if 'chargeattack' in roles:raise ValueError('PLAYER_RELEASE_CHARGEATTACK_OWNER_REQUIRED')
        f=m['fields'];length=f['chainlength'];code=f['atchain'][length-1]if length else 0
        final=attacks[code-1]if 1<=code<=len(attacks)else None
        models.append(dict(id=m['index'],source_sha256=m['source_sha256'],chainlength=length,final_attack=final,final_attack_duration=durations.get(final),durations=durations,
                           missing_active_release_animation_is_source_undefined=bool(length and final not in durations)))
    return dict(capability='INTEGRAL_CHARGETIME_WIN32_X87_ABSENT_CHARGEATTACK',evaluation_policy='WIN32_X87_EXTENDED',models=models,
        source_default_chargetime=2,nonintegral_duration_admitted=False,punch_sound_service_required=True,direct_chain_and_chargetime_mutation_admitted=False,native_bound=False,motu_gameplay_proven=False)
