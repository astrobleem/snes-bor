"""Prepare one 8x8 Astra tile from an immutable source-RLE image.

The caller owns the renderer's direct page at $3400. The emitter reads the tile
index from DP+$18, uses the caller's image/control lease at $7E9400, and calls
the separately linked ``WarmRle_DecodeRow`` row authority. It does not publish
renderer state until the complete tile is prepared.

Private scratch is restricted to $7E9440..$7E94DF. The 8 decoded rows occupy
$7E8400..$7E93FF; cache identity is held in the caller's +$0A/+0C controls.
"""
from collections.abc import Mapping


CONTROL = 0x7E9400
CACHE = 0x7E8400
TILE = 0x7E9800
VALID_TAG = 0xB6E1


def emit(lut_cpu, control=CONTROL, cache=CACHE, tile=TILE, *, planes_cpu=None):
    """Return PASM for WarmTile_Prepare.

    ``lut_cpu`` is the 24-bit CPU address of 256 little-endian 10-bit map words.
    The map word contains the low eight CGRAM index bits and two high plane bits.
    Direction 0 mirrors the image, direction 1 uses its authored orientation.
    Carry reports malformed controls, a bad map word, or row-decoder rejection.
    """
    if isinstance(lut_cpu, bool) or not isinstance(lut_cpu, int) or not 0 <= lut_cpu <= 0xFFFFFF - 511:
        raise ValueError("WARM_TILE_LUT_EXTENT")
    if planes_cpu is not None and (isinstance(planes_cpu,bool) or not isinstance(planes_cpu,int)
                                  or not 0<=planes_cpu<=0x1000000-20480 or planes_cpu&1):
        raise ValueError('WARM_TILE_COLOR_PLANES_EXTENT')
    for name, address, extent in (("control", control, 0xE0), ("cache", cache, 4096), ("tile", tile, 96)):
        if isinstance(address, bool) or not isinstance(address, int) or not 0 <= address <= 0xFFFFFF - extent:
            raise ValueError("WARM_TILE_" + name.upper() + "_EXTENT")
    if control + 0xE0 > cache or cache + 4096 > tile or tile + 96 > control + 0x10000:
        # The standard lease is intentionally ordered; custom leases must remain
        # separate and must not alias emitter-owned control scratch.
        if any(a < b + n and b < a + m for a, m, b, n in (
            (control, 0xE0, cache, 4096), (control, 0xE0, tile, 96),
            (cache, 4096, tile, 96))):
            raise ValueError("WARM_TILE_MEMORY_OVERLAP")

    scratch = control + 0x40
    s = lambda offset: f"${scratch + offset:06X}"
    c = lambda offset: f"${control + offset:06X}"
    k = lambda offset: f"${cache + offset:06X}"
    t = lambda offset: f"${tile + offset:06X}"
    lines = []
    serial = 0

    def put(text):
        lines.extend(text.strip("\n").splitlines())

    def label(name):
        put(name + ":\n.a16\n.i16")

    def branch(op, target):
        nonlocal serial
        serial += 1
        skip = f"WarmTile_Skip{serial}"
        inverse = {"beq": "bne", "bne": "beq", "bcc": "bcs", "bcs": "bcc"}[op]
        put(f" {inverse} {skip}\n jmp {target}")
        label(skip)

    def good_exit():
        put(f" lda #${tile & 0xFFFF:04X}\n sta $08\n lda #${(tile >> 16) & 0xFFFF:04X}\n sta $0A\n lda #12\n sta $48\n lda #8\n sta $46\n lda #0\n sta $56")
        put(" plb\n pld\n ply\n plx\n pla\n plp\n clc\n rtl")

    lines.extend((
        "WarmTile_Prepare:", ".a16", ".i16", " php", " rep #$38", " pha", " phx", " phy", " phd", " phb",
        # Reject a non-renderer DP tile address before using any indexed state.
        " lda $18", " cmp #896",
    ))
    branch("bcs", "WarmTile_Fault")
    put(f' lda.l {c(0x0E)}\n cmp #2')
    branch('bcs','WarmTile_Fault')
    # Controls are a closed source-image descriptor, not actor/callback state.
    put(f" lda.l {c(4)}")
    branch("beq", "WarmTile_Fault")
    put(" cmp #512")
    branch("bcs", "WarmTile_Fault")
    put(f" lda.l {c(6)}")
    branch("beq", "WarmTile_Fault")
    put(f" lda.l {c(4)}\n cmp.l {c(0x28)}")
    branch("bne", "WarmTile_Fault")
    put(f" lda.l {c(6)}\n cmp.l {c(0x2A)}")
    branch("bne", "WarmTile_Fault")
    put(f" lda.l {c(8)}\n cmp #2")
    branch("bcs", "WarmTile_Fault")
    put(f" lda.l {c(0x23)}\n and #$00FF")
    branch("bne", "WarmTile_Fault")
    put(f" lda.l {c(0x22)}\n and #$00FF\n cmp #$00C0")
    branch("bcc", "WarmTile_Fault")
    put(f" lda.l {c(0x20)}\n and #$7FFF\n clc\n adc.l {c(0x24)}")
    branch("bcs", "WarmTile_Fault")
    put(" cmp #$8001")
    branch("bcs", "WarmTile_Fault")
    put(f" lda.l {c(0x24)}")
    branch("beq", "WarmTile_Fault")

    # Screen-space origin from tile index (32 columns, 8 pixels per tile).
    put(" lda $18\n and #$001F\n asl a\n asl a\n asl a")
    put(f" sta.l {s(0)}")  # screen X origin
    put(" lda $18\n and #$03E0\n lsr a\n lsr a")
    put(f" sec\n sbc.l {c(2)}\n sta.l {s(2)}")  # signed source Y base
    put(f" lda.l {c(4)}\n sta.l {s(4)}\n lda.l {c(6)}\n sta.l {s(6)}")
    # Decode a tile-row cache only when the root's image pin/tag is stale.
    put(f" lda.l {c(0x0C)}\n cmp #${VALID_TAG:04X}")
    branch("bne", "WarmTile_Decode")
    put(f" lda.l {c(0x0A)}\n cmp.l {s(2)}")
    branch("beq", "WarmTile_CacheReady")
    label("WarmTile_Decode")
    put(f" lda #0\n sta.l {c(0x0C)}\n lda #0\n sta.l {s(8)}")  # slot
    label("WarmTile_DecodeLoop")
    put(f" lda.l {s(2)}\n clc\n adc.l {s(8)}\n sta.l {s(10)}\n cmp.l {s(6)}")
    branch("bcs", "WarmTile_DecodeNext")
    put(f" lda.l {s(8)}\n tax\n lda.l {s(10)}\n jsl WarmRle_DecodeRow")
    branch("bcs", "WarmTile_Fault")
    label("WarmTile_DecodeNext")
    put(f" lda.l {s(8)}\n inc a\n sta.l {s(8)}\n cmp #8")
    branch("bne", "WarmTile_DecodeLoop")
    put(f" lda.l {s(2)}\n sta.l {c(0x0A)}\n lda #${VALID_TAG:04X}\n sta.l {c(0x0C)}")
    label("WarmTile_CacheReady")

    # Build eight 12-byte rows: duplicated presence mask, then five interleaved
    # little-endian plane pairs in Astra order. Out-of-image rows stay zero.
    put(f" lda #0\n sta.l {s(8)}\n sta.l {s(10)}")  # row, output byte offset
    label("WarmTile_RowLoop")
    put(f" lda.l {s(2)}\n clc\n adc.l {s(8)}\n cmp.l {s(6)}")
    branch("bcs", "WarmTile_RowClear")
    put(f" lda.l {s(10)}\n tax\n lda #0\n sta.l {t(0)},x\n sta.l {t(2)},x\n sta.l {t(4)},x\n sta.l {t(6)},x\n sta.l {t(8)},x\n sta.l {t(10)},x")
    put(f" lda #0\n sta.l {s(12)}\n sta.l {s(14)}")  # col, presence mask
    label("WarmTile_ColumnLoop")
    # sourceX = (tileX+column)-left. Unsigned compare against bounded width
    # clips both negative and positive out-of-image coordinates.
    put(f" lda.l {s(0)}\n clc\n adc.l {s(12)}\n sec\n sbc.l {c(0)}\n cmp.l {s(4)}")
    branch("bcs", "WarmTile_ColumnNext")
    put(f" sta.l {s(16)}")
    put(f" lda.l {c(8)}\n beq WarmTile_Mirror")
    put(f" lda.l {s(16)}\n sta.l {s(18)}\n jmp WarmTile_SourceIndex")
    label("WarmTile_Mirror")
    put(f" lda.l {s(4)}\n dec a\n sec\n sbc.l {s(16)}\n sta.l {s(18)}")
    label("WarmTile_SourceIndex")
    # Cache slot is the tile row (0..7); each slot has a 512-byte stride.
    put(f" lda.l {s(8)}")
    for _ in range(9):
        put(" asl a")
    put(f" clc\n adc.l {s(18)}\n tax\n lda.l {k(0)},x\n and #$00FF")
    branch("beq", "WarmTile_ColumnNext")
    put(f' sta.l {s(30)}\n lda.l {c(0x0E)}')
    branch('bne','WarmTile_SetPresence')
    put(f" lda.l {s(30)}\n asl a\n tax\n lda.l ${lut_cpu:06X},x\n sta.l {s(20)}\n and #$FC00")
    branch("bne", "WarmTile_Fault")
    put(f" lda.l {s(20)}")
    branch("beq", "WarmTile_ColumnNext")
    label('WarmTile_SetPresence')
    # Presence mask duplicates the 8-bit foreground row mask for the kernel.
    put(f" lda.l {s(12)}\n asl a\n tax\n lda.l WarmTile_PixelMasks,x\n ora.l {s(14)}\n sta.l {s(14)}")
    put(f' lda.l {c(0x0E)}')
    branch('bne','WarmTile_ColumnNext')
    if planes_cpu is not None:
        # One source index and column select five precomputed word
        # contributions. Preserve X across each output-row merge; no DBR or
        # additional renderer DP scratch is needed.
        put(f' lda.l {s(30)}\n asl a\n asl a\n asl a\n asl a\n sta.l {s(32)}\n lda.l {s(12)}\n asl a\n clc\n adc.l {s(32)}\n tax')
        for pair in range(5):
            put(f' phx\n lda.l ${planes_cpu+pair*4096:06X},x\n pha\n lda.l {s(10)}\n tax\n pla\n ora.l {t(2+pair*2)},x\n sta.l {t(2+pair*2)},x\n plx')
        put(' jmp WarmTile_ColumnNext')
    # Each map bit sets the matching bit in the pair word. Even planes live in
    # the low byte; odd planes live in the high byte of that pair.
    put(f" lda #0\n sta.l {s(22)}")  # plane byte offset (0,2,...,18)
    label("WarmTile_PlaneLoop")
    put(f" lda.l {s(22)}\n tax\n lda.l WarmTile_PlaneMasks,x\n and.l {s(20)}")
    branch("beq", "WarmTile_PlaneNext")
    put(f" lda.l {s(22)}\n and #2\n bne WarmTile_PlaneHigh")
    put(f" lda.l {s(12)}\n asl a\n tax\n lda.l WarmTile_PixelMasks,x\n and #$00FF\n sta.l {s(24)}\n jmp WarmTile_PlaneMerge")
    label("WarmTile_PlaneHigh")
    put(f" lda.l {s(12)}\n asl a\n tax\n lda.l WarmTile_PixelMasks,x\n and #$FF00\n sta.l {s(24)}")
    label("WarmTile_PlaneMerge")
    put(f" lda.l {s(22)}\n lsr a\n and #$FFFE\n sta.l {s(28)}\n lda.l {s(10)}\n clc\n adc #2\n adc.l {s(28)}\n tax\n lda.l {t(0)},x\n ora.l {s(24)}\n sta.l {t(0)},x")
    label("WarmTile_PlaneNext")
    put(f" lda.l {s(22)}\n clc\n adc #2\n sta.l {s(22)}\n cmp #20")
    branch("bne", "WarmTile_PlaneLoop")
    label("WarmTile_ColumnNext")
    put(f" lda.l {s(12)}\n inc a\n sta.l {s(12)}\n cmp #8")
    branch("bne", "WarmTile_ColumnLoop")
    # Duplicate the eight-bit presence mask into both bytes for the row kernel.
    put(f" lda.l {s(10)}\n tax\n lda.l {s(14)}\n sta.l {t(0)},x\n jmp WarmTile_RowNext")
    label("WarmTile_RowClear")
    # A clipped row is transparent: zero mask and five plane words.
    put(f" lda.l {s(10)}\n tax\n lda #0\n sta.l {t(0)},x\n sta.l {t(2)},x\n sta.l {t(4)},x\n sta.l {t(6)},x\n sta.l {t(8)},x\n sta.l {t(10)},x")
    label("WarmTile_RowNext")
    put(f" lda.l {s(10)}\n clc\n adc #12\n sta.l {s(10)}\n lda.l {s(8)}\n inc a\n sta.l {s(8)}\n cmp #8")
    branch("bne", "WarmTile_RowLoop")
    good_exit()
    label("WarmTile_Fault")
    put(" plb\n pld\n ply\n plx\n pla\n plp\n sec\n rtl")
    # Tables are 16-bit words because the renderer and linked LUT use A16.
    label("WarmTile_PixelMasks")
    put(" .dw $8080,$4040,$2020,$1010,$0808,$0404,$0202,$0101")
    label("WarmTile_PlaneMasks")
    put(" .dw $0001,$0002,$0004,$0008,$0010,$0020,$0040,$0080,$0100,$0200")
    return "\n".join(lines) + "\n"
