"""Controlled source-actor context for isolated presentation experiments.

Only the test underlay/stage are virtual. Models, palettes, animation, dimensions
and alpha come from the original source. This is never an authored-stage build.
"""
import argparse,hashlib,io,json
from pathlib import Path
from PIL import Image
from compiler import Source,key
from source_scene_obj_joint import probe
import numpy as np
from source_scene_obj_raster import prepare,geometry
from raster_bank_search import assign
from raster_palette import schedule,split_color_masks
from source_bg_feasibility import rgb555
from source_scene_bg import compose_rgb8


def fixed_bank_context(source,stage,scene,lookahead=17,time_limit=30,interval_budget=21,global_color_banks=False,maximum_frame_colors_per_bank=None):
    """Compile a source-exact small-OBJ bank assignment before cache repair."""
    actors,metadata,expected=prepare(source,stage,scene);pieces=geometry(actors,'small');height=expected.shape[0]
    if global_color_banks:
        assignment=split_color_masks(pieces,tuple(range(8)),time_limit=time_limit,global_color_banks=True,solver_backend='cp-sat',maximum_frame_colors_per_bank=maximum_frame_colors_per_bank)
        if 'pieces'in assignment:pieces=assignment.pop('pieces')
    else:assignment=assign(pieces,tuple(range(8)),time_limit=time_limit,interval_write_budget=interval_budget,interval_lines=8)
    geom=dict(oam_entries=len(pieces),peak_sprites=max((sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(height)),default=0),
        peak_tile_slivers=max((sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(height)),default=0))
    report=dict(schema='BYOR_ISOLATED_FIXED_BANK_CONTEXT_V1',status='BOUNDED_FIXED_BANK_CONTEXT_NO_CANDIDATE',metadata=metadata,geometry=geom,
        bank_search=assignment,color_math='precomposited',no_color_reduction=True,native_presentation_proven=False,universal_raster_rejected=False,
        compiled_pixel_identity_verified=False,source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest())
    if geom['oam_entries']>128 or geom['peak_sprites']>32 or geom['peak_tile_slivers']>34:
        report['status']='FIXED_SMALL_GEOMETRY_LIMIT';return report
    if 'assignment'not in assignment:return report
    trace,states=schedule(pieces,assignment['assignment'],height,lookahead)
    # Consumers require complete eight-bank state/trace continuity.
    for row in trace:row['resident_before']={b:row['resident_before'].get(b,[None]*15)for b in range(8)}
    background,_=compose_rgb8(source,stage,dict(scene,actors=[]));replay=rgb555(background);indices=np.zeros((height,256),dtype=np.uint8);images=[];compiled=[]
    ownership=np.zeros((height,256),dtype=np.uint8);required_mask=np.zeros_like(ownership)
    for actor in actors:
        for ly,lx in zip(*np.where(actor['pixels']>=0)):required_mask[actor['top']+ly,actor['left']+lx]=1
    for p,bank in zip(pieces,assignment['assignment']):
        image=np.zeros((p['height'],p['width']),dtype=np.uint8);actor=actors[p['actor']]
        for ly in range(p['height']):
            y=p['y']+ly;ay=y-actor['top']
            for lx in range(p['width']):
                x=p['x']+lx;ax=x-actor['left']
                if not(0<=y<height and 0<=x<256 and 0<=ay<actor['pixels'].shape[0]and 0<=ax<actor['pixels'].shape[1]):continue
                color=int(actor['pixels'][ay,ax])
                if color<0 or color not in p['rows'].get(y,[]):continue
                if ownership[y,x]:raise AssertionError('ISOLATED_MASK_PIXEL_OVERLAP')
                ownership[y,x]=1
                slot=states[y][bank].index(color)+1;image[ly,lx]=slot;indices[y,x]=128+16*bank+slot;replay[y,x]=states[y][bank][slot-1]
        flat=image.flatten();images.append(dict(width=p['width'],height=p['height'],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
        compiled.append(dict(p,bank=bank))
    if not np.array_equal(replay,rgb555(expected)):raise AssertionError('ISOLATED_FIXED_BANK_SOURCE_PIXEL_REPLAY')
    if not np.array_equal(ownership,required_mask):raise AssertionError('ISOLATED_SOURCE_OPAQUE_MASK_REPLAY')
    counts=[r['colors_written']for r in trace[1:]]
    report.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,pieces=compiled,piece_pixel_masks=images,trace=trace,
        geometry_size=8,peak_scheduled_writes=max(counts,default=0),peak_cgram_data_bytes=2*max(counts,default=0),average_writes=float(np.mean(counts)),
        worst_scanline=1+int(np.argmax(counts)),lookahead_lines=lookahead,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest())
    outputs=rgb555(expected)
    report.update(source_opaque_mask_identity_verified=True,source_visible_opaque_pixels=int(ownership.sum()),
        source_opaque_output_rgb555_colors=len(np.unique(outputs[ownership!=0])),
        source_peak_scanline_output_rgb555_colors=max((len(np.unique(outputs[y][ownership[y]!=0]))for y in range(height)),default=0))
    report['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=compiled,pixel_masks=images,trace=trace),sort_keys=True).encode()).hexdigest()
    return report


def isolated_source(path,rgb8=(0,0,0)):
    if len(rgb8)!=3 or any(not isinstance(v,int)or not 0<=v<=255 for v in rgb8):raise ValueError('ISOLATED_UNDERLAY_RGB8')
    source=Source(path);image_path='BYOR_PROOF/CONSTANT_UNDERLAY.PNG';stage='BYOR_PROOF/ISOLATED_STAGE.TXT'
    if any(key(n)in source.index for n in(image_path,stage)):raise ValueError('ISOLATED_VIRTUAL_ASSET_COLLISION')
    image=Image.new('P',(256,224),0);image.putpalette(list(rgb8)+[0]*765);stream=io.BytesIO();image.save(stream,format='PNG')
    files={image_path:stream.getvalue(),stage:('background '+image_path+'\npanel '+image_path+' none none\norder a\n').encode('ascii')}
    for name,data in files.items():source.index[key(name)]=(name,None);source.cache[key(name)]=data
    return source,stage,dict(underlay_rgb8=list(rgb8),virtual_stage=stage,virtual_stage_sha256=hashlib.sha256(files[stage]).hexdigest(),
        virtual_underlay=image_path,virtual_underlay_sha256=hashlib.sha256(files[image_path]).hexdigest(),authored_stage_pixels_present=False,
        source_actor_assets_unchanged=True,scope='Controlled constant underlay only; no authored stage, concurrent-actor timing or gameplay admission.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--underlay-rgb8',type=int,nargs=3,default=(0,0,0))
    p.add_argument('--time-limit',type=int,default=60);p.add_argument('--write-budget',type=int,default=120);p.add_argument('--lookahead',type=int,default=17)
    p.add_argument('--size',choices=('8','16','32','mixed'),default='mixed')
    p.add_argument('--prepared-dma-window',type=int)
    p.add_argument('--minimize-resource-load',action='store_true')
    p.add_argument('--bank-search',action='store_true')
    p.add_argument('--global-color-banks',action='store_true')
    p.add_argument('--maximum-frame-colors-per-bank',type=int)
    a=p.parse_args();source,stage,isolation=isolated_source(a.source,tuple(a.underlay_rgb8))
    if a.global_color_banks and not a.bank_search:raise ValueError('ISOLATED_GLOBAL_BANKS_REQUIRE_BANK_SEARCH')
    if a.maximum_frame_colors_per_bank is not None and not a.global_color_banks:raise ValueError('ISOLATED_FRAME_LIMIT_REQUIRES_GLOBAL_BANKS')
    if a.bank_search:r=fixed_bank_context(source,stage,json.loads(a.scene.read_text()),a.lookahead,a.time_limit,min(a.write_budget,21),a.global_color_banks,a.maximum_frame_colors_per_bank)
    else:r=probe(source,stage,json.loads(a.scene.read_text()),size='mixed'if a.size=='mixed'else int(a.size),write_budget=a.write_budget,lookahead=a.lookahead,time_limit=a.time_limit,
        solver_backend='cp-sat',color_math='precomposited',coalesce_opaque_choices=True,feasibility_only=not a.minimize_resource_load,align_visible_bounds=True,clip_horizontal=True,
        prepared_dma_window=a.prepared_dma_window,prepared_dma_partition=a.prepared_dma_window is not None)
    r.update(isolated_context=isolation,source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r.get(k)for k in('status','geometry','peak_scheduled_writes','peak_cgram_data_bytes','solver','isolated_context')}))


if __name__=='__main__':main()
