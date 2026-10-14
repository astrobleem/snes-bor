"""Fail-closed native 65816 source splice for MOTU batch restoration spill.

Input: assembly emitted by `nonblank_batch_rescue.transform` at b40172b...
Output: same assembly with 48 restoration records instead of 32:
  records  0..31: I-RAM $003480..$0034ff (128 B, already leased)
  records 32..47: BW-RAM $42d620..$42d65f (64 B, previously unused
                  chunk space in the exact isolated fused fixture)

The six-pair DMA queue remains $003500..$0036df. No other changes.
No claim of native assembly, Mesen correctness, timing, or general scope.
"""
from collections.abc import Sequence

OLD_CAPACITY = 32
SPILL_CAPACITY = 16
NEW_CAPACITY = OLD_CAPACITY + SPILL_CAPACITY
IRAM_BASE = 0x003480
SPILL_BASE = 0x42D620
SPILL_END = SPILL_BASE + 4*SPILL_CAPACITY
QUEUE_BASE = 0x003500
QUEUE_END = 0x0036E0
META_BASE = 0x42D660


class RestoreSpillContractError(ValueError):
    pass


def _splice_once(a: list[str], original: list[str], replacement: list[str], code: str) -> None:
    positions = [j for j in range(len(a)-len(original)+1) if a[j:j+len(original)]==original]
    if len(positions)!=1:
        raise RestoreSpillContractError(f'{code}: expected 1 anchor, got {len(positions)}')
    j=positions[0];a[j:j+len(original)]=replacement


def transform(source: Sequence[str]) -> list[str]:
    """Apply after nonblank_batch_rescue.transform and its optional fault hooks.

    Fail closed if generated program drifted, spill memory has an existing
    textual claimant, or required program ordering changed. Native audit must
    additionally verify *runtime* ownership, binary placement and mutation.
    """
    a=list(source)
    required=('NbRestorePlan:','NbActorPlanStart:','NbRestoreProduce:',
              'NbActorProduceStart:','NbFree:','NbBeginRetry:',
              'NbFlushQueue:','NbCodeEnd:','.org $C000')
    for label in required:
        if a.count(label)!=1:
            raise RestoreSpillContractError('LABEL_DRIFT:'+label)
    if not (a.index('NbRestorePlan:')<a.index('NbActorPlanStart:')<a.index('NbRestoreProduce:')
            <a.index('NbActorProduceStart:')<a.index('NbCodeEnd:')<a.index('.org $C000')):
        raise RestoreSpillContractError('PROGRAM_ORDER_DRIFT')
    if (IRAM_BASE + OLD_CAPACITY*4 != QUEUE_BASE or SPILL_END > META_BASE
            or SPILL_BASE < 0x42D620 or QUEUE_END>0x3700):
        raise RestoreSpillContractError('LEASE_LAYOUT_INVALID')
    for label in ('NbRestoreStoreOverflow:', 'NbRestoreStoreDone:',
                  'NbRestoreLoadOverflow:', 'NbRestoreLoadDone:'):
        if label in a:raise RestoreSpillContractError('DUPLICATE_SPILL:'+label)
    # Retained generated program must not already reference the scratch range.
    # All of its previous restoration accesses were redirected to $003480.
    for line in a:
        if line.strip().startswith(('lda.l', 'sta.l', 'stz.l', 'inc.l', 'dec.l')):
            for n in range(SPILL_BASE,SPILL_END,2):
                if f'${n:06X}' in line.upper():
                    raise RestoreSpillContractError('SCRATCH_SPILL_ALREADY_CLAIMED')
    _splice_once(a,
        [' lda.l $42D606',' cmp #32'],
        [' lda.l $42D606',f' cmp #{NEW_CAPACITY}'],
        'RECORD_COUNT_GUARD')
    # The already-audited plan obtains slot $2C from NbFree and source home
    # identity $30, then calculates four-byte record offset in X.
    store_old = [
        ' jsr NbFree',' lda.l $42D606',' asl a',' asl a',' tax',
        ' lda $30',' sta.l $003480,x',' lda $2C',' sta.l $003482,x',
    ]
    store_new = [
        ' jsr NbFree',' lda.l $42D606',' asl a',' asl a',' tax',
        f' cpx #{OLD_CAPACITY*4}', ' bcs NbRestoreStoreOverflow',
        ' lda $30',' sta.l $003480,x',' lda $2C',' sta.l $003482,x',
        ' bra NbRestoreStoreDone',
        'NbRestoreStoreOverflow:','.a16','.i16',
        ' txa',' sec', f' sbc #{OLD_CAPACITY*4}',' tax',
        ' lda $30',f' sta.l ${SPILL_BASE:06X},x',
        ' lda $2C',f' sta.l ${SPILL_BASE+2:06X},x',
        'NbRestoreStoreDone:','.a16','.i16',
    ]
    _splice_once(a,store_old,store_new,'RECORD_STORE')
    # Production reads slot into $64 and immutable backdrop home into $2C.
    # The new spill path preserves these exact live values.
    load_old = [
        ' asl a',' asl a',' tax',
        ' lda.l $003482,x',' sta $64',' lda.l $003480,x',' sta $2C',
        ' jsr WarmCopyBackdrop',
    ]
    load_new = [
        ' asl a',' asl a',' tax',
        f' cpx #{OLD_CAPACITY*4}', ' bcs NbRestoreLoadOverflow',
        ' lda.l $003482,x',' sta $64',' lda.l $003480,x',' sta $2C',
        ' bra NbRestoreLoadDone',
        'NbRestoreLoadOverflow:','.a16','.i16',
        ' txa',' sec',f' sbc #{OLD_CAPACITY*4}',' tax',
        f' lda.l ${SPILL_BASE+2:06X},x',' sta $64',
        f' lda.l ${SPILL_BASE:06X},x',' sta $2C',
        'NbRestoreLoadDone:','.a16','.i16',
        ' jsr WarmCopyBackdrop',
    ]
    _splice_once(a,load_old,load_new,'RECORD_LOAD')
    plan_section=a[a.index('NbRestorePlan:'):a.index('NbActorPlanStart:')]
    if ' cmp #32' in plan_section or a.count(' sta.l $003480,x')!=1 or a.count(' lda.l $003480,x')!=1:
        raise RestoreSpillContractError('RESTORATION_MUTATION_OUT_OF_SCOPE')
    if a.count(' jsr NbFlushQueue')!=3:
        raise RestoreSpillContractError('QUEUE_CALLS_DRIFT')
    return a


def record_address(index: int) -> int:
    if type(index) is not int or not 0<=index<NEW_CAPACITY:
        raise ValueError('RESTORE_RECORD_INDEX')
    return IRAM_BASE+index*4 if index<OLD_CAPACITY else SPILL_BASE+(index-OLD_CAPACITY)*4
