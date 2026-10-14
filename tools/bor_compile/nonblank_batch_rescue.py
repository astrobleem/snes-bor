"""Opt-in assembly splice for native BYOR MOTU nonblank slice (01c8167).

OFFLINE CANDIDATE. The emitted source must be assembled and verified in Mesen.
It batches six 80-byte HIGH/LOW tile pairs in audited shared SA-1 I-RAM,
extends the restoration record list to 32, and retries a failed conservative
plan using the existing precise foreground-aware OnlineCoverage predicate.

The queue uses I-RAM $00:3500..$00:36DF (480 bytes), while restoration records
use $00:3480..$00:34FF (128 bytes). Nothing touches $3700 CC-DMA space or
$3780..$37FF SA-1 stack. Both require explicit native ownership certification.
"""
from __future__ import annotations
from collections.abc import Sequence

RESTORE_BASE = 0x003480
RESTORE_CAPACITY = 32
QUEUE_BASE = 0x003500
QUEUE_COUNT = 0x42D660
QUEUE_SLOTS = 0x42D662
EXACT_RETRY = 0x42D674
QUEUE_CAPACITY = 6
QUEUE_END = QUEUE_BASE + 80*QUEUE_CAPACITY  # exclusive 0x36E0
IRAM_LEASE = (0x3480, 0x36E0)
TXN_MAP = 0x42C000
PAIR_READY = 0x42D60A
PAIRS = 0x42D608

class BatchContractError(ValueError):
    pass


def _once(a: list[str], target: str) -> int:
    if a.count(target) != 1:
        raise BatchContractError('BATCH_SOURCE_ANCHOR:'+repr(target)+':'+str(a.count(target)))
    return a.index(target)


def _splice(a: list[str], old: list[str], new: list[str]) -> None:
    starts = [i for i in range(len(a)-len(old)+1) if a[i:i+len(old)]==old]
    if len(starts) != 1:
        raise BatchContractError('BATCH_SOURCE_PATTERN:'+repr(old)+':'+str(len(starts)))
    at = starts[0]
    a[at:at+len(old)] = new


def _a16():
    return ['.a16', '.i16']


def _set_8(reg: int, value: int) -> list[str]:
    return [f' lda #${value:02X}',f' sta.l ${reg:06X}']


def _source_addr_from_index() -> list[str]:
    # Calculate QUEUE_BASE + 80*n, using 80=64+16. n<=5.
    return [' lda $70',' asl a',' asl a',' asl a',' asl a',' sta $74',
            ' asl a',' asl a',' clc',' adc $74',
            ' clc',f' adc #${QUEUE_BASE & 0xffff:04X}',' sta $72']


def _dma_descriptor(source_offset: int, size: int, vram_low: bool, marker: str) -> list[str]:
    assert size in (16,64)
    v=[]
    if not vram_low:
        v+=[' lda $2C',*([' asl a']*5),' sta.l $002116']
    else:
        v+=[' lda $2C',*([' asl a']*3),' clc',' adc #$6000',' sta.l $002116']
    v+=[' lda $72']
    if source_offset:v+=[' clc',f' adc #{source_offset}']
    v+=[' sta.l $004372',f' lda #{size}',' sta.l $004375',' sep #$20','.a8']
    for reg,value in ((0x4370,1),(0x4371,0x18),(0x4374,0),(0x420b,0x80)):
        v+=_set_8(reg,value)
    v += [marker+':',' rep #$20','.a16']
    return v


def _new_preloader() -> list[str]:
    code=['NbPreloadPair:',*_a16(),
          # Preserve caller's current physical slot and registers. Actor caller
          # requires $2C after return to publish MAP[$18].
          ' phx',' phy',' lda $2C',' pha',
          ' lda #0',f' sta.l ${PAIR_READY:06X}',
          f' lda.l ${QUEUE_COUNT:06X}',f' cmp #{QUEUE_CAPACITY}',
          ' bcc NbQueueSpace',' jsr NbFlushQueue','NbQueueSpace:',*_a16(),
          f' lda.l ${QUEUE_COUNT:06X}',' asl a',' tax',' lda $2C',
          f' sta.l ${QUEUE_SLOTS:06X},x',
          f' lda.l ${QUEUE_COUNT:06X}',' sta $70',*_source_addr_from_index(),
          ' phb',' lda #63',' ldx #$D680',' ldy $72',
          ' mvn $00,$42',' plb',
          ' phb',' lda #15',' ldx #$D6C0',' lda $72',' clc',' adc #64',' tay',
          ' lda #15', ' mvn $00,$42',' plb',
          f' lda.l ${QUEUE_COUNT:06X}',' inc a',f' sta.l ${QUEUE_COUNT:06X}',
          f' cmp #{QUEUE_CAPACITY}',' bne NbQueueNotFull',
          ' jsr NbFlushQueue','NbQueueNotFull:',*_a16(),
          ' pla',' sta $2C',' ply',' plx',' rts',
          'NbFlushQueue:',*_a16(),
          f' lda.l ${QUEUE_COUNT:06X}',' bne NbQueueHasPending',' rts',
          'NbQueueHasPending:',*_a16(),' phx',' phy',' lda $2C',' pha',
          # IMPORTANT: one fresh VBlank for the entire *six-pair* batch.
          ' jsr NbFreshVblank',' lda #0',' sta $70',
          'NbQueueDrain:',*_a16(),
          ' lda $70',' asl a',' tax',f' lda.l ${QUEUE_SLOTS:06X},x',' sta $2C',
          *_source_addr_from_index(),
          'NbPairBegin:',*_a16(),' jsr NbQueueDirectPair','NbPairComplete:',*_a16(),
          # PAIRS only advances after both CHR DMA completion fences.
          f' lda.l ${PAIRS:06X}',' inc a',f' sta.l ${PAIRS:06X}',
          ' inc $70',' lda $70',f' cmp.l ${QUEUE_COUNT:06X}',
          ' bcs NbQueueDrainDone',' jmp NbQueueDrain',
          'NbQueueDrainDone:',*_a16(),
          f' lda #0',' sta.l '+f'${QUEUE_COUNT:06X}',
          ' lda #3',f' sta.l ${PAIR_READY:06X}',
          ' pla',' sta $2C',' ply',' plx',' rts',
          'NbQueueDirectPair:',*_a16(),
          *_dma_descriptor(0,64,False,'OnlineDmaDone10'),
          *_dma_descriptor(64,16,True,'OnlineDmaDone11'),
          ' rts']
    return code


def transform(source: Sequence[str]) -> list[str]:
    """Fail-closed transformation on the EXACT generated nonblank assembly.

    Apply AFTER nonblank_slice.transform(), not before. The existing forced-
    blank/default code path is unaffected when this transform is absent.
    """
    a = list(source)
    required = ('NbBegin:','NbMarkTest:','NbRestorePlanStart:',
                'NbRestoreProduce:','NbActorPlanStart:','NbFree:',
                'NbPreloadPair:','NbCodeEnd:','NbValidate:',
                'NbAbort:','NbFreshVblank:','OnlineCoverage:','.org $C000')
    for s in required:_once(a,s)
    if not (a.index('NbBegin:') < a.index('NbMarkTest:') < a.index('NbRestorePlanStart:')
            < a.index('NbActorPlanStart:') < a.index('NbValidate:')
            < a.index('NbAbort:') < a.index('NbPreloadPair:')
            < a.index('NbCodeEnd:') < a.index('.org $C000')):
        raise BatchContractError('BATCH_PRODUCER_ORDER')
    if QUEUE_END>0x3700 or RESTORE_BASE+RESTORE_CAPACITY*4 > QUEUE_BASE:
        raise BatchContractError('BATCH_IRAM_LEASE_OVERLAP')
    # An initial attempt starts conservative. The fallback jumps directly to
    # NbBeginRetry, retaining EXACT_RETRY=1. No transaction ever writes VRAM
    # before this point; NbFree failures first discard their local JSR return.
    at = _once(a,'NbBegin:') + 3
    a[at:at]=[' lda #0',f' sta.l ${EXACT_RETRY:06X}','NbBeginRetry:',*_a16()]
    _splice(a,['NbMarkTest:',*_a16(),' jsr WarmSourcePresence'],
        ['NbMarkTest:',*_a16(),f' lda.l ${EXACT_RETRY:06X}',
         ' beq NbUseSourcePresence',' jsr OnlineCoverage',' bra NbPresenceChecked',
         'NbUseSourcePresence:',*_a16(),' jsr WarmSourcePresence',
         'NbPresenceChecked:',*_a16()])
    _splice(a,[f' lda.l $42D606',' cmp #16'],[f' lda.l $42D606',f' cmp #{RESTORE_CAPACITY}'])
    for before,after in ((0x42D620,RESTORE_BASE),(0x42D622,RESTORE_BASE+2)):
        for instr in ('sta.l','lda.l'):
            old=f' {instr} ${before:06X},x';new=f' {instr} ${after:06X},x'
            if a.count(old)!=1:raise BatchContractError('BATCH_RESTORE_RECORD_REF:'+old)
            a[a.index(old)]=new
    _splice(a,['NbFree:',*_a16(),' lda $2E',' cmp #768',
               ' bcc NbFreeCheck',' pla',' jmp NbAbort'],
        ['NbFree:',*_a16(),' lda $2E',' cmp #768',
         ' bcc NbFreeCheck',' pla',f' lda.l ${EXACT_RETRY:06X}',
         ' bne NbExactExhausted',' lda #1',f' sta.l ${EXACT_RETRY:06X}',
         ' jmp NbBeginRetry','NbExactExhausted:',*_a16(),' jmp NbAbort'])
    # All queued pairs must complete BEFORE the READY validation pass.
    _splice(a,[' lda #0',' sta $70','NbValidate:'],
        [' jsr NbFlushQueue',f' lda.l ${QUEUE_COUNT:06X}',
         ' beq NbAllPairsReady',' jmp NbAbort','NbAllPairsReady:',*_a16(),
         ' lda #0',' sta $70','NbValidate:'])
    # Failed transactions must never carry old queue counts into a retry.
    at=_once(a,'NbBeginRetry:')+3
    a[at:at]=[' lda #0',f' sta.l ${QUEUE_COUNT:06X}']
    at=_once(a,'NbAbort:')+3
    a[at:at]=[' lda #0',f' sta.l ${QUEUE_COUNT:06X}']
    old=['NbPreloadPair:',*_a16(),' lda #0',f' sta.l ${PAIR_READY:06X}',
         ' jsr NbFreshVblank','NbPairBegin:',' jsr WarmDirectPair',
         ' lda #3',f' sta.l ${PAIR_READY:06X}',
         f' lda.l ${PAIRS:06X}',' inc a',f' sta.l ${PAIRS:06X}',
         'NbPairComplete:',' rts']
    start=_once(a,'NbPreloadPair:');end=_once(a,'NbCodeEnd:')
    if a[start:end] != old:
        raise BatchContractError('BATCH_OLD_PRELOADER_DRIFT:'+repr(a[start:end]))
    a[start:end] = _new_preloader()
    assert a.count('NbPairBegin:') == a.count('NbPairComplete:') == 1
    assert a.count('OnlineDmaDone10:')==a.count('OnlineDmaDone11:')==1
    return a
