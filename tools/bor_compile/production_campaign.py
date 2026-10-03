"""Source-owned production campaign linker; encoded media are explicit bindings.

Logical order never follows physical adjacency. Existing media bindings pin
accepted asset encodings, while source content hashes authorize their reuse.
Availability is deliberately a separate, fail-closed release gate.
"""
from copy import deepcopy
from pathlib import Path

from compiler import Source, project, stage, presentation, key, model_catalog


def complete_presentation(source, ir):
    """Include every frontpanel declaration, not only the legacy scalar view."""
    from compiler import digest
    layers = tuple(digest(source.read(source.image_path(d.values[0])))
                   for d in ir.directives if d.name == 'frontpanel')
    return presentation(source, ir), layers


def link_campaigns(bindings, campaigns, scenes, selected=("Easy", "Normal"),
                   legacy_stage_ids=None):
    configs = deepcopy(bindings)
    result = deepcopy(campaigns)
    pak = next(c['pak'] for c in configs if c['family'] == 'bor-original')
    source = Source(pak)
    ir = project(source)
    by_source = {key(c['source_level']): c for c in configs}
    media = {}
    for c in configs:
        if c['family'] != 'bor-original':
            continue
        parsed = stage(source, c['source_level'])
        if parsed.diagnostics:
            raise ValueError(parsed.diagnostics)
        media.setdefault(complete_presentation(source, parsed), c)
    scene_by_path = {key(c['source_scene']): c for c in scenes}
    linked = []
    legacy_stage_ids = legacy_stage_ids or {}
    for source_set in ir.sets:
        if source_set.name not in selected:
            continue
        entries = []
        levels = []
        pins = legacy_stage_ids.get(source_set.name, ())
        for entry in source_set.entries:
            if entry.kind == 'SCENE':
                binding = scene_by_path.get(key(entry.source_path))
                if binding is None:
                    raise ValueError(f'SCENE_MEDIA_UNBOUND: {entry.source_path}')
                entries.append(dict(kind='scene', scene_id=binding['scene_id'],
                                    next_after=entry.next_after))
                continue
            parsed = stage(source, entry.source_path)
            if parsed.diagnostics:
                raise ValueError(parsed.diagnostics)
            signature = complete_presentation(source, parsed)
            binding = media.get(signature)
            if binding is None:
                raise ValueError(f'STAGE_MEDIA_UNBOUND: {entry.source_path}: {signature}')
            existing = by_source.get(key(entry.source_path))
            ordinal = len(levels)
            physical_id = next((i for i, c in enumerate(configs) if c is existing),
                               len(configs))
            if ordinal < len(pins) and physical_id != pins[ordinal]:
                raise ValueError(f'LEGACY_STAGE_ID_DRIFT: {source_set.name}[{ordinal}]: '
                                 f'{physical_id} != {pins[ordinal]}')
            spawn_path = ('out/compiler_campaign/' +
                          key(entry.source_path).removesuffix('.txt') + '/spawn_table.bin')
            if source_set.name == 'Normal' and ordinal < len(pins):
                slug = Path(key(entry.source_path)).stem
                spawn_path = f'out/spawn_normal{slug}/spawn_table.bin'
            cfg = dict(family='bor-original', pak=pak,
                       source_set_id=source_set.source_id,
                       queue_identity_policy=('accepted-legacy' if source_set.name == 'Easy'
                                              else 'source-identity'),
                       source_level=entry.authored_path.replace('/', '\\').upper(),
                       bg=binding['bg'], frontpanel=binding.get('frontpanel'),
                       spawn=existing['spawn'] if existing else spawn_path,
                       scroll_direction=parsed.scroll,
                       source_direction=parsed.scroll,
                       source_mirror=bool(parsed.environment.get('mirror', [0])[-1]))
            if existing is None:
                configs.append(cfg)
                by_source[key(entry.source_path)] = cfg
            else:
                existing.clear()
                existing.update(cfg)
            levels.append(entry.authored_path)
            entries.append(dict(kind='stage', source_level=entry.authored_path,
                                next_after=entry.next_after))
        if len(levels) < len(pins):
            raise ValueError(f'LEGACY_STAGE_ID_DRIFT: {source_set.name} lost pinned stages')
        campaign_id = {'Easy': 'BOR_ORIGINAL', 'Normal': 'BOR_NORMAL_1A_INTERNAL'}[source_set.name]
        result[campaign_id] = dict(family='bor-original', source_levels_file=ir.levels_path,
                                  source_levels=levels, entries=entries,
                                  completion_policy=('accepted-easy-s7' if source_set.name == 'Easy' else 'source-next'),
                                  completion_flags=completion_flags(entries, source_set.name),
                                  source_set_id=source_set.source_id,
                                  ifcomplete=source_set.ifcomplete)
        linked.append(dict(name=source_set.name, entries=len(entries), stages=len(levels)))
    return configs, result, linked


def completion_flags(entries, source_set):
    """Runtime presentation policy, separate from immutable authored next flags.

    S7 Easy shows completion for every physical stage. Nonterminal scene
    continuation also sets Stage_LoadPending and re-enters the same branch;
    terminal Ending goes directly to HandleEnd without setting pending.
    """
    if source_set == 'Normal':
        return [int(e['next_after']) for e in entries]
    if source_set != 'Easy' or any(e['kind'] not in ('stage', 'scene') for e in entries):
        raise ValueError('UNKNOWN_COMPLETION_POLICY: ' + source_set)
    return [int(e['kind'] == 'stage' or i + 1 < len(entries)) for i, e in enumerate(entries)]


def bind_queue_identities(parsed, blob, roster, entities):
    """Bind every source spawn without disturbing map/position/HP/flag bytes.

    Zero is a real roster index. Non-actor props retain their effect/subtype;
    ordinary actors use the existing identified-enemy runtime discriminator.
    """
    from build_spawn_table import (RECORD_KIND_BOSS_IDENTIFIED, RECORD_KIND_PROP,
                                   SUBTYPE_IDENTIFIED_ENEMY, SUBTYPE_SHIFT)
    from queue_abi import RECORD_SIZE
    data = bytearray(blob)
    prefix = len(parsed.environment.get('hole', []))
    if len(data) != (prefix + len(parsed.queue)) * RECORD_SIZE:
        raise ValueError('IDENTITY_QUEUE_ALIGNMENT: ' + parsed.source_path)
    for index, event in enumerate(parsed.queue):
        if event.kind != 'spawn':
            continue
        name = event.character.casefold()
        binding = roster.get(name)
        if binding is None:
            raise ValueError(f'MODEL_UNBOUND: {parsed.source_path}: {event.character}')
        if type(binding) is not int or not 0 <= binding <= 255:
            raise ValueError(f'MODEL_BINDING_RANGE: {name}: {binding}')
        pos = (prefix + index) * RECORD_SIZE
        kind = data[pos + 6] & 7
        if kind != RECORD_KIND_PROP:
            data[pos + 6] = (data[pos + 6] & ~7) | RECORD_KIND_BOSS_IDENTIFIED
            if not event.boss and str(entities[name].get('subtype') or '').casefold() != 'biker':
                data[pos + 6] = ((data[pos + 6] & 31)
                                 | (SUBTYPE_IDENTIFIED_ENEMY << SUBTYPE_SHIFT))
        data[pos + 9] = binding
    return bytes(data)


def compile_queues(configs, roster_configs):
    """Lower selected BOR queues, rejecting missing identities before encoding."""
    from environment_semantics import lower_map_queue
    sources = {}
    output = {}
    for cfg in configs:
        if cfg['family'] != 'bor-original':
            continue
        policy = cfg.get('queue_identity_policy')
        if policy not in ('accepted-legacy', 'source-identity'):
            raise ValueError(f'QUEUE_IDENTITY_POLICY: {policy}')
        if cfg.get('source_set_id') != 0 and policy == 'accepted-legacy':
            raise ValueError('QUEUE_IDENTITY_POLICY: legacy is only authorized for Easy')
        cache_key = cfg['pak'], cfg.get('source_set_id')
        if cache_key not in sources:
            source = Source(cfg['pak'])
            models = model_catalog(source)
            roster = {}
            entities = {}
            for name, model in models.items():
                entities[name] = model['entity']
                path = key(model['source_path'])
                matches = [i for i, r in enumerate(roster_configs)
                           if r['family'] == cfg['family'] and
                           cfg.get('source_set_id') in r.get('runtime_binding_sets', (0, 1)) and
                           (key(r['source_character']) == path.rsplit('/', 1)[0]
                            or key(r['source_character']) == path.removesuffix('.txt'))]
                if len(matches) > 1:
                    raise ValueError(f'AMBIGUOUS_MODEL_BINDING: {name}')
                if matches:
                    roster[name] = matches[0]
                    roster.setdefault(key(model['source_path']).rsplit('/', 1)[-1].removesuffix('.txt'), matches[0])
            sources[cache_key] = source, roster, entities
        source, roster, entities = sources[cache_key]
        exact_ir = stage(source, cfg['source_level'])
        parsed = deepcopy(exact_ir)
        # New runtime bindings use authored defaults. Established actors retain
        # their documented shipped default-HP adaptation.
        for event in parsed.queue:
            if event.character and event.health is None:
                binding = roster.get(event.character.casefold())
                if binding is not None and roster_configs[binding].get('source_defaults'):
                    event.health = int(entities[event.character.casefold()].get('health') or 0)
        for event in parsed.queue:
            for identity in (event.character, event.item):
                if identity and identity.casefold() not in roster:
                    model = model_catalog(source).get(identity.casefold())
                    if model is None:
                        raise ValueError(f'MODEL_UNBOUND: {parsed.source_path}: {identity}')
                    model_path = key(model['source_path'])
                    # Preserve only explicitly inventoried historical bindings
                    # for the accepted set. New set links never inherit them.
                    if policy == 'accepted-legacy' and any(cfg.get('source_set_id') in r.get('accepted_legacy_unbound_sets', ())
                           and key(r.get('source_definition', '__absent')) == model_path
                           for r in roster_configs):
                        continue
                    raise ValueError(f'MODEL_UNBOUND: {parsed.source_path}: {identity}')
        count, blob = lower_map_queue(parsed, roster, entities, dialect='historical-bor')
        from model_ir import pickup_effect
        blob = bytearray(blob)
        prefix = len(parsed.environment.get('hole', []))
        for index, event in enumerate(parsed.queue):
            if not event.character:
                continue
            model = entities[event.character.casefold()]
            binding = roster.get(event.character.casefold())
            if binding is not None and roster_configs[binding].get('source_defaults') and model.get('type') == 'item':
                effect = pickup_effect('historical-bor', model['name'],
                                       model.get('health') or 0, model.get('score') or 0)
                if effect == 'reset_timer':
                    pos = (index + prefix) * 10 + 6
                    blob[pos] = (blob[pos] & 31) | (6 << 5)
        blob = bytes(blob)
        if policy == 'source-identity':
            blob = bind_queue_identities(parsed, blob, roster, entities)
        output[cfg['spawn']] = blob
    return output


def materialize_actor_bindings(roster_configs):
    """Recreate missing selected model media via the existing compat encoder.

    Existing accepted encoded bindings are not migrated or regenerated.
    New bindings must name their source definition explicitly.
    """
    from convert_character import convert_character
    for cfg in roster_configs:
        source_model = cfg.get('source_definition')
        if source_model is None:
            continue
        convert_character(cfg['pak'], source_model, cfg['converted_prefix'])
