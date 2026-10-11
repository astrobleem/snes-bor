"""Balance fixed OAM banks with alias-aware interval pressure.

The score is a necessary cache bound, not an executable transfer schedule.
Equal RGB555 words in one bank count once, including overlapping objects.
"""
import copy, math, random, time
import numpy as np
from raster_slot_greedy import demand, bank_groups
from raster_global_bank_classes import rebuild_schedule


def balance(source, steps=20000, seed=618, time_limit=40):
    if type(steps) is not int or steps < 0 or time_limit <= 0:
        raise ValueError('PIECE_BANK_BALANCE_DOMAIN')
    _, _, images = demand(source)
    pieces = copy.deepcopy(source['pieces']); groups = bank_groups(source)
    domains = []
    for p, image in zip(pieces, images):
        p['rows'] = {p['y']+y: sorted(set(map(int, row[row >= 0])))
                     for y, row in enumerate(image) if np.any(row >= 0)}
        domains.append(tuple(b for b in next(g for g in groups if p['bank'] in g)
                             if b in p.get('allowed_banks', range(8))))
        if not domains[-1]: raise ValueError('PIECE_BANK_BALANCE_BANK_ELIGIBILITY')
    active = sorted({y for p in pieces for y in p['rows']})
    if not active: raise ValueError('PIECE_BANK_BALANCE_EMPTY')
    first, last = min(active), max(active); height = last-first+1
    colors = sorted({c for p in pieces for cs in p['rows'].values() for c in cs})
    columns = {c:i for i,c in enumerate(colors)}
    intervals = [(a,b) for a in range(height) for b in range(a+1,height)]
    lengths = np.array([b-a for a,b in intervals])
    row_cells = []; interval_cells = []
    for p in pieces:
        cells = [(y-first,columns[c]) for y,cs in p['rows'].items() for c in cs]
        row_cells.append(tuple(np.array(cells,dtype=int).reshape((-1,2)).T))
        cells = []
        for i,(a,b) in enumerate(intervals):
            cs = {c for y,row in p['rows'].items() if first+a <= y <= first+b for c in row}
            cells.extend((i,columns[c]) for c in cs)
        interval_cells.append(tuple(np.array(cells,dtype=int).reshape((-1,2)).T))
    rc = np.zeros((8,height,len(colors)),dtype=np.int16)
    ic = np.zeros((8,len(intervals),len(colors)),dtype=np.int16)
    assignment = np.array([p['bank'] for p in pieces])
    for i,b in enumerate(assignment):
        np.add.at(rc[b],row_cells[i],1); np.add.at(ic[b],interval_cells[i],1)
    rn = (rc > 0).sum(axis=2); inn = (ic > 0).sum(axis=2)
    def score():
        bounds = np.maximum(inn-15,0).sum(axis=0)/lengths if len(lengths) else np.array([0.])
        return (max(0,int(rn.max())-15),float(bounds.max()),float(bounds.mean()))
    def energy(v): return v[0]*100000+v[1]*1000+v[2]*10
    def move(i,old,new):
        for counts,totals,cells in ((rc,rn,row_cells[i]),(ic,inn,interval_cells[i])):
            rows,cols = cells
            gone = counts[old][cells] == 1; gained = counts[new][cells] == 0
            np.add.at(totals[old],rows,-gone.astype(int))
            np.add.at(totals[new],rows,gained.astype(int))
            counts[old][cells] -= 1; counts[new][cells] += 1
    current = score()
    if current[0]: raise ValueError('PIECE_BANK_BALANCE_INITIAL_CAPACITY')
    initial = current; best = current; best_assignment = assignment.copy()
    rng = random.Random(seed); started = time.monotonic(); accepted = sampled = 0
    for step in range(steps):
        if time.monotonic()-started > time_limit: break
        i = rng.randrange(len(pieces)); old = int(assignment[i]); new = rng.choice(domains[i])
        if old == new: continue
        sampled += 1; move(i,old,new); candidate = score()
        temperature = 100*(.002**(step/max(1,steps)))
        if candidate < current or rng.random() < math.exp(min(0,(energy(current)-energy(candidate))/temperature)):
            assignment[i] = new; current = candidate; accepted += 1
            if current < best: best = current; best_assignment = assignment.copy()
        else: move(i,new,old)
    search = dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',
                  pieces=[dict(p,source_piece=i) for i,p in enumerate(pieces)],
                  assignment=best_assignment.tolist(),pixel_word_identities_replayed=True)
    result = rebuild_schedule(source,search,height)
    result['piece_bank_balance'] = dict(initial_objective=list(initial),final_objective=list(best),
        seed=seed,steps_requested=steps,proposals_sampled=sampled,moves_accepted=accepted,
        seconds=time.monotonic()-started,word_bank_copies_allowed=True,
        interval_objective_is_residency_relaxation=True,physical_transfer_admitted=False,
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    return result


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=20000);parser.add_argument('--seed',type=int,default=618)
    parser.add_argument('--time-limit',type=float,default=40)
    args=parser.parse_args();result=balance(json.loads(args.schedule.read_text()),args.steps,args.seed,args.time_limit)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['piece_bank_balance']))


if __name__=='__main__':main()
