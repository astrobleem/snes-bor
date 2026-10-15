"""Inventory all physical backdrop homes from retained, certified native bytes."""
import hashlib,json
from pathlib import Path
import numpy as np

def sha(b):return hashlib.sha256(b).hexdigest()

def inventory(folder):
    native=folder/'native';events=json.loads((folder/'native-events.json').read_text())
    row=next(e for e in events if e['kind']=='CP_PLAN' and e['data'][:2]==['3','1'])
    refs=np.frombuffer(bytes.fromhex(row['data'][5]),dtype='<u2')
    marked=np.frombuffer(bytes.fromhex(row['data'][6]),dtype='<u2').copy()
    vr=(native/'before-second-vram.bin').read_bytes()
    hi=np.frombuffer(vr[61440:63488],dtype='<u2');lo=np.frombuffer(vr[63488:],dtype='<u2')
    committed=np.frombuffer((native/'before-second-committed.bin').read_bytes(),dtype='<u2')
    if not np.array_equal(hi,lo) or not np.array_equal(hi,committed):raise ValueError('BORROW_DISPLAY_MAP_IDENTITY')
    if not np.array_equal(refs&0x3fff,np.bincount(hi,minlength=768)):raise ValueError('BORROW_REFERENCE_DIRECTORY_IDENTITY')
    allocated=[int(e['data'][2]) for e in events if e['kind']=='CP_ALLOC' and e['data'][:2]==['3','1']]
    # Reproduce the retained restoration planner in its actual first-appearance
    # order, using the native reservations, not invented physical destinations.
    pending=marked.copy();restores=[]
    for value in marked:
        home=int(value)
        if home<596 and refs[home]&0x8000 and home not in restores:restores.append(home)
    if len(restores)!=10 or len(allocated)!=64:raise ValueError('BORROW_RETAINED_EXACT_PLAN_DRIFT')
    reservations=allocated[:len(restores)]
    for home,dest in zip(restores,reservations):pending[pending==home]=dest|0x4000
    high=(Path('out/byor-motu-online-v3/assets')/'high.chr').read_bytes()
    rom=(native/'bor.sfc').read_bytes();low=rom[0x210000:0x210000+596*16]
    # These are the exact authoritative source banks used by WarmCopyBackdrop.
    if high[:596*64]!=rom[0x200000:0x200000+596*64]:raise ValueError('BORROW_IMMUTABLE_HIGH_AUTHORITY')
    queue=(native/'before-second-queue.bin').read_bytes()
    if int.from_bytes(queue[:2],'little') or any(e['kind']=='PACKET' and e['data'][0]=='3' for e in events):raise ValueError('BORROW_UNRESOLVED_DMA_RESERVATION')
    rows=[];invalid=[];valid=[]
    for home in range(596):
        used_high=int(np.count_nonzero(hi==home));used_low=int(np.count_nonzero(lo==home))
        pending_uses=int(np.count_nonzero((pending&0x3fff)==home))
        bad=bool(refs[home]&0x8000)
        physical_original=(vr[home*64:(home+1)*64]==high[home*64:(home+1)*64]
                           and vr[49152+home*16:49152+(home+1)*16]==low[home*16:(home+1)*16])
        if not bad and not physical_original:raise ValueError('BORROW_VALID_FLAG_WITH_NONORIGINAL_PAIR:'+str(home))
        reserved=home in reservations
        eligible=not (int(refs[home])&0x3fff or used_high or used_low or pending_uses or reserved)
        if eligible:(invalid if bad else valid).append(home)
        rows.append(dict(home=home,display_high_references=used_high,display_low_references=used_low,
                         committed_reference_count=int(refs[home]&0x3fff),pending_physical_references=pending_uses,
                         invalid=bad,physical_pair_original=physical_original,reserved=reserved,
                         high_chr_bytes=[home*64,(home+1)*64],low_chr_bytes=[49152+home*16,49152+(home+1)*16],borrowable=eligible))
    return dict(status='BORROW_CAPACITY_GATE_PASS' if len(invalid)+len(valid)>=41 else 'BACKDROP_HOME_BORROW_BLOCKED',
                invalid_candidates=invalid,valid_candidates=valid,invalid_count=len(invalid),valid_count=len(valid),
                required_borrow=41,restoration_homes=restores,restoration_destinations=reservations,homes=rows,
                physical_vram_sha256=sha(vr),high_map_sha256=sha(vr[61440:63488]),low_map_sha256=sha(vr[63488:]),
                reference_sha256=sha(refs.tobytes()),marked_map_sha256=sha(marked.tobytes()),restoration_planned_map_sha256=sha(pending.tobytes()),
                planned_reservations_tail_only=True,queue_empty=True,complete_pair_eligibility=True)

if __name__=='__main__':
    r=inventory(Path('out/byor-motu-consecutive-up-v2'))
    Path('out/byor-motu-home-borrow-v1/capacity.json').write_text(json.dumps(r,indent=2)+'\n')
    print(r['status'],r['invalid_count'],r['invalid_candidates'],r['valid_count'],r['valid_candidates'])
