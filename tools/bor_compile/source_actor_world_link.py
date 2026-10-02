"""Bounded execution-program linking from the one source-exact actor IR.

This is not whole-model certification. A controlled player action is explicit;
ordinary opponents select their driver from source type and supported features.
Accepted compatibility never falls back into this program format.
"""
import struct

from lowering_policy import Profile

PROGRAM_BYTES = 32


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
