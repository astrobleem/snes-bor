"""Reassign palette lifetimes to physical slots and exact prepared DMA ranges.

Piece geometry stays fixed; bank permutations preserve color-math eligibility.
A solver timeout
does not reject raster. Native CPU/setup/contention admission remains separate.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack


def optimize(schedule,window=348,time_limit=180,maximum_ranges=4,trim_dead_residents=True,flexible_prefetch=False,lookahead=16,demand_gap=None,layout_hint=None,reorder_banks=False,fix_hint_slots=False,split_bank_ranges=False,permute_hint_slots=False,retain_write_times=False,rectangle_lifetimes=False,persistent_color_slots=False,paired_bank_ranges=False,collapse_idle_prefix=False,lifetime_repair_interval=None,search_strategy='portfolio',hint_time_radius=None):
    from ortools.sat.python import cp_model
    if schedule.get('status')!='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN' or not schedule.get('compiled_pixel_identity_verified'):
        raise ValueError('SLOT_LAYOUT_VALIDATED_SCHEDULE_REQUIRED')
    if not 1<=window or not 1<=maximum_ranges<=4:raise ValueError('SLOT_LAYOUT_TRANSFER_DOMAIN')
    if search_strategy not in('portfolio','lns'):raise ValueError('SLOT_LAYOUT_SEARCH_STRATEGY')
    if paired_bank_ranges and(reorder_banks or maximum_ranges!=4):raise ValueError('SLOT_LAYOUT_PAIRED_RANGE_DOMAIN')
    if paired_bank_ranges:split_bank_ranges=True
    height=len(schedule['trace']);segments=[];current={};starts={};original_states=[];active_rows=[]
    original={b:[None]*15 for b in range(8)}
    for y,row in enumerate(schedule['trace']):
        if row['scanline']!=y or {int(b):v for b,v in row['resident_before'].items()}!=original:
            raise ValueError('SLOT_LAYOUT_TRACE_CONTINUITY')
        for e in row['updates']:
            key=e['bank'],e['slot']-1
            if key in current:segments[current[key]]['last']=y-1
            i=len(segments);segments.append(dict(bank=key[0],old_slot=key[1],color=e['color'],first=y,last=height-1));current[key]=i
            starts.setdefault((y,key[0]),[]).append(i);original[key[0]][key[1]]=e['color']
        original_states.append(copy.deepcopy(original));active_rows.append(dict(current))
    if flexible_prefetch and(not trim_dead_residents or not isinstance(lookahead,int)or lookahead<0):raise ValueError('SLOT_LAYOUT_PREFETCH_DOMAIN')
    if hint_time_radius is not None and(type(hint_time_radius)is not int or hint_time_radius<0 or not flexible_prefetch or layout_hint is None or retain_write_times):raise ValueError('SLOT_LAYOUT_HINT_TIME_RADIUS_DOMAIN')
    if reorder_banks and not flexible_prefetch:raise ValueError('SLOT_LAYOUT_BANK_REORDER_REQUIRES_PREFETCH')
    if fix_hint_slots and(not flexible_prefetch or layout_hint is None):raise ValueError('SLOT_LAYOUT_FIXED_HINT_REQUIRES_PREFETCH_HINT')
    if permute_hint_slots and(not flexible_prefetch or layout_hint is None or fix_hint_slots):raise ValueError('SLOT_LAYOUT_PERMUTE_HINT_DOMAIN')
    hint_family=fix_hint_slots or permute_hint_slots
    if retain_write_times and(not flexible_prefetch or demand_gap is not None):raise ValueError('SLOT_LAYOUT_RETAIN_WRITE_TIMES_DOMAIN')
    if rectangle_lifetimes and(not flexible_prefetch or hint_family or retain_write_times):raise ValueError('SLOT_LAYOUT_RECTANGLE_LIFETIME_DOMAIN')
    if collapse_idle_prefix and(not flexible_prefetch or retain_write_times):raise ValueError('SLOT_LAYOUT_IDLE_PREFIX_DOMAIN')
    if lifetime_repair_interval is not None:
        if (not retain_write_times or layout_hint is None or not split_bank_ranges or paired_bank_ranges or reorder_banks or
            len(lifetime_repair_interval)!=2 or any(type(y)is not int for y in lifetime_repair_interval) or
            not 0<=lifetime_repair_interval[0]<=lifetime_repair_interval[1]<height):raise ValueError('SLOT_LAYOUT_LIFETIME_REPAIR_DOMAIN')
    required={};last_use={};first_use={}
    for p,mask in zip(schedule['pieces'],schedule['piece_pixel_masks']):
        image=unpack(mask)
        for ly,lx in zip(*np.where(image!=0)):
            y=int(p['y']+ly);bank=p['bank'];s=int(image[ly,lx])-1;i=active_rows[y][bank,s]
            last_use[i]=max(last_use.get(i,-1),y);first_use[i]=min(first_use.get(i,height),y);required.setdefault((y,bank),set()).add(segments[i]['color'])
    first_visible_line=min(first_use.values(),default=0)
    if demand_gap is not None:
        if not isinstance(demand_gap,int)or demand_gap<0 or not trim_dead_residents:raise ValueError('SLOT_LAYOUT_DEMAND_GAP_DOMAIN')
        uses={}
        for (y,b),colors in required.items():
            for color in colors:uses.setdefault((b,color),[]).append(y)
        old_rows=active_rows;segments=[];starts={};first_use={};last_use={};identity={}
        for (b,color),lines in sorted(uses.items()):
            groups=[]
            for y in sorted(lines):
                if not groups or y-groups[-1][-1]>demand_gap+1:groups.append([])
                groups[-1].append(y)
            for group in groups:
                i=len(segments);first,last=group[0],group[-1]
                old_slot=next(s for (bank,s),old in old_rows[first].items()if bank==b and original_states[first][b][s]==color)
                segments.append(dict(bank=b,old_slot=old_slot,color=color,first=first,last=last))
                starts.setdefault((first,b),[]).append(i);first_use[i]=first;last_use[i]=last
                for y in group:identity[y,b,color]=i
        active_rows=[{(b,s):identity[y,b,original_states[y][b][s]] for (b,s)in row if(y,b,original_states[y][b][s])in identity}for y,row in enumerate(old_rows)]
    if trim_dead_residents:
        for i,segment in enumerate(segments):segment['last']=last_use.get(i,-1)
        active_rows=[{key:i for key,i in row.items()if segments[i]['last']>=y}for y,row in enumerate(active_rows)]
        starts={key:[i for i in values if i in last_use]for key,values in starts.items()}
        starts={key:values for key,values in starts.items()if values}
    hinted={};hint_banks={b:b for b in range(8)}
    if layout_hint is not None:
        hint_banks={int(b):int(v)for b,v in layout_hint.get('physical_slot_layout',{}).get('fixed_piece_bank_permutation',hint_banks).items()}
        if set(hint_banks)!=set(range(8))or sorted(hint_banks.values())!=list(range(8)):raise ValueError('SLOT_LAYOUT_HINT_BANK_PERMUTATION')
        if schedule.get('color_math','additive')=='additive'and any(b//4!=v//4 for b,v in hint_banks.items()):raise ValueError('SLOT_LAYOUT_HINT_COLOR_MATH_CLASS')
        expected_pieces=[dict(p,bank=hint_banks[p['bank']])for p in schedule['pieces']]
        if layout_hint.get('pieces')!=expected_pieces or layout_hint.get('source_rgb555_sha256')!=schedule.get('source_rgb555_sha256')or not layout_hint.get('physical_slot_layout',{}).get('pixel_color_identity_verified'):raise ValueError('SLOT_LAYOUT_HINT_IDENTITY')
        pixels={}
        for p,old,new in zip(schedule['pieces'],schedule['piece_pixel_masks'],layout_hint['piece_pixel_masks']):
            a,b=unpack(old),unpack(new)
            if not np.array_equal(a!=0,b!=0):raise ValueError('SLOT_LAYOUT_HINT_PIXEL_MASK')
            for ly,lx in zip(*np.where(a!=0)):
                y=int(p['y']+ly);i=active_rows[y][p['bank'],int(a[ly,lx])-1]
                pixels.setdefault(i,int(b[ly,lx])-1)
        for i in last_use:
            slot=pixels[i];s=segments[i];events=[row['scanline']for row in layout_hint['trace']if row['scanline']<=first_use[i]for e in row['updates']if e['bank']==hint_banks[s['bank']]and e['slot']==slot+1 and e['color']==s['color']]
            if events:hinted[i]=(slot,max(events))
    model=cp_model.CpModel();slots=[model.new_int_var(0,14,'s'+str(i))for i in range(len(segments))]
    repair_lifetimes=[]
    if lifetime_repair_interval is not None:
        if set(hinted)!=set(last_use):raise ValueError('SLOT_LAYOUT_LIFETIME_REPAIR_HINT_INCOMPLETE')
        left,right=lifetime_repair_interval
        for i in sorted(last_use):
            if left<=segments[i]['first']<=segments[i]['last']<=right:repair_lifetimes.append(i)
            else:model.add(slots[i]==hinted[i][0])
    if persistent_color_slots:
        anchors={}
        for i in sorted(last_use):
            key=segments[i]['bank'],segments[i]['color']
            if key in anchors:model.add(slots[i]==slots[anchors[key]])
            else:anchors[key]=i
    if fix_hint_slots:
        if set(hinted)!=set(last_use):raise ValueError('SLOT_LAYOUT_FIXED_HINT_INCOMPLETE')
        for i,(slot,time)in hinted.items():model.add(slots[i]==slot)
    if permute_hint_slots:
        if set(hinted)!=set(last_use):raise ValueError('SLOT_LAYOUT_PERMUTE_HINT_INCOMPLETE')
        permutations={}
        for bank in range(8):
            values=[model.new_int_var(0,14,f'slotPermutation{bank}_{s}')for s in range(15)]
            model.add_all_different(values)
            for s,value in enumerate(values):permutations[bank,s]=value;model.add_hint(value,s)
        for i,(slot,time)in hinted.items():model.add(slots[i]==permutations[segments[i]['bank'],slot])
    destinations={};bank_choices={}
    if reorder_banks:
        additive=schedule.get('color_math','additive')=='additive'
        for bank in range(8):
            allowed=range((bank//4)*4,(bank//4)*4+4)if additive else range(8)
            destinations[bank]=model.new_int_var_from_domain(cp_model.Domain.from_values(list(allowed)),'bank'+str(bank))
            model.add_hint(destinations[bank],hint_banks[bank])
            for b in (()if split_bank_ranges else allowed):
                q=model.new_bool_var(f'bank{bank}_{b}');model.add(destinations[bank]==b).only_enforce_if(q);model.add(destinations[bank]!=b).only_enforce_if(q.Not());bank_choices[bank,b]=q
        model.add_all_different(list(destinations.values()))
    seen=set();write_times={};write_flags={};fixed_earliest={};pruned_write_times=0;event_hints={}
    if hint_family:
        lanes={}
        for i in sorted(last_use,key=lambda i:(first_use[i],i)):
            key=segments[i]['bank'],hinted[i][0]
            fixed_earliest[i]=lanes.get(key,0)
            lanes[key]=max(lanes.get(key,0),last_use[i]+1)
    if flexible_prefetch:
        lanes={(b,s):[]for b in range(8)for s in range(15)}
        rectangles={b:[]for b in range(8)}
        for i in sorted(last_use):
            first=first_use[i];earliest=max(1,first-lookahead,first_visible_line+1 if collapse_idle_prefix else 1)
            allowed=[0]+list(range(earliest,first+1))
            if retain_write_times:
                if segments[i]['first']not in allowed:raise ValueError('SLOT_LAYOUT_RETAIN_WRITE_TIMES_LATENCY')
                allowed=[segments[i]['first']]
            if hint_family:
                revised=[y for y in allowed if y>=fixed_earliest[i]]
                pruned_write_times+=len(allowed)-len(revised)
                if revised:allowed=revised
                else:model.add(False)
            if hint_time_radius is not None:
                if i not in hinted:raise ValueError('SLOT_LAYOUT_HINT_TIME_RADIUS_INCOMPLETE')
                center=hinted[i][1]
                # Free VBlank initialization stays free when an idle prefix
                # is collapsed; constrain only noninitial transfer timing.
                allowed=[y for y in allowed if (y==0 and center<=first_visible_line and collapse_idle_prefix) or abs(y-center)<=hint_time_radius]
                if not allowed:raise ValueError('SLOT_LAYOUT_HINT_TIME_RADIUS_EMPTY')
            start=model.new_int_var_from_domain(cp_model.Domain.from_values(allowed),'time'+str(i));write_times[i]=start
            original_time=hinted.get(i,(0,segments[i]['first']))[1];hint=original_time if original_time in allowed else allowed[0]
            model.add_hint(start,hint)
            if i in hinted:event_hints[i]=(16*hint_banks[segments[i]['bank']]+hinted[i][0]+1,hint)
            end=last_use[i]+1;duration=model.new_int_var(1,end,'duration'+str(i));model.add(duration==end-start)
            model.add_hint(duration,end-hint)
            if rectangle_lifetimes:
                time_interval=model.new_interval_var(start,duration,end,'timeLife'+str(i))
                slot_interval=model.new_fixed_size_interval_var(slots[i],1,'slotLife'+str(i))
                rectangles[segments[i]['bank']].append((slot_interval,time_interval))
            for s in range(15):
                if hint_family or retain_write_times or rectangle_lifetimes:break
                present=model.new_bool_var(f'lane{i}_{s}');model.add(slots[i]==s).only_enforce_if(present);model.add(slots[i]!=s).only_enforce_if(present.Not())
                model.add_hint(present,int(s==hinted.get(i,(segments[i]['old_slot'],0))[0]))
                lanes[segments[i]['bank'],s].append(model.new_optional_interval_var(start,duration,end,present,f'life{i}_{s}'))
            for y in allowed:
                flag=model.new_bool_var(f'write{i}_{y}');model.add(start==y).only_enforce_if(flag);model.add(start!=y).only_enforce_if(flag.Not())
                model.add_hint(flag,int(y==hint))
                bank=segments[i]['bank']
                if reorder_banks and not split_bank_ranges:
                    for (old,b),q in bank_choices.items():
                        if old!=bank:continue
                        f=model.new_bool_var(f'physicalWrite{i}_{y}_{b}');model.add(f<=flag);model.add(f<=q);model.add(f>=flag+q-1)
                        write_flags.setdefault((y,b),[]).append((i,f))
                else:write_flags.setdefault((y,bank),[]).append((i,flag))
        for values in lanes.values():model.add_no_overlap(values)
        for values in rectangles.values():
            if values:model.add_no_overlap_2d([v[0]for v in values],[v[1]for v in values])
    if not flexible_prefetch or retain_write_times:
        for y in range(height):
            row={i:segment for i,segment in enumerate(segments)if segment['first']<=y<=segment['last']}
            for bank in range(8):
                values=tuple(i for i,segment in row.items()if segment['bank']==bank)
                if len(values)>1 and values not in seen:model.add_all_different([slots[i]for i in values]);seen.add(values)
    ranges={};peak=model.new_int_var(0,4096,'peak')
    for y in range(1,height):
        if split_bank_ranges:break
        banks=[b for b in range(8)if(y,b)in(write_flags if flexible_prefetch else starts)]
        if not banks:continue
        lo={};hi={};active={}
        for b in banks:
            lo[b]=model.new_int_var(0,15,f'lo{y}_{b}');hi[b]=model.new_int_var(-1,14,f'hi{y}_{b}')
            if flexible_prefetch:
                minimum=[];maximum=[];flags=[]
                for i,flag in write_flags[y,b]:
                    mn=model.new_int_var(0,15,f'mn{i}_{y}');mx=model.new_int_var(-1,14,f'mx{i}_{y}')
                    model.add(mn==slots[i]).only_enforce_if(flag);model.add(mn==15).only_enforce_if(flag.Not())
                    model.add(mx==slots[i]).only_enforce_if(flag);model.add(mx==-1).only_enforce_if(flag.Not())
                    minimum.append(mn);maximum.append(mx);flags.append(flag)
                model.add_min_equality(lo[b],minimum);model.add_max_equality(hi[b],maximum)
                active[b]=model.new_bool_var(f'active{y}_{b}');model.add_max_equality(active[b],flags)
            else:
                model.add_min_equality(lo[b],[slots[i]for i in starts[y,b]])
                model.add_max_equality(hi[b],[slots[i]for i in starts[y,b]])
        selected=[];costs=[];cover={b:[]for b in banks}
        for first_index,first in enumerate(banks):
            for last in banks[first_index:]:
                q=model.new_bool_var(f'r{y}_{first}_{last}');cost=model.new_int_var(0,2048,f'c{y}_{first}_{last}')
                if flexible_prefetch:model.add(q<=active[first]);model.add(q<=active[last])
                words=16*(last-first)+hi[last]-lo[first]+1
                model.add(cost==16*words+24).only_enforce_if(q);model.add(cost==0).only_enforce_if(q.Not())
                for b in banks:
                    if first<=b<=last:cover[b].append(q)
                ranges[y,first,last]=q;selected.append(q);costs.append(cost)
        for b,values in cover.items():
            if flexible_prefetch:model.add(sum(values)<=1);model.add(sum(values)>=active[b])
            else:model.add(sum(values)==1)
        model.add(sum(selected)<=maximum_ranges);model.add(sum(costs)<=window+39);model.add(peak>=sum(costs))
    if split_bank_ranges:
        from raster_physical_ranges import constrain,constrain_pairs
        if not flexible_prefetch:write_flags={key:[(i,model.new_constant(1))for i in values]for key,values in starts.items()}
        packet_hints=None
        if layout_hint and layout_hint.get('prepared_dma_packets'):
            packet_hints={row['scanline']:sorted((p['cgram_word_address']-128,p['cgram_word_address']-128+p['word_count']-1)for p in row['packets'])for row in layout_hint['prepared_dma_packets']}
        ranges,peak=constrain_pairs(model,write_flags,slots,height,window)if paired_bank_ranges else constrain(model,write_flags,slots,height,maximum_ranges,window,destinations if reorder_banks else None,packet_hints,event_hints)
    for i,segment in enumerate(segments):model.add_hint(slots[i],hinted.get(i,(segment['old_slot'],0))[0])
    if lifetime_repair_interval is None:model.minimize(peak)
    else:
        left,right=lifetime_repair_interval;costs=[];repair_peak=model.new_int_var(0,4096,'lifetimeRepairPeak')
        for y in range(max(1,left),right+1):
            cost=sum(24*a+16*n for(line,r),(a,begin,end,n)in ranges.items()if line==y)
            model.add(repair_peak>=cost);costs.append(cost)
        model.minimize(repair_peak*(4096*len(costs)+1)+sum(costs))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    if search_strategy=='lns':solver.parameters.use_lns_only=True
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
    status=solver.solve(model)
    result=dict(schema='BYOR_PHYSICAL_RASTER_SLOT_LAYOUT_V1',status='BOUNDED_SLOT_LAYOUT_NO_CANDIDATE',
                solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
                solver_search_strategy=search_strategy,
                lifetime_segments=len(segments),window_master_clocks=window,maximum_ranges=maximum_ranges,
                input_schedule_noninitial_prefetch_latency_lines=max((first_use[i]-segments[i]['first']for i in last_use if segments[i]['first']>0),default=0),
                trim_dead_residents=trim_dead_residents,used_lifetime_segments=len(last_use),
                flexible_prefetch=flexible_prefetch,lookahead_lines=lookahead if flexible_prefetch else None,
                hint_time_radius_lines=hint_time_radius,
                demand_gap_lines=demand_gap,
                idle_prefix_collapsed=collapse_idle_prefix,first_visible_source_line=first_visible_line,
                layout_hint_used=layout_hint is not None,
                reorder_banks=reorder_banks,
                fixed_hint_slots=fix_hint_slots,
                permute_hint_slots=permute_hint_slots,
                retain_write_times=retain_write_times,
                lifetime_repair_interval=list(lifetime_repair_interval)if lifetime_repair_interval is not None else None,
                movable_complete_lifetimes=len(repair_lifetimes),
                rectangle_lifetimes=rectangle_lifetimes,persistent_color_slots=persistent_color_slots,
                split_bank_ranges=split_bank_ranges,
                paired_bank_ranges=paired_bank_ranges,
                fixed_slot_write_times_pruned=pruned_write_times,
                solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints),
                solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,
                solver_probing_level=0,solver_sat_inprocessing=False,
                universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
    if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL):return result
    bank_map={b:solver.value(destinations[b])if reorder_banks else b for b in range(8)}
    result['fixed_piece_bank_permutation']=bank_map
    result['initial_palette_may_preload_entire_frame']=True
    result['maximum_noninitial_prefetch_latency_lines']=max((first_use[i]-(solver.value(write_times[i])if flexible_prefetch else segments[i]['first'])for i in last_use if(solver.value(write_times[i])if flexible_prefetch else segments[i]['first'])>0),default=0)
    if permute_hint_slots:result['fixed_hint_slot_permutations']={b:[solver.value(permutations[b,s])for s in range(15)]for b in range(8)}
    if flexible_prefetch:
        starts={}
        for i,time in write_times.items():starts.setdefault((solver.value(time),bank_map[segments[i]['bank']]),[]).append(i)
    assigned=[solver.value(v)for v in slots];state={b:[None]*15 for b in range(8)};states=[];trace=[];packets=[];physical=[0]*128
    for y,row in enumerate(schedule['trace']):
        before=copy.deepcopy(state);events=[]
        for b in range(8):
            for i in starts.get((y,b),[]):
                s=assigned[i];c=segments[i]['color'];old_bank=segments[i]['bank'];events.append(dict(bank=b,slot=s+1,old=state[b][s],color=c,kind='required'if c in required.get((y,old_bank),set())else'prefetch'));state[b][s]=c
        groups=[]
        if y:
            bounds=[]
            if split_bank_ranges:
                bounds=[(128+solver.value(begin),128+solver.value(end))for (line,r),(active,begin,end,length)in ranges.items()if line==y and solver.value(active)]
            else:
                for (line,first,last),q in ranges.items():
                    if line!=y or not solver.value(q):continue
                    first_slot=min(assigned[i]for i in starts[y,first])+1;last_slot=max(assigned[i]for i in starts[y,last])+1
                    bounds.append((128+16*first+first_slot,128+16*last+last_slot))
            for begin,end in bounds:
                data=bytearray()
                for address in range(begin,end+1):
                    bank,slot=divmod(address-128,16);c=0 if slot==0 else state[bank][slot-1]
                    data.extend((0 if c is None else c).to_bytes(2,'little'))
                groups.append(dict(cgram_word_address=begin,word_count=end-begin+1,data_hex=data.hex()))
            span=max(0,sum(16*p['word_count']+24 for p in groups)-40)
            if span>=window:raise AssertionError('SLOT_LAYOUT_PACKET_WINDOW')
        else:span=0
        if y==0:
            for e in events:physical[e['bank']*16+e['slot']]=e['color']
        for p in groups:
            data=bytes.fromhex(p['data_hex']);begin=p['cgram_word_address']-128
            for i in range(p['word_count']):physical[begin+i]=int.from_bytes(data[2*i:2*i+2],'little')
        for b in range(8):
            if physical[b*16]!=0 or physical[b*16+1:b*16+16]!=[0 if c is None else c for c in state[b]]:
                raise AssertionError('SLOT_LAYOUT_PACKET_CGRAM_IDENTITY')
        # Verify every previously indexed color survives at its assigned slot.
        for (b,s),i in active_rows[y].items():
            if flexible_prefetch and y<first_use[i]:continue
            if state[bank_map[b]][assigned[i]]!=original_states[y][b][s]:raise AssertionError('SLOT_LAYOUT_LIFETIME_IDENTITY')
        states.append(copy.deepcopy(state));packets.append(dict(scanline=y,packets=groups,prepared_commit_span=span))
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in values if c is not None and c in state[b]]for b,values in before.items()},
                          evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
    rewritten=copy.deepcopy(schedule);images=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p,mask in zip(schedule['pieces'],schedule['piece_pixel_masks']):
        image=unpack(mask);new=image.copy();bank=p['bank'];physical_bank=bank_map[bank]
        for ly,lx in zip(*np.where(image!=0)):
            y,x=int(p['y']+ly),int(p['x']+lx);old_slot=int(image[ly,lx])-1;i=active_rows[y][bank,old_slot];s=assigned[i]
            if states[y][physical_bank][s]!=original_states[y][bank][old_slot]:raise AssertionError('SLOT_LAYOUT_PIXEL_COLOR_IDENTITY')
            new[ly,lx]=s+1;indices[y,x]=128+physical_bank*16+s+1
        flat=new.flatten();images.append(dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    rewritten.update(trace=trace,piece_pixel_masks=images,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
                     physical_slot_layout=result,prepared_dma_packets=packets,
                     peak_scheduled_writes=max(row['colors_written']for row in trace[1:]),
                     peak_cgram_data_bytes=max(row['cgram_data_bytes']for row in trace[1:]),
                     worst_scanline=1+int(np.argmax([row['colors_written']for row in trace[1:]])),
                     average_writes=float(np.mean([row['colors_written']for row in trace[1:]])))
    for piece in rewritten['pieces']:piece['bank']=bank_map[piece['bank']]
    payload=dict(pieces=rewritten['pieces'],pixel_masks=images,trace=trace)
    if rewritten.get('scanline_math_controls_source_bound'):
        payload.update(selected_modes=rewritten['selected_modes'],compiled_color_window_descriptors=rewritten['compiled_color_window_descriptors'])
    rewritten['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    result.update(status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',peak_prepared_commit_span=max(p['prepared_commit_span']for p in packets),
                  peak_ranges=max(len(p['packets'])for p in packets),pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True)
    return rewritten


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window',type=int,default=348);p.add_argument('--time-limit',type=float,default=180);p.add_argument('--maximum-ranges',type=int,default=4)
    p.add_argument('--flexible-prefetch',action='store_true');p.add_argument('--lookahead',type=int,default=16)
    p.add_argument('--demand-gap',type=int)
    p.add_argument('--layout-hint',type=Path)
    p.add_argument('--reorder-banks',action='store_true')
    p.add_argument('--fix-hint-slots',action='store_true')
    p.add_argument('--split-bank-ranges',action='store_true')
    p.add_argument('--permute-hint-slots',action='store_true')
    p.add_argument('--retain-write-times',action='store_true')
    p.add_argument('--rectangle-lifetimes',action='store_true')
    p.add_argument('--persistent-color-slots',action='store_true')
    p.add_argument('--paired-bank-ranges',action='store_true')
    p.add_argument('--collapse-idle-prefix',action='store_true',help='Fold writes through the first visible source row into free VBlank initialization; requires flexible prefetch without fixed write times.')
    p.add_argument('--lifetime-repair-interval',type=int,nargs=2,help='Reassign only complete lifetimes inside this inclusive interval; requires a physical hint, retained write times and split ranges.')
    p.add_argument('--search-strategy',choices=('portfolio','lns'),default='portfolio')
    p.add_argument('--hint-time-radius',type=int,help='Restrict noninitial prefetch timing around verified hint writes, while permitting new lifetime slots.')
    a=p.parse_args();r=optimize(json.loads(a.schedule.read_text()),a.window,a.time_limit,a.maximum_ranges,flexible_prefetch=a.flexible_prefetch,lookahead=a.lookahead,demand_gap=a.demand_gap,layout_hint=json.loads(a.layout_hint.read_text())if a.layout_hint else None,reorder_banks=a.reorder_banks,fix_hint_slots=a.fix_hint_slots,split_bank_ranges=a.split_bank_ranges,permute_hint_slots=a.permute_hint_slots,retain_write_times=a.retain_write_times,rectangle_lifetimes=a.rectangle_lifetimes,persistent_color_slots=a.persistent_color_slots,paired_bank_ranges=a.paired_bank_ranges,collapse_idle_prefix=a.collapse_idle_prefix,lifetime_repair_interval=a.lifetime_repair_interval,search_strategy=a.search_strategy,hint_time_radius=a.hint_time_radius)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('physical_slot_layout',r)))


if __name__=='__main__':main()
