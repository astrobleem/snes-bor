"""Joint fixed OAM piece banks and alias-aware palette cache liveness.

Repeated RGB555 words may appear in multiple banks. A bank counts each word
once, even when several objects demand it. Source rectangles and encoding
classes remain fixed; transfer endpoints and physical slots remain relaxed.
"""
import copy
import numpy as np
from raster_slot_greedy import demand,bank_groups
from raster_global_bank_classes import rebuild_schedule
from raster_bank_residency import constrain_flow
from raster_word_cache_repair import compile_cache_rows


def optimize(source,time_limit=45,write_budget=21,window=337,lookahead=55,search_strategy='portfolio',allow_word_masks=False,maximum_masks_per_piece=2,maximum_oam=128,maximum_sprites=32,maximum_tiles=34):
    from ortools.sat.python import cp_model
    if time_limit<=0 or not 0<=write_budget<=120 or window<1 or lookahead<0:raise ValueError('PIECE_BANK_CACHE_DOMAIN')
    if search_strategy not in('portfolio','sat','lns'):raise ValueError('PIECE_BANK_CACHE_SEARCH_STRATEGY')
    if not 1<=maximum_masks_per_piece<=8 or not 1<=maximum_oam<=128 or not 1<=maximum_sprites<=32 or not 1<=maximum_tiles<=34:raise ValueError('PIECE_BANK_CACHE_GEOMETRY_DOMAIN')
    required,_,images=demand(source);pieces=copy.deepcopy(source['pieces']);groups=bank_groups(source);owners={};row_owners={};domains={}
    for i,(p,image)in enumerate(zip(pieces,images)):
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if np.any(row>=0)}
        domains[i]=tuple(b for b in next(g for g in groups if p['bank']in g)if b in p.get('allowed_banks',range(8)))
        if not domains[i]:raise ValueError('PIECE_BANK_CACHE_BANK_ELIGIBILITY')
        for y,cs in p['rows'].items():
            for c in cs:owners.setdefault(c,set()).add(i);row_owners.setdefault((y,c),set()).add(i)
    active=sorted({y for y,c in row_owners})
    if not active:raise ValueError('PIECE_BANK_CACHE_EMPTY')
    first,last=min(active),max(active);model=cp_model.CpModel();selection={};resident={};writes={};by_line={};write_lines={}
    color_rows={}
    for(y,c),indices in row_owners.items():color_rows.setdefault(c,{})[y]=indices
    masks={}
    for i,p in enumerate(pieces):
        colors=sorted({c for cs in p['rows'].values()for c in cs})
        for key in ((i,c)for c in colors)if allow_word_masks else (i,):
            selection[key]={b:model.new_bool_var(f'piece{key}_{b}')for b in domains[i]};model.add_exactly_one(list(selection[key].values()))
            for b,v in selection[key].items():model.add_hint(v,int(b==p['bank']))
        for b in domains[i]:
            if allow_word_masks:
                mask=model.new_bool_var(f'mask{i}_{b}')
                if colors:model.add_max_equality(mask,[selection[i,c][b]for c in colors])
                else:model.add(mask==0)
                masks[i,b]=mask
            else:masks[i,b]=selection[i][b]
        if allow_word_masks:model.add(sum(masks[i,b]for b in domains[i])<=maximum_masks_per_piece)
    def selected(i,c,b):return selection[(i,c)if allow_word_masks else i][b]
    model.add(sum(masks.values())<=maximum_oam)
    for y in range(first,last+1):
        live=[(i,v)for(i,b),v in masks.items()if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height']]
        model.add(sum(v for i,v in live)<=maximum_sprites);model.add(sum(v*(pieces[i]['width']//8)for i,v in live)<=maximum_tiles)
    hints=[];state={b:[None]*15 for b in range(8)}
    for row in source['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        hints.append({b:set(c for c in cs if c is not None)for b,cs in state.items()})
    for c,indices in owners.items():
        last_use=max(color_rows[c])
        for b in sorted({b for i in indices for b in domains[i]}):
            options=[selected(i,c,b)for i in indices if b in domains[i]]
            ever=model.new_bool_var(f'ever{c}_{b}');model.add_max_equality(ever,options)
            for y in range(first,last_use+1):
                r=model.new_bool_var(f'r{c}_{b}_{y}');resident[c,b,y]=r;by_line.setdefault((y,b),[]).append(r);model.add(r<=ever)
                for i in row_owners.get((y,c),[]):
                    if b in domains[i]:model.add(r>=selected(i,c,b))
                model.add_hint(r,int(c in hints[y][b]))
                if y==first:continue
                previous=resident[c,b,y-1];future={i for yy,indices_on_row in color_rows[c].items()if y<=yy<=y+lookahead for i in indices_on_row if b in domains[i]}
                if not future:model.add(r<=previous);continue
                w=model.new_bool_var(f'w{c}_{b}_{y}');writes[c,b,y]=w;write_lines.setdefault((y,b),[]).append(w)
                model.add(w>=r-previous);model.add(w<=r);model.add(w+previous<=1);model.add(w<=sum(selected(i,c,b)for i in future))
                model.add_hint(w,int(c in hints[y][b]and c not in hints[y-1][b]))
    counts_by_line={}
    for y in range(first,last+1):
        for b in range(8):model.add(sum(by_line.get((y,b),[]))<=15)
        if y==first:continue
        counts=[];flags=[]
        for b in range(8):
            n=model.new_int_var(0,15,f'count{y}_{b}');model.add(n==sum(write_lines.get((y,b),[])));counts.append(n);counts_by_line[y,b]=n
            flag=model.new_bool_var(f'active{y}_{b}');model.add(n>=flag);model.add(n<=15*flag);flags.append(flag)
        model.add(sum(counts)<=write_budget);constrain_flow(model,counts,flags,window,f'pieceCache{y}')
    # Each bank can bring only fifteen distinct identities into an interval.
    # OR the participating objects before counting an identity, so shared words
    # never become spurious compulsory duplicate loads.
    prefixes={};aliases={};interval_cuts=0
    for b in range(8):
        prefixes[first,b]=model.new_constant(0)
        for y in range(first+1,last+1):
            prefix=model.new_int_var(0,15*(y-first),f'writePrefix{y}_{b}');prefixes[y,b]=prefix
            model.add(prefix==prefixes[y-1,b]+counts_by_line[y,b])
    for begin in range(first,last):
        union={}
        for end in range(begin,min(last,begin+32)+1):
            for c,rows in color_rows.items():
                if end in rows:union.setdefault(c,set()).update(rows[end])
            if end==begin:continue
            for b in range(8):
                present=[]
                for c,indices in union.items():
                    options=[selected(i,c,b)for i in sorted(indices)if b in domains[i]]
                    if not options:continue
                    if len(options)==1:present.append(options[0]);continue
                    signature=b,tuple(v.index for v in options)
                    if signature not in aliases:
                        alias=model.new_bool_var(f'intervalAlias{len(aliases)}');model.add_max_equality(alias,options);aliases[signature]=alias
                    present.append(aliases[signature])
                model.add(prefixes[end,b]-prefixes[begin,b]>=sum(present)-15);interval_cuts+=1
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False;solver.parameters.stop_after_first_solution=True
    if search_strategy=='sat':solver.parameters.linearization_level=0
    if search_strategy=='lns':solver.parameters.use_lns_only=True
    status=solver.solve(model)
    report=dict(schema='BYOR_JOINT_FIXED_PIECE_BANK_CACHE_V1',status='BOUNDED_FIXED_PIECE_BANK_CACHE_NO_CANDIDATE',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        variables=len(model.proto.variables),constraints=len(model.proto.constraints),branches=solver.num_branches,conflicts=solver.num_conflicts,pieces=len(pieces),write_budget=write_budget,window=window,lookahead=lookahead,search_strategy=search_strategy,
        compulsory_bank_interval_cuts=interval_cuts,interval_word_alias_variables=len(aliases),
        piece_geometry_and_encoding_class_fixed=not allow_word_masks,source_rectangles_and_encoding_classes_fixed=True,
        source_pixel_exact_word_masks_allowed=allow_word_masks,maximum_masks_per_piece=maximum_masks_per_piece if allow_word_masks else 1,
        maximum_oam=maximum_oam,maximum_sprites=maximum_sprites,maximum_tiles=maximum_tiles,
        word_bank_copies_allowed=True,per_bank_word_aliases_counted_once=True,physical_endpoint_slots_relaxed=True,
        physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    expanded=[];assignment=[]
    for i,p in enumerate(pieces):
        for b in domains[i]:
            rs={y:[c for c in cs if solver.value(selected(i,c,b))]for y,cs in p['rows'].items()}
            if any(rs.values()):expanded.append(dict(p,source_piece=i,rows=rs));assignment.append(b)
    search=dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=assignment,pixel_word_identities_replayed=True)
    frame=rebuild_schedule(source,search,lookahead)
    rows={y:{b:set()for b in range(8)}for y in range(first,last+1)}
    for(c,b,y),v in resident.items():
        if solver.value(v):rows[y][b].add(c)
    report.update(status='FIXED_PIECE_BANK_CACHE_AND_OPERAND_IDENTITIES_PROVEN',compiled_oam_entries=len(expanded),changed_piece_banks=sum(pieces[p['source_piece']]['bank']!=b for p,b in zip(expanded,assignment)))
    return compile_cache_rows(frame,rows,lookahead,write_budget,window,report,'piece_bank_cache')


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--time-limit',type=float,default=45);parser.add_argument('--write-budget',type=int,default=21)
    parser.add_argument('--window',type=int,default=337);parser.add_argument('--lookahead',type=int,default=55)
    parser.add_argument('--search-strategy',choices=('portfolio','sat','lns'),default='portfolio')
    parser.add_argument('--allow-word-masks',action='store_true');parser.add_argument('--maximum-masks-per-piece',type=int,default=2)
    parser.add_argument('--maximum-oam',type=int,default=128);parser.add_argument('--maximum-sprites',type=int,default=32);parser.add_argument('--maximum-tiles',type=int,default=34)
    args=parser.parse_args();result=optimize(json.loads(args.schedule.read_text()),args.time_limit,args.write_budget,args.window,args.lookahead,args.search_strategy,args.allow_word_masks,args.maximum_masks_per_piece,args.maximum_oam,args.maximum_sprites,args.maximum_tiles)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('piece_bank_cache',result)))


if __name__=='__main__':main()
