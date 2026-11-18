"""Opt-in BG1 8bpp copy-on-write publisher for the warm renderer.

This emitter consumes the already relocated warm-publisher text.  It keeps the
checked OnlinePublish front end, row decoder/mask, and AstraOpaqueTile kernel,
but replaces the old 10-plane transactional body with a two-map BG8 owner.
The runtime key is a render generation and logical cell, except immutable
backdrop tiles which use generation zero plus source home ID. Hash matches
without an exact key still require a fresh-VBlank 64-byte VRAM comparison.
This module does not build or modify a ROM itself.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

from source_selector_handoff_native import (
    CONTROL as MOTION_CONTROL, HANDOFF_MAGIC, OFF_STATE, STATE_GAMEPLAY,
)
from source_warm_bg8_bounds_native import apply_nonzero_bounds


REFS = 0x430000                 # 960 u16: current bit 0, pending bit 1
HASHES = 0x430780               # 960 u16; zero means no uploaded content
PENDING_MAP = 0x430F00          # 1024 u16 entries
KEYS = 0x431700                 # 960 x two u16 provenance words
CONTROL = 0x432600              # private 256-byte control block
STAGE = 0x432700                # 80 bytes of AstraOpaqueTile output
BUCKETS = 0x432780              # 64 u16 heads; bucket links live in ref high bits
TILE_COUNT = 960
CELL_COUNT = 896
MAP_COUNT = 1024
BATCH_LIMIT = 3
BATCH_COUNT = CONTROL + 0x2E
BATCH_SLOTS = CONTROL + 0x30    # three u16 physical slot IDs
BATCH_INDEX = CONTROL + 0x36
BATCH_DATA = CONTROL + 0x40     # 3 x 64 bytes, wholly inside existing control
BATCH_OVERLAY_LIMIT = 4
BATCH_OVERLAY_INDEX = CONTROL + 0x3C
OBSOLETE_COUNT = CONTROL + 0x38
CURRENT_BACKDROP_REUSE_COUNT = CONTROL + 0x3A
LATEST_PIN = 0x7E7800
RENDER_PIN = 0x7E9600

_BRANCH_INVERSE = {
    "beq": "bne", "bne": "beq", "bcc": "bcs", "bcs": "bcc",
    "bmi": "bpl", "bpl": "bmi",
}


def _relax(text: str) -> str:
    serial = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal serial
        serial += 1
        inverse, target = _BRANCH_INVERSE[match.group(1)], match.group(2)
        skip = f"Bg8_BranchSkip{serial}"
        return f" {inverse} {skip}\n jmp {target}\n{skip}:\n.a16\n.i16"

    return re.sub(
        r"^ (beq|bne|bcc|bcs|bmi|bpl) (Bg8_\w+)$",
        replace,
        text,
        flags=re.M,
    )


def _once(text: str, needle: str, replacement: str, code: str) -> str:
    count = text.count(needle)
    if count != 1:
        raise ValueError(f"BG8_SOURCE_DRIFT:{code}:{count}")
    return text.replace(needle, replacement, 1)


def _address(value: object, name: str) -> int:
    if not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
        raise ValueError(f"BG8_ADDRESS:{name}")
    return value


def _validate_config(config: Mapping[str, object]) -> int:
    # BG8 assets publish a 512-byte source-derived RGB555 palette.  No color
    # values are synthesized here; only the pinned asset address is consumed.
    palette = _address(config.get("palette_cpu"), "palette_cpu")
    if palette < 0xC00000 or ((palette & 0xFFFF) + 512) > 0x10000:
        raise ValueError("BG8_PALETTE_ROM_WINDOW")
    if config.get("tile_bytes", 64) != 64:
        raise ValueError("BG8_TILE_BYTES")
    if config.get("map_cells", MAP_COUNT) != MAP_COUNT:
        raise ValueError("BG8_MAP_CELLS")
    free_reuse = config.get("free_canonical_slot_reuse_v1")
    if free_reuse is not None and free_reuse is not True:
        raise ValueError("BG8_FREE_REUSE_CONFIG")
    if free_reuse is True and config.get("tile_upload_batch_overlay_v2") is not True:
        raise ValueError("BG8_FREE_REQUIRES_OVERLAY")
    return palette


def _validate_symbols(symbols: Mapping[str, object]) -> dict[str, int]:
    needed = ("WarmYield", "WarmYield_Scan", "WarmDisplayLatch")
    return {name: _address(symbols.get(name), name) for name in needed}


def bg8_fingerprint(tile: bytes) -> int:
    """Independent oracle for the emitter's 32-word rotate/XOR/add hash."""
    if not isinstance(tile, bytes) or len(tile) != 64:
        raise ValueError("BG8_FINGERPRINT_TILE")
    value = 0xA532
    for offset in range(0, 64, 2):
        value = (((value << 1) | (value >> 15)) & 0xFFFF)
        value ^= tile[offset] | (tile[offset + 1] << 8)
        value = (value + 0x9E37) & 0xFFFF
    return value or 1


def backdrop_stage_matches(source_tile: bytes, stage_tile: bytes) -> bool:
    """Compare the standard planar stage against immutable 10-byte source rows."""
    if not isinstance(source_tile, bytes) or len(source_tile) != 80:
        raise ValueError("BG8_BACKDROP_SOURCE_TILE")
    if not isinstance(stage_tile, bytes) or len(stage_tile) != 64:
        raise ValueError("BG8_BACKDROP_STAGE_TILE")
    expected = b"".join(
        source_tile[row * 10 + plane * 2:row * 10 + plane * 2 + 2]
        for plane in range(4) for row in range(8))
    return stage_tile == expected


def advance_generation(generation: int,
                       tags: list[tuple[int, int]]) -> tuple[int, list[tuple[int, int]]]:
    """Advance the render serial, invalidating noncanonical tags before reuse.

    Generation zero denotes immutable source-home provenance. Serial FFFF is
    never issued; tags for noncanonical uploads are invalidated to FFFF before
    serial one is reused.
    """
    if not isinstance(generation, int) or not 0 <= generation <= 0xFFFF:
        raise ValueError("BG8_GENERATION_WORD")
    if not isinstance(tags, list) or any(
            not isinstance(tag, tuple) or len(tag) != 2 or
            any(not isinstance(value, int) or not 0 <= value <= 0xFFFF for value in tag)
            for tag in tags):
        raise ValueError("BG8_GENERATION_TAGS")
    if generation < 0xFFFE:
        return generation + 1 or 1, list(tags)
    return 1, [(0, cell) if gen == 0 else (0xFFFF, 0xFFFF)
               for gen, cell in tags]


def lookup_bucket(head: int, packed_refs: list[int], hashes: list[int],
                  query_hash: int) -> list[int]:
    """Walk one packed native bucket, validating every link and ref owner."""
    if len(packed_refs) != len(hashes) or not 1 <= len(hashes) <= TILE_COUNT:
        raise ValueError("BG8_BUCKET_EXTENT")
    if not isinstance(query_hash, int) or not 0 <= query_hash <= 0xFFFF:
        raise ValueError("BG8_BUCKET_HASH")
    chain: list[int] = []
    link = head
    hops = 0
    while link:
        if not isinstance(link, int) or not 1 <= link <= len(hashes):
            raise ValueError("BG8_BUCKET_LINK_RANGE")
        if hops >= len(hashes):
            raise ValueError("BG8_BUCKET_CYCLE")
        hops += 1
        slot = link - 1
        ref = packed_refs[slot]
        if not isinstance(ref, int) or not 0 <= ref <= 0xFFFF or not (ref & 3):
            raise ValueError("BG8_BUCKET_UNOWNED_LINK")
        if hashes[slot] == query_hash:
            chain.append(slot)
        link = (ref >> 2) & 0x3FF
    return chain


def _entry_patch(text: str) -> str:
    ready_replacement = (
        " jsl Bg8_EntryGuard\n bcc Bg8_EntryGuardOK\n"
        " jmp WarmEntry_Reject\nBg8_EntryGuardOK:\nWarmEntry_Skip1:"
    )
    ready_pattern = re.compile(
        r"(?m)^[ \t]*lda\.l \$7FFB96\n[ \t]*cmp #46264\n"
        r"[ \t]*beq WarmEntry_Skip1\n[ \t]*jmp WarmEntry_Reject\n"
        r"WarmEntry_Skip1:"
    )
    text, replaced = ready_pattern.subn(ready_replacement, text, count=1)
    if replaced != 1:
        raise ValueError("BG8_SOURCE_DRIFT:COLD_READY_GUARD")
    a = text.index("OnlinePublish:")
    b = text.index("OnlinePreflight:", a)
    front = text[a:b]
    if front.count("jmp NbBegin") != 1:
        raise ValueError(f"BG8_SOURCE_DRIFT:BEGIN_ROUTE:{front.count('jmp NbBegin')}")
    text = text[:a] + front.replace("jmp NbBegin", "jmp Bg8_Begin", 1) + text[b:]
    return text


def _body(symbols: Mapping[str, int], palette: int, *,
          batch_limit: int = BATCH_LIMIT, batch_index: int = BATCH_INDEX) -> str:
    wy, wys, latch = (symbols["WarmYield"], symbols["WarmYield_Scan"],
                      symbols["WarmDisplayLatch"])
    L: list[str] = [".org $F100", ".a16", ".i16"]

    def add(*lines: str) -> None:
        L.extend(lines)

    def label(name: str) -> None:
        add(name + ":", ".a16", ".i16")

    def branch(op: str, name: str) -> None:
        add(f" {op} Bg8_{name}")

    def sta_long(at: int) -> None:
        add(f" sta.l ${at:06X}")

    label("Bg8_EntryGuard")
    add(" lda.l $7E7700\n cmp #$B6D0")
    branch("bne", "EntryBad")
    add(" lda.l $7FFB88\n cmp #$B6D0")
    branch("bne", "EntryBad")
    add(" lda.l $7FFB96\n cmp #$B4B8")
    branch("beq", "EntryWarm")
    add(f" lda.l ${CONTROL:06X}\n cmp #1")
    branch("bne", "EntryBad")
    add(" lda.l $7FFB96")
    branch("bne", "EntryBad")
    label("Bg8_EntryWarm")
    add(" clc\n rtl")
    label("Bg8_EntryBad")
    add(" sec\n rtl")

    # Entry is reached with the OnlinePublish frame already established. Cold
    # setup runs only when the owner marks the guarded ready=0 path.
    label("Bg8_Begin")
    add(f" lda.l ${CONTROL:06X}")
    add(f" cmp #1")
    branch("beq", "ColdAlreadyPrepared")
    add(f" lda.l ${CONTROL:06X}\n cmp #0")
    branch("bne", "Fault")
    add(f" lda.l $7E7700\n cmp #$B6D0")
    branch("bne", "Fault")
    add(f" lda.l $7FFB88\n cmp #$B6D0")
    branch("bne", "Fault")
    add(" lda.l $7FFB96\n cmp #$B4B8")
    branch("bne", "Fault")
    label("Bg8_ColdAlreadyPrepared")
    # A failed source image decode is sticky and cannot be made ready by this
    # publisher.  Pending references are cleared before planning a new view.
    add(" lda.l $7E9502")
    branch("bne", "Fault")
    add(" ldx #0")
    label("Bg8_ClearPendingRefs")
    add(f" lda.l ${REFS:06X},x\n and #1\n sta.l ${REFS:06X},x\n inx\n inx\n cpx #{TILE_COUNT*2}")
    branch("bcc", "ClearPendingRefs")
    add(" lda #0")
    sta_long(CONTROL + 0x0A)  # cell cursor
    sta_long(CONTROL + 0x0C)  # current hash candidate
    sta_long(CONTROL + 0x0E)  # selected physical tile
    sta_long(CONTROL + 0x10)  # found flag
    sta_long(BATCH_COUNT)
    sta_long(batch_index)
    # Each attempt receives a nonzero generation. Before serial reuse, invalidate
    # every noncanonical tag; canonical (generation zero) home tiles stay valid.
    add(f" lda.l ${CONTROL+4:06X}\n cmp #$FFFE")
    branch("bcs", "GenerationWrap")
    add(f" inc a\n sta.l ${CONTROL+4:06X}\n jmp Bg8_GenerationReady")
    label("Bg8_GenerationWrap")
    add(" ldx #0")
    label("Bg8_GenerationInvalidate")
    add(f" lda.l ${KEYS:06X},x\n beq Bg8_GenerationKeep\n lda #$FFFF\n sta.l ${KEYS:06X},x\n sta.l ${KEYS+2:06X},x")
    label("Bg8_GenerationKeep")
    add(f" txa\n clc\n adc #4\n tax\n cpx #{TILE_COUNT*4}")
    branch("bcc", "GenerationInvalidate")
    add(f" lda #1\n sta.l ${CONTROL+4:06X}")
    label("Bg8_GenerationReady")
    add(" jsr Bg8_RebuildIndex")
    label("Bg8_CellLoop")
    add(f" lda.l ${CONTROL+0x0A:06X}\n cmp #{CELL_COUNT}")
    branch("bcs", "Padding")
    add(f" lda.l ${CONTROL+0x0A:06X}\n sta $18\n lda.l ${CONTROL:06X}\n cmp #1\n beq Bg8_CellYieldDone\n jsl ${wys:06X}\n lda.l $7E9502")
    branch("bne", "Fault")
    label("Bg8_CellYieldDone")
    add(" jsr Bg8_CheckObsolete\n bcs Bg8_Obsolete")
    add(f" lda #0\n sta.l ${CONTROL+0x26:06X}\n jsr Bg8_IsOutsidePose")
    branch("bcs", "OutsidePose")
    add(" jmp Bg8_ComposePose")
    label("Bg8_OutsidePose")
    add(f" lda.l ${CONTROL+0x26:06X}")
    branch("bne", "Fault")
    add(" jsr Bg8_TryCurrentBackdrop")
    branch("bcs", "Hit")
    add(" jmp Bg8_CopyBackdrop")
    label("Bg8_ComposePose")
    add(" jsr OnlineColorPointers\n jsl AstraOpaqueTile\n lda.l $7E9502")
    branch("bne", "Fault")
    add(f" lda.l ${CONTROL+4:06X}\n sta.l ${CONTROL+0x20:06X}\n lda.l ${CONTROL+0x0A:06X}\n sta.l ${CONTROL+0x22:06X}\n jsr Bg8_BackdropKey")
    add(" jmp Bg8_HashInit")
    # The accepted front end records clipped inclusive tile-index bounds in
    # DP. Validate the 32x28 tile domain, then return C=1 only when this cell
    # lies outside the rectangle.
    label("Bg8_IsOutsidePose")
    add(" lda $10\n cmp $12")
    branch("bcc", "PoseBoundsXOrdered")
    branch("beq", "PoseBoundsXOrdered")
    branch("bra", "PoseBad")
    label("Bg8_PoseBoundsXOrdered")
    add(" lda $12\n cmp #32")
    branch("bcs", "PoseBad")
    add(" lda $14\n cmp $16")
    branch("bcc", "PoseBoundsYOrdered")
    branch("beq", "PoseBoundsYOrdered")
    branch("bra", "PoseBad")
    label("Bg8_PoseBoundsYOrdered")
    add(" lda $16\n cmp #28")
    branch("bcs", "PoseBad")
    add(f" lda.l ${CONTROL+0x0A:06X}\n and #31\n cmp $10")
    branch("bcc", "PoseOutside")
    add(f" lda.l ${CONTROL+0x0A:06X}\n and #31\n cmp $12")
    branch("bcc", "PoseCheckY")
    branch("beq", "PoseCheckY")
    branch("bra", "PoseOutside")
    label("Bg8_PoseCheckY")
    add(f" lda.l ${CONTROL+0x0A:06X}\n lsr a\n lsr a\n lsr a\n lsr a\n lsr a\n cmp $14")
    branch("bcc", "PoseOutside")
    add(f" lda.l ${CONTROL+0x0A:06X}\n lsr a\n lsr a\n lsr a\n lsr a\n lsr a\n cmp $16")
    branch("bcc", "PoseInside")
    branch("beq", "PoseInside")
    branch("bra", "PoseOutside")
    label("Bg8_PoseInside")
    add(" clc\n rts")
    label("Bg8_PoseOutside")
    add(" sec\n rts")
    label("Bg8_PoseBad")
    add(f" lda #1\n sta.l ${CONTROL+0x26:06X}")
    add(" sec\n rts")
    # A previous map entry is only a hint: cancellation can leave this array
    # partly overwritten. Current ownership plus an exact immutable backdrop
    # key independently proves the physical content. Misses take the original
    # staging/hash path. The per-cell source scan above is never skipped.
    label("Bg8_TryCurrentBackdrop")
    add(f" lda.l ${CONTROL:06X}")
    branch("bne", "CurrentBackdropMiss")
    add(f" lda.l ${CONTROL+0x0A:06X}\n asl a\n tax\n lda.l $E18000,x\n sta.l ${CONTROL+0x2A:06X}\n lda.l ${PENDING_MAP:06X},x\n cmp #{TILE_COUNT}")
    branch("bcs", "CurrentBackdropMiss")
    add(f" tay\n asl a\n tax\n lda.l ${REFS:06X},x\n and #1")
    branch("beq", "CurrentBackdropMiss")
    add(f" lda.l ${HASHES:06X},x")
    branch("beq", "CurrentBackdropMiss")
    add(f" tya\n asl a\n asl a\n tax\n lda.l ${KEYS:06X},x")
    branch("bne", "CurrentBackdropMiss")
    add(f" lda.l ${KEYS+2:06X},x\n cmp.l ${CONTROL+0x2A:06X}")
    branch("bne", "CurrentBackdropMiss")
    add(f" tya\n sta.l ${CONTROL+0x0E:06X}\n lda #1\n sta.l ${CONTROL+0x10:06X}\n lda.l ${CURRENT_BACKDROP_REUSE_COUNT:06X}\n cmp #$FFFF")
    branch("beq", "CurrentBackdropReused")
    add(f" inc a\n sta.l ${CURRENT_BACKDROP_REUSE_COUNT:06X}")
    label("Bg8_CurrentBackdropReused")
    add(" sec\n rts")
    label("Bg8_CurrentBackdropMiss")
    add(" clc\n rts")
    # Outside the full-image rectangle, copy useful source row pairs into the
    # standard BG8 planar layout and zero the unused fifth pair.
    label("Bg8_CopyBackdrop")
    add(f" lda.l ${CONTROL+0x0A:06X}\n asl a\n tax\n lda.l $E18000,x\n sta.l ${CONTROL+0x2A:06X}\n asl a\n asl a\n clc\n adc.l ${CONTROL+0x2A:06X}\n asl a\n asl a\n asl a\n asl a\n sta $00\n sep #$20\n.a8\n lda #$F3\n sta $02\n rep #$20\n.a16\n ldy #0\n ldx #0\n lda #0\n sta.l ${CONTROL+0x1C:06X}")
    label("Bg8_CopyBackdropRow")
    for plane in range(4):
        add(f" lda [$00],y\n sta.l ${STAGE+plane*16:06X},x\n iny\n iny")
    add(" iny\n iny\n inx\n inx")  # skip planes 8/9; advance output row
    add(f" lda.l ${CONTROL+0x1C:06X}\n inc a\n sta.l ${CONTROL+0x1C:06X}\n cmp #8")
    branch("bcc", "CopyBackdropRow")
    add(" ldx #64\n lda #0")
    label("Bg8_CopyBackdropZero")
    add(f" sta.l ${STAGE:06X},x\n inx\n inx\n cpx #80")
    branch("bcc", "CopyBackdropZero")
    add(f" lda #0\n sta.l ${CONTROL+0x20:06X}\n lda.l ${CONTROL+0x2A:06X}\n sta.l ${CONTROL+0x22:06X}")
    branch("bra", "HashInit")
    label("Bg8_HashInit")
    add(" ldx #0\n lda #$A532")
    sta_long(CONTROL + 0x1E)
    label("Bg8_HashLoop")
    # Rotate the 16-bit value by one without depending on the prior carry:
    # ASL exposes bit 15 in C, then ADC #0 folds it back into bit 0.
    add(f" lda.l ${CONTROL+0x1E:06X}\n asl a\n adc #0\n eor.l ${STAGE:06X},x\n clc\n adc #$9E37\n sta.l ${CONTROL+0x1E:06X}\n inx\n inx\n cpx #64")
    branch("bcc", "HashLoop")
    add(f" lda.l ${CONTROL+0x1E:06X}\n bne Bg8_HashReady\n lda #1\n sta.l ${CONTROL+0x1E:06X}")
    label("Bg8_HashReady")
    add(f" lda #0\n sta.l ${CONTROL+0x16:06X}\n lda.l ${CONTROL+0x1E:06X}\n and #63\n asl a\n tax\n lda.l ${BUCKETS:06X},x\n sta.l ${CONTROL+0x0C:06X}")
    label("Bg8_FindLoop")
    add(f" lda.l ${CONTROL+0x0C:06X}\n beq Bg8_FindFree\n cmp #{TILE_COUNT+1}")
    branch("bcs", "Fault")
    add(f" lda.l ${CONTROL+0x16:06X}\n inc a\n sta.l ${CONTROL+0x16:06X}\n cmp #{TILE_COUNT+1}")
    branch("bcs", "Fault")
    add(f" lda.l ${CONTROL+0x0C:06X}\n dec a\n sta.l ${CONTROL+0x0E:06X}\n asl a\n tax\n lda.l ${REFS:06X},x\n and #3")
    branch("beq", "Fault")
    add(f" lda.l ${HASHES:06X},x\n cmp.l ${CONTROL+0x1E:06X}")
    branch("bne", "FindNext")
    # Provenance equality is an exact source-content identity. Other hash
    # collisions still go through a full 64-byte physical comparison.
    add(f" lda.l ${CONTROL+0x0E:06X}\n asl a\n asl a\n tax")
    for off in (0, 2):
        add(f" lda.l ${KEYS:06X},x\n cmp.l ${CONTROL+0x20+off:06X}")
        branch("bne", "KeyDifferent")
        if off != 2:
            add(" inx\n inx")
    add(" jmp Bg8_KeyMatch")
    label("Bg8_KeyMatch")
    add(f" lda #1\n sta.l ${CONTROL+0x10:06X}\n jmp Bg8_Hit")
    label("Bg8_KeyDifferent")
    # An exact key can reuse privately queued bytes. Any physical comparison
    # first drains all queued uploads, so an indexed pending slot is readable
    # from VRAM only after its exact staged content has actually arrived.
    add(f" jsr Bg8_FlushTiles\n bcs Bg8_Fault\n lda.l ${CONTROL+0x0E:06X}\n sta $2C\n jsr Bg8_WaitFresh\n bcs Bg8_Fault\n jsr Bg8_Compare\n bcc Bg8_CompareHit")
    label("Bg8_FindNext")
    add(f" lda.l ${CONTROL+0x0E:06X}\n asl a\n tax\n lda.l ${REFS:06X},x\n and #$FFFC\n lsr a\n lsr a\n sta.l ${CONTROL+0x0C:06X}\n jmp Bg8_FindLoop")
    label("Bg8_CompareHit")
    add(f" lda #1\n sta.l ${CONTROL+0x10:06X}\n jmp Bg8_Hit")
    label("Bg8_FindFree")
    add(f" lda.l ${CONTROL+0x14:06X}\n beq Bg8_Deferred\n cmp #{TILE_COUNT+1}")
    branch("bcs", "Fault")
    add(f" dec a\n sta.l ${CONTROL+0x0E:06X}\n asl a\n tax\n lda.l ${REFS:06X},x\n and #3")
    branch("bne", "Fault")
    add(f" lda.l ${REFS:06X},x\n and #$FFFC\n lsr a\n lsr a\n sta.l ${CONTROL+0x14:06X}\n lda #0\n sta.l ${REFS:06X},x")
    label("Bg8_FreeFound")
    add(" jsr Bg8_QueueTile\n bcs Bg8_Fault")
    # Publish private pending identity only after the stage copy succeeds.
    # A queued slot cannot be current. Exact provenance may reuse its copied
    # content; the key-different path above flushes before physical readback.
    # No source yield follows a completed batch before this publication.
    add(f" lda.l ${CONTROL+0x0E:06X}\n asl a\n asl a\n tax")
    for off in (0, 2):
        add(f" lda.l ${CONTROL+0x20+off:06X}\n sta.l ${KEYS:06X},x")
        if off != 2:
            add(" inx\n inx")
    add(f" lda.l ${CONTROL+0x0E:06X}\n asl a\n tax\n lda.l ${CONTROL+0x1E:06X}\n sta.l ${HASHES:06X},x\n and #63\n asl a\n sta.l ${CONTROL+0x1A:06X}\n phx\n lda.l ${CONTROL+0x1A:06X}\n tax\n lda.l ${BUCKETS:06X},x\n asl a\n asl a\n ora #2\n sta.l ${CONTROL+0x0C:06X}\n plx\n lda.l ${CONTROL+0x0C:06X}\n sta.l ${REFS:06X},x\n txa\n lsr a\n inc a\n sta.l ${CONTROL+0x0C:06X}\n lda.l ${CONTROL+0x1A:06X}\n tax\n lda.l ${CONTROL+0x0C:06X}\n sta.l ${BUCKETS:06X},x")
    add(f" lda #1\n sta.l ${CONTROL+0x10:06X}\n jmp Bg8_WriteMap")
    label("Bg8_Hit")
    add(f" lda.l ${CONTROL+0x0E:06X}\n asl a\n tax\n lda.l ${REFS:06X},x\n ora #2\n sta.l ${REFS:06X},x")
    label("Bg8_WriteMap")
    add(f" lda.l ${CONTROL+0x0A:06X}\n asl a\n tax\n lda.l ${CONTROL+0x0E:06X}\n sta.l ${PENDING_MAP:06X},x")
    add(f" lda.l ${CONTROL+0x0A:06X}\n inc a\n sta.l ${CONTROL+0x0A:06X}\n jmp Bg8_CellLoop")
    # Rebuild a 64-bucket hash index from current residents at each attempt.
    # Packed ref bits 2..11 contain next-slot-plus-one; the low bits remain the
    # exact current/pending ownership flags. No runtime source service occurs.
    label("Bg8_RebuildIndex")
    add(" lda #0")
    sta_long(CONTROL + 0x14)  # free-list head (slot plus one)
    add(" ldx #0")
    label("Bg8_ClearBuckets")
    add(f" sta.l ${BUCKETS:06X},x\n inx\n inx\n cpx #128")
    branch("bcc", "ClearBuckets")
    add(" ldx #0")
    label("Bg8_IndexLoop")
    add(f" lda.l ${REFS:06X},x\n and #1\n sta.l ${REFS:06X},x")
    branch("beq", "IndexFree")
    add(f" lda.l ${HASHES:06X},x\n and #63\n asl a\n sta.l ${CONTROL+0x1A:06X}\n phx\n lda.l ${CONTROL+0x1A:06X}\n tax\n lda.l ${BUCKETS:06X},x\n asl a\n asl a\n ora #1\n sta.l ${CONTROL+0x0C:06X}\n plx\n lda.l ${CONTROL+0x0C:06X}\n sta.l ${REFS:06X},x\n txa\n lsr a\n inc a\n sta.l ${CONTROL+0x0C:06X}\n phx\n lda.l ${CONTROL+0x1A:06X}\n tax\n lda.l ${CONTROL+0x0C:06X}\n sta.l ${BUCKETS:06X},x\n plx\n jmp Bg8_IndexNext")
    label("Bg8_IndexFree")
    add(f" lda.l ${CONTROL+0x14:06X}\n asl a\n asl a\n sta.l ${REFS:06X},x\n txa\n lsr a\n inc a\n sta.l ${CONTROL+0x14:06X}")
    label("Bg8_IndexNext")
    add(f" inx\n inx\n cpx #{TILE_COUNT*2}")
    branch("bcc", "IndexLoop")
    add(" rts")
    # Padding repeats the first visible cell's already-pending-protected ID.
    # All physical slots, including tile zero, remain available to COW.
    label("Bg8_Padding")
    add(f" lda.l ${PENDING_MAP:06X}\n cmp #{TILE_COUNT}")
    branch("bcs", "Fault")
    add(" asl a\n tax")
    add(f" lda.l ${REFS:06X},x\n and #2")
    branch("beq", "Fault")
    add(f" lda.l ${PENDING_MAP:06X}\n ldx #{CELL_COUNT*2}")
    label("Bg8_ClearPadding")
    add(f" sta.l ${PENDING_MAP:06X},x\n inx\n inx\n cpx #{MAP_COUNT*2}")
    branch("bcc", "ClearPadding")
    label("Bg8_PaddingComplete")
    add(" jsr Bg8_CheckObsolete\n bcs Bg8_Obsolete")
    add(" jsr Bg8_FlushTiles\n bcs Bg8_Fault")
    # Map transfer targets the inactive page. This wait is the last ordinary
    # source-service point; the final switch is a separate no-yield blank.
    add(" jsr Bg8_WaitFresh\n bcs Bg8_Fault\n jsr Bg8_CheckObsolete\n bcs Bg8_Obsolete")
    add(f" lda.l ${CONTROL+2:06X}\n beq Bg8_MapPage0")
    add(" lda #$7800")
    branch("bra", "MapDma")
    label("Bg8_MapPage0")
    add(" lda #$7C00")
    label("Bg8_MapDma")
    add(f" sta.l ${CONTROL+0x12:06X}\n jsr Bg8_DmaMap\n jsr Bg8_WaitFreshNoYield\n bcs Bg8_Fault")
    # The last ownership/sticky/readiness check is before the sole visibility
    # write. Nothing faultable runs after Bg8_SwitchComplete.
    add(" lda.l $7E9502")
    branch("bne", "Fault")
    add(" lda.l $7E7700\n cmp #$B6D0")
    branch("bne", "Fault")
    add(" lda.l $7FFB88\n cmp #$B6D0")
    branch("bne", "Fault")
    add(f" lda.l ${CONTROL:06X}\n cmp #1")
    branch("beq", "SwitchColdReady")
    add(" lda.l $7FFB96\n cmp #$B4B8")
    branch("bne", "Fault")
    branch("bra", "SwitchGuardDone")
    label("Bg8_SwitchColdReady")
    add(" lda.l $7FFB96")
    branch("bne", "Fault")
    label("Bg8_SwitchGuardDone")
    label("Bg8_SwitchBegin")
    add(f" lda.l ${CONTROL+0x12:06X}\n lsr a\n lsr a\n lsr a\n lsr a\n lsr a\n lsr a\n lsr a\n lsr a\n sep #$20\n.a8\n sta.l $002107\n rep #$20\n.a16")
    add(f" lda.l ${CONTROL+0x12:06X}\n cmp #$7C00\n bne Bg8_SwitchPage0\n lda #1\n sta.l ${CONTROL+2:06X}\n jmp Bg8_Switched")
    label("Bg8_SwitchPage0")
    add(f" lda #0\n sta.l ${CONTROL+2:06X}")
    label("Bg8_Switched")
    label("Bg8_SwitchComplete")
    # Map register switch is the visibility point; no failure or source service
    # follows it. Update the immutable display identity before bookkeeping.
    add(f" jsl ${latch:06X}\n ldx #0")
    add(" ldx #0")
    label("Bg8_CommitRefs")
    add(f" lda.l ${REFS:06X},x\n and #2\n beq Bg8_CommitClear\n lda #1\n sta.l ${REFS:06X},x\n jmp Bg8_CommitNext")
    label("Bg8_CommitClear")
    add(f" lda #0\n sta.l ${REFS:06X},x")
    label("Bg8_CommitNext")
    add(f" inx\n inx\n cpx #{TILE_COUNT*2}")
    branch("bcc", "CommitRefs")
    label("Bg8_WarmDone")
    add(" jmp OnlineNoopComplete")
    label("Bg8_Deferred")
    add(" lda #0")
    sta_long(BATCH_COUNT)
    sta_long(batch_index)
    add(" ldx #0")
    label("Bg8_RollbackRefs")
    add(f" lda.l ${REFS:06X},x\n and #1\n sta.l ${REFS:06X},x\n inx\n inx\n cpx #{TILE_COUNT*2}")
    branch("bcc", "RollbackRefs")
    add(f" lda.l ${CONTROL+0x18:06X}\n cmp #$FFFF\n beq Bg8_DeferSaturated\n inc a\n sta.l ${CONTROL+0x18:06X}")
    label("Bg8_DeferSaturated")
    add(" jmp OnlineNoopComplete")
    label("Bg8_Fault")
    add(" lda #0")
    sta_long(BATCH_COUNT)
    sta_long(batch_index)
    add(" ldx #0")
    label("Bg8_FaultRollback")
    add(f" lda.l ${REFS:06X},x\n and #1\n sta.l ${REFS:06X},x\n inx\n inx\n cpx #{TILE_COUNT*2}")
    branch("bcc", "FaultRollback")
    add(" jmp OnlineReject")

    # Only top-level, pre-map callers branch here, with no outstanding local
    # JSR frame. Uploaded free slots remain invisible. Discard pending refs
    # and queue state, then use the existing nonfaulting no-op unwind. Status
    # WarmRenderRetired is distinct from the post-switch WarmPublished latch.
    label("Bg8_Obsolete")
    add(" lda #0")
    sta_long(BATCH_COUNT)
    sta_long(batch_index)
    add(" ldx #0")
    label("Bg8_ObsoleteRollback")
    add(f" lda.l ${REFS:06X},x\n and #1\n sta.l ${REFS:06X},x\n inx\n inx\n cpx #{TILE_COUNT*2}")
    branch("bcc", "ObsoleteRollback")
    add(f" lda.l ${OBSOLETE_COUNT:06X}\n cmp #$FFFF\n beq Bg8_ObsoleteComplete\n inc a")
    sta_long(OBSOLETE_COUNT)
    label("Bg8_ObsoleteComplete")
    add(" jmp OnlineNoopComplete")

    # The latest source snapshot is synchronously sealed before a service
    # returns and NMI does not write it, exactly as WarmTryPublish consumes it.
    # Enable cancellation only after the real gameplay handoff, for the same
    # model. Cold and pre-gameplay calls cannot cancel; position/pose/frame
    # changes alone retain their existing publication behavior.
    # This helper cannot yield, write source state, or run after map staging.
    label("Bg8_CheckObsolete")
    add(f" lda.l ${CONTROL:06X}\n bne Bg8_IdentityGood")
    add(f" lda.l ${MOTION_CONTROL:06X}\n cmp #${HANDOFF_MAGIC:04X}\n bne Bg8_IdentityGood")
    add(f" lda.l ${MOTION_CONTROL+OFF_STATE:06X}\n cmp #{STATE_GAMEPLAY}\n bne Bg8_IdentityGood")
    for pin in (LATEST_PIN, RENDER_PIN):
        # These are the actor's altitude DWORD, not Motion_State. Match the
        # retained WarmEntry zero-altitude admission guard for both snapshots.
        add(f" lda.l ${pin+0x0C:06X}\n ora.l ${pin+0x0E:06X}\n bne Bg8_IdentityGood")
    add(f" lda.l ${LATEST_PIN+0x50:06X}\n cmp.l ${RENDER_PIN+0x50:06X}\n bne Bg8_IdentityGood")
    add(f" lda.l ${LATEST_PIN+0x90:06X}\n ora.l ${LATEST_PIN+0x92:06X}\n beq Bg8_IdentityGood")
    for offset in (0x54, 0x1C):
        add(f" lda.l ${LATEST_PIN+offset:06X}\n cmp.l ${RENDER_PIN+offset:06X}\n bne Bg8_IdentityObsolete")
    label("Bg8_IdentityGood")
    add(" clc\n rts")
    label("Bg8_IdentityObsolete")
    add(" sec\n rts")

    # The legacy three payloads occupy CONTROL. The opt-in fourth is the
    # current STAGE slice itself, flushed immediately when filled. It survives
    # the sole source service before the fresh wait; the native overlay audit
    # must prove its bytes before/after that service. No current slot is eligible.
    label("Bg8_QueueTile")
    add(f" lda.l ${BATCH_COUNT:06X}\n cmp #{batch_limit}")
    branch("bcs", "BatchFail")
    add(f" asl a\n tax\n lda.l ${CONTROL+0x0E:06X}\n cmp #{TILE_COUNT}")
    branch("bcs", "BatchFail")
    add(f" sta.l ${BATCH_SLOTS:06X},x\n lda.l ${BATCH_COUNT:06X}\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n tax")
    # Long indexed-Y is not a 65816 instruction. Unroll the fixed 32 words
    # instead of borrowing a renderer DP pointer or adding another RAM lease.
    for offset in range(0, 64, 2):
        add(f" lda.l ${STAGE+offset:06X}\n sta.l ${BATCH_DATA+offset:06X},x")
    add(f" lda.l ${BATCH_COUNT:06X}\n inc a\n sta.l ${BATCH_COUNT:06X}")
    if batch_limit == BATCH_OVERLAY_LIMIT:
        label("Bg8_QueuePayloadCopied")
    add(f" cmp #{batch_limit}")
    branch("bcc", "BatchGood")
    add(" jsr Bg8_FlushTiles\n rts")
    label("Bg8_BatchGood")
    add(" clc\n rts")
    label("Bg8_BatchFail")
    add(" sec\n rts")

    # The only cooperative yield occurs in the fresh wait, before any DMA.
    # All admitted descriptors execute in that same blank. No source service or
    # faultable metadata work can split them. Save the caller's tile scratch;
    # candidate hash/key/slot controls are preserved throughout the drain.
    label("Bg8_FlushTiles")
    add(f" lda.l ${BATCH_COUNT:06X}")
    branch("beq", "BatchGood")
    add(f" cmp #{batch_limit+1}")
    branch("bcs", "BatchFail")
    add(" jsr Bg8_WaitFresh")
    branch("bcs", "BatchFail")
    add(" lda $2C\n pha")
    label("Bg8_BatchBegin")
    add(" lda #0")
    sta_long(batch_index)
    label("Bg8_FlushLoop")
    add(f" lda.l ${batch_index:06X}\n asl a\n tax\n lda.l ${BATCH_SLOTS:06X},x\n sta $2C\n jsr Bg8_DmaTile")
    add(f" lda.l ${batch_index:06X}\n inc a\n sta.l ${batch_index:06X}\n cmp.l ${BATCH_COUNT:06X}")
    branch("bcc", "FlushLoop")
    label("Bg8_BatchComplete")
    add(" pla\n sta $2C\n lda #0")
    sta_long(BATCH_COUNT)
    sta_long(batch_index)
    add(" clc\n rts")

    # Source-service yield happens before the physical VBlank wait. During cold
    # forced blank with ready=0 it is skipped; all normal waits remain real.
    label("Bg8_WaitFresh")
    add(f" lda.l ${CONTROL:06X}\n cmp #1")
    branch("beq", "WaitCold")
    add(f" jsl ${wy:06X}")
    add(" lda.l $7E9502")
    branch("bne", "WaitFail")
    add(" jmp Bg8_WaitNormal")
    label("Bg8_WaitCold")
    add(" lda.l $7FFB96")
    branch("bne", "WaitFail")
    add(" clc\n rts")
    label("Bg8_WaitNormal")
    add("Bg8_WaitEnd:\n lda.l $004212\n and #$80")
    branch("bne", "WaitEnd")
    label("Bg8_WaitStart")
    add(" lda.l $004212\n and #$80")
    branch("beq", "WaitStart")
    add(" clc\n rts")
    label("Bg8_WaitFreshNoYield")
    add(f" lda.l ${CONTROL:06X}\n cmp #1")
    branch("beq", "WaitNoYieldCold")
    add("Bg8_NoYieldEnd:\n lda.l $004212\n and #$80")
    branch("bne", "NoYieldEnd")
    label("Bg8_NoYieldStart")
    add(" lda.l $004212\n and #$80")
    branch("beq", "NoYieldStart")
    add(" clc\n rts")
    label("Bg8_WaitNoYieldCold")
    add(" lda.l $7FFB96")
    branch("bne", "WaitFail")
    add(" clc\n rts")
    label("Bg8_WaitFail")
    add(" sec\n rts")
    # 16-bit hash of exactly the first four interleaved plane pairs.
    label("Bg8_Compare")
    label("Bg8_CompareBegin")
    add(" lda $2C\n asl a\n asl a\n asl a\n asl a\n asl a\n sta.l $002116\n sep #$20\n.a8\n lda #$80\n sta.l $002115\n rep #$20\n.a16\n lda.l $002139\n ldx #0")
    label("Bg8_CompareLoop")
    add(f" lda.l $002139\n cmp.l ${STAGE:06X},x")
    branch("bne", "CompareBad")
    add(" inx\n inx\n cpx #64")
    branch("bcc", "CompareLoop")
    add(" clc\n bra Bg8_CompareComplete")
    label("Bg8_CompareBad")
    add(" sec")
    label("Bg8_CompareComplete")
    add(" rts")
    # Canonical backdrop identity is admitted only when all 32 useful words
    # exactly equal the immutable F3 source tile.  Source rows are 10 bytes;
    # output planes are 16 bytes apart within each 8-byte output row.
    label("Bg8_BackdropKey")
    add(f" lda.l ${CONTROL+0x0A:06X}\n asl a\n tax\n lda.l $E18000,x\n sta.l ${CONTROL+0x2A:06X}")
    add(f" lda.l ${CONTROL+0x2A:06X}\n asl a\n asl a\n clc\n adc.l ${CONTROL+0x2A:06X}\n asl a\n asl a\n asl a\n asl a\n sta $00\n sep #$20\n.a8\n lda #$F3\n sta $02\n rep #$20\n.a16")
    add(f" lda #0\n sta.l ${CONTROL+0x1C:06X}\n ldx #0\n ldy #0")
    label("Bg8_BackdropRow")
    for plane in range(4):
        add(f" lda [$00],y\n cmp.l ${STAGE+plane*16:06X},x")
        branch("bne", "BackdropNo")
        add(" iny\n iny")
    add(" iny\n iny")
    add(" inx\n inx")
    add(f" lda.l ${CONTROL+0x1C:06X}\n inc a\n sta.l ${CONTROL+0x1C:06X}\n cmp #8")
    branch("bcc", "BackdropRow")
    add(f" lda #0\n sta.l ${CONTROL+0x20:06X}\n lda.l ${CONTROL+0x2A:06X}\n sta.l ${CONTROL+0x22:06X}\n clc\n rts")
    label("Bg8_BackdropNo")
    add(" sec\n rts")
    # Upload one queued 64-byte tile through owned channel 7. FlushTiles bounds
    # the selected batch index and places the entire batch in one fresh VBlank.
    label("Bg8_DmaTile")
    label("Bg8_DmaBegin")
    add(" lda $2C\n asl a\n asl a\n asl a\n asl a\n asl a\n sta.l $002116\n sep #$20\n.a8\n lda #$80\n sta.l $002115\n rep #$20\n.a16")
    add(f" lda.l ${batch_index:06X}\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n clc\n adc #${BATCH_DATA & 0xFFFF:04X}\n sta.l $004372\n lda #64\n sta.l $004375\n sep #$20\n.a8\n lda #1\n sta.l $004370\n lda #$18\n sta.l $004371\n lda #${BATCH_DATA >> 16:02X}\n sta.l $004374\n lda #$80\n sta.l $00420B\n rep #$20\n.a16")
    label("Bg8_DmaComplete")
    add(" rts")
    label("Bg8_DmaMap")
    label("Bg8_MapDmaBegin")
    add(f" sep #$20\n.a8\n lda #$80\n sta.l $002115\n rep #$20\n.a16\n lda.l ${CONTROL+0x12:06X}\n sta.l $002116\n lda #${PENDING_MAP & 0xFFFF:04X}\n sta.l $004372\n lda #2048\n sta.l $004375\n sep #$20\n.a8\n lda #1\n sta.l $004370\n lda #$18\n sta.l $004371\n lda #${PENDING_MAP >> 16:02X}\n sta.l $004374\n lda #$80\n sta.l $00420B\n rep #$20\n.a16")
    label("Bg8_MapDmaComplete")
    add(" rts")

    # Cold is a separately callable wrapper with its own saved context. It
    # runs the normal checked OnlinePublish front while forced blank, then
    # unblanks only on an actual fresh VBlank edge after publication.
    label("Bg8_Cold")
    add(" php\n rep #$38\n pha\n phx\n phy\n phb\n phd\n lda #0\n tcd\n sep #$20\n.a8\n lda #0\n pha\n plb\n rep #$20\n.a16")
    add(" lda.l $7E7700\n cmp #$B6D0")
    branch("bne", "ColdFault")
    add(" lda.l $7FFB88\n cmp #$B6D0")
    branch("bne", "ColdFault")
    add(" lda.l $7FFB96")
    branch("bne", "ColdFault")
    add(f" lda #1\n sta.l ${CONTROL:06X}\n lda #0\n sta.l ${CONTROL+2:06X}")
    add(" ldx #0\n lda #0")
    label("Bg8_ColdClearRefs")
    add(f" sta.l ${REFS:06X},x\n sta.l ${HASHES:06X},x\n inx\n inx\n cpx #{TILE_COUNT*2}")
    branch("bcc", "ColdClearRefs")
    add(" ldx #0")
    label("Bg8_ColdClearMaps")
    add(f" lda #0\n sta.l ${PENDING_MAP:06X},x\n inx\n inx\n cpx #{MAP_COUNT*2}")
    branch("bcc", "ColdClearMaps")
    add(f" ldx #4\n lda #0")
    label("Bg8_ColdClearControls")
    add(f" sta.l ${CONTROL:06X},x\n inx\n inx\n cpx #256")
    branch("bcc", "ColdClearControls")
    add(" sep #$20\n.a8\n lda #$80\n sta.l $002100\n rep #$20\n.a16")
    add(" sep #$20\n.a8\n lda #$80\n sta.l $002115\n rep #$20\n.a16\n lda #0\n sta.l $002116\n ldx #0")
    label("Bg8_ZeroTile")
    add(" lda #0\n sta.l $002118\n inx\n inx\n cpx #64")
    branch("bcc", "ZeroTile")
    add(" sep #$20\n.a8\n lda #3\n sta.l $002105\n lda #0\n sta.l $002133\n sta.l $002106\n lda #1\n sta.l $00212C\n lda #0\n sta.l $00212D\n sta.l $002130\n sta.l $002131\n sta.l $00210B\n lda #$78\n sta.l $002107\n lda #0\n sta.l $00210D\n sta.l $00210D\n lda #$FF\n sta.l $00210E\n sta.l $00210E\n lda #0\n sta.l $002121\n sta.l $002123\n sta.l $002124\n sta.l $002125\n sta.l $002126\n sta.l $002127\n sta.l $002128\n sta.l $002129\n sta.l $00212A\n sta.l $00212B\n sta.l $00212E\n sta.l $00212F\n rep #$20\n.a16")
    add(f" lda #${palette & 0xFFFF:04X}\n sta.l $004372\n lda #512\n sta.l $004375\n sep #$20\n.a8\n lda #0\n sta.l $004370\n lda #$22\n sta.l $004371\n lda #${palette >> 16:02X}\n sta.l $004374\n lda #$80\n sta.l $00420B\n rep #$20\n.a16")
    add(" ldx #0")
    label("Bg8_ColdCopyPin")
    add(" lda.l $7FBA00,x\n sta.l $7E9600,x\n inx\n inx\n cpx #146")
    branch("bcc", "ColdCopyPin")
    add(" lda #0\n sta.l $7E9692\n lda #0")
    sta_long(0x7FFB96)
    add(" jsl OnlinePublish")
    branch("bcs", "ColdFault")
    label("Bg8_ColdWaitUnblankEnd")
    add(" lda.l $004212\n and #$80")
    branch("bne", "ColdWaitUnblankEnd")
    label("Bg8_ColdWaitUnblankStart")
    add(" lda.l $004212\n and #$80")
    branch("beq", "ColdWaitUnblankStart")
    add(" sep #$20\n.a8\n lda #$0F\n sta.l $002100\n rep #$20\n.a16")
    add(f" lda #0\n sta.l ${CONTROL:06X}\n lda #$B4B8")
    sta_long(0x7FFB96)
    label("Bg8_ColdReadyPublished")
    add(" nop\n pld\n plb\n ply\n plx\n pla\n plp\n clc\n rtl")
    label("Bg8_ColdFault")
    add(" lda #0\n sta.l $7FFB96\n sep #$20\n.a8\n lda #$80\n sta.l $002100\n rep #$20\n.a16\n pld\n plb\n ply\n plx\n pla\n plp\n sec\n rtl")
    label("Bg8_CodeEnd")
    return _relax("\n".join(L) + "\n")


def emit(config: Mapping[str, object], helper_symbols: Mapping[str, object],
         publisher_text: str) -> str:
    """Emit a BG8 COW route around the relocated publisher's checked front.

    ``publisher_text`` must be the result of
    ``source_warm_presentation_native.relocate``.  The output preserves the
    accepted front end and tile-composition rows.  The legacy A000 section is
    retained for layout compatibility but is unreachable from the patched
    front; the new F100 body owns the route and adds explicit cold/owner guards.
    """
    if not isinstance(config, Mapping) or not isinstance(helper_symbols, Mapping):
        raise ValueError("BG8_INPUT_MAPPING")
    palette = _validate_config(config)
    symbols = _validate_symbols(helper_symbols)
    if not isinstance(publisher_text, str):
        raise ValueError("BG8_PUBLISHER_TEXT")
    required = ("OnlinePublish:", "OnlinePreflight:", "OnlineColorPointers:",
                "OnlineRowPointers:", "OnlineRowMask:", "AstraOpaqueTile:",
                ".org $A000", ".org $B000", ".org $E200", ".org $F000", ".org $AE40",
                "WarmEntry_Pose:", "WarmEntry_Reject:", "OnlineNoopComplete:",
                "OnlineReject:")
    for anchor in required:
        if publisher_text.count(anchor) != 1:
            raise ValueError(f"BG8_SOURCE_ANCHOR:{anchor}:{publisher_text.count(anchor)}")
    if ".bank 46" not in publisher_text or ".bank 57" in publisher_text:
        raise ValueError("BG8_RELOCATION_BANK")
    text = _entry_patch(publisher_text)
    # Preserve the image-index identity before pose metadata loads overwrite A.
    text = _once(
        text,
        "WarmEntry_Pose:\n.a16\n.i16\n asl a\n asl a\n asl a\n asl a\n asl a\n tax",
        f"WarmEntry_Pose:\n.a16\n.i16\n sta.l ${CONTROL+0x2C:06X}\n asl a\n asl a\n asl a\n asl a\n asl a\n tax",
        "POSE_KEY_ID",
    )
    text = apply_nonzero_bounds(text, config.get("nonzero_pose_bounds"))
    # The accepted Astra tile kernel produces five interleaved 16-byte planes.
    # This build's BG8 asset has a zero fifth plane; route its 64 useful bytes
    # into isolated scratch so the 10-plane predecessor's D680 staging is not
    # exposed to the PPU or a source-yield alias guard.
    a = text.index("AstraOpaqueTile:")
    # The relocated publisher may not carry the builder's synthetic section
    # labels.  The next real kernel boundary is stable and preserves any such
    # labels that happen to be present immediately before it.
    b = text.index(".org $F000", a)
    kernel = text[a:b]
    for old, new in (("$42D680", f"${STAGE:06X}"),
                     ("$42D690", f"${STAGE+0x10:06X}"),
                     ("$42D6A0", f"${STAGE+0x20:06X}"),
                     ("$42D6B0", f"${STAGE+0x30:06X}"),
                     ("$42D6C0", f"${STAGE+0x40:06X}")):
        if old not in kernel:
            raise ValueError(f"BG8_TILE_STAGE_DRIFT:{old}")
        kernel = kernel.replace(old, new)
    text = text[:a] + kernel + text[b:]
    # Preserve the retained A700-AE40 helper sections and place the new code
    # only after the final legacy section, avoiding a backwards .org overlap.
    if text.count(".org $AE40") != 1:
        raise ValueError("BG8_SOURCE_DRIFT:LEGACY_TAIL")
    overlay = config.get("tile_upload_batch_overlay_v2")
    if overlay is not None and overlay is not True:
        raise ValueError("BG8_BATCH_OVERLAY_CONFIG")
    text = text.rstrip() + "\n" + _body(symbols, palette,
        batch_limit=BATCH_OVERLAY_LIMIT if overlay else BATCH_LIMIT,
        batch_index=BATCH_OVERLAY_INDEX if overlay else BATCH_INDEX)
    if config.get("free_canonical_slot_reuse_v1") is True:
        # Import only for the opt-in experiment; the default and existing
        # overlay retain byte-for-byte emission and no module-side test imports.
        from source_warm_bg8_free_native import apply_free_canonical_reuse
        text = apply_free_canonical_reuse(text)
    if config.get("row_band_empty_tiles") is not None:
        from source_warm_bg8_band_native import apply_row_bands
        text = apply_row_bands(text, config["row_band_empty_tiles"])
    if text.count("Bg8_Begin:") != 1 or text.count("Bg8_Cold:") != 1:
        raise ValueError("BG8_EMIT_LABELS")
    return text


def plan_cow(current_refs: list[int], current_hashes: list[int],
             current_keys: list[tuple[int, int]],
             candidate_hashes: list[int],
             candidate_keys: list[tuple[int, int]],
             comparison_results: Mapping[tuple[int, int], bool] | None = None,
             *, padding_cells: int = 128,
             capacity: int = TILE_COUNT) -> dict[str, object]:
    """Small independent COW oracle used by tests and offline planning.

    Hash equality is only a candidate. Exact provenance equality is enough to
    reuse immutable source output; all other matches require the caller's
    full-byte comparator. The model reports comparator requests instead of
    pretending a hash proves equality.
    """
    if not (len(current_refs) == len(current_hashes) == len(current_keys) == capacity):
        raise ValueError("BG8_MODEL_TILE_EXTENT")
    if len(candidate_hashes) != len(candidate_keys):
        raise ValueError("BG8_MODEL_CANDIDATE_EXTENT")
    if not isinstance(padding_cells, int) or padding_cells < 0:
        raise ValueError("BG8_MODEL_PADDING")
    if any(not 0 <= int(x) <= 0xFFFF for x in current_refs + current_hashes + candidate_hashes):
        raise ValueError("BG8_MODEL_WORD_RANGE")
    refs = [v & 1 for v in current_refs]
    hashes = list(current_hashes)
    keys = list(current_keys)
    pending: list[int] = []
    uploads: list[int] = []
    full_compare: list[tuple[int, int]] = []
    comparison_results = comparison_results or {}
    for candidate_index, (query_hash, query_key) in enumerate(zip(candidate_hashes, candidate_keys)):
        if not isinstance(query_key, tuple) or len(query_key) != 2 or any(not isinstance(v, int) for v in query_key):
            raise ValueError("BG8_MODEL_KEY")
        selected = None
        for slot, (refs_word, hash_word) in enumerate(zip(refs, hashes)):
            if not refs_word or hash_word != query_hash:
                continue
            if keys[slot] == query_key:
                selected = slot
                break
            request = (slot, candidate_index)
            full_compare.append(request)
            if comparison_results.get(request, False):
                selected = slot
                break
        if selected is None:
            selected = next((s for s in range(capacity) if refs[s] == 0), None)
            if selected is None:
                return {"accepted": False, "deferred": True, "pending_map": [],
                        "uploads": uploads, "full_compare_requests": full_compare,
                        "refs_after_rollback": [v & 1 for v in current_refs]}
            uploads.append(selected)
            hashes[selected] = query_hash or 1
            keys[selected] = query_key
        refs[selected] |= 2
        pending.append(selected)
    # Pad map slots by repeating the first visible cell's already-owned tile.
    # This adds no new allocation/reference and reserves no physical slot.
    if padding_cells and not pending:
        raise ValueError("BG8_MODEL_PADDING_WITHOUT_VISIBLE_CELL")
    first_visible = pending[0] if pending else None
    while len(pending) < len(candidate_keys) + padding_cells:
        pending.append(first_visible)
    committed_refs = [1 if value & 2 else 0 for value in refs]
    return {"accepted": True, "deferred": False, "pending_map": pending,
            "uploads": uploads, "full_compare_requests": full_compare,
            "refs_after_commit": committed_refs}
