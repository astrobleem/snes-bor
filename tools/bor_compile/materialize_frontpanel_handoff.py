"""Isolated actual environment materialization and FP pixel/pack ABI proof.

No ROM assembly, aggregate MSU packing, native run, or shared output writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
from compiler import ROOT
sys.path.insert(0,str(ROOT))
import build_rom
import snes_tiles as st
import stage_frontpanel as fp
import stage_frontpanel_bg2 as full
from convert_frontpanel import normal_font_palette_binding
from pack_msu_roster import build_fp_blob


def pixel_proof(path):
    m,hashes,working = full.validate_bg2(path)
    oracle = Path(m['indexed_oracle'])
    original = (oracle/'tiles.bin').read_bytes()
    lowered = (path/'tiles.bin').read_bytes()
    w = m['width_tiles']
    old_map = st.decode_tilemap_column_major((oracle/'tilemap.bin').read_bytes(),w,28)
    new_map = st.decode_tilemap_column_major((path/'tilemap.bin').read_bytes(),w,28)
    # Model actual final palette: FP writes 4..15, then Text_Init rewrites 4..7.
    palette = bytearray((path/'palette.bin').read_bytes())
    font,binding = normal_font_palette_binding()
    palette[8:16] = b''.join(v.to_bytes(2,'little') for v in font)
    assert bytes(palette) == (path/'palette.bin').read_bytes()
    colors = np.frombuffer(palette,dtype='<u2')
    old_cache,new_cache = {},{}
    for old,new in zip(old_map,new_map):
        tid,pal,hf,vf = old
        key = old
        if key not in old_cache:
            tile = st.decode_2bpp_tile(original[tid*16:tid*16+16])
            if hf: tile = tile[:,::-1]
            if vf: tile = tile[::-1,:]
            old_cache[key] = np.where(tile == 0,0,pal*4+tile)
        tid,pal,hf,vf = new
        if new not in new_cache:
            tile = st.decode_4bpp_tile(lowered[tid*32:tid*32+32])
            if hf: tile = tile[:,::-1]
            if vf: tile = tile[::-1,:]
            new_cache[new] = tile
        a,b = old_cache[key],new_cache[new]
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(colors[a],colors[b])
    blob,info = build_fp_blob(str(path),m['owner_width_tiles'],0x120000)
    assert blob[2:4] == bytes((28,4))
    return dict(blob_sha256=hashes,working_set=working,pixels_compared=w*28*64,
                final_cgram4_7=font,font_binding=binding,pack_header_bpp=blob[3],
                pack_blob_bytes=info['blob_size'],unique_tiles=m['unique_tiles'],
                source_stride=m['source_stride'],target_cycle_width=m['target_cycle_width'])


def run(root):
    root = Path(root).resolve()
    original = {Path(c[layer])/name for c in build_rom.STAGE_CONFIGS
                for layer in ('bg','frontpanel') if c.get(layer) for name in (*fp.FILES,'manifest.json')}
    before = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in original}
    configs = build_rom.prepare_stage_environment_assets(output_root=root/'stage_water',generated_dir=root/'generated')
    report = json.loads((root/'generated/stage_environment_materialization.json').read_text())
    rows = []
    for row in report['frontpanel_media']:
        path = Path(row['frontpanel'])
        proof = pixel_proof(path)
        cm = json.loads((Path(row['bg'])/'manifest.json').read_text())
        rows.append(dict(physical=row['physical'],frontpanel=str(path),bg=row['bg'],
                         clean_bg_tiles=cm['unique_tiles'],**proof))
    assert before == {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in original}
    for name,data in [('bindings.json',configs),('frontpanel_proof.json',dict(
            status='SOURCE_MEDIA_PASS_NOT_NATIVE',rows=rows,layout=full.layout_proof(),
            accepted_assets_unchanged=True,generated_table_sha256=hashlib.sha256(
                (root/'generated/stage_frontpanel_tables.pasm').read_bytes()).hexdigest()))]:
        (root/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(output=str(root),rows=rows),indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    run(args.output or tempfile.mkdtemp(prefix='s8_fp_handoff_',dir=ROOT/'out'))
