"""Native READY scan, all-case timings and original reference baseline."""
from __future__ import annotations
import borrow_invalidate_evidence as baseline
import ready_validate_evidence as ready


def require(ok,code):
    if not ok:raise ValueError('READY_UNROLL:'+code)


def native_scans(path):
    scans=ready.native_scans(path);entries={};traces={};finishes={}
    for event in ready.events(path):
        data=event['data']
        if event['kind']=='RV_ENTRY':
            regs=dict(zip(ready.REGISTERS,map(int,data[1:9])))
            require(regs['d']==0x3400 and 0x1000<=regs['sp']<0x2000,'STACK_AND_DP_DISJOINT')
            entries[data[0]]=(event['clock'],ready._map(data[9]))
        elif event['kind']=='RV_SCAN':finishes[data[0]]=event['clock']
        elif event['kind']=='RU_TRACE':
            require(len(data)==2 and data[0] not in traces,'WRITE_TRACE_INVENTORY')
            traces[data[0]]=(event['clock'],data[1])
    require(set(entries)==set(traces)==set(scans),'WRITE_TRACE_COMPLETE_INVENTORY')
    for txn,(entry_clock,words) in entries.items():
        trace_clock,trace=traces[txn]
        require(entry_clock<trace_clock==finishes[txn],'WRITE_TRACE_BOUNDARY:'+txn)
        expected=[]
        for index,word in enumerate(words):
            value=word&0x3fff;address=0xc000+2*index
            expected.extend((f'{address:04x}{value&255:02x}',f'{address+1:04x}{value>>8:02x}'))
        require(trace==''.join(expected),'ORDERED_PENDING_MAP_WRITES:'+txn)
        scans[txn]['ordered_pending_map_byte_writes']=2048
    return scans


def verify_timing(report,accepted_reference):
    # Reuse the already-published fail-closed inventory and strict transaction
    # comparisons. This includes committed and aborted transactions in all cases.
    return baseline.compare_case_timings(report,accepted_reference)


def compare_ready(current,control):
    comparison=ready.compare_intervals(current,control)
    require('3' in comparison,'READY_EPOCH3_MISSING')
    target=comparison['3']
    require(target['after_clocks']*4<=target['before_clocks']*3,'READY_GAIN_BELOW_25_PERCENT')
    return comparison
