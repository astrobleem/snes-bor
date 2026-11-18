"""Linux BOR host backing, disk, cgroup and bounded-output guards."""
import json
import os
from pathlib import Path
import shutil

if os.environ.get('BOR_HEAVY_LEASE_FD') is not None:
    from bor_linux_heavy_v1296 import inherit_children
    inherit_children()

GIB = 1024 ** 3
_shared_inodes = None

def evaluate(info, mode, start=False, cgroup_budget=None):
    physical = info['MemAvailable']
    backing = physical + info['SwapFree']
    # Linux heuristic/always-overcommit includes uncharged virtual reservations
    # in Committed_AS. It is not Windows available commit. Require real backing
    # instead, plus a non-swapping hard cgroup cap on this job. Strict mode also
    # requires the kernel's remaining commitment allowance.
    strict = info['CommitLimit'] - info['Committed_AS']
    if mode == 2:
        backing = min(backing, strict)
    assert mode in (0, 1, 2), ('OVERCOMMIT_MODE', mode)
    assert physical >= (2.5 if start else 2) * GIB, ('PHYSICAL_FLOOR', physical)
    assert backing >= (8 if start else 4) * GIB, ('BACKING_FLOOR', backing)
    if cgroup_budget is not None:
        assert cgroup_budget >= GIB, ('ANCESTOR_CAPACITY', cgroup_budget)
    return dict(available_GiB=round(physical/GIB,3), available_backing_GiB=round(backing/GIB,3),
                overcommit_mode=mode, strict_commit_remaining_GiB=round(strict/GIB,3))

def require_memory(start=False):
    info = {k:int(v.split()[0])*1024 for k,v in
            (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    mode = int(Path('/proc/sys/vm/overcommit_memory').read_text())
    result = evaluate(info, mode, start)
    group = next(x[3:] for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
    current = Path('/sys/fs/cgroup') / group.lstrip('/')
    # Every finite ancestor must support the requested job, not just host RAM.
    # The job's own 1 GiB cap is containment, not a fabricated host capacity.
    for p in (current,*current.parents):
        if p == Path('/sys/fs'): break
        limit = p/'memory.max'
        if not limit.exists(): continue
        value=limit.read_text().strip()
        if value != 'max' and not p.name.startswith('bor-v1132-'):
            remaining=int(value)-int((p/'memory.current').read_text())
            assert remaining >= GIB, ('ANCESTOR_MEMORY_HEADROOM',str(p),remaining)
    if os.environ.get('BOR_REQUIRE_CGROUP') == '1' or current.name.startswith('bor-v1132-'):
        from bor_linux_heavy_v1296 import inherited_fds
        inherited_fds()
        assert current.name.startswith('bor-v1132-') and current.name.endswith('.service'), str(current)
        assert int((current/'memory.max').read_text()) <= GIB
        assert int((current/'memory.swap.max').read_text()) == 0
        assert int((current/'pids.max').read_text()) <= 128
    return result

def disk_guard(start=False):
    global _shared_inodes
    root=Path(os.environ['BOR_REMOTE_ROOT'])
    free=shutil.disk_usage(root).free
    assert free > (17 if start else 16)*GIB, ('OUTPUT_DISK_FLOOR',free)
    initial=int(os.environ.get('BOR_DISK_INITIAL',free))
    assert initial-free < 256*1024**2, ('OUTPUT_DISK_DROP_CAP',initial,free)
    run=Path(os.environ['BOR_RUN_ROOT'])
    if _shared_inodes is None:
        _shared_inodes=set()
        for shared in (root/'inputs/media',root/'runtime-cache',root/'runtime-qualified'):
            for base,dirs,files in os.walk(shared,followlinks=False):
                for n in dirs+files:assert not (Path(base)/n).is_symlink()
                for n in files:
                    st=(Path(base)/n).stat();_shared_inodes.add((st.st_dev,st.st_ino))
    total=0
    for base,dirs,files in os.walk(run,followlinks=False):
        for name in dirs+files:
            p=Path(base)/name
            assert not p.is_symlink(),('UNEXPECTED_RUN_SYMLINK',str(p))
        for name in files:
            p=Path(base)/name
            st=p.stat()
            if (st.st_dev,st.st_ino) not in _shared_inodes:total+=st.st_size
    assert total < 256*1024**2,('RUN_SIZE_CAP',total)
    return True

# Identity authentication stays in memory; suppress inherited hash artifacts.
_write = Path.write_text
def _clean(value):
    if isinstance(value,dict):return {k:_clean(v) for k,v in value.items() if 'sha256' not in k.lower()}
    if isinstance(value,list):return [_clean(v) for v in value]
    return value
def _filtered_write(path,data,*args,**kwargs):
    if path.name in ('loaded-rom-identity.json','capture-runtime.json'):return len(data)
    if path.suffix=='.json':
        try:data=json.dumps(_clean(json.loads(data)),indent=2)+'\n'
        except ValueError:pass
    return _write(path,data,*args,**kwargs)
Path.write_text=_filtered_write

if __name__=='__main__':
    base=dict(MemAvailable=3*GIB,SwapFree=6*GIB,CommitLimit=10*GIB,Committed_AS=19*GIB)
    assert evaluate(base,0,True)['available_backing_GiB']==9
    cases=[(dict(base,MemAvailable=2*GIB),0),(dict(base,SwapFree=4*GIB),0),(base,2)]
    for case,mode in cases:
        try:evaluate(case,mode,True)
        except AssertionError:pass
        else:raise AssertionError(('NEGATIVE_GUARD_ACCEPTED',case,mode))
    assert evaluate(dict(base,CommitLimit=30*GIB),2,True)
    print('LINUX_MEMORY_GUARD_CASES_PASS',5)
    print('LIVE_MEMORY',require_memory(start=True))
