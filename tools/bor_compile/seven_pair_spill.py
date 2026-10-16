"""Opt-in, bounded 7th queued HIGH/LOW pair in unused restoration-record IRAM.

Overlay the accepted BYOR MOTU shared-cell candidate at ea9a992fb22c7fd3.
This is a staging optimization only. The 7th 80-byte pair uses $00:34B0..34FF,
provided the *completed* restoration list contains no more than 12 records.
The first twelve four-byte records occupy $00:3480..34AF, so neither live
records nor the bitmap's *expired* queue lease are overwritten. The existing
six slots retain $00:3500..36DF. The seventh slot descriptor is $42:D66E;
the dynamic limit is $42:D670. Both are before the existing $42:D674 retry flag.

Diagnostic partial-queue fault mode 2 deliberately keeps the six-slot policy,
so the 105-pair source fixture still produces a partial queue and tests its
stale/dropped-transfer behavior. The policy does not depend on epoch, actor,
position, authored scene, or the contents of a benchmark fixture.

All writing still occurs after complete admission, before READY, from the
original six-pair producer and synchronous S-CPU DMA owner. No new memory or
VRAM allocation, no graphics kernel edits, and no source-owned changes.

Native Mesen/Poppy certification is separate from this Python source overlay.
"""
from __future__ import annotations
from collections.abc import Sequence

BASE_COMMIT = 'ea9a992fb22c7fd31fc02e785cb9c10fa2ef6395'
BASE_SHA256 = '04eba01445dbae69638ba0858c18aef28d0a0172e250deeb6099585acf88dc57'
RESTORE_RECORD_BASE = 0x3480
SEVENTH_PAIR_BASE = 0x34B0
SEVENTH_PAIR_END = 0x3500
NORMAL_QUEUE_BASE = 0x3500
NORMAL_QUEUE_END = 0x36E0
RECORD_LENGTH = 4
SEVENTH_SLOT_WORD = 0x42D66E
QUEUE_LIMIT_WORD = 0x42D670
RETRY_WORD = 0x42D674
RECORD_COUNT_WORD = 0x42D606
FAULT_MODE_WORD = 0x42D602
QUEUE_COUNT_WORD = 0x42D660
EXISTING_BATCH_SIZE = 6
EXTENDED_BATCH_SIZE = 7
MAX_RECORDS_FOR_EXTENSION = 12


class SevenPairContractError(ValueError):
    pass


def queue_limit(records: int, fault_mode: int = 0) -> int:
    """Pure policy oracle; count is finalized by original restoration planner."""
    if not isinstance(records, int) or not 0 <= records <= 48:
        raise ValueError('RECORD_COUNT_DOMAIN')
    if not isinstance(fault_mode, int) or not 0 <= fault_mode <= 0xFFFF:
        raise ValueError('FAULT_MODE_DOMAIN')
    return (7 if records <= MAX_RECORDS_FOR_EXTENSION and fault_mode != 2 else 6)


def queue_address(index: int, records: int, fault_mode: int = 0) -> int:
    limit = queue_limit(records, fault_mode)
    if not isinstance(index, int) or not 0 <= index < limit:
        raise ValueError('QUEUE_INDEX_DOMAIN')
    return SEVENTH_PAIR_BASE if index == 6 else NORMAL_QUEUE_BASE + 80 * index


def batch_sizes(pair_count: int, record_count: int, fault_mode: int = 0) -> list[int]:
    if type(pair_count) is not int or pair_count < 0:
        raise ValueError('PAIR_COUNT_DOMAIN')
    cap=queue_limit(record_count, fault_mode)
    return [min(cap, pair_count - start) for start in range(0,pair_count,cap)]


def _replace(a: list[str], before: list[str], after: list[str], lo: int, hi: int, name: str) -> None:
    hits=[i for i in range(lo,hi-len(before)+1) if a[i:i+len(before)]==before]
    if len(hits)!=1:
        raise SevenPairContractError(name+': expected one exact anchor; got '+str(len(hits)))
    k=hits[0]
    a[k:k+len(before)]=after


def _source_address_instructions() -> list[str]:
    # Import the exact retained calculation so the patch cannot accidentally
    # recognize or rewrite a different queued DMA implementation.
    from nonblank_batch_rescue import _source_addr_from_index
    result=_source_addr_from_index()
    if result[:1]!=[' lda $70'] or result[-1:]!=[' sta $72'] or ' adc #$3500' not in result:
        raise SevenPairContractError('SIX_PAIR_SOURCE_ADDRESS_DRIFT')
    return result


def _policy() -> list[str]:
    return [
      'Q7PolicyBegin:', '.a16', '.i16',
      ' lda #6',f' sta.l ${QUEUE_LIMIT_WORD:06X}',
      f' lda.l ${RECORD_COUNT_WORD:06X}', ' cmp #13', ' bcs Q7PolicyDone',
      f' lda.l ${FAULT_MODE_WORD:06X}', ' cmp #2', ' beq Q7PolicyDone',
      ' lda #7',f' sta.l ${QUEUE_LIMIT_WORD:06X}',
      'Q7PolicyDone:', '.a16', '.i16',
    ]


def _source_helper() -> list[str]:
    return [
      'Q7SourceFromIndex:', '.a16', '.i16',
      ' lda $70', ' cmp #6',' bne Q7NormalSource',
      'Q7SpillSource:', '.a16', '.i16',
      ' lda #$34B0',' sta $72',' rts',
      'Q7NormalSource:', '.a16','.i16',
      *_source_address_instructions(), ' rts',
      'Q7CodeEnd:', '.a16','.i16',
    ]


def transform(source:Sequence[str]) -> list[str]:
    """Apply once to the accepted full publisher assembly; fail closed on drift."""
    a=list(source)
    required=['BhActorPlanAdmitted:', 'NbActorPlan:', 'NbPreloadPair:',
              'NbQueueSpace:', 'NbQueueNotFull:', 'NbFlushQueue:',
              'NbQueueDrain:', 'NbPairBegin:', 'NbCodeEnd:',
              'NbRestoreProduce:', 'NbActorProduce:', 'BhBitmapBuilt:',
              'RpResolveRestore:', '.org $C000']
    for s in required:
        if a.count(s)!=1:raise SevenPairContractError('Q7_LABEL:'+s)
    if any(s.startswith('Q7') for s in a):
        raise SevenPairContractError('Q7_ALREADY_APPLIED')
    if not (a.index('BhActorPlanAdmitted:')<a.index('NbActorPlan:')<
            a.index('NbRestoreProduce:')<a.index('NbActorProduce:')<
            a.index('NbPreloadPair:')<a.index('NbQueueDrain:')<
            a.index('NbPairBegin:')<a.index('NbCodeEnd:')<
            a.index('.org $C000')):
        raise SevenPairContractError('Q7_CODE_ORDER')
    if not (SEVENTH_PAIR_BASE==RESTORE_RECORD_BASE+MAX_RECORDS_FOR_EXTENSION*RECORD_LENGTH
            and SEVENTH_PAIR_END-SEVENTH_PAIR_BASE==80
            and NORMAL_QUEUE_END==NORMAL_QUEUE_BASE+6*80
            and SEVENTH_SLOT_WORD==QUEUE_COUNT_WORD+2+EXISTING_BATCH_SIZE*2
            and SEVENTH_SLOT_WORD+2==QUEUE_LIMIT_WORD
            and QUEUE_LIMIT_WORD+2<RETRY_WORD):
        raise SevenPairContractError('Q7_MEMORY_LEASE')
    # Original six-pair path runs unchanged when more than twelve restoration
    # records exist or when the partial-queue diagnostic is active.
    k=a.index('BhActorPlanAdmitted:')
    if a[k+1:k+3]!=['.a16','.i16']:
        raise SevenPairContractError('Q7_POLICY_ANCHOR')
    a[k+3:k+3]=_policy()
    lo=a.index('NbPreloadPair:');hi=a.index('NbCodeEnd:')
    _replace(a,[' lda.l $42D660',' cmp #6',' bcc NbQueueSpace'],
        [' lda.l $42D660',f' cmp.l ${QUEUE_LIMIT_WORD:06X}',' bcc NbQueueSpace'],lo,hi,'Q7_STAGE_LIMIT')
    lo=a.index('NbPreloadPair:');hi=a.index('NbCodeEnd:')
    _replace(a,[' sta.l $42D660',' cmp #6',' bne NbQueueNotFull'],
        [' sta.l $42D660',f' cmp.l ${QUEUE_LIMIT_WORD:06X}',' bne NbQueueNotFull'],lo,hi,'Q7_FLUSH_LIMIT')
    address=_source_address_instructions()
    lo=a.index('NbPreloadPair:');hi=a.index('NbCodeEnd:')
    _replace(a,[' sta $70',*address,' phb',' lda #63'],
             [' sta $70',' jsr Q7SourceFromIndex',' phb',' lda #63'],lo,hi,'Q7_STAGE_SOURCE')
    lo=a.index('NbQueueDrain:');hi=a.index('NbCodeEnd:')
    _replace(a,[' sta $2C',*address,'NbPairBegin:'],
             [' sta $2C',' jsr Q7SourceFromIndex','NbPairBegin:'],lo,hi,'Q7_DRAIN_SOURCE')
    i=a.index('NbCodeEnd:')
    a[i:i]=_source_helper()
    if a.count('Q7SourceFromIndex:')!=1 or a.count('Q7PolicyDone:')!=1:
        raise SevenPairContractError('Q7_DUPLICATE')
    return a
