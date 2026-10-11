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


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pieces',type=int,nargs='+',required=True)
    a=p.parse_args();result=subdivide(json.loads(a.schedule.read_text()),a.pieces);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('selective_piece_subdivision',result)))


if __name__=='__main__':main()
