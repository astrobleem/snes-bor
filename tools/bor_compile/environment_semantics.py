"""Pinned historical BOR environment meanings, independent of target encoding.

These functions describe source behavior, not a certificate for the SNES
renderer. In particular, altitude and display alias must not change actor IDs.
"""
from dataclasses import dataclass

SOURCE_COMMIT = 'eba02fe6c9e97e388126c51560a92024f406d8c0'
SOURCE_MAX_MAPS = 7
SOURCE_NAME_BYTES = 20


def historical_map(selection, defined_maps):
    """ent_set_colourmap takes unsigned int; absent colourmap pointers are NULL."""
    selection = int(selection) & 0xffffffff
    if selection > SOURCE_MAX_MAPS or selection > defined_maps:
        return 0
    return selection


def display_name(model_name, alias):
    # findarg supplies one token. BOR's zeroed entity has room for the NUL.
    return (alias or model_name).encode('latin1')[:SOURCE_NAME_BYTES].decode('latin1')


@dataclass(frozen=True)
class AltitudeBinding:
    authored: int
    initial: int | None
    base: int
    ownership: str
    runtime_requirement: str


def altitude_binding(authored, model_type, subtype='', *, authored_x=0,
                     world_x=0, scroll='right', time=0):
    """spawn -> smartspawn ordering. Random altitude is never fabricated.

    `a` and `base` are floats in the source entity; the stage operand is a
    signed C int from atoi, in source pixel units. Depth is a different field.
    """
    a = 0 if authored is None else int(authored)
    if not -(1 << 31) <= a < (1 << 31):
        raise ValueError('altitude outside source signed-int domain')
    if model_type == 'steamer':
        return AltitudeBinding(a, a, a, 'fixed_base', 'signed base altitude inherited by emitted child')
    if model_type == 'player' and time:
        return AltitudeBinding(a, 300, 0, 'player_jump', 'explicit player reentry jump, not nonzero-Z inference')
    if model_type == 'enemy' and subtype != 'biker':
        drop = scroll in ('up', 'down') and -30 < world_x < 350
        if drop or 0 < authored_x < 320:
            return AltitudeBinding(a, None, 0, 'enemy_drop', '240 + randf(40), independently owned enemy drop')
        return AltitudeBinding(a, a, 0, 'enemy_drop', 'gravity toward base; enemy_drop callback')
    return AltitudeBinding(a, a, 0, 'model_driver', 'signed altitude plus independent model state')


def exit_clamp(x, depth, width, blocked):
    return min(x, width - 30 - (232 - depth)) if blocked else x


def hole_predicate(x, depth, width, holes, endhole):
    if endhole and x > width - (232 - depth):
        return 2
    if depth < 195:
        return 0
    # Inputs are C int. Division here uses truncation, not float rounding.
    tilted_left = x + int((depth - 195) / 4)
    tilted_right = x - (depth - 195) * 2
    return int(any(tilted_left >= h + 11 and tilted_right <= h + 200 for h in holes))


def lower_map_queue(ir, roster, entities, *, dialect):
    """Emit extended selectors without changing source IR or the golden adapter.

    The accepted adapter owns all other queue transforms. Its documented
    hole-prefix insertion is asserted here rather than confusing authored and
    packed indices. Unknown dialect map semantics fail closed.
    """
    import copy
    from compiler import lower
    from stage_environment_abi import encode_map
    from queue_abi import RECORD_SIZE
    if dialect != 'historical-bor':
        raise ValueError('UNKNOWN_SOURCE_SEMANTIC: map normalization for this dialect')
    candidate = copy.deepcopy(ir)
    selections = []
    for q in candidate.queue:
        if q.kind != 'spawn':
            selections.append(None)
            continue
        model = entities.get(q.character.casefold())
        if model is None:
            raise ValueError(f'MISSING_MODEL: {ir.source_path}: {q.character}')
        # Keep the requested valid selector. Runtime resolves an absent map
        # to base using the emitted per-model bounds; do not rewrite map 0..3.
        selection = historical_map(q.map, SOURCE_MAX_MAPS)
        selections.append(selection)
        q.map = selection & 3
    count, data = lower(candidate, roster, entities)
    data = bytearray(data)
    prefix = len(ir.environment.get('hole', []))
    if count != len(ir.queue) + prefix:
        raise ValueError('ENVIRONMENT_QUEUE_ALIGNMENT: unknown runtime record insertion')
    for i in range(prefix):
        if data[i * RECORD_SIZE + 6] & 7 != 6:
            raise ValueError('ENVIRONMENT_QUEUE_ALIGNMENT: expected hole prefix')
    for i, selection in enumerate(selections, prefix):
        if selection is None:
            continue
        offset = i * RECORD_SIZE
        data[offset + 5], data[offset + 6] = encode_map(data[offset + 5], data[offset + 6], selection)
    return count, bytes(data)


def extend_legacy_queue_maps(ir, blob):
    """Patch only selector bits in an independently generated historical queue."""
    from stage_environment_abi import encode_map
    from queue_abi import RECORD_SIZE
    if ir.diagnostics:
        raise ValueError(ir.diagnostics)
    prefix = len(ir.environment.get('hole', []))
    if len(blob) != (len(ir.queue) + prefix) * RECORD_SIZE:
        raise ValueError(f'ENVIRONMENT_QUEUE_ALIGNMENT: {ir.source_path}')
    result = bytearray(blob)
    for i, q in enumerate(ir.queue, prefix):
        if q.kind != 'spawn':
            continue
        off = i * RECORD_SIZE
        result[off+5], result[off+6] = encode_map(result[off+5] & 1, result[off+6],
                                               historical_map(q.map, SOURCE_MAX_MAPS))
    return bytes(result)
