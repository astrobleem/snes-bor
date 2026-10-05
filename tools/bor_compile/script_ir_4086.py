"""Generic source-script AST and binding discovery, without native admission.

OpenBOR script uses C syntax with variant values (including void variables).
This frontend preserves declared types and numeric spelling. It does not
impose C type checking or silently substitute a function-name implementation.
Requires pycparser; unsupported syntax fails explicitly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from importlib.metadata import version
from pycparser import c_parser,c_ast
from compiler import Source,key
from source_profile import document,discover
from dialect_4086 import ENGINE_COMMIT,animation_frames


def strip_comments(text):
    pattern=r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    def replace(match):
        value=match.group(0)
        return ''.join('\n' if c=='\n' else ' ' for c in value) if value.startswith(('//','/*')) else value
    return re.sub(pattern,replace,text)


SUPPORTED=frozenset(('FileAST','FuncDef','Decl','FuncDecl','TypeDecl','IdentifierType',
    'ParamList','Compound','If','Return','Assignment','UnaryOp','BinaryOp','FuncCall',
    'ExprList','ID','Constant','EmptyStatement','Cast','Typename','TernaryOp'))


def lower(node):
    if node is None:return None
    kind=type(node).__name__
    if kind not in SUPPORTED:raise ValueError('SCRIPT_AST_UNSUPPORTED: '+kind+' at '+str(node.coord))
    result={'kind':kind}
    for name in node.attr_names:
        value=getattr(node,name)
        if value is not None:result[name]=value
    result['children']=[dict(edge=edge,node=lower(child)) for edge,child in node.children()]
    if node.coord:result['source_line']=node.coord.line
    return result


class Calls(c_ast.NodeVisitor):
    def __init__(self):self.calls=set()
    def visit_FuncCall(self,node):
        if not isinstance(node.name,c_ast.ID):raise ValueError('SCRIPT_INDIRECT_CALL_UNSUPPORTED')
        self.calls.add(node.name.name);self.generic_visit(node)


def parse_script(text,path):
    normalized=re.sub(r'\r+\n','\n',text).replace('\r','\n')
    tree=c_parser.CParser().parse(strip_comments(normalized),filename=path)
    functions={}
    for node in tree.ext:
        if not isinstance(node,c_ast.FuncDef):raise ValueError('SCRIPT_GLOBAL_DECLARATION_UNSUPPORTED: '+str(node.coord))
        name=node.decl.name
        if name in functions:raise ValueError('SCRIPT_DUPLICATE_FUNCTION: '+name)
        calls=Calls();calls.visit(node)
        params=node.decl.type.args.params if node.decl.type.args else []
        params=[p for p in params if not (isinstance(p,c_ast.Typename) and p.type.type.names==['void'])]
        functions[name]=dict(name=name,parameters=[lower(p) for p in params],arity=len(params),
            calls=sorted(calls.calls),ast=lower(node),native_lowered=False)
    return dict(source_path=path,source_sha256=hashlib.sha256(text.encode('latin1')).hexdigest(),
                functions=functions,native_lowered=False)


def inspect(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);libraries={};bindings=[];inline=[];errors=[]
    for model in structure['models']:
        scripts=model['scripts']
        if len(scripts)>1:raise ValueError('MULTIPLE_ANIMATION_SCRIPTS_REQUIRE_LOADER_AUTHORITY')
        library=None
        if scripts:
            path=source.resolve(scripts[0]['values'][0]);identity=key(path)
            if identity not in libraries:
                raw=source.read(path)
                libraries[identity]=parse_script(raw.decode('latin1'),path)
                libraries[identity]['asset_sha256']=hashlib.sha256(raw).hexdigest()
            library=libraries[identity]
        animations=animation_frames(docs[key(model['source_path'])]['directives'])
        for animation in animations:
            for event in animation['events']:
                function=library['functions'].get(event['function']) if library else None
                binding=dict(model=model['declaration'],animation=animation['role'],frame_index=event['frame_index'],
                    declaration=event['declaration'],function=event['function'],arguments=event['arguments'],
                    source_tick=event['start_tick'],library=library['source_path'] if library else None,
                    source_function_bound=bool(function),native_lowered=False)
                if function and len(event['arguments'])!=function['arity']:
                    errors.append(dict(code='SCRIPT_CALL_ARITY',binding=binding,expected=function['arity']))
                elif not function:errors.append(dict(code='SCRIPT_FUNCTION_UNBOUND',binding=binding))
                else:
                    expression='void __call(){'+event['function']+'('+','.join(event['arguments'])+');}'
                    binding['argument_call_ast']=parse_script(expression,model['source_path'])['functions']['__call']['ast']
                bindings.append(binding)
        for ordinal,block in enumerate(model['inline_scripts']):
            role=next((a['role'] for a in reversed(animations) if a['declaration']['line']<block['line']),None)
            text='void __inline(){\n'+'\n'.join(block['text'])+'\n}'
            parsed=parse_script(text,block['source_path'])
            inline.append(dict(model=model['declaration'],animation=role,declaration=block,
                ast=parsed['functions']['__inline']['ast'],calls=parsed['functions']['__inline']['calls'],
                wrapper_runtime_semantics_bound=False,native_lowered=False))
    engine_calls=sorted({call for lib in libraries.values() for f in lib['functions'].values()
                         for call in f['calls'] if call not in lib['functions']} |
                        {call for block in inline for call in block['calls']})
    return dict(schema='BYOR_SCRIPT_AST_4086_V1',engine_authority=ENGINE_COMMIT,libraries=libraries,
        bindings=bindings,inline_blocks=inline,diagnostics=errors,engine_api_requirements=engine_calls,
        frontend=dict(parser='pycparser',version=version('pycparser')),
        variant_authority=dict(parser_path='engine/source/scriptlib/Parser.c',
            assignment_path='engine/source/scriptlib/ScriptVariant.c',
            declared_types_ignored=True,decimal_storage='DOUBLE',integer_division='truncate toward zero',
            divide_by_zero='VT_EMPTY',unary_plus='NO_OP_ALL_VARIANTS',
            decimal_negation='DOUBLE sign flip followed by LONG low-word negation through union fallthrough',
            signed_overflow='UNPROVEN_FAIL_CLOSED',native_numeric_equivalence_proven=False),
        native_lowered=False,numeric_runtime_semantics_bound=False,
        status='SOURCE_SCRIPT_BINDINGS_PROVEN' if not errors else 'SOURCE_SCRIPT_BINDING_FAILURE',
        scope='Source syntax, function identity and arity only. No VM, native command execution or engine API admission.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=inspect(Source(a.source))
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('libraries','bindings','inline_blocks')}))
    if r['diagnostics']:raise SystemExit(1)


if __name__=='__main__':main()
