"""Exact source-derived nonpositive integral binary32 knockdown counter domain."""
from source_combat_effects_requirements import derive as effects
from source_lifecycle_inputs import derive as lifecycle
from source_model_factors import derive as factors
from source_damage_inputs_4086 import derive as damage


def derive(source):
    e=effects(source);l=lifecycle(source);f=factors(source);d=damage(source)
    for i,m in enumerate(e['models']):
        if any(x['models'][i]['id']!=i for x in (l,f,d)):raise ValueError('DAMAGE_DROP_MODEL_PAIR')
        if l['models'][i]['fields']['knockdowncount']!=0 or f['models'][i]['defense'][2]!=1 or d['models'][i]['fields']['animal'] or d['models'][i]['fields']['guardpoints']:raise ValueError('DAMAGE_DROP_OTHER_MODEL_BODY_REQUIRED')
    if any(a['attack_drop']not in (0,1) or a['no_pain']for a in e['attacks']):raise ValueError('DAMAGE_DROP_OTHER_ATTACK_BODY_REQUIRED')
    return dict(schema='BYOR_DAMAGE_DROP_REQUIREMENTS_V1',capability='SOURCE_ZERO_INITIAL_UNIT_KNOCKDOWN',effects=e,attack_types=f['attack_types'],counter_domain='zero and negative integral binary32 through -2**24 inclusive; subtract one at -2**24 rounds to itself, nearest ties even',factor_mutators_admitted=False,model_count_mutators_admitted=False,full_damage_callback_bound=False)
