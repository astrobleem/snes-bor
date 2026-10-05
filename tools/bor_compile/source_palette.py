"""Source-declared model palettes; no inferred historical global palette.

Indexed zero stays transparent. RGB8 -> RGB555 is a named hardware adaptation,
not color-count reduction. Alternate palettes retain source index identity.
"""
import hashlib
import io
import struct

from PIL import Image


def read_palette(source, path):
    resolved = source.resolve(path) if path.lower().endswith('.act') else source.image_path(path)
    raw = source.read(resolved)
    if resolved.lower().endswith('.act'):
        if len(raw) not in (768, 772):
            raise ValueError('MODEL_PALETTE_ACT_EXTENT: '+resolved)
        rgb = list(raw[:768])
    else:
        with Image.open(io.BytesIO(raw)) as image:
            if image.mode != 'P' or image.getpalette() is None:
                raise ValueError('MODEL_PALETTE_INDEXED_REQUIRED: '+resolved)
            rgb = image.getpalette()
        rgb += [0]*(768-len(rgb))
    values = [(rgb[i*3]>>3)|((rgb[i*3+1]>>3)<<5)|((rgb[i*3+2]>>3)<<10) for i in range(256)]
    values[0] = 0
    return dict(source_path=resolved, asset_sha256=hashlib.sha256(raw).hexdigest(),
                rgb8=rgb, rgb555=values,
                colors_sha256=hashlib.sha256(struct.pack('<256H',*values)).hexdigest(),
                hardware_adapter='RGB8_HIGH_BITS_TO_RGB555',
                transparency='source index zero')


def model_palettes(source, model):
    """Model is the source-derived discovery record, not a shipped manifest."""
    rows = model['properties'].get('palette', [])
    first = next((f for a in model['animations'] for f in a['frames']), None)
    path = rows[-1]['values'][0] if rows and rows[-1]['values'] else first['values'][0] if first else None
    if path is None:
        raise ValueError('MODEL_PALETTE_NO_AUTHORITY: '+model['source_path'])
    if path.lower() == 'none':
        return dict(policy='SOURCE_PER_FRAME', base=None, alternates=[],
                    authority=rows[-1], semantics_reference='https://chronocrash.com/obor/wiki/palette/')
    base = read_palette(source,path)
    base['inference'] = 'explicit palette' if rows else 'first frame of first animation'
    alternates = []
    for index,row in enumerate(model['properties'].get('alternatepal', []),1):
        if len(row['values']) != 1:
            raise ValueError('MODEL_ALTERNATE_PALETTE_SCHEMA: '+model['source_path'])
        alternates.append(dict(map=index, declaration=row, **read_palette(source,row['values'][0])))
    return dict(policy='SOURCE_MODEL_INDEXED',base=base,alternates=alternates,
                semantics_reference='https://chronocrash.com/obor/wiki/palette/')
