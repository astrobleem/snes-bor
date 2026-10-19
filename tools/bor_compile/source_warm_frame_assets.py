"""Lossless indexed He-Man SELECT/IDLE/WALK artwork pack.

This is an asset-only source derivation, not a renderer or live runtime binding.
`derive(Source)` returns a JSON-safe manifest plus `image_blobs` (one self-
contained WFR1 blob per unique indexed image) and `metadata` (WFM1 table).
The fixed 32-byte pose records and image directory contain offsets relative to
the separate image blob; a ROM scatter allocator assigns CPU addresses later.

Only opaque indexed He_Man source frames on its declared model palette/map 0
are admitted. Alpha, global/drawmethod palette remaps, other models, and map
domains are explicitly outside this pack. Indexed zero is transparent. Source
indices are preserved byte-for-byte; RGB555 palette conversion is evidence,
not image recoloring. No pose, crop, palette or animation timing is inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

from compiler import Source, key
from source_profile import document, discover
from source_palette import model_palettes, select_model_palette
from dialect_4086 import animation_frames
from source_model_registry import derive as model_registry
from source_animation_init_4086 import derive as animation_registry

IMAGE_MAGIC = b'WFR1'
META_MAGIC = b'WFM1'
VERSION = 1
DESCRIPTOR_SIZE = 32
META_HEADER = struct.Struct('<4sHHHHI')  # magic, version, stride, poses, images, reserved
DESC = struct.Struct('<6H2h4HIHH')
IMAGE_HEADER = struct.Struct('<4sHHH')   # magic, width, height, RLE byte count
IMAGE_DIR = struct.Struct('<IHHHH')      # relative offset, byte length, width, height, reserved


def _fail(tag):
    raise ValueError(tag)


def encode_image(indices):
    """Encode a uint8 indexed image as WFR1 plus row offsets and (count,index) runs."""
    array = np.asarray(indices)
    if array.ndim != 2 or array.dtype != np.uint8:
        _fail('WARM_IMAGE_UINT8_2D_REQUIRED')
    height, width = array.shape
    if not 1 <= width <= 511 or not 1 <= height <= 255:
        _fail('WARM_IMAGE_GEOMETRY')
    payload = bytearray()
    offsets = [0]
    for row in array:
        x = 0
        while x < width:
            value = int(row[x]); end = x + 1
            while end < width and int(row[end]) == value and end - x < 255:
                end += 1
            payload.extend((end - x, value))
            x = end
        offsets.append(len(payload))
    if len(payload) > 0x7fff:
        _fail('WARM_IMAGE_COMPRESSED_LIMIT')
    header = IMAGE_HEADER.pack(IMAGE_MAGIC, width, height, len(payload))
    rows = struct.pack('<' + 'H' * len(offsets), *offsets)
    blob = header + rows + payload
    if len(blob) >= 0x8000:
        _fail('WARM_IMAGE_BLOB_LIMIT')
    return blob


def decode_image(blob):
    """Validate and decode one complete WFR1 blob; malformed extents reject."""
    data = bytes(blob)
    if len(data) < IMAGE_HEADER.size:
        _fail('WARM_IMAGE_TRUNCATED_HEADER')
    magic, width, height, payload_size = IMAGE_HEADER.unpack_from(data)
    if magic != IMAGE_MAGIC or not 1 <= width <= 511 or not 1 <= height <= 255:
        _fail('WARM_IMAGE_HEADER')
    table_end = IMAGE_HEADER.size + (height + 1) * 2
    expected = table_end + payload_size
    if len(data) != expected or expected >= 0x8000:
        _fail('WARM_IMAGE_EXTENT')
    offsets = struct.unpack_from('<' + 'H' * (height + 1), data, IMAGE_HEADER.size)
    if offsets[0] != 0 or offsets[-1] != payload_size:
        _fail('WARM_IMAGE_ROW_EXTENT')
    if any(a > b for a, b in zip(offsets, offsets[1:])):
        _fail('WARM_IMAGE_ROW_ORDER')
    body = data[table_end:]
    result = np.empty((height, width), dtype=np.uint8)
    for y, (start, stop) in enumerate(zip(offsets, offsets[1:])):
        if start == stop or (stop - start) % 2:
            _fail('WARM_IMAGE_ROW_ENCODING')
        x = start
        out = 0
        while x < stop:
            count, value = body[x], body[x + 1]
            if count == 0 or out + count > width:
                _fail('WARM_IMAGE_RUN')
            result[y, out:out + count] = value
            out += count; x += 2
        if out != width:
            _fail('WARM_IMAGE_ROW_WIDTH')
    return result


def screen_geometry(descriptor, x, z, direction):
    """Raw source compositor placement and nonzero bounds for one facing.

    Direction 1 uses anchor_x-offset_x. Direction 0 mirrors the full indexed
    raster and uses anchor_x-(width-offset_x), matching source_scene_bg.
    Returned rectangles are half-open and intentionally unclipped.
    """
    if direction not in (0, 1):
        _fail('WARM_DIRECTION_DOMAIN')
    w, h = descriptor['width'], descriptor['height']
    ox, oy = descriptor['offset']
    x0, y0, x1, y1 = descriptor['bounds']
    left = int(x) - (ox if direction == 1 else w - ox)
    top = int(z) - oy
    if direction == 0:
        x0, x1 = w - x1, w - x0
    return dict(left=left, top=top,
                visible=[left + x0, top + y0, left + x1, top + y1])


def pack_metadata(poses, images):
    """Build WFM1 directory + 32-byte pose rows; blobs remain a separate file."""
    rows = list(poses)
    image_rows = list(images)
    if not rows or not image_rows or len(rows) > 65535 or len(image_rows) > 65535:
        _fail('WARM_META_COUNT')
    out = bytearray(META_HEADER.pack(META_MAGIC, VERSION, DESCRIPTOR_SIZE,
                                    len(rows), len(image_rows), 0))
    seen = set()
    for image in image_rows:
        offset, length = image['image_offset'], image['image_length']
        width, height = image['width'], image['height']
        if not 0 <= offset <= 0xffffffff or not 1 <= length < 0x8000 or not 1 <= width <= 511 or not 1 <= height <= 255:
            _fail('WARM_META_IMAGE_DOMAIN')
        out.extend(IMAGE_DIR.pack(offset, length, width, height, 0))
    for pose in rows:
        key_tuple = (pose['model_id'], pose['handle'], pose['frame'])
        if key_tuple in seen:
            _fail('WARM_META_DUPLICATE_POSE')
        seen.add(key_tuple)
        if (not 0 <= pose['model_id'] <= 0xffff or not 1 <= pose['handle'] <= 0xffff
                or not 0 <= pose['frame'] <= 0xffff or pose['palette_map'] != 0
                or not -0x8000 <= pose['offset'][0] <= 0x7fff
                or not -0x8000 <= pose['offset'][1] <= 0x7fff):
            _fail('WARM_META_POSE_DOMAIN')
        index = pose['image_index']
        if not 0 <= index < len(image_rows):
            _fail('WARM_META_IMAGE_INDEX')
        image = image_rows[index]
        x0, y0, x1, y1 = pose['bounds']
        ox, oy = pose['offset']
        if (pose['width'], pose['height']) != (image['width'], image['height']):
            _fail('WARM_META_DIMENSIONS')
        if not (0 <= x0 <= x1 <= pose['width'] and 0 <= y0 <= y1 <= pose['height']):
            _fail('WARM_META_BOUNDS')
        out.extend(DESC.pack(pose['model_id'], pose['handle'], pose['frame'], index,
                             pose['width'], pose['height'], ox, oy, x0, y0, x1, y1,
                             image['image_offset'], image['image_length'], pose['palette_map']))
    return bytes(out)


def unpack_metadata(data, image_data=None):
    """Validate WFM1 records, keys, row references and declared image extents."""
    raw = bytes(data)
    if len(raw) < META_HEADER.size:
        _fail('WARM_META_TRUNCATED')
    magic, version, stride, pose_count, image_count, reserved = META_HEADER.unpack_from(raw)
    expected = META_HEADER.size + image_count * IMAGE_DIR.size + pose_count * DESCRIPTOR_SIZE
    if (magic != META_MAGIC or version != VERSION or stride != DESCRIPTOR_SIZE or reserved
            or not pose_count or not image_count or len(raw) != expected):
        _fail('WARM_META_HEADER')
    images = []
    cursor = META_HEADER.size
    for _ in range(image_count):
        offset, length, width, height, zero = IMAGE_DIR.unpack_from(raw, cursor); cursor += IMAGE_DIR.size
        if zero or not 1 <= length < 0x8000 or not 1 <= width <= 511 or not 1 <= height <= 255:
            _fail('WARM_META_IMAGE_RECORD')
        if image_data is not None:
            if offset + length > len(image_data):
                _fail('WARM_META_IMAGE_EXTENT')
            decoded = decode_image(memoryview(image_data)[offset:offset + length])
            if decoded.shape != (height, width):
                _fail('WARM_META_IMAGE_GEOMETRY')
        images.append(dict(image_offset=offset, image_length=length, width=width, height=height))
    poses = []; seen = set()
    for _ in range(pose_count):
        fields = DESC.unpack_from(raw, cursor); cursor += DESCRIPTOR_SIZE
        model, handle, frame, image_index, width, height, ox, oy, x0, y0, x1, y1, offset, length, palette_map = fields
        key_tuple = (model, handle, frame)
        if key_tuple in seen:
            _fail('WARM_META_DUPLICATE_POSE')
        seen.add(key_tuple)
        if image_index >= image_count:
            _fail('WARM_META_IMAGE_INDEX')
        image = images[image_index]
        if ((width, height, offset, length) != (image['width'], image['height'], image['image_offset'], image['image_length'])
                or not (0 <= x0 <= x1 <= width and 0 <= y0 <= y1 <= height)):
            _fail('WARM_META_POSE_RECORD')
        poses.append(dict(model_id=model, handle=handle, frame=frame, image_index=image_index,
                          width=width, height=height, offset=[ox, oy], bounds=[x0, y0, x1, y1],
                          image_offset=offset, image_length=length, palette_map=palette_map))
    return dict(images=images, poses=poses)


def derive(source):
    """Derive all frames for He_Man SELECT/IDLE/WALK from a compiler.Source."""
    docs = {k: document(source, name) for k, (name, _) in source.index.items() if k.endswith('.txt')}
    candidates = [m for m in discover(source, docs)['models'] if m['name'].casefold() == 'he_man']
    if len(candidates) != 1:
        _fail('WARM_HEMAN_IDENTITY')
    model = candidates[0]
    alpha = model['properties'].get('alpha', [])
    if alpha and int(alpha[-1]['values'][0]) != 0:
        _fail('WARM_ALPHA_UNSUPPORTED')
    palettes = model_palettes(source, model)
    if palettes['policy'] != 'SOURCE_MODEL_INDEXED' or palettes['base'] is None:
        _fail('WARM_PALETTE_POLICY_UNSUPPORTED')
    palette, selected_map = select_model_palette(palettes, 0)
    if selected_map != 0:
        _fail('WARM_PALETTE_MAP_UNSUPPORTED')
    animation_ids = animation_registry(source)['animations']
    model_id = next((row['id'] for row in model_registry(source)['models']
                     if row['identity'].casefold() == 'he_man'), None)
    if model_id is None:
        _fail('WARM_MODEL_IDENTITY_UNBOUND')

    anim_rows = animation_frames(docs[key(model['source_path'])]['directives'])
    role_to_frames = {a['role'].casefold(): a for a in anim_rows}
    poses, images, blobs = [], [], []
    image_by_digest = {}
    for role in ('select', 'idle', 'walk'):
        if role not in role_to_frames:
            _fail('WARM_ANIMATION_MISSING_' + role.upper())
        identity = [a for a in animation_ids if a['model'].casefold() == 'he_man' and a['role'].casefold() == role]
        if len(identity) != 1:
            _fail('WARM_ANIMATION_HANDLE_IDENTITY')
        handle = identity[0]['handle']
        for frame in role_to_frames[role]['frames']:
            source_path = source.image_path(frame['declaration']['values'][0])
            raw = source.read(source_path)
            sha = hashlib.sha256(raw).hexdigest()
            with Image.open(io.BytesIO(raw)) as im:
                im.load()
                if im.mode != 'P' or im.getpalette() is None or getattr(im, 'n_frames', 1) != 1:
                    _fail('WARM_INDEXED_STILL_REQUIRED')
                indices = np.asarray(im, dtype=np.uint8).copy()
            height, width = indices.shape
            if not 1 <= width <= 511 or not 1 <= height <= 255:
                _fail('WARM_IMAGE_GEOMETRY')
            # A referenced asset is keyed by canonical source path. The pack
            # keeps two differently named source files distinct even if their
            # PNG payloads are byte-identical; manifest hashes make that fact
            # explicit for later deduplication decisions.
            digest = source_path.casefold()
            if digest not in image_by_digest:
                blob = encode_image(indices)
                image_index = len(images)
                image_by_digest[digest] = image_index
                images.append(dict(image_index=image_index, source_path=source_path,
                                   source_png_sha256=sha, index_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
                                   width=width, height=height, image_offset=0,
                                   image_length=len(blob), encoded_sha256=hashlib.sha256(blob).hexdigest()))
                blobs.append(blob)
            else:
                image_index = image_by_digest[digest]
                images[image_index].setdefault('source_aliases', []).append(source_path)
            yy, xx = np.nonzero(indices)
            bounds = [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1] if len(xx) else [0, 0, 0, 0]
            offset = list(frame['offset'])
            poses.append(dict(model_id=model_id, handle=handle, frame=frame['index'], role=role,
                              image_index=image_index, width=width, height=height, offset=offset,
                              bounds=bounds, palette_map=0, source_path=source_path, source_png_sha256=sha))

    # Each unique source frame is stored once. Assign deterministic relative offsets.
    cursor = 0
    for image, blob in zip(images, blobs):
        image['image_offset'] = cursor
        cursor += len(blob)
    packed_metadata = pack_metadata(poses, images)

    # Exact masked actor-color compatibility against the accepted static palette.
    target_indices = set()
    for image in images:
        for alias in [image['source_path'], *image.get('source_aliases', [])]:
            with Image.open(io.BytesIO(source.read(alias))) as im:
                target_indices.update(int(v) for v in np.unique(np.asarray(im, dtype=np.uint8)) if int(v) != 0)
    target_colors = {int(palette['rgb555'][i]) & ~0x420 for i in target_indices}
    accepted_path = Path(__file__).resolve().parents[2] / 'out/byor-motu-online-v3/assets/initial.json'
    accepted_slots = json.loads(accepted_path.read_text()) if accepted_path.exists() else None
    if accepted_slots is not None:
        accepted_colors = {int(v) & ~0x420 for v in accepted_slots if v is not None}
        missing_colors = target_colors - accepted_colors
        lut_path = Path(__file__).resolve().parents[2] / 'out/byor-motu-online-v3/assets/actor-palette.bin'
        if lut_path.exists():
            lut_raw = lut_path.read_bytes()
            if len(lut_raw) != 512:
                _fail('WARM_ACCEPTED_ACTOR_LUT_EXTENT')
            lut = struct.unpack('<256H', lut_raw)
            missing_source_indices = sorted(i for i in target_indices
                                           if (int(palette['rgb555'][i]) & ~0x420) in missing_colors)
            lut_unmapped = [i for i in missing_source_indices if lut[i] == 0]
            actor_lut_comparison = dict(path=str(lut_path.relative_to(Path(__file__).resolve().parents[2]).as_posix()),
                                        sha256=hashlib.sha256(lut_raw).hexdigest(),
                                        missing_color_source_indices=missing_source_indices,
                                        missing_color_indices_with_zero_lut_word=lut_unmapped,
                                        all_missing_color_indices_unmapped=lut_unmapped == missing_source_indices,
                                        semantics='accepted 16-bit source-index draw-code lookup; zero means no accepted mapped draw code here')
        else:
            actor_lut_comparison = dict(available=False)
        color_difference = dict(target_masked_colors=len(target_colors), accepted_palette_colors=len(accepted_colors),
                                missing_from_accepted=sorted(missing_colors),
                                extra_in_accepted=sorted(accepted_colors - target_colors),
                                exact_subset=not missing_colors,
                                actor_palette_lookup=actor_lut_comparison,
                                accepted_palette_source=str(accepted_path.relative_to(Path(__file__).resolve().parents[2]).as_posix()))
    else:
        color_difference = dict(target_masked_colors=len(target_colors), accepted_palette_available=False,
                                exact_subset=None, note='accepted out/byor-motu-online-v3/assets/initial.json not present')

    manifest = dict(schema='BYOR_WARM_FRAME_ASSETS_V1', source_pak_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest()
                    if source.path.is_file() else None,
                    model=dict(identity='He_Man', model_id=model_id, source_path=model['source_path'],
                               source_sha256=docs[key(model['source_path'])]['sha256']),
                    palette=dict(source_path=palette['source_path'], png_sha256=palette['asset_sha256'],
                                 colors_sha256=palette['colors_sha256'], selected_map=selected_map,
                                 hardware_adapter=palette['hardware_adapter'], transparency=palette['transparency']),
                    roles=['select', 'idle', 'walk'], pose_count=len(poses), unique_image_count=len(images),
                    descriptor_stride=DESCRIPTOR_SIZE, image_format='WFR1: header + (height+1) u16 payload-relative row offsets + per-row (count,index) pairs',
                    metadata_format='WFM1: header + 12-byte relative image directory + 32-byte pose records; image bytes separate',
                    poses=poses, images=images, masked_color_comparison=color_difference,
                    unsupported=['models other than He_Man', 'alpha/translucent actors', 'alternate/global/drawmethod palette maps',
                                 'runtime frame selection/binding', 'collision/damage rectangles', 'scene map composition',
                                 'ROM CPU address assignment'])
    return dict(manifest=manifest, image_blobs=tuple(blobs), metadata=packed_metadata)


def write_evidence(source, output):
    result = derive(Source(source))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    image_bytes = b''.join(result['image_blobs'])
    (output / 'asset-images.bin').write_bytes(image_bytes)
    (output / 'asset-metadata.bin').write_bytes(result['metadata'])
    (output / 'asset-manifest.json').write_text(json.dumps(result['manifest'], indent=2) + '\n', encoding='utf-8')
    report = dict(schema='BYOR_WARM_FRAME_ASSET_EVIDENCE_V1', source_pak_sha256=result['manifest']['source_pak_sha256'],
                  counts=dict(poses=result['manifest']['pose_count'], unique_images=result['manifest']['unique_image_count'],
                              image_bytes=len(image_bytes), metadata_bytes=len(result['metadata']),
                              largest_image=max(map(len, result['image_blobs'])),
                              distinct_png_payload_hashes=len({i['source_png_sha256'] for i in result['manifest']['images']})),
                  image_pack_sha256=hashlib.sha256(image_bytes).hexdigest(), metadata_sha256=hashlib.sha256(result['metadata']).hexdigest(),
                  palette_png_sha256=result['manifest']['palette']['png_sha256'],
                  source_images=[dict(path=i['source_path'], png_sha256=i['source_png_sha256'])
                                 for i in result['manifest']['images']],
                  unique_png_sha256=sorted({i['source_png_sha256'] for i in result['manifest']['images']}),
                  color_comparison=result['manifest']['masked_color_comparison'],
                  limitations=result['manifest']['unsupported'])
    (output / 'asset-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(write_evidence(args.source, args.output), indent=2))


if __name__ == '__main__':
    main()
