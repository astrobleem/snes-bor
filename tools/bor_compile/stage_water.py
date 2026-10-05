"""S8 opt-in flattened-BG1 water/rock adapter, not a fidelity certificate.

No stage-name exceptions. Call metadata() with the compiler's physical bindings;
emit_tables() returns assembler text without writing shared generated files.
composite() is an explicit replacement input to the accepted BG tile encoder.
See docs/bor_environment_s8_water.md for the deliberately bounded adaptation.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import io
import math
import json
from pathlib import Path

from compiler import Source, stage
from source_actor_numeric import verify_source

ROCK = (2,2,3,4,5,6,7,7,8,8,9,9,9,9,8,8,
        7,7,6,5,4,3,2,2,1,1,0,0,0,0,1,1)
FRAMES = 5760  # 19200 source ticks: lcm(800, 256, 6*20).
NORMAL_CAMPAIGN = 3  # target campaign ID; source Normal set ID is 1.
ADAPTATION = 'S8_FLATTENED_BG1_BOUNDED_RASTER_V1'


def scale_x(n):
    return (n * 4 + 2) // 5


def scale_y(n):
    return (n * 14 + 7) // 15


def wave(amplitude):
    if amplitude not in (2, 15):
        raise ValueError('WATER_AMPLITUDE_UNBOUND')
    # Source TEXTURE.C rounds amp*(sin(i*pi/128)+1) to nearest integer.
    # Host double is an explicitly declared LUT approximation, not Watcom proof.
    return tuple(scale_x(int(amplitude * (math.sin(i * 3.1415926 / 128) + 1) + .5))
                 - scale_x(amplitude) for i in range(256))


def phases(frame):
    if not 0 <= frame < FRAMES:
        raise ValueError('FRAME_DOMAIN')
    tick = frame * 10 // 3  # declared 60Hz presentation clock, pause by caller
    return tick & 255, scale_y(ROCK[(tick // 25) & 31]), scale_x((tick // 6) % 20) - 8


@dataclass(frozen=True)
class WaterMetadata:
    physical: int
    source_path: str
    amplitude: int = 0
    rocking: bool = False
    background_height: int = 0
    texture_path: str | None = None
    texture_sha256: str | None = None
    texture_size: tuple[int, int] | None = None
    adaptation: str = ADAPTATION

    @property
    def active(self):
        return bool(self.amplitude or self.rocking)


def bind(source, ir, physical, *, dialect='historical-bor'):
    from PIL import Image
    if dialect != 'historical-bor' or ir.diagnostics:
        raise ValueError('WATER_SOURCE_UNCERTAIN')
    if not 0 <= physical < 256:
        raise ValueError('WATER_PHYSICAL_RANGE')
    # Assignment order: last directive wins, including rock 0.
    waters = ir.environment.get('water', [])
    rocks = ir.environment.get('rock', [])
    rocking = bool(rocks[-1]) if rocks else False
    amplitude = max(2, int(waters[-1]['mode'])) if waters else 0
    if amplitude and amplitude not in (2, 15):
        raise ValueError('WATER_AMPLITUDE_UNBOUND')
    if not (amplitude or rocking):
        return WaterMetadata(physical, ir.source_path)
    if ir.scroll not in ('right', 'left') or not ir.background:
        raise ValueError('WATER_SCROLL_OR_BACKGROUND_UNBOUND')
    bg = Image.open(io.BytesIO(source.read(ir.background)))
    if not 0 < bg.height < 160:
        raise ValueError('WATER_BACKGROUND_HEIGHT_UNBOUND')
    path = source.image_path(waters[-1]['source_path']) if waters else None
    data = source.read(path) if path else None
    texture = Image.open(io.BytesIO(data)) if data else None
    return WaterMetadata(physical, ir.source_path, amplitude, rocking, bg.height,
                         path, sha256(data).hexdigest() if data else None,
                         texture.size if texture else None)


def metadata(configs, bor_c):
    """Input is the selected compiler layout, not hardcoded Normal physical IDs."""
    verify_source(bor_c)
    sources, rows = {}, []
    for physical, cfg in enumerate(configs):
        if physical >= 256:
            raise ValueError('WATER_PHYSICAL_RANGE')
        if cfg['family'] != 'bor-original':
            continue
        source = sources.setdefault(cfg['pak'], None)
        if source is None:
            source = sources[cfg['pak']] = Source(cfg['pak'])
        rows.append(bind(source, stage(source, cfg['source_level']), physical))
    return rows


def emit_tables(rows):
    """One <=32KiB ROM bank, same bank as StageWater code (bare long labels)."""
    rows = list(rows)
    if len({r.physical for r in rows}) != len(rows):
        raise ValueError('WATER_DUPLICATE_PHYSICAL')
    indexed = {r.physical: r for r in rows}
    text = ['; Generated S8 target adaptation; not a source-fidelity certificate.']
    def table(name, data):
        text.append(name + ':')
        data = list(data)
        for start in range(0, len(data), 16):
            text.append('    .db ' + ','.join(str(v & 255) for v in data[start:start+16]))
    for field, name in [('amplitude','Mode'), ('rocking','Rock'), ('background_height','Height')]:
        table('StageWater_' + name + 'Map',
              (int(getattr(indexed[i], field)) if i in indexed else 0 for i in range(256)))
    for n, name in enumerate(('Phase','RockY','Drift')):
        table('StageWater_' + name + 'Frames', (phases(i)[n] for i in range(FRAMES)))
    table('StageWater_Wave2', wave(2))
    table('StageWater_Wave15', wave(15))
    table('StageWater_SourceRows', (y * 240 // 224 for y in range(224)))
    table('StageWater_RowPhases', (5 * (y * 240 // 224) for y in range(224)))
    return '\n'.join(text) + '\n'


def raster(row, frame, camera_x=0, camera_y=0, campaign=3):
    """Reference for runtime's 224 mode-2 BG1HOFS HDMA records + VOFS delta."""
    if campaign != NORMAL_CAMPAIGN or not row.active:
        return None
    phase, rock, drift = phases(frame)
    distortion = wave(row.amplitude) if row.amplitude else None
    offsets = []
    for y in range(224):
        sy = y * 240 // 224
        dx = 0
        if row.rocking and sy < 160:
            dx = drift
        elif distortion is not None and row.background_height <= sy < 160:
            dx = distortion[(phase + (sy-row.background_height)*5) & 255]
        offsets.append((camera_x + dx) & 0xffff)
    data = b''.join(bytes((1, x & 255, x >> 8)) for x in offsets) + b'\0'
    return data, (camera_y + (rock if row.rocking else 0)) & 0xffff


def composite(pak_index, level, row, *, panel_y=0, background_y=0, frontpanel_y=0):
    """Bake texture BELOW panels into a fresh source-resolution RGB canvas.

    Supplies the existing encoder's composite_level input; does not call a
    converter, overwrite assets, monkeypatch shared code, or build a ROM.
    Plane is frozen at time=0 with periodic safe indexing; raster translates it.
    Wave uses the mean source distortion in the baked image and runtime delta.
    """
    import numpy as np
    from composite_scene import _blit, _tile_horizontally, level_width
    if background_y != 0:
        raise ValueError('WATER_BACKGROUND_OFFSET_UNBOUND')
    width = level_width(pak_index, level)
    canvas = np.zeros((240, width, 3), dtype=np.uint8)
    if level.background:
        bg, mask = pak_index.image(level.background)
        for y in range(0, 240, len(bg)):
            _tile_horizontally(canvas, bg, mask, y, width)
    if row.texture_path:
        tex, _ = pak_index.image(row.texture_path)
        th, tw = tex.shape[:2]
        for i in range(160-row.background_height):
            if row.rocking:
                step = tw * 256 // (tw + tw*i//11)
                # Repeat the source 320px viewport's time-zero perspective.
                # Fix the source's s==srclen out-of-bounds edge by modulo.
                xs = (((np.arange(width) % 320 - 160)*step + tw*256) >> 8) % tw
            else:
                xs = (np.arange(width) + row.amplitude) % tw
            canvas[row.background_height+i] = tex[i % th, xs]
    x = 0
    for name in level.ordered_panels():
        rgb, mask = pak_index.image(name)
        _blit(canvas, rgb, mask, x, panel_y)
        x += rgb.shape[1]
    if level.frontpanel:
        rgb, mask = pak_index.image(level.frontpanel)
        _tile_horizontally(canvas, rgb, mask, frontpanel_y, width)
    return canvas


def encode_background(pak_index, level, row):
    """Return new streaming BG blobs using the accepted tile/palette primitives.

    No filesystem writes and no ROM build. The selecting compiler must give
    Normal its own output directory/record; never replace an Easy media record.
    Quantization and tile-ID overflow behave like convert_bg.convert_streaming.
    """
    import numpy as np
    from PIL import Image
    import convert_bg as bg
    if not row.active:
        raise ValueError('WATER_ENCODER_REQUIRES_ACTIVE_ADAPTER')
    scene = composite(pak_index, level, row)
    width = round(scene.shape[1] * .8)
    columns = (width + 7) // 8
    rgb = np.zeros((224, columns*8, 3), dtype=np.uint8)
    rgb[:, :width] = np.asarray(Image.fromarray(scene).resize((width,224),Image.Resampling.NEAREST))
    raw = bg.st.image_to_tiles(bg.st.rgb_array_to_bgr555(rgb))
    unique, positions, flips = bg.st.dedup_bgr555(raw)
    palettes, indexed, palette_ids = bg.build_palettes_tileaware(
        unique, num_palettes=bg.NUM_PALETTES, colors_per_palette=bg.COLORS_PER_PALETTE)
    tiles = np.zeros((len(raw),8,8),dtype=np.uint8)
    ids = np.zeros(len(raw),dtype=np.uint8)
    for n, uid in enumerate(positions):
        tile = indexed[uid]
        hf, vf = flips[n]
        if hf:
            tile = tile[:, ::-1]
        if vf:
            tile = tile[::-1, :]
        tiles[n], ids[n] = tile, palette_ids[uid]
    unique, entries = bg.st.dedup_tiles(tiles, ids+bg.PALETTE_OFFSET)
    if len(unique) > bg.MAX_STREAMING_TILES:
        raise ValueError('WATER_TILE_ID_CAPACITY')
    blobs = {
        'tiles.bin': bg.st.encode_tileset(unique,bpp=4),
        'tilemap.bin': bg.st.encode_tilemap_column_major(entries,columns,28),
        'palette.bin': bg.st.encode_palette(
            [[0]*16]*bg.PALETTE_OFFSET+list(palettes),bg.TOTAL_PALETTES,16),
    }
    manifest = dict(level_entry=row.source_path, background=level.background,
                    panels=level.panels, frontpanel=level.frontpanel, streaming=True,
                    width_px=columns*8, height_px=224, width_tiles=columns,
                    height_tiles=28, content_width_tiles=columns, unique_tiles=len(unique),
                    num_palettes=bg.NUM_PALETTES, palette_offset=bg.PALETTE_OFFSET,
                    colors_per_palette=16, panel_y=0, background_y=0, frontpanel_y=0,
                    stage_water=asdict(row))
    manifest.update({name.split('.')[0]+'_bytes':len(data) for name,data in blobs.items()})
    return manifest, blobs


def normal_stage_inputs(configs):
    """One source cache and one Normal IR parse shared by water/bounds/HUD.

    Membership comes from LEVELS.TXT, not a directory prefix or physical ID.
    Foreign sources are cached for the HUD helper, but not parsed as BOR stages.
    """
    from compiler import key, project
    if not 1 <= len(configs) <= 256:
        raise ValueError('ENVIRONMENT_PHYSICAL_CAPACITY')
    sources, normal_sets, parsed = {}, {}, {}
    for physical, cfg in enumerate(configs):
        origin = str(Path(cfg['pak']).resolve())
        if origin not in sources:
            sources[origin] = Source(origin)
        source = sources[origin]
        if cfg['family'] != 'bor-original':
            continue
        if origin not in normal_sets:
            matches = [s for s in project(source).sets if s.name in ('Normal', 'Hard', 'Bonus')]
            if len(matches) != 3:
                raise ValueError('ENVIRONMENT_NORMAL_SET_AMBIGUOUS')
            normal_sets[origin] = {key(e.source_path): selected.source_id
                for selected in matches for e in selected.entries if e.kind == 'STAGE'}
        members = normal_sets[origin]
        member = key(cfg['source_level']) in members
        declared = cfg.get('source_set_id')
        if declared is not None and ((declared in (1, 2, 3)) != member
                or member and declared != members[key(cfg['source_level'])]):
            raise ValueError('ENVIRONMENT_NORMAL_MEMBERSHIP_MISMATCH')
        if member:
            parsed[physical] = stage(source, cfg['source_level'])
    return sources, parsed


def runtime_tile_id_limit(source_path=None):
    """Read the runtime Tile2Slot allocation, separately from the u16 ABI.

    Re-read for each admission (including cache hits). This is a resource
    constraint, not an encoding input; a runtime limit change must not bypass
    validation just because cached media hashes still match.
    """
    import re
    from compiler import ROOT
    path = Path(source_path) if source_path is not None else ROOT/'src/core/stream_cache.pasm'
    values = re.findall(r'^\s*STREAM_MAX_TILE_IDS\s*=\s*([^;\r\n]+)',
                        path.read_text(encoding='utf-8'), re.MULTILINE)
    if len(values) != 1:
        raise ValueError('WATER_RUNTIME_TILE_DOMAIN_UNBOUND: expected one STREAM_MAX_TILE_IDS')
    literal = values[0].strip()
    if not re.fullmatch(r'(?:[0-9]+|\$[0-9A-Fa-f]+|0[xX][0-9A-Fa-f]+)',literal):
        raise ValueError('WATER_RUNTIME_TILE_DOMAIN_UNBOUND: expected literal allocation')
    limit = int(literal[1:],16) if literal.startswith('$') else int(literal,16 if literal.lower().startswith('0x') else 10)
    if not 1 <= limit <= 65535:
        raise ValueError('WATER_RUNTIME_TILE_DOMAIN_UNBOUND: allocation outside catalog domain')
    return limit


def _validate_media(manifest, blobs, row, accepted):
    from compiler import key
    if manifest.get('stage_water') != json.loads(json.dumps(asdict(row))):
        raise ValueError('WATER_MEDIA_BINDING_MISMATCH')
    if (manifest.get('streaming') is not True or manifest.get('height_tiles') != 28
            or manifest.get('width_tiles') != accepted['width_tiles']
            or manifest.get('content_width_tiles') != accepted['content_width_tiles']
            or key(manifest.get('level_entry', '')) != key(row.source_path)):
        raise ValueError('WATER_MEDIA_LAYOUT_MISMATCH')
    count, width = manifest.get('unique_tiles', 0), manifest['width_tiles']
    if not 1 <= count <= 65535 or not 32 <= width <= 65535:
        raise ValueError('WATER_MEDIA_CAPACITY')
    limit = runtime_tile_id_limit()
    if count > limit:
        raise ValueError(f'WATER_MEDIA_TILE2SLOT_CAPACITY: {count} tiles exceeds STREAM_MAX_TILE_IDS={limit}')
    expected = {'tiles.bin': count*32, 'tilemap.bin':width*28*3, 'palette.bin':256}
    for name, size in expected.items():
        if len(blobs[name]) != size or manifest.get(name.split('.')[0]+'_bytes') != size:
            raise ValueError('WATER_MEDIA_SIZE: '+name)
    if any(blobs['palette.bin'][:32]):
        raise ValueError('WATER_MEDIA_HUD_PALETTE')
    tilemap = blobs['tilemap.bin']
    for i in range(0,len(tilemap),3):
        if int.from_bytes(tilemap[i:i+2],'little') >= count or not 1 <= (tilemap[i+2] & 7) <= 7:
            raise ValueError('WATER_MEDIA_TILE_REFERENCE')


def materialize_normal(configs, sources, normal_ir, bor_c, output_root):
    """Return copied physical bindings and verified new Normal-only media.

    No existing catalog/asset path is modified. Content-addressed outputs keep
    rejected/stale generations recoverable. A cache hit verifies every blob.
    No global compiler tables are emitted until the caller completes all checks.
    """
    from compiler import ROOT
    from composite_scene import PakIndex, load_level
    bor_hash = verify_source(bor_c)
    configs_out = [dict(cfg) for cfg in configs]
    rows, report, indices, pak_hashes = [], [], {}, {}
    encoder_files = [Path(__file__), ROOT/'tools/bg_converter/convert_bg.py',
                     ROOT/'tools/bg_converter/composite_scene.py',
                     ROOT/'tools/bg_converter/level_parse.py',
                     ROOT/'tools/bg_converter/snes_tiles.py',
                     ROOT/'tools/bg_converter/tiledpalettequant.py']
    encoder_hashes = {p.name:sha256(p.read_bytes()).hexdigest() for p in encoder_files}
    import numpy
    import PIL
    versions = dict(numpy=numpy.__version__, pillow=PIL.__version__)
    protected = {Path(cfg['bg']).resolve() for cfg in configs}
    for physical, ir in normal_ir.items():
        cfg = configs[physical]
        origin = str(Path(cfg['pak']).resolve())
        source = sources[origin]
        row = bind(source, ir, physical)
        rows.append(row)
        if not row.active:
            continue
        accepted_path = Path(cfg['bg'])/'manifest.json'
        accepted_bytes = accepted_path.read_bytes()
        accepted = json.loads(accepted_bytes)
        if (accepted.get('streaming') is not True or accepted.get('height_tiles') != 28
                or any(accepted.get(k,0) != 0 for k in ('panel_y','background_y','frontpanel_y'))):
            raise ValueError('WATER_ACCEPTED_LAYOUT_UNBOUND: '+str(accepted_path))
        if origin not in pak_hashes:
            with open(origin,'rb') as stream:
                digest = sha256()
                for chunk in iter(lambda:stream.read(1024*1024),b''):
                    digest.update(chunk)
            pak_hashes[origin] = digest.hexdigest()
        inputs = dict(adapter=ADAPTATION, bor_sha256=bor_hash, pak_sha256=pak_hashes[origin],
                      row=asdict(row), accepted_manifest_sha256=sha256(accepted_bytes).hexdigest(),
                      encoder_sha256=encoder_hashes, versions=versions)
        fingerprint = sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
        target = Path(output_root)/fingerprint
        resolved = target.resolve()
        if any(resolved == p or resolved in p.parents or p in resolved.parents for p in protected):
            raise ValueError('WATER_ACCEPTED_OUTPUT_OVERLAP')
        manifest_path = target/'manifest.json'
        blobs = None
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                cached = {n:(target/n).read_bytes() for n in ('tiles.bin','tilemap.bin','palette.bin')}
                if (manifest.get('stage_water_fingerprint') == fingerprint
                        and manifest.get('stage_water_blob_sha256') ==
                        {n:sha256(data).hexdigest() for n,data in cached.items()}):
                    _validate_media(manifest,cached,row,accepted)
                    blobs = cached
            except (OSError,ValueError,KeyError,TypeError):
                pass
        reused = blobs is not None
        if not reused:
            if origin not in indices:
                indices[origin] = PakIndex(origin)
            manifest, blobs = encode_background(indices[origin],load_level(indices[origin],ir.source_path),row)
            manifest = json.loads(json.dumps(manifest))
            _validate_media(manifest,blobs,row,accepted)
            manifest.update(stage_water_fingerprint=fingerprint,stage_water_inputs=inputs,
                            stage_water_blob_sha256={n:sha256(b).hexdigest() for n,b in blobs.items()})
            # Retain an incomplete/corrupt generation rather than overwriting it.
            if target.exists():
                import tempfile
                target = Path(tempfile.mkdtemp(prefix=fingerprint+'-retry-',dir=target.parent))
            target.mkdir(parents=True,exist_ok=True)
            for name,data in blobs.items():
                (target/name).write_bytes(data)
            (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='ascii')
        configs_out[physical]['bg'] = target.as_posix()
        report.append(dict(physical=physical,source_path=ir.source_path,
                           accepted_bg=cfg['bg'],bg=target.as_posix(),reused=reused,
                           fingerprint=fingerprint,water=asdict(row),
                           blob_sha256=manifest['stage_water_blob_sha256']))
    return configs_out, rows, report
