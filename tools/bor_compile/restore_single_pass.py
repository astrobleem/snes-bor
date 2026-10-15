"""Single-pass restoration remapping for the pinned native MOTU publisher.

Apply after home_borrow_bitmap.transform at 8d317e53828a. No new storage.
A16/I16, binary arithmetic, D=$3400, the existing single producer required.

The old planner immediately rescans all 1024 pending words for each newly
encountered invalid home. This overlay instead resolves the current cell from
the existing <=48 (home,destination) records, allocating only on first use.
Successful map, record order, allocation order, and tail cursor are identical.
An unsuccessful pre-DMA plan may have a differently remapped *private* prefix;
the unchanged retry/abort discards it before any composition or DMA.

Crucially, entry/exit to RpResolveRestore use JMP, not JSR. NbFree retains
exactly its original call depth, including its PLA on exhausted allocation.
"""
from __future__ import annotations
from collections.abc import Sequence
import hashlib

BASE_COMMIT = '8d317e53828a741c6d0e79a0cfd5f64cee3c4024'
BASE_ROM_SHA256 = '487be884b06db56ad3755feb5a3549b85837f0965d58459d0949ab3b0f92a52d'
MAP_BASE = 0x42C000
MAP_WORDS = 1024
HOME_COUNT = 596
SLOT_COUNT = 768
RECORD_COUNT = 0x42D606
RECORD_LIMIT = 48

class RestoreContractError(ValueError):
    pass


def asm(text: str) -> list[str]:
    """Match the retained emitter's A16/I16 label conventions exactly."""
    result: list[str] = []
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.endswith(':'):
            result.extend((line, '.a16', '.i16'))
        else:
            result.append(' ' + line)
    return result


def original_plan() -> list[str]:
    """Exact generated block: nonblank_slice + batch rescue + restore spill.

    Source references and the full literal are included in the package. This
    does NOT infer or accept a similar-looking implementation on source drift.
    """
    return asm('''
NbRestorePlan:
 lda $18
 asl a
 tax
 lda.l $42C000,x
 cmp #596
 bcs NbRestorePlanNext
 sta $30
 asl a
 tax
 lda.l $42D000,x
 and #$8000
 beq NbRestorePlanNext
 lda.l $42D606
 cmp #48
 bcc NbGuard1
 jmp NbAbort
NbGuard1:
 jsr NbFree
 lda.l $42D606
 asl a
 asl a
 tax
 cpx #128
 bcs NbRestoreStoreOverflow
 lda $30
 sta.l $003480,x
 lda $2C
 sta.l $003482,x
 bra NbRestoreStoreDone
NbRestoreStoreOverflow:
 txa
 sec
 sbc #128
 tax
 lda $30
 sta.l $42D620,x
 lda $2C
 sta.l $42D622,x
NbRestoreStoreDone:
 lda.l $42D606
 inc a
 sta.l $42D606
 lda #0
 sta $70
NbReroute:
 ldx $70
 lda.l $42C000,x
 cmp $30
 bne NbRerouteNext
 lda $2C
 ora #$4000
 sta.l $42C000,x
NbRerouteNext:
 inc $70
 inc $70
 lda $70
 cmp #2048
 bcc NbReroute
NbRestorePlanNext:
 inc $18
 lda $18
 cmp #1024
 bcs NbActorPlanStart
 jmp NbRestorePlan
''')


def main_loop() -> list[str]:
    # Unchanged filters and loop cadence for cells not needing restoration.
    # Labels around reads/writes allow read-only native operation counting.
    return asm('''
NbRestorePlan:
 lda $18
 asl a
 tax
 lda.l $42C000,x
RpCellLoaded:
 cmp #596
 bcs NbRestorePlanNext
 sta $30
 asl a
 tax
 lda.l $42D000,x
 and #$8000
 beq NbRestorePlanNext
 jmp RpResolveRestore
NbReroute:
 lda $18
 asl a
 tax
 lda $2C
 ora #$4000
RpMapWrite:
 sta.l $42C000,x
NbRerouteNext:
NbRestorePlanNext:
 inc $18
 lda $18
 cmp #1024
 bcs NbActorPlanStart
 jmp NbRestorePlan
''')


def resolver() -> list[str]:
    lookup = asm('''
RpResolveRestore:
 lda #0
 sta $70
RpRecordProbe:
 lda $70
 cmp.l $42D606
 bcc RpRecordExists
 jmp RpNewRecord
RpRecordExists:
 asl a
 asl a
 tax
 cpx #128
 bcs RpProbeSpill
RpReadIramHome:
 lda.l $003480,x
 cmp $30
 bne RpProbeNext
 lda.l $003482,x
 sta $2C
 jmp NbReroute
RpProbeSpill:
 txa
 sec
 sbc #128
 tax
RpReadSpillHome:
 lda.l $42D620,x
 cmp $30
 bne RpProbeNext
 lda.l $42D622,x
 sta $2C
 jmp NbReroute
RpProbeNext:
 inc $70
 jmp RpRecordProbe
RpNewRecord:
''')
    # Reuse the original cap guard, allocation call, and split record append
    # literally, including guard/store labels. Only their placement changes.
    old = original_plan()
    start = old.index(' lda.l $42D606')
    stop = old.index(' lda #0', old.index('NbRestoreStoreDone:'))
    return lookup + old[start:stop] + [' jmp NbReroute', 'RpCodeEnd:', '.a16', '.i16']


def transform(source: Sequence[str]) -> list[str]:
    a = list(source)
    required = ('NbBeginRetry:', 'NbRestorePlanStart:', 'NbRestorePlan:',
                'NbActorPlanStart:', 'NbCodeEnd:', 'BhBitmapBuilt:',
                'BhCodeEnd:', 'SpLatched:', '.org $C000')
    for label in required:
        if a.count(label) != 1:
            raise RestoreContractError('RESTORE_SINGLE_LABEL_DRIFT:' + label)
    if any(s.startswith('Rp') for s in a):
        raise RestoreContractError('RESTORE_SINGLE_ALREADY_INSTALLED')
    start = a.index('NbRestorePlan:')
    stop = a.index('NbActorPlanStart:')
    if a[start:stop] != original_plan():
        raise RestoreContractError('RESTORE_SINGLE_PINNED_PLAN_DRIFT')
    if not (a.index('NbBeginRetry:') < a.index('NbRestorePlanStart:') < start < stop
            < a.index('NbCodeEnd:') < a.index('BhBitmapBuilt:') < a.index('.org $C000')):
        raise RestoreContractError('RESTORE_SINGLE_LIFETIME_ORDER')
    retry = a[a.index('NbBeginRetry:'):a.index('NbRestorePlanStart:')]
    marker = ' sta.l $42D606'
    if retry.count(marker) != 1 or retry[retry.index(marker)-1] != ' lda #0':
        raise RestoreContractError('RESTORE_SINGLE_RECORD_RESET_DRIFT')
    a[start:stop] = main_loop()
    end = a.index('NbCodeEnd:')
    a[end:end] = resolver()
    # No new JSR layer around NbFree: this is part of the failure-unwind ABI.
    if ' jsr RpResolveRestore' in a or a.count('RpResolveRestore:') != 1:
        raise RestoreContractError('RESTORE_SINGLE_STACK_ABI')
    return a


def record_address(index: int) -> int:
    if type(index) is not int or not 0 <= index < RECORD_LIMIT:
        raise ValueError('Restoration record index out of range')
    return 0x003480 + index*4 if index < 32 else 0x42D620 + (index-32)*4


def reference(pending: Sequence[int], refs: Sequence[int], cursor: int = HOME_COUNT) -> dict:
    """Independent eager-remap oracle matching the OLD successful planner.

    Returns the old planner's partial map on failure; callers must not require
    a streaming planner's private intermediate map to match that partial map.
    Committed state, reservation order and failure cause do remain comparable.
    """
    if len(pending) != MAP_WORDS or len(refs) != SLOT_COUNT:
        raise ValueError('Restoration reference dimensions')
    if not HOME_COUNT <= cursor <= SLOT_COUNT:
        raise ValueError('Tail cursor out of range')
    if any(type(w) is not int or not 0 <= w <= 65535 for w in (*pending, *refs)):
        raise ValueError('Expected unsigned 16-bit words')
    result = list(pending)
    records: list[tuple[int, int]] = []
    failure = None
    index = MAP_WORDS
    for index in range(MAP_WORDS):
        home = result[index]
        if home >= HOME_COUNT or not refs[home] & 0x8000:
            continue
        if len(records) == RECORD_LIMIT:
            failure = 'record_limit'
            break
        while cursor < SLOT_COUNT and refs[cursor] & 0x3fff:
            cursor += 1
        if cursor == SLOT_COUNT:
            failure = 'tail_exhausted'
            break
        destination = cursor
        cursor += 1
        records.append((home, destination))
        result = [destination | 0x4000 if w == home else w for w in result]
    if failure is None:
        index = MAP_WORDS
    return dict(success=failure is None, failure=failure, records=records,
                pending=result, cursor=cursor, stopped_cell=index)


def plan_digest() -> str:
    return hashlib.sha256(('\n'.join(original_plan())+'\n').encode()).hexdigest()
