"""Shared environment capability identifiers; adapters are not whole-entry certificates."""

FEATURES = {
    'map-0..3': dict(compiler='ABI_V1_LEGACY_IDENTICAL', runtime='BYTE_SELECTOR', certified=True),
    'map->3': dict(compiler='ABI_V1_FULL_PALETTES', runtime='BYTE_SELECTOR_WITH_MODEL_BOUNDS', certified=True),
    'altitude-fixed-base': dict(compiler='SIGNED_Q16_16_SIDE_TABLE', runtime='INDEPENDENT_BASE_AND_CHILD_RISE', certified=True),
    'altitude-other': dict(compiler='PRESERVED_IR', runtime='DRIVER_BINDING_REQUIRED', certified=False),
    'alias': dict(compiler='INSTANCE_NAME_ID_SEPARATE_FROM_MODEL', runtime='STORED_BUT_GENERAL_OPPONENT_HUD_MISSING', certified=False),
    'water': dict(compiler='BITMAP_AND_MODE_IR', runtime='TEXTURE_WAVE_UNBOUND', certified=False),
    'hole': dict(compiler='SOURCE_SCALED_QUEUE_CONTROL', runtime='Spawn_CheckHole', certified=True),
    'endhole': dict(compiler='FLAG_IR', runtime='DEPTH_DEPENDENT_EXIT_PREDICATE_UNBOUND', certified=False),
    'blocked': dict(compiler='FLAG_IR', runtime='DEPTH_DEPENDENT_EXIT_CLAMP_UNBOUND', certified=False),
    'scroll-right': dict(compiler='X_TRIGGER_SCALE', runtime='HORIZONTAL_CAMERA', certified=True),
    'scroll-left': dict(compiler='REVERSED_PROGRESS', runtime='LEFT_CAMERA_AND_MIRROR', certified=True),
    'scroll-down': dict(compiler='VERTICAL_TRIGGER_SCALE', runtime='Q8_8_VERTICAL_CAMERA', certified=True),
    'geometry': dict(compiler='SOURCE_ASSET_IDENTITY_AND_DIMENSIONS', runtime='ACCEPTED_CROP_SCALE_CATALOG', certified=True),
    'rock': dict(compiler='PRESERVED_IR', runtime='TIME_DRIVEN_DISPLAY_OFFSET_UNBOUND', certified=False),
}


def matrix(stages, dialect='historical-bor', models=None):
    seen = set()
    for ir in stages:
        seen.update(('geometry', 'scroll-' + ir['scroll']))
        for q in ir['queue']:
            seen.add('map->3' if q['map'] > 3 else 'map-0..3')
            if q['alias']: seen.add('alias')
            if q['altitude'] not in (None, 0):
                model=(models or {}).get((q['character'] or '').casefold(),{})
                fixed=dialect=='historical-bor' and model.get('ir',{}).get('stats',{}).get('type')=='steamer'
                seen.add('altitude-fixed-base' if fixed else 'altitude-other')
        seen.update(k for k, v in ir['environment'].items() if v and k in FEATURES)
    return {k:dict(source_seen=k in seen, **(v | {'certified':v['certified'] and dialect=='historical-bor'})) for k,v in FEATURES.items()}
