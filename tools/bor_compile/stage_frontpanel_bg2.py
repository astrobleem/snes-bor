"""Normal full-height foreground, legal discontiguous VRAM, private BG1 clean plate."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
from dataclasses import asdict

from compiler import ROOT
import stage_frontpanel as fp

ADAPTER = 'ACCEPTED_COMPAT_NORMAL_FULL_FP_BG2_V1'
RUNS = ((0,128),(128,64),(192,63))
BLANK_TILE = 255
MAP_WORD = 0x6C00
CHAR_WORD = 0x3000


def layout_proof():
    """Exact current fixed owners, with a fail-closed font growth boundary."""
    from convert_frontpanel import frontpanel_runtime_limits
    limits = frontpanel_runtime_limits()
    if limits['usable_slots'] != 256 or limits['viewport_columns'] != 33 or not 1 <= limits['tile_ids'] <= 2048:
        raise ValueError('FRONTPANEL_BG2_RUNTIME_DOMAIN')
    bindings = {
        'src/main.pasm': {'BG1_TILES_VRAM_WORD':0, 'BG1_TILEMAP_VRAM_WORD':0x6000,
                          'BG3_TILES_VRAM_WORD':0x2000, 'BG3_TILEMAP_VRAM_WORD':0x6800},
        'src/core/text.pasm': {'FONT_TILES_VRAM_WORD':0x2900},
        'src/core/stage_frontpanel_bg2.pasm': {'StageFp_BG2Map':MAP_WORD,
            'StageFp_BG2Char':CHAR_WORD,'StageFp_BG2Rows':28,'StageFp_BG2Slots':255}}
    for filename,constants in bindings.items():
        text = (ROOT/filename).read_text()
        for name,expected in constants.items():
            values = re.findall(r'^\s*'+name+r'\s*=\s*([^;\r\n]+)',text,re.M)
            literal = values[0].strip() if len(values) == 1 else ''
            if not re.fullmatch(r'\$[0-9a-fA-F]+|[0-9]+',literal):
                raise ValueError('FRONTPANEL_BG2_LAYOUT_UNBOUND: '+name)
            actual = int(literal[1:],16) if literal.startswith('$') else int(literal)
            if actual != expected: raise ValueError('FRONTPANEL_BG2_LAYOUT_CHANGED: '+name)
    font = (ROOT/'src/assets/font_tiles.bin').read_bytes()
    if not 0 < len(font) <= (0x3000-0x2900)*2:
        raise ValueError('FRONTPANEL_BG2_FONT_VRAM_OVERLAP')
    owners = [('BG1 cache',0,0x2000),('HUD',0x2000,0x2060),
              ('font',0x2900,0x2900+len(font)//2),
              ('OBJ/source gameplay region',0x4000,0x6000),
              ('BG1 maps',0x6000,0x6800),('BG3 HUD map',0x6800,0x6C00)]
    slots = [BLANK_TILE]+[first+i for first,count in RUNS for i in range(count)]
    if len(slots) != 256 or len(set(slots)) != 256:
        raise ValueError('FRONTPANEL_BG2_SLOT_MAP')
    regions = [('FP blank',CHAR_WORD+BLANK_TILE*16,CHAR_WORD+(BLANK_TILE+1)*16),
               ('BG2 map',MAP_WORD,MAP_WORD+2048)]
    regions += [(f'FP run {i}',CHAR_WORD+first*16,CHAR_WORD+(first+count)*16)
                for i,(first,count) in enumerate(RUNS)]
    for i,(name,lo,hi) in enumerate(regions):
        if not 0 <= lo < hi <= 0x8000:
            raise ValueError('FRONTPANEL_BG2_VRAM_RANGE')
        for other,a,b in owners+regions[:i]:
            if max(lo,a) < min(hi,b):
                raise ValueError(f'FRONTPANEL_BG2_VRAM_OVERLAP: {name}/{other}')
    return dict(char_base=CHAR_WORD,map_base=MAP_WORD,map_words=2048,slots=slots,
                runs=[dict(tile_id=a,count=b,word_start=CHAR_WORD+a*16,word_end=CHAR_WORD+(a+b)*16)
                      for a,b in RUNS],blank_tile=BLANK_TILE,font_tiles_sha256=hashlib.sha256(font).hexdigest(),
                owners=[dict(name=n,start=a,end=b) for n,a,b in owners])


def motion_tables(configs, normal_ir):
    layout = layout_proof()
    modes,periods = [0]*len(configs),[0]*len(configs)
    rows = []
    for i,ir in normal_ir.items():
        if not any(d.name == 'frontpanel' for d in ir.directives): continue
        m,hashes,working = validate_bg2(Path(configs[i]['frontpanel']))
        if ir.scroll not in ('right','left','down'):
            raise ValueError('FRONTPANEL_BG2_DIRECTION')
        max_camera = max(0,m['owner_width_tiles']*8-256)
        if max_camera*7//5 > 65535:
            raise ValueError('FRONTPANEL_MOTION_COORDINATE_OVERFLOW')
        modes[i] = 2 if ir.scroll == 'down' else 1
        periods[i] = m['target_cycle_width']//8
        rows.append(dict(physical=i,source_path=ir.source_path,direction=ir.scroll,
            adapter=ADAPTER,period_columns=periods[i],source_stride=m['source_stride'],
            max_camera=max_camera,max_adapted_camera=max_camera*7//5,
            working_set=working,blob_sha256=hashes,rows=28,window_columns=33,
            staging_union_columns=34,layout=layout))
    text = '; Generated full Normal FP BG2: ACCEPTED_COMPAT, not source timing exact.\n'
    text += f'StageFp_MapCount = {len(configs)}\nStageFp_ModeMap:\n    .db '+','.join(map(str,modes))+'\n'
    text += 'StageFp_PeriodMap:\n    .dw '+','.join(map(str,periods))+'\nStageFp_BG2SlotMap:\n'
    for start in range(0,len(layout['slots']),16):
        text += '    .dw '+','.join(map(str,layout['slots'][start:start+16]))+'\n'
    return text,rows


def validate_bg2(path):
    import snes_tiles as st
    from convert_frontpanel import normal_font_palette_binding,verify_window_budget
    m = json.loads((path/'manifest.json').read_text())
    blobs = {n:(path/n).read_bytes() for n in fp.FILES}
    from convert_frontpanel import frontpanel_runtime_limits
    limit = frontpanel_runtime_limits()['tile_ids']
    if not 1 <= limit <= 2048:
        raise ValueError('FRONTPANEL_BG2_RUNTIME_DOMAIN')
    if (m.get('full_fp_adapter') != ADAPTER or m.get('layer') != 'BG2_frontpanel'
            or m.get('bpp') != 4 or m.get('height_tiles') != 28
            or not 1 <= m['unique_tiles'] <= limit):
        raise ValueError('FRONTPANEL_BG2_ABI')
    w,n = m['width_tiles'],m['unique_tiles']
    if not 1 <= w <= 65535 or not 1 <= m.get('owner_width_tiles',0) <= 65535:
        raise ValueError('FRONTPANEL_BG2_WIDTH')
    if any(len(blobs[name]) != size for name,size in
           [('tiles.bin',n*32),('tilemap.bin',w*28*3),('palette.bin',32)]):
        raise ValueError('FRONTPANEL_BG2_BLOB_SIZE')
    font,binding = normal_font_palette_binding()
    if blobs['palette.bin'][8:16] != b''.join(x.to_bytes(2,'little') for x in font) or m.get('font_palette_binding') != binding:
        raise ValueError('FRONTPANEL_BG2_FONT_PALETTE')
    entries = st.decode_tilemap_column_major(blobs['tilemap.bin'],w,28)
    if any(not 0 <= t < n or p != 0 for t,p,_,_ in entries):
        raise ValueError('FRONTPANEL_BG2_TILE_REFERENCE')
    period = m['target_cycle_width']//8
    if m['target_cycle_width'] % 8 or not 1 <= period <= w:
        raise ValueError('FRONTPANEL_BG2_PERIOD')
    extended = period+34
    ring = [entries[y*w+x%period] for y in range(28) for x in range(extended)]
    working = {str(columns):verify_window_budget(ring,extended,28,columns)[0] for columns in (33,34)}
    if working['34'] > 256:
        raise ValueError('FRONTPANEL_BG2_RESIDENT_UNION_CAPACITY')
    return m,{k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()},working


def validate_clean_background(manifest, blobs, owner_width):
    import snes_tiles as st
    from stage_water import runtime_tile_id_limit
    n = manifest['unique_tiles']
    if (manifest.get('normal_frontpanel_removed') is not True or manifest.get('frontpanel') is not None
            or manifest.get('width_tiles') != owner_width or manifest.get('height_tiles') != 28
            or manifest.get('streaming') is not True or not 1 <= n <= runtime_tile_id_limit()):
        raise ValueError('FRONTPANEL_CLEAN_BG1_ABI')
    for name,size in [('tiles.bin',n*32),('tilemap.bin',owner_width*28*3),('palette.bin',256)]:
        if len(blobs[name]) != size: raise ValueError('FRONTPANEL_CLEAN_BG1_SIZE')
    entries = st.decode_tilemap_column_major(blobs['tilemap.bin'],owner_width,28)
    if any(not 0 <= tile < n or not 1 <= palette <= 7 for tile,palette,_,_ in entries):
        raise ValueError('FRONTPANEL_CLEAN_BG1_REFERENCE')


def clean_scene(index, level, water_row):
    """Clear the scalar compositor input before either generic or water draw."""
    from composite_scene import composite_level
    from stage_water import composite
    clean = copy.deepcopy(level)
    clean.frontpanel = None
    return composite(index,clean,water_row) if water_row.active else composite_level(index,clean)


def encode_clean_background(index, level, water_row, source_path):
    """Same accepted BG quantizer/budget, fed the source clean-plate pixels."""
    import numpy as np
    from PIL import Image
    import convert_bg as bg
    from stage_water import runtime_tile_id_limit
    scene = clean_scene(index,level,water_row)
    raw_width = round(scene.shape[1]*.8)
    width = (raw_width+7)//8
    rgb = np.zeros((224,width*8,3),dtype=np.uint8)
    rgb[:,:raw_width] = np.asarray(Image.fromarray(scene).resize((raw_width,224),Image.Resampling.NEAREST))
    raw = bg.st.image_to_tiles(bg.st.rgb_array_to_bgr555(rgb))
    unique,positions,flips = bg.st.dedup_bgr555(raw)
    palettes,indexed,ids = bg.build_palettes_tileaware(unique,num_palettes=bg.NUM_PALETTES,colors_per_palette=16)
    tiles = []
    for uid,(hf,vf) in zip(positions,flips):
        tile = indexed[uid]
        if hf: tile = tile[:,::-1]
        if vf: tile = tile[::-1,:]
        tiles.append(tile)
    unique,entries = bg.st.dedup_tiles(np.asarray(tiles),np.asarray([ids[u]+bg.PALETTE_OFFSET for u in positions]))
    if not 1 <= len(unique) <= runtime_tile_id_limit():
        raise ValueError('FRONTPANEL_CLEAN_BG1_TILE_DOMAIN')
    blobs = dict(zip(fp.FILES,(bg.st.encode_tileset(unique,bpp=4),
        bg.st.encode_tilemap_column_major(entries,width,28),
        bg.st.encode_palette([[0]*16]+list(palettes),8,16))))
    m = dict(level_entry=source_path,background=level.background,panels=level.panels,frontpanel=None,
        streaming=True,width_px=width*8,height_px=224,width_tiles=width,height_tiles=28,
        content_width_tiles=width,unique_tiles=len(unique),num_palettes=7,palette_offset=1,
        colors_per_palette=16,panel_y=0,background_y=0,frontpanel_y=0,
        normal_frontpanel_removed=True,stage_water=asdict(water_row))
    m.update({k.split('.')[0]+'_bytes':len(v) for k,v in blobs.items()})
    return m,blobs


def materialize_normal(configs,sources,normal_ir,bor_c,output_root):
    """Preserve the verified 2bpp oracle; publish separate full BG2 + clean BG1."""
    from composite_scene import PakIndex,load_level
    from stage_water import bind
    indexed,indexed_rows = fp.materialize_normal(configs,sources,normal_ir,bor_c,Path(output_root)/'indexed')
    linked = [dict(c) for c in indexed]
    report = []
    layout = layout_proof()
    helper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for row in indexed_rows:
        i = row['physical']
        original = Path(linked[i]['frontpanel'])
        im = json.loads((original/'manifest.json').read_text())
        inputs = dict(indexed_fingerprint=row['fingerprint'],indexed_hashes=row['blob_sha256'],
            layout=layout,helper_sha256=helper_hash,adapter=ADAPTER)
        fingerprint = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
        path = Path(output_root)/'bg2'/fingerprint
        reused = False
        if (path/'manifest.json').exists():
            try:
                m,hashes,working = validate_bg2(path)
                reused = m.get('full_fp_fingerprint') == fingerprint and m.get('full_fp_blob_sha256') == hashes
            except (ValueError,OSError,KeyError,TypeError): pass
        if not reused:
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists(): path = Path(tempfile.mkdtemp(prefix=fingerprint+'-retry-',dir=path.parent))
            path.mkdir(parents=True,exist_ok=True)
            old_blobs = {n:(original/n).read_bytes() for n in fp.FILES}
            lower = fp.lower_bg2(old_blobs,im['width_tiles'],im['target_cycle_width']//8)
            blobs = dict(zip(fp.FILES,(lower['tiles_bin'],lower['tilemap_bin'],old_blobs['palette.bin'])))
            m = dict(im,layer='BG2_frontpanel',bpp=4,unique_tiles=lower['unique_tiles'],
                num_palettes=1,colors_per_palette=16,palette_offset=0,full_fp_adapter=ADAPTER,
                full_fp_fingerprint=fingerprint,full_fp_inputs=inputs,indexed_oracle=original.as_posix(),
                full_fp_blob_sha256={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()})
            m.update({k.split('.')[0]+'_bytes':len(v) for k,v in blobs.items()})
            for name,data in blobs.items(): (path/name).write_bytes(data)
            (path/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='ascii')
            m,hashes,working = validate_bg2(path)
        # Strip FP from generic and water composites alike, with identical source IR.
        source = sources[str(Path(configs[i]['pak']).resolve())]
        water_row = bind(source,normal_ir[i],i)
        index = PakIndex(configs[i]['pak'])
        level = load_level(index,normal_ir[i].source_path)
        image_paths = list(level.ordered_panels())
        if level.background: image_paths.append(level.background)
        if water_row.texture_path: image_paths.append(water_row.texture_path)
        source_images = {source.image_path(p):hashlib.sha256(source.read(source.image_path(p))).hexdigest()
                         for p in image_paths}
        bg_inputs = dict(fp_fingerprint=fingerprint,water=asdict(water_row),
            source_images=source_images,
            accepted_bg_sha256=hashlib.sha256((Path(configs[i]['bg'])/'manifest.json').read_bytes()).hexdigest())
        bg_fingerprint = hashlib.sha256(json.dumps(bg_inputs,sort_keys=True).encode()).hexdigest()
        clean = Path(output_root)/'clean_bg1'/bg_fingerprint
        bg_reused = False
        if (clean/'manifest.json').exists():
            try:
                cm = json.loads((clean/'manifest.json').read_text())
                validate_clean_background(cm,{n:(clean/n).read_bytes() for n in fp.FILES},m['owner_width_tiles'])
                bg_reused = (cm.get('clean_fp_fingerprint') == bg_fingerprint and
                    cm.get('normal_frontpanel_removed') is True and cm.get('frontpanel') is None and
                    cm.get('clean_blob_sha256') == {n:hashlib.sha256((clean/n).read_bytes()).hexdigest() for n in fp.FILES})
            except (OSError,ValueError,KeyError): pass
        if not bg_reused:
            clean.parent.mkdir(parents=True,exist_ok=True)
            if clean.exists(): clean = Path(tempfile.mkdtemp(prefix=bg_fingerprint+'-retry-',dir=clean.parent))
            clean.mkdir(parents=True,exist_ok=True)
            cm,blobs = encode_clean_background(index,level,water_row,normal_ir[i].source_path)
            validate_clean_background(cm,blobs,m['owner_width_tiles'])
            if cm['width_tiles'] != m.get('owner_width_tiles',m['width_tiles']):
                raise ValueError('FRONTPANEL_CLEAN_BG_WIDTH')
            cm.update(clean_fp_fingerprint=bg_fingerprint,clean_fp_inputs=bg_inputs,
                clean_blob_sha256={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()})
            for name,data in blobs.items(): (clean/name).write_bytes(data)
            (clean/'manifest.json').write_text(json.dumps(cm,indent=2)+'\n',encoding='ascii')
        linked[i].update(frontpanel=path.as_posix(),bg=clean.as_posix())
        report.append(dict(row,frontpanel=path.as_posix(),bg=clean.as_posix(),
            reused=reused,clean_bg_reused=bg_reused,adapter=ADAPTER,full_fp_fingerprint=fingerprint,
            full_fp_blob_sha256=hashes,working_set=working,layout=layout,
            clean_bg_fingerprint=bg_fingerprint,clean_bg_hashes=cm['clean_blob_sha256']))
    return linked,report
