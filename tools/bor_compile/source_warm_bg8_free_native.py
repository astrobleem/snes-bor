"""Opt-in BG8 free-canonical-slot text overlay.

This module transforms emitted PASM only. It does not import test helpers,
launch tools, build a ROM, or modify captured evidence.
"""
from __future__ import annotations

import re

import source_warm_bg8_native as bg8

FREE_HINT_SLOT = bg8.CONTROL + 0x26
FREE_CURR_LINK = bg8.CONTROL + 0x28
FREE_RESULT = bg8.CONTROL + 0x24  # 0 miss, 1 hit, 2 malformed list


def _free_helper() -> str:
    """Return 65816 helper text; branches are relaxed independently."""
    c, refs, hashes, keys = bg8.CONTROL, bg8.REFS, bg8.HASHES, bg8.KEYS
    pm, buckets = bg8.PENDING_MAP, bg8.BUCKETS
    lines = [
        "Bg8_TryFreeBackdrop:", ".a16", ".i16",
        # Only an exact source-backed backdrop query may reclaim a resident
        # canonical slot. Bg8_BackdropKey / CopyBackdrop publish generation 0
        # and the immutable home in CONTROL+20/+22.
        f" lda #0\n sta.l ${FREE_RESULT:06X}\n lda.l ${c+0x20:06X}\n cmp #0",
        " bne Bg8_FreeBackdropMiss",
        f" lda.l ${c+0x0A:06X}\n asl a\n tax\n lda.l ${pm:06X},x\n cmp #960",
        " bcs Bg8_FreeBackdropMiss",
        f" sta.l ${FREE_HINT_SLOT:06X}\n asl a\n tax\n lda.l ${refs:06X},x\n and #1",
        " beq Bg8_FreeBackdropMiss",
        f" lda.l ${hashes:06X},x",
        " beq Bg8_FreeBackdropMiss",
        f" lda.l ${FREE_HINT_SLOT:06X}\n asl a\n asl a\n tax\n lda.l ${keys:06X},x",
        " beq Bg8_FreeBackdropMiss",
        " cmp #$FFFF",
        " beq Bg8_FreeBackdropMiss",
        f" lda.l ${keys+2:06X},x\n cmp.l ${c+0x0A:06X}",
        " bne Bg8_FreeBackdropMiss",
        # Walk the existing plus-one free list, preserving predecessor and
        # current link separately. The 961st visit or invalid link fails
        # closed through the caller's normal fault path.
        f" lda #0\n sta.l ${c+0x0C:06X}\n sta.l ${c+0x16:06X}\n lda.l ${c+0x14:06X}\n sta.l ${FREE_CURR_LINK:06X}",
        "Bg8_FreeBackdropLoop:", ".a16", ".i16",
        f" lda.l ${FREE_CURR_LINK:06X}\n beq Bg8_FreeBackdropMiss\n cmp #961",
        " bcs Bg8_FreeBackdropBad",
        f" lda.l ${c+0x16:06X}\n inc a\n sta.l ${c+0x16:06X}\n cmp #961",
        " bcs Bg8_FreeBackdropBad",
        f" lda.l ${FREE_CURR_LINK:06X}\n dec a\n sta.l ${c+0x0E:06X}\n asl a\n tax\n lda.l ${refs:06X},x\n and #3",
        " bne Bg8_FreeBackdropBad",
        f" lda.l ${refs:06X},x\n and #$FFFC\n lsr a\n lsr a\n sta.l ${FREE_RESULT:06X}\n cmp #961",
        " bcs Bg8_FreeBackdropBad",
        # A self-link at a candidate cannot be unlinked safely without leaving
        # the claimed slot as the free-list head/successor.
        f" lda.l ${c+0x0E:06X}\n inc a\n cmp.l ${FREE_RESULT:06X}",
        " bne Bg8_FreeSelfLinkOK\n jmp Bg8_FreeBackdropBad",
        "Bg8_FreeSelfLinkOK:", ".a16", ".i16",
        f" lda.l ${hashes:06X},x\n beq Bg8_FreeBackdropNext\n cmp.l ${c+0x1E:06X}\n bne Bg8_FreeBackdropNext\n lda.l ${c+0x0E:06X}\n asl a\n asl a\n tax\n lda.l ${keys:06X},x",
        " bne Bg8_FreeBackdropNext",
        f" lda.l ${keys+2:06X},x\n cmp.l ${c+0x22:06X}",
        " bne Bg8_FreeBackdropNext",
        # Candidate matches. Unlink it before replacing the packed free-list
        # link with a hash-bucket link and pending ownership.
        "Bg8_FreeBackdropCandidate:", ".a16", ".i16",
        f" lda.l ${c+0x0C:06X}\n beq Bg8_FreeBackdropHead",
        f" dec a\n asl a\n tax\n lda.l ${FREE_RESULT:06X}\n asl a\n asl a\n sta.l ${refs:06X},x\n jmp Bg8_FreeBackdropInsert",
        "Bg8_FreeBackdropHead:", ".a16", ".i16",
        f" lda.l ${FREE_RESULT:06X}\n sta.l ${c+0x14:06X}",
        "Bg8_FreeBackdropInsert:", ".a16", ".i16",
        f" lda.l ${c+0x0E:06X}\n asl a\n tax\n lda.l ${hashes:06X},x\n and #63\n asl a\n sta.l ${c+0x1A:06X}\n tax\n lda.l ${buckets:06X},x\n asl a\n asl a\n ora #2\n sta.l ${c+0x0C:06X}",
        f" lda.l ${c+0x0E:06X}\n asl a\n tax\n lda.l ${c+0x0C:06X}\n sta.l ${refs:06X},x\n lda.l ${c+0x0E:06X}\n inc a\n sta.l ${c+0x0C:06X}\n lda.l ${c+0x1A:06X}\n tax\n lda.l ${c+0x0C:06X}\n sta.l ${buckets:06X},x",
        f" lda.l ${c+0x0A:06X}\n asl a\n tax\n lda.l ${c+0x0E:06X}\n sta.l ${pm:06X},x",
        "Bg8_FreeBackdropReused:", ".a16", ".i16",
        f" lda #1\n sta.l ${FREE_RESULT:06X}\n rts",
        "Bg8_FreeBackdropNext:", ".a16", ".i16",
        f" lda.l ${FREE_CURR_LINK:06X}\n sta.l ${c+0x0C:06X}\n lda.l ${FREE_RESULT:06X}\n sta.l ${FREE_CURR_LINK:06X}\n jmp Bg8_FreeBackdropLoop",
        "Bg8_FreeBackdropBad:", ".a16", ".i16",
        f" lda #2\n sta.l ${FREE_RESULT:06X}\n rts",
        "Bg8_FreeBackdropMiss:", ".a16", ".i16",
        f" lda #0\n sta.l ${FREE_RESULT:06X}\n clc\n rts",
    ]
    # The helper is relaxed separately so generated skip labels cannot collide
    # with labels in the retained body.
    helper = bg8._relax("\n".join(lines) + "\n")
    return re.sub(r"Bg8_BranchSkip(\d+)", r"Bg8_FreeBranchSkip\1", helper)


def _invalidate_helper() -> str:
    c, hashes, keys = bg8.CONTROL, bg8.HASHES, bg8.KEYS
    lines = [
        "Bg8_InvalidateQueued:", ".a16", ".i16",
        " php\n pha\n phx\n phy",
        f" lda.l ${bg8.BATCH_COUNT:06X}\n beq Bg8_InvalidateQueuedDone\n cmp #5",
        " bcc Bg8_InvalidateQueuedCountOK",
        " lda #4",
        "Bg8_InvalidateQueuedCountOK:", ".a16", ".i16",
        f" sta.l ${c+0x16:06X}\n lda #0\n sta.l ${c+0x0C:06X}",
        "Bg8_InvalidateQueuedLoop:", ".a16", ".i16",
        f" lda.l ${c+0x0C:06X}\n cmp.l ${c+0x16:06X}\n bcs Bg8_InvalidateQueuedDone",
        f" asl a\n tax\n lda.l ${bg8.BATCH_SLOTS:06X},x\n cmp #960\n bcs Bg8_InvalidateQueuedNext",
        f" tay\n asl a\n tax\n lda #0\n sta.l ${hashes:06X},x\n tya\n asl a\n asl a\n tax\n lda #$FFFF\n sta.l ${keys:06X},x\n sta.l ${keys+2:06X},x",
        "Bg8_InvalidateQueuedNext:", ".a16", ".i16",
        f" lda.l ${c+0x0C:06X}\n inc a\n sta.l ${c+0x0C:06X}\n jmp Bg8_InvalidateQueuedLoop",
        "Bg8_InvalidateQueuedDone:", ".a16", ".i16",
        "Bg8_QueuedInvalidated:", ".a16", ".i16",
        " ply\n plx\n pla\n plp\n rts",
    ]
    helper = bg8._relax("\n".join(lines) + "\n")
    return re.sub(r"Bg8_BranchSkip(\d+)", r"Bg8_InvalidateBranchSkip\1", helper)



def apply_free_canonical_reuse(text: str) -> str:
    """Add a free-list canonical-backdrop probe after resident lookup misses."""
    if not isinstance(text, str):
        raise ValueError("BG8_FREE_REUSE_TEXT")
    find_anchor = "Bg8_FindFree:\n.a16\n.i16\n"
    if text.count(find_anchor) != 1:
        raise ValueError(f"BG8_FREE_REUSE_FIND_FREE:{text.count(find_anchor)}")
    route = (
        " jsr Bg8_TryFreeBackdrop\n"
        f" lda.l ${FREE_RESULT:06X}\n cmp #2\n bne Bg8_FreeRouteNotCorrupt\n"
        " jmp Bg8_Fault\n"
        "Bg8_FreeRouteNotCorrupt:\n.a16\n.i16\n cmp #1\n"
        " bne Bg8_FreeRouteMiss\n jmp Bg8_Hit\n"
        "Bg8_FreeRouteMiss:\n.a16\n.i16\n"
    )
    route = bg8._relax(route)
    route = re.sub(r"Bg8_BranchSkip(\d+)", r"Bg8_FreeRouteSkip\1", route)
    text = text.replace(find_anchor, find_anchor + route, 1)
    for anchor in ("Bg8_TryFreeBackdrop:", "Bg8_InvalidateQueued:",
                   "Bg8_FreeBackdropCandidate:", "Bg8_FreeBackdropReused:",
                   "Bg8_QueuedInvalidated:"):
        if anchor in text:
            raise ValueError(f"BG8_FREE_REUSE_REAPPLY:{anchor}")
    # All observer labels live directly in the helpers and add no opcodes.
    helper = _free_helper() + _invalidate_helper()
    if text.count("Bg8_CodeEnd:\n.a16\n.i16") != 1:
        raise ValueError("BG8_FREE_REUSE_CODE_END")
    text = text.replace("Bg8_CodeEnd:\n.a16\n.i16",
                        helper + "Bg8_CodeEnd:\n.a16\n.i16", 1)
    # Invalidate metadata before the existing exit clears BATCH_COUNT. This is
    # needed on deferred, fault and obsolete paths, including partial drains.
    for label in ("Bg8_Deferred", "Bg8_Fault", "Bg8_Obsolete"):
        anchor = f"{label}:\n.a16\n.i16\n lda #0\n sta.l ${bg8.BATCH_COUNT:06X}"
        if text.count(anchor) != 1:
            raise ValueError(f"BG8_FREE_REUSE_EXIT:{label}:{text.count(anchor)}")
        replacement = (f"{label}:\n.a16\n.i16\n jsr Bg8_InvalidateQueued\n"
                       f" lda #0\n sta.l ${bg8.BATCH_COUNT:06X}")
        text = text.replace(anchor, replacement, 1)
    return text
