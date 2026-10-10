"""Optimistic OBJ sliver bounds for exact visible pixels in a specified scene.

Each source actor retains ownership of its pieces. Independent row alignment,
arbitrary masks, any legal width and free palette assignment are granted. This
does not prove pose reachability or reject a renderer that merges actor pixels.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from compiler import Source
from source_scene_obj_raster import prepare
from source_bg_feasibility import rgb555


def cover_eight(points):
    """Minimum width-eight intervals covering integer pixel coordinates."""
    count=0;end=-1
    for x in sorted(set(map(int,points))):
        if x>end:count+=1;end=x+7
    return count


def bound(actors,height,width):
    trace=[]
    for y in range(height):
        rows=[];union=[]
        for actor in actors:
            local=y-actor['top'];points=[]
            if 0<=local<actor['pixels'].shape[0]:points=[actor['left']+int(x)for x in np.flatnonzero(actor['pixels'][local]>=0)if 0<=actor['left']+int(x)<width]
            rows.append(cover_eight(points));union.extend(points)
        trace.append(dict(scanline=y,actor_tile_lower_bounds=rows,actor_owned_tile_lower_bound=sum(rows),merged_pixels_tile_lower_bound=cover_eight(union),maximum_width_sprite_lower_bound=sum((v+7)//8 for v in rows)))
    peak=max(r['actor_owned_tile_lower_bound']for r in trace)
    return dict(peak_actor_owned_tile_lower_bound=peak,worst_scanlines=[r['scanline']for r in trace if r['actor_owned_tile_lower_bound']==peak],actor_owned_geometry_rejected=peak>34,trace=trace)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();scene=json.loads(a.scene.read_text());actors,metadata,pixels=prepare(Source(a.source),a.stage,scene);r=bound(actors,*pixels.shape[:2]);r.update(schema='BYOR_SCENE_OBJ_PIXEL_SLIVER_LOWER_BOUND_V1',source_scene=scene,metadata=metadata,source_rgb555_sha256=hashlib.sha256(rgb555(pixels).astype('<u2').tobytes()).hexdigest(),actor_piece_ownership_required=True,source_pose_reachability_proven=False,universal_raster_rejected=False,no_color_reduction=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k in ('peak_actor_owned_tile_lower_bound','worst_scanlines','actor_owned_geometry_rejected')}))


if __name__=='__main__':main()
