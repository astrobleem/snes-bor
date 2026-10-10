"""Joint exact-context pixel encoding, fixed OAM masks and slot residency MILP.

An incumbent is replayed independently. No incumbent is a bounded solver limit,
never universal hardware infeasibility. Native BG/OBJ math routing is unproven.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from compiler import Source
from source_scene_bg import compose_rgb8
from source_scene_obj_raster import prepare
from source_bg_feasibility import rgb555
from source_scene_obj_math import residual, add_rgb555, split_interval_bound
from raster_palette import pieces_for_grid


def probe(source, stage, scene, size=16, write_budget=20, lookahead=16, time_limit=45):
    if size not in (8,16,32) or write_budget<0 or lookahead<0:
        raise ValueError('JOINT_SOLVER_DOMAIN')
    actors, metadata, expected = prepare(source, stage, scene)
    bg, _ = compose_rgb8(source, stage, dict(scene, actors=[])); bg = rgb555(bg)
    height = expected.shape[0]; pieces = []; atoms = []
    for actor_index, actor in enumerate(actors):
        for piece in pieces_for_grid(actor['pixels'], (size, size)):
            i = len(pieces); x0, y0 = piece['x'], piece['y']
            piece.update(actor=actor_index, local_x=x0, local_y=y0, x=x0+actor['left'], y=y0+actor['top'])
            pieces.append(piece)
            for ly in piece['rows']:
                grouped = {}
                for lx in range(x0, min(x0+size, actor['pixels'].shape[1])):
                    output = int(actor['pixels'][ly, lx])
                    if output < 0:
                        continue
                    y, x = ly+actor['top'], lx+actor['left']
                    value = residual(output, int(bg[y, x]))
                    grouped.setdefault((output, value), []).append((y, x))
                for (output, value), pixels in grouped.items():
                    atoms.append(dict(piece=i, line=ly+actor['top'], output=output, residual=value, pixels=pixels))
    variable_count = 0
    def allocate():
        nonlocal variable_count
        result = variable_count; variable_count += 1; return result
    masks = {(i,b):allocate() for i in range(len(pieces)) for b in range(8)}
    choices = {}; uses = {}
    for i, atom in enumerate(atoms):
        for bank in range(8):
            color = atom['output'] if bank < 4 else atom['residual']
            if color is None:
                continue
            choices[i, bank] = allocate()
            uses.setdefault((bank, color), set()).add(atom['line'])
    resident = {(b,c,y):allocate() for (b,c), lines in sorted(uses.items()) for y in range(max(0,min(lines)-lookahead),max(lines)+1)}
    writes = {key:allocate() for key in resident if key[2] > 0}
    rr=[];cc=[];vv=[];lo=[];hi=[]
    def constraint(items, lower, upper):
        row = len(lo)
        for variable, value in items:
            rr.append(row);cc.append(variable);vv.append(value)
        lo.append(lower);hi.append(upper)
    for i, atom in enumerate(atoms):
        options = [(choices[i,b],1) for b in range(8) if (i,b) in choices]
        constraint(options,1,1)
        for bank in range(8):
            if (i,bank) not in choices:
                continue
            color = atom['output'] if bank < 4 else atom['residual']
            variable = choices[i,bank]
            constraint([(variable,1),(masks[atom['piece'],bank],-1)],-np.inf,0)
            constraint([(variable,1),(resident[bank,color,atom['line']],-1)],-np.inf,0)
    constraint([(v,1) for v in masks.values()],0,128)
    for y in range(height):
        active = [(i,b) for i,p in enumerate(pieces) if p['y'] <= y < p['y']+size for b in range(8)]
        constraint([(masks[key],1) for key in active],0,32)
        constraint([(masks[key],size//8) for key in active],0,34)
    bank_lines = {}; write_lines = {}
    for key, variable in resident.items():
        b,c,y = key
        bank_lines.setdefault((b,y),[]).append(variable)
        if y:
            items=[(variable,1),(writes[key],-1)]
            if (b,c,y-1) in resident:
                items.append((resident[b,c,y-1],-1))
            constraint(items,-np.inf,0);write_lines.setdefault(y,[]).append(writes[key])
    for variables in bank_lines.values():
        constraint([(v,1) for v in variables],0,15)
    for variables in write_lines.values():
        constraint([(v,1) for v in variables],0,write_budget)
    objective=np.zeros(variable_count);integrality=np.ones(variable_count)
    for variable in masks.values():objective[variable]=1
    for variable in writes.values():objective[variable]=.001;integrality[variable]=0
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(lo),variable_count)).tocsc()
    result=milp(objective,integrality=integrality,bounds=Bounds(0,1),constraints=LinearConstraint(matrix,lo,hi),options={'time_limit':time_limit,'mip_rel_gap':.05})
    report=dict(schema='BYOR_JOINT_EXACT_CONTEXT_OBJ_MILP_V1',status='BOUNDED_JOINT_SOLVER_NO_CANDIDATE',
                metadata=metadata,geometry_size=size,write_budget=write_budget,lookahead_lines=lookahead,
                solver=dict(status=int(result.status),message=result.message,variables=variable_count,constraints=len(lo)),
                no_color_reduction=True,universal_raster_rejected=False,native_presentation_proven=False,
                source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
                scope='Explicit pose. Exact opaque/additive pixel alternatives and fixed OAM color masks on one legal grid. No native layer routing, source reachability or hardware bandwidth admission.')
    if result.x is None:
        return report
    chosen = {}
    demand=[{b:set() for b in range(8)} for _ in range(height)]
    expanded={}
    for i, atom in enumerate(atoms):
        banks=[b for b in range(8) if (i,b) in choices and result.x[choices[i,b]]>.5]
        if len(banks)!=1:
            raise AssertionError('JOINT_ATOM_BANK_FAULT')
        b=banks[0];c=atom['output'] if b<4 else atom['residual'];chosen[i]=b
        demand[atom['line']][b].add(c)
        expanded.setdefault((atom['piece'],b),{}).setdefault(atom['line'],set()).add(c)
    selected=[dict(pieces[i],rows={y:sorted(colors) for y,colors in rows.items()},bank=b) for (i,b),rows in sorted(expanded.items())]
    geometry=dict(oam_entries=len(selected),peak_sprites=max(sum(p['y']<=y<p['y']+size for p in selected) for y in range(height)),peak_tile_slivers=max(sum(size//8 for p in selected if p['y']<=y<p['y']+size) for y in range(height)))
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:
        raise AssertionError('JOINT_GEOMETRY_LIMIT_FAULT')
    wanted=[{b:set() for b in range(8)} for _ in range(height)]
    for (b,c,y),variable in resident.items():
        if result.x[variable]>.5:wanted[y][b].add(c)
    slots={b:[None]*15 for b in range(8)};states=[];trace=[]
    for y in range(height):
        before={b:list(values) for b,values in slots.items()};events=[]
        for b in range(8):
            if len(wanted[y][b])>15 or not demand[y][b] <= wanted[y][b]:
                raise AssertionError('JOINT_RESIDENCY_FAULT')
            for color in sorted(wanted[y][b]-set(slots[b])):
                at=next(i for i,c in enumerate(slots[b]) if c not in wanted[y][b])
                events.append(dict(bank=b,slot=at+1,old=slots[b][at],color=color,kind='required' if color in demand[y][b] else 'prefetch'));slots[b][at]=color
        if y and len(events)>write_budget:raise AssertionError('JOINT_WRITE_LIMIT_FAULT')
        states.append({b:list(values) for b,values in slots.items()})
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in values if c is not None and c in slots[b]] for b,values in before.items()},evicted=[e['old'] for e in events if e['old'] is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank'] for e in events})))
    replay=bg.copy();indices=np.zeros((height,256),dtype=np.uint8)
    for i,atom in enumerate(atoms):
        b=chosen[i];color=atom['output'] if b<4 else atom['residual'];slot=states[atom['line']][b].index(color)+1
        for y,x in atom['pixels']:
            indices[y,x]=128+b*16+slot
            replay[y,x]=color if b<4 else add_rgb555(color,int(bg[y,x]))
    if not np.array_equal(replay,rgb555(expected)):raise AssertionError('JOINT_SOURCE_PIXEL_IDENTITY_FAULT')
    groups=[[demand[y][b] for y in range(height)] for b in range(8)]
    report.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',geometry=geometry,pieces=selected,trace=trace,
                  compiled_pixel_identity_verified=True,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
                  peak_scheduled_writes=max(row['colors_written'] for row in trace[1:]),fixed_bank_interval_bound=split_interval_bound(groups,15))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--size',type=int,choices=(8,16,32),default=16)
    p.add_argument('--write-budget',type=int,default=20);p.add_argument('--time-limit',type=int,default=45)
    a=p.parse_args();r=probe(Source(a.source),a.stage,json.loads(a.scene.read_text()),a.size,a.write_budget,time_limit=a.time_limit)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k in ('status','solver','geometry','peak_scheduled_writes')}))


if __name__=='__main__':main()
