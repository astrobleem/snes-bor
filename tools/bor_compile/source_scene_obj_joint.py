"""Joint exact-context pixel encoding, fixed OAM masks and slot residency MILP.

An incumbent is replayed independently. No incumbent is a bounded solver limit,
never universal hardware infeasibility. Native BG/OBJ math routing is unproven.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import milp, linprog, Bounds, LinearConstraint
from scipy.sparse import coo_matrix,vstack
from compiler import Source
from source_scene_bg import compose_rgb8
from source_scene_obj_raster import prepare
from source_bg_feasibility import rgb555
from source_scene_obj_math import residual, add_rgb555, split_interval_bound
from raster_palette import pieces_for_grid
from raster_obj_math_cover import MODES,apply_math,complete_math_cover
from raster_math_windows import evaluate


def scanline_controls(candidate,metadata,pixel_digest,height):
    """Bind saved controls to a source context; uncovered rows explicitly add."""
    if candidate.get('status')!='INTEGER_POOL_SOURCE_REPLAY_PROVEN' or candidate.get('metadata')!=metadata or candidate.get('source_rgb555_sha256')!=pixel_digest or not candidate.get('full_interval_source_pixels_verified') or candidate.get('zero_main_clipping_palette_demand_relaxed'):
        raise ValueError('JOINT_SCANLINE_CONTROL_SOURCE_IDENTITY')
    modes={int(y):m for y,m in candidate['selected_modes'].items()}
    windows={int(y):d for y,d in candidate['compiled_color_window_descriptors'].items()}
    if set(modes)!=set(windows) or any(not 0<=y<height or m not in MODES for y,m in modes.items()):
        raise ValueError('JOINT_SCANLINE_CONTROL_DOMAIN')
    states={int(y):{int(k):set(v)for k,v in state.items()}for y,state in candidate['selected_palette_residency'].items()}
    if any(set(state)!={0,1} or any(len(colors)>60 or any(type(c)is not int or not 0<=c<32768 for c in colors)for colors in state.values())for state in states.values()):
        raise ValueError('JOINT_SCANLINE_CONTROL_PALETTE_DOMAIN')
    if not set(modes)<=set(states):raise ValueError('JOINT_SCANLINE_CONTROL_STATE_DOMAIN')
    # Validate the actual register descriptor, including source-free gaps.
    for descriptor in windows.values():
        bounds=descriptor.get('bounds',[])
        if len(bounds)!=2 or any(len(pair)!=2 or any(type(x)is not int or not 0<=x<=255 for x in pair)for pair in bounds) or descriptor.get('wobjsel_color_bits',0)&~0xf0 or descriptor.get('wobjlog_color_bits')not in(0,4) or descriptor.get('cgwsel_clip_and_prevent_bits')!=0x10:
            raise ValueError('JOINT_SCANLINE_CONTROL_WINDOW_DOMAIN')
    return modes,windows,states


def saturated_corners(output,background):
    """Exact min/max operands for each saturated channel, at most eight words."""
    base=residual(output,background)
    if base is None:return []
    values=[base]
    for shift in (0,5,10):
        if (output>>shift)&31==31:
            values=sorted(set(values+[c|31<<shift for c in values]))
    return values


def hint_ownership(schedule,pieces):
    """Decode fixed source-pixel ownership; never infer it from rectangles."""
    from raster_obj_compact import unpack
    fields=('actor','local_x','local_y','width','height','x','y')
    lookup={tuple(p[f]for f in fields):i for i,p in enumerate(pieces)}
    state={b:[None]*15 for b in range(8)};states=[]
    for row in schedule['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        states.append({b:list(v)for b,v in state.items()})
    owner={};chosen_masks=set()
    for p,image in zip(schedule['pieces'],schedule['piece_pixel_masks']):
        key=tuple(p[f]for f in fields)
        if key not in lookup:raise ValueError('JOINT_SCHEDULE_HINT_GEOMETRY')
        piece_index=lookup[key];bank=p['bank'];chosen_masks.add((piece_index,bank));image=unpack(image)
        for ly,lx in zip(*np.where(image!=0)):
            y,x=int(p['y']+ly),int(p['x']+lx)
            if (y,x)in owner:raise ValueError('JOINT_SCHEDULE_HINT_OVERLAP')
            owner[y,x]=piece_index,bank,states[y][bank][int(image[ly,lx])-1]
    return owner,chosen_masks,states


def fixed_hint_geometry(schedule,actors,bg,math_enabled,legal_sizes):
    """Use validated legal hint rectangles, including offline subdivisions."""
    fields=('actor','local_x','local_y','width','height','x','y')
    pieces=[];seen=set()
    for p in schedule['pieces']:
        key=tuple(p[f]for f in fields)
        if key in seen:continue
        seen.add(key)
        actor_index=p['actor']
        if type(actor_index)is not int or not 0<=actor_index<len(actors):raise ValueError('JOINT_HINT_ACTOR')
        actor=actors[actor_index]
        if p['width']!=p['height']or p['width']not in legal_sizes:raise ValueError('JOINT_HINT_LEGAL_SIZE')
        if p['x']!=actor['left']+p['local_x']or p['y']!=actor['top']+p['local_y']:raise ValueError('JOINT_HINT_SOURCE_COORDINATES')
        pieces.append({f:p[f]for f in fields}|{'rows':{}})
    owner,_,_=hint_ownership(schedule,pieces)
    expected=set();grouped={}
    for actor_index,actor in enumerate(actors):
        for ly,lx in zip(*np.where(actor['pixels']>=0)):
            y,x=int(actor['top']+ly),int(actor['left']+lx)
            if not(0<=y<bg.shape[0]and 0<=x<bg.shape[1]):continue
            expected.add((y,x))
            if (y,x)not in owner:raise ValueError('JOINT_HINT_SOURCE_PIXEL_COVERAGE')
            index,_,_=owner[y,x];piece=pieces[index]
            if piece['actor']!=actor_index:raise ValueError('JOINT_HINT_SOURCE_PIXEL_ACTOR')
            output=int(actor['pixels'][ly,lx]);value=residual(output,int(bg[y,x]))
            piece['rows'].setdefault(int(ly),set()).add(output)
            key=index,y,output,value,int(bg[y,x]),math_enabled(y,x)
            grouped.setdefault(key,[]).append((y,x))
    if expected!=set(owner):raise ValueError('JOINT_HINT_SOURCE_PIXEL_COVERAGE')
    for p in pieces:p['rows']={y:sorted(c)for y,c in p['rows'].items()}
    atoms=[dict(piece=i,options=[i],line=y,output=output,residual=value,pixels=pixels)for(i,y,output,value,_,_),pixels in grouped.items()]
    return pieces,atoms


def probe(source, stage, scene, size=16, write_budget=20, lookahead=16, time_limit=45, relaxed=False, pool_residency=None, clip_horizontal=False, feasibility_only=False, bank_symmetry=False, early_write_budget=None, late_start=75, saturated_reuse=False, pool_only=False, integer_pool_budget=None, align_visible_bounds=False, solver_backend='highs', pin_pool_intervals=False, prepared_dma_window=None, schedule_hint=None, underlay_bypass=False, saturated_extrema=False, complete_additive_cover=False, grid_padding_x=0, grid_padding_y=0, prepared_dma_partition=False, coalesce_opaque_choices=False, color_math="additive", mixed_small_size=8, mixed_large_size=32, additive_only=False,pool_math_modes=None,fixed_geometry=False,maximum_frame_colors_per_bank=None,scanline_math_candidate=None,row_capacity_only=False,coalesce_math_choices=False,fixed_rectangles=False,pin_scanline_pool_intervals=False,pool_interval_bank_copies=1,pool_interval_max_lines=0,maximum_banks_per_piece_class=0,preserve_hint_math_classes=False,preserve_hint_words=False,pool_interval_initial_preload=False,pool_interval_gap_bridge_lines=0,collapse_inactive_prefix=False,rectangle_bank_slack=0,rectangle_cover=None,literal_actor_bank=None,subdivide_rectangle_cover=False,relax_scanline_pool=False):
    if solver_backend not in ('highs','cp-sat') or (relaxed and solver_backend!='highs'):raise ValueError('JOINT_SOLVER_BACKEND')
    if fixed_geometry and fixed_rectangles:raise ValueError('JOINT_FIXED_GEOMETRY_AND_RECTANGLES_CONFLICT')
    if subdivide_rectangle_cover and rectangle_cover is None:raise ValueError('JOINT_SUBDIVISION_REQUIRES_RECTANGLE_COVER')
    if type(rectangle_bank_slack)is not int or not 0<=rectangle_bank_slack<=7 or rectangle_bank_slack and not fixed_rectangles:raise ValueError('JOINT_RECTANGLE_BANK_SLACK_DOMAIN')
    if (fixed_geometry or fixed_rectangles)and(schedule_hint is None or pool_only or(bank_symmetry and fixed_geometry)):raise ValueError('JOINT_FIXED_GEOMETRY_REQUIRES_HINT_WITHOUT_POOL_OR_SYMMETRY')
    if maximum_frame_colors_per_bank is not None and(not isinstance(maximum_frame_colors_per_bank,int)or maximum_frame_colors_per_bank<1 or pool_only or relaxed):raise ValueError('JOINT_FRAME_COLOR_LIMIT_DOMAIN')
    if size not in (8,16,32,'mixed') or write_budget<0 or lookahead<0:
        raise ValueError('JOINT_SOLVER_DOMAIN')
    if mixed_small_size not in (8,16):raise ValueError('JOINT_MIXED_SMALL_SIZE_DOMAIN')
    if (mixed_small_size,mixed_large_size)not in ((8,16),(8,32),(16,32)):raise ValueError('JOINT_MIXED_SIZE_PAIR_DOMAIN')
    if color_math not in ('additive','precomposited','subscreen-additive'):raise ValueError('JOINT_COLOR_MATH_DOMAIN')
    if color_math=='subscreen-additive' and (scanline_math_candidate is not None or pool_math_modes is not None or preserve_hint_math_classes):raise ValueError('JOINT_SUBSCREEN_SHARED_ROUTING_POLICY')
    if additive_only and color_math!='additive':raise ValueError('JOINT_ADDITIVE_ONLY_REQUIRES_ADDITIVE_MATH')
    if pool_math_modes is not None and(not pool_only or color_math!='additive' or integer_pool_budget is not None):raise ValueError('JOINT_MATH_MODES_REQUIRE_RELAXED_POOL_ONLY')
    if scanline_math_candidate is not None and(color_math!='additive' or pool_only or pool_residency or complete_additive_cover or saturated_reuse or saturated_extrema):raise ValueError('JOINT_SCANLINE_CONTROL_POLICY_CONFLICT')
    if pin_scanline_pool_intervals and (scanline_math_candidate is None or pool_residency or row_capacity_only):raise ValueError('JOINT_SCANLINE_INTERVAL_POLICY')
    if type(pool_interval_bank_copies)is not int or not 1<=pool_interval_bank_copies<=4 or(pool_interval_bank_copies!=1 and not pin_scanline_pool_intervals):raise ValueError('JOINT_SCANLINE_INTERVAL_COPIES')
    if type(pool_interval_max_lines)is not int or pool_interval_max_lines<0 or(pool_interval_max_lines and not pin_scanline_pool_intervals):raise ValueError('JOINT_SCANLINE_INTERVAL_LENGTH')
    if type(maximum_banks_per_piece_class)is not int or not 0<=maximum_banks_per_piece_class<=8:raise ValueError('JOINT_PIECE_CLASS_BANK_CAP')
    if (preserve_hint_math_classes or preserve_hint_words)and not(fixed_rectangles or fixed_geometry)or preserve_hint_words and not preserve_hint_math_classes:raise ValueError('JOINT_PRESERVED_HINT_POLICY')
    if pool_interval_initial_preload and not pin_scanline_pool_intervals:raise ValueError('JOINT_INTERVAL_INITIAL_PRELOAD_POLICY')
    if type(pool_interval_gap_bridge_lines)is not int or pool_interval_gap_bridge_lines<0 or(pool_interval_gap_bridge_lines and not pin_scanline_pool_intervals):raise ValueError('JOINT_INTERVAL_GAP_BRIDGE_POLICY')
    if collapse_inactive_prefix and(row_capacity_only or pool_residency or pool_only):raise ValueError('JOINT_INACTIVE_PREFIX_POLICY')
    def kind(bank):return int(color_math=='subscreen-additive' or color_math=='additive' and bank>=4)
    def banks_for_kind(k):return range(4*k,4*k+4) if color_math=='additive' else range(8)
    base_size=mixed_large_size if size=='mixed'else size
    if not all(isinstance(p,int)and 0<=p<base_size for p in (grid_padding_x,grid_padding_y)) or (not align_visible_bounds and (grid_padding_x or grid_padding_y)):
        raise ValueError('JOINT_GRID_PADDING_DOMAIN')
    if pin_pool_intervals and not pool_residency:raise ValueError('JOINT_INTERVAL_PIN_REQUIRES_POOL')
    if prepared_dma_partition and prepared_dma_window is None:raise ValueError('JOINT_DMA_PARTITION_REQUIRES_WINDOW')
    if prepared_dma_window is not None:
        if prepared_dma_window<1:raise ValueError('JOINT_DMA_WINDOW_DOMAIN')
        if bank_symmetry:raise ValueError('JOINT_DMA_BANK_SYMMETRY_UNSAFE')
    if early_write_budget is not None and (early_write_budget < 0 or not 1 <= late_start < 224):
        raise ValueError('JOINT_ROW_BUDGET_DOMAIN')
    if row_capacity_only and(write_budget!=120 or lookahead!=0 or early_write_budget is not None or prepared_dma_window is not None or pool_residency or pin_pool_intervals or schedule_hint):raise ValueError('JOINT_ROW_CAPACITY_ONLY_REQUIRES_UNBOUNDED_NO_PREFETCH')
    def line_budget(y):return early_write_budget if early_write_budget is not None and y < late_start else write_budget
    actors, metadata, expected = prepare(source, stage, scene)
    if literal_actor_bank is not None:
        if type(literal_actor_bank)is not int or not 0<=literal_actor_bank<4 or color_math!='additive' or fixed_geometry or fixed_rectangles or schedule_hint is not None:raise ValueError('JOINT_LITERAL_ACTOR_BANK_POLICY')
        if any('metadata'not in actor for actor in actors):raise ValueError('JOINT_LITERAL_ACTOR_SOURCE_ALPHA_REQUIRED')
    input_geometry_search_hint=schedule_hint is not None and schedule_hint.get('status')=='SOURCE_EXACT_GEOMETRY_SEARCH_HINT'
    if input_geometry_search_hint:
        if not(fixed_geometry or fixed_rectangles):raise ValueError('JOINT_GEOMETRY_SEARCH_HINT_REQUIRES_FIXED_RECTANGLES')
        from raster_slot_greedy import demand as replay_hint
        replay_hint(schedule_hint,allow_geometry_hint=True)
    if schedule_hint is not None and ((solver_backend!='cp-sat' and not(fixed_geometry or fixed_rectangles)) or schedule_hint.get('status')not in('JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN','SOURCE_EXACT_GEOMETRY_SEARCH_HINT') or not schedule_hint.get('compiled_pixel_identity_verified') or schedule_hint.get('metadata')!=metadata or schedule_hint.get('source_rgb555_sha256')!=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest()):
        raise ValueError('JOINT_SCHEDULE_HINT_IDENTITY')
    if schedule_hint is not None and schedule_hint.get('color_math','additive')!=color_math:raise ValueError('JOINT_SCHEDULE_HINT_COLOR_MATH')
    pool=set();pool_first=0
    if pool_residency:
        if pool_residency['metadata']!=metadata or pool_residency['status']!='POOLED_INTEGER_RESIDENCY_CANDIDATE':raise ValueError('JOINT_POOL_CONTEXT_IDENTITY')
        if pool_residency.get('color_math','additive')!=color_math:raise ValueError('JOINT_POOL_COLOR_MATH')
        pool={(e['kind'],e['color'],e['line'])for e in pool_residency['fractional_residency']if e['value']>.5}
        pool_first=min(y for kind,c,y in pool)
    def allowed(bank,color,y):return not pool_residency or (kind(bank),color,max(y,pool_first))in pool
    bg, _ = compose_rgb8(source, stage, dict(scene, actors=[])); bg = rgb555(bg)
    control_modes,control_windows,control_states=scanline_controls(scanline_math_candidate,metadata,hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),len(bg))if scanline_math_candidate is not None else({},{},{})
    if relax_scanline_pool:
        if scanline_math_candidate is None:raise ValueError('JOINT_RELAXED_POOL_REQUIRES_SOURCE_CONTROLS')
        control_states={}
    def math_enabled(y,x):return y not in control_windows or evaluate(control_windows[y],x)
    def render_word(c,y,x):return apply_math(c,int(bg[y,x]),control_modes.get(y,'add'))if math_enabled(y,x)else c
    source_canvases=[list(a['pixels'].shape[::-1])for a in actors];bypassed=0
    if underlay_bypass:
        # Final ownership was already applied by prepare(). A pixel whose
        # final RGB555 value equals the actor-free underlay needs no OBJ draw.
        # Retain source canvases/metadata and independently replay the result.
        actors=[dict(a,pixels=a['pixels'].copy())for a in actors]
        for a in actors:
            ys,xs=np.where(a['pixels']>=0);sy=ys+a['top'];sx=xs+a['left']
            valid=(sy>=0)&(sy<bg.shape[0])&(sx>=0)&(sx<bg.shape[1])
            ys,xs,sy,sx=ys[valid],xs[valid],sy[valid],sx[valid]
            same=a['pixels'][ys,xs]==bg[sy,sx]
            a['pixels'][ys[same],xs[same]]=-1;bypassed+=int(same.sum())
    height = expected.shape[0]; pieces = []; atoms = []
    row_tile_lower_bounds=[0]*height
    for actor in actors:
        for ly,row in enumerate(actor['pixels']):
            y=ly+actor['top']
            if not 0<=y<height:continue
            end=-1000
            for lx in np.where(row>=0)[0]:
                x=int(lx+actor['left'])
                if x>end:row_tile_lower_bounds[y]+=1;end=x+7
    def slivers(piece):
        width=piece['width']
        if not clip_horizontal:return width//8
        x=piece['x']
        if x==-256:return width//8
        return sum(x+column*8+8>0 and x+column*8<256 for column in range(width//8))
    for actor_index, actor in enumerate([]if fixed_geometry or fixed_rectangles or rectangle_cover is not None else actors):
        base_size=mixed_large_size if size=='mixed'else size
        surface=actor['pixels'];origin_x=origin_y=0
        if align_visible_bounds:
            ys,xs=np.where(surface>=0)
            if not len(xs):continue
            origin_x=max(0,int(xs.min())-grid_padding_x)
            origin_y=max(0,int(ys.min())-grid_padding_y)
            surface=surface[origin_y:int(ys.max())+1,origin_x:int(xs.max())+1]
        for piece in pieces_for_grid(surface, (base_size, base_size)):
            piece['x']+=origin_x;piece['y']+=origin_y
            piece['rows']={y+origin_y:colors for y,colors in piece['rows'].items()}
            i = len(pieces); x0, y0 = piece['x'], piece['y']
            piece.update(actor=actor_index, local_x=x0, local_y=y0, x=x0+actor['left'], y=y0+actor['top'])
            pieces.append(piece)
            blocks=[(i,piece)]
            if size=='mixed':
                blocks=[]
                for child in pieces_for_grid(actor['pixels'][y0:y0+mixed_large_size,x0:x0+mixed_large_size],(mixed_small_size,mixed_small_size)):
                    cx,cy=x0+child['x'],y0+child['y']
                    child.update(actor=actor_index,local_x=cx,local_y=cy,x=cx+actor['left'],y=cy+actor['top'],rows={yy+y0:colors for yy,colors in child['rows'].items()})
                    index=len(pieces);pieces.append(child);blocks.append((index,child))
            for block_index,block in blocks:
             for ly in block['rows']:
                grouped = {}
                for lx in range(block['local_x'], min(block['local_x']+block['width'], actor['pixels'].shape[1])):
                    output = int(actor['pixels'][ly, lx])
                    if output < 0:
                        continue
                    y, x = ly+actor['top'], lx+actor['left']
                    value = residual(output, int(bg[y, x]))
                    grouped.setdefault((output,value,int(bg[y,x]),math_enabled(y,x))if scanline_math_candidate is not None else(output,value), []).append((y,x))
                for key,pixels in grouped.items():
                    output,value=key[:2]
                    atoms.append(dict(piece=block_index,options=[i,block_index]if size=='mixed'else[i],line=ly+actor['top'], output=output, residual=value, pixels=pixels))
    if rectangle_cover is not None:
        if fixed_geometry or fixed_rectangles or schedule_hint is not None or rectangle_cover.get('status')!='SOURCE_EXACT_OBJ_RECTANGLE_COVER_PROVEN' or rectangle_cover.get('metadata')!=metadata or rectangle_cover.get('source_rgb555_sha256')!=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest():raise ValueError('JOINT_RECTANGLE_COVER_SOURCE_IDENTITY')
        legal_sizes=(mixed_small_size,mixed_large_size)if size=='mixed'else(size,)
        ownership=[np.zeros_like(a['pixels'],dtype=np.uint8)for a in actors]
        if subdivide_rectangle_cover and(size!='mixed' or mixed_small_size!=8):raise ValueError('JOINT_RECTANGLE_SUBDIVISION_SIZE_PAIR')
        for p in rectangle_cover['rectangles']:
            p=dict(p);actor=actors[p['actor']];x0,y0=p['local_x'],p['local_y']
            if p['width']!=p['height']or p['width']not in legal_sizes or p['x']!=x0+actor['left']or p['y']!=y0+actor['top']:raise ValueError('JOINT_RECTANGLE_COVER_GEOMETRY')
            i=len(pieces);pieces.append(p);children={}
            if subdivide_rectangle_cover and p['width']>8:
                for dy in range(0,p['height'],8):
                    for dx in range(0,p['width'],8):
                        children[dx//8,dy//8]=len(pieces)
                        pieces.append(dict(p,local_x=x0+dx,local_y=y0+dy,x=p['x']+dx,y=p['y']+dy,width=8,height=8))
            for ly in range(max(0,y0),min(actor['pixels'].shape[0],y0+p['height'])):
                grouped={}
                for lx in range(max(0,x0),min(actor['pixels'].shape[1],x0+p['width'])):
                    output=int(actor['pixels'][ly,lx])
                    if output<0:continue
                    ownership[p['actor']][ly,lx]+=1;y,x=ly+actor['top'],lx+actor['left'];value=residual(output,int(bg[y,x]))
                    child=children.get(((lx-x0)//8,(ly-y0)//8),i)
                    grouped.setdefault((output,value,child,int(bg[y,x]),math_enabled(y,x))if scanline_math_candidate is not None else(output,value,child),[]).append((y,x))
                for key,pixels in grouped.items():atoms.append(dict(piece=key[2],options=[i,key[2]]if key[2]!=i else[i],line=ly+actor['top'],output=key[0],residual=key[1],pixels=pixels))
        if any(not np.array_equal(mask,(a['pixels']>=0).astype(np.uint8))for a,mask in zip(actors,ownership)):raise ValueError('JOINT_RECTANGLE_COVER_PIXEL_OWNERSHIP')
    if fixed_geometry or fixed_rectangles:
        pieces,atoms=fixed_hint_geometry(schedule_hint,actors,bg,math_enabled,(mixed_small_size,mixed_large_size)if size=='mixed'else(size,))
    if literal_actor_bank is not None:
        for piece in pieces:
            if actors[piece['actor']]['metadata']['alpha']==0:piece['allowed_banks']=[literal_actor_bank]
        for atom in atoms:
            if actors[pieces[atom['piece']]['actor']]['metadata']['alpha']==0:atom['literal_bank']=literal_actor_bank
    residual_corpus={a['residual'] for a in atoms if a['residual'] is not None}
    if saturated_extrema:
        for a in atoms:
            y,x=a['pixels'][0];residual_corpus.update(saturated_corners(a['output'],int(bg[y,x])))
    residual_corpus=sorted(residual_corpus)
    complete_options={};complete_cover_report=None
    if complete_additive_cover and color_math in('additive','subscreen-additive'):
        from raster_additive_cover import complete_cover
        complete_options,complete_cover_report=complete_cover((a["output"],a["residual"])for a in atoms)
        residual_corpus=sorted({c for values in complete_options.values()for c in values})
    control_cover=None;control_options={}
    if scanline_math_candidate is not None:
        requirements=[(a['output'],int(bg[y,x]),math_enabled(y,x))for a in atoms for y,x in a['pixels']if y not in control_states]
        if requirements:
            outside_modes=tuple(dict.fromkeys(control_modes.get(a['line'],'add')for a in atoms if a['line']not in control_states))
            control_options,control_cover=complete_math_cover(requirements,modes=outside_modes,tag_modes=True,fixed_window_context=True)
    alternative_cache={}
    for atom in atoms:
        values=[] if atom['residual'] is None or color_math=='precomposited' else [atom['residual']]
        if complete_additive_cover and values:
            values=complete_options[atom['output'],atom['residual']]
        elif (saturated_reuse or saturated_extrema) and values:
            y,x=atom['pixels'][0];background=int(bg[y,x]);key=(atom['output'],background)
            if key not in alternative_cache:
                alternative_cache[key]=[c for c in residual_corpus if add_rgb555(c,background)==atom['output']]
            values=alternative_cache[key]
        if scanline_math_candidate is not None:
            y,x=atom['pixels'][0]
            values=sorted(c for c in control_states[y][1]if render_word(c,y,x)==atom['output'])if y in control_states else control_options[control_modes.get(y,'add'),atom['output'],int(bg[y,x]),math_enabled(y,x)]
            if y in control_states and atom['output']not in control_states[y][0]and not values:
                raise ValueError('JOINT_SCANLINE_CONTROL_SOURCE_PIXEL_COVERAGE')
        atom['residual_options']=values
    if pool_only:
        from raster_palette_cover_liveness import lower_bound
        rows=[set() for _ in range(height)]
        for atom in atoms:rows[atom['line']].add((atom['output'],tuple(atom['residual_options'])))
        math_cover_report=None
        if pool_math_modes is not None:
            requirements={(atom['output'],int(bg[y,x]))for atom in atoms for y,x in atom['pixels']}
            math_options,math_cover_report=complete_math_cover(requirements,pool_math_modes)
            rows=[set()for _ in range(height)]
            for atom in atoms:
                for y,x in atom['pixels']:rows[y].add((atom['output'],tuple(math_options[atom['output'],int(bg[y,x])])))
        result=lower_bound(rows,capacities=(0,120)if color_math=='subscreen-additive'else(0,60)if additive_only else(120,60)if color_math=='precomposited'else(60,60),time_limit=time_limit,include_solution=True,integer_budget=integer_pool_budget)
        output_sets=[{normal for normal,additive in row}for row in rows]
        result.update(visible_final_obj_output_full_frame_colors=len(set().union(*output_sets)),
                      peak_visible_final_obj_output_colors_per_scanline=max(map(len,output_sets),default=0),
                      final_output_counts_apply_source_alpha_and_occlusion=True,
                      final_output_counts_exclude_exact_underlay_bypass_pixels=underlay_bypass)
        result.update(additive_only=additive_only,opaque_obj_banks_reserved=4 if additive_only else 0,color_math=color_math,complete_additive_cover=complete_cover_report,metadata=metadata,saturated_reuse=saturated_reuse,saturated_extrema=saturated_extrema,exact_underlay_bypass=underlay_bypass,underlay_bypassed_pixels=bypassed,source_actor_canvases=source_canvases,no_color_reduction=True,native_presentation_proven=False,
                      source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest())
        if pool_math_modes is not None:result.update(color_math='RELAXED_POOL_MATH_MODES',complete_obj_math_cover=math_cover_report,global_math_mode_constraints_relaxed=len(set(pool_math_modes))>1)
        return result
    owner,chosen_masks,hint_states=hint_ownership(schedule_hint,pieces)if schedule_hint is not None else({},set(),[])
    if fixed_geometry or fixed_rectangles:
        from raster_obj_compact import unpack
        pixel_allowed={}
        for p,m in zip(schedule_hint['pieces'],schedule_hint['piece_pixel_masks']):
            for ly,lx in zip(*np.where(unpack(m)!=0)):pixel_allowed[int(p['y']+ly),int(p['x']+lx)]=tuple(p.get('allowed_banks',range(8)))
        split=[]
        for atom in atoms:
            groups={}
            for pixel in atom['pixels']:
                if tuple(pixel)not in owner:raise ValueError('JOINT_SCHEDULE_HINT_PIXEL')
                piece,bank,word=owner[tuple(pixel)]
                if piece not in atom['options']:raise ValueError('JOINT_FIXED_GEOMETRY_PIXEL_OPTION')
                groups.setdefault((piece,bank if fixed_geometry else None,kind(bank)if preserve_hint_math_classes else None,word if preserve_hint_words else None,pixel_allowed[tuple(pixel)]),[]).append(pixel)
            for (piece,bank,hint_class,hint_word,allowed_banks),pixels in groups.items():split.append(dict(atom,options=[piece],fixed_bank=bank,hint_class=hint_class,hint_word=hint_word,hint_allowed_banks=allowed_banks,pixels=pixels))
        atoms=split
    variable_count = 0;nonboolean_upper={}
    def allocate():
        nonlocal variable_count
        result = variable_count; variable_count += 1; return result
    masks = {(i,b):allocate() for i in range(len(pieces)) for b in range(8)}
    single_bank_word_ownership=preserve_hint_words and(fixed_geometry or fixed_rectangles and maximum_banks_per_piece_class==1)
    choices = {}; uses = {};opaque_variables={};opaque_choice_entries=0;math_variables={};math_choice_entries=0
    for i, atom in enumerate(atoms):
        for bank in range(8):
            if 'literal_bank'in atom and bank!=atom['literal_bank']:continue
            if bank not in atom.get('hint_allowed_banks',range(8)):continue
            if fixed_geometry and bank!=atom['fixed_bank']:continue
            if preserve_hint_math_classes and kind(bank)!=atom['hint_class']:continue
            if additive_only and kind(bank)==0:continue
            colors=[atom['output']] if kind(bank)==0 else atom['residual_options']
            if preserve_hint_words:colors=[c for c in colors if c==atom['hint_word']]
            for color in colors:
                if not allowed(bank,color,atom['line']):continue
                if scanline_math_candidate is not None and atom['line']in control_states and color not in control_states[atom['line']][kind(bank)]:continue
                for piece_index in atom['options']:
                    if single_bank_word_ownership:
                        choices[i,piece_index,bank,color]=masks[piece_index,bank]
                    elif kind(bank)==0:
                        opaque_choice_entries+=1;key=piece_index,bank,color,atom['line']
                        if coalesce_opaque_choices:
                            if key not in opaque_variables:opaque_variables[key]=allocate()
                            choices[i,piece_index,bank,color]=opaque_variables[key]
                        else:choices[i,piece_index,bank,color]=allocate()
                    else:
                        math_choice_entries+=1
                        y,x=atom['pixels'][0]
                        key=piece_index,bank,color,y,atom['output'],int(bg[y,x]),math_enabled(y,x)
                        if coalesce_math_choices:
                            # Equal contexts in this piece can share one
                            # operand. Extending its pixel mask adds neither
                            # an OAM rectangle nor a required palette word.
                            if key not in math_variables:math_variables[key]=allocate()
                            choices[i,piece_index,bank,color]=math_variables[key]
                        else:choices[i,piece_index,bank,color]=allocate()
                uses.setdefault((bank,color),set()).add(atom['line'])
    first_visible_line=min((a['line']for a in atoms),default=0)
    def residency_lines(lines):
        if row_capacity_only:return sorted(lines)
        if pool_residency:return [0]+list(range(pool_first,max(lines)+1))if pool_first else list(range(max(lines)+1))
        if collapse_inactive_prefix:return ([0]if first_visible_line else[])+list(range(first_visible_line,max(lines)+1))
        lower=max(0,min(lines)-lookahead)
        return ([0] if lower else [])+list(range(lower,max(lines)+1))
    interval_anchors={};interval_members={};zero_write=None
    if pin_scanline_pool_intervals:
        # Restricted construction: bounded bank copies persist through each
        # saved pool interval or chunk. Optional unused words may be omitted.
        # First-row pool words may be installed in VBlank and remain resident
        # until their interval ends, with their slots counted on every row.
        if any(a['line']not in control_states for a in atoms):raise ValueError('JOINT_SCANLINE_INTERVAL_REQUIRES_FULL_PIXEL_SCOPE')
        first=min(control_states);last=max(control_states)
        if set(control_states)!=set(range(first,last+1)):raise ValueError('JOINT_SCANLINE_INTERVAL_CONTIGUOUS_SCOPE')
        resident={}
        for b,c in sorted(uses):
            groups=[]
            for y in range(first,last+1):
                if c not in control_states[y][kind(b)]:continue
                if groups and groups[-1][-1]+1==y:groups[-1].append(y)
                else:groups.append([y])
            if pool_interval_gap_bridge_lines:
                bridged=[]
                for g in groups:
                    if bridged and g[0]-bridged[-1][-1]-1<=pool_interval_gap_bridge_lines:bridged[-1].extend(range(bridged[-1][-1]+1,g[-1]+1))
                    else:bridged.append(g)
                groups=bridged
            if pool_interval_initial_preload and groups:groups[0]=list(range(groups[0][0]))+groups[0]
            if pool_interval_max_lines:groups=[g[i:i+pool_interval_max_lines]for g in groups for i in range(0,len(g),pool_interval_max_lines)]
            for group_index,lines in enumerate(groups):
                if lines[0]==first and not pool_interval_initial_preload:lines=list(range(first))+lines
                if collapse_inactive_prefix and lines[-1]<first:continue
                if collapse_inactive_prefix:
                    lines=[y for y in lines if y>=first]
                    if lines[0]==first:lines=list(range(first))+lines
                v=allocate();anchor=(b,c,lines[0]);interval_anchors[anchor]=v
                for y in lines:resident[b,c,y]=v
                interval_members.setdefault((kind(b),c,lines[0],lines[-1]),[]).append(v)
        zero_write=allocate();nonboolean_upper[zero_write]=0
        writes={key:allocate()if key in interval_anchors else zero_write for key in resident if key[2]>0}
    else:
        resident={}
        for (b,c),lines in sorted(uses.items()):
            for y in residency_lines(lines):
                if allowed(b,c,y):resident[b,c,y]=resident[b,c,0]if collapse_inactive_prefix and first_visible_line and y==first_visible_line else allocate()
        writes = {key:allocate() for key in resident if key[2] > 0}
    peak = allocate() if relaxed else None
    frame_colors={(b,c):allocate()for b,c in uses}if maximum_frame_colors_per_bank is not None else {}
    rr=[];cc=[];vv=[];lo=[];hi=[]
    def constraint(items, lower, upper):
        row = len(lo)
        for variable, value in items:
            rr.append(row);cc.append(variable);vv.append(value)
        lo.append(lower);hi.append(upper)
    for values in interval_members.values():constraint([(v,1)for v in values],0,pool_interval_bank_copies)
    if frame_colors:
        for (b,c,y),v in resident.items():constraint([(v,1),(frame_colors[b,c],-1)],-np.inf,0)
        for b in range(8):constraint([(v,1)for (bank,c),v in frame_colors.items()if bank==b],0,maximum_frame_colors_per_bank)
    atom_choices={};mask_choices={key:[] for key in masks}
    for (i,piece_index,bank,color),variable in choices.items():
        atom_choices.setdefault(i,[]).append((piece_index,bank,color,variable))
        mask_choices[piece_index,bank].append(variable)
    mandatory={};forced_colors={}
    implications=set();geometry_cover_cuts=set();atom_choice_equalities=set()
    for i,atom in enumerate(atoms):
        options=atom_choices.get(i,[])
        equality=tuple(sorted(v for p,b,c,v in options))
        if equality not in atom_choice_equalities:
            constraint([(v,1)for v in equality],1,1);atom_choice_equalities.add(equality)
        eligible_masks=tuple(sorted({masks[p,b]for p,b,c,v in options}))
        if eligible_masks not in geometry_cover_cuts:
            constraint([(v,1)for v in eligible_masks],1,np.inf)
            geometry_cover_cuts.add(eligible_masks)
        eligible_pieces={p for p,b,c,v in options};kinds={kind(b)for p,b,c,v in options}
        if len(eligible_pieces)==1 and len(kinds)==1:
            p=next(iter(eligible_pieces));k=next(iter(kinds));key=p,k
            mandatory[key]=max(mandatory.get(key,0),1)
            colors={c for pp,b,c,v in options}
            if len(colors)==1:forced_colors.setdefault((p,k,atom['line']),set()).update(colors)
        for piece_index,bank,color,variable in options:
            for dependency in (masks[piece_index,bank],resident[bank,color,atom['line']]):
                if (variable,dependency)not in implications:
                    constraint([(variable,1),(dependency,-1)],-np.inf,0)
                    implications.add((variable,dependency))
    # A selected OAM mask must own at least one opaque source pixel. Otherwise
    # feasibility search can branch over unused sprites which only consume
    # hardware capacity. Removing those masks preserves every valid rendering.
    for key,variables in mask_choices.items():
        variables=set(variables)
        constraint([(masks[key],1)]+[(v,-1)for v in variables],-np.inf,0)
    for (p,k,y),colors in forced_colors.items():
        mandatory[p,k]=max(mandatory[p,k],(len(colors)+14)//15)
    if maximum_banks_per_piece_class:
        for p in range(len(pieces)):
            for k in ((0,1)if color_math=='additive'else(0,)):
                constraint([(masks[p,b],1)for b in banks_for_kind(k)],0,maximum_banks_per_piece_class)
    for (p,k),count in mandatory.items():
        constraint([(masks[p,b],1)for b in banks_for_kind(k)],count,np.inf)
    mandatory_geometry=dict(oam_entries=sum(mandatory.values()),
        peak_sprites=max((sum(n for (i,k),n in mandatory.items()if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height'])for y in range(height)),default=0),
        peak_tile_slivers=max((sum(n*slivers(pieces[i])for (i,k),n in mandatory.items()if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height'])for y in range(height)),default=0))
    constraint([(v,1) for v in masks.values()],0,128)
    if bank_symmetry:
        # Canonicalize interchangeable bank labels by first piece using each bank.
        # At one piece, simultaneous first uses may retain symmetry, but no valid
        # schedule is lost: order banks by their first active piece.
        for first_bank in ((0,4)if color_math=='additive'else(0,)):
            for bank in range(first_bank+1,first_bank+(4 if color_math=='additive'else 8)):
                for i in range(len(pieces)):
                    constraint([(masks[i,bank],1)]+[(masks[j,bank-1],-1) for j in range(i+1)],-np.inf,0)
    for y in range(height):
        active = [(i,b) for i,p in enumerate(pieces) if p['y'] <= y < p['y']+p['height'] for b in range(8)]
        constraint([(masks[key],1) for key in active],0,32)
        constraint([(masks[key],slivers(pieces[key[0]])) for key in active],row_tile_lower_bounds[y],34)
    color_choices={}
    for (i,piece_index,b,c),variable in choices.items():color_choices.setdefault((b,c),set()).add((atoms[i]['line'],variable))
    bank_lines = {}; write_lines = {}
    preload_prefixes={}
    for key, variable in resident.items():
        b,c,y = key
        bank_lines.setdefault((b,y),[]).append(variable)
        if y:
            if pin_scanline_pool_intervals and writes[key]==zero_write:continue
            future={v for line,v in color_choices.get((b,c),())if y<=line<=y+lookahead}
            constraint([(writes[key],1)]+[(v,-1)for v in future],-np.inf,0)
            items=[(variable,1),(writes[key],-1)]
            previous=0 if pool_residency and y==pool_first else y-1
            if not pin_scanline_pool_intervals and not row_capacity_only and not pool_residency and (b,c,previous) not in resident and (b,c,0) in resident:previous=0
            prior=resident.get((b,c,previous))
            if prior is not None:
                items.append((prior,-1))
                constraint([(writes[key],1),(prior,1)],-np.inf,1)
            # Exact new-residency transition, rather than an unconstrained
            # surplus write. Rewriting a retained word cannot help admission.
            constraint([(writes[key],1),(variable,-1)],-np.inf,0)
            constraint(items,-np.inf,0);write_lines.setdefault(y,[]).append(writes[key])
    # Sparse residency has an initial variable followed by the first legal
    # prefetch row. An initially loaded color occupies a slot throughout that
    # prefix; ignoring it allowed another color to overwrite its physical slot
    # while the later transition still treated it as resident for free.
    for b,c in uses:
        lines=[y for y in residency_lines(uses[b,c])if(b,c,y)in resident]
        if not pin_scanline_pool_intervals and not row_capacity_only and len(lines)>1 and lines[0]==0 and lines[1]>1:
            preload_prefixes[b,c]=lines[1]
            for y in range(1,lines[1]):bank_lines.setdefault((b,y),[]).append(resident[b,c,0])
    interval_groups=0
    if pin_pool_intervals:
        # Restricted constructive family: every represented pool residency is
        # retained in one bank for its full interval. No claim of completeness.
        color_lines={}
        for b,c,y in resident:color_lines.setdefault((kind(b),c),set()).add(y)
        for (k,color),lines_for_color in color_lines.items():
            groups=[]
            for y in sorted(lines_for_color):
                if groups and (y==groups[-1][-1]+1 or groups[-1][-1]==0 and y==pool_first):groups[-1].append(y)
                else:groups.append([y])
            for group in groups:
                initial=[]
                for bank in banks_for_kind(k):
                    first=(bank,color,group[0])
                    if first not in resident:continue
                    anchor=resident[first];initial.append((anchor,1))
                    for y in group[1:]:
                        if (bank,color,y) in resident:constraint([(resident[bank,color,y],1),(anchor,-1)],0,0)
                constraint(initial,1,1);interval_groups+=1
    for variables in bank_lines.values():
        constraint([(v,1) for v in variables],0,15)
    for y,variables in write_lines.items():
        constraint([(v,1) for v in variables],0,line_budget(y))
        if relaxed:constraint([(v,1) for v in variables]+[(peak,-1)],-np.inf,0)
    if prepared_dma_window is not None:
        by_bank_line={}
        for (b,c,y),v in writes.items():by_bank_line.setdefault((b,y),[]).append(v)
        for y,variables in write_lines.items():
            active={b:allocate()for b in range(8)};bridges={b:allocate()for b in range(7)}
            for b,a in active.items():
                values=by_bank_line.get((b,y),[])
                for v in values:constraint([(v,1),(a,-1)],-np.inf,0)
                constraint([(a,1)]+[(v,-1)for v in values],-np.inf,0)
            for b,v in bridges.items():
                for a in (active[b],active[b+1]):constraint([(v,1),(a,-1)],-np.inf,0)
            # Favorable necessary bound: grant every adjacent bank bridge
            # without charging unused intermediate slots. Each bridge can
            # save at most eight clocks (zero-word 16, range switch 24).
            # CGRAM commits only the high byte. Grant one low-byte preload
            # before the window, reducing the necessary commit span by eight.
            constraint([(v,16)for v in variables]+[(v,24)for v in active.values()]+[(v,-8)for v in bridges.values()],-np.inf,prepared_dma_window+39)
            if prepared_dma_partition:
                from raster_dma_partition import constrain_ranges,minimum_commit_span
                maximum_colors=max(c for c in range(121)if minimum_commit_span(c)<prepared_dma_window)
                constraint([(v,1)for v in variables],0,maximum_colors)
                domains=constrain_ranges({b:by_bank_line.get((b,y),[])for b in range(8)},active,allocate,constraint,prepared_dma_window)
                nonboolean_upper.update(domains)
    objective=np.zeros(variable_count);integrality=np.ones(variable_count)
    for variable in masks.values():objective[variable]=1
    for variable in writes.values():
        objective[variable]=.001
        if not pin_scanline_pool_intervals:integrality[variable]=0
    upper=np.ones(variable_count)
    if literal_actor_bank is not None:
        for (i,b),v in masks.items():
            if actors[pieces[i]['actor']]['metadata']['alpha']==0 and b!=literal_actor_bank:upper[v]=0
    if fixed_geometry or fixed_rectangles:
        permitted={p for p,b in chosen_masks}
        for key,v in masks.items():
            if(key not in chosen_masks if fixed_geometry else key[0]not in permitted):upper[v]=0
    if fixed_rectangles:
        # Keep the admitted rectangles and their maximum multiplicity, while
        # letting offline search select new fixed palette banks for them.
        for p in {p for p,b in chosen_masks}:
            constraint([(masks[p,b],1)for b in range(8)],0,min(8,sum(pp==p for pp,b in chosen_masks)+rectangle_bank_slack))
    for v,limit in nonboolean_upper.items():upper[v]=limit
    if feasibility_only:objective[:]=0
    if relaxed:
        integrality[:]=0;objective[:]=0;objective[peak]=1;upper[peak]=write_budget
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(lo),variable_count)).tocsc()
    hint=None
    if schedule_hint is not None:
        hint={v:int(key in chosen_masks)for key,v in masks.items()}
        for (i,p,b,c),v in choices.items():
            wanted=owner.get(tuple(atoms[i]['pixels'][0]))
            if wanted is None:raise ValueError('JOINT_SCHEDULE_HINT_PIXEL')
            hint[v]=int(wanted==(p,b,c))
        if not pin_scanline_pool_intervals:
            for (b,c,y),v in resident.items():hint[v]=int(c in hint_states[y][b])
            for (b,c,y),v in writes.items():
                previous=0 if pool_residency and y==pool_first else y-1
                if not pool_residency and (b,c,previous)not in resident:previous=0
                hint[v]=int(c in hint_states[y][b]and c not in hint_states[previous][b])
    if relaxed:
        low=np.asarray(lo);high=np.asarray(hi)
        equal=low==high;bounded_low=np.isfinite(low)&~equal;bounded_high=np.isfinite(high)&~equal
        inequalities=vstack((matrix[bounded_high],-matrix[bounded_low])).tocsc()
        limits=np.concatenate((high[bounded_high],-low[bounded_low]))
        result=linprog(objective,A_ub=inequalities,b_ub=limits,A_eq=matrix[equal],b_eq=low[equal],bounds=list(zip(np.zeros(variable_count),upper)),method='highs-ipm',options={'time_limit':time_limit})
    elif solver_backend=='cp-sat':
        from raster_boolean_solver import solve
        result=solve(matrix,lo,hi,objective,time_limit,hint=hint,variable_upper=upper)
    else:
        result=milp(objective,integrality=integrality,bounds=Bounds(0,upper),constraints=LinearConstraint(matrix,lo,hi),options={'time_limit':time_limit,'mip_rel_gap':.05})
    report=dict(schema='BYOR_JOINT_EXACT_CONTEXT_OBJ_MILP_V1',status='BOUNDED_JOINT_SOLVER_NO_CANDIDATE',
                metadata=metadata,geometry_size=size,mixed_small_size=mixed_small_size if size=='mixed'else None,mixed_large_size=mixed_large_size if size=='mixed'else None,write_budget=write_budget,lookahead_lines=lookahead,noninitial_prefetch_lookahead_enforced=True,initial_palette_may_preload_entire_frame=not row_capacity_only and(not pin_scanline_pool_intervals or pool_interval_initial_preload),initial_palette_restricted_to_first_pool_row=pin_scanline_pool_intervals and not pool_interval_initial_preload,pool_interval_initial_preload=pool_interval_initial_preload,pool_interval_gap_bridge_lines=pool_interval_gap_bridge_lines,collapse_inactive_prefix=collapse_inactive_prefix,
                solver=dict(status=int(result.status),message=result.message,variables=variable_count,constraints=len(lo),mip_nodes=int(result.mip_node_count) if getattr(result,'mip_node_count',None) is not None else None,mip_gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None and np.isfinite(result.mip_gap) else None),
                exact_residency_write_indicators=True,geometry_cover_cuts=len(geometry_cover_cuts),row_capacity_only=row_capacity_only,literal_alpha_zero_actor_bank=literal_actor_bank,
                palette_transfer_budget_relaxed=row_capacity_only,
                fixed_geometry_and_pixel_bank_ownership=fixed_geometry,
                fixed_rectangles_and_pixel_rectangle_ownership=fixed_rectangles,preserve_hint_math_classes=preserve_hint_math_classes,preserve_hint_words=preserve_hint_words,
                fixed_rectangle_bank_assignment_may_change=fixed_rectangles,
                additional_bank_masks_per_hint_rectangle=rectangle_bank_slack,
                fixed_single_bank_word_ownership_factored=single_bank_word_ownership,
                additive_only=additive_only,opaque_obj_banks_reserved=4 if additive_only else 0,color_math=color_math,opaque_choice_coalescing=coalesce_opaque_choices,opaque_choice_entries=opaque_choice_entries,
                math_choice_coalescing=coalesce_math_choices,math_choice_entries=math_choice_entries,
                distinct_math_choice_variables=len(math_variables)if coalesce_math_choices else math_choice_entries,
                distinct_opaque_choice_variables=len(opaque_variables)if coalesce_opaque_choices else opaque_choice_entries,
                no_color_reduction=True,universal_raster_rejected=False,native_presentation_proven=False,
                pooled_residency_pinned=bool(pool_residency),
                scanline_pool_intervals_single_bank_restricted=pin_scanline_pool_intervals and pool_interval_bank_copies==1,pool_interval_bank_copies=pool_interval_bank_copies,pool_interval_max_lines=pool_interval_max_lines,scanline_pool_interval_variables=len(interval_anchors),
                full_pool_intervals_retained=pin_pool_intervals,pool_residency_intervals=interval_groups,
                feasibility_only=feasibility_only,bank_symmetry=bank_symmetry,bank_symmetry_policy='first visible piece' if bank_symmetry else None,early_write_budget=early_write_budget,late_start=late_start,saturated_reuse=saturated_reuse,align_visible_bounds=align_visible_bounds,
                maximum_frame_colors_per_bank=maximum_frame_colors_per_bank,
                additive_alternative_count=sum(len(a["residual_options"]) for a in atoms),
                complete_additive_cover=complete_cover_report,
                saturated_extrema=saturated_extrema,additive_operand_corpus_colors=len(residual_corpus),
                grid_padding_x=grid_padding_x,grid_padding_y=grid_padding_y,
                horizontal_clip_limit_counted=clip_horizontal,
                maximum_banks_per_piece_class=maximum_banks_per_piece_class,
                mandatory_geometry_lower_bound=mandatory_geometry,
                independent_actor_row_tile_lower_bounds=row_tile_lower_bounds,
                independent_actor_peak_tile_lower_bound=max(row_tile_lower_bounds,default=0),
                row_tile_lower_bound_relaxes_piece_alignment_and_palette_masks=True,
                prepared_dma_partition_bound_enforced=prepared_dma_partition,
                prepared_dma_window_master_clocks=prepared_dma_window,
                prepared_dma_window_is_optimistic_necessary_only=prepared_dma_window is not None,
                schedule_hint_used=schedule_hint is not None,
                input_geometry_is_search_hint=input_geometry_search_hint,
                schedule_residency_hint_used=schedule_hint is not None and solver_backend=='cp-sat'and not pin_scanline_pool_intervals,
                initial_preload_prefix_capacity_modeled=True,
                initial_preload_prefix_colors=len(preload_prefixes),
                exact_underlay_bypass=underlay_bypass,underlay_bypassed_pixels=bypassed,source_actor_canvases=source_canvases,
                source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
                scope='Explicit pose. Exact opaque/additive pixel alternatives and fixed OAM color masks on one legal grid. No native layer routing, source reachability or hardware bandwidth admission.')
    if color_math=='subscreen-additive':
        report.update(obj_operand_screen='SUBSCREEN',operand_palette_banks=list(range(8)),main_screen_color_math_layer='BG1',main_screen_obj_disabled=True,subscreen_background_disabled=True,fixed_color_rgb555=0,shared_scanline_math_mode='add',concurrent_main_obj_layer_routing_proven=False,native_layer_routing_proven=False)
    if scanline_math_candidate is not None:
        report.update(scanline_math_controls_source_bound=True,scanline_math_candidate_sha256=hashlib.sha256(json.dumps(scanline_math_candidate,sort_keys=True).encode()).hexdigest(),
            scanline_math_control_rows=sorted(control_modes),outside_control_rows_math_policy='FULL_ADD_NO_WINDOW',
            scanline_pool_candidate_pixel_coverage_replayed=True,
            scanline_pool_operand_choices_restricted=not relax_scanline_pool,scanline_pool_residency_pinned=False,
            selected_modes={y:control_modes.get(y,'add')for y in range(height)},compiled_color_window_descriptors=control_windows,
            complete_outside_control_math_cover=control_cover,window_register_schedule_proven=False)
    report['solver']['backend']=solver_backend
    if relaxed:report['solver']['relaxation_algorithm']='HIGHS_IPM'
    if hasattr(result,'boolean_stats'):report['solver']['boolean_stats']=result.boolean_stats
    if hasattr(result,'bounded_log'):report['bounded_solver_log']=result.bounded_log
    if result.x is None:
        return report
    if relaxed:
        values=matrix @ result.x
        violation=max(float(np.max(np.maximum(np.array(lo)-values,0))),float(np.max(np.maximum(values-np.array(hi),0))),float(np.max(np.maximum(-result.x,0))),float(np.max(np.maximum(result.x-upper,0))))
        if violation>1e-6:raise AssertionError('JOINT_LP_PRIMAL_RESIDUAL_FAULT')
        report.update(status='FRACTIONAL_RELAXATION_DOES_NOT_PROVE_SCHEDULE',fractional_peak_writes=float(result.x[peak]),optimal_relaxation=result.status==0,maximum_primal_violation=violation,scope='Fractional necessary relaxation of the specified grid/lookahead. Pixel ownership, OAM and residency may be fractional; no hardware schedule is proven.')
        return report
    chosen = {}
    demand=[{b:set() for b in range(8)} for _ in range(height)]
    expanded={}
    for i, atom in enumerate(atoms):
        banks=[(p,b,c)for p,b,c,v in atom_choices.get(i,[])if result.x[v]>.5]
        if len(banks)!=1:
            raise AssertionError('JOINT_ATOM_BANK_FAULT')
        piece_index,b,c=banks[0];chosen[i]=(piece_index,b,c)
        demand[atom['line']][b].add(c)
        expanded.setdefault((piece_index,b),{}).setdefault(atom['line'],set()).add(c)
    selected=[dict(pieces[i],rows={y:sorted(colors) for y,colors in rows.items()},bank=b) for (i,b),rows in sorted(expanded.items())]
    if set(expanded)!={key for key,variable in masks.items() if result.x[variable]>.5}:
        raise AssertionError('JOINT_OAM_MASK_OWNERSHIP_FAULT')
    geometry=dict(oam_entries=len(selected),peak_sprites=max(sum(p['y']<=y<p['y']+p['height'] for p in selected) for y in range(height)),peak_tile_slivers=max(sum(slivers(p) for p in selected if p['y']<=y<p['y']+p['height']) for y in range(height)))
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:
        raise AssertionError('JOINT_GEOMETRY_LIMIT_FAULT')
    wanted=[{b:set() for b in range(8)} for _ in range(height)]
    for (b,c,y),variable in resident.items():
        if result.x[variable]>.5:wanted[y][b].add(c)
    for (b,c),end in preload_prefixes.items():
        if result.x[resident[b,c,0]]>.5:
            for y in range(1,end):wanted[y][b].add(c)
    slots={b:[None]*15 for b in range(8)};states=[];trace=[];prefetch_latency=0
    for y in range(height):
        before={b:list(values) for b,values in slots.items()};events=[]
        for b in range(8):
            if len(wanted[y][b])>15 or not demand[y][b] <= wanted[y][b]:
                raise AssertionError('JOINT_RESIDENCY_FAULT')
            for color in sorted(wanted[y][b]-set(slots[b])):
                if y:
                    future=next((line for line in range(y,min(height,y+lookahead+1))if color in demand[line][b]),None)
                    if future is None:raise AssertionError('JOINT_PREFETCH_LOOKAHEAD_FAULT')
                    prefetch_latency=max(prefetch_latency,future-y)
                at=next(i for i,c in enumerate(slots[b]) if c not in wanted[y][b])
                events.append(dict(bank=b,slot=at+1,old=slots[b][at],color=color,kind='required' if color in demand[y][b] else 'prefetch'));slots[b][at]=color
        if y and len(events)>line_budget(y):raise AssertionError('JOINT_WRITE_LIMIT_FAULT')
        if y and events and prepared_dma_window is not None:
            from raster_cgram_packets import optimistic_dma_span
            span=optimistic_dma_span(events)
            required=max(0,span['best_partition_span_master_clocks']-8)if prepared_dma_partition else span['first_to_last_cgram_commit_master_clocks']
            if required>=prepared_dma_window:
                raise AssertionError('JOINT_DMA_SPAN_LOWER_BOUND_FAULT')
        states.append({b:list(values) for b,values in slots.items()})
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in values if c is not None and c in slots[b]] for b,values in before.items()},evicted=[e['old'] for e in events if e['old'] is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank'] for e in events})))
    replay=bg.copy();indices=np.zeros((height,256),dtype=np.uint8)
    piece_ids={key:i for i,key in enumerate(sorted(expanded))}
    piece_pixels=[np.zeros((p['height'],p['width']),dtype=np.uint8)for p in selected]
    for i,atom in enumerate(atoms):
        piece_index,b,color=chosen[i];slot=states[atom['line']][b].index(color)+1
        for y,x in atom['pixels']:
            indices[y,x]=128+b*16+slot
            index=piece_ids[piece_index,b];p=selected[index]
            piece_pixels[index][y-p['y'],x-p['x']]=slot
    ownership=np.zeros((height,256),dtype=np.uint8)
    for piece,pixels in zip(selected,piece_pixels):
        for ly,lx in zip(*np.where(pixels!=0)):
            y,x=int(ly+piece['y']),int(lx+piece['x']);b=piece['bank']
            if ownership[y,x]:raise AssertionError('JOINT_PIXEL_MASK_OVERLAP')
            ownership[y,x]=1;color=states[y][b][int(pixels[ly,lx])-1]
            replay[y,x]=color if kind(b)==0 else render_word(color,y,x)
    if not np.array_equal(replay,rgb555(expected)):raise AssertionError('JOINT_SOURCE_PIXEL_IDENTITY_FAULT')
    if maximum_frame_colors_per_bank is not None:
        if any(len({e['color']for row in trace for e in row['updates']if e['bank']==b})>maximum_frame_colors_per_bank for b in range(8)):raise AssertionError('JOINT_FRAME_COLOR_LIMIT_REPLAY')
    groups=[[demand[y][b] for y in range(height)] for b in range(8)]
    report.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',geometry=geometry,pieces=selected,trace=trace,
                  compiled_pixel_identity_verified=True,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
                  piece_pixel_masks=[dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(pixels.flatten()[::2]|(pixels.flatten()[1::2]<<4)).tobytes().hex())for p,pixels in zip(selected,piece_pixels)],
                  peak_scheduled_writes=max(row['colors_written'] for row in trace[1:]),fixed_bank_interval_bound=split_interval_bound(groups,15))
    counts=[row['colors_written']for row in trace[1:]]
    hash_payload=dict(pieces=selected,pixel_masks=report['piece_pixel_masks'],trace=trace)
    if scanline_math_candidate is not None:
        hash_payload.update(selected_modes=report['selected_modes'],compiled_color_window_descriptors=control_windows,outside_control_rows_math_policy=report['outside_control_rows_math_policy'])
    report.update(peak_cgram_data_bytes=2*max(counts,default=0),average_writes=float(np.mean(counts)),worst_scanline=1+int(np.argmax(counts)),maximum_noninitial_prefetch_latency_lines=prefetch_latency,noninitial_prefetch_latency_replayed=True,
                  compiled_schedule_sha256=hashlib.sha256(json.dumps(hash_payload,sort_keys=True).encode()).hexdigest(),
                  schedule_latency_requirement='All updates for line y must finish before that line consumes OBJ colors; initial slots restored during VBlank. No native timing admission.')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--size',choices=('8','16','32','mixed'),default='16')
    p.add_argument('--mixed-small-size',type=int,choices=(8,16),default=8)
    p.add_argument('--mixed-large-size',type=int,choices=(16,32),default=32)
    p.add_argument('--write-budget',type=int,default=20);p.add_argument('--time-limit',type=int,default=45)
    p.add_argument('--lookahead',type=int,default=16)
    p.add_argument('--relaxed',action='store_true')
    p.add_argument('--pool-residency',type=Path)
    p.add_argument('--pin-pool-intervals',action='store_true')
    p.add_argument('--clip-horizontal',action='store_true')
    p.add_argument('--feasibility-only',action='store_true');p.add_argument('--bank-symmetry',action='store_true')
    p.add_argument('--saturated-reuse',action='store_true')
    p.add_argument('--solver-backend',choices=('highs','cp-sat'),default='highs')
    p.add_argument('--align-visible-bounds',action='store_true')
    p.add_argument('--pool-only',action='store_true');p.add_argument('--integer-pool-budget',type=int)
    p.add_argument('--early-write-budget',type=int);p.add_argument('--late-start',type=int,default=75)
    p.add_argument('--prepared-dma-window',type=int)
    p.add_argument('--prepared-dma-partition',action='store_true')
    p.add_argument('--coalesce-opaque-choices',action='store_true')
    p.add_argument('--coalesce-math-choices',action='store_true')
    p.add_argument('--additive-only',action='store_true',help='Reserve the four opaque OBJ banks; every visible pixel must use an exact BG-additive operand.')
    p.add_argument('--pool-math-mode',action='append',choices=('add','half-add','subtract','half-subtract'),help='Necessary pool relaxation only; modes may differ per pixel.')
    p.add_argument('--color-math',choices=('additive','precomposited','subscreen-additive'),default='additive',help='Subscreen operands can use all eight banks with BG1 main-screen math; native routing and concurrent actors remain required.')
    p.add_argument('--schedule-hint',type=Path)
    p.add_argument('--preserve-hint-math-classes',action='store_true',help='Fixed rectangle bank search keeping every hinted pixel in its original color-math bank class.')
    p.add_argument('--preserve-hint-words',action='store_true',help='Also preserve exact per-pixel palette words; requires fixed rectangles and preserved math classes.')
    p.add_argument('--maximum-banks-per-piece-class',type=int,default=0,help='Optional restricted maximum OAM bank masks per geometry rectangle and color-math class; zero is unrestricted.')
    p.add_argument('--collapse-inactive-prefix',action='store_true',help='Choose the first required OBJ row palette during VBlank and hold it through the preceding actor-free rows.')
    p.add_argument('--pool-interval-gap-bridge-lines',type=int,default=0,help='Allow interval residency to span bounded gaps in the saved pool; every bridged row counts occupied palette slots.')
    p.add_argument('--pool-interval-initial-preload',action='store_true',help='Allow future first pool intervals to preload in VBlank; their slots remain occupied throughout every preceding row.')
    p.add_argument('--pool-interval-max-lines',type=int,default=0,help='Optional subdivision of pool lifetimes into bounded chunks; retained bank copies across chunks incur no new write.')
    p.add_argument('--pool-interval-bank-copies',type=int,default=1,help='Maximum bank copies of a retained saved pool interval, each charged as a write when newly loaded.')
    p.add_argument('--pin-scanline-pool-intervals',action='store_true',help='Restricted construction: retain bounded bank copies through each saved word interval or chunk; requires full source-pixel scope.')
    p.add_argument('--fixed-rectangles',action='store_true',help='Keep hinted rectangles and pixel ownership, but allow new offline fixed bank assignments within their original multiplicity.')
    p.add_argument('--rectangle-bank-slack',type=int,default=0,help='Allow extra fixed bank masks per hinted rectangle, with full OAM and per-line hardware limits still enforced.')
    p.add_argument('--fixed-geometry',action='store_true',help='Keep every hinted pixel in its existing OAM piece and bank; search exact operands and residency only.')
    p.add_argument('--underlay-bypass',action='store_true')
    p.add_argument('--saturated-extrema',action='store_true')
    p.add_argument('--complete-additive-cover',action='store_true')
    p.add_argument('--grid-padding-x',type=int,default=0);p.add_argument('--grid-padding-y',type=int,default=0)
    p.add_argument('--maximum-frame-colors-per-bank',type=int)
    p.add_argument('--row-capacity-only',action='store_true',help='Geometry/bank search only: requires 120 writes and zero lookahead; no transfer admission.')
    p.add_argument('--scanline-math-candidate',type=Path,help='Source-replayed integer pool controls and operand choices; outside its rows explicitly uses full add without a window.')
    p.add_argument('--rectangle-cover',type=Path,help='Source-bound exact visible-pixel rectangles; palette masks still obey OAM and scanline limits.')
    p.add_argument('--subdivide-rectangle-cover',action='store_true')
    p.add_argument('--literal-actor-bank',type=int,help='Fix all alpha-zero actors to one shared math-ineligible bank, with combined row capacity enforced.')
    p.add_argument('--relax-scanline-pool',action='store_true',help='Keep source-bound math modes/windows while allowing new exact operand identities.')
    a=p.parse_args();r=probe(Source(a.source),a.stage,json.loads(a.scene.read_text()),'mixed'if a.size=='mixed'else int(a.size),a.write_budget,lookahead=a.lookahead,time_limit=a.time_limit,relaxed=a.relaxed,pool_residency=json.loads(a.pool_residency.read_text())if a.pool_residency else None,clip_horizontal=a.clip_horizontal,feasibility_only=a.feasibility_only,bank_symmetry=a.bank_symmetry,early_write_budget=a.early_write_budget,late_start=a.late_start,saturated_reuse=a.saturated_reuse,pool_only=a.pool_only,integer_pool_budget=a.integer_pool_budget,align_visible_bounds=a.align_visible_bounds,solver_backend=a.solver_backend,pin_pool_intervals=a.pin_pool_intervals,prepared_dma_window=a.prepared_dma_window,schedule_hint=json.loads(a.schedule_hint.read_text())if a.schedule_hint else None,underlay_bypass=a.underlay_bypass,saturated_extrema=a.saturated_extrema,complete_additive_cover=a.complete_additive_cover,grid_padding_x=a.grid_padding_x,grid_padding_y=a.grid_padding_y,prepared_dma_partition=a.prepared_dma_partition,coalesce_opaque_choices=a.coalesce_opaque_choices,color_math=a.color_math,mixed_small_size=a.mixed_small_size,mixed_large_size=a.mixed_large_size,additive_only=a.additive_only,pool_math_modes=a.pool_math_mode,fixed_geometry=a.fixed_geometry,maximum_frame_colors_per_bank=a.maximum_frame_colors_per_bank,scanline_math_candidate=json.loads(a.scanline_math_candidate.read_text())if a.scanline_math_candidate else None,row_capacity_only=a.row_capacity_only,coalesce_math_choices=a.coalesce_math_choices,fixed_rectangles=a.fixed_rectangles,pin_scanline_pool_intervals=a.pin_scanline_pool_intervals,pool_interval_bank_copies=a.pool_interval_bank_copies,pool_interval_max_lines=a.pool_interval_max_lines,maximum_banks_per_piece_class=a.maximum_banks_per_piece_class,preserve_hint_math_classes=a.preserve_hint_math_classes,preserve_hint_words=a.preserve_hint_words,pool_interval_initial_preload=a.pool_interval_initial_preload,pool_interval_gap_bridge_lines=a.pool_interval_gap_bridge_lines,collapse_inactive_prefix=a.collapse_inactive_prefix,rectangle_bank_slack=a.rectangle_bank_slack,rectangle_cover=json.loads(a.rectangle_cover.read_text())if a.rectangle_cover else None,literal_actor_bank=a.literal_actor_bank,subdivide_rectangle_cover=a.subdivide_rectangle_cover,relax_scanline_pool=a.relax_scanline_pool)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k in ('status','solver','geometry','peak_scheduled_writes','peak_write_lower_bound','candidate_peak_writes')}))


if __name__=='__main__':main()
