"""Joint exact-context pixel encoding, fixed OAM masks and slot residency MILP.

An incumbent is replayed independently. No incumbent is a bounded solver limit,
never universal hardware infeasibility. Native BG/OBJ math routing is unproven.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from compiler import Source
from source_scene_bg import compose_rgb8
from source_scene_obj_raster import prepare
from source_bg_feasibility import rgb555
from source_scene_obj_math import residual, add_rgb555, split_interval_bound
from raster_palette import pieces_for_grid


def probe(source, stage, scene, size=16, write_budget=20, lookahead=16, time_limit=45, relaxed=False, pool_residency=None, clip_horizontal=False, feasibility_only=False, bank_symmetry=False, early_write_budget=None, late_start=75, saturated_reuse=False, pool_only=False, integer_pool_budget=None, align_visible_bounds=False, solver_backend='highs', pin_pool_intervals=False, prepared_dma_window=None):
    if solver_backend not in ('highs','cp-sat') or (relaxed and solver_backend!='highs'):raise ValueError('JOINT_SOLVER_BACKEND')
    if size not in (8,16,32,'mixed') or write_budget<0 or lookahead<0:
        raise ValueError('JOINT_SOLVER_DOMAIN')
    if pin_pool_intervals and not pool_residency:raise ValueError('JOINT_INTERVAL_PIN_REQUIRES_POOL')
    if prepared_dma_window is not None:
        if prepared_dma_window<1:raise ValueError('JOINT_DMA_WINDOW_DOMAIN')
        if bank_symmetry:raise ValueError('JOINT_DMA_BANK_SYMMETRY_UNSAFE')
    if early_write_budget is not None and (early_write_budget < 0 or not 1 <= late_start < 224):
        raise ValueError('JOINT_ROW_BUDGET_DOMAIN')
    def line_budget(y):return early_write_budget if early_write_budget is not None and y < late_start else write_budget
    actors, metadata, expected = prepare(source, stage, scene)
    pool=set();pool_first=0
    if pool_residency:
        if pool_residency['metadata']!=metadata or pool_residency['status']!='POOLED_INTEGER_RESIDENCY_CANDIDATE':raise ValueError('JOINT_POOL_CONTEXT_IDENTITY')
        pool={(e['kind'],e['color'],e['line'])for e in pool_residency['fractional_residency']if e['value']>.5}
        pool_first=min(y for kind,c,y in pool)
    def allowed(bank,color,y):return not pool_residency or (int(bank>=4),color,max(y,pool_first))in pool
    bg, _ = compose_rgb8(source, stage, dict(scene, actors=[])); bg = rgb555(bg)
    height = expected.shape[0]; pieces = []; atoms = []
    def slivers(piece):
        width=piece['width']
        if not clip_horizontal:return width//8
        x=piece['x']
        if x==-256:return width//8
        return sum(x+column*8+8>0 and x+column*8<256 for column in range(width//8))
    for actor_index, actor in enumerate(actors):
        base_size=32 if size=='mixed'else size
        surface=actor['pixels'];origin_x=origin_y=0
        if align_visible_bounds:
            ys,xs=np.where(surface>=0)
            if not len(xs):continue
            origin_x,origin_y=int(xs.min()),int(ys.min())
            surface=surface[origin_y:int(ys.max())+1,origin_x:int(xs.max())+1]
        for piece in pieces_for_grid(surface, (base_size, base_size)):
            piece['x']+=origin_x;piece['y']+=origin_y
            piece['rows']={y+origin_y:colors for y,colors in piece['rows'].items()}
            i = len(pieces); x0, y0 = piece['x'], piece['y']
            piece.update(actor=actor_index, local_x=x0, local_y=y0, x=x0+actor['left'], y=y0+actor['top'])
            pieces.append(piece)
            blocks=[(i,piece)]
            if size=='mixed':
                blocks=[]
                for child in pieces_for_grid(actor['pixels'][y0:y0+32,x0:x0+32],(8,8)):
                    cx,cy=x0+child['x'],y0+child['y']
                    child.update(actor=actor_index,local_x=cx,local_y=cy,x=cx+actor['left'],y=cy+actor['top'],rows={yy+y0:colors for yy,colors in child['rows'].items()})
                    index=len(pieces);pieces.append(child);blocks.append((index,child))
            for block_index,block in blocks:
             for ly in block['rows']:
                grouped = {}
                for lx in range(block['local_x'], min(block['local_x']+block['width'], actor['pixels'].shape[1])):
                    output = int(actor['pixels'][ly, lx])
                    if output < 0:
                        continue
                    y, x = ly+actor['top'], lx+actor['left']
                    value = residual(output, int(bg[y, x]))
                    grouped.setdefault((output, value), []).append((y, x))
                for (output, value), pixels in grouped.items():
                    atoms.append(dict(piece=block_index,options=[i,block_index]if size=='mixed'else[i],line=ly+actor['top'], output=output, residual=value, pixels=pixels))
    residual_corpus=sorted({a['residual'] for a in atoms if a['residual'] is not None})
    alternative_cache={}
    for atom in atoms:
        values=[] if atom['residual'] is None else [atom['residual']]
        if saturated_reuse and values:
            y,x=atom['pixels'][0];background=int(bg[y,x]);key=(atom['output'],background)
            if key not in alternative_cache:
                alternative_cache[key]=[c for c in residual_corpus if add_rgb555(c,background)==atom['output']]
            values=alternative_cache[key]
        atom['residual_options']=values
    if pool_only:
        from raster_palette_cover_liveness import lower_bound
        rows=[set() for _ in range(height)]
        for atom in atoms:rows[atom['line']].add((atom['output'],tuple(atom['residual_options'])))
        result=lower_bound(rows,time_limit=time_limit,include_solution=True,integer_budget=integer_pool_budget)
        result.update(metadata=metadata,saturated_reuse=saturated_reuse,no_color_reduction=True,native_presentation_proven=False,
                      source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest())
        return result
    variable_count = 0
    def allocate():
        nonlocal variable_count
        result = variable_count; variable_count += 1; return result
    masks = {(i,b):allocate() for i in range(len(pieces)) for b in range(8)}
    choices = {}; uses = {}
    for i, atom in enumerate(atoms):
        for bank in range(8):
            colors=[atom['output']] if bank<4 else atom['residual_options']
            for color in colors:
                if not allowed(bank,color,atom['line']):continue
                for piece_index in atom['options']:choices[i,piece_index,bank,color] = allocate()
                uses.setdefault((bank,color),set()).add(atom['line'])
    def residency_lines(lines):
        if pool_residency:return [0]+list(range(pool_first,max(lines)+1))if pool_first else list(range(max(lines)+1))
        lower=max(0,min(lines)-lookahead)
        return ([0] if lower else [])+list(range(lower,max(lines)+1))
    resident = {(b,c,y):allocate() for (b,c), lines in sorted(uses.items()) for y in residency_lines(lines)if allowed(b,c,y)}
    writes = {key:allocate() for key in resident if key[2] > 0}
    peak = allocate() if relaxed else None
    rr=[];cc=[];vv=[];lo=[];hi=[]
    def constraint(items, lower, upper):
        row = len(lo)
        for variable, value in items:
            rr.append(row);cc.append(variable);vv.append(value)
        lo.append(lower);hi.append(upper)
    atom_choices={};mask_choices={key:[] for key in masks}
    for (i,piece_index,bank,color),variable in choices.items():
        atom_choices.setdefault(i,[]).append((piece_index,bank,color,variable))
        mask_choices[piece_index,bank].append(variable)
    mandatory={};forced_colors={}
    for i,atom in enumerate(atoms):
        options=atom_choices.get(i,[])
        constraint([(v,1)for p,b,c,v in options],1,1)
        eligible_pieces={p for p,b,c,v in options};kinds={int(b>=4)for p,b,c,v in options}
        if len(eligible_pieces)==1 and len(kinds)==1:
            p=next(iter(eligible_pieces));kind=next(iter(kinds));key=p,kind
            mandatory[key]=max(mandatory.get(key,0),1)
            colors={c for pp,b,c,v in options}
            if len(colors)==1:forced_colors.setdefault((p,kind,atom['line']),set()).update(colors)
        for piece_index,bank,color,variable in options:
            constraint([(variable,1),(masks[piece_index,bank],-1)],-np.inf,0)
            constraint([(variable,1),(resident[bank,color,atom['line']],-1)],-np.inf,0)
    # A selected OAM mask must own at least one opaque source pixel. Otherwise
    # feasibility search can branch over unused sprites which only consume
    # hardware capacity. Removing those masks preserves every valid rendering.
    for key,variables in mask_choices.items():
        constraint([(masks[key],1)]+[(v,-1)for v in variables],-np.inf,0)
    for (p,kind,y),colors in forced_colors.items():
        mandatory[p,kind]=max(mandatory[p,kind],(len(colors)+14)//15)
    for (p,kind),count in mandatory.items():
        constraint([(masks[p,b],1)for b in range(4*kind,4*kind+4)],count,np.inf)
    mandatory_geometry=dict(oam_entries=sum(mandatory.values()),
        peak_sprites=max((sum(n for (i,k),n in mandatory.items()if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height'])for y in range(height)),default=0),
        peak_tile_slivers=max((sum(n*slivers(pieces[i])for (i,k),n in mandatory.items()if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height'])for y in range(height)),default=0))
    constraint([(v,1) for v in masks.values()],0,128)
    if bank_symmetry:
        # Canonicalize interchangeable bank labels by first piece using each bank.
        # At one piece, simultaneous first uses may retain symmetry, but no valid
        # schedule is lost: order banks by their first active piece.
        for first_bank in (0,4):
            for bank in range(first_bank+1,first_bank+4):
                for i in range(len(pieces)):
                    constraint([(masks[i,bank],1)]+[(masks[j,bank-1],-1) for j in range(i+1)],-np.inf,0)
    for y in range(height):
        active = [(i,b) for i,p in enumerate(pieces) if p['y'] <= y < p['y']+p['height'] for b in range(8)]
        constraint([(masks[key],1) for key in active],0,32)
        constraint([(masks[key],slivers(pieces[key[0]])) for key in active],0,34)
    bank_lines = {}; write_lines = {}
    for key, variable in resident.items():
        b,c,y = key
        bank_lines.setdefault((b,y),[]).append(variable)
        if y:
            items=[(variable,1),(writes[key],-1)]
            previous=0 if pool_residency and y==pool_first else y-1
            if not pool_residency and (b,c,previous) not in resident and (b,c,0) in resident:previous=0
            if (b,c,previous) in resident:
                items.append((resident[b,c,previous],-1))
            constraint(items,-np.inf,0);write_lines.setdefault(y,[]).append(writes[key])
    interval_groups=0
    if pin_pool_intervals:
        # Restricted constructive family: every represented pool residency is
        # retained in one bank for its full interval. No claim of completeness.
        color_lines={}
        for b,c,y in resident:color_lines.setdefault((int(b>=4),c),set()).add(y)
        for (kind,color),lines_for_color in color_lines.items():
            groups=[]
            for y in sorted(lines_for_color):
                if groups and (y==groups[-1][-1]+1 or groups[-1][-1]==0 and y==pool_first):groups[-1].append(y)
                else:groups.append([y])
            for group in groups:
                initial=[]
                for bank in range(4*kind,4*kind+4):
                    first=(bank,color,group[0])
                    if first not in resident:continue
                    anchor=resident[first];initial.append((anchor,1))
                    for y in group[1:]:
                        if (bank,color,y) in resident:constraint([(resident[bank,color,y],1),(anchor,-1)],0,0)
                constraint(initial,1,1);interval_groups+=1
    for variables in bank_lines.values():
        constraint([(v,1) for v in variables],0,15)
    for y,variables in write_lines.items():
        constraint([(v,1) for v in variables],0,line_budget(y))
        if relaxed:constraint([(v,1) for v in variables]+[(peak,-1)],-np.inf,0)
    if prepared_dma_window is not None:
        by_bank_line={}
        for (b,c,y),v in writes.items():by_bank_line.setdefault((b,y),[]).append(v)
        for y,variables in write_lines.items():
            active={b:allocate()for b in range(8)};bridges={b:allocate()for b in range(7)}
            for b,a in active.items():
                values=by_bank_line.get((b,y),[])
                for v in values:constraint([(v,1),(a,-1)],-np.inf,0)
                constraint([(a,1)]+[(v,-1)for v in values],-np.inf,0)
            for b,v in bridges.items():
                for a in (active[b],active[b+1]):constraint([(v,1),(a,-1)],-np.inf,0)
            # Favorable necessary bound: grant every adjacent bank bridge
            # without charging unused intermediate slots. Each bridge can
            # save at most eight clocks (zero-word 16, range switch 24).
            # CGRAM commits only the high byte. Grant one low-byte preload
            # before the window, reducing the necessary commit span by eight.
            constraint([(v,16)for v in variables]+[(v,24)for v in active.values()]+[(v,-8)for v in bridges.values()],-np.inf,prepared_dma_window+39)
    objective=np.zeros(variable_count);integrality=np.ones(variable_count)
    for variable in masks.values():objective[variable]=1
    for variable in writes.values():objective[variable]=.001;integrality[variable]=0
    upper=np.ones(variable_count)
    if feasibility_only:objective[:]=0
    if relaxed:
        integrality[:]=0;objective[:]=0;objective[peak]=1;upper[peak]=write_budget
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(lo),variable_count)).tocsc()
    if solver_backend=='cp-sat':
        from raster_boolean_solver import solve
        result=solve(matrix,lo,hi,objective,time_limit)
    else:
        result=milp(objective,integrality=integrality,bounds=Bounds(0,upper),constraints=LinearConstraint(matrix,lo,hi),options={'time_limit':time_limit,'mip_rel_gap':.05})
    report=dict(schema='BYOR_JOINT_EXACT_CONTEXT_OBJ_MILP_V1',status='BOUNDED_JOINT_SOLVER_NO_CANDIDATE',
                metadata=metadata,geometry_size=size,write_budget=write_budget,lookahead_lines=lookahead,
                solver=dict(status=int(result.status),message=result.message,variables=variable_count,constraints=len(lo),mip_nodes=int(result.mip_node_count) if getattr(result,'mip_node_count',None) is not None else None,mip_gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None and np.isfinite(result.mip_gap) else None),
                no_color_reduction=True,universal_raster_rejected=False,native_presentation_proven=False,
                pooled_residency_pinned=bool(pool_residency),
                full_pool_intervals_retained=pin_pool_intervals,pool_residency_intervals=interval_groups,
                feasibility_only=feasibility_only,bank_symmetry=bank_symmetry,bank_symmetry_policy='first visible piece' if bank_symmetry else None,early_write_budget=early_write_budget,late_start=late_start,saturated_reuse=saturated_reuse,align_visible_bounds=align_visible_bounds,
                additive_alternative_count=sum(len(a["residual_options"]) for a in atoms),
                horizontal_clip_limit_counted=clip_horizontal,
                mandatory_geometry_lower_bound=mandatory_geometry,
                prepared_dma_window_master_clocks=prepared_dma_window,
                prepared_dma_window_is_optimistic_necessary_only=prepared_dma_window is not None,
                source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
                scope='Explicit pose. Exact opaque/additive pixel alternatives and fixed OAM color masks on one legal grid. No native layer routing, source reachability or hardware bandwidth admission.')
    report['solver']['backend']=solver_backend
    if hasattr(result,'boolean_stats'):report['solver']['boolean_stats']=result.boolean_stats
    if hasattr(result,'bounded_log'):report['bounded_solver_log']=result.bounded_log
    if result.x is None:
        return report
    if relaxed:
        values=matrix @ result.x
        violation=max(float(np.max(np.maximum(np.array(lo)-values,0))),float(np.max(np.maximum(values-np.array(hi),0))),float(np.max(np.maximum(-result.x,0))),float(np.max(np.maximum(result.x-upper,0))))
        if violation>1e-6:raise AssertionError('JOINT_LP_PRIMAL_RESIDUAL_FAULT')
        report.update(status='FRACTIONAL_RELAXATION_DOES_NOT_PROVE_SCHEDULE',fractional_peak_writes=float(result.x[peak]),optimal_relaxation=result.status==0,maximum_primal_violation=violation,scope='Fractional necessary relaxation of the specified grid/lookahead. Pixel ownership, OAM and residency may be fractional; no hardware schedule is proven.')
        return report
    chosen = {}
    demand=[{b:set() for b in range(8)} for _ in range(height)]
    expanded={}
    for i, atom in enumerate(atoms):
        banks=[(p,b,c)for p,b,c,v in atom_choices.get(i,[])if result.x[v]>.5]
        if len(banks)!=1:
            raise AssertionError('JOINT_ATOM_BANK_FAULT')
        piece_index,b,c=banks[0];chosen[i]=(piece_index,b,c)
        demand[atom['line']][b].add(c)
        expanded.setdefault((piece_index,b),{}).setdefault(atom['line'],set()).add(c)
    selected=[dict(pieces[i],rows={y:sorted(colors) for y,colors in rows.items()},bank=b) for (i,b),rows in sorted(expanded.items())]
    if set(expanded)!={key for key,variable in masks.items() if result.x[variable]>.5}:
        raise AssertionError('JOINT_OAM_MASK_OWNERSHIP_FAULT')
    geometry=dict(oam_entries=len(selected),peak_sprites=max(sum(p['y']<=y<p['y']+p['height'] for p in selected) for y in range(height)),peak_tile_slivers=max(sum(slivers(p) for p in selected if p['y']<=y<p['y']+p['height']) for y in range(height)))
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:
        raise AssertionError('JOINT_GEOMETRY_LIMIT_FAULT')
    wanted=[{b:set() for b in range(8)} for _ in range(height)]
    for (b,c,y),variable in resident.items():
        if result.x[variable]>.5:wanted[y][b].add(c)
    slots={b:[None]*15 for b in range(8)};states=[];trace=[]
    for y in range(height):
        before={b:list(values) for b,values in slots.items()};events=[]
        for b in range(8):
            if len(wanted[y][b])>15 or not demand[y][b] <= wanted[y][b]:
                raise AssertionError('JOINT_RESIDENCY_FAULT')
            for color in sorted(wanted[y][b]-set(slots[b])):
                at=next(i for i,c in enumerate(slots[b]) if c not in wanted[y][b])
                events.append(dict(bank=b,slot=at+1,old=slots[b][at],color=color,kind='required' if color in demand[y][b] else 'prefetch'));slots[b][at]=color
        if y and len(events)>line_budget(y):raise AssertionError('JOINT_WRITE_LIMIT_FAULT')
        if y and events and prepared_dma_window is not None:
            from raster_cgram_packets import optimistic_dma_span
            if optimistic_dma_span(events)['first_to_last_cgram_commit_master_clocks']>=prepared_dma_window:
                raise AssertionError('JOINT_DMA_SPAN_LOWER_BOUND_FAULT')
        states.append({b:list(values) for b,values in slots.items()})
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in values if c is not None and c in slots[b]] for b,values in before.items()},evicted=[e['old'] for e in events if e['old'] is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank'] for e in events})))
    replay=bg.copy();indices=np.zeros((height,256),dtype=np.uint8)
    piece_ids={key:i for i,key in enumerate(sorted(expanded))}
    piece_pixels=[np.zeros((p['height'],p['width']),dtype=np.uint8)for p in selected]
    for i,atom in enumerate(atoms):
        piece_index,b,color=chosen[i];slot=states[atom['line']][b].index(color)+1
        for y,x in atom['pixels']:
            indices[y,x]=128+b*16+slot
            index=piece_ids[piece_index,b];p=selected[index]
            piece_pixels[index][y-p['y'],x-p['x']]=slot
    ownership=np.zeros((height,256),dtype=np.uint8)
    for piece,pixels in zip(selected,piece_pixels):
        for ly,lx in zip(*np.where(pixels!=0)):
            y,x=int(ly+piece['y']),int(lx+piece['x']);b=piece['bank']
            if ownership[y,x]:raise AssertionError('JOINT_PIXEL_MASK_OVERLAP')
            ownership[y,x]=1;color=states[y][b][int(pixels[ly,lx])-1]
            replay[y,x]=color if b<4 else add_rgb555(color,int(bg[y,x]))
    if not np.array_equal(replay,rgb555(expected)):raise AssertionError('JOINT_SOURCE_PIXEL_IDENTITY_FAULT')
    groups=[[demand[y][b] for y in range(height)] for b in range(8)]
    report.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',geometry=geometry,pieces=selected,trace=trace,
                  compiled_pixel_identity_verified=True,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
                  piece_pixel_masks=[dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(pixels.flatten()[::2]|(pixels.flatten()[1::2]<<4)).tobytes().hex())for p,pixels in zip(selected,piece_pixels)],
                  peak_scheduled_writes=max(row['colors_written'] for row in trace[1:]),fixed_bank_interval_bound=split_interval_bound(groups,15))
    counts=[row['colors_written']for row in trace[1:]]
    report.update(peak_cgram_data_bytes=2*max(counts,default=0),average_writes=float(np.mean(counts)),worst_scanline=1+int(np.argmax(counts)),
                  compiled_schedule_sha256=hashlib.sha256(json.dumps(dict(pieces=selected,pixel_masks=report['piece_pixel_masks'],trace=trace),sort_keys=True).encode()).hexdigest(),
                  schedule_latency_requirement='All updates for line y must finish before that line consumes OBJ colors; initial slots restored during VBlank. No native timing admission.')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--size',choices=('8','16','32','mixed'),default='16')
    p.add_argument('--write-budget',type=int,default=20);p.add_argument('--time-limit',type=int,default=45)
    p.add_argument('--relaxed',action='store_true')
    p.add_argument('--pool-residency',type=Path)
    p.add_argument('--pin-pool-intervals',action='store_true')
    p.add_argument('--clip-horizontal',action='store_true')
    p.add_argument('--feasibility-only',action='store_true');p.add_argument('--bank-symmetry',action='store_true')
    p.add_argument('--saturated-reuse',action='store_true')
    p.add_argument('--solver-backend',choices=('highs','cp-sat'),default='highs')
    p.add_argument('--align-visible-bounds',action='store_true')
    p.add_argument('--pool-only',action='store_true');p.add_argument('--integer-pool-budget',type=int)
    p.add_argument('--early-write-budget',type=int);p.add_argument('--late-start',type=int,default=75)
    p.add_argument('--prepared-dma-window',type=int)
    a=p.parse_args();r=probe(Source(a.source),a.stage,json.loads(a.scene.read_text()),'mixed'if a.size=='mixed'else int(a.size),a.write_budget,time_limit=a.time_limit,relaxed=a.relaxed,pool_residency=json.loads(a.pool_residency.read_text())if a.pool_residency else None,clip_horizontal=a.clip_horizontal,feasibility_only=a.feasibility_only,bank_symmetry=a.bank_symmetry,early_write_budget=a.early_write_budget,late_start=a.late_start,saturated_reuse=a.saturated_reuse,pool_only=a.pool_only,integer_pool_budget=a.integer_pool_budget,align_visible_bounds=a.align_visible_bounds,solver_backend=a.solver_backend,pin_pool_intervals=a.pin_pool_intervals,prepared_dma_window=a.prepared_dma_window)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k in ('status','solver','geometry','peak_scheduled_writes','peak_write_lower_bound','candidate_peak_writes')}))


if __name__=='__main__':main()
