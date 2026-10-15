"""Replace repeated BhEligible map scans with exact transaction-local bitmaps.

Apply AFTER home_borrow.transform at snes-bor 836e8a9c8ad1. Only the
BhPrepare overflow branch and BhEligible change. No allocation policy,
source movement, compositor, invalidation, upload, or rollback changes.

Two 76-byte bitmaps temporarily occupy the EMPTY six-pair upload queue:
  $003500..$00354B: exact raw committed-map home membership
  $00354C..$003597: pending-map low-14-bit physical home membership
They are built once, after restoration remaps and before actor allocations.
They die when BhPrepare returns, before the first queue producer can run.
No persistent RAM allocation; no active record/latch/queue bytes are borrowed.

A16 / I16 / binary arithmetic, graphics DP=$3400, single producer required.
The new code uses A/X and dead DP $70/$78/$7A; Y/DBR/DP are untouched.
Restricted bytecode tests are supplied; Poppy/Mesen certification is separate.
"""
from __future__ import annotations
from collections.abc import Sequence
import hashlib

BASE_COMMIT = "836e8a9c8ad1dec108d68c29bdab6fd62bcc04cc"
BASE_ROM_SHA256 = "061c574cb37a0d8dfabe731bb1fb8685610a091ec3b7d48fdb46ed9aabf38fda"
HOME_COUNT = 596
MAP_WORDS = 1024
BITMAP_WORDS = (HOME_COUNT + 15) // 16
BITMAP_BYTES = 2 * BITMAP_WORDS
COMMITTED_BITS = 0x003500
PENDING_BITS = COMMITTED_BITS + BITMAP_BYTES
BITMAP_END = PENDING_BITS + BITMAP_BYTES
QUEUE_END = 0x0036E0
# Hash of the exact emitted BhInitialize..BhCodeEnd block, with LF terminators.
EXPECTED_HELPERS_SHA256 = "f51af9e86e80424184e41f5b0e1387aeaaca0ab07b854a90ff7fd6a40439dc14"


class BitmapContractError(ValueError):
    """An input source, lifetime, or integration contract changed."""


def _emit(text: str, prefix: str) -> list[str]:
    """Poppy-compatible branches: invert over a same-bank JMP, never guess range."""
    out: list[str] = []
    serial = 0
    inverse = {"bcc": "bcs", "bcs": "bcc", "beq": "bne", "bne": "beq"}
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.endswith(":"):
            out.extend((line, ".a16", ".i16"))
            continue
        op, _, target = line.partition(" ")
        if op in inverse:
            serial += 1
            label = f"{prefix}{serial}"
            out.extend((f" {inverse[op]} {label}", f" jmp {target}",
                        label + ":", ".a16", ".i16"))
        elif op == "bra":
            out.append(" jmp " + target)
        else:
            out.append(" " + line)
    return out


def _eligibility() -> list[str]:
    # Keep the old guard precedence. A nonzero count is ineligible even when
    # another flag is set. A zero count plus reserved bit or committed use
    # is inconsistent and returns carry set. Pending tags are masked only
    # while BUILDING the pending bitmap; committed words are never masked.
    return _emit('''
BhEligible:
 lda $76
 asl a
 tax
 lda.l $42D000,x
 and #$3FFF
 bne BhNotEligible
 lda.l $42D000,x
 and #$4000
 bne BhInconsistent
 lda $76
 jsr BhBitmapAddress
 lda.l $003500,x
 and $7A
 bne BhInconsistent
 lda.l $00354C,x
 and $7A
 bne BhNotEligible
 lda #1
 clc
 rts
BhNotEligible:
 lda #0
 clc
 rts
BhInconsistent:
 sec
 rts
''', "BhBitmapEligibleBranch")


def _routines() -> list[str]:
    # Pair/state checks establish that no queue payload is live. They execute
    # only on the slow overflow path, not on a normal or tails-sufficient call.
    text = '''
BhBitmapBuild:
 lda.l $42D600
 cmp #1
 bne BhBitmapBuildBad
 lda.l $42D660
 bne BhBitmapBuildBad
 lda.l $42D608
 bne BhBitmapBuildBad
 lda.l $42D60A
 bne BhBitmapBuildBad
 lda.l $42D70C
 bne BhBitmapBuildBad
BhBitmapLeaseBegin:
 lda #0
 ldx #0
BhBitmapClear:
 sta.l $003500,x
 inx
 inx
 cpx #152
 bcc BhBitmapClear
 lda #0
 sta $70
BhBitmapMapLoop:
 ldx #0
 lda $70
 tax
 lda.l $42C800,x
 cmp #596
 bcs BhBitmapPending
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
BhBitmapBuilt:
 clc
 rts
BhBitmapBuildBad:
 sec
 rts
BhBitmapAddress:
 sta $78
 and #15
 asl a
 tax
 lda.l BhBitmapMasks,x
 sta $7A
 lda $78
 lsr a
 lsr a
 lsr a
 and #$FFFE
 tax
 rts
BhBitmapMasks:
'''
    # 16 little-endian word masks: fixed ROM data, not a new RAM resource.
    masks = b"".join((1 << bit).to_bytes(2, "little") for bit in range(16))
    text += " .db " + ",".join(f"${value:02X}" for value in masks) + "\n"
    text += "BhBitmapCodeEnd:\n"
    # Remove a redundant X reset; all loop paths restore X from the cursor.
    text = text.replace("BhBitmapMapLoop:\n ldx #0\n", "BhBitmapMapLoop:\n")
    return _emit(text, "BhBitmapBuildBranch")


def _digest(lines: Sequence[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def transform(source: Sequence[str]) -> list[str]:
    """Fail-closed overlay on the already home-borrow-enabled publisher source."""
    a = list(source)
    required = ("BhInitialize:", "BhPrepare:", "BhClass:", "BhEligible:",
                "BhTake:", "BhPrepareOK:", "BhPrepareBad:", "BhCodeEnd:",
                ".org $B300", ".org $C000")
    for label in required:
        if a.count(label) != 1:
            raise BitmapContractError("BITMAP_LABEL_DRIFT:" + label)
    if any(s.startswith("BhBitmap") for s in a):
        raise BitmapContractError("BITMAP_ALREADY_INSTALLED")
    start, end = a.index("BhInitialize:"), a.index("BhCodeEnd:") + 3
    if not (a.index(".org $B300") < start < end <= a.index(".org $C000")):
        raise BitmapContractError("BITMAP_CODE_ORDER")
    original = a[start:end]
    if _digest(original) != EXPECTED_HELPERS_SHA256:
        raise BitmapContractError("BITMAP_PINNED_HELPERS_DRIFT")
    if not (BITMAP_BYTES == 76 and BITMAP_END == 0x3598 < QUEUE_END):
        raise BitmapContractError("BITMAP_LEASE_LAYOUT")

    # This anchor follows the actor-minus-tail overflow calculation and the
    # existing >64 rejection. Normal/conservative paths do not execute it.
    anchor = [" lda #0", " sta $7E", "BhClass:"]
    indices = [i for i in range(len(a) - len(anchor) + 1)
               if a[i:i + len(anchor)] == anchor]
    if len(indices) != 1:
        raise BitmapContractError("BITMAP_OVERFLOW_ANCHOR")
    at = indices[0]
    a[at:at] = [" jsr BhBitmapBuild", " bcc BhBitmapPrepared",
                 " jmp BhPrepareBad", "BhBitmapPrepared:", ".a16", ".i16"]
    lo, hi = a.index("BhEligible:"), a.index("BhTake:")
    a[lo:hi] = _eligibility()
    at = a.index("BhCodeEnd:")
    a[at:at] = _routines()
    return a


def membership_reference(committed: Sequence[int], pending: Sequence[int]) -> tuple[bytes, bytes]:
    """Independent host oracle. Not an allocator and never native evidence."""
    if len(committed) != MAP_WORDS or len(pending) != MAP_WORDS:
        raise ValueError("BITMAP_MAP_SIZE")
    if any(type(w) is not int or not 0 <= w <= 0xFFFF for w in (*committed, *pending)):
        raise ValueError("BITMAP_WORD_DOMAIN")
    committed_homes = {w for w in committed if w < HOME_COUNT}
    pending_homes = {w & 0x3FFF for w in pending if (w & 0x3FFF) < HOME_COUNT}
    result = []
    for homes in (committed_homes, pending_homes):
        bitmap = bytearray(BITMAP_BYTES)
        for home in homes:
            bitmap[home // 8] |= 1 << (home % 8)
        result.append(bytes(bitmap))
    return result[0], result[1]
