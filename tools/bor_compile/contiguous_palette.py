"""Offline bounded contiguous CGRAM bursts; failure is heuristic, not a limit."""
from bisect import bisect_right
import hashlib
import json
import argparse
from pathlib import Path
import numpy as np


def attempt(lines,capacity,span,layout='first',prefetch=True,breaks=(),compact=False,initial_slots=None):
    if not 1<=span<=capacity<=255:raise ValueError('INVALID_CONTIGUOUS_CAPACITY')
    uses={}
    for y,cs in enumerate(lines):
        for c in cs:uses.setdefault(c,[]).append(y)
    order=sorted(uses,key=lambda c:(uses[c][0],c))
    if layout.startswith('initial_'):
        if layout=='initial_frequency':ranked=sorted(uses,key=lambda c:(-len(uses[c]),uses[c][0],c))
        elif layout=='initial_persistent':ranked=sorted(uses,key=lambda c:(-(uses[c][-1]-uses[c][0]),uses[c][0],c))
        elif layout=='initial_last':ranked=sorted(uses,key=lambda c:(-uses[c][-1],uses[c][0],c))
        elif layout=='initial_peak':
            peak=max(range(len(lines)),key=lambda y:len(lines[y]))
            importance={c:sum(abs(y-peak)<=12 for y in ys) for c,ys in uses.items()}
            ranked=sorted(uses,key=lambda c:(-importance[c],-len(uses[c]),uses[c][0],c))
        else:raise ValueError('INVALID_INITIAL_PALETTE_LAYOUT')
        # VBlank may preload any future identities, but line zero is mandatory.
        required=set(lines[0]);order=sorted(required)+[c for c in ranked if c not in required]
    initial=order[:capacity]
    if layout=='persistent':initial.sort(key=lambda c:(-(uses[c][-1]-uses[c][0]),uses[c][0],c))
    elif layout=='last':initial.sort(key=lambda c:(uses[c][-1],uses[c][0],c))
    elif layout=='frequency':initial.sort(key=lambda c:(-len(uses[c]),uses[c][0],c))
    slots=initial+[None]*(capacity-len(initial));trace=[];states=[]
    if initial_slots is not None:
        if len(initial_slots)!=capacity:raise ValueError('CONTIGUOUS_INITIAL_RESIDENCY_SIZE')
        slots=[c if c in uses else None for c in initial_slots]
        present=set(slots)-{None}
        if len(present)!=sum(c is not None for c in slots):raise ValueError('CONTIGUOUS_INITIAL_DUPLICATE_IDENTITY')
        mandatory=set(lines[0])-present
        for c in sorted(mandatory):
            free=next((i for i,v in enumerate(slots) if v is None),None)
            if free is None:
                candidates=[i for i,v in enumerate(slots) if v not in lines[0]]
                if not candidates:return dict(status='CONTIGUOUS_HEURISTIC_LIMIT',scanline=0,missing=len(mandatory),layout=layout)
                free=max(candidates,key=lambda i:(uses[slots[i]][0],i))
            slots[free]=c
        present=set(slots)-{None}
        wanted=sorted(set(lines[0])-present)+[c for c in order if c not in present and c not in lines[0]]
        for i,c in zip((i for i,v in enumerate(slots) if v is None),wanted):slots[i]=c
    def nxt(c,y):
        if c is None:return len(lines)+1
        i=bisect_right(uses[c],y)
        return uses[c][i] if i<len(uses[c]) else len(lines)+1
    for y,required in enumerate(lines):
        required=set(required);missing=required-set(slots)
        if len(missing)>span:
            return dict(status='CONTIGUOUS_HEURISTIC_LIMIT',scanline=y,missing=len(missing),layout=layout)
        if y==0:
            if missing:raise AssertionError('INITIAL_REQUIRED_COLORS_MISSING')
            trace.append(dict(scanline=0,start_slot=1,values=list(slots),phase='VBLANK'))
            states.append(list(slots));continue
        future=sorted((c for c in uses if c not in slots and c not in missing),key=lambda c:(nxt(c,y),c))
        best=None
        for start in range(capacity-span+1):
            if any(start<b<start+span for b in breaks):continue
            free=[i for i in range(start,start+span) if slots[i] not in required]
            if len(free)<len(missing):continue
            victims=sorted(free,key=lambda i:(-nxt(slots[i],y),i))
            cost=sum((len(lines)+1-nxt(slots[i],y)) for i in victims[:len(missing)])
            gain=sum(max(0,nxt(slots[i],y)-nxt(c,y))
                     for i,c in zip(victims[len(missing):],future)) if prefetch else 0
            score=(cost,-gain,-len(free),start)
            if best is None or score<best[0]:best=(score,start,victims)
        if best is None:
            return dict(status='CONTIGUOUS_HEURISTIC_LIMIT',scanline=y,missing=len(missing),
                        reason='NO_SAFE_SINGLE_BURST_WINDOW',layout=layout)
        _,start,victims=best;updates=[];before=list(slots)
        for c,i in zip(sorted(missing),victims):
            updates.append(dict(slot=i+1,old=slots[i],color=c));slots[i]=c
        rest=victims[len(missing):]
        if prefetch:
            for i in rest:
                candidates=[c for c in future if c not in slots and nxt(c,y)<nxt(slots[i],y)]
                if candidates:
                    c=candidates[0];updates.append(dict(slot=i+1,old=slots[i],color=c));slots[i]=c
        if compact:
            # The chosen burst already transfers every word in its window.
            # Pack long-lived current identities together inside that window
            # so later dead slots can form a contiguous refill region. Pixels
            # are remapped offline to the resulting per-row slot identities.
            window=slots[start:start+span]
            window.sort(key=lambda c:(c is None,c not in required,
                -(uses[c][-1] if c is not None else -1),nxt(c,y),c if c is not None else -1))
            slots[start:start+span]=window
            updates=[dict(slot=i+1,old=before[i],color=slots[i]) for i in range(start,start+span) if before[i]!=slots[i]]
        if not required<=set(slots):raise AssertionError('CONTIGUOUS_PALETTE_IDENTITY')
        trace.append(dict(scanline=y,start_slot=start+1,values=slots[start:start+span] if updates else [],
                          updates=updates,data_bytes=span*2 if updates else 0,phase='BEFORE_SCANLINE'))
        states.append(list(slots))
    return dict(status='CONTIGUOUS_BURST_SCHEDULE_PROVEN',capacity=capacity,span=span,layout=layout,breaks=list(breaks),compact=compact,
                trace=trace,states=states,peak_cgram_data_bytes=span*2,native_admitted=False,
                previous_frame_residency_used=initial_slots is not None)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--canvas',type=Path,required=True)
    p.add_argument('--capacity',type=int,default=239);p.add_argument('--span',type=int,default=16)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raw=a.canvas.read_bytes();pixels=np.frombuffer(raw,dtype='<u2').reshape(224,256)
    lines=[set(map(int,row)) for row in pixels];attempts=[]
    for layout in ('first','persistent','last','frequency'):
        r=attempt(lines,a.capacity,a.span,layout,breaks=(111,) if a.capacity in (175,239) else ())
        attempts.append({k:v for k,v in r.items() if k not in ('trace','states')})
        if 'states' in r:
            indices=np.array([[r['states'][y].index(int(c))+1 for c in row] for y,row in enumerate(pixels)],dtype=np.uint8)
            recovered=np.array([[r['states'][y][i-1] for i in row] for y,row in enumerate(indices)],dtype='<u2')
            if not np.array_equal(pixels,recovered):raise AssertionError('CONTIGUOUS_PIXEL_IDENTITY')
            r.update(pixel_identity_verified=True,indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest())
            assets=a.output.with_suffix('');assets.mkdir(parents=True,exist_ok=True)
            (assets/'indices.bin').write_bytes(indices.tobytes());(assets/'expected.rgb555').write_bytes(raw)
            (assets/'initial.json').write_text(json.dumps(r['states'][0])+'\n');r.pop('states');break
    else:r=dict(status='CONTIGUOUS_HEURISTIC_LIMIT',native_admitted=False)
    r.update(attempts=attempts,canvas_sha256=hashlib.sha256(raw).hexdigest())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='trace'}))


if __name__=='__main__':main()
