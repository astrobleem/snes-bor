"""BG8-only specialized warm tile emitter.

The generic five-pair emitter remains the default. The specialized path is
explicitly guarded by the fixed renderer lease and exact 8-bit LUT/table proof.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
from source_warm_tile_native import emit as emit_five_pair

CONTROL = 0x7E9400
CACHE = 0x7E8400
TILE = 0x7E9800

PAIR_BYTES = 4096
PAIRS = 5
TABLE_BYTES = PAIR_BYTES * PAIRS


def build_plane_table(lut):
    """Build the emitter's 5x4096 contribution table for 8-bit CGRAM values."""
    if len(lut) != 256:
        raise ValueError("BG8_LUT_EXTENT")
    table = bytearray(TABLE_BYTES)
    for index, value in enumerate(lut):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFF:
            raise ValueError("BG8_LUT_VALUE")
        if index == 0:
            if value:
                raise ValueError("BG8_TRANSPARENT_LUT")
            continue
        for col in range(8):
            bit = 0x80 >> col
            for plane in range(8):
                if value & (1 << plane):
                    pair = plane // 2
                    contribution = bit << (8 if plane & 1 else 0)
                    offset = pair * PAIR_BYTES + index * 16 + col * 2
                    word = int.from_bytes(table[offset:offset + 2], "little") | contribution
                    table[offset:offset + 2] = word.to_bytes(2, "little")
    return bytes(table)


def validate_bg8_table(table):
    if not isinstance(table, (bytes, bytearray, memoryview)) or len(table) != TABLE_BYTES:
        raise ValueError("BG8_PLANE_TABLE_EXTENT")
    if any(table[4 * PAIR_BYTES:]):
        raise ValueError("BG8_FIFTH_PAIR_NONZERO")
    return bytes(table)


def validate_bg8_lut(lut_bytes):
    """Require the production BG8 palette LUT shape: 256 byte indices."""
    if not isinstance(lut_bytes, (bytes, bytearray, memoryview)) or len(lut_bytes) != 512:
        raise ValueError("BG8_LUT_EXTENT")
    words = [int.from_bytes(lut_bytes[i:i + 2], "little")
             for i in range(0, len(lut_bytes), 2)]
    if words[0] != 0 or any(value > 0xFF for value in words):
        raise ValueError("BG8_LUT_NOT_8BIT")
    return words



def emit_bg8(lut_cpu, planes_cpu, lut_bytes, table_bytes, control=CONTROL,
             cache=CACHE, tile=TILE):
    """Emit the BG8-specialized helper after validating its exact table domain."""
    if (control, cache, tile) != (CONTROL, CACHE, TILE):
        raise ValueError("BG8_FIXED_LEASE")
    lut_words = validate_bg8_lut(lut_bytes)
    table = validate_bg8_table(table_bytes)
    if build_plane_table(lut_words) != table:
        raise ValueError("BG8_TABLE_LUT_MISMATCH")
    asm = emit_five_pair(lut_cpu, control=control, cache=cache, tile=tile,
                         planes_cpu=planes_cpu)

    prologue = " phb\n lda $18"
    replacement = " phb\n sep #$20\n.a8\n lda #$7E\n pha\n plb\n rep #$20\n.a16\n lda $18"
    if asm.count(prologue) != 1:
        raise ValueError("BG8_PROLOGUE_TEMPLATE")
    asm = asm.replace(prologue, replacement, 1)

    clear_row = "\n".join((
        f" lda.l ${control + 0x4A:06X}",
        " tax",
        " lda #0",
        f" sta.l ${tile:06X},x",
        f" sta.l ${tile + 2:06X},x",
        f" sta.l ${tile + 4:06X},x",
        f" sta.l ${tile + 6:06X},x",
        f" sta.l ${tile + 8:06X},x",
        f" sta.l ${tile + 10:06X},x",
        f" lda #0",
        f" sta.l ${control + 0x4C:06X}",
        f" sta.l ${control + 0x4E:06X}",
    ))
    clear_with_y = "\n".join((
        f" lda.l ${control + 0x4A:06X}",
        " tax",
        " lda #0",
        f" sta.l ${tile:06X},x",
        f" sta.l ${tile + 2:06X},x",
        f" sta.l ${tile + 4:06X},x",
        f" sta.l ${tile + 6:06X},x",
        f" sta.l ${tile + 8:06X},x",
        f" sta.l ${tile + 10:06X},x",
        f" lda.l ${control + 0x4A:06X}",
        " tay",
        f" lda #0",
        f" sta.l ${control + 0x4C:06X}",
        f" sta.l ${control + 0x4E:06X}",
    ))
    if asm.count(clear_row) != 1:
        raise ValueError("BG8_ROW_TEMPLATE")
    asm = asm.replace(clear_row, clear_with_y, 1)

    pattern = re.compile(
        r" phx\n lda\.l \$(?P<plane>[0-9a-f]{6}),x\n pha\n"
        r" lda\.l \$[0-9a-f]{6}\n tax\n pla\n"
        r" ora\.l \$(?P<tile>7e980[2468a]),x\n"
        r" sta\.l \$(?P=tile),x\n plx", re.IGNORECASE)
    matches = list(pattern.finditer(asm))
    if len(matches) != 5:
        raise ValueError(f"BG8_MERGE_TEMPLATE:{len(matches)}")

    def simplify(match):
        plane = int(match.group("plane"), 16)
        out = int(match.group("tile"), 16)
        pair = (out - 0x7E9802) // 2
        expected = planes_cpu + pair * PAIR_BYTES
        if plane != expected:
            raise ValueError("BG8_PLANE_ORDER")
        if pair == 4:
            return ""  # the row clear keeps pair five exactly zero
        return (f" lda.l ${plane:06X},x\n"
                f" ora ${out & 0xFFFF:04X},y\n"
                f" sta ${out & 0xFFFF:04X},y")

    asm = pattern.sub(simplify, asm)
    return asm

def integrate_helper(text, lut_cpu, planes_cpu, lut_bytes, table_bytes):
    """Replace exactly the checked-in tile helper within a complete helper source.

    The generic helper bytes and the original prefix/suffix are otherwise left
    untouched. This also keeps earlier decoder/service labels at their original
    addresses when the row decoder precedes WarmTile_Prepare in the input.
    """
    if not isinstance(text, str):
        raise TypeError("BG8_HELPER_TEXT")
    old = emit_five_pair(lut_cpu, control=CONTROL, cache=CACHE, tile=TILE,
                         planes_cpu=planes_cpu)
    if text.count(old) != 1:
        raise ValueError("BG8_OLD_HELPER_CARDINALITY")
    tile_at = text.index("WarmTile_Prepare:")
    decoder_at = text.find("WarmRle_DecodeRow:")
    publisher_at = text.find("WarmPublish:")
    if decoder_at >= 0 and not decoder_at < tile_at:
        raise ValueError("BG8_HELPER_LABEL_ORDER")
    if publisher_at >= 0 and decoder_at >= 0 and not publisher_at < decoder_at:
        raise ValueError("BG8_HELPER_LABEL_ORDER")
    if text.index(old) != tile_at and text[text.index(old):].find("WarmTile_Prepare:") != 0:
        # Template cardinality already protects the content; this branch makes
        # accidental unrelated replacement fail closed if section labels drift.
        raise ValueError("BG8_TILE_SECTION_ANCHOR")
    new = emit_bg8(lut_cpu, planes_cpu, lut_bytes, table_bytes,
                   CONTROL, CACHE, TILE)
    return text.replace(old, new, 1)
