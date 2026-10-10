"""Necessary prepared-DMA range bound with physical 16-word OBJ banks.

Endpoint writes can be packed freely; intermediate banks cost all 16 words.
Slot ordering, setup, contention and channel availability remain unproven.
"""
import math


def minimum_commit_span(colors):
    """Best possible prepared-range span, allowing arbitrary bank/slot packing.

    Each bank has 15 opaque slots. P banks in R disjoint ranges cross at least
    P-R transparent words; each range costs 24 setup clocks. Grant the same
    32-clock data-span subtraction and eight-clock first-low preload as the
    physical partition model. This only bounds that prepared-DMA family.
    """
    if not isinstance(colors,int)or not 0<=colors<=120:
        raise ValueError('DMA_PARTITION_COLOR_COUNT')
    return 0 if not colors else 16*(colors+(colors+14)//15-2)


def constrain_ranges(bank_writes, active, allocate, constraint, window):
    ranges={};word_counts={};domains={}
    for first in range(8):
        for last in range(first,8):
            q=allocate();t=allocate();domains[t]=30
            ranges[first,last]=q;word_counts[first,last]=t
            constraint([(q,1),(active[first],-1)],-math.inf,0)
            if last!=first:constraint([(q,1),(active[last],-1)],-math.inf,0)
            endpoints=bank_writes[first]+(bank_writes[last]if last!=first else [])
            constraint([(t,1),(q,-30)],-math.inf,0)
            constraint([(t,-1),(q,30)]+[(v,1)for v in endpoints],-math.inf,30)
            constraint([(t,1)]+[(v,-1)for v in endpoints],-math.inf,0)
    for bank in range(8):
        covering=[(q,1)for (first,last),q in ranges.items()if first<=bank<=last]
        constraint(covering,-math.inf,1)
        constraint(covering+[(active[bank],-1)],0,math.inf)
    cost=[(v,16)for v in word_counts.values()]
    cost += [(q,24+(16*(16*(last-first-1)+1)if last!=first else 0))for (first,last),q in ranges.items()]
    # First-to-last data span subtracts 32; preloading the first low byte
    # grants another 8. Strictly fit the window's last accessible clock.
    constraint(cost,-math.inf,window+39)
    return domains
