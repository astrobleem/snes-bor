"""Analyze/export EXISTING Sol assets without rebuilding a ROM or opening a PAK.

Read-only inputs; output directory must not already exist. Optional retained
observations/oracles let Sol validate actual MOTU assets with Astra's replacement
and emitted kernel before touching the native publisher. This is still OFFLINE.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from opaque_planar import (compile_atlas,coverage_masks,compose_patch,decode_pair,
                            tile_to_rows,visual_key)
from warm_cache import WarmCache,apply_packets,verify_vram
from astra_opaque_kernel import emit,run_row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--observations',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--check-emitted-kernel',action='store_true')
    args=p.parse_args()
    if args.output.exists():raise ValueError('OUTPUT_MUST_BE_NEW')
    assets=args.assets
    authority=json.loads((assets/'source-assets.json').read_text())
    report=json.loads((assets/'report.json').read_text())
    if any(row['updates'] for row in report['trace'][1:]):
        raise ValueError('STATIC_COMPONENT_PALETTE_ONLY')
    if (report['bg_mode'],report['low_bpp'],report['high_palette_start'])!=(4,2,4):
        raise ValueError('COMPONENT_BACKEND_CONTRACT')
    lut=np.frombuffer((assets/'actor-palette.bin').read_bytes(),dtype='<u2')
    high=(assets/'high.chr').read_bytes();low=(assets/'low.chr').read_bytes()
    if len(high)%64 or len(low)%16 or len(high)//64!=len(low)//16:
        raise ValueError('PAIRED_BACKDROP_CONTRACT')
    n=len(high)//64
    tiles=[high[i*64:(i+1)*64]+low[i*16:(i+1)*16] for i in range(n)]
    bm=np.frombuffer((assets/'0-high.map').read_bytes(),dtype='<u2').reshape(32,32)
    lm=np.frombuffer((assets/'0-low.map').read_bytes(),dtype='<u2').reshape(32,32)
    if not np.array_equal(bm,lm) or np.any(bm>=n) or np.any(bm&0x6000):
        raise ValueError('PAIRED_MAP_CONTRACT')
    foreground=np.frombuffer((assets/'foreground.bin').read_bytes(),dtype=np.uint8).reshape(224,256)
    fm=coverage_masks(foreground)
    initial=json.loads((assets/'initial.json').read_text())
    palette=np.zeros(256,dtype=np.uint16)
    palette[:4]=report['low_component_palette']
    palette[4:4+len(initial)]=[c or 0 for c in initial]
    atlases={};sources={};frames={}
    for frame in authority['frames']:
        role=frame['role'];w,h=frame['dimensions']
        indices=np.frombuffer((assets/f'{role}.indices').read_bytes(),dtype=np.uint8).reshape(h,w)
        used=indices[indices!=0]
        if (np.any((lut[used]&255)<4) or np.any((lut[used]&255)>239)
                or np.any((lut[used]>>8)>3)):
            raise ValueError('ACTOR_IMMUTABLE_PALETTE_LOOKUP_DOMAIN')
        sources[role]=indices;frames[role]=frame
        atlases[role]=compile_atlas(indices,lut)
    args.output.mkdir(parents=True)
    exports={r:a.save(args.output,r) for r,a in atlases.items()}
    back_rows=b''.join(tile_to_rows(raw).astype('<u2').tobytes() for raw in tiles)
    (args.output/'backdrop-rows.bin').write_bytes(back_rows)
    (args.output/'foreground-masks.bin').write_bytes(fm.tobytes())
    kernel=emit()
    (args.output/'opaque_row.pasm').write_text(kernel.assembly)
    (args.output/'opaque_row.bin').write_bytes(kernel.code)
    manifest=dict(schema='ASTRA_OPAQUE_PHASE_ASSETS_V1',
        source_pak_sha256=authority['source_pak_sha256'],frames=exports,
        backdrop_tiles=n,backdrop_row_bytes=len(back_rows),foreground_mask_bytes=fm.nbytes,
        original_actor_index_bytes=sum(a.size for a in sources.values()),
        phase_actor_bytes=sum(a.asset_bytes for a in atlases.values()),
        source_asset_domain='Opaque source-indexed, fixed camera, immutable component palette; NOT dynamic SCREEN alpha',
        kernel_bytes=len(kernel.code),kernel_sha256=hashlib.sha256(kernel.code).hexdigest(),
        native_run=False)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if args.observations is None:
        print(json.dumps(manifest,indent=2));return
    observations=json.loads(args.observations.read_text())
    if not isinstance(observations,list):raise ValueError('OBSERVATIONS_LIST_REQUIRED')
    base=np.zeros((224,256),dtype=np.uint16)
    decoded=[decode_pair(t) for t in tiles]
    for ty in range(28):
        for tx in range(32):base[ty*8:ty*8+8,tx*8:tx*8+8]=decoded[int(bm[ty,tx])]
    cache=WarmCache(tiles,bm.flat);vram=cache.initialized_vram()
    measurements=[];previous_key=None;previous_patch=None;kernel_checks=0
    for i,ob in enumerate(observations):
        scene=ob['scene']
        if scene.get('camera',[0,0])!=[0,0] or len(scene['actors'])!=1:
            raise ValueError('BOUNDED_SCENE_REQUIRED')
        actor=scene['actors'][0];role=actor['animation']
        if (actor['frame']!=0 or actor.get('direction',1)!=1
                or actor.get('map',0)!=0 or actor['position'][2]!=0):
            raise ValueError('BOUNDED_ACTOR_REQUIRED')
        f=frames[role];ox,oy=f['offset']
        xq,zq=ob['x_q16'],ob['z_q16']
        if [xq/65536,zq/65536]!=actor['position'][:2]:
            raise ValueError('SNAPSHOT_SCENE_COORDINATE_MISMATCH')
        key=visual_key(model=authority['model_id'],frame=f['handle'],direction=1,
            palette=authority['palette_identity']['colors_sha256'],stage='fixed-source',
            underlay_generation=0,x_q16=xq,z_q16=zq,offset_x=ox,offset_y=oy)
        left,top=key[-2:]
        reused=key==previous_key
        if reused:
            patch=previous_patch
            counts=dict(composed_tiles=0,copy_back_rows=0,copy_source_rows=0,mixed_rows=0)
        else:
            patch,counts=compose_patch(tiles,bm,fm,atlases[role],left,top)
        # Independent direct source-index reference, not the phase compiler.
        expected=base.copy();src=sources[role]
        y0,y1=max(0,top),min(224,top+src.shape[0]);x0,x1=max(0,left),min(256,left+src.shape[1])
        if y1>y0 and x1>x0:
            cut=src[y0-top:y1-top,x0-left:x1-left]
            valid=(cut!=0)&(foreground[y0:y1,x0:x1]==0)
            region=expected[y0:y1,x0:x1]
            region[valid]=lut[cut[valid]]
        actual=base.copy()
        for cell,raw in patch.items():
            ty,tx=divmod(cell,32);actual[ty*8:ty*8+8,tx*8:tx*8+8]=decode_pair(raw)
        if not np.array_equal(actual,expected):raise ValueError('OFFLINE_SOURCE_PIXEL_MISMATCH')
        rgb=(palette[actual&255]+palette[(actual>>8)&3]).astype('<u2')
        oracle=args.observations.parent/f'expected-{i:02d}.rgb555'
        if not oracle.exists():raise ValueError('RETAINED_ORACLE_MISSING:'+str(oracle))
        if rgb.tobytes()!=oracle.read_bytes():raise ValueError('RETAINED_ORACLE_MISMATCH')
        if args.check_emitted_kernel and not reused:
            # Replay every affected tile row through the actual emitted bytes.
            atlas=atlases[role];cx=left+atlas.crop_x;cy=top+atlas.crop_y
            phase=cx%8;first=cx//8;record=atlas.phases[phase]
            for cell,raw in patch.items():
                ty,tx=divmod(cell,32);brows=tile_to_rows(tiles[int(bm[ty,tx])]);outrows=tile_to_rows(raw)
                for ry in range(8):
                    sy=ty*8+ry-cy;row=np.zeros(6,dtype='<u2')
                    if 0<=sy<atlas.height:row=record[sy,tx-first]
                    mask=int(row[0])&(65535^(int(fm[ty,tx,ry])*257))
                    result,cpu=run_row(brows[ry].astype('<u2').tobytes(),row[1:].astype('<u2').tobytes(),mask,ry)
                    if result!=outrows[ry].astype('<u2').tobytes():raise ValueError('EMITTED_KERNEL_MISMATCH')
                    kernel_checks+=1
        plan=cache.prepare(i+1,patch);apply_packets(vram,plan)
        cache.commit(plan,[p.tag for p in plan.packets]);verify_vram(vram,plan.cells)
        kernel_cycles=(counts['copy_back_rows']*123+counts['copy_source_rows']*125+counts['mixed_rows']*216)
        measurements.append(dict(epoch=ob['epoch'],role=role,render_noop=reused,
            **counts,missing_tile_pairs=len(plan.slot_writes),dma_bytes=plan.dma_bytes,
            dma_packets=len(plan.packets),changed_map_cells=plan.changed_cells,
            needs_forced_blank=plan.needs_forced_blank,
            row_kernel_nominal_cycles=kernel_cycles,
            row_kernel_only_ms_at_uniform_8_master_clocks=kernel_cycles*8/21477.27,
            pixels_checked=57344,pixel_mismatches=0))
        previous_key=key;previous_patch=patch
    result=dict(scope='OFFLINE actual compiled source assets + retained native oracle; no new native run or native timing claim',
                epochs=measurements,emitted_kernel_row_checks=kernel_checks,
                verified_pixels=len(measurements)*57344,
                render_noops=sum(r['render_noop'] for r in measurements),
                max_warm_dma_bytes=max(r['dma_bytes'] for r in measurements),
                max_row_kernel_nominal_cycles=max(r['row_kernel_nominal_cycles'] for r in measurements))
    (args.output/'actual-asset-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
