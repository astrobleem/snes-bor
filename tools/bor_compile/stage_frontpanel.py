"""Normal-only materialization of authored frontpanel cycles.

Uses the owner's existing source/Normal StageIR cache. Does not select by
stage name, mutate shared bindings, or change runtime camera/parallax policy.
"""
import hashlib
import json
from pathlib import Path
import tempfile

from compiler import ROOT
from source_actor_numeric import verify_source

ADAPTER = 'NORMAL_ORDERED_FP_CYCLE_INTEGER_CAMERA_V1'
MOTION_ADAPTER = 'ACCEPTED_COMPAT_NORMAL_FP_SCREEN_X_7_OVER_5_V1'
FILES = ('tiles.bin','tilemap.bin','palette.bin')


def lower_bg2(blobs, width, period):
    """Lossless indexed-color lowering: BG3 pal*4+i -> BG2 pal0 index.

    Index zero remains transparent; resulting colors address CGRAM 0..15.
    Deduplication includes the formerly separate palette identity.
    """
    import numpy as np
    import snes_tiles as st
    from convert_frontpanel import verify_window_budget
    source = blobs['tiles.bin']
    if len(source)%16 or not 1 <= period <= width:
        raise ValueError('FRONTPANEL_BG2_SOURCE_ABI')
    decoded = [st.decode_2bpp_tile(source[i:i+16]) for i in range(0,len(source),16)]
    entries = st.decode_tilemap_column_major(blobs['tilemap.bin'],width,28)
    tiles = []
    for tid,pal,hf,vf in entries:
        if not 0 <= tid < len(decoded) or not 1 <= pal <= 3:
            raise ValueError('FRONTPANEL_BG2_SOURCE_REFERENCE')
        tile = decoded[tid]
        if hf: tile = tile[:,::-1]
        if vf: tile = tile[::-1,:]
        tiles.append(np.where(tile == 0,0,pal*4+tile).astype(np.uint8))
    unique,mapped = st.dedup_tiles(np.asarray(tiles),np.zeros(len(tiles),dtype=np.uint8))
    wrapped_width = period+33
    wrapped = [mapped[y*width+x%period] for y in range(28) for x in range(wrapped_width)]
    peak,column = verify_window_budget(wrapped,wrapped_width,28,33)
    return dict(tiles_bin=st.encode_tileset(unique,bpp=4),
        tilemap_bin=st.encode_tilemap_column_major(mapped,width,28),
        unique_tiles=len(unique),peak_full_window=peak,peak_column=column,
        cgram_max=15,palette_id=0,bpp=4)


def sequence_directives(source, ir):
    if ir.diagnostics:
        raise ValueError('FRONTPANEL_SOURCE_UNCERTAIN')
    result = []
    for d in ir.directives:
        if d.name != 'frontpanel':
            continue
        if len(d.values) != 1:
            raise ValueError('FRONTPANEL_DIRECTIVE_ARITY')
        path = source.image_path(d.values[0])
        result.append(dict(source_path=path,line=d.line,
                           sha256=hashlib.sha256(source.read(path)).hexdigest()))
    return result


def validate_materialized(path, expected, width):
    """Validate fresh and cached bytes against live BG3 resource ownership."""
    import numpy as np
    from convert_frontpanel import frontpanel_runtime_limits,verify_sequence_resources,normal_font_palette_binding
    import snes_tiles as st
    manifest = json.loads((path/'manifest.json').read_text())
    blobs = {name:(path/name).read_bytes() for name in FILES}
    if manifest.get('owner_width_tiles',manifest.get('width_tiles')) != width:
        raise ValueError('FRONTPANEL_OWNER_WIDTH')
    expected_atlas_width = max(width,manifest.get('target_cycle_width',0)//8) if manifest.get('full_height_frontpanel') else width
    if manifest.get('width_tiles') != expected_atlas_width:
        raise ValueError('FRONTPANEL_ATLAS_WIDTH')
    width = expected_atlas_width
    if (manifest.get('sequence_adapter') != ADAPTER or manifest.get('streaming') is not True
            or manifest.get('layer') != 'BG3_frontpanel' or manifest.get('height_tiles') != 28
            or manifest.get('width_tiles') != width or manifest.get('content_width_tiles') != width
            or manifest.get('num_palettes') != 3 or manifest.get('palette_offset') != 1
            or manifest.get('colors_per_palette') != 4):
        raise ValueError('FRONTPANEL_MATERIALIZED_ABI')
    actual = manifest.get('frontpanel_sequence',[])
    if [(r['source_path'],r['sha256']) for r in actual] != [(r['source_path'],r['sha256']) for r in expected]:
        raise ValueError('FRONTPANEL_SEQUENCE_IDENTITY')
    count = manifest['unique_tiles']
    limits = frontpanel_runtime_limits()
    if manifest.get('full_height_frontpanel'):
        limits = dict(limits,row_start=0,row_count=28)
    if not 1 <= count <= limits['tile_ids']:
        raise ValueError('FRONTPANEL_TILE2SLOT_CAPACITY')
    if manifest.get('source_stride') != actual[0]['opaque_bounds'][2]-actual[0]['opaque_bounds'][0] or manifest['source_stride'] <= 0:
        raise ValueError('FRONTPANEL_SOURCE_STRIDE')
    cycle = manifest['source_stride']*len(actual)
    if (manifest.get('source_cycle_width') != cycle
            or manifest.get('target_cycle_width') != max(8,((cycle+5)//10)*8)
            or manifest.get('target_cycle_rounding') != 'nearest_8px_after_4_over_5_scale'):
        raise ValueError('FRONTPANEL_CYCLE_GEOMETRY')
    for name,size in (('tiles.bin',count*16),('tilemap.bin',width*28*3),('palette.bin',32)):
        if len(blobs[name]) != size or manifest.get(name.split('.')[0]+'_bytes') != size:
            raise ValueError('FRONTPANEL_BLOB_SIZE: '+name)
    if any(blobs['palette.bin'][:8]):
        raise ValueError('FRONTPANEL_HUD_PALETTE')
    font,binding = normal_font_palette_binding()
    if (blobs['palette.bin'][8:16] != b''.join(w.to_bytes(2,'little') for w in font)
            or manifest.get('font_palette_binding') != binding):
        raise ValueError('FRONTPANEL_FINAL_FONT_PALETTE')
    entries = st.decode_tilemap_column_major(blobs['tilemap.bin'],width,28)
    if any(not 0 <= tid < count or not 1 <= pal <= 3 for tid,pal,_,_ in entries):
        raise ValueError('FRONTPANEL_TILE_REFERENCE')
    # No source artwork may be silently stranded outside the runtime's rows.
    unused_rows = list(range(limits['row_start']))+list(range(limits['row_start']+limits['row_count'],28))
    unused_tiles = {entries[y*width+x][0] for y in unused_rows for x in range(width)}
    if any(np.any(st.decode_2bpp_tile(blobs['tiles.bin'][t*16:t*16+16])) for t in unused_tiles):
        raise ValueError('FRONTPANEL_CONTENT_OUTSIDE_RUNTIME_ROWS')
    resources = verify_sequence_resources(entries,count,width,limits)
    from convert_frontpanel import verify_window_budget
    boot_worst,_ = verify_window_budget(entries,width,28,32)
    if boot_worst > limits['usable_slots']:
        raise ValueError('FRONTPANEL_BOOT_RESIDENT_CAPACITY')
    resources['boot_unique_tiles'] = boot_worst
    resources['authored_rows_outside_streamed_band'] = [y for y in unused_rows
        if any(np.any(st.decode_2bpp_tile(blobs['tiles.bin'][entries[y*width+x][0]*16:entries[y*width+x][0]*16+16]))
               for x in range(width))]
    return manifest,{name:hashlib.sha256(data).hexdigest() for name,data in blobs.items()},resources


def materialize_normal(configs, sources, normal_ir, bor_c, output_root):
    from convert_frontpanel import convert_frontpanel_streaming,normal_font_palette_binding
    import numpy
    import PIL
    bor_hash = verify_source(bor_c)
    linked = [dict(c) for c in configs]
    report = []
    protected = {Path(c[k]).resolve() for c in configs for k in ('bg','frontpanel') if c.get(k)}
    files = [Path(__file__),ROOT/'tools/bg_converter/convert_frontpanel.py',
             ROOT/'tools/bg_converter/composite_scene.py',ROOT/'tools/bg_converter/level_parse.py',
             ROOT/'tools/bg_converter/snes_tiles.py',ROOT/'tools/bg_converter/tiledpalettequant.py']
    encoder_hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for physical,ir in normal_ir.items():
        cfg = configs[physical]
        source = sources[str(Path(cfg['pak']).resolve())]
        sequence = sequence_directives(source,ir)
        if not sequence:
            continue
        bg_bytes = (Path(cfg['bg'])/'manifest.json').read_bytes()
        bg = json.loads(bg_bytes)
        if bg.get('streaming') is not True or bg.get('height_tiles') != 28:
            raise ValueError('FRONTPANEL_BG_LAYOUT_UNBOUND')
        width = bg['width_tiles']
        prior_fp = cfg.get('frontpanel')
        y = json.loads((Path(prior_fp)/'manifest.json').read_text()).get('frontpanel_y',0) if prior_fp else 0
        inputs = dict(adapter=ADAPTER,bor_sha256=bor_hash,physical=physical,source_path=ir.source_path,
                      source_level_sha256=hashlib.sha256(source.read(ir.source_path)).hexdigest(),
                      sequence=sequence,accepted_bg_sha256=hashlib.sha256(bg_bytes).hexdigest(),
                      font_palette_binding=normal_font_palette_binding()[1],
                      width_tiles=width,frontpanel_y=y,encoder_sha256=encoder_hashes,
                      versions=dict(numpy=numpy.__version__,pillow=PIL.__version__))
        fingerprint = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
        target = Path(output_root)/fingerprint
        resolved = target.resolve()
        if any(resolved == p or resolved in p.parents or p in resolved.parents for p in protected):
            raise ValueError('FRONTPANEL_ACCEPTED_OUTPUT_OVERLAP')
        reused = False
        if (target/'manifest.json').exists():
            try:
                manifest,hashes,resources = validate_materialized(target,sequence,width)
                reused = (manifest.get('sequence_fingerprint') == fingerprint
                          and manifest.get('sequence_blob_sha256') == hashes)
            except (OSError,ValueError,TypeError,KeyError):
                pass
        if not reused:
            if target.exists():
                target = Path(tempfile.mkdtemp(prefix=fingerprint+'-retry-',dir=target.parent))
            paths = [r['source_path'] for r in sequence]
            convert_frontpanel_streaming(cfg['pak'],ir.source_path,target,width,
                frontpanel_y=y,verbose=False,frontpanel_sequence=paths,
                normal_font_palette=True,full_height=True)
            manifest,hashes,resources = validate_materialized(target,sequence,width)
            manifest.update(sequence_fingerprint=fingerprint,sequence_inputs=inputs,
                            sequence_blob_sha256=hashes,sequence_resources=resources)
            (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='ascii')
        linked[physical]['frontpanel'] = target.as_posix()
        report.append(dict(physical=physical,source_path=ir.source_path,accepted_frontpanel=prior_fp,
                           frontpanel=target.as_posix(),reused=reused,fingerprint=fingerprint,
                           sequence=sequence,source_stride=manifest['source_stride'],
                           blob_sha256=hashes,resources=resources,adapter=ADAPTER,
                           source_horizontal_scroll='trunc(advancex*1.4)',source_vertical_scroll=0,
                           runtime_camera=MOTION_ADAPTER))
    return linked,report


def motion_tables(configs, normal_ir):
    """Source direction + admitted target period. No additional source parse."""
    from convert_frontpanel import frontpanel_runtime_limits,verify_sequence_resources,normal_font_palette_binding
    import snes_tiles as st
    modes,periods,rows = [0]*len(configs),[0]*len(configs),[]
    limits = frontpanel_runtime_limits()
    for physical,ir in normal_ir.items():
        if not any(d.name == 'frontpanel' for d in ir.directives):
            continue
        if ir.scroll not in ('right','left','down'):
            raise ValueError('FRONTPANEL_MOTION_DIRECTION')
        path = Path(configs[physical]['frontpanel'])
        m = json.loads((path/'manifest.json').read_text())
        font,binding = normal_font_palette_binding()
        if ((path/'palette.bin').read_bytes()[8:16] != b''.join(w.to_bytes(2,'little') for w in font)
                or m.get('font_palette_binding') != binding):
            raise ValueError('FRONTPANEL_MOTION_FINAL_PALETTE_UNBOUND')
        width = m['width_tiles']
        max_camera = max(0,width*8-256)
        if max_camera*7//5 > 65535:
            raise ValueError('FRONTPANEL_MOTION_COORDINATE_OVERFLOW')
        entries = st.decode_tilemap_column_major((path/'tilemap.bin').read_bytes(),width,28)
        resources = verify_sequence_resources(entries,m['unique_tiles'],width,limits)
        period = m.get('target_cycle_width',width*8)//8
        if not 1 <= period <= width:
            raise ValueError('FRONTPANEL_MOTION_PERIOD')
        # Include the cyclic seam in the resource admission, not just atlas interior.
        wrapped_width = period+limits['viewport_columns']
        wrapped = [entries[y*width+x%period] for y in range(28) for x in range(wrapped_width)]
        seam = verify_sequence_resources(wrapped,m['unique_tiles'],wrapped_width,limits)
        modes[physical] = 2 if ir.scroll == 'down' else 1
        periods[physical] = period
        rows.append(dict(physical=physical,source_path=ir.source_path,direction=ir.scroll,
            max_camera=max_camera,max_adapted_camera=max_camera*7//5,
            adapter=MOTION_ADAPTER,period_columns=period,resources=resources,seam_resources=seam,
            period_adapter='authored_tile_aligned_cycle' if m.get('target_cycle_rounding') == 'nearest_8px_after_4_over_5_scale' else 'accepted_scalar_atlas_repeat',
            presentation='resident-clamped 33-column FP band; fixed HUD via channel5 HDMA',
            row_start=limits['row_start'],row_count=limits['row_count'],
            manifest_sha256=hashlib.sha256((path/'manifest.json').read_bytes()).hexdigest()))
    text = '; Generated Normal FP motion: ACCEPTED_COMPAT, not source exact.\n'
    text += f'StageFp_MapCount = {len(configs)}\nStageFp_ModeMap:\n    .db '+','.join(map(str,modes))+'\n'
    text += 'StageFp_PeriodMap:\n    .dw '+','.join(map(str,periods))+'\n'
    return text,rows
