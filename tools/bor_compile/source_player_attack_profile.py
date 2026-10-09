"""Derive readonly absent alternate attacks; retain RUNATTACK and GET queries."""
from source_model_core_4086 import derive as model_core
from script_dispatch_4086 import compile_source
ABSENT_ROLES=('duckattack','attackbackward','throwattack')


def derive(source):
    models=model_core(source)['models'];animations=compile_source(source)['animation_handles'];result=[]
    for m in models:
        declared=[a['role']for a in animations if a['model']==m['identity']]
        if any(r in declared for r in ABSENT_ROLES):raise ValueError('PLAYER_ATTACK_OTHER_OWNER_REQUIRED:'+m['identity'])
        result.append(dict(id=m['id'],source_sha256=m['source_sha256'],runattack_present='runattack'in declared,get_present='get'in declared))
    return dict(capability='READONLY_ALTERNATE_ATTACK_ABSENCE_WITH_EMPTY_ITEM_SEARCH',models=result,absent_roles=list(ABSENT_ROLES),
        matching_live_item_candidates_require_full_owner=True,direct_animation_table_mutation_admitted=False,attack_chain_and_punch_services_required=True,native_bound=False,motu_gameplay_proven=False)
