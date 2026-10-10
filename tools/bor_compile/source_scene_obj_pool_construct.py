"""Construct fixed bank masks after greedy exact operand selection.

Restricted global color-bank family, not an infeasibility test for all raster.
All expensive choices are offline; every successful source frame is replayed.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from source_scene_obj_joint import scanline_controls
from source_scene_obj_math import residual
from raster_obj_math_cover import apply_math
from raster_math_windows import evaluate
from raster_palette import pieces_for_grid,split_color_masks,schedule


def select_words(requirements):
    """Greedy exact set cover, with stable deterministic tie breaking."""
    pending=set(range(len(requirements)));owners={};selected=[]
    covers={}
    for i,options in enumerate(requirements):
        if not options:raise ValueError('POOL_CONSTRUCT_PIXEL_WITHOUT_EXACT_WORD')
        for word in options:covers.setdefault(word,set()).add(i)
    while pending:
        word=max(covers,key=lambda w:(len(covers[w]&pending),-w[0],-w[1]))
        owned=covers[word]&pending
        if not owned:raise AssertionError('POOL_CONSTRUCT_COVER_PROGRESS')
        selected.append(word)
        for i in owned:owners[i]=word
        pending-=owned
    return owners,selected


def construct(source,stage,scene,candidate,time_limit=30,lookahead=17):
    actors,metadata,expected=prepare(source,stage,scene)
    background=rgb555(compose_rgb8(source,stage,dict(scene,actors=[]))[0])
    digest=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest()
    modes,windows,states=scanline_controls(candidate,metadata,digest,len(background))
    def enabled(y,x):return y not in windows or evaluate(windows[y],x)
    def render(c,y,x):return apply_math(c,int(background[y,x]),modes.get(y,'add'))if enabled(y,x)else c
    coordinates=[[]for _ in background];requirements=[[]for _ in background];bypassed=0
    for i,a in enumerate(actors):
        for ly,lx in zip(*np.where(a['pixels']>=0)):
            y,x=int(ly+a['top']),int(lx+a['left']);out=int(a['pixels'][ly,lx])
            if out==int(background[y,x]):bypassed+=1;continue
            if y in states:
                options={(0,out)}if out in states[y][0]else set()
                options.update((1,c)for c in states[y][1]if render(c,y,x)==out)
            else:
                options={(0,out)};c=residual(out,int(background[y,x]))
                if c is not None:options.add((1,c))
            coordinates[y].append((i,int(ly),int(lx)));requirements[y].append(options)
    canvases=[[np.full_like(a['pixels'],-1)for a in actors]for _ in range(2)]
    counts=[]
    for y,line in enumerate(requirements):
        owners,words=select_words(line)if line else({},[])
        counts.append([sum(k==kind for k,c in words)for kind in range(2)])
        for j,(i,ly,lx)in enumerate(coordinates[y]):
            k,c=owners[j];canvases[k][i][ly,lx]=c
    report=dict(schema='BYOR_SOURCE_POOL_FIXED_BANK_CONSTRUCTION_V1',status='BOUNDED_POOL_CONSTRUCTION_NO_BANK_ASSIGNMENT',
        source_rgb555_sha256=digest,metadata=metadata,no_color_reduction=True,universal_raster_rejected=False,
        native_presentation_proven=False,operand_selection_policy='GREEDY_EXACT_ROW_SET_COVER',
        outside_control_rows_math_policy='FULL_ADD_NO_WINDOW_MINIMAL_OPERAND_OR_LITERAL',
        peak_selected_colors_by_class=[max(row[k]for row in counts)for k in range(2)],
        global_color_bank_identity_restricted=True,bank_search=[],exact_underlay_bypass=True,underlay_bypassed_pixels=bypassed)
    pieces=[];assignment=[]
    for k in range(2):
        cells=[]
        for i,a in enumerate(actors):
            for p in pieces_for_grid(canvases[k][i],(8,8)):
                p.update(actor=i,local_x=p['x'],local_y=p['y'])
                p['x']+=a['left'];p['y']+=a['top'];p['rows']={y+a['top']:cs for y,cs in p['rows'].items()if cs and 0<=y+a['top']<len(background)}
                cells.append(p)
        if not cells:continue
        search=split_color_masks(cells,tuple(range(k*4,k*4+4)),time_limit=time_limit,global_color_banks=True,solver_backend='cp-sat',defer_geometry_admission=True)
        expanded=search.pop('pieces',None);report['bank_search'].append(dict(kind=k,**search))
        if expanded is None:return report
        pieces.extend(expanded);assignment.extend(search['assignment'])
    trace,palette_states=schedule(pieces,assignment,len(background),lookahead)
    for row in trace:row['resident_before']={b:row['resident_before'].get(b,[None]*15)for b in range(8)}
    replay=background.copy();ownership=np.zeros(background.shape,dtype=np.uint8);images=[]
    compiled=[]
    for p,b in zip(pieces,assignment):
        k=b//4;canvas=canvases[k][p['actor']];a=actors[p['actor']]
        image=np.zeros((8,8),dtype=np.uint8)
        for ly in range(8):
            y=p['y']+ly;ay=y-a['top']
            if not 0<=ay<len(canvas):continue
            for lx in range(8):
                x=p['x']+lx;ax=x-a['left']
                if not 0<=ax<canvas.shape[1]:continue
                c=int(canvas[ay,ax])
                if c<0 or c not in p['rows'].get(y,[]):continue
                if ownership[y,x]:raise AssertionError('POOL_CONSTRUCT_PIXEL_OVERLAP')
                ownership[y,x]=1;slot=palette_states[y][b].index(c)+1;image[ly,lx]=slot
                replay[y,x]=c if k==0 else render(c,y,x)
        flat=image.flatten();images.append(dict(width=8,height=8,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()));compiled.append(dict(p,bank=b))
    if not np.array_equal(replay,rgb555(expected)):raise AssertionError('POOL_CONSTRUCT_SOURCE_PIXEL_IDENTITY')
    if int(ownership.sum())!=sum(map(len,coordinates)):raise AssertionError('POOL_CONSTRUCT_OPAQUE_MASK_IDENTITY')
    geometry=dict(oam_entries=len(pieces),peak_sprites=max(sum(p['y']<=y<p['y']+8 for p in pieces)for y in range(len(background))),peak_tile_slivers=max(sum(p['y']<=y<p['y']+8 for p in pieces)for y in range(len(background))))
    report.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,
        hardware_geometry_admitted=geometry['oam_entries']<=128 and geometry['peak_sprites']<=32 and geometry['peak_tile_slivers']<=34,
        color_math='additive',geometry=geometry,geometry_size=8,pieces=compiled,piece_pixel_masks=images,trace=trace,
        selected_modes={y:modes.get(y,'add')for y in range(len(background))},compiled_color_window_descriptors=windows,
        scanline_math_controls_source_bound=True,window_register_schedule_proven=False,
        peak_scheduled_writes=max(row['colors_written']for row in trace[1:]),lookahead_lines=lookahead)
    if not report['hardware_geometry_admitted']:
        report['status']='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW'
    report['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=compiled,pixel_masks=images,trace=trace,modes=report['selected_modes'],windows=windows),sort_keys=True).encode()).hexdigest()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','stage','scene','candidate','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--time-limit',type=int,default=30)
    a=p.parse_args();r=construct(Source(a.source),a.stage,json.loads(Path(a.scene).read_text()),json.loads(Path(a.candidate).read_text()),a.time_limit)
    Path(a.output).write_text(json.dumps(r,indent=2)+'\n')
    summary={k:r[k]for k in ('status','peak_selected_colors_by_class','geometry','hardware_geometry_admitted','peak_scheduled_writes')if k in r}
    summary['bank_search']=[{k:v for k,v in search.items()if k!='assignment'}for search in r['bank_search']]
    print(json.dumps(summary))


if __name__=='__main__':main()
