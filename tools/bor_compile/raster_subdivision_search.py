"""Bounded source-exact legal OBJ subdivision and fixed-bank search.

Interval demand is a search heuristic, not hardware bandwidth or admission.
All candidates use the same color-math operands and preserve source pixels.
"""
import argparse,json,time
from pathlib import Path
from raster_bank_rebalance import subdivide,rebalance


def search(source,iterations=3,time_limit=100,maximum_moves=8,maximum_interval=16,lookahead=55):
    if iterations<1 or time_limit<=0 or maximum_moves<0 or maximum_interval<1 or lookahead<0:
        raise ValueError('SUBDIVISION_SEARCH_DOMAIN')
    started=time.monotonic()
    best=rebalance(source,lookahead,maximum_moves,maximum_interval,time_limit=time_limit)
    score=tuple(best['bank_rebalance']['final_objective']);initial=score;trials=[];selections=[]
    for iteration in range(iterations):
        chosen=None
        for i,piece in enumerate(best['pieces']):
            if piece['width']<=8:continue
            remaining=time_limit-(time.monotonic()-started)
            if remaining<=0:break
            try:split=subdivide(best,[i])
            except ValueError as e:
                if str(e)not in('BANK_SUBDIVISION_HARDWARE_GEOMETRY_LIMIT','BANK_SUBDIVISION_GLOBAL_SIZE_PAIR'):raise
                trials.append(dict(iteration=iteration,piece=i,status=str(e)));continue
            candidate=rebalance(split,lookahead,maximum_moves,maximum_interval,time_limit=remaining)
            value=tuple(candidate['bank_rebalance']['final_objective'])
            trials.append(dict(iteration=iteration,piece=i,objective=list(value),geometry=candidate['geometry']))
            if value<score and(chosen is None or value<chosen[0]):chosen=(value,candidate,i)
        if chosen is None:break
        score,best,piece=chosen
        entry=dict(iteration=iteration,input_piece=piece,objective=list(score),geometry=best['geometry'])
        selections.append(entry);print(json.dumps(entry),flush=True)
    best['bounded_subdivision_search']=dict(schema='BYOR_BOUNDED_LEGAL_SUBDIVISION_SEARCH_V1',
        seconds=time.monotonic()-started,time_limit_seconds=time_limit,iterations_requested=iterations,
        initial_interval_objective=list(initial),final_interval_objective=list(score),
        selections=selections,trials=trials,source_pixels_exact=True,color_math_operands_unchanged=True,
        physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    return best


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--iterations',type=int,default=3)
    p.add_argument('--time-limit',type=float,default=100);p.add_argument('--maximum-moves',type=int,default=8)
    p.add_argument('--maximum-interval',type=int,default=16);p.add_argument('--lookahead',type=int,default=55)
    a=p.parse_args();result=search(json.loads(a.schedule.read_text()),a.iterations,a.time_limit,a.maximum_moves,a.maximum_interval,a.lookahead)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result['bounded_subdivision_search'].items()if k!='trials'}))


if __name__=='__main__':main()
