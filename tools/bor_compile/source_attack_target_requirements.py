"""Closed target-filter requirements from source animation and collision data."""
import hashlib,re,subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_frame_state_4086 import derive,pack,unpack
from source_model_core_4086 import integer
from source_model_registry import derive as registry


def derive_requirements(source,engine='E:/gh/openbor-bcec'):
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
    if 'newanim->attackone = -1;'not in raw:raise ValueError('ATTACK_TARGET_ANIMATION_DEFAULT_AUTHORITY')
    translate=extract(raw,'translate_ani_id')
    positive_roles=re.findall(r'stricmp\(value, "([^"]+)"\)[\s\S]*?\{([^{}]*)\}',translate)
    positive={name for name,body in positive_roles if 'newanim->attackone = 1;'in body}
    if len(positive)!=10:raise ValueError('ATTACK_TARGET_ANIMATION_ROLE_AUTHORITY')
    ir=derive(source);models=registry(source)['models'];table=pack(ir);data=unpack(table);animations=[]
    for anim in ir['animations']:
        value=1 if anim['role']in positive else -1
        for r in anim['retained_directives']:
            if r['directive']=='attackone':value=integer(r['values'])
        if value>0:raise ValueError('ATTACK_TARGET_POSITIVE_ATTACKONE_STATE_REQUIRED')
        animations.append(dict(handle=anim['handle'],source_sha256=anim['source_sha256'],attackone=value))
    return dict(schema='BYOR_ATTACK_TARGET_REQUIREMENTS_V1',capability='SOURCE_NONPOSITIVE_ATTACKONE_TARGET_FILTER',engine_commit=ENGINE_COMMIT,animations=animations,models=models,model_count=len(models),collision_table_sha256=hashlib.sha256(table).hexdigest(),collision_table_bytes=len(table),attacks=data['attacks'],dynamic_attackone_writers_admitted=False,followup_policy='a -1 followup inherits a nonpositive current value, retaining false attackone>0 predicate',native_filter_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
