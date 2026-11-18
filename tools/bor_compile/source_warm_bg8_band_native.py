"""Optional exact-zero row-band shortcut before BG8 actor composition.

The table describes immutable source indices. A positive result only takes the
existing backdrop path; every cell scan, source-service point and queue remains.
"""
from collections.abc import Mapping


def _layout(spec):
    if not isinstance(spec, Mapping) or set(spec) != {
            'pose_table_cpu', 'pose_count', 'descriptor_stride', 'window_row_bytes'}:
        raise ValueError('BG8_BAND_LAYOUT')
    table, count = spec['pose_table_cpu'], spec['pose_count']
    if (type(table) is not int or type(count) is not int or
            not 0xC00000 <= table <= 0xFFFFFF or table & 1 or
            not 1 <= count <= 2047 or (table & 0xFFFF) + count * 8 > 0x10000 or
            type(spec['descriptor_stride']) is not int or spec['descriptor_stride'] != 8 or
            type(spec['window_row_bytes']) is not int or spec['window_row_bytes'] != 4):
        raise ValueError('BG8_BAND_LAYOUT')
    return table, count


def helper(spec):
    """A16/X16, fixed renderer DP; preserve A/X/Y/P except returned carry.

    Only DP $00..$07 is temporary. The source descriptor, cell index, bounds,
    queue, references and all source state are read-only. DBR/DP are untouched.
    Unsupported geometry or malformed table values returns C=0 to compose.
    """
    table, count = _layout(spec)
    lines = []
    serial = 0

    def put(text):
        lines.extend(text.strip().splitlines())

    def label(name):
        put(name + ':\n.a16\n.i16')

    def branch(op, target):
        nonlocal serial
        serial += 1
        skip = f'Bg8_BandSkip{serial}'
        inverse = {'beq':'bne','bne':'beq','bcc':'bcs','bcs':'bcc',
                   'bmi':'bpl','bpl':'bmi'}[op]
        put(f' {inverse} {skip}\n jmp {target}')
        label(skip)

    fallback = 'Bg8_BandCompose'
    empty = 'Bg8_BandRestoreEmpty'
    label('Bg8_TryEmptyBand')
    put(' php\n phx\n phy\n pha')
    # The same fixed domain as the existing nonzero-bound front end. Arithmetic
    # below stays signed-exact; invalid controls keep the original composition.
    put(' lda $18\n cmp #896')
    branch('bcs', fallback)
    put(' lda.l $43262C')
    put(f' cmp #{count}')
    branch('bcs', fallback)
    put(' asl a\n asl a\n asl a\n tax')
    for at, upper in ((0x7E9404, 512), (0x7E9406, 256)):
        put(f' lda.l ${at:06X}')
        branch('beq', fallback)
        put(f' cmp #{upper}')
        branch('bcs', fallback)
    for offset, at in ((4, 0x7E9404), (6, 0x7E9406)):
        put(f' lda.l ${table+offset:06X},x\n cmp.l ${at:06X}')
        branch('bne', fallback)
    put(' lda.l $7E9408\n cmp #2')
    branch('bcs', fallback)
    for axis, at, low, high in (('X',0x7E9400,-512,512), ('Y',0x7E9402,-256,256)):
        ok = 'Bg8_BandOrigin' + axis
        put(f' lda.l ${at:06X}\n cmp #{high}')
        branch('bcc', ok)
        put(f' cmp #${low & 0xFFFF:04X}')
        branch('bcc', fallback)
        label(ok)
    put(f' lda.l ${table:06X},x\n sta $00\n lda.l ${table+2:06X},x\n cmp #$00C0')
    branch('bcc', fallback)
    put(' cmp #$0100')
    branch('bcs', fallback)
    put(' sta $02\n lda.l $7E9406\n clc\n adc #7\n sta $06')
    # Windows cover source y=-7..height-1, each record {minX,maxXExclusive}.
    # Unsigned rejection also handles a source y below -7.
    put(' lda $18\n and #$03E0\n lsr a\n lsr a\n sec\n sbc.l $7E9402\n clc\n adc #7\n cmp $06')
    branch('bcs', empty)
    put(' asl a\n asl a\n tay\n lda [$00],y\n sta $04\n iny\n iny\n lda [$00],y\n sta $06')
    put(' ora $04')
    branch('beq', empty)
    put(' lda $04\n cmp $06')
    branch('bcs', fallback)
    put(' lda.l $7E9404\n cmp $06')
    branch('bcc', fallback)
    put(' lda.l $7E9408')
    branch('bne', 'Bg8_BandOriented')
    put(' lda.l $7E9404\n sec\n sbc $06\n pha\n lda.l $7E9404\n sec\n sbc $04\n sta $06\n pla\n sta $04')
    label('Bg8_BandOriented')
    # Convert to clipped screen bounds before unsigned comparisons. The full
    # raster origin and width own the mirror; no crop-relative origin is used.
    put(' lda $04\n clc\n adc.l $7E9400')
    branch('bpl', 'Bg8_BandLowerPositive')
    put(' lda #0')
    label('Bg8_BandLowerPositive')
    put(' cmp #256')
    branch('bcs', empty)
    put(' sta $04\n lda $06\n clc\n adc.l $7E9400')
    branch('bmi', empty)
    branch('beq', empty)
    put(' cmp #256')
    branch('bcc', 'Bg8_BandUpperClipped')
    put(' lda #256')
    label('Bg8_BandUpperClipped')
    put(' sta $06\n lda $18\n and #31\n asl a\n asl a\n asl a\n cmp $06')
    branch('bcs', empty)
    put(' clc\n adc #8\n cmp $04')
    branch('bcc', empty)
    branch('beq', empty)
    label(fallback)
    put(' pla\n ply\n plx\n plp')
    label('Bg8_BandReturnCompose')
    put(' clc\n rts')
    label(empty)
    put(' pla\n ply\n plx\n plp')
    label('Bg8_BandEmpty')
    put(' sec\n rts')
    label('Bg8_BandHelperEnd')
    return '\n'.join(lines) + '\n'


def apply_row_bands(text, spec):
    if spec is None:
        return text
    _layout(spec)
    if not isinstance(text, str) or 'Bg8_TryEmptyBand:' in text:
        raise ValueError('BG8_BAND_SOURCE_DRIFT')
    old = 'Bg8_PoseInside:\n.a16\n.i16\n clc\n rts'
    if text.count(old) != 1 or text.count('OnlinePreflight:') != 1:
        raise ValueError('BG8_BAND_SOURCE_DRIFT')
    route = ' jmp Bg8_ComposePose'
    if text.count(route) != 1:
        raise ValueError('BG8_BAND_SOURCE_DRIFT')
    # Keep the current-backdrop fast path's original outside-rectangle domain.
    # A zero band inside that rectangle uses the existing staged backdrop/hash
    # path, including exact resident lookup, rather than widening that fast path.
    text = text.replace(route,
        ' jsr Bg8_TryEmptyBand\n bcc Bg8_BandDoCompose\n jmp Bg8_CopyBackdrop\n'
        'Bg8_BandDoCompose:\n.a16\n.i16\n jmp Bg8_ComposePose', 1)
    # Entry jumps to Bg8_Begin before this helper. It fits in the checked front
    # section; no code is appended to the almost-full F100 body.
    return text.replace('OnlinePreflight:', helper(spec) + 'OnlinePreflight:', 1)
