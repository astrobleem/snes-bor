"""Exact native staging-copy boundary and write-order checks."""
from __future__ import annotations
import hashlib

import ready_validate_evidence as ready

REGISTERS=ready.REGISTERS


def require(ok,code):
    if not ok: raise ValueError('PRELOAD_PAIR:'+code)


def _hex(value,size):
    require(isinstance(value,str) and len(value)==size*2,'HEX_LENGTH')
    data=bytes.fromhex(value); require(len(data)==size,'HEX_BYTES')
    return data


def validate(before,after,trace):
    entry,index,oldbase,oldscratch,source,stage=before
    actual,idx,base,scratch,end_source,end_stage=after
    require(entry['d']==0x3400 and entry['ps']&0x38==0,'NATIVE_ENTRY_CONTRACT')
    require(entry['sp']>=0x1000 and entry['sp']<0x3000,'NATIVE_STACK_DISJOINT')
    require(0<=index<7 and idx==index==entry['counter'],'INDEX')
    destination=0x34b0 if index==6 else 0x3500+80*index
    expected=dict(entry,a=0xffff,x=0xd6d0,y=destination+80,
        ps=(entry['ps']&~0xc3)|(0x80 if entry['dbr']&0x80 else 0)|(2 if entry['dbr']==0 else 0))
    require(actual==expected,'CONTINUATION_CPU')
    require(base==destination and scratch==(oldscratch if index==6 else 16*index),'DIRECT_PAGE')
    require(source==end_source,'SOURCE_MUTATION')
    expected_stage=bytearray(stage);start=destination-0x34b0
    expected_stage[start:start+80]=source
    require(end_stage==expected_stage,'STAGING_CONTENTS')
    writes=[]
    if index!=6:
        writes.extend(((0x474,(16*index)&255),(0x475,(16*index)>>8)))
    writes.extend(((0x472,destination&255),(0x473,destination>>8)))
    writes.extend((destination-0x3000+i,value) for i,value in enumerate(source))
    expected_trace=''.join(f'{address:04x}{value:02x}' for address,value in writes)
    # Mesen selects the callback by physical sa1InternalRam range, but passes
    # the S-CPU bus address as `a`. Pin this native schema before normalizing
    # the bank-$00 $3000 mirror to its physical I-RAM offset.
    require(len(trace)%6==0,'WRITE_TRACE_SCHEMA')
    normalized=[]
    for at in range(0,len(trace),6):
        address=int(trace[at:at+4],16);value=int(trace[at+4:at+6],16)
        require(address in (0x3472,0x3473,0x3474,0x3475) or 0x34b0<=address<=0x36df,
            'WRITE_CALLBACK_BUS_ADDRESS')
        normalized.append(f'{address&0x7ff:04x}{value:02x}')
    require(''.join(normalized)==expected_trace,'PHYSICAL_IRAM_WRITE_ORDER')
    # The copy never reads its destination. Pair only the complete read set;
    # each call independently proves all 560 staging bytes before/after.
    return dict(index=index,destination=destination,input_sha256=hashlib.sha256(
        repr(entry).encode()+source+oldbase.to_bytes(2,'little')+oldscratch.to_bytes(2,'little')).hexdigest(),
        preserved_stage_before_sha256=hashlib.sha256(stage).hexdigest(),
        writes=len(writes))


def native_calls(path,enabled=False):
    active=None;calls=[];authorized=False;store_clock=None
    for event in ready.events(path):
        kind,data=event['kind'],event['data']
        if kind=='PP_STORE_BEGIN':
            require(enabled and active is not None and not authorized and len(data)==4,'STORE_BEGIN')
            start,was_txn,before=active
            require(int(data[0])==len(calls)+1 and data[1]==was_txn and int(data[3])==before[1]
                and int(data[2])==(0x34b0 if before[1]==6 else 0x3500+80*before[1]),'STORE_AUTHORIZATION')
            require(event['clock']>start['clock'],'STORE_BEFORE_ENTRY')
            authorized=True;store_clock=event['clock'];continue
        if kind not in ('PP_ENTRY','PP_EXIT'): continue
        require(len(data)==(15 if kind=='PP_ENTRY' else 17),'RECORD')
        seq,txn=int(data[0]),data[1];shift=0 if kind=='PP_ENTRY' else 1
        regs=dict(zip(REGISTERS,map(int,data[2+shift:10+shift])))
        parts=(regs,*map(int,data[10+shift:13+shift]),_hex(data[13+shift],80),_hex(data[14+shift],560))
        if kind=='PP_ENTRY':
            require(active is None and seq==len(calls)+1,'ENTRY_ORDER')
            active=(event,txn,parts);authorized=False;store_clock=None
        else:
            require(active is not None and seq==len(calls)+1,'EXIT_ORDER')
            start,was_txn,before=active; elapsed=int(data[2])
            require(authorized==enabled,'MISSING_OR_UNEXPECTED_STORE_AUTHORIZATION')
            require(not enabled or store_clock<event['clock'],'STORE_AFTER_EXIT')
            require(txn==was_txn and elapsed==event['clock']-start['clock'] and elapsed>0,'CLOCKS')
            proof=validate(before,parts,data[16]);calls.append(dict(sequence=seq,transaction=txn,
                master_clocks=elapsed,**proof));active=None
    require(active is None and bool(calls),'INCOMPLETE_CALLS')
    return calls


def compare_calls(current,control):
    require(len(current)==len(control),'CALL_COUNT')
    totals={}
    for now,was in zip(current,control):
        require(all(now[k]==was[k] for k in ('sequence','transaction','index','destination','input_sha256','writes')),
            'INPUT_DRIFT')
        row=totals.setdefault(was['transaction'],dict(calls=0,before_clocks=0,after_clocks=0))
        row['calls']+=1;row['before_clocks']+=was['master_clocks'];row['after_clocks']+=now['master_clocks']
    for row in totals.values():
        require(row['after_clocks']<=row['before_clocks'],'FUNCTION_CLOCK_REGRESSION')
        row['improvement_percent']=100*(row['before_clocks']-row['after_clocks'])/row['before_clocks']
    return totals
