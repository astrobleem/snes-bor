"""Exactly fuse committed+pending bitmap insertion for identical backdrop cells.

Opt-in follow-on overlay for the accepted native 65816 renderer at
c028eff584f87de7ff2d67ea7a5c43701fd4e4dc.

The existing BhBitmapMapLoop builds two 596-home membership bitmaps, each
76 bytes in the empty six-pair queue. On a committed home whose RAW word
matches the pending word, both memberships can be set using one computed
bitmap word offset and mask. All unequal/tagged/non-home cases execute the
original two-map path. No owner, scratch, RAM, VRAM or DMA change.

A16/I16; CMP absolute-long-indexed opcode DF is supported on 65816. No new
JSR layer around the restoration planner or allocator is introduced.
All machine/native speed claims require actual native Mesen measurements.
"""
from __future__ import annotations
from collections.abc import Sequence
from hashlib import sha256
from home_borrow_bitmap import _emit, _routines, BITMAP_END, COMMITTED_BITS, PENDING_BITS

BASE_COMMIT = 'c028eff584f87de7ff2d67ea7a5c43701fd4e4dc'
BASE_ROM_SHA256 = 'f1f03464e47d9736ceb2af6b66067bea76960c09e9dd3880795fd1f46b6aa81e'

class SharedCellContractError(ValueError):
    pass


def _digest(lines: Sequence[str]) -> str:
    return sha256(('\n'.join(lines)+'\n').encode()).hexdigest()


def original_loop() -> list[str]:
    """Exact accepted block; source drift is fatal, not silently adapted."""
    old = _routines()
    return old[old.index('BhBitmapMapLoop:'):old.index('BhBitmapBuilt:')]


# Use only original A/X and dead DP $70/$78/$7A; preserve Y, DBR, DP, stack.
# Fast path accepts exactly matching RAW words for native backdrop homes <596.
# For an unchanged high/tagged word >=596 the old pending low-14-bit probe
# still executes; a tagged physical home can NEVER be misclassified as absent.
# We deliberately do not combine entries that are merely equal after masking.
def shared_loop() -> list[str]:
    return _emit('''
BhBitmapMapLoop:
 lda $70
 tax
 lda.l $42C800,x
 cmp #596
 bcs BhBitmapPending
 cmp.l $42C000,x
 bne BhBitmapDifferent
BhBitmapSharedHit:
 jsr BhBitmapAddress
 lda.l $003500,x
 ora $7A
 sta.l $003500,x
 lda.l $00354C,x
 ora $7A
 sta.l $00354C,x
 jmp BhBitmapNext
BhBitmapDifferent:
 jsr BhBitmapAddress
 lda.l $003500,x
 ora $7A
 sta.l $003500,x
BhBitmapPending:
 lda $70
 tax
 lda.l $42C000,x
 and #$3FFF
 cmp #596
 bcs BhBitmapNext
 jsr BhBitmapAddress
 lda.l $00354C,x
 ora $7A
 sta.l $00354C,x
BhBitmapNext:
 inc $70
 inc $70
 lda $70
 cmp #2048
 bcc BhBitmapMapLoop
''', 'BcSharedBranch')


def transform(source: Sequence[str]) -> list[str]:
    """Splice only a single pinned bitmap loop, nothing else."""
    a = list(source)
    required=('BhBitmapBuild:', 'BhBitmapMapLoop:', 'BhBitmapPending:',
              'BhBitmapNext:', 'BhBitmapBuilt:', 'BhBitmapAddress:',
              'BhBitmapCodeEnd:', 'BhEligible:', 'NbRestorePlan:',
              'RpResolveRestore:', 'BhCodeEnd:', '.org $C000')
    for name in required:
        if a.count(name)!=1:
            raise SharedCellContractError('SHARED_BITMAP_LABEL_DRIFT:'+name)
    if any(x.startswith('BcShared') or x.startswith('BhBitmapDifferent:') for x in a):
        raise SharedCellContractError('SHARED_BITMAP_ALREADY_APPLIED')
    lo=a.index('BhBitmapMapLoop:')
    hi=a.index('BhBitmapBuilt:')
    if not (a.index('BhBitmapBuild:')<lo<hi<a.index('BhBitmapAddress:')<
            a.index('BhBitmapCodeEnd:')<a.index('BhCodeEnd:')<a.index('.org $C000')):
        raise SharedCellContractError('SHARED_BITMAP_ORDER')
    if a[lo:hi]!=original_loop():
        raise SharedCellContractError('SHARED_BITMAP_PINNED_LOOP_DRIFT')
    if (BITMAP_END,COMMITTED_BITS,PENDING_BITS)!=(0x3598,0x3500,0x354c):
        raise SharedCellContractError('SHARED_BITMAP_LEASE_DRIFT')
    a[lo:hi]=shared_loop()
    if a.count('BhBitmapMapLoop:')!=1 or a.count('BhBitmapPending:')!=1:
        raise SharedCellContractError('SHARED_BITMAP_LABEL_COLLISION')
    return a


def bitmap_parts(lines: Sequence[str]) -> list[str]:
    """Extract exact contiguous builder for independent opcode-byte auditing."""
    a=list(lines)
    return a[a.index('BhBitmapBuild:'):a.index('BhBitmapCodeEnd:')+3]
