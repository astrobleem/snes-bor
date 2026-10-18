"""Opt-in eighth zero-copy DMA pair appended to the accepted seven-pair queue.

Overlay the exact Q7 publisher at commit d9674ecc5a2785b31f0aefdb4f788d8649f13e66.

First seven pairs remain staged byte-identically in owned I-RAM. When the
completed restoration count <=12 and native fault mode !=2, the final eighth
pair remains in the existing 80-byte, already-composed BW-RAM scratch
$42D680..$42D6CF. Queue submission immediately flushes eight pairs; no new
composition may overwrite the eighth pair before WarmDirectPair's pair DMA.

The eighth physical slot descriptor takes the former limit word $42D670;
limit moves to previously unclaimed $42D676. The exact-retry marker at D674
and all other queue, journal and backdrop record leases remain unchanged.

The sixth/partial-fault mode remains on six pairs. No new I-RAM, BW-RAM, VRAM,
source data or permanent state. Native ROM and PPU certification is required.
"""
from __future__ import annotations
from collections.abc import Sequence

BASE_COMMIT='d9674ecc5a2785b31f0aefdb4f788d8649f13e66'
BASE_ROM_SHA256='c2b429e86171f68cdab639511da61fb5d1679d34fc6c2b9ae6cc23f41e7d2604'
SCRATCH_HIGH=0x42D680
SCRATCH_LOW=0x42D6C0
SCRATCH_END=0x42D6D0
SLOT8_WORD=0x42D670
NEW_LIMIT_WORD=0x42D676
EXACT_RETRY=0x42D674
MAX_EXTENDED_RECORDS=12


class EightPairContractError(ValueError):
    pass


def queue_capacity(record_count: int, fault_mode: int=0) -> int:
    """Pinned dynamic policy: 8 or unchanged diagnostic/safety fallback 6."""
    if type(record_count) is not int or not 0<=record_count<=48:
        raise ValueError('Q8_RECORD_DOMAIN')
    if type(fault_mode) is not int or not 0<=fault_mode<=65535:
        raise ValueError('Q8_FAULT_MODE_DOMAIN')
    return 6 if record_count>12 or fault_mode==2 else 8


def staging_source(index: int,record_count: int,fault_mode: int=0) -> int|None:
    """No copy for index 7: producer's existing scratch is its DMA source."""
    cap=queue_capacity(record_count,fault_mode)
    if type(index) is not int or not 0<=index<cap:
        raise ValueError('Q8_QUEUE_INDEX_DOMAIN')
    if index==7:return None
    return 0x34B0 if index==6 else 0x3500+80*index


def output_sources(index: int,record_count: int,fault_mode: int=0) -> tuple[int,int]:
    source=staging_source(index,record_count,fault_mode)
    return (SCRATCH_HIGH,SCRATCH_LOW) if source is None else (source,source+64)


def batch_sizes(pairs: int,records: int,fault_mode: int=0)->list[int]:
    if type(pairs) is not int or pairs<0:raise ValueError('Q8_PAIR_COUNT_DOMAIN')
    cap=queue_capacity(records,fault_mode)
    return [min(cap,pairs-at) for at in range(0,pairs,cap)]


def _splice_once(lines:list[str],old:list[str],new:list[str],lo:int,hi:int,tag:str)->None:
    hits=[i for i in range(lo,hi-len(old)+1) if lines[i:i+len(old)]==old]
    if len(hits)!=1:raise EightPairContractError(tag+': '+str(len(hits))+' exact anchors')
    i=hits[0];lines[i:i+len(old)]=new


def _source_live_area(a:list[str]) -> tuple[int,int]:
    return a.index('NbPreloadPair:'),a.index('NbCodeEnd:')


def transform(source:Sequence[str])->list[str]:
    """Fail closed unless the exact Q7 producer, policy and scratch ABI match."""
    a=list(source)
    required=('Q7PolicyBegin:','Q7PolicyDone:','Q7SourceFromIndex:',
              'Q7SpillSource:','NbPreloadPair:','NbQueueSpace:',
              'NbQueueNotFull:','NbFlushQueue:','NbQueueDrain:',
              'NbPairBegin:','NbPairComplete:','NbQueueDirectPair:',
              'NbCodeEnd:','WarmDirectPair:','OnlineDmaDone8:',
              'OnlineDmaDone9:', 'OnlineDmaDone10:', 'OnlineDmaDone11:')
    for label in required:
        if a.count(label)!=1:raise EightPairContractError('Q8_PINNED_LABEL:'+label)
    if any(x.startswith('Q8') for x in a):
        raise EightPairContractError('Q8_ALREADY_INSTALLED')
    if not (a.index('Q7PolicyBegin:')<a.index('NbPreloadPair:')<
            a.index('NbQueueSpace:')<a.index('NbQueueDrain:')<
            a.index('NbPairBegin:')<a.index('NbQueueDirectPair:')<
            a.index('Q7SourceFromIndex:')<a.index('NbCodeEnd:')<
            a.index('WarmDirectPair:')):
        raise EightPairContractError('Q8_PINNED_ROUTINE_ORDER')
    if not (SLOT8_WORD+2<=0x42D672<=EXACT_RETRY and
            NEW_LIMIT_WORD>EXACT_RETRY+1 and SCRATCH_END-SCRATCH_HIGH==80):
        raise EightPairContractError('Q8_UNSAFE_METADATA_OR_SCRATCH_LEASE')
    if any('$42D676' in x.upper() for x in a):
        raise EightPairContractError('Q8_LIMIT_ALREADY_OWNED')
    # Exact Q7 policy: no actor, epoch, or source-image conditional introduced.
    original=[
      'Q7PolicyBegin:','.a16','.i16',' lda #6',' sta.l $42D670',
      ' lda.l $42D606',' cmp #13',' bcs Q7PolicyDone',
      ' lda.l $42D602',' cmp #2',' beq Q7PolicyDone',
      ' lda #7',' sta.l $42D670','Q7PolicyDone:'
    ]
    replacement=[
      'Q7PolicyBegin:','.a16','.i16',' lda #6',' sta.l $42D676',
      ' lda.l $42D606',' cmp #13',' bcs Q7PolicyDone',
      ' lda.l $42D602',' cmp #2',' beq Q7PolicyDone',
      ' lda #8',' sta.l $42D676','Q7PolicyDone:'
    ]
    _splice_once(a,original,replacement,0,a.index('NbPreloadPair:'),'Q8_POLICY')
    lo,hi=_source_live_area(a)
    # Other two Q7 limit references, in the admission and full-queue checks.
    for old,new in (
      (' cmp.l $42D670',' cmp.l $42D676'),
    ):
        matches=[i for i in range(lo,hi) if a[i]==old]
        if len(matches)!=2:raise EightPairContractError('Q8_QUEUE_LIMIT_COMPARISON:'+str(len(matches)))
        for i in matches:a[i]=new
    # One eighth *slot identity* is kept at D670 (the +14 byte element of
    # existing queue array D662), but the eighth scratch DATA is NOT staged.
    # Find the exact original scratch-to-I-RAM pair MVNs and only skip those.
    lo,hi=_source_live_area(a)
    start_candidates=[i for i in range(lo,hi-3) if a[i:i+3]==[
        ' lda.l $42D660',' sta $70',' jsr Q7SourceFromIndex']]
    if len(start_candidates)!=1:raise EightPairContractError('Q8_STAGE_SOURCE_ANCHOR')
    st=start_candidates[0]+2
    # The next increment of QUEUE_COUNT occurs immediately after both copies.
    end_candidates=[i for i in range(st+1,hi) if a[i]==' lda.l $42D660']
    if not end_candidates:raise EightPairContractError('Q8_STAGE_COUNT_ANCHOR')
    en=end_candidates[0]
    staged=a[st:en]
    if not (staged[0]==' jsr Q7SourceFromIndex' and
            staged.count(' mvn $00,$42')==2 and staged[-1]==' plb' and
            ' ldx #$D680' in staged and ' ldx #$D6C0' in staged and
            ' lda #63' in staged and ' lda #15' in staged):
        raise EightPairContractError('Q8_STAGE_MVN_DRIFT')
    # Avoid an unknown short branch distance: inverse BNE over an absolute JMP.
    a[st:en]=[
       ' lda $70',' cmp #7',' bne Q8StageCopy',' jmp Q8ScratchNoStage',
       'Q8StageCopy:','.a16','.i16',*staged,
       'Q8ScratchNoStage:','.a16','.i16',
    ]
    # Proof that index seven cannot survive into the NEXT compositor call:
    # incrementing to eight must immediately synchronously flush the queue.
    lo,hi=_source_live_area(a)
    full=[' lda.l $42D660',' inc a',' sta.l $42D660',
          ' cmp.l $42D676',' bne NbQueueNotFull',
          ' jsr NbFlushQueue','NbQueueNotFull:']
    if sum(a[i:i+len(full)]==full for i in range(lo,hi-len(full)+1))!=1:
        raise EightPairContractError('Q8_IMMEDIATE_FULL_QUEUE_FLUSH_NOT_PROVEN')
    entry=[' lda.l $42D660',' cmp.l $42D676',
           ' bcc NbQueueSpace',' jsr NbFlushQueue','NbQueueSpace:']
    if sum(a[i:i+len(entry)]==entry for i in range(lo,hi-len(entry)+1))!=1:
        raise EightPairContractError('Q8_QUEUE_OVERFLOW_PRECHECK_CHANGED')
    # At drain, slot #7 uses original vetted bank-42 scratch-to-VRAM DMA.
    # The other seven retain the same bank-00 staged NbQueueDirectPair.
    lo,hi=_source_live_area(a)
    old=[' jsr Q7SourceFromIndex','NbPairBegin:','.a16','.i16',
         ' jsr NbQueueDirectPair','NbPairComplete:']
    new=['NbPairBegin:','.a16','.i16',
         ' lda $70',' cmp #7',' bne Q8StagedPair',
         'Q8DirectScratch:','.a16','.i16',
         ' jsr WarmDirectPair',
         'Q8DirectComplete:','.a16','.i16',
         ' jmp NbPairComplete',
         'Q8StagedPair:','.a16','.i16',
         ' jsr Q7SourceFromIndex',' jsr NbQueueDirectPair',
         'NbPairComplete:']
    _splice_once(a,old,new,lo,hi,'Q8_DRAIN_DISPATCH')
    # Dynamic cap 8 must be selected ONLY with at most 12 live records.
    # Original six-pair fault-mode fallback, Q7 source helper, all DMA
    # descriptor bodies and source-world routines are unmodified.
    if a.count('Q8ScratchNoStage:')!=1 or a.count('Q8DirectScratch:')!=1:
        raise EightPairContractError('Q8_CONTROL_FLOW_COLLISION')
    assert queue_capacity(12)==8 and queue_capacity(13)==6 and queue_capacity(0,2)==6
    return a
