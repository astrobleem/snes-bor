"""Bounded genuine foreign-PAK frame probes; no dialect normalization or packaging."""
import hashlib
import io
import json
from pathlib import Path
from PIL import Image
from actor_s5_isolated import ROOT,Source
from frame_packing import pack_image,reconstruct,viewport_resources


def main():
    result=[]
    cases=[('tmnt','Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak',['leo','foot01','yellowb']),
           ('motu','Masters of the Universe [v.3.0 Build 4086].pak',['he_man','knightbot'])]
    for project,pak,names in cases:
        source=Source(ROOT/pak)
        report_path=ROOT/f'out/bor_compile_s7/before-{project}/actors.json'
        report=json.loads(report_path.read_text())
        for name in names:
            model=report['models'][name]['ir']
            animation=next((a for a in model['animations'] if a['role']=='idle'),model['animations'][0])
            f=animation['frames'][0];raw=source.read(f['source_path'])
            assert hashlib.sha256(raw).hexdigest()==f['asset_sha256']
            packed=pack_image(raw,f['state'].get('offset',(0,0)))
            assert reconstruct(raw,packed)
            image=Image.open(io.BytesIO(raw));image.load()
            colors=len(set(image.tobytes())-{0})
            result.append(dict(project=project,model=name,source=f['source_path'],sha256=f['asset_sha256'],
                role=animation['role'],frame=0,source_dialect=model['dialect'],
                dimensions=packed['dimensions'],nontransparent_bbox=packed['bbox'],
                pieces=len(packed['pieces']),tile_bytes_upper_bound=packed['tile_bytes'],
                unique_indexed_tile_bytes=len(set(packed['tile_ids']))*32,
                viewport=viewport_resources(packed),nontransparent_colors=colors,
                palette_requirement_minimum=(colors+14)//15,
                raw_geometry_lossless=True,compiler_image_decode='PASS',
                generic_single_palette_encoding='WITHIN_COLOR_COUNT' if colors<=15 else 'ENCODER_PALETTE_SPLIT_REQUIRED',
                publication='DIALECT_BLOCKED',
                reason='Foreign transparency/global palette/remap interpretation is not certified; no BOR compatibility fallback.',
                caveat='Geometry is conditional on index-zero transparency. Packing is an upper bound; whole-image tile demand is not a viewport or hardware-impossibility proof.',
                input_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest()))
    output=ROOT/'out/s7_foreign_publication.json'
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
