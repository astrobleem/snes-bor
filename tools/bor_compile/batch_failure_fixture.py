"""Native fault controls only: mode 1 READY abort, 2 partial-queue deferral,
3 stale generation. Mode 0 executes Astra's unchanged production algorithm.
Only transaction metadata is modified; source player and sealed view untouched.
"""
from nonblank_batch_rescue import QUEUE_CAPACITY

def transform(source):
    a=list(source)
    at=a.index('NbFlushQueue:')+3
    a[at:at]=[' lda.l $42D602',' cmp #2',' bne BatchFlushAllowed',' lda.l $42D660',f' cmp #{QUEUE_CAPACITY}',' bcs BatchFlushAllowed',' rts','BatchFlushAllowed:','.a16','.i16']
    at=a.index('NbValidate:')-2
    if a[at:at+2]!=[' lda #0',' sta $70']:raise ValueError('BATCH_STALE_HOOK_DRIFT')
    a[at:at]=[' lda.l $42D602',' cmp #3',' bne BatchEpochNormal',' lda.l $42D604',' inc a',' sta.l $42D604','BatchEpochNormal:','.a16','.i16']
    return a
