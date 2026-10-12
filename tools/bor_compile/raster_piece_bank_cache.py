"""Joint fixed OAM piece banks and alias-aware palette cache liveness.

Repeated RGB555 words may appear in multiple banks. A bank counts each word
once, even when several objects demand it. Source rectangles and encoding
classes remain fixed; transfer endpoints and physical slots remain relaxed.
"""
import copy
from collections import deque
import numpy as np
from raster_slot_greedy import demand,bank_groups
from raster_global_bank_classes import rebuild_schedule
from raster_bank_residency import constrain_flow
from raster_word_cache_repair import compile_cache_rows
from raster_obj_geometry import active_on_line,tile_slivers


def validated_assignment_hints(source,hint,images,domains,allow_word_masks,row_word_masks):
    """Replay source ownership/words before supplying optional bank-choice hints."""
    if (source.get('source_rgb555_sha256')!=hint.get('source_rgb555_sha256') or
        any(source.get(k)!=hint.get(k) for k in ('selected_modes','compiled_color_window_descriptors'))):
        raise ValueError('PIECE_BANK_CACHE_HINT_SOURCE_IDENTITY')
    def pixels(frame,decoded):
        result={}
        for p,image in zip(frame['pieces'],decoded):
            for y,x in zip(*np.where(image>=0)):
                key=(p['actor'],int(p['y']+y),int(p['x']+x))
                if key in result:raise ValueError('PIECE_BANK_CACHE_HINT_OVERLAPPING_OWNERSHIP')
                result[key]=(int(image[y,x]),p['bank'])
        return result
    original=pixels(source,images);actual=pixels(hint,demand(hint)[2])
    if original.keys()!=actual.keys() or any(original[k][0]!=actual[k][0] for k in original):
        raise ValueError('PIECE_BANK_CACHE_HINT_PIXEL_IDENTITY')
    choices={}
    for i,(p,image) in enumerate(zip(source['pieces'],images)):
        for y,x in zip(*np.where(image>=0)):
            yy=int(p['y']+y);c=int(image[y,x]);bank=actual[p['actor'],yy,int(p['x']+x)][1]
            if bank not in domains[i]:raise ValueError('PIECE_BANK_CACHE_HINT_BANK_ELIGIBILITY')
            key=(i,c,yy)if row_word_masks else(i,c)if allow_word_masks else i
            choices.setdefault(key,set()).add(bank)
    # A legal split hint may use multiple banks for a coarser decision. Such
    # choices are omitted, never fixed or converted into a false source claim.
    return {key:next(iter(banks)) for key,banks in choices.items() if len(banks)==1}


def optimize(source,time_limit=45,write_budget=21,window=337,lookahead=55,search_strategy='portfolio',allow_word_masks=False,maximum_masks_per_piece=2,maximum_oam=128,maximum_sprites=32,maximum_tiles=34,row_word_masks=False,assignment_hint=None,geometry_reservation=None):
    from ortools.sat.python import cp_model
    if time_limit<=0 or not 0<=write_budget<=120 or window<1 or lookahead<0:raise ValueError('PIECE_BANK_CACHE_DOMAIN')
    if search_strategy not in('portfolio','sat','sat-repair','lns'):raise ValueError('PIECE_BANK_CACHE_SEARCH_STRATEGY')
    if row_word_masks and not allow_word_masks:raise ValueError('PIECE_BANK_CACHE_ROW_MASKS_REQUIRE_WORD_MASKS')
    if not 1<=maximum_masks_per_piece<=8 or not 1<=maximum_oam<=128 or not 1<=maximum_sprites<=32 or not 1<=maximum_tiles<=34:raise ValueError('PIECE_BANK_CACHE_GEOMETRY_DOMAIN')
    required,_,images=demand(source);pieces=copy.deepcopy(source['pieces']);groups=bank_groups(source);owners={};row_owners={};domains={}
    height=len(required);reservation=geometry_reservation if geometry_reservation is not None else source.get('geometry_reservation')
    if reservation is None:reservation=dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
    if not isinstance(reservation,dict)or set(reservation)!={'oam_entries','sprites_per_line','tile_slivers_per_line'}or type(reservation['oam_entries'])is not int or not 0<=reservation['oam_entries']<=128 or any(not isinstance(reservation[k],list)or len(reservation[k])!=height or any(type(v)is not int or not 0<=v<=limit for v in reservation[k])for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)]):raise ValueError('PIECE_BANK_CACHE_GEOMETRY_RESERVATION')
    reservation=copy.deepcopy(reservation)
    for i,(p,image)in enumerate(zip(pieces,images)):
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if np.any(row>=0)}
        domains[i]=tuple(b for b in next(g for g in groups if p['bank']in g)if b in p.get('allowed_banks',range(8)))
        if not domains[i]:raise ValueError('PIECE_BANK_CACHE_BANK_ELIGIBILITY')
        for y,cs in p['rows'].items():
            for c in cs:owners.setdefault(c,set()).add(i);row_owners.setdefault((y,c),set()).add(i)
    validated_hints=validated_assignment_hints(source,assignment_hint,images,domains,allow_word_masks,row_word_masks)if assignment_hint is not None else {}
    active=sorted({y for y,c in row_owners})
    if not active:raise ValueError('PIECE_BANK_CACHE_EMPTY')
    first,last=min(active),max(active);model=cp_model.CpModel();selection={};resident={};writes={};by_line={};write_lines={}
    color_rows={}
    for(y,c),indices in row_owners.items():color_rows.setdefault(c,{})[y]=indices
    masks={}
    for i,p in enumerate(pieces):
        colors=sorted({c for cs in p['rows'].values()for c in cs})
        keys=[(i,c,y)for y,cs in p['rows'].items()for c in cs]if row_word_masks else [(i,c)for c in colors]if allow_word_masks else[i]
        for key in keys:
            selection[key]={b:model.new_bool_var(f'piece{key}_{b}')for b in domains[i]};model.add_exactly_one(list(selection[key].values()))
            for b,v in selection[key].items():model.add_hint(v,int(b==validated_hints.get(key,p['bank'])))
        for b in domains[i]:
            if allow_word_masks:
                mask=model.new_bool_var(f'mask{i}_{b}')
                if colors:model.add_max_equality(mask,[selection[key][b]for key in keys])
                else:model.add(mask==0)
                masks[i,b]=mask
            else:masks[i,b]=selection[i][b]
        if allow_word_masks:model.add(sum(masks[i,b]for b in domains[i])<=maximum_masks_per_piece)
    def selected(i,c,y,b):return selection[(i,c,y)if row_word_masks else(i,c)if allow_word_masks else i][b]
    model.add(sum(masks.values())<=maximum_oam-reservation['oam_entries'])
    interchangeable=window>16*128+24*3-16 and all(domains[i]==tuple(next(g for g in groups if p['bank']in g))for i,p in enumerate(pieces))
    if interchangeable:
        for group in groups:
            for before,bank in zip(group,group[1:]):
                for i in range(len(pieces)):
                    if(i,bank)in masks:model.add(masks[i,bank]<=sum(masks[j,before]for j in range(i+1)if(j,before)in masks))
    for y in range(height):
        live=[(i,v)for(i,b),v in masks.items()if active_on_line(pieces[i],y)]
        model.add(sum(v for i,v in live)<=maximum_sprites-reservation['sprites_per_line'][y])
        model.add(sum(v*tile_slivers(pieces[i])for i,v in live)<=maximum_tiles-reservation['tile_slivers_per_line'][y])
    hints=[];state={b:[None]*15 for b in range(8)}
    for row in (assignment_hint or source)['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        hints.append({b:set(c for c in cs if c is not None)for b,cs in state.items()})
    for c,indices in owners.items():
        last_use=max(color_rows[c])
        for b in sorted({b for i in indices for b in domains[i]}):
            options=list({selected(i,c,y,b).index:selected(i,c,y,b)for y,ii in color_rows[c].items()for i in ii if b in domains[i]}.values())
            ever=model.new_bool_var(f'ever{c}_{b}');model.add_max_equality(ever,options)
            for y in range(first,last_use+1):
                r=model.new_bool_var(f'r{c}_{b}_{y}');resident[c,b,y]=r;by_line.setdefault((y,b),[]).append(r);model.add(r<=ever)
                for i in row_owners.get((y,c),[]):
                    if b in domains[i]:model.add(r>=selected(i,c,y,b))
                model.add_hint(r,int(c in hints[y][b]))
                if y==first:continue
                previous=resident[c,b,y-1];future={selected(i,c,yy,b).index:selected(i,c,yy,b)for yy,indices_on_row in color_rows[c].items()if y<=yy<=y+lookahead for i in indices_on_row if b in domains[i]}
                if not future:model.add(r<=previous);continue
                w=model.new_bool_var(f'w{c}_{b}_{y}');writes[c,b,y]=w;write_lines.setdefault((y,b),[]).append(w)
                model.add(w>=r-previous);model.add(w<=r);model.add(w+previous<=1);model.add(w<=sum(future.values()))
                model.add_hint(w,int(c in hints[y][b]and c not in hints[y-1][b]))
    counts_by_line={}
    for y in range(first,last+1):
        for b in range(8):model.add(sum(by_line.get((y,b),[]))<=15)
        if y==first:continue
        counts=[];flags=[]
        for b in range(8):
            n=model.new_int_var(0,15,f'count{y}_{b}');model.add(n==sum(write_lines.get((y,b),[])));counts.append(n);counts_by_line[y,b]=n
            flag=model.new_bool_var(f'active{y}_{b}');model.add(n>=flag);model.add(n<=15*flag);flags.append(flag)
        model.add(sum(counts)<=write_budget)
        # Even a full 128-word enclosing range fits this conservative span.
        # Omit only a provably redundant flow graph, including its range cap.
        worst_span=16*128+24*3-16
        if window<=worst_span:constrain_flow(model,counts,flags,window,f'pieceCache{y}')
    # Each bank can bring only fifteen distinct identities into an interval.
    # OR the participating objects before counting an identity, so shared words
    # never become spurious compulsory duplicate loads.
    prefixes={};aliases={};interval_cuts=0
    for b in range(8):
        prefixes[first,b]=model.new_constant(0)
        for y in range(first+1,last+1):
            prefix=model.new_int_var(0,15*(y-first),f'writePrefix{y}_{b}');prefixes[y,b]=prefix
            model.add(prefix==prefixes[y-1,b]+counts_by_line[y,b])
    # Row-specific choices create many distinct long-interval OR graphs.
    # The exact residency constraints already imply every such cut; shorter
    # redundant cuts reduce presolve cost without relaxing cache capacity.
    cut_span=8 if row_word_masks else 32
    for begin in range(first,last):
        union={}
        for end in range(begin,min(last,begin+cut_span)+1):
            for c,rows in color_rows.items():
                if end in rows:union.setdefault(c,set()).update((i,end)for i in rows[end])
            if end==begin:continue
            for b in range(8):
                present=[]
                for c,indices in union.items():
                    options=list({selected(i,c,y,b).index:selected(i,c,y,b)for i,y in sorted(indices)if b in domains[i]}.values())
                    if not options:continue
                    if len(options)==1:present.append(options[0]);continue
                    signature=b,tuple(v.index for v in options)
                    if signature not in aliases:
                        alias=model.new_bool_var(f'intervalAlias{len(aliases)}');model.add_max_equality(alias,options);aliases[signature]=alias
                    present.append(aliases[signature])
                model.add(prefixes[end,b]-prefixes[begin,b]>=sum(present)-15);interval_cuts+=1
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False;solver.parameters.stop_after_first_solution=True
    if search_strategy in('sat','sat-repair'):
        solver.parameters.linearization_level=0
        solver.parameters.subsolvers.append('no_lp')
        solver.parameters.num_full_subsolvers=1
    if search_strategy=='sat-repair':
        solver.parameters.repair_hint=True;solver.parameters.hint_conflict_limit=50000
    if search_strategy=='lns':solver.parameters.use_lns_only=True
    solver.parameters.log_search_progress=True;solver.parameters.log_to_stdout=False
    log=deque(maxlen=32);log_lines=0
    def capture(message):
        nonlocal log_lines
        for line in message.splitlines():log_lines+=1;log.append(line[:512])
    solver.log_callback=capture
    status=solver.solve(model)
    report=dict(schema='BYOR_JOINT_FIXED_PIECE_BANK_CACHE_V1',status='BOUNDED_FIXED_PIECE_BANK_CACHE_NO_CANDIDATE',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        variables=len(model.proto.variables),constraints=len(model.proto.constraints),branches=solver.num_branches,conflicts=solver.num_conflicts,pieces=len(pieces),write_budget=write_budget,window=window,lookahead=lookahead,search_strategy=search_strategy,
        bounded_solver_log=list(log),solver_log_lines=log_lines,
        validated_assignment_hint_used=assignment_hint is not None,validated_bank_choice_hints=len(validated_hints),bank_choice_hints_are_soft=True,
        compulsory_bank_interval_cuts=interval_cuts,interval_word_alias_variables=len(aliases),redundant_interval_cut_span=cut_span,
        piece_geometry_and_encoding_class_fixed=not allow_word_masks,source_rectangles_and_encoding_classes_fixed=True,
        source_pixel_exact_word_masks_allowed=allow_word_masks,maximum_masks_per_piece=maximum_masks_per_piece if allow_word_masks else 1,
        word_bank_selection_scope='piece row'if row_word_masks else'piece word'if allow_word_masks else'whole piece',fixed_bank_per_compiled_oam_entry=True,
        interchangeable_bank_first_piece_order=interchangeable,
        maximum_oam=maximum_oam,maximum_sprites=maximum_sprites,maximum_tiles=maximum_tiles,
        geometry_reservation=reservation,reservation_palette_and_layer_demand_included=False,
        full_padded_oam_lifetimes_counted=True,oam_y_wrap_counted=True,fully_offscreen_tile_slivers_skipped=True,
        word_bank_copies_allowed=True,per_bank_word_aliases_counted_once=True,physical_endpoint_slots_relaxed=True,
        physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    expanded=[];assignment=[]
    for i,p in enumerate(pieces):
        for b in domains[i]:
            rs={y:[c for c in cs if solver.value(selected(i,c,y,b))]for y,cs in p['rows'].items()}
            if any(rs.values()):expanded.append(dict(p,source_piece=i,rows=rs));assignment.append(b)
    search=dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=assignment,pixel_word_identities_replayed=True)
    frame=rebuild_schedule(source,search,lookahead)
    combined=dict(oam_entries=len(frame['pieces'])+reservation['oam_entries'],
        peak_sprites=max(sum(active_on_line(p,y)for p in frame['pieces'])+reservation['sprites_per_line'][y]for y in range(height)),
        peak_tile_slivers=max(sum(tile_slivers(p)for p in frame['pieces']if active_on_line(p,y))+reservation['tile_slivers_per_line'][y]for y in range(height)))
    if combined['oam_entries']>maximum_oam or combined['peak_sprites']>maximum_sprites or combined['peak_tile_slivers']>maximum_tiles:raise AssertionError('PIECE_BANK_CACHE_RESERVED_GEOMETRY_REPLAY')
    report['combined_reserved_geometry']=combined
    rows={y:{b:set()for b in range(8)}for y in range(first,last+1)}
    for(c,b,y),v in resident.items():
        if solver.value(v):rows[y][b].add(c)
    report.update(status='FIXED_PIECE_BANK_CACHE_AND_OPERAND_IDENTITIES_PROVEN',compiled_oam_entries=len(expanded),changed_piece_banks=sum(pieces[p['source_piece']]['bank']!=b for p,b in zip(expanded,assignment)))
    result=compile_cache_rows(frame,rows,lookahead,write_budget,window,report,'piece_bank_cache')
    result.update(geometry_reservation=reservation,combined_reserved_geometry=combined,reservation_palette_and_layer_demand_included=False)
    return result


def main():
    import argparse,hashlib,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--time-limit',type=float,default=45);parser.add_argument('--write-budget',type=int,default=21)
    parser.add_argument('--window',type=int,default=337);parser.add_argument('--lookahead',type=int,default=55)
    parser.add_argument('--search-strategy',choices=('portfolio','sat','sat-repair','lns'),default='portfolio')
    parser.add_argument('--allow-word-masks',action='store_true');parser.add_argument('--maximum-masks-per-piece',type=int,default=2)
    parser.add_argument('--assignment-hint',type=Path)
    parser.add_argument('--row-word-masks',action='store_true',help='Allow equal words on different rows to use separate source-pixel masks; each compiled OAM entry still has one fixed bank.')
    parser.add_argument('--maximum-oam',type=int,default=128);parser.add_argument('--maximum-sprites',type=int,default=32);parser.add_argument('--maximum-tiles',type=int,default=34)
    parser.add_argument('--geometry-reservation',type=Path,help='Override the source input reservation; geometry only, not actor palettes or layers.')
    args=parser.parse_args();input_bytes=args.schedule.read_bytes();source=json.loads(input_bytes.decode('utf-8'))
    result=optimize(source,args.time_limit,args.write_budget,args.window,args.lookahead,args.search_strategy,args.allow_word_masks,args.maximum_masks_per_piece,args.maximum_oam,args.maximum_sprites,args.maximum_tiles,args.row_word_masks,json.loads(args.assignment_hint.read_text(encoding='utf-8'))if args.assignment_hint else None,json.loads(args.geometry_reservation.read_text(encoding='utf-8'))if args.geometry_reservation else None)
    result.update(source_input_sha256=hashlib.sha256(input_bytes).hexdigest(),source_input_path=str(args.schedule),
        source_rgb555_sha256=source.get('source_rgb555_sha256'),source_pak_sha256=source.get('source_pak_sha256'))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');report=result.get('piece_bank_cache',result)
    print(json.dumps({k:v for k,v in report.items()if k not in('geometry_reservation','bounded_solver_log')}))


if __name__=='__main__':main()
