"""Measure a source model's static OBJ color demand and explicit alternatives.

No assets are rewritten. Color-reduction figures are deterministic examples,
not an optimal quantizer, visual acceptance or a runtime admission guarantee.
"""
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


def measure(path, model_name, role):
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
            frame_reports.append(dict(**frame, image_path=image_path, asset_sha256=sha(raw),
                colors=len(set(map(int,visible))), visible_pixels=int(visible.size),
                maximum_scanline_colors=max(map(len,line_sets), default=0),
                maximum_adjacent_new_colors=max((len(line_sets[y]-line_sets[y-1])
                                                 for y in range(1,len(line_sets))),default=0),
                frame_palette_matches_authority=(image.getpalette()==palette or visible.size==0)))
    if not histogram:
        raise ValueError('COLOR_MODEL_HAS_NO_VISIBLE_PIXELS: '+model_name)
    colors = np.array(sorted(histogram),dtype=np.int32)
    rgb = np.column_stack((colors&31,(colors>>5)&31,(colors>>10)&31))
    weights = np.array([histogram[int(c)] for c in colors],dtype=np.int64)
    alternatives = []
    for budget in (120,90,60):
        selected = [int(np.argmax(weights))]
        distances = np.sum((rgb-rgb[selected[0]])**2,axis=1)
        while len(selected)<min(budget,len(colors)):
            next_color = int(np.argmax(distances*weights))
            if distances[next_color]==0:
                break
            selected.append(next_color)
            distances = np.minimum(distances,np.sum((rgb-rgb[next_color])**2,axis=1))
        alternatives.append(dict(policy='EXAMPLE_WEIGHTED_GREEDY_RGB555_SOURCE_COLOR_REDUCTION',
            opaque_colors=len(selected), obj_palettes=(len(selected)+14)//15,
            remaining_obj_palettes=8-(len(selected)+14)//15,
            changed_pixel_fraction=float(weights[distances!=0].sum()/weights.sum()),
            rgb555_channel_rmse=float(np.sqrt(np.sum(distances*weights)/(3*weights.sum()))),
            maximum_rgb555_euclidean_error=float(np.sqrt(distances.max())),
            selected_rgb555=list(map(int,colors[selected])),
            scope='animation pixel-frequency sample, no timing weight; not runtime admission or visual approval'))
    peak = max(frame_reports,key=lambda r:r['colors'])
    hardware_source = ROOT.parent/'Mesen2/Core/SNES/SnesPpu.cpp'
    return dict(status='STATIC_OBJ_COLOR_RESOURCE_LIMIT' if peak['colors']>120 else 'STATIC_OBJ_COLOR_CAPACITY_WITHIN_LIMIT',source_sha256=sha(Path(path).read_bytes()),
        model=model['declaration'],role=role,model_source_path=model['source_path'],
        palette_authority=source.resolve(palette_path),alpha=model['properties'].get('alpha',[]),
        peak_frame=peak, animation_union_colors=len(colors),
        hardware=dict(obj_palette_banks=8,opaque_colors_per_bank=15,static_opaque_capacity=120,
            source=str(hardware_source),
            source_sha256=sha(hardware_source.read_bytes()) if hardware_source.is_file() else None,
            online_source='https://github.com/SourMesen/Mesen2/blob/master/Core/SNES/SnesPpu.cpp',
            invariants=['Palette=(flags>>1)&7','GetTilePixelColor<4>','color zero transparent','CGRAM offset=128+(palette<<4)+color']),
        static_color_deficit=peak['colors']-120,
        required_static_palettes=(peak['colors']+14)//15,
        frame_requirements=frame_reports,source_color_reduction_examples=alternatives,
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
    args=parser.parse_args()
    report=measure(args.source,args.model,args.role)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','static_color_deficit','required_static_palettes','animation_union_colors')},indent=2))
