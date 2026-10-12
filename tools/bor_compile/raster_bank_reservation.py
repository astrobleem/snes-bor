"""Exhaustively move a bounded set of fixed OBJ pieces off reserved banks.

This proves row capacity and source identity only; residency and physical
transfer admission remain separate. Large assignment spaces fail explicitly.
"""
import copy,itertools
import numpy as np
from raster_slot_greedy import demand,bank_groups
from raster_global_bank_classes import rebuild_schedule


def reserve(source,reserved_banks,maximum_assignments=100000,lookahead=17):
    if (not isinstance(reserved_banks,(list,tuple))or not reserved_banks or
        any(type(b)is not int or not 0<=b<8 for b in reserved_banks)or
        len(set(reserved_banks))!=len(reserved_banks)or
        type(maximum_assignments)is not int or maximum_assignments<1):
        raise ValueError('BANK_RESERVATION_DOMAIN')
    _,_,images=demand(source);groups=bank_groups(source);pieces=copy.deepcopy(source['pieces'])
    rows=[{p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(im)if np.any(row>=0)}for p,im in zip(pieces,images)]
    moving=[i for i,p in enumerate(pieces)if p['bank']in reserved_banks];domains=[]
    for i in moving:
        p=pieces[i];domains.append([b for b in next(g for g in groups if p['bank']in g)
                                   if b not in reserved_banks and b in p.get('allowed_banks',range(8))])
    count=1
    for domain in domains:count*=len(domain)
    report=dict(schema='BYOR_BOUNDED_BANK_RESERVATION_V1',reserved_banks=list(reserved_banks),
        moving_pieces=len(moving),assignment_space=count,physical_transfer_admitted=False,
        concurrent_actor_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,
        no_color_reduction=True)
    if count>maximum_assignments:return dict(report,status='ASSIGNMENT_SPACE_LIMIT')
    valid=0;first=None
    for targets in itertools.product(*domains):
        assignment=[p['bank']for p in pieces]
        for i,b in zip(moving,targets):assignment[i]=b
        required={}
        for i,b in enumerate(assignment):
            for y,cs in rows[i].items():required.setdefault((y,b),set()).update(cs)
        if any(len(cs)>15 for cs in required.values()):continue
        valid+=1
        if first is None:first=assignment
    report['valid_assignments']=valid
    if first is None:return dict(report,status='FIXED_GEOMETRY_BANK_RESERVATION_INFEASIBLE')
    for p in pieces:p['allowed_banks']=[b for b in p.get('allowed_banks',range(8))if b not in reserved_banks]
    expanded=[dict(p,source_piece=i,rows=rows[i])for i,p in enumerate(pieces)]
    result=rebuild_schedule(source,dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',
        pieces=expanded,assignment=first,pixel_word_identities_replayed=True),lookahead)
    report['status']='RESERVED_BANK_ROW_CAPACITY_AND_SOURCE_IDENTITIES_PROVEN'
    result['bank_reservation']=report
    return result


def main():
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--reserve',type=int,nargs='+',required=True)
    p.add_argument('--maximum-assignments',type=int,default=100000);p.add_argument('--lookahead',type=int,default=17)
    a=p.parse_args();r=reserve(json.loads(a.schedule.read_text()),a.reserve,a.maximum_assignments,a.lookahead)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('bank_reservation',r)))


if __name__=='__main__':main()
