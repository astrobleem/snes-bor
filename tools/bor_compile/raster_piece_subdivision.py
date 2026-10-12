"""Source-exact selective subdivision into legal 8x8 OBJ pieces.

Retains the input bank and palette trace as a replayable optimization hint.
Hardware geometry is checked before any result is admitted. No native claim.
"""
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_bank_rebalance import subdivide as subdivide_geometry


def identities(source):
    return Counter((p['actor'],p['x']+int(x),p['y']+int(y),p['bank'],int(words[y,x]))for p,words in zip(source['pieces'],demand(source)[2])for y,x in zip(*np.where(words>=0)))


def subdivide(source,selected):
    selected=set(selected)
    if any(type(i)is not int or not 0<=i<len(source['pieces'])for i in selected):raise ValueError('SUBDIVISION_PIECE_DOMAIN')
    original=identities(source)
    if any(source['pieces'][i]['width']!=16 or source['pieces'][i]['height']!=16 for i in selected):raise ValueError('SUBDIVISION_LEGAL_16X16_PARENT_REQUIRED')
    if any(p['width']not in(8,16)or p['height']!=p['width']for p in source['pieces']):raise ValueError('SUBDIVISION_OBJ_SIZE_PAIR_REQUIRED')
    result=subdivide_geometry(source,selected,preserve_packets=True,report_limits=True)
    if result.get('status')=='SELECTIVE_SUBDIVISION_HARDWARE_GEOMETRY_LIMIT':return result
    report=dict(schema='BYOR_SELECTIVE_OBJ_SUBDIVISION_V1',selected_parent_pieces=sorted(selected),child_piece_indices=result['bank_subdivision']['child_piece_indices'],geometry=result['geometry'],
                no_color_reduction=True,native_timing_admitted=False,universal_raster_rejected=False)
    for key in('geometry_compaction','bounded_subdivision_search'):
        if key in result:result['input_'+key]=result.pop(key)
    result.update(hardware_geometry_admitted=True,geometry_mode='SOURCE_EXACT_SELECTIVE_8X8_SUBDIVISION',bank_assignment_authority='source_exact_selective_subdivision')
    if identities(result)!=original:raise AssertionError('SUBDIVISION_SOURCE_PIXEL_WORD_BANK_IDENTITY')
    report.update(status='SOURCE_EXACT_SELECTIVE_SUBDIVISION_PROVEN',source_pixel_word_bank_identity_verified=True,opaque_source_pixels=sum(original.values()))
    result['selective_piece_subdivision']=report
    result['input_compiled_schedule_sha256']=source.get('compiled_schedule_sha256')
    return result


def select_for_bank_flexibility(source,maximum_added_entries):
    """Bounded source-only heuristic; bank/cache feasibility remains separate."""
    if type(maximum_added_entries)is not int or not 0<=maximum_added_entries<=127:
        raise ValueError('SUBDIVISION_ADDED_ENTRY_BUDGET')
    _,_,images=demand(source);candidates=[]
    for i,(p,image)in enumerate(zip(source['pieces'],images)):
        if p['width']!=16 or p['height']!=16:continue
        children=[image[y:y+8,x:x+8]for y in(0,8)for x in(0,8)]
        words=[set(map(int,c[c>=0]))for c in children]
        union=set().union(*words);cost=sum(bool(cs)for cs in words)-1
        gain=len(union)-max(map(len,words),default=0)
        candidates.append((gain/max(1,cost),len(union),-cost,i))
    selected=[];result=subdivide(source,[])
    for score,word_count,negative_cost,i in sorted(candidates,reverse=True):
        trial=subdivide(source,selected+[i])
        if trial.get('status')=='SELECTIVE_SUBDIVISION_HARDWARE_GEOMETRY_LIMIT':continue
        if len(trial['pieces'])-len(source['pieces'])>maximum_added_entries:continue
        selected.append(i);result=trial
    result['bounded_subdivision_selection']=dict(
        policy='FRAME_WORD_SPREAD_ACROSS_NONEMPTY_CHILDREN',candidate_parents=len(candidates),
        selected_parent_pieces=selected,maximum_added_entries=maximum_added_entries,
        added_entries=len(result['pieces'])-len(source['pieces']),
        palette_and_transfer_feasibility_proven=False,universal_raster_rejected=False,no_color_reduction=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    selection=p.add_mutually_exclusive_group(required=True);selection.add_argument('--pieces',type=int,nargs='+');selection.add_argument('--maximum-added-entries',type=int)
    a=p.parse_args();source=json.loads(a.schedule.read_text(encoding='utf-8'))
    result=subdivide(source,a.pieces)if a.pieces is not None else select_for_bank_flexibility(source,a.maximum_added_entries)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result.get('bounded_subdivision_selection',result.get('selective_piece_subdivision',result))))


if __name__=='__main__':main()
