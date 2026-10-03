"""Exact transparent-tile cover by the existing SMALL OBJ size.

Overlapping source rectangles repeat identical pixels. They neither crop nor
scale the source. Only the chosen piece origins change; native ABI is unchanged.
"""
import io
import numpy as np
from PIL import Image
from scipy.optimize import milp,Bounds,LinearConstraint


def pack_compact(raw, offset=(0,0)):
    image=Image.open(io.BytesIO(raw));image.load()
    if image.mode!='P':raise ValueError('INDEXED_SINGLE_FRAME_REQUIRED')
    bbox=image.getbbox()
    if not bbox:return dict(pieces=[])
    # An eight-pixel grid is target-format geometry, not a source rescale.
    occupied={(x,y) for y in range(0,image.height,8) for x in range(0,image.width,8)
              if image.crop((x,y,x+8,y+8)).getbbox()}
    candidates={}
    for x,y in occupied:
        for dx in (0,8):
            for dy in (0,8,16,24):
                origin=(x-dx,y-dy)
                cells={(origin[0]+xx,origin[1]+yy) for yy in range(0,32,8) for xx in (0,8)}
                candidates[origin]=cells&occupied
    origins=sorted(candidates);cells=sorted(occupied)
    a=np.array([[cell in candidates[o] for o in origins] for cell in cells],dtype=float)
    costs=np.ones(len(origins))
    result=milp(costs,integrality=costs,bounds=Bounds(0,1),constraints=LinearConstraint(a,1,np.inf),options={'time_limit':10})
    if result.x is None or result.status!=0:raise ValueError('COMPACT_COVER_SEARCH_LIMIT')
    selected=[o for i,o in enumerate(origins) if result.x[i]>.5]
    assert set.union(*(candidates[o] for o in selected))==occupied
    ox,oy=offset
    return dict(pieces=[dict(source_xy=[x,y],size=[16,32],right_xy=[x-ox,y-oy],left_xy=[ox-x-15,y-oy]) for x,y in selected],
                overlap_is_identical_source_pixels=True,solver_status=int(result.status))
