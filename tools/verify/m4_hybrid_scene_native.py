"""PPU/OBJ/CGRAM proof for an explicit lossless hybrid source pose."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
import m4_bg_components_native as bg
from _harness import McpSession


def prepare(folder):
    r=json.loads((folder/'report.json').read_text());out=folder/'native-input';out.mkdir(exist_ok=True)
    high=np.fromfile(folder/'high.bin',dtype=np.uint8).reshape(224,256)
    (out/'indices.bin').write_bytes((high-3).tobytes())
    (out/'low_indices.bin').write_bytes((folder/'low.bin').read_bytes())
    (out/'expected.rgb555').write_bytes((folder/'expected.bin').read_bytes())
    state=[0]*236
    for entry in r['bg_schedule']['initial']:state[entry['slot']-4]=entry['color'] or 0
    (out/'initial.json').write_text(json.dumps(state)+'\n')
    starts={e['scanline']:e for e in r['bg_schedule']['trace']};trace=[];bursts=[]
    start=r['dynamic_physical_slots'][0]
    for y in range(224):
        entry=starts.get(y);events=[]
        if entry:
            start=entry['cgram_start']
            events=[dict(slot=start+i-3,color=c or 0) for i,c in enumerate(entry['values'])]
        trace.append(dict(scanline=y,updates=events));bursts.append(dict(scanline=y,start_slot=start-3))
    span=r['bg_schedule']['span']
    report=dict(bg_mode=4,low_bpp=2,high_palette_start=4,high_opaque_capacity=236,
        low_chr_vram_base=49152,low_component_palette=r.get('low_component_palette',[0,32,1024,1056]),span=span,
        trace=trace,contiguous_bursts=bursts,peak_hblank_colors_written=span,native_obj_entries=r['native_obj_entries'])
    path=out/'report.json';path.write_text(json.dumps(report,indent=2)+'\n')
    return r,report,path,out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--timer',type=int,default=160)
    p.add_argument('--static-residency',type=Path,help='Use a verified retained/subdivided ordinary OBJ atlas')
    p.add_argument('--share-low-offset-map',action='store_true')
    p.add_argument('--resident-bg-tiles',action='store_true',help='Use the verified static residency HIGH/LOW CHR and maps')
    a=p.parse_args();folder=a.assets.resolve();output=a.output.resolve();output.mkdir(parents=True,exist_ok=True)
    source,report,path,inputs=prepare(folder);compiler=bg.compile_rom
    promoted=np.fromfile(folder/'promoted.bin',dtype=np.bool_).reshape(28,32)
    chr_data=(folder/'obj_chr.bin').read_bytes();oam=(folder/'oam.bin').read_bytes()
    high_base=8192;high_tile_offset=0;obsel=0xc0;residency=None
    if a.static_residency:
        residency=json.loads((a.static_residency/'report.json').read_text())
        if not residency['static_obj_retention_verified']:raise ValueError('HYBRID_STATIC_RETENTION_UNPROVEN')
        chr_data=(a.static_residency/'obj.chr').read_bytes();oam=(a.static_residency/'oam.bin').read_bytes()
        report['native_obj_entries']=residency['static_obj_entries']
        if residency['static_obj_subdivision']:
            high_base=0;high_tile_offset=64;obsel=0
        path.write_text(json.dumps(report,indent=2)+'\n')
    cache_assets=None
    if a.resident_bg_tiles:
        if not a.static_residency or not a.share_low_offset_map:raise ValueError('HYBRID_RESIDENT_BG_REQUIRES_STATIC_RESIDENCY_AND_LOW_ALIAS')
        cache_assets=inputs/'resident-bg';cache_assets.mkdir(exist_ok=True)
        # *-tiles.chr is the source tile vocabulary, not a physical VRAM image.
        # Replay the first boot assignment into the actual sparse slot array.
        for plane,stride in [('high',64),('low',16)]:
            vocabulary=(a.static_residency/(plane+'-tiles.chr')).read_bytes()
            plan=residency[plane];resident=bytearray(plan['slot_extent']*stride)
            for write in plan['frames'][0]['writes']:
                if write['phase']!='BOOT':raise ValueError('HYBRID_RESIDENT_BG_BOOT_PHASE')
                slot,tile=write['slot'],write['tile'];data=vocabulary[tile*stride:(tile+1)*stride]
                if len(data)!=stride:raise ValueError('HYBRID_RESIDENT_BG_TILE_VOCABULARY')
                resident[slot*stride:(slot+1)*stride]=data
            (cache_assets/(plane+'.chr')).write_bytes(resident)
        for target,name in [('0-high.map','00-high.map'),('0-low.map','00-low.map')]:
            (cache_assets/target).write_bytes((a.static_residency/name).read_bytes())
        (cache_assets/'layout.json').write_text(json.dumps(dict(low_chr_vram_base=residency['allocation']['low_chr'][0]))+'\n')
    def compile_hybrid(r,assets,timer,**kwargs):
        if a.share_low_offset_map:kwargs['offset_alias']='low'
        return compiler(r,assets,timer,high_base=high_base,high_tile_offset=high_tile_offset,obj_obsel=obsel,
            priority_mask=promoted,obj_chr=chr_data,oam=oam,cache_assets=cache_assets,**kwargs)
    class ObservedHybrid(McpSession):
        def __enter__(self):
            lua=output/'observer.lua'
            with lua.open('a') as f:
                f.write('''
local oam={};local shown=false
emu.addMemoryCallback(function(a,v) if not shown then oam[#oam+1]=string.format('%02x',v) end end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v) if v==15 and not shown then shown=true;emu.log('HYBRIDOAM|'..table.concat(oam,'')) end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function() if shown then emu.log('HYBRIDFLAGS|'..emu.read(0x213e,emu.memType.snesMemory)) end end,emu.eventType.endFrame)
''')
            return super().__enter__()
    argv=['m4_bg_components_native.py','--report',str(path),'--assets',str(inputs),'--output',str(output),'--timer',str(a.timer)]
    with patch.object(sys,'argv',argv),patch.object(bg,'compile_rom',compile_hybrid),patch.object(bg,'McpSession',ObservedHybrid):
        bg.main()
    result=json.loads((output/'result.json').read_text());log=(output/'mesen.log').read_text()
    observed=[line.split('HYBRIDOAM|',1)[1] for line in log.splitlines() if 'HYBRIDOAM|' in line]
    flags=[int(line.split('HYBRIDFLAGS|',1)[1]) for line in log.splitlines() if 'HYBRIDFLAGS|' in line]
    result.update(schema='BYOR_HYBRID_SOURCE_POSE_NATIVE_V1',oam_observer_verified=observed==[oam.hex()],
        oam_sha256=hashlib.sha256(oam).hexdigest(),obj_chr_sha256=hashlib.sha256(chr_data).hexdigest(),
        ppu_obj_status=flags,obj_overflow_samples=sum(bool(v&0xc0) for v in flags),
        obj_palette_banks=source['obj_banks'],bg_exact_obj_palette_aliases=source['bg_exact_obj_palette_aliases'],
        promoted_tiles=source['promoted_tiles'],fully_bg_occluded_obj_entries=source['fully_bg_occluded_obj_entries'],
        source_rgb555_sha256=source['source_rgb555_sha256'],source_scene=source['scene'],
        no_color_reduction=True,scope='Native explicit hybrid pose, source-sized graphics, exact SCREEN already compiled; no live world, moving underlay generation, audio or Demo certification')
    if residency:
        result['static_obj_subdivision']=residency['static_obj_subdivision']
        result['resident_bg_tiles']=a.resident_bg_tiles
        result['residency_allocation']=residency['allocation']
    result['pass']=result['pass'] and result['oam_observer_verified'] and bool(flags) and not result['obj_overflow_samples']
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('pass','pixel_mismatches','oam_observer_verified','obj_overflow_samples','ppu_obj_status')}))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
