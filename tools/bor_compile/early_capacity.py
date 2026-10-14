"""Fail-closed native early capacity choice for BYOR MOTU's bounded nonblank producer.

Offline assembly candidate for snes-bor feat/byor-motu at 4b6433c972ef.
Install AFTER restore_spill.transform and its source-owned native fault hooks.

Before NbRestorePlan writes any records, I-RAM $003480..$0034FF contains ZERO
live restoration records (RESTORES was reset by NbBeginRetry). Borrow only
$003480..$0034CB, 38 words = 608 bits, as a transient visited-home bitmap.
It is overwritten by actual records after admission, never DMA'd and never
used as a new persistent resource. The existing six-pair queue starts at $3500.

Predictor counts EXACTLY the current conservative allocation demand:
  marked actor cells ($FFFF in 1024-word pending map)
+ distinct invalid immutable backdrop homes still present in that map
versus currently unreferenced tail slots 596..767. It also checks the 48-entry
record cap. This chooses the existing exact-foreground pass early when the
conservative pass would exhaust NbFree or overflow restorations. It never
substitutes its prediction for the authoritative planner, native DMA fences,
VRAM ownership, READY checks, or independent pixel verification.
"""
from __future__ import annotations
from collections.abc import Sequence

RESTORE_BASE=0x003480
BITSET_WORDS=38
BITSET_BYTES=BITSET_WORDS*2
RESTORE_BUFFER_END=0x003500
META_RETRY=0x42D674
REF_BASE=0x42D000
MAP_BASE=0x42C000
FIRST_TAIL_SLOT=596
SLOT_CAPACITY=768
RESTORE_RECORD_CAPACITY=48

class EarlyCapacityContractError(ValueError):
    pass


def _predictor() -> list[str]:
    """Emitter uses only Poppy-supported existing 65816 instructions/format.

    DP $18 = map-cell index; $70 free count; $72 actor count;
    $74 distinct invalid-home count; $76 candidate home id;
    $78 home bit mask. X/Y are intra-transaction scratch.
    On RTS: C=1 means conservative planner definitely cannot fit.
    """
    return [
        'NbCapacityPredict:', '.a16', '.i16',
        # Bitmap is temporary workspace in restoration storage, BEFORE first
        # record exists. 596 homes require ceil(596/16)=38 words.
        ' lda #0', ' ldx #0',
        'NbCapacityClear:', '.a16', '.i16',
        ' sta.l $003480,x', ' inx', ' inx', f' cpx #{BITSET_BYTES}',
        ' bcc NbCapacityClear',
        ' sta $70', ' sta $72', ' sta $74', ' sta $18',
        'NbCapacityMapLoop:', '.a16', '.i16',
        ' lda $18', ' asl a', ' tax',
        ' lda.l $42C000,x', ' cmp #$FFFF',
        ' bne NbCapacityNotActor', ' jmp NbCapacityActor',
        'NbCapacityNotActor:', '.a16', '.i16',
        f' cmp #{FIRST_TAIL_SLOT}', ' bcc NbCapacityHomeCandidate',
        ' jmp NbCapacityNext',
        'NbCapacityHomeCandidate:', '.a16', '.i16',
        ' sta $76', ' asl a', ' tax',
        ' lda.l $42D000,x', ' and #$8000',
        ' bne NbCapacityOverwritten', ' jmp NbCapacityNext',
        'NbCapacityOverwritten:', '.a16', '.i16',
        # Find word containing home bit. Need no address-derived table or extra
        # metadata: upper home bits select bitmap word; low 4 select mask.
        ' lda #1', ' sta $78', ' lda $76', ' and #15', ' tay',
        ' beq NbCapacityMaskReady',
        'NbCapacityMaskShift:', '.a16', '.i16',
        ' asl $78', ' dey', ' bne NbCapacityMaskShift',
        'NbCapacityMaskReady:', '.a16', '.i16',
        ' lda $76', ' lsr a', ' lsr a', ' lsr a', ' and #$FFFE', ' tax',
        ' lda.l $003480,x', ' and $78',
        ' beq NbCapacityNewHome', ' jmp NbCapacityNext',
        'NbCapacityNewHome:', '.a16', '.i16',
        ' lda.l $003480,x', ' ora $78', ' sta.l $003480,x',
        ' inc $74', ' jmp NbCapacityNext',
        'NbCapacityActor:', '.a16', '.i16', ' inc $72',
        'NbCapacityNext:', '.a16', '.i16',
        ' inc $18', ' lda $18', ' cmp #1024',
        ' bcs NbCapacityCountFree', ' jmp NbCapacityMapLoop',
        'NbCapacityCountFree:', '.a16', '.i16',
        f' ldx #{FIRST_TAIL_SLOT*2}',
        'NbCapacityFreeLoop:', '.a16', '.i16',
        ' lda.l $42D000,x', ' and #$3FFF',
        ' bne NbCapacityFreeNext', ' inc $70',
        'NbCapacityFreeNext:', '.a16', '.i16',
        ' inx', ' inx', f' cpx #{SLOT_CAPACITY*2}',
        ' bcc NbCapacityFreeLoop',
        ' lda $74', f' cmp #{RESTORE_RECORD_CAPACITY+1}',
        ' bcs NbCapacityNotFit',
        ' lda $72', ' clc', ' adc $74', ' cmp $70',
        ' bcc NbCapacityFit', ' beq NbCapacityFit',
        'NbCapacityNotFit:', '.a16', '.i16', ' sec', ' rts',
        'NbCapacityFit:', '.a16', '.i16', ' clc', ' rts',
    ]


def legacy_transform(source:Sequence[str]) -> list[str]:
    """Only two source splices. No fixture flags, source authority, or ROM writes.

    The predictor is appended before NbCodeEnd (after NbQueueDirectPair's RTS).
    Target Poppy must audit code <39:C000 and all 8-bit branch displacements.
    Default/no-flag branch must be byte-identical to the prior certified ROM.
    """
    a=list(source)
    required=['NbBeginRetry:', 'NbRestorePlanStart:', 'NbRestorePlan:',
              'NbRestoreProduce:', 'NbActorPlanStart:', 'NbCodeEnd:',
              'NbQueueDirectPair:', '.org $C000']
    for label in required:
        if a.count(label)!=1:raise EarlyCapacityContractError('EARLY_LABEL_DRIFT:'+label)
    if not (a.index('NbBeginRetry:')<a.index('NbRestorePlanStart:')<
            a.index('NbRestorePlan:')<a.index('NbActorPlanStart:')<
            a.index('NbRestoreProduce:')<a.index('NbQueueDirectPair:')<
            a.index('NbCodeEnd:')<a.index('.org $C000')):
        raise EarlyCapacityContractError('EARLY_ORDER_DRIFT')
    if 'NbCapacityPredict:' in a or 'NbCapacityPredictSkip:' in a:
        raise EarlyCapacityContractError('EARLY_ALREADY_INSTALLED')
    pattern=['NbRestorePlanStart:', '.a16', '.i16',
             ' lda #0',' sta $18','NbRestorePlan:']
    occurrences=[i for i in range(len(a)-len(pattern)+1) if a[i:i+len(pattern)]==pattern]
    if len(occurrences)!=1:raise EarlyCapacityContractError('EARLY_PREDICT_ANCHOR:'+str(len(occurrences)))
    assert BITSET_BYTES<=128 and BITSET_BYTES%2==0
    # Verify source still resets record count before the mark, so our temporary
    # bitset is guaranteed dead while the predictor runs. The queue is separate.
    marker=' sta.l $42D606'
    retry_block=a[a.index('NbBeginRetry:'):a.index('NbRestorePlanStart:')]
    if retry_block.count(marker)!=1 or retry_block[retry_block.index(marker)-1]!=' lda #0':
        raise EarlyCapacityContractError('EARLY_RECORD_LIFETIME_DRIFT')
    at=occurrences[0]
    a[at:at+len(pattern)]=[
        'NbRestorePlanStart:', '.a16', '.i16',
        f' lda.l ${META_RETRY:06X}', ' bne NbCapacityPredictSkip',
        ' jsr NbCapacityPredict', ' bcc NbCapacityPredictSkip',
        'NbCapacityPredictedRetry:', '.a16', '.i16',
        ' lda #1',f' sta.l ${META_RETRY:06X}', ' jmp NbBeginRetry',
        'NbCapacityPredictSkip:', '.a16', '.i16',
        ' lda #0', ' sta $18', 'NbRestorePlan:',
    ]
    # The preceding routine already ends with RTS. No new addressable lease:
    # append to end of existing A000 transaction code, before NbCodeEnd.
    i=a.index('NbCodeEnd:');a[i:i]=_predictor()
    if a.count('NbCapacityPredict:')!=1 or a.count('NbCapacityPredictSkip:')!=1:
        raise EarlyCapacityContractError('EARLY_DUPLICATE_ROUTINE')
    return a



def _pressure_gate() -> list[str]:
    """C=0: skip prediction after 129 free words; C=1: run prediction.
    A/X and existing transient DP $70 are clobbered. No record/bitmap writes.
    """
    return ['NbCapacityPressureGate:','.a16','.i16',
        ' lda #0',' sta $70',f' ldx #{FIRST_TAIL_SLOT*2}',
        'NbCapacityPressureLoop:','.a16','.i16',
        ' lda.l $42D000,x',' and #$3FFF',' bne NbCapacityPressureNext',
        ' inc $70',' lda $70',' cmp #129',' bcs NbCapacityPressureSkip',
        'NbCapacityPressureNext:','.a16','.i16',
        ' inx',' inx',f' cpx #{SLOT_CAPACITY*2}',' bcc NbCapacityPressureLoop',
        'NbCapacityPressureRun:','.a16','.i16',' sec',' rts',
        'NbCapacityPressureSkip:','.a16','.i16',' clc',' rts']


def transform(source:Sequence[str]) -> list[str]:
    """Retain the exact predictor/planner and gate only conservative prediction.
    Threshold 129 is a workload heuristic, never allocator admission authority.
    The original bounds/record guards and exact fallback remain mandatory.
    """
    a=legacy_transform(source)
    old=[' jsr NbCapacityPredict',' bcc NbCapacityPredictSkip']
    positions=[i for i in range(len(a)-len(old)+1) if a[i:i+len(old)]==old]
    if len(positions)!=1:raise EarlyCapacityContractError('PRESSURE_DISPATCH_DRIFT')
    at=positions[0];a[at:at+len(old)]=[
        ' jsr NbCapacityPressureGate','NbCapacityPressureReturned:','.a16','.i16',
        ' bcc NbCapacityPredictSkip',' jsr NbCapacityPredict',
        'NbCapacityPredictionReturned:','.a16','.i16',' bcc NbCapacityPredictSkip']
    at=a.index('NbCodeEnd:');a[at:at]=_pressure_gate()
    return a

def reference(pending_map,refs):
    """Independent exact conservative-plan footprint (for tests & host oracle).
    Inputs: 1024 pending-map words, 768 reference/flag words. No allocation.
    """
    if len(pending_map)!=1024 or len(refs)!=SLOT_CAPACITY:
        raise ValueError('EARLY_REFERENCE_DOMAIN')
    actors=sum(w==0xFFFF for w in pending_map)
    homes={w for w in pending_map if 0<=w<FIRST_TAIL_SLOT and refs[w]&0x8000}
    free=sum((refs[s]&0x3fff)==0 for s in range(FIRST_TAIL_SLOT,SLOT_CAPACITY))
    return dict(actor=actors,restoration_homes=len(homes),free_tail=free,
                conservative_fits=(actors+len(homes)<=free and len(homes)<=RESTORE_RECORD_CAPACITY))
