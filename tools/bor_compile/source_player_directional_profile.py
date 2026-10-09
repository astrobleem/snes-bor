"""Derive the run-only directional capability from immutable animation roles."""
from source_model_core_4086 import derive as model_core
from script_dispatch_4086 import compile_source
ABSENT_ROLES=('duck','attackup','attackdown','attackforward','dodge')
def derive(source):
    models=model_core(source)['models'];animations=compile_source(source)['animation_handles'];result=[]
    for m in models:
        present=[a['role']for a in animations if a['model']==m['identity'] and a['role']in ABSENT_ROLES]
        if present:raise ValueError('PLAYER_DIRECTIONAL_OTHER_OWNER_REQUIRED:'+m['identity'])
        result.append(dict(id=m['id'],source_sha256=m['source_sha256']))
    return dict(capability='READONLY_DIRECTIONAL_RUN_ONLY',models=result,absent_roles=list(ABSENT_ROLES),platform_duck_body_unreachable=True,
        direct_animation_table_mutation_admitted=False,native_bound=False,motu_gameplay_proven=False)
