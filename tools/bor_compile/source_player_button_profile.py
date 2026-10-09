"""Source-derived absent alternate button actions, with live BLOCK admission."""
from source_model_core_4086 import derive as model_core
from script_dispatch_4086 import compile_source
ABSENT_ROLES=('attackboth','charge','special2')
def derive(source):
    models=model_core(source)['models'];animations=compile_source(source)['animation_handles'];result=[]
    for m in models:
        present=[a['role']for a in animations if a['model']==m['identity'] and a['role']in ABSENT_ROLES]
        if present:raise ValueError('PLAYER_BUTTON_OTHER_ACTION_OWNER_REQUIRED:'+m['identity'])
        result.append(dict(id=m['id'],source_sha256=m['source_sha256']))
    return dict(capability='READONLY_ABSENT_ALTERNATE_BUTTON_ACTIONS',models=result,absent_roles=list(ABSENT_ROLES),
        present_block_requires_owner=True,direct_animation_table_mutation_admitted=False,native_bound=False,motu_gameplay_proven=False)
