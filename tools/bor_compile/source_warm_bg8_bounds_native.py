"""BG8-only conservative tile bounds from immutable source nonzero indices.

The full raster origin, dimensions, RLE rows and mirror operation stay intact.
Only the four publisher tile bounds change. Empty or unsupported descriptors
keep the original full-raster rectangle. No RAM lease or per-cell yield changes.
"""
from collections.abc import Mapping


def apply_nonzero_bounds(text: str, spec: Mapping | None) -> str:
    if spec is None:
        return text
    if not isinstance(spec, Mapping) or set(spec) != {"metadata_rows_cpu", "pose_count"}:
        raise ValueError("BG8_NONZERO_CONFIG")
    meta, count = spec["metadata_rows_cpu"], spec["pose_count"]
    if (type(meta) is not int or type(count) is not int or
            not 0xC00000 <= meta <= 0xFFFFFF or not 1 <= count <= 2047 or
            (meta & 0xFFFF) + count * 32 > 0x10000):
        raise ValueError("BG8_NONZERO_METADATA_WINDOW")
    begin, end = text.index("OnlinePublish:"), text.index("OnlinePreflight:")
    front = text[begin:end]
    # Bind to the same immutable 32-byte pose rows used by the admitted front.
    for offset, target in ((8, 0x7E9404), (10, 0x7E9406)):
        needle = f"lda.l ${meta+offset:06X},x\n sta.l ${target:06X}"
        if front.count(needle) != 1:
            raise ValueError("BG8_NONZERO_FRONT_METADATA")
    for needle in ("sta.l $43262C", "jmp Bg8_Begin"):
        if front.count(needle) != 1:
            raise ValueError("BG8_NONZERO_FRONT_ROUTE")

    lines = []
    serial = 0

    def put(code):
        lines.extend(code.splitlines())

    def label(name):
        put(name + ":\n.a16\n.i16")

    def branch(op, target):
        nonlocal serial
        serial += 1
        skip = f"Bg8_NonzeroSkip{serial}"
        inverse = {"beq": "bne", "bne": "beq", "bcc": "bcs", "bcs": "bcc"}[op]
        put(f" {inverse} {skip}\n jmp {target}")
        label(skip)

    fallback = "Bg8_NonzeroBoundsFallback"
    label("Bg8_SetNonzeroBounds")
    put(f" cpx #{count*32}")
    branch("bcs", fallback)
    put(" txa\n and #31")
    branch("bne", fallback)
    for at, maximum in ((0x7E9404, 512), (0x7E9406, 256)):
        put(f" lda.l ${at:06X}")
        branch("beq", fallback)
        put(f" cmp #{maximum}")
        branch("bcs", fallback)
    put(" lda.l $7E9408\n cmp #2")
    branch("bcs", fallback)
    # Domain guards make every subsequent signed sum exact in 16 bits.
    # Out-of-domain origins retain the existing conservative full bounds.
    for axis, at, low, high in (("X", 0x7E9400, -512, 512),
                                ("Y", 0x7E9402, -256, 256)):
        ok = f"Bg8_NonzeroOrigin{axis}"
        put(f" lda.l ${at:06X}\n cmp #{high}")
        branch("bcc", ok)
        put(f" cmp #${low & 0xFFFF:04X}")
        branch("bcc", fallback)
        label(ok)
    # Validate both axes before writing any original tile bound. Equality
    # denotes an empty image and takes the original full-composition path.
    for lower, upper, extent in ((16, 20, 0x7E9404), (18, 22, 0x7E9406)):
        put(f" lda.l ${meta+lower:06X},x\n cmp.l ${meta+upper:06X},x")
        branch("bcs", fallback)
        put(f" lda.l ${meta+upper:06X},x\n cmp.l ${extent:06X}")
        ok = f"Bg8_NonzeroExtent{lower}"
        branch("bcc", ok)
        branch("bne", fallback)
        label(ok)

    for target, axis, lower, upper, end_edge, limit in (
            (0x10, "X", 16, 20, False, 256),
            (0x12, "X", 16, 20, True, 256),
            (0x14, "Y", 18, 22, False, 224),
            (0x16, "Y", 18, 22, True, 224)):
        ready = f"Bg8_NonzeroCoordinate{target}"
        if axis == "X":
            normal = f"Bg8_NonzeroNormal{target}"
            put(" lda.l $7E9408")
            branch("bne", normal)
            # Mirroring is about the full source width, never the crop.
            opposite = lower if end_edge else upper
            put(f" lda.l $7E9404\n sec\n sbc.l ${meta+opposite:06X},x\n jmp {ready}")
            label(normal)
        edge = upper if end_edge else lower
        put(f" lda.l ${meta+edge:06X},x")
        label(ready)
        origin = 0x7E9400 if axis == "X" else 0x7E9402
        put(f" clc\n adc.l ${origin:06X}")
        if end_edge:
            put(" dec a")
        positive = f"Bg8_NonzeroPositive{target}"
        clipped = f"Bg8_NonzeroClipped{target}"
        put(f" bpl {positive}\n lda #0")
        label(positive)
        put(f" cmp #{limit}")
        branch("bcc", clipped)
        put(f" lda #{limit-1}")
        label(clipped)
        put(f" lsr a\n lsr a\n lsr a\n sta ${target:02X}")
    label("Bg8_NonzeroBoundsApplied")
    put(" sec\n rts")
    label(fallback)
    put(" clc\n rts")
    helper = "\n".join(lines) + "\n"
    # The jump skips the helper except for the one local call at entry.
    front = front.replace("jmp Bg8_Begin", "jsr Bg8_SetNonzeroBounds\n jmp Bg8_Begin\n" + helper, 1)
    return text[:begin] + front + text[end:]
