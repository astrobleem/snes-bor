"""Exclusive nested-call accounting for bounded S7 replay; no runtime writes.

Interrupt intervals are removed from the deepest interrupted callback, not
counted again in its parents. NMI epilogue/outer vector remain in caller cost.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import median

PASS = dict(enumerate(('lost/lifecycle', 'gravity', 'simulation/AI',
                      'animation', 'hit/collision', 'displayed-health')))
HOOK = dict(zip(('S6_WorldLost','S6_WorldGravity','S6_ThinkPass',
                 'S6_AnimationPass','S6_WorldAttack','S6_WorldHealth'), PASS.values()))


def category(row):
    name = row[2]
    if name == 'S6_UpdateWorldDispatch':
        return PASS[int(row[8])]
    return HOOK.get(name, name)


def intervals(rows, begin, end):
    pending = None
    result = []
    for row in rows:
        if row[1] == begin:
            if pending is not None:
                raise ValueError('NESTED_INTERVAL')
            pending = int(row[4])
        elif row[1] == end and pending is not None:
            result.append((pending, int(row[4])))
            pending = None
    return result


def profile_intervals(report):
    """Match profile callbacks, clipping only routines interrupted at the run boundary."""
    opened, spans = {}, []
    for row in report['profile_rows']:
        if row[1] == 'enter':
            opened[row[3]] = row
        else:
            first = opened.pop(row[3])
            spans.append((int(first[4]), int(row[4]), category(first), row[3]))
    nmi_done = [int(row[4]) for row in report.get('rows', [])
                if row[1] == 'Core_Nmi_Play__done']
    end = max(nmi_done) if nmi_done else max(
        (int(row[4]) for row in report['profile_rows']), default=0)
    clipped = []
    for ident, first in opened.items():
        start = int(first[4])
        if start > end:
            clipped.append((first[2], ident, 0))
            continue
        spans.append((start, end, category(first), ident))
        clipped.append((first[2], ident, end-start))
    return spans, clipped


def detailed(report):
    """Partition the exact replay window, excluding world/release before service.

    Innermost observed call owns each clock; IRQ body overrides interrupted code.
    Unobserved outer vector/loop instructions remain explicitly unclassified.
    """
    spans, _ = profile_intervals(report)
    ticks=[(int(a[3]),int(b[3])) for a,b in zip(report['cpu_rows'][::2],report['cpu_rows'][1::2])]
    releases=[(a,b) for a,b,n,_ in spans if n=='S7Resident_Flush']
    lo=ticks[0][0];hi=max([ticks[-1][1]]+[b for a,b in releases])
    irq=intervals(report['rows'],'Core_Nmi_Play__do_commit','Core_Nmi_Play__done')
    entries=[]
    for a,b,n,i in spans: entries.append((a,b,n,i,1))
    for i,(a,b) in enumerate(irq):entries.append((a,b,'NMI/DMA body',f'irq{i}',2))
    for i,(a,b) in enumerate(ticks+releases):entries.append((a,b,'WORLD/RELEASE',f'world{i}',3))
    points={lo:[],hi:[]}
    for ident,(a,b,n,call,priority) in enumerate(entries):
        if b<=lo or a>=hi:continue
        points.setdefault(max(a,lo),[]).append((True,ident))
        points.setdefault(min(b,hi),[]).append((False,ident))
    active=set();totals=Counter();invocations={};last=lo
    for at,changes in sorted(points.items()):
        if at>last:
            chosen=max(active,key=lambda j:(entries[j][4],-(entries[j][1]-entries[j][0])),default=None)
            name=entries[chosen][2] if chosen is not None else 'UNCLASSIFIED outer-loop/vector'
            totals[name]+=at-last
            if chosen is not None:invocations.setdefault(name,set()).add(entries[chosen][3])
        for add,ident in changes:
            if add:active.add(ident)
            else:active.discard(ident)
        last=at
    traversal=Counter();calls=Counter()
    blocked=[(a,b) for a,b,n,_ in spans if n in HOOK.values()]+irq
    irq_nested=[(max(x,u),min(y,v)) for x,y in irq
                for u,v,n,_ in spans if n in HOOK.values() and max(x,u)<min(y,v)]
    # Only direct callbacks + IRQ need exclusion, not their nested callees.
    blocks=report.get('block_rows',[])
    for first,second in zip(blocks,blocks[1:]):
        name=first[1]
        if name=='S6_UpdateWorld__done':continue
        a,b=int(first[2]),int(second[2])
        own=b-a-sum(max(0,min(b,y)-max(a,x)) for x,y in blocked)
        # IRQ inside a callback was already excluded with that callback.
        own+=sum(max(0,min(b,y)-max(a,x)) for x,y in irq_nested)
        traversal[name]+=own;calls[name]+=1
    groups=Counter();group_calls=Counter()
    for name,c in traversal.items():
        group=('preflight' if name in ('S6_UpdateWorld','S6_UpdateWorld__preflight','S6_UpdateWorld__next_check')
               else 'slot_limit' if name.endswith('__slot')
               else 'lookup_existence_error' if name.endswith('__visit')
               else 'context_callback_time' if name.endswith(('__call','__time_ready'))
               else 'slot_advance' if name.endswith('__next') else 'pass_setup_bound_entry')
        groups[group]+=c;group_calls[group]+=calls[name]
    return dict(window_clocks=hi-lo,traversal_groups={n:dict(clocks=c,label_visits=group_calls[n])
        for n,c in groups.items()},outside={n:dict(clocks=c,
        invocations=len(invocations.get(n,())),
        clocks_per_invocation=c/len(invocations[n]) if invocations.get(n) else None)
        for n,c in totals.most_common()},traversal={n:dict(clocks=c,calls=calls[n])
        for n,c in traversal.most_common()})


def analyze(report):
    spans, clipped = profile_intervals(report)
    calls = Counter()
    events = []
    for start, end, name, ident in spans:
        calls[name] += 1
        events.append((start, end, name))
    # Use the same NMI-body boundaries for both pre/post reports.
    nmis = intervals(report['rows'], 'Core_Nmi_Play__do_commit', 'Core_Nmi_Play__done')
    cost, stack, roots = Counter(), [], []
    for start, end, name in sorted(events, key=lambda x:(x[0], -x[1])):
        while stack and start >= stack[-1][1]:
            stack.pop()
        if stack and end > stack[-1][1]:
            raise ValueError('CROSSING_CALL_INTERVAL')
        own = end-start
        irq = sum(max(0, min(end,b)-max(start,a)) for a,b in nmis)
        cost[name] += own-irq
        if stack:
            cost[stack[-1][2]] -= own-irq
        else:
            cost['NMI/DMA measured body'] += irq
            roots.append((start,end,name))
        stack.append((start,end,name))
    ticks, pending = [], None
    for row in report['cpu_rows']:
        if row[1] == 'S6Host_Tick':
            pending = row
        else:
            ticks.append((int(pending[4]),int(pending[3]),int(row[3])))
    costs = [b-a for _,a,b in ticks]
    # Physical contiguous execution: gaps include clock advance/host fixture,
    # NMI is included in each tick. Explicit gap threshold, not a source law.
    bursts, burst = [], []
    for tick in ticks:
        if burst and tick[1]-burst[-1][2] > 4096:
            bursts.append(burst)
            burst=[]
        burst.append(tick)
    if burst: bursts.append(burst)
    # Service profiling may wrap releases in Game_State_Play/ClockAdvance.
    # A release is outside measured ticks, not necessarily a profile root.
    flushes=[(a,b,n) for a,b,n in events if n in ('S7Resident_Flush','Relay_Flush')]
    assert all(not (a<y and b>x) for a,b,_ in flushes for _,x,y in ticks), 'RELEASE_OVERLAPS_TICK'
    flush_cost=sum(b-a for a,b,_ in flushes)
    final_ready=max([ticks[-1][2]]+[b for _,b,_ in flushes])
    return dict(exclusive_master_clocks=dict(cost.most_common()),calls=dict(calls),
        profile_intervals_clipped_at_nmi_end=clipped,
        batch_release=dict(count=len(flushes),inclusive_clocks=flush_cost),
        world_plus_release=sum(costs)+flush_cost,
        elapsed_through_final_release=final_ready-ticks[0][1],
        inclusive_ticks=dict(count=len(costs),min=min(costs),median=median(costs),
            p95=sorted(costs)[int((len(costs)-1)*.95)],max=max(costs),
            total=sum(costs),mean=sum(costs)/len(costs)),
        max_contiguous_burst=max((dict(ticks=len(b),first_tick=b[0][0],
            last_tick=b[-1][0],elapsed=b[-1][2]-b[0][1],
            execution=sum(y-x for _,x,y in b)) for b in bursts), key=lambda b:b['elapsed']),
        nmi_body=dict(count=len(nmis),max=max(b-a for a,b in nmis)),
        accounting='NMI commit body excluded from callbacks; outer vector/epilogue residual '
                   'remains charged to interrupted callback. No host observer emulated instructions.',
        phase=report['world_deadline_analysis'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before',type=Path)
    parser.add_argument('after',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--detail',action='store_true')
    parser.add_argument('--require-same-epoch',action='store_true')
    args=parser.parse_args()
    before=json.loads(args.before.read_text())
    after=json.loads(args.after.read_text())
    result=dict(before=analyze(before),after=analyze(after),
        semantic_trace_equal=before['semantic_rows']==after['semantic_rows'],
        pass_callback_order_equal=[(r[7], category(r)) for r in before['profile_rows']
            if r[1]=='enter' and (r[2]=='S6_UpdateWorldDispatch' or r[2] in HOOK)]==
            [(r[7],category(r)) for r in after['profile_rows']
            if r[1]=='enter' and (r[2]=='S6_UpdateWorldDispatch' or r[2] in HOOK)],
        callback_events_equal=before.get('event_rows')==after.get('event_rows'),
        first_tick_epoch_equal=before['cpu_rows'][0][3]==after['cpu_rows'][0][3],
        before_path=str(args.before),after_path=str(args.after))
    if args.detail:
        result['before_detail']=detailed(before)
        result['after_detail']=detailed(after)
        boundaries=[r for r in after.get('block_rows',[]) if r[1] in
                    ('S6_UpdateWorld','S6_UpdateWorldBound','S6_UpdateWorld__done')]
        if boundaries:
            result['world_boundary_abi']=dict(samples=len(boundaries),
                d_sp_dbr=sorted(set(tuple(r[3:6]) for r in boundaries)),
                widths_decimal_clear=all(int(r[6])&0x38==0 for r in boundaries))
            assert result['world_boundary_abi']['widths_decimal_clear']
            assert len(result['world_boundary_abi']['d_sp_dbr'])==1
    assert result['semantic_trace_equal'] and result['pass_callback_order_equal']
    assert result['callback_events_equal']
    if args.require_same_epoch:assert result['first_tick_epoch_equal']
    text=json.dumps(result,indent=2)+'\n'
    if args.output: args.output.write_text(text)
    print(text)


if __name__=='__main__':
    main()
