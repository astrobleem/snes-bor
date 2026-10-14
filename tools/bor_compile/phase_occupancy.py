"""Source-phase tile-occupancy preflight for BYOR MOTU's opaque one-actor renderer.

This is a REFERENCE/GENERATOR, not native runtime code.  It consumes the existing
ASTRA_OPAQUE_PHASE_ASSETS_V1 format (6 little-endian u16s per [row, tile column]:
coverage duplicated in both bytes, then five packed bitplane words).

The occupancy table is a CONSERVATIVE source-coverage oracle; foreground
occlusion remains the responsibility of the existing native row composer.
No artwork or colors are changed, and no screen-position bitmaps are stored.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import json
import struct


@lru_cache(maxsize=64)
def compile_mask_rows(raw: bytes, *, rows: int, row_stride: int):
    if type(rows) is not int or rows < 0 or not isinstance(row_stride,int) or row_stride < 0 or row_stride % 12:
        raise ValueError("PHASE_GEOMETRY")
    cols = row_stride // 12
    if len(raw) != rows * row_stride:
        raise ValueError("PHASE_DATA_LENGTH")
    masks = [bytearray(cols) for _ in range(rows)]
    for y in range(rows):
        for col in range(cols):
            mask = struct.unpack_from('<H', raw, y*row_stride+col*12)[0]
            if (mask&255) != (mask >> 8):
                raise ValueError("PHASE_MASK_NOT_DUPLICATED")
            masks[y][col] = mask&255
    return masks


def compile_occupancy(raw:bytes,*,rows:int,row_stride:int):
    """8 vertical phases, fixed-size padded rows; [q][relative_ty][relative_tx].

    Actor origin X phase is already selected by the original 8 horizontal
    phase atlas. q = (cropped actor origin Y)&7. Relative tile row and column
    are measured from floor(cropped source origin/8), INCLUDING negative origin.
    The byte is the OR of its source coverage masks, so nonzero iff ANY source
    pixel intersects that screen tile. Foreground is intentionally ignored.
    """
    masks=compile_mask_rows(raw,rows=rows,row_stride=row_stride)
    cols=row_stride//12
    maxrows=(rows+14)//8  # max q=7: ceil((rows+7)/8)
    output=bytearray(8*maxrows*cols)
    for q in range(8):
        for rel_ty in range(maxrows):
            lo=max(0,rel_ty*8-q)
            hi=min(rows,(rel_ty+1)*8-q)
            for tx in range(cols):
                cover=0
                for sy in range(lo,hi):
                    cover |= masks[sy][tx]
                output[(q*maxrows+rel_ty)*cols+tx]=cover
    return bytes(output), dict(cols=cols, tile_rows=maxrows,phase_y_count=8,
                               byte_stride=cols,bytes=len(output),
                               maximum_source_occupied_tiles=max(sum(v!=0 for v in output[q*maxrows*cols:(q+1)*maxrows*cols]) for q in range(8)))


def tile_maybe_covered(table:bytes,geometry:dict,*,origin_x:int,origin_y:int,screen_tx:int,screen_ty:int):
    """Exact source-presence yes/no for legal 8x8 screen tile; no FG applied."""
    sx=screen_tx-(origin_x//8)
    sy=screen_ty-(origin_y//8)
    if sx<0 or sy<0 or sx>=geometry['cols'] or sy>=geometry['tile_rows']:
        return False
    q=origin_y&7
    return table[(q*geometry['tile_rows']+sy)*geometry['cols']+sx]!=0


def slow_from_phase_masks(raw:bytes,*,rows:int,row_stride:int,
                          origin_x:int,origin_y:int,screen_tx:int,screen_ty:int):
    """Independent per-pixel coverage reference for an *already selected* X phase."""
    masks=compile_mask_rows(raw,rows=rows,row_stride=row_stride)
    cols=row_stride//12
    for py in range(screen_ty*8,screen_ty*8+8):
        sy=py-origin_y
        if not 0<=sy<rows:continue
        for px in range(screen_tx*8,screen_tx*8+8):
            sc=px-(origin_x//8)*8
            if sc<0 or sc>=cols*8:continue
            tilecol=sc//8
            bit=7-sc%8
            if masks[sy][tilecol]&(1<<bit):return True
    return False


def export(source:Path,output:Path,*,capacity:int=768):
    """Read assets only, write into a NEW directory, enforce source-bound capacity."""
    if output.exists():raise ValueError("OUTPUT_MUST_BE_NEW")
    manifest=json.loads((source/'manifest.json').read_text())
    if manifest.get('schema') != 'ASTRA_OPAQUE_PHASE_ASSETS_V1':
        raise ValueError("WRONG_PHASE_MANIFEST")
    result={'schema':'ASTRA_CONSERVATIVE_COVERAGE_V1','source_manifest_sha256':
            hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
            'backdrop_tiles':manifest['backdrop_tiles'],'capacity':capacity,
            'frames':{},'native_timed':False,'native_integrated':False}
    products=[]
    for role,frame in manifest['frames'].items():
        out=[]
        if len(frame['phases'])!=8:raise ValueError("HORIZONTAL_PHASE_COUNT")
        for entry in frame['phases']:
            phase=entry['phase'];path=source/entry['path'];raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:
                raise ValueError("INPUT_ASSET_CHANGED:"+role+':'+str(phase))
            table,g=compile_occupancy(raw,rows=entry['row_count'],row_stride=entry['row_stride'])
            filename=f'{role}-x{phase}.occupancy';products.append((filename,table))
            out.append(dict(x_phase=phase,filename=filename,sha256=hashlib.sha256(table).hexdigest(),**g))
        if sorted(e['x_phase'] for e in out)!=list(range(8)):
            raise ValueError("HORIZONTAL_PHASE_IDENTITIES")
        result['frames'][role]={'x_phases':out,'maximum_source_occupied_tiles':max(e['maximum_source_occupied_tiles'] for e in out)}
    result['worst_source_occupied_tiles']=max(v['maximum_source_occupied_tiles'] for v in result['frames'].values())
    result['maximum_required_pairs']=result['backdrop_tiles']+result['worst_source_occupied_tiles']
    if result['maximum_required_pairs']>capacity:raise ValueError("CONSERVATIVE_SOURCE_OCCUPANCY_EXCEEDS_CAPACITY")
    result['table_bytes']=sum(len(b) for _,b in products)
    output.mkdir(parents=True)
    for name,payload in products:(output/name).write_bytes(payload)
    (output/'occupancy-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phases',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(export(args.phases,args.output),indent=2))


if __name__=='__main__':main()
