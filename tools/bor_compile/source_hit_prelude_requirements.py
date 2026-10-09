"""Closed animation-only scripts and zero ground-missile model policy."""
import hashlib
import subprocess
from compiler import key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document, discover
from source_model_core_4086 import integer
from source_script_clone import derive as scripts, pack
from script_nested_authority import extract


def derive(source, engine='E:/gh/openbor-bcec'):
    raw = subprocess.check_output(['git', 'show', ENGINE_COMMIT + ':engine/openbor.c'], cwd=engine).decode('latin1')
    init = raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')]
    if 's_model *newchar = calloc(1, sizeof(*newchar));' not in init or 'newchar->ground' in init:
        raise ValueError('HIT_PRELUDE_GROUND_DEFAULT_AUTHORITY')
    candamage = extract(raw, 'lcmHandleCommandCandamage')
    if 'newchar->ground = 1;' not in candamage:
        raise ValueError('HIT_PRELUDE_GROUND_COMMAND_AUTHORITY')
    docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    models = discover(source, docs)['models']
    result = []
    for i, m in enumerate(models):
        ground = 0
        for r in docs[key(m['source_path'])]['directives']:
            if r['directive'] == 'subclass':
                raise ValueError('HIT_PRELUDE_SUBCLASS_REQUIRED')
            if r['directive'] == 'ondoattackscript':
                raise ValueError('HIT_PRELUDE_ONDOATTACK_OWNER_REQUIRED')
            if r['directive'] == 'candamage' and any(v.lower() == 'ground' for v in r['values']):
                ground = 1
            elif r['directive'] == 'hitenemy':
                ground = integer(r['values'], 1)
        if ground:
            raise ValueError('HIT_PRELUDE_GROUND_INAIR_OWNER_REQUIRED')
        result.append(dict(id=i, identity=m['declaration'], source_sha256=docs[key(m['source_path'])]['sha256'], ground=ground))
    sr = scripts(source)
    if len(result) != len(sr['models']):
        raise ValueError('HIT_PRELUDE_SCRIPT_MODEL_PAIR')
    return dict(schema='BYOR_HIT_PRELUDE_REQUIREMENTS_V1', capability='SOURCE_EMPTY_ONDOATTACK_ZERO_GROUND',
                engine_commit=ENGINE_COMMIT, models=result, script_descriptor_sha256=hashlib.sha256(pack(sr)).hexdigest(),
                model_ground_mutators_admitted=False, nonanimation_script_mutators_admitted=False,
                actual_item_blocking_damage_services_bound=False, production_world_owner_bound=False,
                motu_gameplay_proven=False, no_color_reduction=True)
