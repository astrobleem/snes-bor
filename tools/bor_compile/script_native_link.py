"""Link generic slot-VM programs into ROM instructions and compact metadata.

B48R is deliberately distinct from legacy B48S: the old loader must reject
it. Runtime binding is a separate gate. No functions, commands or arguments
are removed; operands are relocated by their actual ABI role.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from script_native_module import lower,POLICY
from openbor_script.compiler import Module,Instr,Callsite
from openbor_script.module import pack_module


def unpack(blob):
    if blob[:8]!=b'B48S\x01\x30\x00\x00':raise ValueError('SCRIPT_LINK_MODULE_ABI')
    if zlib.crc32(blob[64:])&0xffffffff!=struct.unpack_from('<I',blob,56)[0]:
        raise ValueError('SCRIPT_LINK_MODULE_CRC')
    m=Module();count,slots,calls,natives,entry=struct.unpack_from('<5H',blob,8)
    offsets=struct.unpack_from('<6I',blob,24);m.entry_main=entry
    m.instructions=[Instr(op,a,b,c,flags) for op,flags,a,b,c in
        struct.iter_unpack('<BBHHH',blob[offsets[0]:offsets[0]+count*8])]
    m.slots=list(struct.iter_unpack('<BBHI',blob[offsets[1]:offsets[1]+slots*8]))
    for i in range(calls):
        kind,argc,target,result,index,flags,debug=struct.unpack_from('<BBHHHHH',blob,offsets[2]+i*12)
        args=list(struct.unpack_from('<'+'H'*argc,blob,offsets[3]+index*2))
        m.callsites.append(Callsite(kind,argc,target,result,args,index,flags,debug))
    strings=offsets[4];n=struct.unpack_from('<H',blob,strings)[0]
    indices=struct.unpack_from('<'+'H'*(n+1),blob,strings+2);base=strings+2+2*(n+1)
    m.strings=[blob[base+indices[i]:base+indices[i+1]] for i in range(n)]
    arities={}
    for i in range(natives):
        sid,minimum,maximum=struct.unpack_from('<HHH',blob,offsets[5]+i*6)
        if minimum!=maximum:raise ValueError('SCRIPT_LINK_NATIVE_ARITY_RANGE_UNSUPPORTED')
        arities[sid]=minimum;m.natives_used.add(sid)
    return m,arities


def link(programs):
    m=Module();arities={};entries=[];arg_offset=0
    binary=set(range(12,15))|set(range(16,20))|set(range(22,33))
    for identity,blob in programs:
        source,natives=unpack(blob);ib=len(m.instructions);sb=len(m.slots);cb=len(m.callsites)
        entries.append(dict(identity=identity,entry_ip=ib+source.entry_main,
            instructions=len(source.instructions),slots=len(source.slots),slot_base=sb,
            source_module_sha256=hashlib.sha256(blob).hexdigest()))
        strings={}
        for i,string in enumerate(source.strings):
            if string not in m.strings:m.strings.append(string)
            strings[i]=m.strings.index(string)
        for kind,flags,aux,value in source.slots:
            if kind==6:
                if value not in strings:raise ValueError('SCRIPT_LINK_INITIAL_STRING_HANDLE')
                value=strings[value]
            m.slots.append((kind,flags,aux,value))
        for old in source.callsites:
            target=old.target_id+ib if old.target_kind==0 else old.target_id
            m.callsites.append(Callsite(old.target_kind,old.argc,target,old.result_slot+sb,
                [x+sb for x in old.arg_slot_ids],arg_offset,old.flags,old.debug_name_id))
            arg_offset+=old.argc
        for old in source.instructions:
            op=old.op;a,b,c=old.a,old.b,old.c
            if op==4:a+=sb;b+=sb
            elif op in (10,11,40):a+=sb
            elif op in binary:a+=sb;b+=sb;c+=sb
            elif op==36:a+=ib;b+=sb
            elif op==46:a+=ib;b+=sb
            elif op==8:
                if source.callsites[c].target_kind==0:a+=ib
                b+=sb;c+=cb
            elif op!=43:raise ValueError('SCRIPT_LINK_OPCODE_ROLE_UNSUPPORTED: '+str(op))
            m.instructions.append(Instr(op,a,b,c,old.flags))
        for sid,argc in natives.items():
            if sid in arities and arities[sid]!=argc:raise ValueError('SCRIPT_LINK_NATIVE_ARITY_CONFLICT')
            arities[sid]=argc
        m.natives_used.update(source.natives_used)
    # ROM holds immutable instruction records; all remaining metadata is
    # contiguous in the checked RAM code reservation. Literal slots are
    # copied into the separately reserved slot arena by a future loader.
    full=pack_module(m,native_arities=arities,vm_code_max=65535)
    length=len(m.instructions)*8;instructions=full[64:64+length]
    metadata=bytearray(full[:64]+full[64+length:]);metadata[:4]=b'B48R'
    struct.pack_into('<I',metadata,24,0) # no RAM instruction section
    for field in range(28,48,4):
        struct.pack_into('<I',metadata,field,struct.unpack_from('<I',full,field)[0]-length)
    struct.pack_into('<I',metadata,52,len(metadata))
    struct.pack_into('<I',metadata,56,zlib.crc32(metadata[64:])&0xffffffff)
    if len(metadata)>17760:raise ValueError('SCRIPT_LINK_METADATA_WRAM_CAPACITY')
    if length>32768:raise ValueError('SCRIPT_LINK_INSTRUCTIONS_ROM_BANK_CAPACITY')
    result=dict(schema='BYOR_ROM_SCRIPT_LINK_V1',numeric_policy=POLICY,
        instruction_count=len(m.instructions),instruction_bytes=length,slot_count=len(m.slots),
        slot_bytes=len(m.slots)*8,metadata_bytes=len(metadata),callsites=len(m.callsites),
        instruction_sha256=hashlib.sha256(instructions).hexdigest(),
        metadata_sha256=hashlib.sha256(metadata).hexdigest(),programs=entries,
        no_functions_removed=True,no_commands_removed=True,native_loader_bound=False,
        native_rom_fetch_bound=False,entity_api_bound=False,motu_gameplay_proven=False)
    return instructions,bytes(metadata),result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    source=json.loads(a.input.read_text());programs=[]
    for item in source['programs']:
        blob,report=lower(item['program'],numeric_policy=POLICY)
        programs.append((dict(model=item['model'],source_path=item['source_path']),blob))
    code,metadata,report=link(programs)
    (a.output/'instructions.bin').write_bytes(code);(a.output/'metadata.b48r').write_bytes(metadata)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('instruction_count','instruction_bytes','slot_count','metadata_bytes')}))


if __name__=='__main__':main()
