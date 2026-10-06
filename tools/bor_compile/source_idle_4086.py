"""Pinned set_idle policy; target search and animation initialization are services."""


def default_idle_capability(identities, core):
    """A restricted native leaf is legal only when the complete registry proves it.

    Cached model animation inheritance cannot introduce a special idle if no
    admitted cached model owns one. Dynamic idlemode is also checked natively.
    """
    if identities['limits']['max_idles'] != 1:
        raise ValueError('SOURCE_IDLE_RANGE_SERVICE_REQUIRED')
    models = {m['identity']: m for m in core['models']}
    rows = []
    for model in identities['models']:
        fields = models[model['identity']]['fields']
        if fields['subtype'] != 0:
            raise ValueError('SOURCE_IDLE_SUBTYPE_SERVICE_REQUIRED')
        if any(a['engine_animation_id'] in (61, 80) for a in model['animations']):
            raise ValueError('SOURCE_IDLE_SPECIAL_SERVICE_REQUIRED')
        rows.append(dict(identity=model['identity'], capability='DEFAULT_IDLE_ONLY',
                         cached_type=fields['type'], cached_subtype=fields['subtype']))
    if len(rows) != len(models):
        raise ValueError('SOURCE_IDLE_REGISTRY_IDENTITY')
    return dict(schema='BYOR_4086_IDLE_CAPABILITY_V1', models=rows,
                native_animation_initializer_required=True,
                dynamic_idlemode_domain=[0, 1], motu_gameplay_proven=False)


def common_anim_series(entity, series, force, default, owner):
    if force < 0 or force > len(series):
        raise ValueError('SOURCE_ANIMATION_SERIES_INDEX_UNDEFINED')
    valid = owner['valid_animation']
    selected = series[force - 1:force] if force else series
    for number in selected:
        if valid(entity, number) and number != default:
            if force or owner['find_target'](number, 0):
                owner['set_animation'](entity, number, 0)
                return 1
    if valid(entity, default):
        owner['set_animation'](entity, default, 0)
        return 1
    return 0


def common_idle_anim(entity, owner):
    previous = owner['self']
    owner['self'] = entity
    try:
        if entity['idling']:
            entity['idling'] |= 2
        model = entity['model']
        if model['subtype'] != owner['biker'] and model['type'] != 0:
            entity['vx'] = entity['vz'] = 0
        valid = owner['valid_animation']
        # C signed integer division truncates toward zero, including negative maxima.
        health = entity['modeldata']['health']
        threshold = health // 4 if health >= 0 else -((-health) // 4)
        if valid(entity, owner['faint']) and entity['health'] <= threshold:
            owner['set_animation'](entity, owner['faint'], 0)
            return 1
        if valid(entity, owner['sleep']) and owner['time'] > entity['sleeptime']:
            owner['set_animation'](entity, owner['sleep'], 0)
            return 1
        return common_anim_series(entity, owner['idles'], entity['idlemode'], owner['idle'], owner)
    finally:
        owner['self'] = previous


def set_idle(entity, owner):
    entity['idling'] = 1
    for name in ('attacking', 'inpain', 'jumping', 'blocking'):
        entity[name] = 0
    common_idle_anim(entity, owner)
    return 1
