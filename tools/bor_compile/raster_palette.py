"""Offline fixed-OAM-bank feasibility and lossless scanline slot scheduling.

Geometry is an explicit input: a grid of legal SNES OBJ sizes, never a pool
of 120 interchangeable colors. MILP infeasibility applies only to that grid.
No native timing or alpha admission is implied by mathematical feasibility.
"""
from bisect import bisect_right
import hashlib
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


LEGAL_SIZES = ((8,8),(16,16),(32,32),(64,64),(16,32),(32,64))
OBJ_SIZE_PAIRS = (((8,8),(16,16)), ((8,8),(32,32)), ((8,8),(64,64)),
                  ((16,16),(32,32)), ((16,16),(64,64)), ((32,32),(64,64)),
                  ((16,32),(32,64)), ((16,32),(32,32)))


def pieces_for_grid(pixels, size):
    """pixels uses -1 for transparency, including opaque RGB555 black correctly."""
    if tuple(size) not in LEGAL_SIZES:
        raise ValueError('ILLEGAL_OBJ_SIZE')
    h,w = pixels.shape
    pw,ph = size
    pieces=[]
    for y in range(0,h,ph):
        for x in range(0,w,pw):
            region=pixels[y:y+ph,x:x+pw]
            if np.any(region>=0):
                rows={y+r: sorted(set(map(int,row[row>=0]))) for r,row in enumerate(region)}
                pieces.append(dict(x=x,y=y,width=pw,height=ph,rows=rows))
    return pieces


def assign_banks(pieces, banks, time_limit=60):
    """Exact binary model: piece chooses one bank; row union <=15 per bank."""
    if not banks or any(b not in range(8) for b in banks):
        raise ValueError('INVALID_BANKS')
    pairs=sorted({(y,c) for p in pieces for y,cs in p['rows'].items() for c in cs})
    nb=len(banks); npieces=len(pieces)
    cv={(y,c,b):npieces*nb+i*nb+b for i,(y,c) in enumerate(pairs) for b in range(nb)}
    count=npieces*nb+len(cv)
    rr=[];cc=[];vv=[];lo=[];hi=[]
    def row(items,lower,upper):
        r=len(lo)
        for c,v in items: rr.append(r);cc.append(c);vv.append(v)
        lo.append(lower);hi.append(upper)
    for i,p in enumerate(pieces):
        row([(i*nb+b,1) for b in range(nb)],1,1)
        allowed = p.get('allowed_banks', banks)
        for b, bank in enumerate(banks):
            if bank not in allowed:
                row([(i*nb+b,1)],0,0)
        for y,cs in p['rows'].items():
            for c in cs:
                for b in range(nb): row([(i*nb+b,1),(cv[y,c,b],-1)],-np.inf,0)
    for y in sorted({y for y,c in pairs}):
        for b in range(nb): row([(cv[yy,c,b],1) for yy,c in pairs if yy==y],0,15)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(lo),count)).tocsc()
    result=milp(np.zeros(count),integrality=np.ones(count),bounds=Bounds(0,1),
        constraints=LinearConstraint(matrix,lo,hi),options={'time_limit':time_limit})
    if result.x is None:
        return dict(status='FIXED_GRID_INFEASIBLE' if result.status==2 else 'SOLVER_LIMIT',
                    solver_status=int(result.status),message=result.message)
    assignment=[banks[int(np.argmax(result.x[i*nb:(i+1)*nb]))] for i in range(npieces)]
    if any(bank not in p.get('allowed_banks', banks) for p, bank in zip(pieces, assignment)):
        raise AssertionError('INVALID_SOLVER_BANK_ELIGIBILITY')
    # Never accept a fractional/invalid incumbent as proof.
    for y in sorted({y for y,c in pairs}):
        for bank in banks:
            colors={c for i,p in enumerate(pieces) if assignment[i]==bank for c in p['rows'].get(y,[])}
            if len(colors)>15: raise AssertionError('INVALID_SOLVER_ASSIGNMENT')
    return dict(status='FIXED_BANK_ASSIGNMENT_PROVEN',assignment=assignment,
                solver_status=int(result.status),message=result.message)


def split_color_masks(pieces, banks, time_limit=60,global_color_banks=False,solver_backend='highs',maximum_frame_colors_per_bank=None,defer_oam_admission=False,residency_window_lines=None,defer_geometry_admission=False):
    """Allow multiple legal objects per cell, masking disjoint source pixels.

    Each output object still has one fixed bank. Color/row assignment is
    compiled into the tile pixels, never changed via OAM during a scanline.
    The optimization accounts for empty rows in a live object's rectangle.
    """
    if solver_backend not in('highs','cp-sat'):raise ValueError('MASK_SOLVER_BACKEND')
    if maximum_frame_colors_per_bank is not None and(not global_color_banks or not isinstance(maximum_frame_colors_per_bank,int)or maximum_frame_colors_per_bank<1):raise ValueError('MASK_FRAME_COLOR_LIMIT')
    if residency_window_lines is not None and(not global_color_banks or not isinstance(residency_window_lines,int)or residency_window_lines<1):raise ValueError('MASK_RESIDENCY_WINDOW_DOMAIN')
    nb=len(banks); n=len(pieces)
    pairs=sorted({(y,c) for p in pieces for y,cs in p['rows'].items() for c in cs})
    if residency_window_lines is not None:
        windows=[(len({c for yy,c in pairs if y<=yy<y+residency_window_lines}),y)for y in sorted({y for y,c in pairs})]
        peak,first=max(windows,default=(0,0),key=lambda v:(v[0],-v[1]))
        if peak>15*nb:
            return dict(status='MASK_GRID_INFEASIBLE',solver_status=2,message='WINDOW_UNION_CAPACITY_LIMIT',
                        residency_window_lines=residency_window_lines,window_union_colors=peak,worst_window_first_scanline=first,
                        available_opaque_slots=15*nb,universal_raster_rejected=False)
    colors=sorted({c for y,c in pairs});color_ids={c:j for j,c in enumerate(colors)}
    cv={(y,c,b):n*nb+(color_ids[c]if global_color_banks else j)*nb+b for j,(y,c) in enumerate(pairs) for b in range(nb)}
    count=n*nb+(len(colors)if global_color_banks else len(pairs))*nb;rr=[];cc=[];vv=[];lo=[];hi=[]
    def row(items,lower,upper):
        r=len(lo)
        for c,v in items:rr.append(r);cc.append(c);vv.append(v)
        lo.append(lower);hi.append(upper)
    first={}
    for y,c in pairs:
        if global_color_banks and c in first:continue
        first[c]=y;row([(cv[y,c,b],1) for b in range(nb)],1,1)
    if global_color_banks:
        if maximum_frame_colors_per_bank is not None:
            for b in range(nb):row([(cv[y,c,b],1)for c,y in first.items()],0,maximum_frame_colors_per_bank)
    for i,p in enumerate(pieces):
        seen=set()
        for y,cs in p['rows'].items():
            for c in cs:
                for b in range(nb):
                    v=cv[y,c,b]
                    if v in seen:continue
                    seen.add(v);row([(v,1),(i*nb+b,-1)],-np.inf,0)
    if not defer_oam_admission and not defer_geometry_admission:row([(i,1) for i in range(n*nb)],0,128)
    for y in range(max(p['y']+p['height'] for p in pieces)):
        for b in range(nb):row([(cv[yy,c,b],1) for yy,c in pairs if yy==y],0,15)
        live=[(i*nb+b,1) for i,p in enumerate(pieces) if p['y']<=y<p['y']+p['height'] for b in range(nb)]
        if not defer_geometry_admission:
            row(live,0,32)
            row([(i*nb+b,(p['width']+7)//8) for i,p in enumerate(pieces) if p['y']<=y<p['y']+p['height'] for b in range(nb)],0,34)
    # Optional restricted search family: every rolling union fits one bank's
    # fifteen slots. This steers temporal assignment before slot allocation;
    # failure does not reject assignments outside this restriction.
    if residency_window_lines is not None:
        for y in sorted({y for y,c in pairs}):
            required={c for yy,c in pairs if y<=yy<y+residency_window_lines}
            for b in range(nb):row([(cv[first[c],c,b],1)for c in sorted(required)],0,15)
    objective=np.zeros(count);objective[:n*nb]=1
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(lo),count)).tocsc()
    if solver_backend=='cp-sat':
        from raster_boolean_solver import solve
        result=solve(matrix,lo,hi,objective,time_limit)
    else:result=milp(objective,integrality=np.ones(count),bounds=Bounds(0,1),
        constraints=LinearConstraint(matrix,lo,hi),options={'time_limit':time_limit,'mip_rel_gap':0.03})
    if result.x is None:
        return dict(status='MASK_GRID_INFEASIBLE' if result.status==2 else 'SOLVER_LIMIT',solver_status=int(result.status),message=result.message,residency_window_lines=residency_window_lines,universal_raster_rejected=False)
    expanded=[];assignment=[]
    for p in pieces:
        for b,bank in enumerate(banks):
            rows={y:[c for c in cs if result.x[cv[y,c,b]]>0.5] for y,cs in p['rows'].items()}
            if any(rows.values()):expanded.append(dict(p,rows=rows));assignment.append(bank)
    if residency_window_lines is not None:
        for y in sorted({y for y,c in pairs}):
            for bank in banks:
                colors={c for p,b in zip(expanded,assignment)if b==bank for yy,cs in p['rows'].items()if y<=yy<y+residency_window_lines for c in cs}
                if len(colors)>15:raise AssertionError('MASK_RESIDENCY_WINDOW_REPLAY')
    return dict(status='COLOR_MASK_FIXED_BANK_ASSIGNMENT_PROVEN',pieces=expanded,
                assignment=assignment,solver_status=int(result.status),message=result.message,
                objective=float(np.dot(objective,result.x)),lower_bound=float(result.mip_dual_bound)if getattr(result,'mip_dual_bound',None)is not None else None,
                global_color_banks=global_color_banks,solver_backend=solver_backend,maximum_frame_colors_per_bank=maximum_frame_colors_per_bank,
                residency_window_lines=residency_window_lines,
                oam_admission_deferred=defer_oam_admission or defer_geometry_admission,geometry_admission_deferred=defer_geometry_admission,hardware_oam_limit_verified=len(expanded)<=128)


def split_scene_color_masks(pieces, banks=tuple(range(8)), time_limit=60, adjacent_write_budget=None):
    """Piece-local color masks with shared row/bank capacity and eligibility.

    Unlike the simpler one-image model, equal colors on different actors may
    occupy different banks. This permits distinct alpha eligibility per piece.
    Infeasibility is confined to the supplied grid and legal size mode.
    """
    if not pieces:
        return dict(status='COLOR_MASK_FIXED_BANK_ASSIGNMENT_PROVEN', pieces=[], assignment=[])
    if not banks or len(set(banks)) != len(banks) or any(b not in range(8) for b in banks):
        raise ValueError('INVALID_BANKS')
    sizes = {(p['width'],p['height']) for p in pieces}
    if not any(sizes <= set(pair) for pair in OBJ_SIZE_PAIRS):
        raise ValueError('NO_SHARED_OBSEL_SIZE_MODE')
    nb = len(banks); n = len(pieces)
    atoms = [(i,y,c) for i,p in enumerate(pieces) for y,cs in p['rows'].items() for c in cs]
    local = {(i,y,c,b):n*nb+j*nb+b for j,(i,y,c) in enumerate(atoms) for b in range(nb)}
    pairs = sorted({(y,c) for i,y,c in atoms})
    start = n*nb+len(local)
    resident = {(y,c,b):start+j*nb+b for j,(y,c) in enumerate(pairs) for b in range(nb)}
    count = start+len(resident)
    adjacent = {}; excess = {}; adjacent_lines = {}
    if adjacent_write_budget is not None:
        if not isinstance(adjacent_write_budget,int) or adjacent_write_budget<0:
            raise ValueError('INVALID_ADJACENT_WRITE_BUDGET')
        height=max(p['y']+p['height'] for p in pieces)
        adjacent_pairs=sorted({(line,c) for y,c in pairs for line in (y,y+1) if 0<line<height})
        adjacent={(y,c,b):count+j*nb+b for j,(y,c)in enumerate(adjacent_pairs)for b in range(nb)}
        count+=len(adjacent)
        lines=sorted({y for y,c in adjacent_pairs})
        excess={(y,b):count+j*nb+b for j,y in enumerate(lines)for b in range(nb)}
        count+=len(excess)
        for y,c in adjacent_pairs:adjacent_lines.setdefault(y,[]).append(c)
    rr=[]; cc=[]; vv=[]; lo=[]; hi=[]
    def row(items, lower, upper):
        r=len(lo)
        for c,v in items: rr.append(r); cc.append(c); vv.append(v)
        lo.append(lower); hi.append(upper)
    for i,p in enumerate(pieces):
        if tuple((p['width'],p['height'])) not in LEGAL_SIZES:
            raise ValueError('ILLEGAL_OBJ_SIZE')
        for b,bank in enumerate(banks):
            if bank not in p.get('allowed_banks',banks): row([(i*nb+b,1)],0,0)
    for i,y,c in atoms:
        row([(local[i,y,c,b],1) for b in range(nb)],1,1)
        for b in range(nb):
            row([(local[i,y,c,b],1),(i*nb+b,-1)],-np.inf,0)
            row([(local[i,y,c,b],1),(resident[y,c,b],-1)],-np.inf,0)
    row([(i,1) for i in range(n*nb)],0,128)
    for y in sorted({y for y,c in pairs} | {yy for p in pieces for yy in range(p['y'],p['y']+p['height'])}):
        for b in range(nb): row([(resident[yy,c,b],1) for yy,c in pairs if yy==y],0,15)
        live = [(i*nb+b,1) for i,p in enumerate(pieces) if p['y']<=y<p['y']+p['height'] for b in range(nb)]
        row(live,0,32)
        row([(i*nb+b,(p['width']+7)//8) for i,p in enumerate(pieces)
             if p['y']<=y<p['y']+p['height'] for b in range(nb)],0,34)
    # A bank holds only 15 opaque identities before the next line. The
    # previous/current required union minus 15 is an unavoidable write lower
    # bound, regardless of lookahead. This is necessary, not a full schedule.
    for (y,c,b),variable in adjacent.items():
        for line in (y-1,y):
            if (line,c,b)in resident:row([(resident[line,c,b],1),(variable,-1)],-np.inf,0)
    for y,colors in adjacent_lines.items():
        for b in range(nb):row([(adjacent[y,c,b],1)for c in colors]+[(excess[y,b],-1)],-np.inf,15)
        row([(excess[y,b],1)for b in range(nb)],0,adjacent_write_budget)
    upper=np.ones(count)
    for variable in excess.values():upper[variable]=adjacent_write_budget
    objective=np.zeros(count); objective[:n*nb]=1
    result=milp(objective,integrality=np.ones(count),bounds=Bounds(np.zeros(count),upper),
        constraints=LinearConstraint(coo_matrix((vv,(rr,cc)),shape=(len(lo),count)).tocsc(),lo,hi),
        options={'time_limit':time_limit,'mip_rel_gap':0.03})
    if result.x is None:
        return dict(status='SCENE_MASK_GRID_INFEASIBLE' if result.status==2 else 'SOLVER_LIMIT',
                    solver_status=int(result.status),message=result.message)
    expanded=[]; assignment=[]
    for i,p in enumerate(pieces):
        for b,bank in enumerate(banks):
            rows={y:[c for c in cs if result.x[local[i,y,c,b]]>0.5] for y,cs in p['rows'].items()}
            if any(rows.values()):
                if bank not in p.get('allowed_banks',banks): raise AssertionError('INVALID_BANK_ELIGIBILITY')
                expanded.append(dict(p,rows=rows,source_piece=i)); assignment.append(bank)
    for i,p in enumerate(pieces):
        for y,cs in p['rows'].items():
            recovered=[c for q in expanded if q['source_piece']==i for c in q['rows'].get(y,[])]
            if sorted(recovered)!=sorted(cs): raise AssertionError('SCENE_COLOR_MASK_IDENTITY')
    for y in sorted({yy for p in pieces for yy in range(p['y'],p['y']+p['height'])}):
        live=[p for p in expanded if p['y']<=y<p['y']+p['height']]
        if len(live)>32 or sum((p['width']+7)//8 for p in live)>34: raise AssertionError('SCENE_OBJ_OVERFLOW')
        for bank in banks:
            if len({c for p,b in zip(expanded,assignment) if b==bank for c in p['rows'].get(y,[])})>15:
                raise AssertionError('SCENE_BANK_OVERFLOW')
    if len(expanded)>128: raise AssertionError('SCENE_OAM_OVERFLOW')
    adjacent_bounds={}
    if adjacent_write_budget is not None:
        demands={}
        for p,b in zip(expanded,assignment):
            for y,cs in p['rows'].items():demands.setdefault(y,{}).setdefault(b,set()).update(cs)
        for y in adjacent_lines:
            lower_bound=sum(max(0,len(demands.get(y-1,{}).get(b,set())|demands.get(y,{}).get(b,set()))-15)for b in banks)
            if lower_bound>adjacent_write_budget:raise AssertionError('ADJACENT_WRITE_BOUND_FAULT')
            adjacent_bounds[y]=lower_bound
    return dict(status='COLOR_MASK_FIXED_BANK_ASSIGNMENT_PROVEN',pieces=expanded,assignment=assignment,
        solver_status=int(result.status),message=result.message,objective=float(result.fun),
        lower_bound=float(result.mip_dual_bound),piece_row_color_identity_verified=True,
        adjacent_write_budget=adjacent_write_budget,adjacent_write_lower_bounds=adjacent_bounds,
        complete_palette_write_schedule_proven=False)


def schedule(pieces, assignment, height, lookahead=16, prefetch_write_budget=16, capacity=15):
    """Retain resident colors; evict farthest future use; preload empty slots.

    Lookahead bounds prefetch latency. Required misses are not artificially
    bandwidth capped. First row is VBlank initialization, not an HBlank write.
    This heuristic produces a valid schedule, not a minimum-bandwidth proof.
    """
    demands=[{} for _ in range(height)]
    for p,b in zip(pieces,assignment):
        for y,cs in p['rows'].items(): demands[y].setdefault(b,set()).update(cs)
    uses={}
    for y,line in enumerate(demands):
        for b,cs in line.items():
            for c in cs: uses.setdefault((b,c),[]).append(y)
    slots={b:[None]*capacity for b in set(assignment)}
    trace=[]; snapshots=[]
    def next_use(b,c,y):
        seq=uses.get((b,c),[]);i=bisect_right(seq,y)
        return seq[i] if i<len(seq) else height+lookahead+1
    for y,line in enumerate(demands):
        events=[];before={b:list(s) for b,s in slots.items()}
        for b,s in slots.items():
            required=line.get(b,set())
            if len(required)>capacity: raise ValueError('BANK_ROW_OVERFLOW')
            for c in sorted(required-set(s)):
                free=[i for i,v in enumerate(s) if v not in required]
                i=max(free,key=lambda i: next_use(b,s[i],y) if s[i] is not None else height+lookahead+2)
                events.append(dict(bank=b,slot=i+1,old=s[i],color=c,kind='required'))
                s[i]=c
        # Global earliest deadline first; idle slots can preload even when
        # filled with dead colors. Never evict this row's required identity.
        future=sorted((next_use(b,c,y),b,c) for b,c in uses if c not in slots[b])
        for when,b,c in future:
            if when>y+lookahead: break
            if y and len(events)>=prefetch_write_budget: break
            s=slots[b];required=line.get(b,set())
            free=[i for i,v in enumerate(s) if v not in required]
            if not free: continue
            i=max(free,key=lambda i: next_use(b,s[i],y) if s[i] is not None else height+lookahead+2)
            if s[i] is not None and next_use(b,s[i],y)<=when: continue
            events.append(dict(bank=b,slot=i+1,old=s[i],color=c,kind='prefetch'))
            s[i]=c
        snapshots.append({b:list(s) for b,s in slots.items()})
        trace.append(dict(scanline=y,resident_before=before,
            retained={b:[c for c in s if c is not None and c in slots[b]] for b,s in before.items()},
            evicted=[e['old'] for e in events if e['old'] is not None],
            prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,
            colors_written=len(events),cgram_data_bytes=2*len(events),
            affected_banks=sorted({e['bank'] for e in events}),
            phase='VBLANK_INITIALIZATION' if y==0 else 'BEFORE_SCANLINE'))
    return trace,snapshots


def bounded_schedule(pieces, assignment, height, capacity=15, write_budget=7, lookahead=16, time_limit=60,
                     fixed_residency=None,slot_locks=None,fixed_color_slots=None):
    """MILP admission for a strict total color-write budget per scanline.

    Residency is binary per color/bank/line; newly resident identities count
    as writes. No write is charged for eviction or initial VBlank loads.
    A feasible incumbent is replayed into fixed slots and verified locally.
    """
    demands=[{} for _ in range(height)];uses={}
    for p,b in zip(pieces,assignment):
        for y,cs in p['rows'].items():demands[y].setdefault(b,set()).update(cs)
    for y,line in enumerate(demands):
        for b,cs in line.items():
            for c in cs:uses.setdefault((b,c),[]).append(y)
    fixed_residency=fixed_residency or {};slot_locks=slot_locks or {}
    fixed_color_slots=fixed_color_slots or {}
    keys=sorted({(b,c,y) for (b,c),ys in uses.items() for y in range(max(0,ys[0]-lookahead),ys[-1]+1)} |
                {key for key,value in fixed_residency.items() if value})
    for b,c,y in keys:uses.setdefault((b,c),[])
    ids={key:i for i,key in enumerate(keys)};n=len(keys)
    rr=[];cc=[];vv=[];lo=[];hi=[]
    def row(items,lower,upper):
        r=len(lo)
        for c,v in items:rr.append(r);cc.append(c);vv.append(v)
        lo.append(lower);hi.append(upper)
    lower=np.zeros(n*2);upper=np.ones(n*2);integrality=np.zeros(n*2);integrality[:n]=1
    for key,value in fixed_residency.items():
        if key in ids:lower[ids[key]]=upper[ids[key]]=int(value)
        elif value:return dict(status='PINNED_RESIDENCY_OUTSIDE_LOOKAHEAD',key=list(key))
    objective=np.zeros(n*2);objective[n:]=1
    lineids={};bankline={}
    for i,(b,c,y) in enumerate(keys):
        bankline.setdefault((b,y),[]).append(i)
        if c in demands[y].get(b,set()):
            if upper[i]==0:return dict(status='PINNED_REQUIRED_RESIDENCY_CONFLICT',key=[b,c,y])
            lower[i]=1
        if y:
            items=[(i,1),(n+i,-1)]
            if (b,c,y-1) in ids:items.append((ids[b,c,y-1],-1))
            row(items,-np.inf,0);lineids.setdefault(y,[]).append(n+i)
        else:upper[n+i]=0
    for indices in bankline.values():row([(i,1) for i in indices],0,capacity)
    for indices in lineids.values():row([(i,1) for i in indices],0,write_budget)
    result=milp(objective,integrality=integrality,bounds=Bounds(lower,upper),
        constraints=LinearConstraint(coo_matrix((vv,(rr,cc)),shape=(len(lo),n*2)).tocsc(),lo,hi),
        options={'time_limit':time_limit,'mip_rel_gap':0.05})
    if result.x is None:return dict(status='WRITE_BUDGET_INFEASIBLE' if result.status==2 else 'SOLVER_LIMIT',solver_status=int(result.status),message=result.message)
    slots={b:[None]*capacity for b,c in uses};trace=[];states=[]
    residency=[{} for _ in range(height)]
    for i,(b,c,y) in enumerate(keys):
        if result.x[i]>0.5:residency[y].setdefault(b,set()).add(c)
    for y,line in enumerate(residency):
        before={b:list(s) for b,s in slots.items()};events=[]
        for b,s in slots.items():
            wanted=line.get(b,set());required=demands[y].get(b,set())
            if len(wanted)>capacity or not required<=wanted:raise AssertionError('RESIDENCY_ADMISSION_FAULT')
            for c in sorted(wanted-set(s)):
                end=y
                while end+1<height and c in residency[end+1].get(b,set()):end+=1
                candidates=[i for i,v in enumerate(s) if v not in wanted and all(
                    slot_locks.get((b,i,yy),c)==c for yy in range(y,end+1))]
                locked=[i for i in range(capacity) if slot_locks.get((b,i,y))==c]
                if (b,c) in fixed_color_slots:locked=[fixed_color_slots[b,c]]
                if locked:candidates=[i for i in candidates if i in locked]
                if not candidates:return dict(status='SLOT_LOCK_REPLAY_LIMIT',scanline=y,bank=b,color=c,
                    scope='Residency solution exists; greedy physical-slot replay failed. Not hardware infeasibility.')
                i=candidates[0]
                events.append(dict(bank=b,slot=i+1,old=s[i],color=c,kind='required' if c in required else 'prefetch'))
                s[i]=c
            # Eviction need not overwrite CGRAM; retain stale but harmless
            # identities. Future insertions can use their physical slots.
            if any(s[i]!=c for (bb,i,yy),c in slot_locks.items() if bb==b and yy==y):
                return dict(status='SLOT_LOCK_REPLAY_LIMIT',scanline=y,bank=b,
                    scope='Resident identity is in a different physical slot. Not hardware infeasibility.')
        if y and len(events)>write_budget:raise AssertionError('WRITE_BUDGET_FAULT')
        states.append({b:list(s) for b,s in slots.items()})
        trace.append(dict(scanline=y,resident_before=before,
            retained={b:[c for c in s if c is not None and c in slots[b]] for b,s in before.items()},
            evicted=[e['old'] for e in events if e['old'] is not None],
            prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,
            colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank'] for e in events}),
            phase='VBLANK_INITIALIZATION' if y==0 else 'BEFORE_SCANLINE'))
    return dict(status='BOUNDED_SLOT_SCHEDULE_PROVEN',trace=trace,states=states,
        solver_status=int(result.status),message=result.message,write_budget=write_budget,lookahead_lines=lookahead)


def prove_frame(pixels, size=(8,8), banks=tuple(range(8)), lookahead=16, time_limit=60, color_masks=False):
    pieces=pieces_for_grid(pixels,size)
    if not pieces:
        return dict(status='TRANSPARENT_FRAME_PROVEN',geometry=dict(oam_entries=0,peak_sprites_per_line=0,peak_tile_slivers_per_line=0),
                    pixel_identity_verified=True,peak_hblank_colors_written=0,peak_hblank_cgram_data_bytes=0,
                    hardware_geometry_admitted=True,native_timing_admitted=False,alpha_admitted=False)
    assignment=split_color_masks(pieces,banks,time_limit) if color_masks else assign_banks(pieces,banks,time_limit)
    if color_masks and 'pieces' in assignment:pieces=assignment.pop('pieces')
    geometry=dict(oam_entries=len(pieces),peak_sprites_per_line=max((sum(p['y']<=y<p['y']+p['height'] for p in pieces) for y in range(pixels.shape[0])),default=0),
        peak_tile_slivers_per_line=max((sum((p['width']+7)//8 for p in pieces if p['y']<=y<p['y']+p['height']) for y in range(pixels.shape[0])),default=0))
    result=dict(geometry=geometry,piece_size=list(size),allowed_banks=list(banks),**assignment)
    if 'assignment' not in assignment: return result
    trace,states=schedule(pieces,assignment['assignment'],pixels.shape[0],lookahead)
    recovered=np.full_like(pixels,-1);indices=np.zeros_like(pixels,dtype=np.uint8)
    for p,b in zip(pieces,assignment['assignment']):
        for y in p['rows']:
            for x in range(p['x'],min(p['x']+p['width'],pixels.shape[1])):
                c=int(pixels[y,x])
                if c>=0 and c in p['rows'][y]:
                    slot=states[y][b].index(c);indices[y,x]=slot+1;recovered[y,x]=states[y][b][slot]
    if not np.array_equal(pixels,recovered): raise AssertionError('PIXEL_IDENTITY_FAULT')
    counts=[r['colors_written'] for r in trace[1:]]
    lifetimes={}
    for p in pieces:
        for y,cs in p['rows'].items():
            for c in cs:lifetimes.setdefault(c,set()).add(y)
    result.update(pieces=[dict(**p,bank=b) for p,b in zip(pieces,assignment['assignment'])],
        color_lifetimes=[dict(rgb555=c,first_line=min(ys),last_line=max(ys),required_lines=sorted(ys)) for c,ys in sorted(lifetimes.items())],
        trace=trace,lookahead_lines=lookahead,peak_hblank_colors_written=max(counts,default=0),
        peak_hblank_cgram_data_bytes=2*max(counts,default=0),
        average_hblank_colors_written=float(np.mean(counts)) if counts else 0,
        worst_scanline=1+int(np.argmax(counts)) if counts else None,
        pixel_identity_verified=True,source_rgb555_sha256=hashlib.sha256(pixels.astype('<i4').tobytes()).hexdigest(),
        remapped_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
        hardware_geometry_admitted=(geometry['oam_entries']<=128 and geometry['peak_sprites_per_line']<=32 and geometry['peak_tile_slivers_per_line']<=34),
        native_timing_admitted=False,alpha_admitted=False)
    return result
