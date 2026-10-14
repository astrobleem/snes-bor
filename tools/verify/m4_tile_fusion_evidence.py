"""Actual assembled layout, exact native A/B identities and paired timing gate."""
import hashlib
import json
from pathlib import Path
import numpy as np
from assemble_sanity import audit_asm
from astra_opaque_kernel import emit
from m4_input_controller_native import offset

BASELINE=Path('out/byor-motu-occupancy-v1')
BASELINE_SHA='edbc7c2e1013cfddb602c29bb2691b2d3cbf79a284e5d1c1f2650b74d713c648'


def audit_rom(rom,contract):
    old=(BASELINE/'native/bor.sfc').read_bytes()
    if hashlib.sha256(old).hexdigest()!=BASELINE_SHA:raise ValueError('FUSION_BASELINE_IDENTITY')
    sy=contract['native_symbols'];start=sy['AstraOpaqueTile'];end=sy['AstraTileDone']+4
    inferred=audit_asm()
    if start!=0x39e200 or end-start!=inferred['bytes'] or end>=0x39f000:raise ValueError('FUSION_ASSEMBLED_PLACEMENT')
    a,b=offset(start),offset(end)
    if any(old[a:b]):raise ValueError('FUSION_OCCUPIED_CODE_LEASE')
    if rom[b:offset(0x39f000)]!=old[b:offset(0x39f000)]:raise ValueError('FUSION_NMI_GAP_CORRUPTION')
    k=offset(sy['AstraOpaqueRow'])
    if rom[k:k+175]!=emit().code or rom[k:k+175]!=old[k:k+175]:raise ValueError('FUSION_REFERENCE_KERNEL_CORRUPTION')
    bank=57*32768
    if rom[:bank]!=old[:bank] or rom[bank+32768:]!=old[bank+32768:]:raise ValueError('FUSION_OUTSIDE_CODE_BANK_CHANGE')
    nmi=offset(0x39f000)
    if rom[nmi:bank+32768]!=old[nmi:bank+32768]:raise ValueError('FUSION_NMI_CORRUPTION')
    return dict(bank=57,start=start,end=end,bytes=end-start,nmi_start=0x39f000,remaining_to_nmi=0x39f000-end,
                baseline_lease_zero=True,old_kernel_byte_identical=True,all_bytes_outside_code_bank_identical=True,
                sha256=hashlib.sha256(rom[a:b]).hexdigest(),inferred_branch_audit=inferred)


def certify(folder,result):
    old=json.loads((BASELINE/'result.json').read_text());paired=[];unused_differences=[]
    if (result['verified_epochs'],result['verified_pixels'],result['pixel_mismatches'],result['unsafe_register_writes'],result['resource_faults'])!=(18,1032192,0,0,0):raise ValueError('FUSION_NATIVE_CORRECTNESS')
    hz=result['measured_costs']['master_clock_hz']
    def register_blank_times(path):
        durations={};epoch=-1;start=None
        for e in json.loads(path.read_text()):
            if e['phase']=='OnlinePublish':epoch+=1;start=None
            elif e['phase']=='INIDISP:128' and start is None:start=e['clock']
            elif e['phase']=='INIDISP:15' and start is not None:durations[epoch]=e['clock']-start;start=None
        return durations
    before_blank=register_blank_times(BASELINE/'native/timing-events.json')
    after_blank=register_blank_times(folder/'native/timing-events.json')
    old_initial=(BASELINE/'native/initial-vram.bin').read_bytes()
    new_initial=(folder/'native/initial-vram.bin').read_bytes()
    packets=json.loads((folder/'native/dma-packets.json').read_text());old_packets=json.loads((BASELINE/'native/dma-packets.json').read_text())
    if packets!=old_packets:raise ValueError('FUSION_DMA_PACKET_DRIFT')
    written=np.zeros(65536,dtype=bool)
    for i,(before,after) in enumerate(zip(old['measured_costs']['epochs'],result['measured_costs']['epochs'],strict=True)):
        for name in ('world','cgram','expected','directory'):
            ext='rgb555' if name=='expected' else 'bin'
            if (folder/f'native/{name}-{i:02d}.{ext}').read_bytes()!=(BASELINE/f'native/{name}-{i:02d}.{ext}').read_bytes():raise ValueError('FUSION_CONTROL_DRIFT:'+name)
        for packet in packets:
            if packet['epoch']==i and packet['target']==0x18:
                at=packet['vram_word']*2;written[at:at+packet['bytes']]=True
        old_vram=(BASELINE/f'native/vram-{i:02d}.bin').read_bytes();new_vram=(folder/f'native/vram-{i:02d}.bin').read_bytes()
        refs=np.frombuffer((folder/f'native/directory-{i:02d}.bin').read_bytes(),dtype='<u2')
        diff=np.flatnonzero(np.frombuffer(old_vram,dtype='u1')!=np.frombuffer(new_vram,dtype='u1'))
        # Legacy boot may leave different garbage in unallocated paired slots.
        # It is admissible ONLY if never DMA-written by either producer, still
        # byte-identical to its own captured boot state, and unreferenced now.
        for at in diff:
            slot=int(at)//64 if at<49152 else (int(at)-49152)//16
            if at>=61440 or written[at] or refs[slot]&0x3fff or old_vram[at]!=old_initial[at] or new_vram[at]!=new_initial[at]:raise ValueError('FUSION_CONTROL_DRIFT:resident_vram')
        unused_differences.append(dict(epoch=i,unreferenced_untouched_boot_bytes=len(diff)))
        h=result['helper_measurements'][i];tiles=result['observations'][i]['dirty_tiles']
        if h['tile_calls']!=tiles or h['kernel_calls']!=8*tiles or h['legacy_row_calls']!=0:raise ValueError('FUSION_NATIVE_CALL_COUNTS')
        if old['observations'][i]['dirty_tiles']!=tiles or old['helper_measurements'][i]['coverage_calls']!=h['coverage_calls']:raise ValueError('FUSION_ADMISSION_DRIFT')
        if bool(before.get('render_noop'))!=bool(after.get('render_noop')):raise ValueError('FUSION_NOOP_DRIFT')
        def measurements(row,register_blank):
            pre=row.get('preflight_and_allocation_clocks',0);comp=row['composition_clocks'];dma=row['dma_clocks']
            other=row['production_clocks']-pre-comp-dma
            blank=0 if row.get('render_noop') else row['publication_clocks']-row['admission_to_blank_clocks']
            clocks=dict(composition=comp,preflight_allocation=pre,dma=dma,other_production=other,production=row['production_clocks'],publication=row['publication_clocks'],forced_blank=blank,forced_blank_register=register_blank)
            return dict(clocks=clocks,ms={k:v*1000/hz for k,v in clocks.items()},dma_bytes=row['dma_bytes'],dma_descriptors=row['dma_transfers'])
        if bool(after.get('render_noop')) and i in after_blank:raise ValueError('FUSION_NOOP_BLANK_WRITE')
        paired.append(dict(epoch=i,render_noop=bool(after.get('render_noop')),tiles=tiles,rows=h['kernel_calls'],before=measurements(before,before_blank.get(i,0)),after=measurements(after,after_blank.get(i,0)),fused_mask_blend_step_ms=h['fused_tile_clocks']*1000/hz,fused_blend_body_ms=h['kernel_clocks']*1000/hz))
    if result['negative']!=old['negative']:raise ValueError('FUSION_REJECTION_DRIFT')
    warm=[p for p in paired[1:] if not p['render_noop']]
    before_max={k:max(p['before']['ms'][k] for p in warm) for k in warm[0]['before']['ms']}
    after_max={k:max(p['after']['ms'][k] for p in warm) for k in warm[0]['after']['ms']}
    material=after_max['composition']<before_max['composition']*.95 and after_max['publication']<before_max['publication'] and all(p['after']['clocks']['composition']<p['before']['clocks']['composition'] for p in warm)
    return dict(status='PASS' if material else 'NO_SPEEDUP',classification='BYOR_MOTU_FUSED_TILE_NATIVE_PASS' if material else 'FUSED_TILE_NO_SPEEDUP',
                meaningful_gate='At least 5% lower worst warm composition, lower worst publication, every changing warm epoch composes faster',
                paired_epochs=paired,warm_worst_before_ms=before_max,warm_worst_after_ms=after_max,
                composition_reduction_percent=100*(1-after_max['composition']/before_max['composition']),
                publication_reduction_percent=100*(1-after_max['publication']/before_max['publication']),
                byte_identical_source_snapshots=18,byte_identical_resident_vram_cgram_directory=18,byte_identical_dma_packets=True,
                unreferenced_boot_differences=unused_differences,
                helper_boundary='Fused tile entry to AstraTileDone fetch includes mask, blend, pointers and loop; excludes final register restoration/RTL. Blend-only AstraTileRow to AstraTilePixelDone differs from old kernel entry to AstraDone; use composition boundaries for A/B.')
