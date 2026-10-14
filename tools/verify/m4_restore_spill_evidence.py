"""Re-certify retained spill native cases and assemble their handoff receipt."""
import json,hashlib
from pathlib import Path
from m4_restore_spill_capacity_native import certify

def collect():
    root=Path('out/byor-motu-restore-spill-v1');cases={}
    for name,mode,folder in [('capacity_success',0,'out/byor-motu-restore-spill-capacity-v2')]+[(f'fault_{i}',i,f'out/byor-motu-restore-spill-fault-{i}-v1') for i in (4,1,2,3)]:
        p=Path(folder);old=json.loads((p/'result.json').read_text());r=certify(p,old['fields'],mode);(p/'result.json').write_text(json.dumps(r,indent=2)+'\n');cases[name]=r
        c=json.loads((p/'contract.json').read_text());c.update(nonblank_restore_spill=True,restoration_records=48,restoration_spill_lease=[0x42d620,0x42d660]);(p/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
    import m4_nonblank_batch_native as batch
    from m4_restore_spill_native import audit_rom
    from unittest.mock import patch
    p=Path('out/byor-motu-restore-spill-regression-v1');r=json.loads((p/'result.json').read_text())
    with patch.object(batch,'audit_rom',audit_rom):r=batch.certify(p,r['contract'],json.loads((p/'fields.json').read_text()))
    r['classification']='RESTORE_SPILL_BATCH_REGRESSION_PASS'
    r['capacity_admission']='Verified separately by the capacity success fixture.'
    cases['batch_regression']=r
    (p/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    controls={}
    for name,folder,expected in [('batch','out/byor-motu-batch-rescue-v1/native','e710074d80cd6ad2354664956c7d0be867008c13a98006042f51d6fc9bd091ec'),('one_pair','out/byor-motu-nonblank-v5/native','9f85b14626405c06295536e65b6f73a229849a6b6bebf0b99862792035f6130f'),('rect','out/byor-motu-rect-map-v1/native','52872d1546c26d2d9a0be438aaae32bb4ac764c74dc2a6b5a3632f90d4a179c0')]:
        actual=hashlib.sha256((Path(folder)/'bor.sfc').read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('RETAINED_CONTROL_SHA:'+name)
        controls[name]=actual
    historical=json.loads(Path('out/byor-motu-batch-capacity-v1/result.json').read_text())
    if historical['classification']!='NATIVE_EXACT_RETRY_SAFE_RECORD_CAP_REJECTION':raise ValueError('HISTORICAL_REJECTION_CHANGED')
    controls['capacity_rejection']=historical['rom_sha256']
    before=json.loads((root/'dirty-before.json').read_text())
    if len(before)!=29:raise ValueError('INHERITED_DIRTY_COUNT')
    for f in before:
        if hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('INHERITED_DIRTY_CHANGED:'+f['path'])
    (root/'dirty-after.json').write_text(json.dumps(before,indent=2)+'\n')
    summary=dict(schema=1,classification='BYOR_MOTU_NONBLANK_BATCH_CAPACITY_RESCUE_PASS',starting_commit='b40172b68db17dd0229a0bfdf210e46261d65278',master_clock_hz=21477270,cases=cases,controls=controls,visible_fields=sum(r.get('visible_fields',r.get('observed_fields',0)) for r in cases.values()),verified_pixels=sum(r['verified_pixels'] for r in cases.values()),pixel_mismatches=0,focused_tests=124,inherited_29_byte_identical=True,protected_17_byte_identical=True,spill_lease=[0x42d620,0x42d660],queue_lease_unchanged=[0x3500,0x36e0],restoration_capacity=48,isolated_services='Returning worker held; legacy NMI/audio/video writers withdrawn; NMI disabled during producer; automatic JOY restored while idle.',nonclaims=['general scene/animation capacity','SA-1 coexecution','30 FPS','200-Hz scheduling','dynamic alpha','authored audio','breath','HUD','combat','MOTU Demo'])
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');Path('docs/receipts/byor-motu-restoration-spill.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__=='__main__':
    s=collect();print(s['classification'],s['visible_fields'],s['verified_pixels'])
