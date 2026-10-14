"""Bind occupancy optimization claims to actual native and retained control evidence."""
import hashlib
import json
from pathlib import Path


def certify(folder,result):
    baseline=Path('out/byor-motu-opaque-warm-v4')
    old=json.loads((baseline/'result.json').read_text())
    analysis=json.loads((folder/'asset-validation.json').read_text())
    if hashlib.sha256((baseline/'native/bor.sfc').read_bytes()).hexdigest()!='8b2350b578d926c024ed55490c2d85b8ab88062ec756f098234649af942af637':raise ValueError('OCCUPANCY_BASELINE_IDENTITY')
    if (result['verified_epochs'],result['verified_pixels'],result['pixel_mismatches'],result['unsafe_register_writes'],result['resource_faults'])!=(18,1032192,0,0,0):raise ValueError('OCCUPANCY_NATIVE_CORRECTNESS')
    for i in range(18):
        if (folder/f'native/world-{i:02d}.bin').read_bytes()!=(baseline/f'native/world-{i:02d}.bin').read_bytes():raise ValueError('OCCUPANCY_WORLD_DRIFT')
    if not all(result['negative'][k] for k in ('rejected','vram_unchanged','previous_display_retained')):raise ValueError('OCCUPANCY_REJECTION')
    current=result['measured_costs']['epochs'];previous=old['measured_costs']['epochs']
    if [i for i,r in enumerate(current) if r.get('render_noop')]!=[3,5,7,11,12,13]:raise ValueError('OCCUPANCY_NOOP_DRIFT')
    for i,row in enumerate(current):
        helper=result['helper_measurements'][i];actual=result['observations'][i]['dirty_tiles']
        expected=0 if row.get('render_noop') else analysis['epochs'][i]['source_occupied_tiles']
        if actual!=expected or helper['kernel_calls']!=8*expected:raise ValueError('OCCUPANCY_NATIVE_ADMISSION_COUNT')
        if row.get('render_noop') and any((row['composition_clocks'],row['dma_bytes'],helper['coverage_calls'])):raise ValueError('OCCUPANCY_NOOP_WORK')
    hz=result['measured_costs']['master_clock_hz']
    def maxima(r,rows):
        return dict(coverage_lookup_clocks=max(h['coverage_clocks'] for h in r['helper_measurements'][1:]),
                    preflight_and_allocation_clocks=max(e.get('preflight_and_allocation_clocks',0) for e in rows[1:]),
                    allocation_clocks=max(e.get('allocation_clocks',0) for e in rows[1:]),
                    composition_clocks=max(e['composition_clocks'] for e in rows[1:]),
                    production_clocks=max(e['production_clocks'] for e in rows[1:]),
                    publication_clocks=max(e['publication_clocks'] for e in rows[1:]),
                    dma_clocks=max(e['dma_clocks'] for e in rows[1:]),
                    dma_bytes=max(e['dma_bytes'] for e in rows[1:]))
    before=maxima(old,previous);after=maxima(result,current)
    if after['coverage_lookup_clocks']>=before['coverage_lookup_clocks']/2:raise ValueError('OCCUPANCY_NO_SUBSTANTIAL_REDUCTION')
    if after['publication_clocks']>=before['publication_clocks']:raise ValueError('OCCUPANCY_NO_PUBLICATION_REDUCTION')
    return dict(status='PASS',source_snapshots_byte_identical=18,capacity=analysis['maximum_required_pairs'],
                maximum_extra_admissions=max(e['extra_admissions'] for e in analysis['epochs']),
                admission_comparison=analysis['epochs'],before=before,after=after,
                before_ms={k.replace('_clocks','_ms'):v*1000/hz for k,v in before.items() if k.endswith('_clocks')},
                after_ms={k.replace('_clocks','_ms'):v*1000/hz for k,v in after.items() if k.endswith('_clocks')},
                coverage_reduction_percent=100*(1-after['coverage_lookup_clocks']/before['coverage_lookup_clocks']))
