"""Compile literal pinned loader range statements and compare derived rows."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from compiler import Source, key
from source_profile import document, discover
from source_animation_range_4086 import load, derive, pack, unpack, FIELDS
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output = a.output.resolve(); a.output.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', 'show', ENGINE_COMMIT+':engine/openbor.c'], cwd='E:/gh/openbor-bcec').decode('latin1')
    translator = extract(raw, 'translate_ani_id')
    overrides = []
    for role in ('jump', 'upper', 'jumpattack', 'block'):
        start = translator.index('else if(stricmp(value, "'+role+'") == 0)')
        end = translator.find('    else if(', start+10)
        assert end > start
        overrides.append(translator[start:end])
    default_start = raw.index('                if(!newanim->range.min.x)')
    default_end = raw.index('                newanim->jumpframe.velocity.y', default_start)
    defaults = raw[default_start:default_end]
    commands = []
    names = ('JUMPHEIGHT', 'GRABDISTANCE', 'RANGE', 'RANGEZ', 'RANGEA', 'RANGEB')
    for name in names:
        match = re.search(r'            case CMD_MODEL_'+name+r':.*?                break;', raw, re.S)
        assert match
        commands.append(match[0])
    # Detect authority drift/additional role range writes, rather than silently
    # verifying a hand-picked list against itself.
    assert len(re.findall(r'newanim->range\.(?:min|max)\.', translator)) == sum(len(re.findall(r'newanim->range\.(?:min|max)\.', b)) for b in overrides)
    source = Source(a.source); docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    discovery = discover(source, docs)
    rows = [dict(identity=m['declaration'], rows=docs[key(m['source_path'])]['directives']) for m in discovery['models']]
    def row(name, *values): return dict(directive=name, values=list(map(str, values)), line=1)
    for height in ('4', '4.9', '3.99', '-1.9', '0', '8'):
        for distance in ('36', '35.9', '-35.9', '0', '2.9'):
            for role in ('idle', 'jump', 'upper', 'jumpattack', 'jumpattack2', 'block'):
                rows.append(dict(identity='numeric-defaults', rows=[row('jumpheight', height), row('grabdistance', distance), row('anim', role)]))
    for name in ('range', 'rangez', 'rangea', 'rangeb'):
        for values in ((), ('7',), ('0','0'), ('12tail','-9other'), ('2147483647','2147483647'), ('-2147483648','2147483647')):
            rows.append(dict(identity='atoi-and-equality', rows=[row('anim','idle'), row(name, *values)]))
    rows.append(dict(identity='model-order', rows=[row('anim','idle'),row('jumpheight','9.9'),row('grabdistance','17.9'),row('anim','jumpattack'),row('range','0','0'),row('anim','walk')]))
    code = '''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {int x,z,y,base;} axes;
typedef struct {struct {axes min,max;}range;} animation;
typedef struct {float jumpheight,grabdistance;} model;
typedef struct {int counterattack;} attack_t;
#define GET_ARG(i) args[i]
#define GET_INT_ARG(i) atoi(GET_ARG(i))
#define GET_FLOAT_ARG(i) atof(GET_ARG(i))
enum {ANI_JUMP,ANI_UPPER,ANI_JUMPATTACK,ANI_BLOCK};
'''+ 'enum {'+','.join('CMD_MODEL_'+n for n in names)+'};\n'
    code += 'void begin(char*value,model*newchar,animation*newanim){int ani_id=0;attack_t a,*attack=&a;'+defaults+'\nif(0){}\n'+'\n'.join(overrides)+'\n}\n'
    code += 'void command(int cmd,char**args,model*newchar,animation*newanim){char*shutdownmessage;switch(cmd){'+'\n'.join(commands)+'}return;lCleanup:exit(3);}\n'
    code += 'int main(void){model m,*newchar=&m;animation anim,*newanim=&anim;char*args[32];\n'
    expected = []
    for case in rows:
        expected.extend(v['ranges'] for v in load(case['rows']))
        code += 'newchar->jumpheight=4.0f;newchar->grabdistance=36.0f;\n'
        active = False
        for r in case['rows']:
            n, v = r['directive'], r['values']
            if n == 'anim':
                if active: code += 'printf("%d,%d,%d,%d,%d,%d,%d,%d\\n",'+','.join('newanim->range.'+f for f in FIELDS)+');\n'
                code += 'memset(newanim,0,sizeof(anim));begin('+json.dumps(' '.join(v))+',newchar,newanim);\n'; active = True
            elif n.upper() in names:
                code += ''.join('args['+str(i)+']='+json.dumps(v[i-1] if i and i<=len(v) else '')+';' for i in range(32))+'\n'
                code += 'command(CMD_MODEL_'+n.upper()+',args,newchar,newanim);\n'
        if active: code += 'printf("%d,%d,%d,%d,%d,%d,%d,%d\\n",'+','.join('newanim->range.'+f for f in FIELDS)+');\n'
    code += 'return 0;}\n'; (a.output/'animation_range.c').write_text(code)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','animation_range.c','-fe=animation_range.exe'], cwd=a.output, env=env, capture_output=True, text=True)
    (a.output/'build.log').write_text(build.stdout+build.stderr); assert build.returncode == 0
    log = subprocess.check_output([str(a.output/'animation_range.exe')], cwd=a.output, text=True)
    (a.output/'authority.log').write_text(log); actual = [list(map(int,l.split(','))) for l in log.splitlines()]
    ir = derive(source); table = pack(ir)
    assert unpack(table) == [v['ranges'] for v in sorted(ir['animations'], key=lambda v:v['handle'])]
    ok = actual == expected
    report = dict(schema='BYOR_4086_ANIMATION_RANGE_AUTHORITY_V1',status='PASS' if ok else 'FAIL',engine_commit=ENGINE_COMMIT,
                  source_subset_sha256=hashlib.sha256((defaults+'\n'.join(overrides+commands)).encode()).hexdigest(),
                  cases=len(actual),inputs=rows,actual=actual,expected=expected,source_animations=len(ir['animations']),
                  table_bytes=len(table),table_sha256=hashlib.sha256(table).hexdigest(),literal_range_statements_unmodified=True,
                  full_loader_executed=False,runtime_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n'); print(report['status'],len(actual),'literal loader animation range rows'); assert ok


if __name__ == '__main__': main()
