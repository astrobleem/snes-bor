"""Lossless SMALL footprint placement with byte-identical tile overlap."""
import random


def solve(blocks, seconds=120):
    """Binary placement formulation; a feasible answer is checked byte-for-byte."""
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import coo_array
    blocks=sorted(set(blocks));variables=[];cellvars={};constraints=[]
    for i,b in enumerate(blocks):
        indices=[]
        for y in range(13):
            for x in range(15):
                # The whole atlas may be reflected with each footprint's
                # offsets reflected; do not impose a fixed corner position.
                n=len(variables);variables.append((i,y*16+x));indices.append(n)
        constraints.append((indices,[1]*len(indices),1,1))
    base=len(variables)
    for n,(i,o) in enumerate(variables):
        b=blocks[i]
        for k in range(8):
            pair=(o+(k//2)*16+k%2,b[k*32:(k+1)*32])
            if pair not in cellvars:cellvars[pair]=base+len(cellvars)
            constraints.append(([n,cellvars[pair]],[1,-1],-np.inf,0))
    for cell in range(256):
        ids=[v for (at,_),v in cellvars.items() if at==cell]
        constraints.append((ids,[1]*len(ids),-np.inf,1))
    rows=[];cols=[];data=[];lo=[];hi=[]
    for r,(cc,vv,l,h) in enumerate(constraints):
        rows.extend([r]*len(cc));cols.extend(cc);data.extend(vv);lo.append(l);hi.append(h)
    size=base+len(cellvars)
    matrix=coo_array((np.array(data,dtype=float),(np.array(rows,dtype=np.int32),np.array(cols,dtype=np.int32))),shape=(len(lo),size)).tocsc()
    result=milp(np.zeros(size),integrality=np.r_[np.ones(base),np.zeros(len(cellvars))],
                bounds=Bounds(0,1),constraints=LinearConstraint(matrix,lo,hi),options=dict(time_limit=seconds))
    if result.x is None:raise ValueError(f'MILP status={result.status}: {result.message}')
    origins={};grid={}
    for n,(i,o) in enumerate(variables):
        if result.x[n]<.5:continue
        assert blocks[i] not in origins;origins[blocks[i]]=o
        for k in range(8):
            at=o+(k//2)*16+k%2;t=blocks[i][k*32:(k+1)*32]
            assert at not in grid or grid[at]==t
            grid[at]=t
    assert len(origins)==len(blocks)
    return origins,grid


def solve_torus(blocks,seconds=120):
    """Symmetry-reduced relaxation admitting the PPU's wrapped tile origins."""
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import coo_matrix
    blocks=sorted(set(blocks));isolated=[]
    grids=[{(x,y):b[(y*2+x)*32:(y*2+x+1)*32] for y in range(4) for x in range(2)} for b in blocks]
    for i,a in enumerate(grids):
        shares=False
        for j,b in enumerate(grids):
            if i==j:continue
            for dy in range(-3,4):
                for dx in range(-1,2):
                    bb={(x+dx,y+dy):t for (x,y),t in b.items()}
                    if all(a[k]==bb[k] for k in a.keys()&bb.keys()):shares=True
        if not shares:isolated.append(i)
    print('isolated footprints',len(isolated),flush=True)
    cells={o:[((o//16+r)&15)*16+((o%16+c)&15) for r in range(4) for c in range(2)] for o in range(256)}
    fixed=set(cells[0]);variables=[];constraints=[];solid=[]
    for i in range(len(blocks)):
        if i in isolated:continue
        ids=[]
        for o,cc in cells.items():
            if isolated and fixed.intersection(cc):continue
            ids.append(len(variables));variables.append((i,o))
        constraints.append((ids,[1]*len(ids),1,1))
    for o,cc in cells.items():
        if not isolated:break
        if o!=0 and fixed.intersection(cc):continue
        solid.append(len(variables));variables.append((-1,o))
    if isolated:
        constraints.append((solid,[1]*len(solid),len(isolated),len(isolated)))
        constraints.append(([solid[0]],[1],1,1))
    base=len(variables);z={}
    for n,(i,o) in enumerate(variables):
        if i<0:continue
        for k,at in enumerate(cells[o]):
            pair=(at,blocks[i][k*32:(k+1)*32]);v=z.setdefault(pair,base+len(z))
            constraints.append(([n,v],[1,-1],-np.inf,0))
    for at in range(256):
        ids=[v for (cell,_),v in z.items() if cell==at]+[n for n in solid if at in cells[variables[n][1]]]
        constraints.append((ids,[1]*len(ids),-np.inf,1))
    rows=[];cols=[];data=[];lo=[];hi=[]
    for r,(cc,vv,l,h) in enumerate(constraints):
        rows.extend([r]*len(cc));cols.extend(cc);data.extend(vv);lo.append(l);hi.append(h)
    size=base+len(z);matrix=coo_matrix((np.array(data,dtype=float),(rows,cols)),shape=(len(lo),size)).tocsc()
    result=milp(np.zeros(size),integrality=np.r_[np.ones(base),np.zeros(len(z))],bounds=Bounds(0,1),
                constraints=LinearConstraint(matrix,lo,hi),options=dict(time_limit=seconds))
    if result.x is None:raise ValueError(f'TORUS MILP status={result.status}: {result.message}')
    origins={};grid={};nextsolid=iter(isolated)
    for n,(i,o) in enumerate(variables):
        if result.x[n]<.5:continue
        if i<0:i=next(nextsolid)
        assert blocks[i] not in origins;origins[blocks[i]]=o
        for k,at in enumerate(cells[o]):
            t=blocks[i][k*32:(k+1)*32];assert at not in grid or grid[at]==t;grid[at]=t
    assert len(origins)==len(blocks)
    return origins,grid


def search(blocks, steps=50000, seed=0, wrap=False, fixed=None):
    """Deterministic compile-time min-conflict search; failure is not UNSAT."""
    import numpy as np
    fixed=fixed or {};allblocks=sorted(set(blocks));blocks=[b for b in allblocks if b not in fixed];rng=np.random.default_rng(seed)
    vocabulary={t:i for i,t in enumerate(sorted({b[n:n+32] for b in allblocks for n in range(0,256,32)}))}
    tiles=np.array([[vocabulary[b[n:n+32]] for n in range(0,256,32)] for b in blocks])
    origins=np.array([y*16+x for y in range(16 if wrap else 13) for x in range(16 if wrap else 15)])
    cells=np.array([[(((o//16+r)&15)*16+((o%16+c)&15)) for r in range(4) for c in range(2)] for o in origins])
    positions=rng.integers(0,len(origins),len(blocks))
    counts=np.zeros((256,len(vocabulary)),dtype=np.int16);total=np.zeros(256,dtype=np.int16)
    for b,o in fixed.items():
        cc=[((o//16+r)&15)*16+((o%16+c)&15) for r in range(4) for c in range(2)]
        tt=[vocabulary[b[n:n+32]] for n in range(0,256,32)]
        counts[cc,tt]+=1;total[cc]+=1
    for i,p in enumerate(positions):counts[cells[p],tiles[i]]+=1;total[cells[p]]+=1
    tabu=np.zeros((len(blocks),len(origins)),dtype=np.int32)
    best=100000
    for step in range(steps):
        conflicts=(total[cells[positions]]-counts[cells[positions],tiles]).sum(axis=1)
        error=int(conflicts.sum());best=min(best,error)
        if not error:
            result=dict(fixed);result.update({b:int(origins[positions[i]]) for i,b in enumerate(blocks)});grid={}
            for b,o in result.items():
                for n in range(8):
                    at=((o//16+n//2)&15)*16+((o%16+n%2)&15);t=b[n*32:(n+1)*32]
                    assert at not in grid or grid[at]==t
                    grid[at]=t
            return result,grid
        active=np.flatnonzero(conflicts)
        i=int(rng.integers(len(blocks))) if step%7==0 else int(rng.choice(active))
        if wrap and step%3==0:
            group=[i]
            own=set(cells[positions[i]])
            neighbours=[j for j in range(len(blocks)) if j!=i and own.intersection(cells[positions[j]])]
            rng.shuffle(neighbours)
            group+=neighbours[:int(rng.integers(1,5))]
            for j in group:counts[cells[positions[j]],tiles[j]]-=1;total[cells[positions[j]]]-=1
            alternatives=[];score=np.zeros(256)
            for j in group:
                old=origins[positions[j]]
                shifted=(((old//16+origins//16)&15)*16+((old%16+origins%16)&15))
                alternatives.append(shifted)
                score+=(total[cells[shifted]]-counts[cells[shifted],tiles[j]]).sum(axis=1)
            score+=rng.random(256)*.9
            shift=int(score.argmin())
            for j,alt in zip(group,alternatives):
                positions[j]=alt[shift];counts[cells[positions[j]],tiles[j]]+=1;total[cells[positions[j]]]+=1
            continue
        old=positions[i];counts[cells[old],tiles[i]]-=1;total[cells[old]]-=1
        score=(total[cells]-counts[cells,tiles[i]]).sum(axis=1).astype(float)
        score[tabu[i]>step]+=1000
        score+=rng.random(len(origins))*.9
        if step%47==0:p=int(rng.integers(len(origins)))
        else:p=int(score.argmin())
        tabu[i,old]=step+int(rng.integers(5,30))
        positions[i]=p;counts[cells[p],tiles[i]]+=1;total[cells[p]]+=1
    raise ValueError(f'OVERLAP_SEARCH_EXHAUSTED: best pair conflict={best}; not an impossibility proof')


def strips(blocks, attempts=1000, wrap=False):
    """Pack identical two-tile rows into eight legal 16-row OBJ columns."""
    rng=random.Random(0)
    for attempt in range(attempts):
        chains=[([b[i:i+64] for i in range(0,256,64)],{b:0}) for b in sorted(set(blocks))]
        while len(chains)>8:
            choices=[]
            for i,(a,_) in enumerate(chains):
                for j,(b,_) in enumerate(chains):
                    if i==j:continue
                    overlap=max([0]+[n for n in range(1,min(len(a),len(b))+1) if a[-n:]==b[:n]])
                    size=len(a)+len(b)-overlap
                    joinedrows=a+b[overlap:]
                    valid=size<=16 or (wrap and size<=19 and joinedrows[16:]==joinedrows[:size-16])
                    if valid:choices.append((-overlap, size if not attempt else rng.random(),i,j))
            if not choices:break
            _,_,i,j=min(choices);a,aa=chains[i];b,bb=chains[j]
            overlap=max([0]+[n for n in range(1,min(len(a),len(b))+1) if a[-n:]==b[:n]])
            joined=(a+b[overlap:],dict(aa,**{}));joined[1].update({k:v+len(a)-overlap for k,v in bb.items()})
            chains=[c for n,c in enumerate(chains) if n not in (i,j)]+[joined]
        if len(chains)<=8:
            origins={};grid={}
            for col,(rows,starts) in enumerate(chains):
                for block,row in starts.items():origins[block]=(row%16)*16+col*2
                for row,data in enumerate(rows[:16]):
                    for x in range(2):grid[row*16+col*2+x]=data[x*32:(x+1)*32]
            return origins,grid
    raise ValueError('STRIP_SEARCH_EXHAUSTED; not an impossibility proof')


def place(blocks, protected=None, attempts=200):
    """Pure compile-time search. A zero tile is data, not a don't-care.

    Returns physical tile origins; no live relocation is performed here.
    """
    protected=protected or {}
    ordered=sorted(set(blocks))
    rng=random.Random(0)
    for attempt in range(attempts):
        grid=dict(protected);origins={}
        order=sorted(ordered,key=lambda b:(-sum(any(b[n:n+32]) for n in range(0,256,32)),b))
        if attempt:
            rng.shuffle(order)
            order.sort(key=lambda b:-sum(any(b[n:n+32]) for n in range(0,256,32)))
        for block in order:
            tiles=[block[n:n+32] for n in range(0,256,32)]
            candidates=[]
            for y in range(13):
                for x in range(15):
                    cells={16*(y+r)+x+c:tiles[2*r+c] for r in range(4) for c in range(2)}
                    if any(i in grid and grid[i]!=t for i,t in cells.items()):continue
                    new=sum(i not in grid for i in cells)
                    candidates.append((new, rng.random() if attempt else y*16+x,y*16+x,cells))
            if not candidates:break
            _,_,origin,cells=min(candidates)
            grid.update(cells);origins[block]=origin
        else:return origins,grid
    raise ValueError('OVERLAP_PLACEMENT_SEARCH_EXHAUSTED; not an impossibility proof')

