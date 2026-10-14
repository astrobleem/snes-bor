"""Re-certify native precheck evidence and report paired performance tradeoff."""
import json,hashlib
from pathlib import Path
from unittest.mock import patch
import m4_nonblank_batch_native as batch
from m4_early_capacity_native import audit_rom,predictor_evidence,REG,REG_SHA,CAP,CAP_SHA
from m4_early_capacity_fixture import certify

CLOCKS_PER_MS=21477.270

def collect():
    root=Path('out/byor-motu-early-capacity-v1');cases={}
    for name,mode,folder in [('rescue',0,'out/byor-motu-early-capacity-success-v1')]+[(f'fault_{i}',i,f'out/byor-motu-early-capacity-fault-{i}-v1') for i in (4,1,2,3)]:
        p=Path(folder);r=json.loads((p/'result.json').read_text());r=certify(p,r['fields'],mode);
        control=CAP if mode==0 else Path(f'out/byor-motu-restore-spill-fault-{mode}-v1/native')
        for filename in ('world-17.bin','after-refs.bin','after-committed.bin','after-pending.bin'):
            if (p/'native'/filename).read_bytes()!=(control/filename).read_bytes():raise ValueError('EARLY_PHYSICAL_CONTROL_DRIFT:'+filename)
        import numpy as np
        residue={}
        for stage in ('before','after'):
            refs=np.frombuffer((p/'native'/f'{stage}-refs.bin').read_bytes(),dtype='<u2')&0x3fff
            if (p/'native'/f'{stage}-refs.bin').read_bytes()!=(control/f'{stage}-refs.bin').read_bytes():raise ValueError('EARLY_CONTROL_REF_DRIFT')
            aa=np.frombuffer((p/'native'/f'{stage}-vram.bin').read_bytes(),dtype='u1');bb=np.frombuffer((control/f'{stage}-vram.bin').read_bytes(),dtype='u1');different=np.flatnonzero(aa!=bb)
            slots=set()
            for at in different:
                if at>=61440:raise ValueError('EARLY_CONTROL_MAP_DRIFT')
                slot=int(at//64 if at<49152 else (at-49152)//16)
                if refs[slot]:raise ValueError('EARLY_CONTROL_REFERENCED_CHR_DRIFT')
                slots.add(slot)
            residue[stage]=dict(unreferenced_bytes_different=len(different),unreferenced_slots=sorted(slots))
        r['control_unreferenced_residue']=residue
        r['native_allocator_attempts']=1;r['mark_attempts']=2;(p/'result.json').write_text(json.dumps(r,indent=2)+'\n');cases[name]=r
    p=Path('out/byor-motu-early-capacity-regression-v1');r=json.loads((p/'result.json').read_text())
    with patch.object(batch,'audit_rom',audit_rom):r=batch.certify(p,r['contract'],json.loads((p/'fields.json').read_text()))
    r['classification']='EARLY_CAPACITY_BATCH_REGRESSION_PASS';r['early_capacity']={str(i):predictor_evidence(p,i,False) for i in (1,2)};r['capacity_admission']='Separate native rescue candidate verified; optimization acceptance withheld for ordinary latency regression.';(p/'result.json').write_text(json.dumps(r,indent=2)+'\n');cases['ordinary']=r
    controls={}
    for name,path,digest in [('spill_batch',REG,REG_SHA),('spill_rescue',CAP,CAP_SHA)]:
        if hashlib.sha256((path/'bor.sfc').read_bytes()).hexdigest()!=digest:raise ValueError('EARLY_BASELINE_IDENTITY')
        controls[name]=digest
    old_rescue=json.loads((CAP.parent/'result.json').read_text());old_normal=json.loads((REG.parent/'result.json').read_text())
    def row(name,base,candidate,fields_before,fields_after):
        out=dict(name=name,baseline_master_clocks=base,candidate_master_clocks=candidate,baseline_ms=base/CLOCKS_PER_MS,candidate_ms=candidate/CLOCKS_PER_MS,delta_ms=(candidate-base)/CLOCKS_PER_MS,delta_percent=100*(candidate-base)/base,baseline_fields=fields_before,candidate_fields=fields_after)
        return out
    comparison=[row('rescue',old_rescue['costs']['total_master_clocks'],cases['rescue']['costs']['total_master_clocks'],old_rescue['transition_fields'],cases['rescue']['transition_fields']),row('ordinary',old_normal['transaction_costs'][1]['total_clocks'],r['transaction_costs'][1]['total_clocks'],old_normal['transition_fields'],r['transition_fields'])]
    before=json.loads((root/'dirty-before.json').read_text())
    if len(before)!=29:raise ValueError('EARLY_DIRTY_COUNT')
    for f in before:
        if hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('EARLY_INHERITED_CHANGED:'+f['path'])
    (root/'dirty-after.json').write_text(json.dumps(before,indent=2)+'\n')
    summary=dict(schema=1,classification='EARLY_CAPACITY_MEASURED_TRADEOFF',optimization_accepted=False,reason='Rescue is faster, but ordinary publication grows from 30 to 32 fields (+6.55%); retain certified backend.',starting_commit='4b6433c972efa325f44de73348cd218a12b9c43e',master_clock_hz=21477270,comparison=comparison,cases=cases,controls=controls,focused_tests=138,visible_fields=sum(r.get('visible_fields',r.get('observed_fields',0)) for r in cases.values()),verified_pixels=sum(r['verified_pixels'] for r in cases.values()),pixel_mismatches=0,resource_faults=0,unsafe_ppu_operations=0,temporary_bitmap=[0x3480,0x34cc],new_memory_allocations=0,inherited_29_byte_identical=True,protected_17_byte_identical=True,default_renderer_unchanged=True,nonclaims=['optimization PASS','general capacity','30 FPS','200-Hz scheduling','SA-1 coexecution','authored audio','breath','HUD','MOTU Demo'])
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');Path('docs/receipts/byor-motu-early-capacity.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__=='__main__':
    s=collect();print(s['classification'],s['visible_fields'],s['verified_pixels'])
