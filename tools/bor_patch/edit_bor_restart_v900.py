"""Exact reversible three-site worker restart patch; no backup or report."""
from pathlib import Path
import sys,hashlib
R=Path('E:/gh/snes-bor')
ORIGINAL={
 'src/core/actor_s8_normal_sa1_runtime.pasm':'1d7d1d6fa9addd8fcc73273ab8ff4b9e7d3f0eca88c3edd109925641a88a221f',
 'tools/verify/actor_s7_persistent_worker.py':'32c5e77b7610380bbab630f22f6c6e351c3707f9625e050ec10e5f0296befb33'}
PATCHES=(
('src/core/actor_s8_normal_sa1_runtime.pasm',
'''S6Normal_Init__enabled:
    lda #0
    sta.l S6Normal_NmiArm
    sta.l S6Normal_NmiContext
    sta.l $7E175C
''',
'''S6Normal_Init__enabled:
    lda #0
    sta.l S6Normal_NmiArm
    sta.l S6Normal_NmiContext
    sta.l $435442 ; disable old normal publication before the epoch changes
    lda.l $7E175C
    cmp #1
    bne S6Normal_Init__previous_parked
    lda.l $7E175E
    cmp #2
    bne S6Normal_Init__previous_parked
    ; Keep the previous worker parked across all reset/bind/shared copies.
    ; Owned becomes0 below, so ordinary birth-fence End cannot unpark it.
    jsl S6Normal_MutationFenceBegin
S6Normal_Init__previous_parked:
    lda #0
    sta.l $7E175C
'''),
('tools/verify/actor_s7_persistent_worker.py',
'''Worker_MutationFenceWait:
    lda.l $41200C
    bne Worker_MutationFenceWait
    rep #$30
''',
'''Worker_MutationFenceWait:
    lda.l $41200C
    bne Worker_MutationFenceWait
    ; A new-run acquire clears READY while parked, then copies the new
    ; world before releasing this fence. Ordinary birth/retire keeps3.
    lda $3027
    bne Worker_MutationFenceResume
    lda $3025
    cmp #$55
    bne Worker_MutationFenceResume
    lda #3
    sta $3027
Worker_MutationFenceResume:
    rep #$30
'''),
('tools/verify/actor_s7_persistent_worker.py',
'''    lda #$55
    sta $3025
    ldy #$FFFF
Relay_Acquired:
''',
'''    lda #$55
    sta $3025
    ; Cold first acquire has no parked predecessor. On a new run, only
    ; release ACK2 after every world/context/metadata copy above completed.
    lda.l $41200C
    cmp #2
    bne Relay_AcquireUnparked
    lda #0
    sta.l $41200C
Relay_AcquireUnparked:
    ldy #$FFFF
Relay_Acquired:
'''))

def change(reverse=False):
    edits={}
    if not reverse:
        for name,digest in ORIGINAL.items():
            assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest,name
    for name,before,after in (reversed(PATCHES) if reverse else PATCHES):
        path=R/name
        raw=edits.get(path,path.read_bytes())
        eol=b'\r\n' if b'\r\n' in raw else b'\n'
        assert b'\r' not in raw.replace(b'\r\n',b''),name
        a=before.encode().replace(b'\n',eol);b=after.encode().replace(b'\n',eol)
        old,new=(b,a) if reverse else (a,b)
        assert raw.count(old)==1 and raw.count(new)==0,(name,'unexpected patch state')
        edits[path]=raw.replace(old,new,1)
    if reverse:
        for path,data in edits.items():
            assert hashlib.sha256(data).hexdigest()==ORIGINAL[path.relative_to(R).as_posix()],path
    # All patterns validated before any source write. Preserve original EOL.
    for path,data in edits.items():path.write_bytes(data)
    print('RESTORED_EXACT_RESTART_PATCH' if reverse else 'APPLIED_RESTART_PATCH',len(edits),'files')

if __name__=='__main__':change('--restore' in sys.argv)
