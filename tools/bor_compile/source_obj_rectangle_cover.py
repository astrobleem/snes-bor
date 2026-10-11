"""Construct legal OBJ geometry before assigning palette banks or operands.

Exact coverage uses nonempty source 8-pixel cells. Larger rectangles may contain
transparent cells. Every selected rectangle counts its full width on every row.
Failure is restricted to this aligned candidate family, never all geometry.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source
from source_scene_obj_raster import prepare
from source_bg_feasibility import rgb555


def cover(actors,time_limit=20,large_size=16,maximum_oam=128,maximum_sprites=32,maximum_tiles=34,objective='oam',origin=(0,0)):
    from ortools.sat.python import cp_model
    if large_size not in (16,32):raise ValueError('RECTANGLE_COVER_LEGAL_SIZE_PAIR')
    if objective not in ('oam','peak_tiles'):raise ValueError('RECTANGLE_COVER_OBJECTIVE')
    if len(origin)!=2 or any(type(v)is not int or not 0<=v<8 for v in origin):raise ValueError('RECTANGLE_COVER_ORIGIN')
    ox,oy=origin
    model=cp_model.CpModel();pieces=[];variables=[];owners={};rows={}
    for i,actor in enumerate(actors):
        pixels=actor['pixels'];occupied={((int(x)-ox)//8,(int(y)-oy)//8)for y,x in zip(*np.where(pixels>=0))}
        candidates={(8,x*8+ox,y*8+oy)for x,y in occupied}
        n=large_size//8
        for x,y in occupied:
            candidates.update((large_size,(x-dx)*8+ox,(y-dy)*8+oy)for dy in range(n)for dx in range(n))
        for size,x,y in sorted(candidates):
            cells={(xx,yy)for xx,yy in occupied if x<=xx*8+ox<x+size and y<=yy*8+oy<y+size}
            if not cells:continue
            sx,sy=x+actor['left'],y+actor['top']
            if not -256<=sx<256 or not -256<=sy<256:continue
            index=len(pieces);var=model.new_bool_var('piece'+str(index));variables.append(var)
            piece=dict(actor=i,local_x=x,local_y=y,x=sx,y=sy,width=size,height=size)
            pieces.append(piece)
            for cell in cells:owners.setdefault((i,*cell),[]).append(var)
            for line in range(max(0,sy),min(224,sy+size)):rows.setdefault(line,[]).append((var,size//8))
    for options in owners.values():model.add(sum(options)==1)
    model.add(sum(variables)<=maximum_oam)
    peak=model.new_int_var(0,maximum_tiles,'peak_tiles')
    for entries in rows.values():
        model.add(sum(v for v,w in entries)<=maximum_sprites)
        model.add(sum(v*w for v,w in entries)<=maximum_tiles)
        model.add(sum(v*w for v,w in entries)<=peak)
    model.minimize(sum(variables)if objective=='oam'else peak*(maximum_oam+1)+sum(variables))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    status=solver.solve(model)
    report=dict(schema='BYOR_SOURCE_ALIGNED_OBJ_RECTANGLE_COVER_V1',status='BOUNDED_RECTANGLE_COVER_NO_CANDIDATE',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,candidate_rectangles=len(pieces),
        obj_size_pair=[8,large_size],objective=objective,origin=list(origin),bank_assignment_proven=False,source_operand_encoding_proven=False,
        native_presentation_proven=False,universal_geometry_rejected=False,no_color_reduction=True)
    if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    selected=[p for p,v in zip(pieces,variables)if solver.value(v)]
    ownership=[np.zeros_like(a['pixels'],dtype=np.uint8)for a in actors]
    for p in selected:
        a=actors[p['actor']];mask=ownership[p['actor']];h,w=mask.shape
        x0,y0=max(0,p['local_x']),max(0,p['local_y']);x1,y1=min(w,p['local_x']+p['width']),min(h,p['local_y']+p['height'])
        mask[y0:y1,x0:x1]+=a['pixels'][y0:y1,x0:x1]>=0
    if any(not np.array_equal(mask,(a['pixels']>=0).astype(np.uint8))for a,mask in zip(actors,ownership)):raise AssertionError('RECTANGLE_COVER_SOURCE_PIXEL_OWNERSHIP')
    geometry=dict(oam_entries=len(selected),peak_sprites=max((sum(p['y']<=y<p['y']+p['height']for p in selected)for y in range(224)),default=0),
        peak_tile_slivers=max((sum(p['width']//8 for p in selected if p['y']<=y<p['y']+p['height'])for y in range(224)),default=0))
    report.update(status='SOURCE_EXACT_OBJ_RECTANGLE_COVER_PROVEN',rectangles=selected,geometry=geometry,source_visible_pixel_ownership_verified=True,
        solver_objective_bound=solver.best_objective_bound,source_pixels_preserved=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--large-size',type=int,choices=(16,32),default=16);p.add_argument('--time-limit',type=float,default=20)
    p.add_argument('--objective',choices=('oam','peak_tiles'),default='oam')
    p.add_argument('--origin',type=int,nargs=2,default=(0,0));p.add_argument('--maximum-tiles',type=int,default=34)
    a=p.parse_args();source=Source(a.source);actors,metadata,expected=prepare(source,a.stage,json.loads(a.scene.read_text()))
    r=cover(actors,a.time_limit,a.large_size,objective=a.objective,origin=tuple(a.origin),maximum_tiles=a.maximum_tiles);r.update(metadata=metadata,source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ('status','solver_status','solver_seconds','geometry')if k in r}))


if __name__=='__main__':main()
