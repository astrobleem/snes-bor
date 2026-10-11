"""Bounded fixed-piece bank refinement using validated cache LP scores.

Every proposed assignment preserves exact words, geometry and math classes.
Improving a necessary bound does not prove physical transfer feasibility.
"""
import argparse,copy,json,random,time
from pathlib import Path
from raster_bank_rebalance import rebalance
from raster_bank_residency import relaxed_bound


def refine(source,lookahead=55,maximum_trials=24,time_limit=60,seed=224,dual_guidance=False,include_swaps=False):
    if maximum_trials<0 or time_limit<=0:raise ValueError('LP_REFINE_DOMAIN')
    started=time.monotonic();best=copy.deepcopy(source)
    base=relaxed_bound(best,lookahead,min(10,time_limit),include_dual_pressure=dual_guidance)
    if base['status']!='FRACTIONAL_FIXED_BANK_CACHE_LOWER_BOUND':raise ValueError('LP_REFINE_INITIAL_BOUND_UNAVAILABLE')
    bound=initial=base['validated_dual_lower_bound'];trials=[];rng=random.Random(seed)
    additive=source.get('color_math','additive')!='precomposited'
    proposals=[]
    for i,p in enumerate(source['pieces']):
        banks=range(4*(p['bank']//4),4*(p['bank']//4)+4)if additive else range(8)
        proposals.extend(((i,b),)for b in banks if b!=p['bank']and b in p.get('allowed_banks',range(8)))
    if include_swaps:
        for i,p in enumerate(source['pieces']):
            for j,q in enumerate(source['pieces'][:i]):
                if p['bank']!=q['bank']and(not additive or p['bank']//4==q['bank']//4)and q['bank']in p.get('allowed_banks',range(8))and p['bank']in q.get('allowed_banks',range(8)):
                    proposals.append(((i,q['bank']),(j,p['bank'])))
    rng.shuffle(proposals)
    pressure={(e['bank'],e['scanline']):abs(e['marginal'])for e in base.get('dual_active_bank_capacity',[])}
    if dual_guidance:
        def weight(proposal):
            return sum(sum(pressure.get((source['pieces'][i]['bank'],int(y)),0)for y,colors in source['pieces'][i].get('rows',{}).items()if colors)for i,b in proposal)
        proposals.sort(key=weight,reverse=True)
    for proposal in proposals[:maximum_trials]:
        remaining=time_limit-(time.monotonic()-started)
        if remaining<1:break
        assignment=[p['bank']for p in best['pieces']]
        if all(assignment[i]==b for i,b in proposal):continue
        for i,b in proposal:assignment[i]=b
        try:candidate=rebalance(best,lookahead,maximum_moves=0,maximum_interval=1,initial_assignment=assignment)
        except ValueError as error:
            if str(error)!='BANK_REBALANCE_INPUT_ROW_CAPACITY':raise
            trials.append(dict(proposal=list(proposal),status='ROW_CAPACITY_REJECTED'));continue
        result=relaxed_bound(candidate,lookahead,min(10,remaining))
        entry=dict(proposal=list(proposal),bound=result,accepted=False);trials.append(entry)
        if result['status']=='FRACTIONAL_FIXED_BANK_CACHE_LOWER_BOUND'and result['validated_dual_lower_bound']<bound-1e-6:
            best=candidate;bound=result['validated_dual_lower_bound'];entry['accepted']=True
    best['bank_lp_refinement']=dict(schema='BYOR_FIXED_BANK_LP_REFINEMENT_V1',initial_validated_lower_bound=initial,
        final_validated_lower_bound=bound,seed=seed,maximum_trials=maximum_trials,trials=trials,dual_guidance=dual_guidance,swap_proposals=include_swaps,initial_dual_pressure=base if dual_guidance else None,
        seconds=time.monotonic()-started,source_pixel_identity_preserved=True,geometry_unchanged=True,
        lower_bound_only=True,physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False)
    return best


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--dual-guidance',action='store_true');p.add_argument('--include-swaps',action='store_true')
    p.add_argument('--lookahead',type=int,default=55);p.add_argument('--maximum-trials',type=int,default=24)
    p.add_argument('--time-limit',type=float,default=60);p.add_argument('--seed',type=int,default=224)
    a=p.parse_args();result=refine(json.loads(a.schedule.read_text()),a.lookahead,a.maximum_trials,a.time_limit,a.seed,a.dual_guidance,a.include_swaps)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    r=result['bank_lp_refinement'];print(json.dumps({k:v for k,v in r.items()if k not in ('trials','initial_dual_pressure')}|dict(trials_evaluated=len(r['trials']),accepted=sum(t.get('accepted',False)for t in r['trials']))))


if __name__=='__main__':main()
