"""S7 source-frame resource inventory; encoding is not live publication proof.

Foreign images are inspected without assuming their palette/dialect semantics.
Transparent-only 16x32 cells can be omitted; no nontransparent pixels are cropped.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image
from compiler import Source


def measure_frame(raw):
    with Image.open(io.BytesIO(raw)) as image:
        width, height = image.size
        result = dict(dimensions=[width, height], image_mode=image.mode,
                      canvas_cells=((width+15)//16)*((height+31)//32))
        if image.mode != 'P' or getattr(image, 'n_frames', 1) != 1:
            return dict(result, status='MEDIA_CONTRACT_REQUIRED')
        pixels = image.tobytes()
    cells = []
    for y in range(0, height, 32):
        for x in range(0, width, 16):
            if any(pixels[yy*width+xx] for yy in range(y, min(y+32,height))
                   for xx in range(x, min(x+16,width))):
                cells.append([x,y])
    # Index-zero transparency is conditional outside the historical dialect.
    return dict(result, status='INDEX_ZERO_TRANSPARENCY_MEASURED', cells=cells,
        pieces=len(cells), tiles=len(cells)*8, transfer_bytes=len(cells)*256,
        source_colors=len(set(pixels)-{0}),
        exceeds_single_frame_oam=len(cells)>128,
        exceeds_current_frame_encoder=len(cells)>32)


def inventory(pak, report):
    source = Source(pak)
    raw = Path(report).read_bytes()
    data = json.loads(raw)
    cache, frames, failures = {}, [], []
    for name, model in sorted(data['models'].items()):
        for animation in model['ir']['animations']:
            for index, frame in enumerate(animation['frames']):
                path = frame['source_path']
                try:
                    if path not in cache:
                        payload = source.read(path)
                        digest = hashlib.sha256(payload).hexdigest()
                        cache[path] = (digest,measure_frame(payload))
                    digest, measured = cache[path]
                    if digest != frame['asset_sha256']:
                        raise ValueError('SOURCE_ASSET_HASH_MISMATCH')
                    frames.append(dict(model=name,role=animation['role'],frame=index,
                        source_path=path,source_sha256=digest,
                        dialect=model['ir']['dialect'],**measured))
                except (OSError,ValueError,KeyError) as error:
                    failures.append(dict(model=name,role=animation['role'],frame=index,
                                         source_path=path,error=str(error)))
    measured = [f for f in frames if 'pieces' in f]
    return dict(project_id=data['project_id'],input_report_sha256=hashlib.sha256(raw).hexdigest(),
        models=len(data['models']),frames=frames,failures=failures,
        maximum_pieces=max(measured,key=lambda f:f['pieces'],default=None),
        maximum_width=max(frames,key=lambda f:f['dimensions'][0],default=None),
        maximum_height=max(frames,key=lambda f:f['dimensions'][1],default=None),
        publication_certified=False,
        note='Foreign palette/transparency semantics not certified. Tile counts use '
             'the current 16x32 cell decomposition, not a hardware-optimal lower bound.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',nargs=3,action='append',required=True,
                        metavar=('LABEL','PAK','REPORT'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result={label:inventory(pak,report) for label,pak,report in args.project}
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'frames.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    for label, project in result.items():
        maximum=project['maximum_pieces']
        print(label, 'models',project['models'],'frames',len(project['frames']),
              'failures',len(project['failures']), 'max pieces',maximum['pieces'] if maximum else None,
              'asset',maximum['source_path'] if maximum else None)


if __name__=='__main__':main()
