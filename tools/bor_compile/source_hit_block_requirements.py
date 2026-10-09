"""Source requirements for default block properties and absent counters."""
import hashlib
import subprocess
from compiler import key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_model_core_4086 import integer
from source_model_factors import derive as factors
from source_damage_inputs_4086 import load as damage
from source_model_attack_policy import load as policy
from source_animation_init_4086 import derive as animations
from source_animation_ids import configure


def derive(source,engine='E:/gh/openbor-bcec'):
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
    init=raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')]
    if 's_model *newchar = calloc(1, sizeof(*newchar));' not in init or any('newchar->'+n in init for n in ('blockback','thold','blockpain')):
        raise ValueError('HIT_BLOCK_MODEL_DEFAULT_AUTHORITY')
    if 'newanim->counterrange.frame.min = -1;' not in raw or 'newanim->counterrange.frame.max = -1;' not in raw:
        raise ValueError('HIT_BLOCK_COUNTER_DEFAULT_AUTHORITY')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs)
    config=configure(docs[key(structure['models_path'])]['directives']);ar=animations(source);fr=factors(source);models=[]
    for i,m in enumerate(structure['models']):
        doc=docs[key(m['source_path'])];rows=doc['directives'];properties=dict(blockback=0,thold=0,blockpain=0)
        for r in rows:
            if r['directive'] in ('counterframe','counterrange'):
                raise ValueError('HIT_BLOCK_COUNTER_OWNER_REQUIRED')
            if r['directive']=='subclass':raise ValueError('HIT_BLOCK_SUBCLASS_REQUIRED')
            if r['directive'] in properties:properties[r['directive']]=integer(r['values'])
        if any(properties.values()) or damage(rows)['guardpoints']:
            raise ValueError('HIT_BLOCK_NONDEFAULT_PROPERTIES_OWNER_REQUIRED')
        vector=fr['models'][i]['defense']
        if vector[1]!=0 or vector[3]!=0:raise ValueError('HIT_BLOCK_NONZERO_FACTORS_OWNER_REQUIRED')
        block=[a for a in ar['animations']if a['model']==m['declaration'] and a['engine_animation_id']==config['authority']['enum']['ANI_BLOCK']]
        models.append(dict(id=i,identity=m['declaration'],source_sha256=doc['sha256'],properties=properties,guardpoints_max=0,
            policy=policy(rows),authored_block_handles=[a['handle']for a in block if a['numframes']]))
    return dict(schema='BYOR_HIT_BLOCK_REQUIREMENTS_V1',capability='SOURCE_DEFAULT_BLOCK_PROPERTIES_NO_COUNTER',engine_commit=ENGINE_COMMIT,
        block_role=config['authority']['enum']['ANI_BLOCK'],maximum_animations=ar['maximum_animations'],models=models,
        animations=ar['animations'],counter_range=[-1,-1],uniform_blockpower=0,uniform_blockthreshold=0,
        initial_self_defense_threshold_requirement='capture the actual initial self vector before the source attack prefix; this closed capability permits zero only',
        inair_policy='explicit ACCEPTED_COMPAT_Q16_16 predicate; no arbitrary binary32 equivalence claim',
        source_rand32_required=True,model_and_counter_property_mutators_admitted=False,
        actual_blocking_damage_bodies_bound=False,production_world_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
