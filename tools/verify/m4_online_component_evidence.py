"""Independent replay of displayed pixels, source movement and measured fences."""
import argparse
import json
from pathlib import Path
import struct
import numpy as np
from PIL import Image
from compiler import Source
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from m4_live_ground_component_native import sha,scene_from_snapshot,check_motion

MASTER_HZ=21477270


def costs(events):
    epochs=[];current=None;tile=None;encode=None;dma=None
    # Two callbacks can occupy the same native instruction boundary (final
    # DMA completion and OnlineComplete). Registration order is not chronology.
    events=sorted(events,key=lambda e:(e['clock'],0 if e['phase'].startswith(('OnlineDmaDone','OnlineBootDmaDone')) else 1))
    for e in events:
        p=e['phase'];t=e['clock']
        if p=='OnlinePublish':
            if current is not None:raise ValueError('ONLINE_UNFINISHED_PRODUCTION_TRACE')
            current=dict(start=t,gather_clocks=0,encode_clocks=0,dma_clocks=0,dma_bytes=0,dma_transfers=0)
        elif current is None:continue
        elif p=='OnlineTile':tile=t
        elif p=='OnlineEncode':
            if tile is None:raise ValueError('ONLINE_GATHER_TRACE')
            current['gather_clocks']+=t-tile;encode=t
        elif p=='OnlineTransfer':
            if encode is None:raise ValueError('ONLINE_ENCODE_TRACE')
            current['encode_clocks']+=t-encode
        elif p.startswith('DMA:'):
            if dma is not None:raise ValueError('ONLINE_DMA_WITHOUT_COMPLETION')
            n=int(p.split(':')[1]);current['dma_bytes']+=n;current['dma_transfers']+=1;dma=t
        elif p.startswith(('OnlineDmaDone','OnlineBootDmaDone')):
            if dma is None:raise ValueError('ONLINE_COMPLETION_WITHOUT_DMA')
            current['dma_clocks']+=t-dma;dma=None
        elif p=='OnlineComplete':
            if dma is not None:raise ValueError('ONLINE_PUBLICATION_BEFORE_DMA')
            current['complete']=t
        elif p=='INIDISP:15':
            if 'complete' not in current:raise ValueError('ONLINE_PARTIAL_PUBLICATION')
            current['production_clocks']=current['complete']-current['start']
            current['publication_clocks']=t-current['start']
            current['composition_clocks']=current['gather_clocks']+current['encode_clocks']
            current['non_dma_production_clocks']=current['production_clocks']-current['dma_clocks']
            for k in ('composition','production','publication','dma','non_dma_production'):
                current[k+'_ms']=current[k+'_clocks']*1000/MASTER_HZ
            epochs.append(current);current=None
        elif p=='OnlineReject':
            if dma is not None or current['dma_transfers']:raise ValueError('ONLINE_REJECTION_AFTER_MUTATION')
            current=None
    if current is not None or not epochs:raise ValueError('ONLINE_INCOMPLETE_COST_TRACE')
    fields=('composition_clocks','production_clocks','publication_clocks','dma_clocks','dma_bytes','dma_transfers',
            'non_dma_production_clocks','composition_ms','production_ms','publication_ms','dma_ms','non_dma_production_ms')
    return dict(master_clock_hz=MASTER_HZ,epochs=epochs,worst={k:max(e[k] for e in epochs) for k in fields},
        boundary='Actual emulated master-clock callbacks. DMA completion is sampled after the first post-DMA instruction, because Mesen fetch callbacks precede pending DMA; intervals include that instruction. Composition is source gathering plus planar encoding; non-DMA production also includes preflight, PPU setup and DMA setup. Publication ends at INIDISP=15. No real-time admission.')


def decode_vram(vram,cgram):
    """Decode actual PPU storage independently of producer/compiler encoding."""
    palette=np.frombuffer(cgram,dtype='<u2');out=np.zeros((224,256),dtype='<u2')
    for y in range(224):
        for x in range(256):
            at=((y//8)*32+x//8)*2
            total=0
            for mapbase,chrbase,bpp in ((0xf000,0,8),(0xf800,0xc000,2)):
                word=struct.unpack_from('<H',vram,mapbase+at)[0]
                if word&0xfc00 or (word&1023)>=768:raise ValueError('ONLINE_UNSAFE_DESCRIPTOR')
                tile=word&1023;row=y%8;col=x%8;index=0
                for p in range(bpp):
                    byte=vram[chrbase+tile*8*bpp+(p//2)*16+row*2+p%2]
                    index|=((byte>>(7-col))&1)<<p
                if bpp==8 and index<4:raise ValueError('ONLINE_HIGH_TRANSPARENCY')
                total+=int(palette[index])
            out[y,x]=total
    return out


def verify(folder,source):
    result=json.loads((folder/'result.json').read_text());native=folder/'native';old=None;subpixels=[];newpositions=set();movement_changed=[];seen=[];vertical=[]
    if sha(source.path.read_bytes())!=result['source_pak_sha256']:raise ValueError('ONLINE_SOURCE_IDENTITY')
    previous=json.loads(Path('out/byor-motu-movement-component-v5/result.json').read_text())
    oldpositions={(int(s['x_q16'])//65536,int(s['z_q16'])//65536) for s in previous['samples']}
    for r in result['observations']:
        i=r['epoch'];raw=(native/f'world-{i:02d}.bin').read_bytes()
        if sha(raw)!=r['sha256'] or struct.unpack_from('<H',raw,144)[0]!=i:raise ValueError('ONLINE_WORLD_IDENTITY')
        expected=rgb555(compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene_from_snapshot(raw,source))[0]).astype('<u2')
        screenshot=rgb555(np.asarray(Image.open(native/f'display-{i:02d}.png').convert('RGB')))
        vram=(native/f'vram-{i:02d}.bin').read_bytes();cgram=(native/f'cgram-{i:02d}.bin').read_bytes()
        decoded=decode_vram(vram,cgram)
        if not np.array_equal(expected,screenshot) or not np.array_equal(expected,decoded):raise ValueError('ONLINE_INDEPENDENT_PIXEL_REPLAY')
        if sha(vram)!=r['vram_sha256'] or sha(cgram)!=r['palette_sha256']:raise ValueError('ONLINE_GENERATED_DATA_IDENTITY')
        actor=r['scene']['actors'][0];pos=tuple(int(v) for v in actor['position'][:2])
        for before,beforepixels in seen:
            a=before['scene']['actors'][0]
            if (a['animation'],a['frame'],a['direction'])==(actor['animation'],actor['frame'],actor['direction']) and int(a['position'][0])==pos[0] and int(a['position'][1])!=pos[1]:
                if np.array_equal(expected,beforepixels):raise ValueError('ONLINE_VERTICAL_MOVEMENT_NOT_VISIBLE')
                vertical.append([before['epoch'],i])
        if pos not in oldpositions:newpositions.add(pos)
        if old is not None:
            prior,priorpixels=old
            a=prior['scene']['actors'][0]
            if a['animation']==actor['animation'] and a['frame']==actor['frame'] and a['direction']==actor['direction']:
                if tuple(int(v) for v in a['position'][:2])==pos and a['position']!=actor['position']:
                    if not np.array_equal(expected,priorpixels):raise ValueError('ONLINE_SUBPIXEL_PROJECTION')
                    subpixels.append([i-1,i])
                elif not np.array_equal(expected,priorpixels):movement_changed.append([i-1,i])
        old=r,expected
        seen.append(old)
    if len(newpositions)<2 or not subpixels or not movement_changed or not vertical:raise ValueError('ONLINE_MOVEMENT_COVERAGE')
    if result['contract']['complete_actor_contexts'] or result['contract']['finite_position_selector']:raise ValueError('ONLINE_FINITE_CONTEXT_DEPENDENCY')
    if sha((native/'bor.sfc').read_bytes())!=result['rom_sha256']:raise ValueError('ONLINE_ROM_IDENTITY')
    rejected=(native/'rejected-world.bin').read_bytes()
    if sha(rejected)!=result['negative']['world_snapshot_sha256'] or rejected[:8]!=(native/f'world-{i:02d}.bin').read_bytes()[:8]:raise ValueError('ONLINE_REJECTED_WORLD_IDENTITY')
    if struct.unpack_from('<I',rejected,28)[0]!=0 or result['negative']['raw_controller']!=0x200:raise ValueError('ONLINE_REJECTED_CONTROLLER_CONTEXT')
    if (native/'rejected-vram.bin').read_bytes()!=(native/f'vram-{i:02d}.bin').read_bytes():raise ValueError('ONLINE_REJECTED_VRAM_CORRUPTION')
    if not np.array_equal(rgb555(np.asarray(Image.open(native/'rejected.png').convert('RGB'))),old[1]):raise ValueError('ONLINE_REJECTED_DISPLAY_CORRUPTION')
    check_motion(result['observations'])
    return dict(status='PASS',source_and_actual_vram_and_screenshots_equal=True,verified_pixels=result['verified_pixels'],
        newly_generated_integer_positions=sorted(newpositions),subpixel_same_pixels=subpixels,movement_changes_coverage=movement_changed,vertical_movement_pixel_pairs=vertical,
        complete_actor_canvases_in_rom=0,finite_position_selector=False,negative_context_retention_verified=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=verify(a.output,Source(a.source));(a.output/'native/independent-replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
