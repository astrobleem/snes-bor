"""Source-derived player death model policy and global script dependencies.

Missing global hooks follow the pinned loader's clear-on-load-failure path.
Present hooks remain required children; they are never silently skipped.
"""
import argparse,hashlib,json,re,struct,subprocess,zlib
from pathlib import Path
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_damage_tail_model_policy import derive as model_policy
from source_model_core_4086 import integer
from source_profile import document,discover
from script_nested_authority import extract


def derive(source):
    raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs)
    if structure['diagnostics']:raise ValueError('PLAYER_DEATH_SOURCE_DIAGNOSTICS')
    policy=0;declarations=[]
    for row in docs[key(structure['models_path'])]['directives']:
        if row['directive']=='nomaxrushreset':
            policy=integer(row['values']);declarations.append(row)
    loader=re.search(r'case CMD_MODELSTXT_NOMAXRUSHRESET\s*:(.*?)break;',raw,re.S)
    if not loader or 'nomaxrushreset[4] = GET_INT_ARG(1);'not in loader[0]:
        raise ValueError('PLAYER_DEATH_RUSH_POLICY_AUTHORITY')
    if not re.search(r'nomaxrushreset\[5\]\s*=\s*\{0,\s*0,\s*0,\s*0,\s*0\}',raw):
        raise ValueError('PLAYER_DEATH_RUSH_DEFAULT_AUTHORITY')
    hooks=[];functions={}
    for family,array,function in (('die','pdie_script','execute_pdie_script'),('respawn','respawn_script','execute_respawn_script')):
        body=extract(raw,function)
        if f'Script_IsInitialized(&{array}[index])'not in body or f'Script_Execute(&{array}[index])'not in body:
            raise ValueError('PLAYER_DEATH_HOOK_EXECUTION_AUTHORITY')
        functions[function]=hashlib.sha256(body.encode('latin1')).hexdigest()
        for index in range(4):
            path=f'data/scripts/{family}{index+1}.c'
            pattern=r'if\(!load_script\(&'+array+r'\['+str(index)+r'\],\s*"'+re.escape(path)+r'"\)\)\s*\{\s*Script_Clear\(&'+array+r'\['+str(index)+r'\],\s*2\);'
            if not re.search(pattern,raw):raise ValueError('PLAYER_DEATH_HOOK_LOAD_AUTHORITY')
            present=key(path)in source.index
            hooks.append(dict(family=family,player_index=index,source_path=source.resolve(path)if present else path,
                              source_sha256=hashlib.sha256(source.read(path)).hexdigest()if present else None,
                              disposition='SCRIPT_CHILD_BINDING_REQUIRED'if present else'UNINITIALIZED_HOOK_NO_EXECUTION'))
    policies=model_policy(source)
    models=[dict(id=m['id'],identity=m['identity'],source_sha256=m['source_sha256'],nodieblink=m['fields']['nodieblink'],
                 weaploss_type=m['fields']['weaploss_type'])for m in policies['models']]
    return dict(schema='BYOR_PLAYER_DEATH_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,models=models,hooks=hooks,
                rush_reset_policy=policy,rush_policy_declarations=declarations,hook_function_sha256=functions,
                model_loader_authority_sha256=policies['source_authority_sha256'],
                absent_hooks_source_derived=True,initialized_hooks_bound=False,model_policy_mutators_admitted=False,
                native_player_die_bound=False,production_binding=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack_models(report):
    models=report['models']
    if not 1<=len(models)<=128:raise ValueError('PLAYER_DEATH_MODEL_CAPACITY')
    payload=bytearray()
    for index,model in enumerate(models):
        if model['id']!=index or not -2147483648<=model['nodieblink']<=2147483647:
            raise ValueError('PLAYER_DEATH_MODEL_RECORD')
        payload.extend(struct.pack('<HHi',index,0,model['nodieblink']))
    return struct.pack('<4sHHHHI',b'B4PD',1,8,len(models),0,zlib.crc32(payload)&0xffffffff)+payload


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);r=derive(Source(a.source));data=pack_models(r)
    (a.output/'model_policy.bin').write_bytes(data)
    r.update(packed_model_policy_bytes=len(data),packed_model_policy_sha256=hashlib.sha256(data).hexdigest())
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(len(r['models']),'source model policies;',sum(h['source_sha256']is not None for h in r['hooks']),'required global script children; rush policy',r['rush_reset_policy'])


if __name__=='__main__':main()
