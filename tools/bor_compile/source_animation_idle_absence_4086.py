"""Derive immutable absence of frame idle arrays from the complete source set.

BOR clears alloc_anim, initializes/resets loader idle=0, and allocates the
array in addframe only for nonzero idle. Explicit zero directives also fit.
Present idle arrays require a full frame-property owner, never a busy guess.
"""
from source_profile import document
from source_model_core_4086 import derive as model_core,integer
from script_dispatch_4086 import compile_source

def derive(source):
    models=model_core(source)['models'];animations=compile_source(source)['animation_handles'];result=[]
    for m in models:
        doc=document(source,m['source_path'])
        for row in doc['directives']:
            if row['directive']=='idle' and integer(row['values'])!=0:
                raise ValueError('ANIMATION_IDLE_ARRAY_OWNER_REQUIRED:'+m['identity'])
        result.append(dict(id=m['id'],source_sha256=m['source_sha256'],handles=[a['handle']for a in animations if a['model']==m['identity']]))
    return dict(capability='IMMUTABLE_ABSENT_ANIMATION_IDLE_ARRAY',models=result,
        authority='BOR alloc_anim memset; loader initial/reset idle=0; CMD_MODEL_IDLE; addframe conditional allocation',
        direct_frame_property_mutation_admitted=False,native_bound=False,motu_gameplay_proven=False)
