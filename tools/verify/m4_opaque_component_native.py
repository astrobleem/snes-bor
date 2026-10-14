"""Measure the opaque replacement against the retained native source fixture."""
import argparse
import json
import os
from pathlib import Path
import shutil
from compiler import Source
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_online_component_native import run
from m4_online_component_publisher import build
from m4_opaque_component_publisher import transform,capacity_bound
from m4_live_ground_component_native import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--phases',type=Path,default=Path('out/astra-opaque-assets-v1'))
    p.add_argument('--source',type=Path,default=Path('Masters of the Universe [v.3.0 Build 4086].pak'))
    p.add_argument('--occupancy',type=Path);p.add_argument('--tile-fusion',action='store_true');p.add_argument('--direct-pair-dma',action='store_true');p.add_argument('--rect-map-diff',action='store_true');p.add_argument('--nonblank-slice',action='store_true');p.add_argument('--run-existing',action='store_true');p.add_argument('--build-only',action='store_true');p.add_argument('--warm',action='store_true');a=p.parse_args()
    folder=a.output.resolve();native=folder/'native';native.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path('src/main.sym'));baseline=Path('out/byor-motu-online-v3');original=(baseline/'native/bor.sfc').read_bytes()
    if sha(original)!='d58ea3f89e2130ee00723823e02bc04e3312fea4ce15c15884eb292f9faf332e':raise ValueError('OPAQUE_SCALAR_ORACLE_ROM_IDENTITY')
    if not a.run_existing:
        if a.occupancy:
            from m4_occupancy_assets import verify as verify_assets
            analysis=verify_assets(a.phases,a.occupancy,baseline/'assets',Path('out/byor-motu-opaque-warm-v4/native/observations.json'))
            (folder/'asset-validation.json').write_text(json.dumps(analysis,indent=2)+'\n')
        # Remove ONLY the previous private component leases. Source owners,
        # constructor tables and all other fixture bytes are retained verbatim.
        rom=bytearray(original);rom[57*32768:58*32768]=bytes(32768)
        for at,n in ((0x200000,131072),(0x220000,76288),(0x240000,57344),(0x250000,50000),
                     (0x260000,68200),(0x280000,68200),(0x2a0000,512)):
            rom[at:at+n]=bytes(n)
        nmi=offset(sy['nmi_handler']);base=(baseline/'base/bor.sfc').read_bytes();rom[nmi:nmi+8]=base[nmi:nmi+8]
        rom,contract=build(rom,sy,native,baseline/'assets',transform(a.phases,a.warm,baseline/'assets',a.occupancy,a.tile_fusion,a.direct_pair_dma,a.rect_map_diff,a.nonblank_slice))
        contract.update(opaque_phase_rows=True,capacity_proof=capacity_bound(a.phases),scalar_reference_sha256=sha(original),phase_manifest=json.loads((a.phases/'manifest.json').read_text()),
            visual_key_excludes_fraction_and_epoch=True,immutable_authority_generations=dict(palette=1,layer_underlay=1,camera=0),dp_lease=[0x3400,0x3480 if a.warm else 0x3460],persistent_key_lease=[0x42d6d0,0x42d6f2],warm_residency=a.warm,occupancy_preflight=a.occupancy is not None,tile_fusion=a.tile_fusion,direct_pair_dma=a.direct_pair_dma,rect_map_diff=a.rect_map_diff,nonblank_slice=a.nonblank_slice)
        if a.occupancy:
            contract['occupancy_manifest']=json.loads((a.occupancy/'occupancy-manifest.json').read_text())
            contract['occupancy_rom_lease']=[0xf43600,0xf4d700]
        if a.tile_fusion:
            from m4_tile_fusion_evidence import audit_rom
            contract['tile_fusion_layout']=audit_rom(rom,contract)
        if a.nonblank_slice:
            from m4_nonblank_component_native import audit_rom
            contract["nonblank_layout"]=audit_rom(rom,native)
            contract['resources']['runtime_publication']='Cold forced blank; warm preparation visible, free-tail CHR pairs in fresh VBlanks; paired maps in one VBlank.'
            contract['publication']='Single-owner pending transaction; committed maps/refcounts retained until map DMA completion; owned RAM bookkeeping then epoch/state release.'
            contract['transaction_header_lease']=[0x42d600,0x42d680]
        elif a.rect_map_diff:
            from m4_rect_map_evidence import audit_rom as audit_rectangle
            contract['rect_map_layout']=audit_rectangle(rom,contract,native)
        elif a.direct_pair_dma:
            from m4_direct_pair_evidence import audit_rom as audit_direct
            contract['direct_pair_layout']=audit_direct(rom,contract)
        (native/'bor.sfc').write_bytes(rom);(folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        script=(baseline/'native/callback_owner.lua').read_text().split('-- ONLINE_OBSERVER_BEGIN')[0]
        (native/'callback_owner.lua').write_text(script)
        if not(native/'bor.msu').exists():os.link(baseline/'native/bor.msu',native/'bor.msu')
    else:contract=json.loads((folder/'contract.json').read_text())
    if not a.build_only:
        if contract.get('nonblank_slice'):
            from m4_nonblank_component_native import run as run_slice
            run_slice(folder,Source(a.source),sy,contract)
            return
        result=run(folder,Source(a.source),sy,contract)
        if contract['warm_residency']:
            from m4_opaque_dma_replay import verify
            result['actual_dma_replay']=verify(folder)
            (native/'dma-replay.json').write_text(json.dumps(result['actual_dma_replay'],indent=2)+'\n')
            (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if contract.get('occupancy_preflight'):
            from m4_occupancy_evidence import certify
            result['occupancy_preflight']=certify(folder,result)
            result['classification']='BYOR_MOTU_OCCUPANCY_PREFLIGHT_PASS'
            (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if contract.get('rect_map_diff'):
            from m4_rect_map_evidence import certify
            result['rect_map_diff']=certify(folder,result)
            result['classification']=result['rect_map_diff']['classification']
            (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        elif contract.get('direct_pair_dma'):
            from m4_direct_pair_evidence import certify
            result['direct_pair_dma']=certify(folder,result)
            result['classification']=result['direct_pair_dma']['classification']
            (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        elif contract.get('tile_fusion'):
            from m4_tile_fusion_evidence import certify
            result['tile_fusion']=certify(folder,result)
            result['classification']=result['tile_fusion']['classification']
            (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
