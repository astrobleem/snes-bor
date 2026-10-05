"""Lower source variant bytecode into the existing slot VM, with explicit policy.

This does not bind engine APIs or claim binary64 numeric equivalence. Native
IDs distinguish name AND arity; no fixed player, actor name, or property alias
from the earlier VM fixture is used. All bytecode joins have checked stack
heights before lowering. Recursive calls are refused because VM slots are flat.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_converter'))
from openbor_script.compiler import Module,Instr,Callsite,BINOP_OPCODE
from openbor_script.module import pack_module
from script_bytecode import OPS,BINARY
from script_native_api import IDS

POLICY='ACCEPTED_COMPAT_Q16_16'


def decode(function):
    code=bytes.fromhex(function['code_hex']);rows={};pc=0
    while pc<len(code):
        start=pc;op=OPS[code[pc]];pc+=1;arg=None;argc=None
        if op in ('CONST','CALL','BR_FALSE','JUMP'):
            arg=struct.unpack_from('<H',code,pc)[0];pc+=2
        elif op in ('LOAD','STORE'):arg=code[pc];pc+=1
        if op=='CALL':argc=code[pc];pc+=1
        rows[start]=(op,arg,argc,pc)
    heights={0:0};todo=[0];peak=0
    while todo:
        address=todo.pop()
        if address not in rows:raise ValueError('NATIVE_LOWERING_INVALID_TARGET')
        op,arg,argc,nxt=rows[address];height=heights[address]
        required=(argc if op=='CALL' else 2 if op in BINARY.values() else
                  1 if op in ('DROP','STORE','BR_FALSE','RETURN','NEG','POS','NOT') else 0)
        if height<required:raise ValueError('NATIVE_LOWERING_STACK_UNDERFLOW')
        delta=(1 if op in ('CONST','EMPTY','LOAD') else 1-argc if op=='CALL' else
               -1 if op in BINARY.values() or op in ('DROP','BR_FALSE','RETURN') else 0)
        after=height+delta;peak=max(peak,height,after)
        successors=() if op=='RETURN' else (arg,) if op=='JUMP' else (arg,nxt) if op=='BR_FALSE' else (nxt,)
        for target in successors:
            if target in heights:
                if heights[target]!=after:raise ValueError('NATIVE_LOWERING_STACK_JOIN_MISMATCH')
            else:heights[target]=after;todo.append(target)
    return rows,heights,peak


def lower(library,entry='main',numeric_policy=None,native_ids=None):
    if numeric_policy!=POLICY:raise ValueError('NATIVE_NUMERIC_POLICY_REQUIRED')
    if entry not in library['functions'] or library['functions'][entry]['arity']:
        raise ValueError('NATIVE_ROOT_ENTRY_REQUIRED')
    names={v['id']:k for k,v in library['function_ids'].items()}
    decoded={name:decode(fn) for name,fn in library['functions'].items()}
    edges={name:{names[arg] for op,arg,argc,nxt in decoded[name][0].values()
                 if op=='CALL' and not arg&0x8000} for name in decoded}
    def visit(name,path):
        if name in path:raise ValueError('NATIVE_FLAT_SLOT_RECURSION_UNSUPPORTED')
        for target in edges[name]:visit(target,path|{name})
    for name in edges:visit(name,set())
    if any(entry in targets for targets in edges.values()):
        raise ValueError('NATIVE_ROOT_ENTRY_CALLED_AS_FUNCTION')
    requirements=sorted({(library['builtin_requirements'][arg&0x7fff],argc)
        for rows,_,_ in decoded.values() for op,arg,argc,nxt in rows.values()
        if op=='CALL' and arg&0x8000})
    native_ids=IDS if native_ids is None else native_ids
    if any(key not in native_ids for key in requirements):
        raise ValueError('NATIVE_SOURCE_API_SIGNATURE_UNKNOWN')
    if len(set(native_ids.values()))!=len(native_ids):raise ValueError('NATIVE_ID_COLLISION')
    m=Module();numeric=[]
    def slot(kind=0,value=0,aux=0):
        index=len(m.slots);m.slots.append((kind,0,aux,value&0xffffffff));return index
    empty=slot();constant_slots=[]
    for c in library['constants']:
        if c['type']=='INTEGER32':s=slot(1,c['value'])
        elif c['type']=='DECIMAL64':
            number=struct.unpack('<d',bytes.fromhex(c['little_endian']))[0];q=round(number*65536)
            if not -2147483648<=q<=2147483647:raise ValueError('NATIVE_Q16_CONSTANT_RANGE')
            s=slot(2,q);numeric.append(dict(source_bits=c['little_endian'],source=number,
                adapted=q/65536,error=q/65536-number))
        else:
            raw=c['value'].encode('latin1')
            if raw not in m.strings:m.strings.append(raw)
            s=slot(6,m.strings.index(raw),len(raw))
        constant_slots.append(s)
    homes={name:[slot() for _ in fn['locals']] for name,fn in library['functions'].items()}
    stacks={name:[slot() for _ in range(data[2])] for name,data in decoded.items()}
    entries={};patches=[];arg_offset=0
    inverse={value:BINOP_OPCODE[key] for key,value in BINARY.items()}
    def emit(op,a=0,b=0,c=0):
        index=len(m.instructions);m.instructions.append(Instr(op,a,b,c));return index
    for name in [entry]+[n for n in decoded if n!=entry]:
        entries[name]=len(m.instructions);fn=library['functions'][name]
        if name!=entry:
            for local in homes[name][:fn['arity']]:emit(40,local)
        rows,heights,peak=decoded[name];targets={};returns=[]
        for address,(op,arg,argc,nxt) in rows.items():
            if address not in heights:continue
            targets[address]=len(m.instructions);h=heights[address];stack=stacks[name]
            if op in ('EMPTY','CONST','LOAD'):
                emit(4,stack[h],empty if op=='EMPTY' else constant_slots[arg] if op=='CONST' else homes[name][arg])
            elif op=='STORE':emit(4,homes[name][arg],stack[h-1])
            elif op in ('DROP','POS'):pass
            elif op in inverse:emit(inverse[op],stack[h-2],stack[h-2],stack[h-1])
            elif op in ('NEG','NOT'):emit(10 if op=='NEG' else 11,stack[h-1])
            elif op in ('JUMP','BR_FALSE'):
                i=emit(36,0,empty if op=='JUMP' else stack[h-1])
                patches.append((i,name,arg,'local'))
            elif op=='RETURN':
                if name==entry:emit(43)
                else:returns.append(emit(46,0,stack[h-1]))
            elif op=='CALL':
                args=stack[h-argc:h];dest=stack[h-argc]
                if arg&0x8000:
                    target=native_ids[(library['builtin_requirements'][arg&0x7fff],argc)];kind=2
                    m.natives_used.add(target)
                else:target=0;kind=0
                cs=Callsite(kind,argc,target,dest,args,arg_offset);arg_offset+=argc
                m.callsites.append(cs);i=emit(8,0,dest,len(m.callsites)-1)
                if kind==0:patches.append((i,names[arg],len(m.callsites)-1,'function'))
        epilogue=len(m.instructions);emit(43)
        for i in returns:m.instructions[i].a=epilogue
        for i,pname,target,kind in patches:
            if pname==name and kind=='local':m.instructions[i].a=targets[target]
    for i,name,cs,kind in patches:
        if kind=='function':m.instructions[i].a=entries[name];m.callsites[cs].target_id=entries[name]
    arities={native_ids[key]:key[1] for key in requirements}
    blob=pack_module(m,native_arities=arities)
    if len(blob)>32768:raise ValueError('NATIVE_MODULE_WRAM_CAPACITY')
    report=dict(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),instructions=len(m.instructions),
        slots=len(m.slots),callsites=len(m.callsites),numeric_policy=POLICY,decimal_constants=numeric,
        function_local_slots={name:dict(zip(library['functions'][name]['locals'],slots)) for name,slots in homes.items()},
        function_stack_slots=stacks,
        engine_api_requirements=[dict(id=native_ids[k],name=k[0],arity=k[1],bound=False) for k in requirements],
        source_numeric_equivalence=False,native_executed=False,entity_api_bound=False,
        unresolved_semantics=['Q16 arithmetic differs from binary64 including decimal NEG union fallthrough',
            'engine pointer identity and comparisons require native support',
            'divide-by-zero EMPTY behavior requires native support'])
    return blob,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--numeric-policy',choices=[POLICY],required=True)
    a=p.parse_args();source=json.loads(a.input.read_text());a.output.mkdir(parents=True,exist_ok=True)
    keys=set()
    for item in source['programs']:
        lib=item['program']
        for fn in lib['functions'].values():
            for op,arg,argc,nxt in decode(fn)[0].values():
                if op=='CALL' and arg&0x8000:keys.add((lib['builtin_requirements'][arg&0x7fff],argc))
    ids=IDS;reports=[]
    for item in source['programs']:
        blob,report=lower(item['program'],item['entry_function'],a.numeric_policy,ids)
        (a.output/(item['model']+'.b48s')).write_bytes(blob);reports.append(dict(model=item['model'],**report))
    result=dict(schema='BYOR_4086_NATIVE_MODULE_LOWERING_V1',programs=reports,native_executed=False,
        entity_api_bound=False,source_numeric_equivalence=False)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(models=len(reports),bytes=sum(r['bytes'] for r in reports),native_executed=False)))


if __name__=='__main__':main()
