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


def constrain_fixed_addresses(model,write_flags,height,maximum_ranges,window,packet_hints=None,line_windows=None):
    """Exact contiguous coverage costs when each event has a fixed OBJ slot.

    Keys use i=15*bank+opaque_slot-1. Each covered word costs sixteen clocks;
    every run costs twenty-four. Coverage may include unchanged and transparent
    words. The returned per-address cost terms share the interval API, but are
    not transfer descriptors; callers independently partition actual changes.
    """
    ranges={};peak=model.new_int_var(0,4096,'fixedAddressPeak')
    for y in range(1,height):
        events={16*b+(i-15*b)+1:flag for(line,b),values in write_flags.items()if line==y for i,flag in values}
        if not events:continue
        hints=(packet_hints or {}).get(y,[]);covers=[];starts=[]
        for address in range(128):
            cover=model.new_bool_var(f'covered{y}_{address}');start=model.new_bool_var(f'runStart{y}_{address}')
            if address in events:model.add(cover>=events[address])
            if address==0:model.add(start==cover)
            else:
                model.add(start<=cover);model.add(start<=1-covers[-1]);model.add(start>=cover-covers[-1])
            covers.append(cover);starts.append(start)
            ranges[y,address]=(start,0,0,cover)
            if packet_hints is not None:
                covered=any(lo<=address<=hi for lo,hi in hints)
                previous_covered=address>0 and any(lo<=address-1<=hi for lo,hi in hints)
                # Packet tables may split adjacent words across DMA channels.
                # Coverage has one start for their union, not one per packet.
                model.add_hint(cover,int(covered))
                model.add_hint(start,int(covered and not previous_covered))
        model.add(sum(starts)<=maximum_ranges)
        bank_active=[]
        for b in range(8):
            flags=[flag for address,flag in events.items()if address//16==b]
            if not flags:continue
            active=model.new_bool_var(f'coveredBankActive{y}_{b}')
            model.add_max_equality(active,flags);bank_active.append(active)
        # Every range spanning distinct active banks crosses transparent slot
        # zero between them. This necessary cut also holds for wider ranges
        # and for multiple disjoint ranges within the same bank.
        model.add(sum(covers)>=sum(events.values())+sum(bank_active)-sum(starts))
        cost=16*sum(covers)+24*sum(starts)
        model.add(cost<=(line_windows or {}).get(y,window)+39);model.add(peak>=cost)
    return ranges,peak


def constrain(model, write_flags, slots, height, maximum_ranges, window, bank_destinations=None, packet_hints=None, event_hints=None,line_windows=None,fixed_address_change_hints=None):
    from raster_dma_partition import minimum_commit_span
    ranges = {}
    peak = model.new_int_var(0, 4096, 'physicalPeak')
    for y in range(1, height):
        events = [(i, b, flag) for (line, b), values in write_flags.items()
                  if line == y for i, flag in values]
        if not events:
            continue
        row_window=(line_windows or {}).get(y,window)
        color_limit=max((c for c in range(121) if minimum_commit_span(c)<row_window),default=0)
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
                elif packet_hints is not None and (y,i,bank)in(fixed_address_change_hints or {}):
                    address_hint,changed_hint=fixed_address_change_hints[y,i,bank]
                    model.add_hint(member,int(changed_hint and r<len(hints)and hints[r][0]<=address_hint<=hints[r][1]))
            model.add(sum(choices) == flag)
        cost = sum(24 * active + 16 * length for active, begin, end, length in row)
        writes = sum(flag for i, b, flag in events)
        # Redundant physical bounds strengthen propagation: simultaneous
        # writes occupy distinct opaque slots, at most fifteen per bank.
        model.add(writes <= color_limit)
        model.add(sum(length for active, begin, end, length in row) >= writes)
        if bank_destinations is None:
            bank_active=[]
            for bank in sorted({b for i,b,flag in events}):
                active=model.new_bool_var(f'physicalBankActive{y}_{bank}')
                model.add_max_equality(active,[flag for i,b,flag in events if b==bank])
                bank_active.append(active)
            # R ranges spanning B active banks include at least B-R
            # transparent words. This bound also permits intra-bank splits.
            model.add(sum(length for active,begin,end,length in row)>=writes+sum(bank_active)-sum(active for active,begin,end,length in row))
        model.add(cost <= row_window + 39)
        model.add(peak >= cost)
    return ranges, peak
