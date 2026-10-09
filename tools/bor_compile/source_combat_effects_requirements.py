"""Closed authored combat-effect requirements; unsupported scalar effects reject."""
from source_current_colourmap import derive as palettes
from source_hit_block_requirements import derive as attacks
from source_damage_inputs_4086 import derive as damage


def derive(source):
    p=palettes(source);a=attacks(source);d=damage(source)
    if any(any(v[n]for n in ('steal','seal','dot','blast','no_pain'))or v['forcemap']not in (-1,0)for v in a['attacks']):raise ValueError('COMBAT_EFFECTS_OTHER_SOURCE_BODY_REQUIRED')
    for m,di in zip(p['models'],d['models']):
        if m['id']!=di['id']or m['identity']!=di['identity']:raise ValueError('COMBAT_EFFECTS_MODEL_PAIR')
        m['nodrop']=di['fields']['nodrop']
    return dict(schema='BYOR_COMBAT_EFFECTS_REQUIREMENTS_V1',capability='SOURCE_FREEZE_UNFREEZE_NO_STEAL_SEAL_DOT',palette_requirements=p,models=p['models'],attacks=a['attacks'],collision_table_bytes=a['collision_table_bytes'],engine_commit=p['engine_commit'],inair_policy='explicit ACCEPTED_COMPAT_Q16_16; arbitrary binary32 equivalence unclaimed',model_policy_mutators_admitted=False,full_damage_callback_bound=False,no_color_reduction=True)
