"""Bounded host reference for generic variant bytecode; never a native claim."""
from dataclasses import dataclass
import struct
from script_bytecode import OPS


@dataclass(frozen=True)
class Value:
    kind:str='EMPTY'
    data:object=None


def numeric(v):return v.kind in ('INTEGER','DECIMAL')
def truth(v):return v.kind!='EMPTY' and bool(v.data)
def integer(n):
    if not -2147483648<=n<=2147483647:raise ValueError('REFERENCE_INT32_RANGE_UNPROVEN')
    return Value('INTEGER',int(n))
def text(v):
    if v.kind=='EMPTY':return '<VT_EMPTY>   Unitialized'
    if v.kind=='POINTER':
        if not isinstance(v.data,int) or not 0<=v.data<=0xffffffff:
            raise ValueError('REFERENCE_POINTER32_IDENTITY_REQUIRED')
        # Build 4086 casts ptrVal to signed LONG for textual script keys.
        return '#'+str(struct.unpack('<i',struct.pack('<I',v.data))[0])
    if v.kind=='DECIMAL':return format(v.data,'.6f')
    return str(v.data)


def unary(op,v):
    if op=='NOT':return integer(not truth(v))
    # Build 4086 Pos is an empty function, including for nonnumeric variants.
    if op=='POS' or not numeric(v):return v
    if v.kind=='INTEGER':return integer(-v.data)
    # Neg falls through from dblVal to lVal in the same union. Preserve the
    # observable little-endian, 32-bit LONG behavior instead of repairing it.
    raw=bytearray(struct.pack('<d',-v.data))
    low=struct.unpack_from('<i',raw)[0]
    if low==-2147483648:raise ValueError('REFERENCE_DECIMAL_NEG_SIGNED_OVERFLOW_UNPROVEN')
    struct.pack_into('<i',raw,0,-low)
    return Value('DECIMAL',struct.unpack('<d',raw)[0])


def binary(op,a,b):
    if op in ('AND','OR'):return integer((truth(a) and truth(b)) if op=='AND' else (truth(a) or truth(b)))
    if op in ('EQ','NE'):
        equal=(a.data==b.data) if numeric(a) and numeric(b) else a.kind==b.kind and a.data==b.data
        return integer(equal if op=='EQ' else not equal)
    if op in ('LT','LE','GT','GE'):
        if not (numeric(a) and numeric(b) or a.kind==b.kind=='STRING'):raise ValueError('REFERENCE_COMPARISON_TYPES_UNPROVEN')
        return integer({'LT':lambda:a.data<b.data,'LE':lambda:a.data<=b.data,
                        'GT':lambda:a.data>b.data,'GE':lambda:a.data>=b.data}[op]())
    if op=='ADD' and (a.kind=='STRING' or b.kind=='STRING'):
        return Value('STRING',text(a)+text(b))
    if not (numeric(a) and numeric(b)):return Value()
    x,y=a.data,b.data
    if op in ('BIT_AND','BIT_OR','XOR','SHL','SHR','MOD'):
        x,y=int(x),int(y)
        if op=='MOD':
            if not y:raise ValueError('REFERENCE_INTEGER_MOD_ZERO_UNPROVEN')
            value=x-int(x/y)*y
        elif op in ('SHL','SHR'):
            if not 0<=y<32:raise ValueError('REFERENCE_SHIFT_RANGE_UNPROVEN')
            value=x<<y if op=='SHL' else x>>y
        else:value={'BIT_AND':lambda:x&y,'BIT_OR':lambda:x|y,'XOR':lambda:x^y}[op]()
        return integer(value)
    if op=='DIV' and not y:return Value()
    value={'ADD':lambda:x+y,'SUB':lambda:x-y,'MUL':lambda:x*y,'DIV':lambda:x/y}[op]()
    return Value('DECIMAL',float(value)) if 'DECIMAL' in (a.kind,b.kind) else integer(int(value))


class Machine:
    def __init__(self,library,hooks,max_steps=10000,max_depth=32):
        self.library=library;self.hooks=hooks;self.max_steps=max_steps;self.max_depth=max_depth
        self.steps=0;self.depth=0
        self.names={f['id']:name for name,f in library['function_ids'].items()}

    def call(self,name,args=()):
        if self.depth>=self.max_depth:raise ValueError('REFERENCE_SCRIPT_CALL_DEPTH')
        function=self.library['functions'][name]
        if len(args)!=function['arity']:raise ValueError('REFERENCE_SCRIPT_CALL_ARITY')
        locals=[Value() for _ in function['locals']];locals[:len(args)]=args
        stack=[];code=bytes.fromhex(function['code_hex']);pc=0;self.depth+=1
        try:
            while pc<len(code):
                self.steps+=1
                if self.steps>self.max_steps:raise ValueError('REFERENCE_SCRIPT_STEP_BUDGET')
                op=OPS[code[pc]];pc+=1;operand=None
                if op in ('CONST','CALL','BR_FALSE','JUMP'):
                    operand=struct.unpack_from('<H',code,pc)[0];pc+=2
                elif op in ('LOAD','STORE'):operand=code[pc];pc+=1
                if op=='EMPTY':stack.append(Value())
                elif op=='CONST':
                    c=self.library['constants'][operand]
                    stack.append(Value('DECIMAL',struct.unpack('<d',bytes.fromhex(c['little_endian']))[0])
                        if c['type']=='DECIMAL64' else Value('STRING' if c['type']=='STRING' else 'INTEGER',c['value']))
                elif op=='LOAD':stack.append(locals[operand])
                elif op=='STORE':locals[operand]=stack[-1]
                elif op=='DROP':stack.pop()
                elif op=='RETURN':return stack.pop()
                elif op=='JUMP':pc=operand
                elif op=='BR_FALSE':
                    if not truth(stack.pop()):pc=operand
                elif op=='CALL':
                    count=code[pc];pc+=1;args=stack[-count:] if count else []
                    if count:del stack[-count:]
                    if operand&0x8000:
                        builtin=self.library['builtin_requirements'][operand&0x7fff]
                        if builtin not in self.hooks:raise ValueError('REFERENCE_ENGINE_API_UNBOUND: '+builtin)
                        value=self.hooks[builtin](*args)
                        if not isinstance(value,Value):raise ValueError('REFERENCE_ENGINE_VARIANT_REQUIRED: '+builtin)
                    else:value=self.call(self.names[operand],args)
                    stack.append(value)
                elif op in ('NEG','POS','NOT'):
                    stack.append(unary(op,stack.pop()))
                else:
                    b=stack.pop();a=stack.pop();stack.append(binary(op,a,b))
            raise ValueError('REFERENCE_SCRIPT_NO_RETURN')
        finally:self.depth-=1
