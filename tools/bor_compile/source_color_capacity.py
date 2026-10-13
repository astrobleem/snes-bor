"""Measure source RGB555 demand without modifying or reducing source colors."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from compiler import Source, ROOT
from source_profile import document, discover, sha
from source_palette import model_palettes


def measure(path, model_name, role, raster=False, banks=tuple(range(8)), piece_size=(8,8), color_masks=False, raster_all_frames=False):
    if raster_all_frames and not raster:raise ValueError('COLOR_ALL_RASTER_FRAMES_REQUIRES_RASTER')
    source = Source(path)
    docs = {k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure = discover(source,docs)
    models = [m for m in structure['models'] if m['declaration'].casefold()==model_name.casefold()]
    if len(models)!=1:
        raise ValueError('MODEL_NOT_UNIQUE: '+model_name)
    model = models[0]
    animations = [a for a in model['animations'] if a['role']==role]
    if len(animations)!=1:
        raise ValueError('ANIMATION_NOT_UNIQUE: '+role)
    frames = animations[0]['frames']
    palettes = model_palettes(source,model)
    if palettes['base'] is None:
        raise ValueError('MODEL_SHARED_PALETTE_REQUIRED_FOR_THIS_MEASUREMENT')
    palette_path = palettes['base']['source_path']
    palette = palettes['base']['rgb8']
    lut = np.array(palettes['base']['rgb555'])
    histogram, frame_reports = Counter(), []
    raster_pixels=[];frame_line_sets=[]
    for frame in frames:
        image_path = source.image_path(frame['values'][0])
        raw = source.read(image_path)
        with Image.open(io.BytesIO(raw)) as image:
            if image.mode!='P':
                raise ValueError('INDEXED_ACTOR_REQUIRED: '+image_path)
            indices = np.asarray(image)
            colors = lut[indices]
            visible = colors[indices!=0]
            histogram.update(map(int,visible))
            line_sets = [set(map(int,colors[y][indices[y]!=0])) for y in range(image.height)]
            frame_line_sets.append(line_sets)
            if raster:
                raster_pixels.append(np.where(indices!=0,colors,-1))
            frame_reports.append(dict(**frame, image_path=image_path, asset_sha256=sha(raw),
                colors=len(set(map(int,visible))), visible_pixels=int(visible.size),
                maximum_scanline_colors=max(map(len,line_sets), default=0),
                maximum_adjacent_union_colors=max((len(line_sets[y]|line_sets[y-1])
                                                  for y in range(1,len(line_sets))),default=0),
                adjacent_union_write_lower_bounds_by_bank_count={str(n):max(
                    (max(0,len(line_sets[y]|line_sets[y-1])-15*n)
                     for y in range(1,len(line_sets))),default=0)for n in range(1,9)},
                maximum_adjacent_new_colors=max((len(line_sets[y]-line_sets[y-1])
                                                 for y in range(1,len(line_sets))),default=0),
                frame_palette_matches_authority=(image.getpalette()==palette or visible.size==0)))
    if not histogram:
        raise ValueError('COLOR_MODEL_HAS_NO_VISIBLE_PIXELS: '+model_name)
    colors = np.array(sorted(histogram),dtype=np.int32)
    peak = max(frame_reports,key=lambda r:r['colors'])
    from raster_palette_interval import interval_bound
    peak_lines=frame_line_sets[frame_reports.index(peak)]
    raw_bounds={str(count):interval_bound(peak_lines,slots=15*count)for count in range(1,9)}
    raster_report=None;raster_frames=None
    if raster:
        from raster_palette import prove_frame
        raster_report=prove_frame(raster_pixels[frame_reports.index(peak)],piece_size,banks,color_masks=color_masks)
        if raster_all_frames:
            raster_frames=[dict(frame=i,image_path=f['image_path'],asset_sha256=f['asset_sha256'],
                **(raster_report if i==frame_reports.index(peak)else prove_frame(pixels,piece_size,banks,color_masks=color_masks)))
                for i,(f,pixels)in enumerate(zip(frame_reports,raster_pixels))]
    hardware_source = ROOT.parent/'Mesen2/Core/SNES/SnesPpu.cpp'
    return dict(status='STATIC_OBJ_COLOR_RESOURCE_LIMIT' if peak['colors']>120 else 'STATIC_OBJ_COLOR_CAPACITY_WITHIN_LIMIT',source_sha256=sha(Path(path).read_bytes()),
        model=model['declaration'],role=role,model_source_path=model['source_path'],
        palette_authority=source.resolve(palette_path),alpha=model['properties'].get('alpha',[]),
        peak_frame=peak, animation_union_colors=len(colors),
        maximum_animation_scanline_colors=max(r['maximum_scanline_colors']for r in frame_reports),
        maximum_animation_adjacent_new_colors=max(r['maximum_adjacent_new_colors']for r in frame_reports),
        peak_frame_raw_palette_interval_bounds_by_bank_count=raw_bounds,
        raw_palette_interval_scope='Optimistic source RGB555 residency only; excludes alpha context encoding and fixed bank assignment. Cannot prove feasibility or universally reject raster.',
        hardware=dict(obj_palette_banks=8,opaque_colors_per_bank=15,static_opaque_capacity=120,
            source=str(hardware_source),
            source_sha256=sha(hardware_source.read_bytes()) if hardware_source.is_file() else None,
            online_source='https://github.com/SourMesen/Mesen2/blob/master/Core/SNES/SnesPpu.cpp',
            invariants=['Palette=(flags>>1)&7','GetTilePixelColor<4>','color zero transparent','CGRAM offset=128+(palette<<4)+color']),
        static_color_deficit=peak['colors']-120,
        required_static_palettes=(peak['colors']+14)//15,
        frame_requirements=frame_reports,raster_peak_frame=raster_report,raster_all_frame_results=raster_frames,
        other_options=[dict(policy='RASTER_PALETTE_REUSE',
            fidelity='Potential RGB555 color preservation; not proven.',
            costs='Per-line CGRAM traffic and fixed OAM bank/index constraints; competes with actor palettes and HDMA.',
            measurements=dict(peak_frame_max_line_colors=peak['maximum_scanline_colors'],
                              peak_frame_max_adjacent_new_colors=peak['maximum_adjacent_new_colors']),
            admission='NOT_PROVEN; no impossibility inference from full-frame color count'),
            dict(policy='BG_EFFECT_RENDERER',fidelity='Potential RGB555 color preservation; not proven.',
                 costs='Dedicated BG resources or software compositing; conflicts with stage frontpanel, background and HUD allocation.',
                 admission='NOT_PROVEN')],
        nonclaims=['No universal SNES rendering impossibility proof.',
                   'Color demand is before alpha compositing; alpha fidelity is a separate unresolved capability.',
                   'No quantization, artwork resize, source substitution or candidate build performed.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--role',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--raster',action='store_true')
    parser.add_argument('--raster-all-frames',action='store_true')
    parser.add_argument('--banks',default='0,1,2,3,4,5,6,7')
    parser.add_argument('--piece-size',default='8,8')
    parser.add_argument('--color-masks',action='store_true')
    args=parser.parse_args()
    report=measure(args.source,args.model,args.role,args.raster,
                   tuple(map(int,args.banks.split(','))),tuple(map(int,args.piece_size.split(','))),args.color_masks,args.raster_all_frames)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','static_color_deficit','required_static_palettes','animation_union_colors')},indent=2))
