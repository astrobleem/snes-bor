"""Derive immutable zero nopain/noflip and uniform zero defense pain."""
import subprocess
from compiler import key
from source_profile import document,discover
from source_model_core_4086 import integer
from source_model_factors import derive as factors
from dialect_4086 import ENGINE_COMMIT


def derive(source,engine='E:/gh/openbor-bcec'):
    raw=subprocess.check_output(['git','-C',engine,'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    for text in ('s_model *newchar = calloc(1, sizeof(*newchar));','newchar->nopain = GET_INT_ARG(1);','newchar->noflip = GET_INT_ARG(2);'):
        if text not in raw:raise ValueError('DAMAGE_FLIP_LOADER_AUTHORITY')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);f=factors(source);models=[]
    for i,m in enumerate(structure['models']):
        doc=docs[key(m['source_path'])];nopain=noflip=0
        for r in doc['directives']:
            if r['directive']=='subclass':raise ValueError('DAMAGE_FLIP_SUBCLASS_OWNER_REQUIRED')
            if r['directive']=='nopain':nopain=integer(r['values'])
            if r['directive']=='nomove':noflip=integer(r['values'],1)
        if nopain or noflip or f['models'][i]['defense'][5]:raise ValueError('DAMAGE_FLIP_NONDEFAULT_MODEL_OWNER_REQUIRED:'+m['declaration'])
        models.append(dict(id=i,identity=m['declaration'],source_sha256=doc['sha256'],nopain=0,noflip=0,defense_pain=0))
    return dict(schema='BYOR_DAMAGE_FLIP_REQUIREMENTS_V1',capability='SOURCE_ZERO_PAIN_ZERO_NOFLIP',engine_commit=ENGINE_COMMIT,models=models,model_policy_mutators_admitted=False,attack_descriptor_owner_bound=False,production_callback_bound=False,no_color_reduction=True)
