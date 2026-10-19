"""Read-only wait-body accounting. Elapsed transaction gates remain unchanged."""
import hashlib,json
from pathlib import Path
import borrow_invalidate_evidence as evidence

REGISTERS=evidence.REGISTERS
def require(ok,code):
    if not ok:raise ValueError('TIMING_ALIGNMENT:'+code)
def parse_waits(path,callers):
    starts={};result=[]
    for event in evidence.ready.events(path):
        data=event['data']
        if event['kind']=='TA_WAIT_BEGIN':
            require(len(data)==11,'ENTRY_RECORD')
            seq,txn,caller=int(data[0]),data[1],int(data[2])
            require(seq==len(starts)+1 and seq==len(result)+1,'ENTRY_ORDER')
            require(caller in callers,'UNEXPECTED_CALLER')
            before=dict(zip(REGISTERS,map(int,data[3:11])))
            require(before['ps']&0x30==0,'ENTRY_WIDTH')
            starts[seq]=(event,txn,caller,before)
        elif event['kind']=='TA_WAIT_END':
            require(len(data)==12,'EXIT_RECORD')
            seq,txn,elapsed,caller=int(data[0]),data[1],int(data[2]),int(data[3])
            require(seq==len(result)+1 and seq in starts,'EXIT_ORDER')
            entry,was_txn,was_caller,before=starts[seq]
            require(txn==was_txn and caller==was_caller,'CALLER_OR_TRANSACTION')
            require(elapsed==event['clock']-entry['clock'] and elapsed>0,'CLOCKS')
            expected=dict(before,a=(before['a']&0xff00)|0x80,ps=(before['ps']&~0xa2)|0x80)
            require(dict(zip(REGISTERS,map(int,data[4:12])))==expected,'WAIT_BODY_ABI')
            result.append(dict(sequence=seq,transaction=txn,caller=caller,
                start=entry['clock'],finish=event['clock'],master_clocks=elapsed,
                entry_registers=before,entry_frame=entry['frame'],exit_frame=event['frame']))
    require(bool(result) and len(result)==len(starts),'INCOMPLETE_WAIT_INVENTORY')
    return result

def decompose(transaction,waits):
    selected=[row for row in waits if row['transaction']==str(transaction['transaction'])]
    require(bool(selected),'MISSING_TRANSACTION_WAITS')
    require(all(transaction['start']<=row['start']<row['finish']<=transaction['finish'] for row in selected),
            'WAIT_NOT_WITHIN_TRANSACTION')
    total=sum(row['master_clocks'] for row in selected)
    require(total<=transaction['master_clocks'],'WAIT_EXCEEDS_TRANSACTION')
    return dict(transaction=transaction['transaction'],committed=transaction['committed'],
        total_clocks=transaction['master_clocks'],fields=transaction['fields'],wait_calls=len(selected),
        wait_body_clocks=total,non_poll_residual_clocks=transaction['master_clocks']-total,
        wait_callers=[row['caller'] for row in selected])

def compare(before,after):
    require((before['transaction'],before['committed'],before['wait_calls'],before['wait_callers'])==
        (after['transaction'],after['committed'],after['wait_calls'],after['wait_callers']),'COMPARISON_INVENTORY')
    result=dict(transaction=before['transaction'],committed=before['committed'],
        before=before,after=after,field_delta=after['fields']-before['fields'])
    for key in ('total_clocks','wait_body_clocks','non_poll_residual_clocks'):
        result[key+'_delta']=after[key]-before[key]
    require(result['total_clocks_delta']==result['wait_body_clocks_delta']+result['non_poll_residual_clocks_delta'],
            'DECOMPOSITION_SUM')
    result['strict_transaction_gate_pass']=result['total_clocks_delta']<=0 and result['field_delta']<=0
    return result

def pair_leafs(current,control):
    """Diagnostic pairing only; this does not change or replace an acceptance gate."""
    require(len(current)==len(control),'LEAF_CALL_COUNT')
    totals={}
    for now,was in zip(current,control):
        require(all(now[key]==was[key] for key in ('sequence','transaction','home','count','prepared',
            'input_sha256','return_pc','caller_return_pc')),'LEAF_INPUT_DRIFT')
        row=totals.setdefault(was['transaction'],dict(calls=0,before_clocks=0,after_clocks=0))
        row['calls']+=1;row['before_clocks']+=was['master_clocks'];row['after_clocks']+=now['master_clocks']
    for row in totals.values():row['clock_delta']=row['after_clocks']-row['before_clocks']
    return totals
