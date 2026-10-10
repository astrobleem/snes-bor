"""Prepared DMA intervals over physical CGRAM, including intra-bank splits.

This is an optimistic first-to-last commit span. Runtime setup and contention
still need native admission. Addresses are relative to the 128-word OBJ half.
"""


def constrain_pairs(model,write_flags,slots,height,window):
    """Restricted four adjacent-bank pairs, with arbitrary endpoint slots."""
    ranges={};peak=model.new_int_var(0,4096,'pairedPhysicalPeak')
    for y in range(1,height):
        costs=[]
        for pair in range(4):
            events=[(i,b,flag)for (line,b),values in write_flags.items()if line==y and b//2==pair for i,flag in values]
            if not events:continue
            active=model.new_bool_var(f'pairActive{y}_{pair}');model.add_max_equality(active,[flag for i,b,flag in events])
            minima=[];maxima=[]
            for i,b,flag in events:
                address=16*b+slots[i]+1
                lo=model.new_int_var(0,128,f'pairLow{y}_{i}');hi=model.new_int_var(-1,127,f'pairHigh{y}_{i}')
                model.add(lo==address).only_enforce_if(flag);model.add(lo==128).only_enforce_if(flag.Not())
                model.add(hi==address).only_enforce_if(flag);model.add(hi==-1).only_enforce_if(flag.Not())
                minima.append(lo);maxima.append(hi)
            minimum=model.new_int_var(0,128,f'pairMinimum{y}_{pair}');model.add_min_equality(minimum,minima)
            end=model.new_int_var(-1,127,f'pairEnd{y}_{pair}');model.add_max_equality(end,maxima)
            begin=model.new_int_var(0,127,f'pairBegin{y}_{pair}')
            model.add(begin==minimum).only_enforce_if(active);model.add(begin==0).only_enforce_if(active.Not())
            length=model.new_int_var(0,32,f'pairLength{y}_{pair}');model.add(length==end-begin+1)
            ranges[y,pair]=(active,begin,end,length);costs.append(24*active+16*length)
        if costs:model.add(sum(costs)<=window+39);model.add(peak>=sum(costs))
    return ranges,peak


def constrain(model, write_flags, slots, height, maximum_ranges, window, bank_destinations=None, packet_hints=None, event_hints=None):
    from raster_dma_partition import minimum_commit_span
    color_limit = max((c for c in range(121) if minimum_commit_span(c) < window), default=0)
    ranges = {}
    peak = model.new_int_var(0, 4096, 'physicalPeak')
    for y in range(1, height):
        events = [(i, b, flag) for (line, b), values in write_flags.items()
                  if line == y for i, flag in values]
        if not events:
            continue
        row = []
        hints = (packet_hints or {}).get(y, [])
        for r in range(maximum_ranges):
            active = model.new_bool_var(f'physicalActive{y}_{r}')
            begin = model.new_int_var(0, 127, f'physicalBegin{y}_{r}')
            length = model.new_int_var(0, 128, f'physicalLength{y}_{r}')
            end = model.new_int_var(-1, 127, f'physicalEnd{y}_{r}')
            model.add(end == begin + length - 1)
            model.add(length >= active)
            model.add(length <= 128 * active)
            model.add(begin == 0).only_enforce_if(active.Not())
            if row:
                model.add(active <= row[-1][0])
                model.add(begin > row[-1][2]).only_enforce_if(active)
            row.append((active, begin, end, length))
            ranges[y, r] = row[-1]
            if packet_hints is not None:
                hint=hints[r]if r<len(hints)else None
                model.add_hint(active,int(hint is not None))
                model.add_hint(begin,hint[0]if hint else 0)
                model.add_hint(length,hint[1]-hint[0]+1 if hint else 0)
                model.add_hint(end,hint[1]if hint else -1)
        for i, bank, flag in events:
            address = 16 * (bank_destinations or {}).get(bank, bank) + slots[i] + 1
            choices = []
            for r, (active, begin, end, length) in enumerate(row):
                member = model.new_bool_var(f'physicalMember{y}_{i}_{bank}_{r}')
                model.add(member <= active)
                model.add(begin <= address).only_enforce_if(member)
                model.add(end >= address).only_enforce_if(member)
                choices.append(member)
                if packet_hints is not None and i in (event_hints or {}):
                    address_hint,time_hint=event_hints[i]
                    model.add_hint(member,int(time_hint==y and r<len(hints)and hints[r][0]<=address_hint<=hints[r][1]))
            model.add(sum(choices) == flag)
        cost = sum(24 * active + 16 * length for active, begin, end, length in row)
        writes = sum(flag for i, b, flag in events)
        # Redundant physical bounds strengthen propagation: simultaneous
        # writes occupy distinct opaque slots, at most fifteen per bank.
        model.add(writes <= color_limit)
        model.add(sum(length for active, begin, end, length in row) >= writes)
        model.add(cost <= window + 39)
        model.add(peak >= cost)
    return ranges, peak
