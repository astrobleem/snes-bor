"""Compile source-script ASTs to generic variant bytecode; no native VM claim.

Declared C types are ignored as in the selected 4086 parser. Constants retain
signed 32-bit integer / binary64 decimal identity. Logical operands are eager,
matching Parser_Log_or_expr2/Parser_Log_and_expr2, not C short-circuit rules.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct

OPS=['EMPTY','CONST','LOAD','STORE','DROP','CALL','BR_FALSE','JUMP','RETURN',
     'ADD','SUB','MUL','DIV','MOD','EQ','NE','LT','LE','GT','GE','AND','OR',
     'BIT_AND','BIT_OR','XOR','SHL','SHR','NEG','POS','NOT']
BINARY={'+':'ADD','-':'SUB','*':'MUL','/':'DIV','%':'MOD','==':'EQ','!=':'NE',
        '<':'LT','<=':'LE','>':'GT','>=':'GE','&&':'AND','||':'OR','&':'BIT_AND',
        '|':'BIT_OR','^':'XOR','<<':'SHL','>>':'SHR'}


def child(node,edge,default=None):
    return next((c['node'] for c in node['children'] if c['edge']==edge),default)


class FunctionCompiler:
    def __init__(self,function,functions,builtins,constants):
        self.function=function;self.functions=functions;self.builtins=builtins
        self.constants=constants;self.code=bytearray();self.scopes=[{}];self.locals=[]
        for p in function['parameters']:self.declare(p['name'])

    def declare(self,name):
        if name in self.scopes[-1]:raise ValueError('SCRIPT_LOCAL_DUPLICATE: '+name)
        index=len(self.locals);self.locals.append(name);self.scopes[-1][name]=index
        if index>255:raise ValueError('SCRIPT_LOCAL_CAPACITY')
        return index

    def local(self,name):
        for scope in reversed(self.scopes):
            if name in scope:return scope[name]
        raise ValueError('SCRIPT_IDENTIFIER_UNBOUND: '+name)

    def emit(self,op,operand=None):
        address=len(self.code);self.code.append(OPS.index(op))
        if op in ('CONST','CALL','BR_FALSE','JUMP'):self.code.extend(struct.pack('<H',operand or 0))
        elif operand is not None:self.code.append(operand)
        return address

    def patch(self,address,target):
        if target>65535:raise ValueError('SCRIPT_FUNCTION_BYTECODE_CAPACITY')
        self.code[address+1:address+3]=struct.pack('<H',target)

    def expression(self,node):
        kind=node['kind']
        if kind=='Constant':
            spelling=node['value'];ctype=node['type']
            if ctype=='string':value=dict(type='STRING',value=ast.literal_eval(spelling))
            elif ctype in ('float','double'):
                number=float(spelling.rstrip('fFlL'))
                value=dict(type='DECIMAL64',little_endian=struct.pack('<d',number).hex(),spelling=spelling)
            elif ctype=='int':
                number=int(spelling,16 if spelling.lower().startswith('0x') else 10)
                if not -2147483648<=number<=2147483647:raise ValueError('SCRIPT_INT32_CONSTANT_RANGE')
                value=dict(type='INTEGER32',value=number)
            else:raise ValueError('SCRIPT_CONSTANT_TYPE_UNSUPPORTED: '+ctype)
            if value not in self.constants:self.constants.append(value)
            if len(self.constants)>65536:raise ValueError('SCRIPT_CONSTANT_POOL_CAPACITY')
            self.emit('CONST',self.constants.index(value))
        elif kind=='ID':self.emit('LOAD',self.local(node['name']))
        elif kind=='BinaryOp':
            self.expression(child(node,'left'));self.expression(child(node,'right'))
            if node['op'] not in BINARY:raise ValueError('SCRIPT_BINARY_UNSUPPORTED: '+node['op'])
            self.emit(BINARY[node['op']])
        elif kind=='UnaryOp':
            if node['op'] not in ('-','+','!'):raise ValueError('SCRIPT_UNARY_UNSUPPORTED: '+node['op'])
            self.expression(child(node,'expr'));self.emit({'-':'NEG','+':'POS','!':'NOT'}[node['op']])
        elif kind=='FuncCall':
            name=child(node,'name')
            if name['kind']!='ID':raise ValueError('SCRIPT_INDIRECT_CALL_UNSUPPORTED')
            name=name['name'];args=child(node,'args');args=[c['node'] for c in args['children']] if args else []
            for arg in args:self.expression(arg)
            if name in self.functions:
                target=self.functions[name]
                if len(args)!=target['arity']:raise ValueError('SCRIPT_SOURCE_CALL_ARITY: '+name)
                address=target['id']
            elif name in self.builtins:address=0x8000+self.builtins.index(name)
            else:raise ValueError('SCRIPT_CALL_UNBOUND: '+name)
            if len(args)>255:raise ValueError('SCRIPT_CALL_ARGUMENT_CAPACITY')
            self.emit('CALL',address);self.code.append(len(args))
        elif kind=='Assignment':
            target=child(node,'lvalue')
            if target['kind']!='ID':raise ValueError('SCRIPT_ASSIGNMENT_TARGET_UNSUPPORTED')
            index=self.local(target['name'])
            if node['op']!='=':
                if node['op'][:-1] not in BINARY:raise ValueError('SCRIPT_ASSIGNMENT_OP_UNSUPPORTED')
                self.emit('LOAD',index)
            self.expression(child(node,'rvalue'))
            if node['op']!='=':self.emit(BINARY[node['op'][:-1]])
            self.emit('STORE',index) # STORE retains expression value.
        else:raise ValueError('SCRIPT_EXPRESSION_UNSUPPORTED: '+kind)

    def statement(self,node):
        if node is None:return
        kind=node['kind']
        if kind=='Compound':
            self.scopes.append({})
            for c in node['children']:self.statement(c['node'])
            self.scopes.pop()
        elif kind=='Decl':
            index=self.declare(node['name']);initializer=child(node,'init')
            if initializer:self.expression(initializer)
            else:self.emit('EMPTY')
            self.emit('STORE',index);self.emit('DROP')
        elif kind=='If':
            self.expression(child(node,'cond'));branch=self.emit('BR_FALSE')
            self.statement(child(node,'iftrue'));otherwise=child(node,'iffalse')
            if otherwise:
                jump=self.emit('JUMP');self.patch(branch,len(self.code));self.statement(otherwise);self.patch(jump,len(self.code))
            else:self.patch(branch,len(self.code))
        elif kind=='Return':
            expression=child(node,'expr')
            if expression:self.expression(expression)
            else:self.emit('EMPTY')
            self.emit('RETURN')
        elif kind=='EmptyStatement':pass
        elif kind in ('FuncCall','Assignment'):
            self.expression(node);self.emit('DROP')
        else:raise ValueError('SCRIPT_STATEMENT_UNSUPPORTED: '+kind)

    def compile(self):
        self.statement(child(self.function['ast'],'body'));self.emit('EMPTY');self.emit('RETURN')
        return dict(code_hex=self.code.hex(),bytes=len(self.code),locals=self.locals,
                    arity=self.function['arity'],native_executed=False)


def compile_library(library,builtins):
    if len(builtins)>=32768:raise ValueError('SCRIPT_BUILTIN_ID_CAPACITY')
    functions={name:dict(id=i,arity=f['arity']) for i,(name,f) in enumerate(library['functions'].items())}
    if len(functions)>=32768:raise ValueError('SCRIPT_FUNCTION_ID_CAPACITY')
    constants=[];compiled={name:FunctionCompiler(f,functions,builtins,constants).compile()
                            for name,f in library['functions'].items()}
    return dict(source_path=library['source_path'],asset_sha256=library.get('asset_sha256'),
        functions=compiled,function_ids=functions,constants=constants,builtin_requirements=builtins,
        native_bound=False,bytecode_bytes=sum(f['bytes'] for f in compiled.values()))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();source=json.loads(a.input.read_text())
    libraries={name:compile_library(library,source['engine_api_requirements']) for name,library in source['libraries'].items()}
    r=dict(schema='BYOR_VARIANT_BYTECODE_V1',libraries=libraries,opcodes=OPS,
        source_ast_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),engine_authority=source['engine_authority'],
        logical_evaluation='EAGER_BOTH_OPERANDS',declared_types_ignored=True,
        native_vm_bound=False,frame_dispatch_bound=False,inline_wrappers_bound=False)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(libraries=len(libraries),
        functions=sum(len(l['functions']) for l in libraries.values()),
        bytecode_bytes=sum(l['bytecode_bytes'] for l in libraries.values()),native_bound=False)))


if __name__=='__main__':main()
