"""Exact fused clone/recount output, traces, access inventory and timing gates."""
from __future__ import annotations
import borrow_invalidate_evidence as baseline
import ref_rebuild_evidence as reference


def require(ok,code):
    if not ok:raise ValueError('COMMIT_REBUILD_FUSE:'+code)


def native_scans(path):
    scans=reference.native_rebuilds(path);entries={};outputs={};maps={};finishes={}
    for event in reference.ready.events(path):
        data=event['data'];kind=event['kind'];txn=data[0] if data else None
        if kind=='RF_ENTRY':
            regs=reference.ready._registers(data[1:9])
            require(regs['d']==0x3400 and 0x1000<=regs['sp']<0x2000 and regs['counter']==2048,'STACK_DP_AND_COUNTER')
            maps[txn]=(event['clock'],reference._words(data[10],1024))
        elif kind=='RF_SCAN':finishes[txn]=event['clock']
        elif kind=='CF_ENTRY':
            require(len(data)==2 and txn not in entries,'CLONE_ENTRY_INVENTORY')
            entries[txn]=(event['clock'],reference._words(data[1],1024))
        elif kind=='CF_SCAN':
            require(len(data)==5 and txn not in outputs,'CLONE_EXIT_INVENTORY')
            outputs[txn]=(event['clock'],reference._words(data[1],1024),data[2],int(data[3]),int(data[4]))
    require(set(scans)==set(entries)==set(outputs)==set(maps)==set(finishes),'CLONE_SCAN_INVENTORY')
    for txn in scans:
        entry_clock,words=maps[txn];clock,committed,trace,map_reads,ref_reads=outputs[txn]
        require(entry_clock==entries[txn][0]<clock==finishes[txn],'CLONE_BOUNDARIES')
        require(committed==words,'COMMITTED_MAP_COPY')
        expected=[]
        for index,word in enumerate(words):
            address=0xc800+2*index
            expected.extend((f'{address:04x}{word&255:02x}',f'{address+1:04x}{word>>8:02x}'))
        require(trace==''.join(expected),'ORDERED_COMMITTED_BYTE_WRITES')
        require((map_reads,ref_reads)==(2048,3586),'PHYSICAL_READ_INVENTORY')
        scans[txn].update(committed_map_exact=True,committed_byte_writes=2048,
            pending_byte_reads=map_reads,reference_byte_reads=ref_reads,
            helper_exclusive_read_write_monitors=True)
    return scans


def compare_postmap(current,control):
    comparison=reference.compare_intervals(current,control)
    require('3' in comparison,'POSTMAP_EPOCH3_MISSING')
    cost=comparison['3']
    require(cost['after_clocks']*5<=cost['before_clocks']*4,'POSTMAP_GAIN_BELOW_20_PERCENT')
    return comparison


def verify_timing(report,accepted_reference):
    return baseline.compare_case_timings(report,accepted_reference)
