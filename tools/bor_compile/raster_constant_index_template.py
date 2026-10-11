"""Source-exact constant word-index template for later palette prefetch.

This restricted family is optional. Its failure never rejects raster, and a
template is not a transfer-window or native admission.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_physical_relabel import point_partition
from raster_slot_refine import verify_packets


def construct(source,time_limit=10):
    from ortools.sat.python import cp_model
    if time_limit<=0:raise ValueError('CONSTANT_INDEX_TIME_DOMAIN')
    required,uses,pixels=demand(source);indices={};banks=[]
    for b in range(8):
        if not uses[b]:indices[b]={};continue
        model=cp_model.CpModel();slots={c:model.new_int_var(0,14,f'color{c}')for c in uses[b]}
        anchor=max((row[b]for row in required),key=len)
        for s,c in enumerate(sorted(anchor)):model.add(slots[c]==s)
        seen=set()
        for row in required:
            colors=tuple(sorted(row[b]))
            if len(colors)>1 and colors not in seen:model.add_all_different([slots[c]for c in colors]);seen.add(colors)
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
        status=solver.solve(model);banks.append(dict(bank=b,status=solver.status_name(status),seconds=solver.wall_time))
        if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):
            return dict(schema='BYOR_CONSTANT_WORD_INDEX_TEMPLATE_V1',status='CONSTANT_INDEX_FAMILY_NO_CANDIDATE',
                banks=banks,constant_word_index_family_only=True,universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
        indices[b]={c:solver.value(v)+1 for c,v in slots.items()}
    initial={b:[0]*15 for b in range(8)};seen=set()
    for row in required:
        for b in range(8):
            for c in sorted(row[b]):
                s=indices[b][c]
                if(b,s)not in seen:initial[b][s-1]=c;seen.add((b,s))
    state={b:[None]*15 for b in range(8)};snapshots=[];trace=[];packets=[];physical=[0]*128
    for y,row in enumerate(required):
        before=copy.deepcopy(state);events=[]
        wanted=initial if y==0 else{b:{indices[b][c]:c for c in row[b]}for b in range(8)}
        for b in range(8):
            edits=enumerate(wanted[b],1)if y==0 else sorted(wanted[b].items())
            for s,c in edits:
                if state[b][s-1]!=c:
                    events.append(dict(bank=b,slot=s,old=state[b][s-1],color=c,kind='required'if c in row[b]else'prefetch'))
                    state[b][s-1]=c;physical[16*b+s]=c
        span,groups=point_partition([16*e['bank']+e['slot']for e in events]if y else[])
        packets.append(dict(scanline=y,prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,
            data_hex=b''.join(physical[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in groups]))
        trace.append(dict(scanline=y,resident_before=before,updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),
            retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},
            evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],affected_banks=sorted({e['bank']for e in events})))
        snapshots.append(copy.deepcopy(state))
    masks=[];canvas=np.zeros((len(required),256),dtype=np.uint8)
    for p,words in zip(source['pieces'],pixels):
        image=np.zeros(words.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(words>=0)):
            c=int(words[ly,lx]);s=indices[p['bank']][c];y,x=int(p['y']+ly),int(p['x']+lx)
            if snapshots[y][p['bank']][s-1]!=c:raise AssertionError('CONSTANT_INDEX_SOURCE_WORD')
            image[ly,lx]=s;canvas[y,x]=128+16*p['bank']+s
        flat=image.flatten();masks.append(dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    report=dict(schema='BYOR_CONSTANT_WORD_INDEX_TEMPLATE_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',banks=banks,
        constant_word_indices=True,constant_word_index_family_only=True,slot_labels_canonicalized_without_transfer_constraints=True,
        peak_prepared_commit_span=max(r['prepared_commit_span']for r in packets),peak_changed_physical_words=max(len(r['updates'])for r in trace[1:]),
        pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    wanted_rows=[{(b,indices[b][c]):c for b in range(8)for c in row[b]}for row in required]
    forced=[sum(address in wanted_rows[y-1]and wanted_rows[y-1][address]!=c for address,c in row.items())if y else 0 for y,row in enumerate(wanted_rows)]
    report.update(peak_unavoidable_adjacent_slot_overwrites_for_this_mapping=max(forced),
        worst_forced_overwrite_scanline=int(np.argmax(forced)),forced_overwrite_count_ignores_other_liveness_and_physical_range_costs=True)
    previous={};write_windows=[]
    for y,row in enumerate(wanted_rows):
        for address,c in row.items():
            if address in previous and previous[address][0]!=c:write_windows.append((previous[address][1]+1,y))
            previous[address]=(c,y)
    visible=[y for y,row in enumerate(wanted_rows)if row];density=(0,None,0)
    for left in range(min(visible),max(visible)+1):
        for right in range(left,max(visible)+1):
            count=sum(left<=release and deadline<=right for release,deadline in write_windows)
            value=count/(right-left+1)
            if value>density[0]:density=(value,[left,right],count)
    report.update(constant_index_write_window_density_lower_bound=density[0],
        write_density_worst_interval=density[1],write_density_interval_events=density[2],noninitial_constant_index_write_events=len(write_windows),
        word_indices=indices)
    result=copy.deepcopy(source);result.update(trace=trace,piece_pixel_masks=masks,prepared_dma_packets=packets,physical_slot_layout=report,
        native_presentation_proven=False,input_compiled_schedule_sha256=source.get('compiled_schedule_sha256'),
        peak_scheduled_writes=report['peak_changed_physical_words'],peak_cgram_data_bytes=2*report['peak_changed_physical_words'],
        average_writes=float(np.mean([len(r['updates'])for r in trace[1:]])),worst_scanline=1+int(np.argmax([len(r['updates'])for r in trace[1:]])),
        write_budget=None,lookahead_lines=0,maximum_noninitial_prefetch_latency_lines=0,
        schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=0,initial_palette_may_preload_entire_frame=True))
    for field in('bank_residency','physical_slot_refinement'):
        if field in result:result['input_'+field]=result.pop(field)
    payload=dict(pieces=result['pieces'],pixel_masks=masks,trace=trace)
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    result['compiled_indices_sha256']=hashlib.sha256(canvas.tobytes()).hexdigest()
    result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    verify_packets(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,demand(result)[2])):raise AssertionError('CONSTANT_INDEX_PIXEL_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--time-limit',type=float,default=10)
    a=p.parse_args();result=construct(json.loads(a.schedule.read_text()),a.time_limit)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.get('physical_slot_layout',result).items()if k!='word_indices'}))


if __name__=='__main__':main()
