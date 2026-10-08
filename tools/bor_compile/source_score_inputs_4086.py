"""Source-derived score globals and score-script presence capabilities."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_model_core_4086 import integer
from source_profile import document,discover
from script_nested_authority import extract


def derive(source,engine=Path('E:/gh/openbor-bcec')):
    raw=subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    match=re.search(r'unsigned int\s+lifescore\s*=\s*(\d+)\s*;',raw)
    if not match:raise ValueError('SOURCE_LIFESCORE_DEFAULT_AUTHORITY')
    set_initializer=re.search(r's_set_entry \*add_set\(\)\s*\{.*?\n\}',raw,re.S)
    if not set_initializer or 'memset(set, 0, sizeof(*set));'not in set_initializer[0]:raise ValueError('SOURCE_SET_ZERO_INITIALIZATION_AUTHORITY')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs)
    registry=docs[key(structure['models_path'])];lifescore=int(match[1]);declarations=[]
    for row in registry['directives']:
        if row['directive']=='lifescore':lifescore=integer(row['values'])&0xffffffff;declarations.append(row)
    if not lifescore:raise ValueError('SOURCE_LIFESCORE_DIVISION_BY_ZERO')
    scripts=[]
    for i in range(4):
        name='data/scripts/score'+str(i+1)+'.c'
        # The pinned startup names are the authority, not model declarations.
        if not re.search(r'load_script\(&score_script\['+str(i)+r'\]\s*,\s*"'+re.escape(name)+r'"\)',raw):raise ValueError('SOURCE_SCORE_SCRIPT_PATH_AUTHORITY')
        present=key(name)in source.index
        scripts.append(dict(player_index=i,source_path=name,present=present,source_sha256=hashlib.sha256(source.read(name)).hexdigest()if present else None))
    routes=[]
    for s in structure['sets']:
        mp_mode=0
        for r in s['settings']:
            if r['directive']=='typemp':mp_mode=integer(r['values'])
        routes.append(dict(source_set=s['id'],name=s['name'],magic_type=mp_mode,hit_mp_add_is_source_no_op=mp_mode!=1))
    return dict(schema='BYOR_4086_SCORE_INPUTS_V1',engine_commit=ENGINE_COMMIT,
                registry_source=registry['source_path'],registry_sha256=registry['sha256'],lifescore=lifescore,lifescore_declarations=declarations,
                score_scripts=scripts,score_script_presence_mask=sum(1<<r['player_index']for r in scripts if r['present']),
                absent_score_scripts_capability=not any(r['present']for r in scripts),sets=routes,
                set_zero_initialization_sha256=hashlib.sha256(set_initializer[0].encode('latin1')).hexdigest(),
                source_addscore_sha256=hashlib.sha256(extract(raw,'addscore').encode('latin1')).hexdigest(),
                hit_mp_source_function_sha256=hashlib.sha256(extract(raw,'checkmpadd').encode('latin1')).hexdigest(),
                native_global_installation_bound=False,extra_life_service_proven=False,score_script_service_proven=False,motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=derive(Source(a.source),a.engine);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print('lifescore',r['lifescore'],'score script mask',r['score_script_presence_mask'],'sets',r['sets'])


if __name__=='__main__':main()
