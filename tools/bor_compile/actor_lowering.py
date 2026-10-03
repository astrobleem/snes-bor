"""Source actor semantic lowering and strict current-target certification.

This is shadow data, not a replacement for the accepted roster encoder.
Descriptors retain every frame and attack role. A reference evaluator is not
a 65816 runtime proof: missing consumers remain explicit blockers.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from fractions import Fraction

from compiler import key
from model_ir import KNOWN_ROLES, source_behavior, validate_model_ir

CATEGORIES = ('IDENTITY', 'ASSETS', 'PALETTES', 'STATS', 'ANIMATION_ROLES',
              'FRAME_GEOMETRY', 'COLLISION', 'ATTACKS', 'MOVEMENT',
              'AI_BEHAVIOR', 'SPECIAL_EFFECTS')


@dataclass(frozen=True)
class RoleBinding:
    source_role: str
    status: str
    target: str | None
    reason: str


def role_binding(role):
    # Explicit target roles, never a model-name correspondence table.
    slots = {'idle', 'walk', 'fall', 'rise', 'jump', 'jumpattack',
             'jumpattack2', 'special', 'waiting', 'get', 'attack2', 'attack3',
             'attack4', 'grab', 'slide', 'riseattack', 'grabattack', 'freespecial'}
    if role == 'attack1':
        return RoleBinding(role, 'ADAPTABLE', 'attack', 'base attack role adapter')
    if role in slots:
        return RoleBinding(role, 'DIRECT', role, 'existing animation slot; behavioral fidelity checked separately')
    if role in KNOWN_ROLES:
        return RoleBinding(role, 'REQUIRES_RUNTIME_ROLE', None,
                           'recognized source role lacks an unconditional distinct packed slot')
    return RoleBinding(role, 'UNSUPPORTED', None, 'unknown source role/dialect')


def allocate_ids(identities, pinned=None, reserved=(), maximum=255):
    """One project per link. Compatibility pins are input, never global IDs."""
    identities = set(tuple(i) for i in identities)
    if len({i[0] for i in identities}) > 1:
        raise ValueError('MULTIPLE_PROJECTS_IN_ACTOR_BUILD')
    pins = {tuple(i): n for i, n in (pinned or {}).items()}
    if not set(pins) <= identities or len(set(pins.values())) != len(pins):
        raise ValueError('INVALID_ACTOR_ID_PINS')
    occupied = set(reserved)
    if occupied & set(pins.values()):
        raise ValueError('RESERVED_ACTOR_ID_COLLISION')
    occupied.update(pins.values())
    if any(not 0 <= n <= maximum for n in occupied):
        raise ValueError('ACTOR_ID_CAPACITY_EXCEEDED')
    result = dict(pins)
    for identity in sorted(identities - set(pins)):
        available = next((n for n in range(maximum + 1) if n not in occupied), None)
        if available is None:
            raise ValueError('ACTOR_ID_CAPACITY_EXCEEDED')
        result[identity] = available
        occupied.add(available)
    return result


def lower_model(ir, runtime_id=None):
    """Lossless semantic descriptors, with source integers and asset identity.

    No quantization, median timing, role-dependent attack removal, or alias
    substitution occurs here. Current-runtime certification is separate.
    """
    animations = []
    for animation in ir.animations:
        frames = []
        for ordinal, frame in enumerate(animation.frames):
            state=copy.deepcopy(frame.state)
            source_binding=None
            if ir.dialect=='historical-bor':
                offset=state['offset'];box=state['bbox'];attack=state.get('attack')
                source_binding=dict(body_corners=box_corners(box,offset),
                    vulnerable=bool(box[2] and box[3]),
                    attack_corners=None if attack is None else box_corners(attack['box'],offset),
                    delay_ticks=state['delay']*2,clock_hz=200)
            frames.append(dict(ordinal=ordinal, source_line=frame.line,
                               source_asset=frame.source_path,
                               asset_sha256=frame.asset_sha256,
                               dimensions=frame.dimensions,
                               source_binding=source_binding, **state))
        animations.append(dict(role=animation.role,
                               binding=asdict(role_binding(animation.role)),
                               properties=copy.deepcopy(animation.properties),
                               frames=frames))
    return dict(schema='bor-actor-semantic-v1', mode='SHADOW',
                source_identity=ir.identity, source_path=ir.source_path,
                source_sha256=ir.source_sha256, dialect=ir.dialect,
                runtime_id=runtime_id, stats=copy.deepcopy(ir.stats),
                behavior=source_behavior(ir), remaps=copy.deepcopy(ir.remaps),
                dependencies=list(ir.dependencies), animations=animations,
                directives=[asdict(d) for d in ir.directives],
                diagnostics=copy.deepcopy(ir.diagnostics))


def box_corners(box, offset):
    """load_cached_model: source x/y/width/height minus frame offset."""
    left,top=box[0]-offset[0],box[1]-offset[1]
    return [left,top,left+box[2],top+box[3]]


def attack_at(actor, role, frame, *, attacking=False, projectile=False):
    """BOR update_ents gate, independent of role spelling and actor identity.

    This returns a descriptor, not hit resolution. Target filters, depth,
    vulnerability, geometry and per-target attack IDs are independent checks.
    """
    animation = next(a for a in actor['animations'] if a['role'] == role)
    if not 0 <= frame < len(animation['frames']):
        raise IndexError('animation frame outside descriptor')
    attack = animation['frames'][frame].get('attack')
    if not (attacking or projectile) or not attack or not attack['force']:
        return None
    return copy.deepcopy(attack)


def drift_spawn(behavior, authored_x, world_x, random_fraction):
    """Pinned smartspawn reference: one random sample, THINK_SPEED=2/200s."""
    if behavior.get('driver') != 'noncombat_horizontal_drift':
        raise ValueError('behavior does not select noncombat drift')
    random_fraction = Fraction(random_fraction)
    if not 0 <= random_fraction < 1:
        raise ValueError('random fraction must be in [0,1)')
    speed = Fraction(behavior['source_speed']) + 3 * random_fraction
    return dict(x=Fraction(world_x), xdir=speed if authored_x < 160 else -speed,
                alive=True, attacking=False, damage_callback=False,
                role='walk', source_tick_seconds=Fraction(1, 100))


def source_random32_step(seed):
    """Pinned GAMELIB3/RAND32.ASM, unsigned 32-bit state and return.

    The returned bits are NOT the next seed. This reference does not bind
    target RNG call order or emulate the subsequent C floating-point math.
    """
    if not 0 <= seed <= 0xffffffff:
        raise ValueError('source RNG seed outside u32')
    wide=seed*1103515245+12345
    return wide & 0xffffffff, (wide >> 16) & 0xffffffff


def source_random_fraction(value):
    """Exact sample index used by randf; rational, not a C float emulator."""
    if not 0 <= value <= 0xffffffff:
        raise ValueError('source RNG result outside u32')
    return Fraction(value % 1000,1000)


def drift_tick(state, camera_x):
    result = dict(state)
    if not result['alive']:
        return result
    if result['x'] < camera_x - 80 or result['x'] > camera_x + 400:
        result['alive'] = False
    else:
        result['x'] += result['xdir']
    return result


def effect_descriptor(behavior):
    """Consumes an engine-semantic effect, never an actor name or alias."""
    effect = behavior.get('default_effect')
    if effect is None:
        return None
    return dict(kind=effect,
                source_counter_value=40000 if effect == 'reset_timer' else None,
                source_tick_hz=200 if effect == 'reset_timer' else None,
                target_bound=False)


def certify_current(ir, lowered):
    """Fail closed against committed fixed-slot runtime, not proposed ABI.

    Category PASS means that category has no missing runtime requirements;
    source parse or encoder success alone cannot certify an executable actor.
    """
    matrix = {c: dict(status='CERTIFIED', blockers=[]) for c in CATEGORIES}

    def block(category, code, reason, role=None, line=0, directive=None):
        matrix[category]['status'] = 'BLOCKED'
        matrix[category]['blockers'].append(dict(code=code, reason=reason,
            source_file=ir.source_path, source_identity=ir.identity,
            animation_role=role, line=line, directive=directive))

    if lowered['runtime_id'] is None:
        block('IDENTITY', 'MISSING_LINK_ID', 'no project-scoped link allocation')
    # Asset presence and identity are facts; encoding/binding proof is not.
    if not ir.animations or not any(a.frames for a in ir.animations):
        block('ASSETS', 'NO_FRAME_DATA', 'model has no parsed frame assets')
    block('ASSETS', 'FIXED_SLOT_MEDIA_FORMAT',
          'target graphics ABI uses fixed 768-byte 32x48 poses and a fixed role sequence rather than arbitrary source dimensions/role media; the exact descriptor catalog does not change that graphics ABI')
    if ir.remaps:
        block('PALETTES', 'PALETTE_QUANTIZATION_POLICY',
              'byte map selector and palette loader support authored map indices, but the fixed raster encoder quantizes source colors to a shared 16-color target; exact source color/remap preservation is not guaranteed')
    block('STATS', 'BASE_STAT_BINDING',
          'fixed-slot target applies spawn health and fixed player constants, not complete model-health/default arbitration and source speed semantics')
    behavior = lowered['behavior']
    driver=behavior.get('driver','unknown')
    behavior_gaps={
        'noncombat_horizontal_drift':'source rand32/randf IEEE-float arithmetic and 100Hz think scheduling differ from the experimental live byte-RNG fixed-point driver',
        'enemy_drop_then_ai':'source role-aware randomized enemy decisions/stall/drop lifecycle differ from target proximity attack and seek/hold state decisions',
        'pickup':'source pickup effect precedence, entity removal/suicide and timed lifecycle are not represented by the target breakable/pickup callback contract',
        'player':'source input/role transition and move cancellation contract differs from target fixed action-state driver',
        'biker':'source subtype movement/damage lifecycle is not interchangeable with the target fixed-speed biker adapter',
        'none':'source noncombat no-damage-callback and animation lifetime contract differs from target HP/role-based entity lifecycle',
        'obstacle':'source damage callback/box and destruction lifecycle differs from target fixed prop-hit path',
        'steamer':'source periodic child-spawn/animation lifecycle differs from the accepted target emitter adaptation',
    }
    block('AI_BEHAVIOR', 'SOURCE_BEHAVIOR_CONTRACT',
          behavior_gaps.get(driver,behavior.get('reason','unknown source driver/dialect: '+driver)))
    for a in lowered['animations']:
        role = a['role']
        if a['binding']['status'] in ('REQUIRES_RUNTIME_ROLE', 'UNSUPPORTED'):
            block('ANIMATION_ROLES', 'ROLE_BINDING', a['binding']['reason'], role)
        if len(a['frames']) > 255:
            block('ANIMATION_ROLES', 'FRAME_COUNT_WIDTH', 'runtime frame count exceeds byte representation', role)
        if len({f.get('delay') for f in a['frames']}) > 1:
            block('ANIMATION_ROLES', 'PER_FRAME_TIMING',
                  'fixed-slot animation scheduler consumes median delay; the exact 200Hz descriptor primitive is separate from automatic renderer/state scheduling', role)
        if a['frames']:
            block('FRAME_GEOMETRY', 'FRAME_TRANSFORM_PROOF',
                  'target OAM/frame ABI fixes a 32x48 raster within 32x64 OBJ allocation; arbitrary source per-frame dimensions/offsets use crop/scale adaptation, not a source-exact raster transform', role)
        if a['frames'] and (ir.stats.get('type') in ('player','enemy','obstacle') or
                           any(any(f.get('bbox', [])) for f in a['frames'])):
            block('COLLISION', 'SOURCE_BODY_BOXES',
                  'fixed-slot collision uses fixed extents; isolated source-box consumption does not bind all production interactions or raster coordinates', role)
        if any(f.get('attack') and f['attack']['force'] for f in a['frames']):
            block('ATTACKS', 'FRAME_ATTACK_CONSUMER',
                  'exact descriptor/HP consumption is available in fixtures; complete source target filters, attack-ID dedupe, damage-type/drop callbacks and behavior-owned activation are not represented by the fixed-slot hit path', role)
        if any(f.get('move') for f in a['frames']):
            block('MOVEMENT', 'FRAME_MOVE_CONSUMER', 'target movement is state-driver displacement, not authored per-frame movement-event execution', role)
    if behavior.get('driver') == 'noncombat_horizontal_drift':
        block('MOVEMENT', 'DRIFT_DRIVER', 'live parameterized drift is experimental: byte RNG, fixed-point numerics and per-OOP clock feeding are not source rand32/randf/IEEE-float and scheduler equivalence', 'walk')
    effect = effect_descriptor(behavior)
    if effect:
        block('SPECIAL_EFFECTS', 'EFFECT_BINDING',
              'source effect requires runtime lifecycle binding: ' + effect['kind'])
    for diagnostic in validate_model_ir(ir)['diagnostics']:
        # Retain exact unknown semantics even if no narrower category fits.
        block('AI_BEHAVIOR', diagnostic['category'], diagnostic['reason'],
              diagnostic.get('animation_role'), diagnostic['line'], diagnostic['directive'])
    return dict(status='BLOCKED' if any(v['status']=='BLOCKED' for v in matrix.values()) else 'CERTIFIED',
                matrix=matrix, effect=effect, runtime_publication=False)
