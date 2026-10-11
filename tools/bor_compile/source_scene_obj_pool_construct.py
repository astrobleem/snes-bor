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


def select_words(requirements,preferences=None):
    """Greedy exact set cover, with stable deterministic tie breaking."""
    pending=set(range(len(requirements)));owners={};selected=[]
    covers={}
    for i,options in enumerate(requirements):
        if not options:raise ValueError('POOL_CONSTRUCT_PIXEL_WITHOUT_EXACT_WORD')
        for word in options:covers.setdefault(word,set()).add(i)
    while pending:
        word=max((w for w in covers if covers[w]&pending),key=lambda w:((preferences or {}).get(w,0),len(covers[w]&pending),-w[0],-w[1]))
        owned=covers[word]&pending
        if not owned:raise AssertionError('POOL_CONSTRUCT_COVER_PROGRESS')
        selected.append(word)
        for i in owned:owners[i]=word
        pending-=owned
    return owners,selected


def construct(source,stage,scene,candidate,time_limit=30,lookahead=17,prefer_resident_words=False,frame_word_cover=False,bank_residency_window_lines=None,joint_bank_geometry=False,persistent_word_indices=False):
    if frame_word_cover and prefer_resident_words:raise ValueError('POOL_CONSTRUCT_FRAME_AND_RESIDENT_POLICY_CONFLICT')
    if persistent_word_indices and not joint_bank_geometry:raise ValueError('POOL_CONSTRUCT_FIXED_INDICES_REQUIRE_JOINT')
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
    counts=[];global_owners={}
    if frame_word_cover:
        flat=[options for line in requirements for options in line]
        owners,_=select_words(flat)if flat else({},[])
        offset=0
        for y,line in enumerate(requirements):
            global_owners[y]={i:owners[offset+i]for i in range(len(line))};offset+=len(line)
    for y,line in enumerate(requirements):
        previous=states.get(y-1,{})
        preferences={(k,c):1 for k,colors in previous.items()for c in colors}if prefer_resident_words else None
        if frame_word_cover:
            owners=global_owners[y];words=sorted(set(owners.values()))
        else:owners,words=select_words(line,preferences)if line else({},[])
        counts.append([sum(k==kind for k,c in words)for kind in range(2)])
        for j,(i,ly,lx)in enumerate(coordinates[y]):
            k,c=owners[j];canvases[k][i][ly,lx]=c
    report=dict(schema='BYOR_SOURCE_POOL_FIXED_BANK_CONSTRUCTION_V1',status='BOUNDED_POOL_CONSTRUCTION_NO_BANK_ASSIGNMENT',
        source_rgb555_sha256=digest,metadata=metadata,no_color_reduction=True,universal_raster_rejected=False,
        native_presentation_proven=False,operand_selection_policy='GREEDY_EXACT_FRAME_SET_COVER'if frame_word_cover else'GREEDY_EXACT_ROW_SET_COVER_PREFER_RESIDENT'if prefer_resident_words else'GREEDY_EXACT_ROW_SET_COVER',
        outside_control_rows_math_policy='FULL_ADD_NO_WINDOW_MINIMAL_OPERAND_OR_LITERAL',
        peak_selected_colors_by_class=[max(row[k]for row in counts)for k in range(2)],
        global_color_bank_identity_restricted=True,bank_search=[],exact_underlay_bypass=True,underlay_bypassed_pixels=bypassed)
    pieces=[];assignment=[];joint_cells=[]
    for k in range(2):
        cells=[]
        for i,a in enumerate(actors):
            for p in pieces_for_grid(canvases[k][i],(8,8)):
                p.update(actor=i,local_x=p['x'],local_y=p['y'])
                p['x']+=a['left'];p['y']+=a['top'];p['rows']={y+a['top']:cs for y,cs in p['rows'].items()if cs and 0<=y+a['top']<len(background)}
                cells.append(p)
        if not cells:continue
        if joint_bank_geometry:
            joint_cells.extend(dict(p,allowed_banks=list(range(k*4,k*4+4)))for p in cells);continue
        search=split_color_masks(cells,tuple(range(k*4,k*4+4)),time_limit=time_limit,global_color_banks=True,solver_backend='cp-sat',defer_geometry_admission=True,residency_window_lines=bank_residency_window_lines)
        expanded=search.pop('pieces',None);report['bank_search'].append(dict(kind=k,**search))
        if expanded is None:return report
        pieces.extend(expanded);assignment.extend(search['assignment'])
    if joint_bank_geometry:
        from raster_global_bank_classes import assign_masks
        search=assign_masks(joint_cells,time_limit,bank_residency_window_lines,persistent_word_indices=persistent_word_indices)
        pieces=search.pop('pieces',None);report['bank_search'].append(dict(joint_math_classes=True,**search))
        if pieces is None:return report
        assignment=search['assignment']
    if persistent_word_indices:
        from raster_global_bank_classes import fixed_slot_schedule
        trace,palette_states=fixed_slot_schedule(pieces,assignment,search['word_slot_indices'],len(background))
        report['persistent_word_slot_template']=True
    else:trace,palette_states=schedule(pieces,assignment,len(background),lookahead)
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
    p.add_argument('--bank-residency-window-lines',type=int,help='Restricted global bank assignment: every rolling window union must fit fifteen slots per bank.')
    p.add_argument('--frame-word-cover',action='store_true',help='Choose exact words by shared coverage across the full source frame rather than independently per row.')
    p.add_argument('--prefer-resident-words',action='store_true')
    p.add_argument('--joint-bank-geometry',action='store_true',help='Solve both eligible math classes together under the shared 34-sliver limit; defer OAM/sprite admission to compaction.')
    p.add_argument('--persistent-word-indices',action='store_true',help='Restricted joint family assigning each exact word a fixed physical palette index; requires joint bank geometry.')
    a=p.parse_args();r=construct(Source(a.source),a.stage,json.loads(Path(a.scene).read_text()),json.loads(Path(a.candidate).read_text()),a.time_limit,prefer_resident_words=a.prefer_resident_words,frame_word_cover=a.frame_word_cover,bank_residency_window_lines=a.bank_residency_window_lines,joint_bank_geometry=a.joint_bank_geometry,persistent_word_indices=a.persistent_word_indices)
    Path(a.output).write_text(json.dumps(r,indent=2)+'\n')
    summary={k:r[k]for k in ('status','peak_selected_colors_by_class','geometry','hardware_geometry_admitted','peak_scheduled_writes')if k in r}
    summary['bank_search']=[{k:v for k,v in search.items()if k not in('assignment','word_slot_indices')}for search in r['bank_search']]
    print(json.dumps(summary))


if __name__=='__main__':main()
