"""Source-derived closed ordinary jump attack requirements, never actor names."""
from source_profile import document
from source_model_core_4086 import derive as model_core,integer
from script_dispatch_4086 import compile_source

ABSENT_ROLES=('jumpspecial','jumpattack2','jumpattack3','runjumpattack','jumpforward')


def derive(source):
    models=model_core(source)['models'];animations=compile_source(source)['animation_handles'];result=[]
    for m in models:
        flags=dict(jumpmovex=0,jumpmovez=0)
        for row in document(source,m['source_path'])['directives']:
            if row['directive']=='jumpmove':flags=dict(jumpmovex=integer(row['values']),jumpmovez=integer(row['values'],1))
        present=[a['role']for a in animations if a['model']==m['identity']and a['role']in ABSENT_ROLES]
        if any(flags.values())or present:raise ValueError('PLAYER_JUMP_OTHER_AIR_OWNER_REQUIRED:'+m['identity'])
        result.append(dict(id=m['id'],source_sha256=m['source_sha256'],fields=flags))
    return dict(capability='READONLY_ZERO_AIR_CONTROL_DEFAULT_ATTACK',models=result,absent_roles=list(ABSENT_ROLES),
        authority='calloc jumpmovex/jumpmovez; CMD_MODEL_JUMPMOVE; complete immutable animation universe',
        required_noaircancel=0,direct_air_flag_mutation_admitted=False,native_bound=False,motu_gameplay_proven=False)
