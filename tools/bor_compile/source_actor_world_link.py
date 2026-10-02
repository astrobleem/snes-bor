"""Bounded execution-program linking from the one source-exact actor IR.

This is not whole-model certification. A controlled player action is explicit;
ordinary opponents select their driver from source type and supported features.
Accepted compatibility never falls back into this program format.
"""
import struct
from fractions import Fraction

from lowering_policy import Profile

PROGRAM_BYTES = 32
NORMAL_WORLD_DEATH_SOFTKILL = 0x8000


def link_world_program(actor, scheduler, runtime_id, *,
                       controlled_player_action=False, profile=Profile.SOURCE_EXACT):
    if Profile(profile) != Profile.SOURCE_EXACT:
        raise ValueError('SOURCE_WORLD_POLICY: no compatibility fallback')
    if actor.get('dialect') != 'historical-bor':
        raise ValueError('SOURCE_WORLD_DIALECT: source driver semantics unproven')
    if not 0 <= runtime_id <= 255:
        raise ValueError('SOURCE_WORLD_ID_WIDTH: actual actor catalog uses a byte')
    roles = {row['role']: row['role_id'] for row in scheduler['roles']}
    required = ('idle', 'pain', 'rise', 'attack1', 'walk')
    kind = actor['stats'].get('type')
    if actor.get('behavior', {}).get('default_effect') == 'reset_timer':
        raise ValueError('SPECIAL_EFFECT_GAMEPLAY_TIMER_LIFECYCLE: no source-equivalent runtime timer')
    if kind == 'player':
        if not controlled_player_action:
            raise ValueError('SOURCE_PLAYER_CONTROLLER: full input/chaining/grab controller unsupported')
        source_type, driver = 1, 2
        scope = 'CONTROLLED_ATTACK1_ACTION'
    elif kind == 'enemy':
        if controlled_player_action:
            raise ValueError('SOURCE_WORLD_DRIVER_TYPE: enemy is not a controlled player')
        extra = sorted(set(roles) & {'attack2','attack3','upper','jumpattack','jumpattack2'})
        if extra:
            raise ValueError('SOURCE_AI_EXTRA_ROLE_SEMANTICS: '+','.join(extra))
        source_type, driver = 2, 1
        scope = 'GROUNDED_IN_RANGE_SINGLE_ATTACK'
    else:
        raise ValueError('SOURCE_WORLD_BEHAVIOR_CAPABILITY: '+str(kind))
    missing = sorted(set(required)-roles.keys())
    if missing:
        raise ValueError('SOURCE_WORLD_ROLE_CONTRACT: selected driver requires '+','.join(missing))
    health = int(actor['stats'].get('health',0))
    if not 0 < health <= 255:
        raise ValueError(f'SOURCE_WORLD_HEALTH_WIDTH: required={health}, available=1..255')
    attack = next(a for a in actor['animations'] if a['role']=='attack1')
    limits = [int(v) for v in attack['properties'].get('range',[['-10','80']])[-1]]
    if len(limits)!=2 or any(not -32768<=v<=32767 for v in limits):
        raise ValueError('SOURCE_WORLD_RANGE_WIDTH')
    for animation in actor['animations']:
        if animation['role'] not in required:
            continue
        events = set(animation['properties']) & {'throwframe','shootframe','jumpframe','sound'}
        if events:
            raise ValueError('SOURCE_WORLD_FRAME_EVENT: '+','.join(sorted(events)))
    pointer = scheduler['role_table']
    if pointer>>16 not in range(0x40) or pointer&65535<0x8000:
        raise ValueError('SOURCE_WORLD_PROGRAM_ROM_POINTER')
    values = (runtime_id,source_type,health,driver,pointer&65535,pointer>>16,
              len(roles),*(roles[r] for r in required),*limits,0,0)
    blob = struct.pack('<16H',*[v&65535 for v in values])
    return blob,dict(format='SOURCE_WORLD_PROGRAM_V1',bytes=PROGRAM_BYTES,
                     source_identity=actor['source_identity'],runtime_id=runtime_id,
                     source_sha256=actor.get('source_sha256'),
                     scope=scope,source_type=source_type,source_health=health,
                     source_range=limits,profile=Profile.SOURCE_EXACT.value,
                     source_certified=False,
                     required_domain=['unlinked','grounded','integral_source_lattice',
                                      'source_health_fits_byte','bounded_camera_and_position'],
                     excluded=['general_movement','airborne_damage','whole_player_controller',
                               'source_hit_effect_entities','source_raster_compositor'])


def link_normal_campaign_world_program(actor, scheduler, runtime_id, *,
                                       controlled_player_action=False):
    """Encode a Normal roster identity for the persistent campaign host.

    The host consumes sequenced held-direction and attack-edge input for
    controlled player rows, plus source-speed movement and grounded attack1.
    Every source role/frame remains in the immutable scheduler; higher-order
    action roles are retained but are not selected by this bounded controller.
    Actor HP is an instance value written by Spawn_Play, so the program carries
    the preserve-instance sentinel and never overwrites authored queue health.
    """
    if actor.get('dialect') != 'historical-bor':
        raise ValueError('NORMAL_WORLD_DIALECT')
    if not 0 <= runtime_id <= 255:
        raise ValueError('NORMAL_WORLD_ID_WIDTH')
    source_actor_type = actor.get('stats', {}).get('type')
    if source_actor_type not in ('enemy', 'player'):
        raise ValueError('NORMAL_WORLD_ONLY_COMBAT_ROSTER')
    if source_actor_type == 'player' and not controlled_player_action:
        raise ValueError('NORMAL_WORLD_PLAYER_ACTION_SCOPE')
    roles = {row['role']: row['role_id'] for row in scheduler['roles']}
    if 'idle' not in roles:
        raise ValueError('NORMAL_WORLD_ROLE_CONTRACT: idle')
    source_type = 1 if controlled_player_action else 2
    # Normal queue/position lowering rounds source coordinates through 4/5.
    # Carry that explicit bridge policy in the source-linked model record;
    # the bounded/reference linker above continues to require exact lattice.
    flags = (2 if controlled_player_action else 1) | 4
    attack_role = 'attack1' if 'attack1' in roles else 'idle'
    fallback = roles['idle']
    limits = [-10, 80]
    if attack_role != 'idle':
        attack = next(a for a in actor['animations'] if a['role'] == attack_role)
        values = attack['properties'].get('range')
        if values:
            limits = [int(v) for v in values[-1]]
    if len(limits) != 2 or any(not -32768 <= v <= 32767 for v in limits):
        raise ValueError('NORMAL_WORLD_RANGE_WIDTH')
    encoded_role_names = ('idle', 'pain', 'rise', attack_role, 'walk')
    selected_roles = list(encoded_role_names)
    encoded_roles = [roles.get(role, fallback) for role in encoded_role_names]
    frame_events = []
    for animation in actor['animations']:
        events = sorted(set(animation['properties']) &
                        {'throwframe', 'shootframe', 'jumpframe', 'sound'})
        if events:
            frame_events.append(dict(role=animation['role'], events=events,
                                     selected_by_host=animation['role'] in selected_roles))
    pointer = scheduler['role_table']
    if pointer >> 16 not in range(0x40) or pointer & 65535 < 0x8000:
        raise ValueError('NORMAL_WORLD_PROGRAM_ROM_POINTER')
    # Enemy movement callbacks run every two 200-Hz source ticks. Store the
    # authored decimal speed in twentieths so full/half speed are exact
    # integers in the worker's subpixel accumulator.
    speed = Fraction(actor.get('behavior', {}).get('source_speed', '1'))
    speed20 = speed * 20
    if speed20.denominator != 1 or not 10 <= speed20.numerator <= 600:
        raise ValueError('NORMAL_WORLD_SPEED_DOMAIN')
    death_policy = NORMAL_WORLD_DEATH_SOFTKILL
    values = (runtime_id, source_type, 0xFFFF, flags, pointer & 65535,
              pointer >> 16, len(scheduler['roles']), *encoded_roles,
              *limits, death_policy, speed20.numerator)
    blob = struct.pack('<16H', *[v & 65535 for v in values])
    ignored = sorted(set(roles) - set(selected_roles))
    return blob, dict(format='NORMAL_COMPAT_WORLD_PROGRAM_V1', bytes=PROGRAM_BYTES,
        source_identity=actor['source_identity'], runtime_id=runtime_id,
        source_sha256=actor.get('source_sha256'), source_type=source_type,
        source_actor_type=source_actor_type,
        coordinate_bridge='nearest_4_5',
        scope=('CONTROLLED_SOURCE_MOVEMENT_ATTACK1' if controlled_player_action
               else 'GROUNDED_IN_RANGE_ATTACK1'),
        input_contract=(['sequenced_held_dpad_per_source_tick', 'sequenced_y_attack1_edge',
                         'b_run_speed_modifier']
                        if controlled_player_action else None),
        role_fallbacks={role: 'idle' for role in ('pain', 'rise', 'walk') if role not in roles},
        no_attack1='idle-authored-hitbox-only' if attack_role == 'idle' else None,
        death_policy='grounded lethal hit retires through native HP-zero soft-kill seam',
        source_frame_events=frame_events,
        frame_event_transport='NOT_CERTIFIED_FOR_SA1_BOUND_ACTORS',
        source_roles_retained=sorted(roles), source_roles_not_selected_by_host=ignored,
        source_roles_selected_by_host=sorted(set(selected_roles)),
        source_health='preserve-spawn-instance', source_range=limits,
        source_speed=str(speed), source_speed_twentieths=speed20.numerator,
        compatibility_adapter='S8_NORMAL_SOURCE_GROUNDED_V2', source_certified=False)
