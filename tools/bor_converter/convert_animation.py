#!/usr/bin/env python3
"""Convert a full OpenBOR animation (all frames of one `anim` block from an
entity .txt) into SNES-native 4bpp source data, using ONE shared scale
factor and ONE shared 16-color palette across every frame.

convert_sprite.py handles a single isolated frame: it crops to that frame's
own bounding box and independently centers/feet-aligns it, which is fine in
isolation but wrong for an animation -- different frames of e.g. a walk
cycle have different bounding boxes (arm swings, stride width), so
per-frame independent centering would make the character visibly jitter/
resize frame to frame instead of animating in place. OpenBOR's own `offset`
directive (parsed by entity_parse.py) gives the fix: it's the hotspot pixel,
in each frame's own original-image coordinates, that should land at a fixed
position on screen -- i.e. the character's ground-contact point. Anchoring
every frame to that shared hotspot (rather than to each frame's own bbox
center) keeps the animation visually stable.

Algorithm:
  1. For each frame, compute its own tight foreground bbox (via the same
     background-distance threshold convert_sprite.py uses) in original
     image pixel coordinates, and express that bbox relative to the
     frame's hotspot (its `offset` value).
  2. Take the union of those hotspot-relative bboxes across all frames --
     this is the space the whole animation needs, anchored at (0,0) = the
     hotspot. Pick ONE scale factor that fits that union into the 32x48
     target, so every frame is scaled identically (no per-frame resizing
     artifacts).
  3. Place each frame's scaled crop into the canvas at the position implied
     by its hotspot-relative offset and the shared scale -- frames whose
     bbox sits closer to the hotspot end up correspondingly closer to the
     shared anchor point on screen.
  4. Build ONE shared palette: stack every frame's canvas into a single
     tall image and run MEDIANCUT quantization once across all of them
     (same background-pixel-averaging trick as convert_sprite.py, applied
     per frame before stacking), then slice the quantized result back into
     per-frame index bitmaps. Because they were quantized together, every
     frame's indices already refer to the same shared 16-color palette --
     no separate nearest-color remapping step needed.

Usage:
    python convert_animation.py <pak_path> <entity_txt_entry> <anim_name> <out_dir>

Example:
    python convert_animation.py "Beats of Rage Original [v.3.0 Build 4086].pak" \\
        "DATA\\CHARS\\RALF\\RALF.TXT" idle out/ralf_idle
    # -> out/ralf_idle/frame00.bin .. frame05.bin, palette.txt, manifest.json, preview.png
"""
import sys
import os
import json
from PIL import Image

sys.path.append(os.path.dirname(__file__))
from pak_extract import extract
from entity_parse import parse_entity
from convert_sprite import dist2, to_bgr555, BG_DIST_THRESHOLD, MAX_COLORS

TARGET_W, TARGET_H = 32, 48


def _frame_bbox_and_bg(rgb_im):
    bg_rgb = rgb_im.getpixel((0, 0))
    w, h = rgb_im.size
    px = rgb_im.load()
    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if dist2(px[x, y], bg_rgb) > BG_DIST_THRESHOLD ** 2:
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    return (minx, miny, maxx, maxy)


def convert_animation(pak_path, entity_entry_name, anim_name, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    entity_data = extract(pak_path, entity_entry_name)
    entity = parse_entity(entity_data.decode('latin1'))
    anim = entity['animations'].get(anim_name)
    if anim is None:
        raise KeyError(f'no animation {anim_name!r} in {entity_entry_name!r} '
                        f'(have: {list(entity["animations"])})')
    frames_meta = anim['frames']
    if not frames_meta:
        raise ValueError(f'animation {anim_name!r} has no frames')

    base_dir = entity_entry_name.replace('/', '\\').rsplit('\\', 1)[0]

    frame_ims = []      # RGB Image per frame, original resolution
    frame_bg = []
    frame_bbox = []      # (minx,miny,maxx,maxy) in original coords
    frame_hotspot = []   # (hx,hy) from entity offset, defaulting to bbox center-bottom

    for fm in frames_meta:
        gif_name = fm['gif'].replace('/', '\\')
        # entries in the .pak are stored relative to DATA\..., convert_sprite's
        # extract() matches case-insensitively so this simple join is enough
        if '\\' not in gif_name:
            gif_name = base_dir + '\\' + gif_name
        gif_bytes = extract(pak_path, gif_name)
        tmp_path = os.path.join(out_dir, '_tmp_' + os.path.basename(gif_name))
        with open(tmp_path, 'wb') as f:
            f.write(gif_bytes)
        im = Image.open(tmp_path).convert('RGB')
        os.remove(tmp_path)

        bbox = _frame_bbox_and_bg(im)
        bg_rgb = im.getpixel((0, 0))
        hotspot = fm['offset'] if fm['offset'] is not None else (
            (bbox[0] + bbox[2]) // 2, bbox[3])

        frame_ims.append(im)
        frame_bg.append(bg_rgb)
        frame_bbox.append(bbox)
        frame_hotspot.append(hotspot)

    # --- shared scale: union of hotspot-relative bboxes across all frames ---
    rel = []
    for (minx, miny, maxx, maxy), (hx, hy) in zip(frame_bbox, frame_hotspot):
        rel.append((minx - hx, miny - hy, maxx - hx, maxy - hy))
    union_minx = min(r[0] for r in rel)
    union_miny = min(r[1] for r in rel)
    union_maxx = max(r[2] for r in rel)
    union_maxy = max(r[3] for r in rel)
    extent_w = union_maxx - union_minx + 1
    extent_h = union_maxy - union_miny + 1
    scale = min(TARGET_W / extent_w, TARGET_H / extent_h)

    hx_canvas = round(-union_minx * scale)
    hy_canvas = round(-union_miny * scale)

    # --- place each frame into its own 32x48 canvas at the shared scale/anchor ---
    canvases = []
    masks = []
    for im, bg_rgb, (minx, miny, maxx, maxy), (hx, hy) in zip(
            frame_ims, frame_bg, frame_bbox, frame_hotspot):
        crop = im.crop((minx, miny, maxx + 1, maxy + 1))
        cw, ch = crop.size
        new_w, new_h = max(1, round(cw * scale)), max(1, round(ch * scale))
        resized = crop.resize((new_w, new_h), Image.NEAREST)

        canvas = Image.new('RGB', (TARGET_W, TARGET_H), bg_rgb)
        px_pos = hx_canvas + round((minx - hx) * scale)
        py_pos = hy_canvas + round((miny - hy) * scale)
        canvas.paste(resized, (px_pos, py_pos))
        canvases.append(canvas)

        cpx = canvas.load()
        mask = [[dist2(cpx[x, y], bg_rgb) > BG_DIST_THRESHOLD ** 2
                 for x in range(TARGET_W)] for y in range(TARGET_H)]
        masks.append(mask)

    # --- shared palette: replace background with one global avg fg color,
    # stack all frames vertically, quantize once ---
    all_fg = [canvases[i].load()[x, y]
              for i in range(len(canvases))
              for y in range(TARGET_H) for x in range(TARGET_W) if masks[i][y][x]]
    if not all_fg:
        raise ValueError('no foreground pixels survived the background threshold in any frame')
    avg_fg = tuple(sum(c[k] for c in all_fg) // len(all_fg) for k in range(3))

    n = len(canvases)
    stack = Image.new('RGB', (TARGET_W, TARGET_H * n))
    for i, canvas in enumerate(canvases):
        cpx = canvas.load()
        spx = stack.load()
        for y in range(TARGET_H):
            for x in range(TARGET_W):
                spx[x, i * TARGET_H + y] = cpx[x, y] if masks[i][y][x] else avg_fg

    quant = stack.quantize(colors=MAX_COLORS, method=Image.MEDIANCUT)
    qpal = quant.getpalette()
    qpx = quant.load()

    palette = {0: (0, 0, 0)}
    frame_indices = []
    for i in range(n):
        indices = [[0] * TARGET_W for _ in range(TARGET_H)]
        for y in range(TARGET_H):
            for x in range(TARGET_W):
                if masks[i][y][x]:
                    qi = qpx[x, i * TARGET_H + y] + 1
                    indices[y][x] = qi
                    palette.setdefault(qi, tuple(qpal[(qi - 1) * 3:(qi - 1) * 3 + 3]))
        frame_indices.append(indices)

    # --- write outputs ---
    bin_paths = []
    for i, indices in enumerate(frame_indices):
        out_bin = bytearray(indices[y][x] & 0x0F for y in range(TARGET_H) for x in range(TARGET_W))
        bin_path = os.path.join(out_dir, f'frame{i:02d}.bin')
        with open(bin_path, 'wb') as f:
            f.write(out_bin)
        bin_paths.append(bin_path)

    pal_path = os.path.join(out_dir, 'palette.txt')
    with open(pal_path, 'w') as f:
        for idx in range(16):
            rgb_val = palette.get(idx, (0, 0, 0))
            f.write(f'    lda #${to_bgr555(rgb_val):04X}\n')

    manifest = {
        'entity': entity['name'], 'anim': anim_name, 'loop': anim['loop'],
        'scale': scale, 'hotspot_canvas': [hx_canvas, hy_canvas],
        'frames': [
            {'delay': fm['delay'], 'offset': fm['offset'], 'bbox': fm['bbox'],
             'attack': fm['attack'], 'move': fm['move'], 'bin': os.path.basename(p)}
            for fm, p in zip(frames_meta, bin_paths)
        ],
    }
    manifest_path = os.path.join(out_dir, 'manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    preview = Image.new('RGB', (TARGET_W * n, TARGET_H))
    ppx = preview.load()
    for i, indices in enumerate(frame_indices):
        for y in range(TARGET_H):
            for x in range(TARGET_W):
                ppx[i * TARGET_W + x, y] = palette.get(indices[y][x], (255, 0, 255))
    preview_path = os.path.join(out_dir, 'preview.png')
    preview.resize((TARGET_W * n * 4, TARGET_H * 4), Image.NEAREST).save(preview_path)

    return {
        'frames': n, 'colors_used': len(palette), 'scale': scale,
        'bin_paths': bin_paths, 'pal_path': pal_path,
        'manifest_path': manifest_path, 'preview_path': preview_path,
    }


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        raise SystemExit(1)
    pak_path, entity_entry, anim_name, out_dir = sys.argv[1:5]
    result = convert_animation(pak_path, entity_entry, anim_name, out_dir)
    for k, v in result.items():
        print(f'{k}: {v}')


if __name__ == '__main__':
    main()
