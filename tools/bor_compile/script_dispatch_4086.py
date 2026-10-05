"""Compile loader-derived animation wrappers through generic source bytecode."""
import argparse
import json
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from script_ir_4086 import parse_script,inspect
from script_bytecode import compile_library
from dialect_4086 import ENGINE_COMMIT
from source_animation_ids import configure,role_id


def compile_source(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);registry=docs[key(structure['models_path'])]['directives']
    animation_ids=configure(registry)
    compatibility=[r for r in registry if r['directive']=='nocmdcompatible']
    if compatibility and int(compatibility[-1]['values'][0])!=0:
        raise ValueError('SCRIPT_NOCMDCOMPATIBLE_POLICY_UNSUPPORTED')
    frontend=inspect(source)
    if frontend['diagnostics']:raise ValueError('SCRIPT_SOURCE_BINDING_FAILURE')
    handles=[];programs=[]
    for model in structure['models']:
        roles={}
        for animation in model['animations']:
            role=animation['role']
            if role in roles:raise ValueError('SCRIPT_DUPLICATE_ANIMATION_REQUIRES_LOADER_AUTHORITY')
            roles[role]=len(handles)+1
            handles.append(dict(handle=roles[role],model=model['declaration'],source_path=model['source_path'],
                                role=role,engine_animation_id=role_id(animation_ids,role)))
        if not model['scripts'] and not model['inline_scripts']:continue
        functions=''
        if model['scripts']:
            functions=source.read(model['scripts'][0]['values'][0]).decode('latin1')
        blocks={b['line']:b for b in model['inline_scripts']}
        groups=[];body=None;frame=0;role=None
        for row in docs[key(model['source_path'])]['directives']:
            name=row['directive'];values=row['values']
            if name=='anim':
                role=' '.join(values);frame=0;body=[];groups.append((role,body))
            elif name=='frame':frame+=1
            elif name=='@cmd':
                if body is None:raise ValueError('SCRIPT_FRAME_COMMAND_OUTSIDE_ANIMATION')
                body.append('if(frame=='+str(frame)+'){'+values[0]+'('+','.join(values[1:])+');}')
            elif name=='@script':
                if body is None:raise ValueError('SCRIPT_GLOBAL_INLINE_WRAPPER_UNSUPPORTED')
                body.extend(blocks[row['line']]['text'])
        wrapper='void main(){int frame=getlocalvar("frame");int animhandle=getlocalvar("animhandle");\n'
        for role,body in groups:
            if body:wrapper+='if(animhandle=='+str(roles[role])+'){\n'+'\n'.join(body)+'\nreturn;}\n'
        wrapper+='}'
        library=parse_script(functions+'\n'+wrapper,model['source_path']+'#generated-animation-wrapper')
        library['asset_sha256']=docs[key(model['source_path'])]['sha256']
        compiled=compile_library(library,frontend['engine_api_requirements'])
        programs.append(dict(model=model['declaration'],source_path=model['source_path'],
            wrapper=wrapper,program=compiled,entry_function='main',native_bound=False))
    return dict(schema='BYOR_4086_ANIMATION_SCRIPT_PROGRAM_V1',engine_authority=ENGINE_COMMIT,
        programs=programs,animation_handles=handles,no_cmd_compatible=0,
        wrapper_semantics='main reads frame/animhandle; animation guard encloses source-order commands and inline bodies',
        execution_requirements=['update_frame executes script after setting animpos and nextanim',
            'self/animnum/frame/animhandle installed as local variants',
            'current model script followed by distinct default model script',
            'original local frame snapshot persists if a command changes animation/frame',
            'update_frame aborts subsequent frame side effects after animation/frame interruption'],
        native_vm_bound=False,entity_api_bound=False,source_numeric_native_equivalence=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=compile_source(Source(a.source))
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(models=len(r['programs']),animation_handles=len(r['animation_handles']),
        bytecode_bytes=sum(m['program']['bytecode_bytes'] for m in r['programs']),native_bound=False)))


if __name__=='__main__':main()
