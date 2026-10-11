"""Bounded word-to-bank balancing over exact source OAM masks.

Every output mask retains a fixed bank. The interval objective is a necessary
cache bound, not a residency, physical transfer or native timing certificate.
"""
import copy,math,random,time
import numpy as np
from raster_global_bank_classes import rebuild_schedule
from raster_slot_greedy import bank_groups,demand


def balance(source,initial,steps=50000,seed=618,time_limit=40,maximum_oam=128,maximum_tiles=34,maximum_sprites=32):
    if type(steps)is not int or steps<0 or time_limit<=0 or not 1<=maximum_oam<=128 or not 1<=maximum_tiles<=34 or not 1<=maximum_sprites<=32:
        raise ValueError('WORD_BANK_BALANCE_DOMAIN')
    # Rebuild first: a success flag alone is not source/geometry authority.
    rebuild_schedule(source,initial)
    groups=bank_groups(source);pieces=copy.deepcopy(source['pieces']);keys=[];indices={};assignment=[];domains=[]
    for p,image in zip(pieces,demand(source)[2]):
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if np.any(row>=0)}
    for p,bank in zip(initial['pieces'],initial['assignment']):
        original=pieces[p['source_piece']]
        domain=tuple(b for b in next(g for g in groups if original['bank']in g)if b in original.get('allowed_banks',range(8)))
        for cs in p['rows'].values():
            for color in cs:
                key=domain,color
                if key in indices:
                    if assignment[indices[key]]!=bank:raise ValueError('WORD_BANK_BALANCE_REQUIRES_GLOBAL_WORD_BANK')
                else:indices[key]=len(keys);keys.append(key);assignment.append(bank);domains.append(domain)
    unique_domains=set(domains)
    if any(set(a)&set(b)for a in unique_domains for b in unique_domains if a!=b):
        raise ValueError('WORD_BANK_BALANCE_OVERLAPPING_ELIGIBILITY_DOMAINS')
    active=sorted({int(y)for p in pieces for y,cs in p['rows'].items()if cs})
    if not active:raise ValueError('WORD_BANK_BALANCE_EMPTY')
    first,last=min(active),max(active);height=last-first+1
    rows=np.zeros((height,len(keys)),dtype=np.int16);owned=np.zeros((len(pieces),len(keys)),dtype=np.int16)
    for i,p in enumerate(pieces):
        domain=tuple(b for b in next(g for g in groups if p['bank']in g)if b in p.get('allowed_banks',range(8)))
        for y,cs in p['rows'].items():
            for c in cs:
                if(domain,c)not in indices:raise ValueError('WORD_BANK_BALANCE_MISSING_SOURCE_WORD')
                column=indices[domain,c];rows[int(y)-first,column]=1;owned[i,column]=1
    live=np.array([[p['y']<=y<p['y']+p['height']for p in pieces]for y in range(first,last+1)],dtype=np.int16)
    tile_widths=np.array([p['width']//8 for p in pieces],dtype=np.int16)
    unions=[];lengths=[]
    for begin in range(height-1):
        union=np.zeros(len(keys),dtype=np.int16)
        for end in range(begin,height):
            union=np.maximum(union,rows[end])
            if end>begin:unions.append(union.copy());lengths.append(end-begin)
    unions=np.array(unions,dtype=np.int16).reshape((-1,len(keys)));lengths=np.array(lengths)
    def counts(a):
        encoded=np.eye(8,dtype=np.int16)[a]
        return rows@encoded,owned@encoded,unions@encoded
    def score(rc,pc,ic):
        masks=(pc>0).astype(np.int16);per_piece=masks.sum(axis=1)
        sprites=live@per_piece;tiles=live@(per_piece*tile_widths)
        invalid=max(0,int(rc.max())-15)+max(0,int(tiles.max())-maximum_tiles)+max(0,int(sprites.max())-maximum_sprites)+max(0,int(masks.sum())-maximum_oam)
        interval=np.maximum(ic-15,0).sum(axis=1)/lengths if len(lengths)else np.array([0.])
        return(invalid,float(interval.max()),float(interval.mean()),int(masks.sum()))
    def energy(value):return value[0]*100000+value[1]*1000+value[2]*10+value[3]*.1
    assignment=np.array(assignment,dtype=np.int16);rc,pc,ic=counts(assignment);current=score(rc,pc,ic)
    if current[0]:raise ValueError('WORD_BANK_BALANCE_INITIAL_HARDWARE_LIMIT')
    initial_score=current;best=current;best_assignment=assignment.copy();rng=random.Random(seed);started=time.monotonic();accepted=sampled=0
    for step in range(steps):
        if time.monotonic()-started>time_limit:break
        column=rng.randrange(len(keys));old=int(assignment[column]);new=rng.choice(domains[column])
        if old==new:continue
        sampled+=1;dr=rows[:,column];dp=owned[:,column];di=unions[:,column]
        rc[:,old]-=dr;rc[:,new]+=dr;pc[:,old]-=dp;pc[:,new]+=dp;ic[:,old]-=di;ic[:,new]+=di
        candidate=score(rc,pc,ic);temperature=100*(.002**(step/max(1,steps)))
        if candidate<current or rng.random()<math.exp(min(0,(energy(current)-energy(candidate))/temperature)):
            assignment[column]=new;current=candidate;accepted+=1
            if current<best:best=current;best_assignment=assignment.copy()
        else:
            rc[:,old]+=dr;rc[:,new]-=dr;pc[:,old]+=dp;pc[:,new]-=dp;ic[:,old]+=di;ic[:,new]-=di
    expanded=[];banks=[]
    for i,p in enumerate(pieces):
        domain=tuple(b for b in next(g for g in groups if p['bank']in g)if b in p.get('allowed_banks',range(8)))
        for bank in domain:
            rs={int(y):[c for c in cs if best_assignment[indices[domain,c]]==bank]for y,cs in p['rows'].items()}
            if any(rs.values()):expanded.append(dict(p,rows=rs,source_piece=i));banks.append(bank)
    search=dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=banks,pixel_word_identities_replayed=True,
        word_bank_balance=dict(initial_objective=list(initial_score),final_objective=list(best),seed=seed,steps_requested=steps,proposals_sampled=sampled,moves_accepted=accepted,seconds=time.monotonic()-started,
            maximum_oam=maximum_oam,maximum_tiles=maximum_tiles,maximum_sprites=maximum_sprites,interval_objective_is_residency_relaxation=True),
        global_word_bank_identity_restricted=True,physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    result=rebuild_schedule(source,search,last-first)
    result['word_bank_balance']=copy.deepcopy(search['word_bank_balance'])
    return result,search


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('schedule','initial-search','output','search-output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--steps',type=int,default=50000);parser.add_argument('--seed',type=int,default=618)
    parser.add_argument('--time-limit',type=float,default=40);parser.add_argument('--maximum-oam',type=int,default=128)
    parser.add_argument('--maximum-tiles',type=int,default=34);parser.add_argument('--maximum-sprites',type=int,default=32)
    args=parser.parse_args()
    frame,search=balance(json.loads(args.schedule.read_text()),json.loads(args.initial_search.read_text()),args.steps,args.seed,args.time_limit,args.maximum_oam,args.maximum_tiles,args.maximum_sprites)
    args.output.write_text(json.dumps(frame,indent=2)+'\n');args.search_output.write_text(json.dumps(search,indent=2)+'\n')
    print(json.dumps(dict(geometry=frame['geometry'],search=search['word_bank_balance'],physical_transfer_admitted=False,native_timing_admitted=False)))


if __name__=='__main__':main()
