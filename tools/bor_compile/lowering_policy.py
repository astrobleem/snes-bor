"""Explicit target policy after the single source-exact IR has been parsed.

Compatibility is an opt-in baseline binding, never a source dialect or a
parser option. No compatibility policy exists for an unaccepted identity.
"""
import copy
import hashlib
import json
from enum import Enum
from actor_lowering import CATEGORIES


class Profile(str, Enum):
    SOURCE_EXACT = 'SOURCE_EXACT'
    ACCEPTED_COMPAT = 'ACCEPTED_COMPAT'


def source_fingerprint(source):
    return hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def apply_policy(source, profile=Profile.SOURCE_EXACT, *, accepted=None):
    """Never edits source descriptors. All adaptations are target-only records.

    accepted must be a resolved baseline binding for this exact source model;
    verification of emitted bytes/runtime remains a separate proof obligation.
    """
    profile=Profile(profile)
    result=dict(profile=profile.value,source_fingerprint=source_fingerprint(source),
                source_identity=source['source_identity'],adaptations=[],
                target=copy.deepcopy(source),status='BLOCKED',blockers=[])
    if profile==Profile.SOURCE_EXACT:
        result['blockers']=['SOURCE_EXACT_RUNTIME_CERTIFICATION_REQUIRED']
        return result
    if (accepted is None or source['dialect']!='historical-bor' or
        tuple(accepted.get('source_identity',()))!=tuple(source['source_identity']) or
        accepted.get('source_sha256')!=source['source_sha256']):
        result['blockers']=['NO_ACCEPTED_COMPAT_BINDING']
        return result
    result['baseline']=accepted['baseline']
    result['target']['runtime_id']=accepted['runtime_id']
    result['target']['policy_contract']=copy.deepcopy(accepted['contract'])
    for animation in result['target']['animations']:
        role=animation['role']
        source_animation=next(a for a in source['animations'] if a['role']==role)
        binding=accepted['animations'].get(role)
        if binding is None:
            result['adaptations'].append(dict(category='ANIMATION_ROLES',role=role,
                source='authored role present',accepted='not packed as a distinct runtime role',adapter='accepted_role_omission'))
            animation['runtime_binding']=None
            continue
        animation['runtime_binding']=copy.deepcopy(binding)
        source_frames=source_animation['frames']
        rows=(('ATTACKS',dict(eligibility='attacking OR projectile',frames=[f.get('attack') for f in source_frames]),
               'selected attack state; accepted hit latch and variant exclusions','accepted_state_attack_gate'),
              ('DAMAGE',[None if not f.get('attack') else {k:f['attack'][k] for k in ('kind','force','drop')} for f in source_frames],accepted['contract']['damage'],'accepted_damage'),
              ('COLLISION',[dict(bbox=f['bbox'],offset=f['offset'],binding=f['source_binding']) for f in source_frames],accepted['contract']['collision'],'accepted_collision'),
              ('TIMING',[f['delay'] for f in source_animation['frames']],binding['delay'],'accepted_animation_delay'),
              ('MOVEMENT',[f['move'] for f in source_animation['frames']],
               'existing driver/state displacement; no new source frame-move consumer','accepted_movement'),
              ('GEOMETRY',[dict(dimensions=f['dimensions'],offset=f['offset']) for f in source_animation['frames']],
               binding.get('geometry'),'accepted_raster_transform'))
        for category,exact,compat,adapter in rows:
            result['adaptations'].append(dict(category=category,role=role,
                source=copy.deepcopy(exact),accepted=copy.deepcopy(compat),adapter=adapter))
    for category,exact,compat,adapter in (
        ('AI',source['behavior'],accepted['contract']['behavior'],'accepted_behavior_driver'),
        ('STATS',source['stats'],accepted['contract']['stats'],'accepted_stats'),
        ('SPECIAL_EFFECTS',source['behavior'].get('default_effect'),accepted['contract']['effects'],'accepted_effects'),
        ('PALETTES',len(source['remaps']),accepted['contract']['palettes'],'accepted_palette_emission')):
        result['adaptations'].append(dict(category=category,source=copy.deepcopy(exact),accepted=copy.deepcopy(compat),adapter=adapter))
    # A known policy alone is not equivalence proof.
    result['blockers']=['ACCEPTED_RUNTIME_EQUIVALENCE_PROOF_REQUIRED']
    return result


def certify_policy(result, *, source_categories=None, equivalence_proof=None):
    """Labels cannot cross policy boundaries. Missing evidence fails closed."""
    result=copy.deepcopy(result)
    if result['profile']==Profile.SOURCE_EXACT.value:
        if (source_categories and set(source_categories)==set(CATEGORIES) and
            all(s=='SOURCE_CERTIFIED' for s in source_categories.values())):
            result.update(status='SOURCE_CERTIFIED',blockers=[])
    elif result['blockers']==['ACCEPTED_RUNTIME_EQUIVALENCE_PROOF_REQUIRED']:
        if (equivalence_proof and equivalence_proof.get('passed') is True and
            equivalence_proof.get('source_fingerprint')==result['source_fingerprint'] and
            equivalence_proof.get('baseline')==result['baseline']):
            result.update(status='ADAPTER_EQUIVALENT',blockers=[],proof=copy.deepcopy(equivalence_proof))
    return result


def require_certified(result):
    expected='SOURCE_CERTIFIED' if result['profile']==Profile.SOURCE_EXACT.value else 'ADAPTER_EQUIVALENT'
    if result['status']!=expected:
        raise ValueError(f"{result['profile']}_LOWERING_BLOCKED: {result['blockers']}")
    return result
