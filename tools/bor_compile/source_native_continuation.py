"""Precompute native constructor resume records from real lowered callsites.

B4NC retains VM execution state and the conservative mutable slots of the
active source functions. It uses one existing frame-stack row for the VM
snapshot plus one for the parent frame owner; it allocates no new actor RAM.
This is an offline ABI and capacity proof, not a live native API binding.
"""
import argparse, hashlib, json, struct, zlib
from pathlib import Path
from compiler import Source
from script_frame_dispatch import compile_frames
from script_native_module import lower, POLICY
from script_native_link import link, unpack as unpack_module

HEADER, DIRECTORY_STRIDE, SNAPSHOT_BYTES = 32, 4, 512
# The trace head and log observation are global history, not caller context.
SEGMENTS=[(0x7fe090,12),(0x7fe09d,15),(0x7ff600,72),(0x7ff660,30),
          (0x7ff780,26),(0x7ff7a0,64),(0x7ffb30,8),(0x7ff400,10)]
CONTEXT_BYTES=sum(n for _,n in SEGMENTS)
TARGETS={'projectile','spawn'}

def derive(source):
    frames=compile_frames(source);inputs=[];details=[]
    for item in frames['programs']:
        blob,detail=lower(item['program'],entry='__byor_empty',export_roots=item['roots'],
                          numeric_policy=POLICY,rom_link_input=True)
        inputs.append((dict(model=item['model'],source_path=item['source_path']),blob));details.append(detail)
    instructions,metadata,linked=link(inputs);records=[]
    for program,(item,detail,location,(_,blob))in enumerate(zip(frames['programs'],details,linked['programs'],inputs)):
        module,_=unpack_module(blob)
        for chain in detail['native_call_chains']:
            if chain['name']not in TARGETS:continue
            ip=chain['native_ip'];ins=module.instructions[ip];call=module.callsites[ins.c]
            if ins.op!=8 or call.target_kind!=2 or ins.c!=chain['native_callsite'] or call.argc!=chain['arity']:
                raise ValueError('NATIVE_CONTINUATION_CALLSITE_WITNESS')
            slots=[s+location['slot_base']for s in chain['conservative_mutable_slots']]
            sites=[s+location['callsite_base']for s in chain['frame_callsites']]
            if len(sites)!=chain['script_frames']or any(module.callsites[s].target_kind!=0 for s in chain['frame_callsites']):
                raise ValueError('NATIVE_CONTINUATION_SCRIPT_FRAME_WITNESS')
            size=CONTEXT_BYTES+12*len(sites)+8*len(slots)
            if size>SNAPSHOT_BYTES:raise ValueError('NATIVE_CONTINUATION_SNAPSHOT_CAPACITY')
            result=ins.b+location['slot_base']
            if result not in slots:raise ValueError('NATIVE_CONTINUATION_RESULT_OWNERSHIP')
            records.append(dict(program=program,model=item['model'],native_name=chain['name'],arity=chain['arity'],
                functions=chain['functions'],resume_ip=ip+location['entry_ip']+1,
                native_id=call.target_id,callsite=ins.c+location['callsite_base'],result_slot=result,
                frame_callsites=sites,slots=slots,snapshot_bytes=size))
    # The same native instruction may be called from multiple frame roots;
    # actual saved script callsite IDs disambiguate the caller chain.
    keys=[(r['program'],r['resume_ip'],tuple(r['frame_callsites']))for r in records]
    if len(set(keys))!=len(keys):raise ValueError('NATIVE_CONTINUATION_DUPLICATE_KEY')
    report=dict(schema='BYOR_4086_NATIVE_CONTINUATION_ABI_V1',records=records,
        segments=[dict(address=a,bytes=n)for a,n in SEGMENTS],context_bytes=CONTEXT_BYTES,
        instruction_sha256=hashlib.sha256(instructions).hexdigest(),metadata_sha256=hashlib.sha256(metadata).hexdigest(),
        instruction_crc32=zlib.crc32(instructions)&0xffffffff,metadata_crc32=zlib.crc32(metadata)&0xffffffff,
        program_count=len(inputs),peak_snapshot_bytes=max((r['snapshot_bytes']for r in records),default=CONTEXT_BYTES),
        snapshot_capacity=SNAPSHOT_BYTES,frame_stack_rows_per_native=2,
        maximum_native_nesting_without_other_frame_rows=4,
        slot_policy='conservative locals and operand stacks of the actual active source function chain',
        dynamic_string_retention_bound=False,native_snapshot_execution_bound=False,
        native_api_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    return report,instructions,metadata

def pack(report):
    records=report['records']
    if not 1<=len(records)<=1024:raise ValueError('NATIVE_CONTINUATION_RECORD_COUNT')
    body=bytearray(DIRECTORY_STRIDE*len(records))
    for i,r in enumerate(records):
        frames,slots=r['frame_callsites'],r['slots'];size=CONTEXT_BYTES+12*len(frames)+8*len(slots)
        if size>SNAPSHOT_BYTES or size!=r['snapshot_bytes']or slots!=sorted(set(slots))or not 0<=r['program']<report['program_count']or r['result_slot']not in slots:
            raise ValueError('NATIVE_CONTINUATION_RECORD')
        row=struct.pack('<8H',r['program'],r['resume_ip'],r['native_id'],r['callsite'],r['result_slot'],len(frames),len(slots),size)
        row+=struct.pack('<'+'H'*(len(frames)+len(slots)),*(frames+slots))
        struct.pack_into('<HH',body,i*4,HEADER+len(body),len(row));body.extend(row)
    if HEADER+len(body)>32768:raise ValueError('NATIVE_CONTINUATION_ROM_BANK_CAPACITY')
    return struct.pack('<4s4H5I',b'B4NC',1,len(records),DIRECTORY_STRIDE,0,len(body),
        zlib.crc32(body)&0xffffffff,report['instruction_crc32'],report['metadata_crc32'],0)+body

def unpack(raw):
    if len(raw)<HEADER:raise ValueError('NATIVE_CONTINUATION_HEADER')
    magic,version,count,stride,flags,size,crc,icrc,mcrc,reserved=struct.unpack_from('<4s4H5I',raw)
    if (magic,version,stride,flags,reserved)!=(b'B4NC',1,4,0,0)or not 1<=count<=1024 or size!=len(raw)-HEADER or size<4*count or crc!=zlib.crc32(raw[HEADER:])&0xffffffff:
        raise ValueError('NATIVE_CONTINUATION_ABI')
    records=[];end=HEADER+4*count
    for i in range(count):
        offset,length=struct.unpack_from('<HH',raw,HEADER+i*4)
        if offset!=end or length<16 or offset+length>len(raw):raise ValueError('NATIVE_CONTINUATION_DIRECTORY')
        program,resume,target,call,result,frames,slots,payload=struct.unpack_from('<8H',raw,offset)
        if length!=16+2*(frames+slots)or payload!=CONTEXT_BYTES+12*frames+8*slots or payload>SNAPSHOT_BYTES:
            raise ValueError('NATIVE_CONTINUATION_ROW')
        values=list(struct.unpack_from('<'+'H'*(frames+slots),raw,offset+16));slot_ids=values[frames:]
        if slot_ids!=sorted(set(slot_ids))or result not in slot_ids:raise ValueError('NATIVE_CONTINUATION_SLOTS')
        records.append(dict(program=program,resume_ip=resume,native_id=target,callsite=call,result_slot=result,frame_callsites=values[:frames],slots=slot_ids,snapshot_bytes=payload));end+=length
    if end!=len(raw):raise ValueError('NATIVE_CONTINUATION_TRAILING')
    keys=[(r['program'],r['resume_ip'],tuple(r['frame_callsites']))for r in records]
    if len(set(keys))!=len(keys):raise ValueError('NATIVE_CONTINUATION_DUPLICATE_KEY')
    return records,icrc,mcrc

def validate_pair(raw,instructions,metadata):
    rows,icrc,mcrc=unpack(raw)
    if icrc!=zlib.crc32(instructions)&0xffffffff or mcrc!=zlib.crc32(metadata)&0xffffffff:
        raise ValueError('NATIVE_CONTINUATION_MODULE_PAIR')
    # B48R compact metadata retains the header fields used by the native VM.
    if len(metadata)<64 or metadata[:8]!=b'B48R\x01\x30\x00\x00' or len(instructions)%8:
        raise ValueError('NATIVE_CONTINUATION_MODULE_ABI')
    if struct.unpack_from('<I',metadata,52)[0]!=len(metadata) or struct.unpack_from('<I',metadata,56)[0]!=zlib.crc32(metadata[64:])&0xffffffff or struct.unpack_from('<I',metadata,24)[0]:
        raise ValueError('NATIVE_CONTINUATION_METADATA_ABI')
    instruction_count,slot_count,call_count=struct.unpack_from('<3H',metadata,8)
    if instruction_count*8!=len(instructions):raise ValueError('NATIVE_CONTINUATION_INSTRUCTION_COUNT')
    call_base=struct.unpack_from('<I',metadata,32)[0]
    if call_base<64 or call_base+12*call_count>len(metadata):raise ValueError('NATIVE_CONTINUATION_CALL_TABLE')
    for row in rows:
        ip=row['resume_ip']-1
        if not 0<=ip<instruction_count or row['callsite']>=call_count or any(s>=slot_count for s in row['slots']):
            raise ValueError('NATIVE_CONTINUATION_INDEX')
        opcode,flags,arg,result,site=struct.unpack_from('<BB3H',instructions,ip*8)
        if site>=call_count:raise ValueError('NATIVE_CONTINUATION_CALL_INDEX')
        kind,argc,target=struct.unpack_from('<BBH',metadata,call_base+site*12)
        if opcode!=8 or site!=row['callsite']or result!=row['result_slot']or kind!=2 or target!=row['native_id']:
            raise ValueError('NATIVE_CONTINUATION_NATIVE_WITNESS')
        for frame in row['frame_callsites']:
            if frame>=call_count or metadata[call_base+frame*12]!=0:raise ValueError('NATIVE_CONTINUATION_FRAME_WITNESS')
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report,instructions,metadata=derive(Source(a.source));raw=pack(report);decoded=validate_pair(raw,instructions,metadata)
    assert decoded==[{k:r[k]for k in decoded[0]}for r in report['records']]
    report.update(table_bytes=len(raw),table_sha256=hashlib.sha256(raw).hexdigest())
    a.output.mkdir(parents=True,exist_ok=True)
    for name,data in [('continuations.b4nc',raw),('instructions.bin',instructions),('metadata.b48r',metadata)]:
        (a.output/name).write_bytes(data)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(len(decoded),'resume records;',len(raw),'table bytes;',report['peak_snapshot_bytes'],'peak VM snapshot bytes')

if __name__=='__main__':main()
