"""Astra's opaque phase rows integrated into the existing component producer.

The scalar emitter remains the oracle. This transform changes gathering and
encoding, not the source services, pixel authority, PPU layout or NMI ownership.
"""
import hashlib
import json
import struct
from pathlib import Path
from astra_opaque_kernel import emit
from m4_live_ground_owner import SNAPSHOT
from m4_bounded_component_publisher import READY,DISPLAY_EPOCH

KEY=0x42d6d0
# The bounded ROM has immutable palette/layer and camera authorities. Keep
# their generation words explicit in the committed key; no camera/underlay
# mutation API is admitted by this producer.
IMMUTABLE_GENERATIONS=((0x42d6ec,1),(0x42d6ee,1),(0x42d6f0,0))


def capacity_bound(phases):
    import numpy as np
    manifest=json.loads((phases/'manifest.json').read_text());bounds={}
    for role,atlas in manifest['frames'].items():
        count=0
        for phase in atlas['phases']:
            record=np.frombuffer((phases/phase['path']).read_bytes(),dtype='<u2').reshape(phase['row_count'],-1,6)
            ys,xs=np.nonzero(record[:,:,0])
            count=max(count,max(len({((int(y)+shift)//8,int(x)) for y,x in zip(ys,xs)}) for shift in range(8)))
        bounds[role]=count
    maximum=manifest['backdrop_tiles']+max(bounds.values())
    if maximum>768:raise ValueError('OPAQUE_TARGET_RESIDENCY_CAPACITY')
    return dict(source_coverage_tile_bounds=bounds,maximum_required_pairs=maximum,capacity=768)


def transform(phases,warm=False,assets=None,occupancy=None,tile_fusion=False,direct_pair_dma=False,rect_map_diff=False):
    if rect_map_diff and not (warm and occupancy is not None and tile_fusion and direct_pair_dma):raise ValueError("RECT_MAP_CAPABILITY_DEPENDENCIES")
    manifest=json.loads((phases/'manifest.json').read_text())
    capacity_bound(phases)
    def apply(lines,rom,authority,sy):
        def put(at,data):
            if any(rom[at:at+len(data)]):raise ValueError('OPAQUE_ASSET_ROM_LEASE')
            rom[at:at+len(data)]=data
        cursor=0x2b0000;tables=[]
        for frame in authority['frames']:
            f=manifest['frames'][frame['role']];table=bytearray()
            for phase in f['phases']:
                data=(phases/phase['path']).read_bytes()
                if hashlib.sha256(data).hexdigest()!=phase['sha256']:raise ValueError('OPAQUE_PHASE_IDENTITY')
                address=0xc00000+cursor;put(cursor,data);cursor+=len(data)
                table+=address.to_bytes(3,'little')+bytes(1)+struct.pack('<2H',phase['row_stride'],phase['row_count'])
            tables.append(table)
        if cursor>0x330000:raise ValueError('OPAQUE_PHASE_BANK_CAPACITY')
        put(0x330000,(phases/'backdrop-rows.bin').read_bytes())
        put(0x340000,(phases/'foreground-masks.bin').read_bytes())
        for i,t in enumerate(tables):put(0x342000+i*64,t)
        def splice(start,end,replacement):
            a=lines.index(start);b=lines.index(end,a)
            lines[a:b]=replacement
        def before(label,new):
            at=lines.index(label);lines[at:at]=new
        # This private fixed-camera scene has immutable layer/palette generation.
        # Stage and the established snapshot/lifetime owners remain guards.
        check=[]
        for name,value in (('SourceWorldTick4086_Ready',0xb4d5),('SourceSelf4086_Ready',0xb4f6),('SourceLifecycle4086_Ready',0xb4fb),('VmSourceWorld_Level',1)):
            label='OpaqueGuard_'+name
            check +=[f' lda.l {sy[name]}',f' cmp #{value}',f' beq {label}',' jmp OnlineReject',label+':','.a16','.i16']
        before(f' lda.l {SNAPSHOT+84}',check)
        # Capability/lease validation precedes the projected-picture fast path.
        keys=[SNAPSHOT+o for o in (80,84,86,28,54,62)]+[0x433830,sy['SourceWorldTick4086_Ready'],sy['VmSourceWorld_Level']]
        for i,frame in enumerate(authority['frames']):
            a=lines.index(f'OnlineFrame{i}:');b=lines.index(' jmp OnlinePreflight',a)
            f=manifest['frames'][frame['role']]
            setup=[' lda $00',' clc',f' adc #{f["crop_x"]}',' pha',' and #7',' asl a',' asl a',' asl a',' tax',
                ' pla',' cmp #$8000',' ror a',' cmp #$8000',' ror a',' cmp #$8000',' ror a',' sta $4A',
                ' lda $02',' clc',f' adc #{f["crop_y"]}',' sta $4C',
                f' lda.l ${0xf42000+i*64:06X},x',' sta $50',f' lda.l ${0xf42002+i*64:06X},x',' sta $52',
                f' lda.l ${0xf42004+i*64:06X},x',' sta $48',f' lda #{f["height"]}',' sta $46',
                f' lda.l {READY}',' cmp #$B4B8',f' bne OnlineChanged{i}']
            for k,at in enumerate(keys):setup +=[f' lda.l {at}',f' cmp.l {KEY+k*2}',f' bne OnlineChanged{i}']
            for at,generation in IMMUTABLE_GENERATIONS:setup +=[f' lda #{generation}',f' cmp.l {at}',f' bne OnlineChanged{i}']
            setup+=[' jmp OnlineNoop',f'OnlineChanged{i}:','.a16','.i16']
            lines[b:b]=setup
        at=lines.index('OnlineMarkDirty:')+3
        lines[at:at]=[' jsr OnlineCoverage',' cmp #0',' bne OnlineHasCoverage',' jmp OnlineUnchanged','OnlineHasCoverage:','.a16','.i16']
        # Only tiles with effective source coverage get actor storage.
        start=lines.index('OnlineTile:');finish=lines.index('OnlineTransfer:',start)
        original=lines[start:finish]
        # The old allocated map is the preflight authority; zero-coverage cells
        # retain the exact restored backdrop and never invoke the row kernel.
        replacement=['OnlineTile:','.a16','.i16',' jsr OnlineCoverage',' cmp #0',' bne OnlineComposeTile',' jmp OnlineTileNext',
            'OnlineComposeTile:','.a16','.i16',' lda $18',' asl a',' tax',' lda.l $42C000,x',' sta $2C',
            ' jsr OnlineRowPointers',' lda #0',' sta $1E','OnlineRow:','.a16','.i16',' jsr OnlineRowMask',
            ' lda $08',' clc',' adc #2',' sta $3C',' lda $0A',' adc #0',' sta $3E',
            ' lda $1E',' asl a',' tax',' jsl AstraOpaqueRow',' jsr OnlineStepRow',
            ' inc $1E',' lda $1E',' cmp #8',' bcc OnlineRow',
            'OnlineEncode:','.a16','.i16']
        lines[start:finish]=replacement
        # Insert a skip target after both tile DMA fences, before loop advance.
        at=lines.index('OnlineDmaDone2:');at=lines.index(' lda $18',at)
        lines[at:at]=['OnlineTileNext:','.a16','.i16']
        # Keep last SUCCESSFUL key, not the last attempted snapshot/epoch.
        at=lines.index('OnlineComplete:')+3
        lines[at:at]=[s for k,address in enumerate(keys) for s in (f' lda.l {address}',f' sta.l {KEY+k*2}')]
        at=lines.index('OnlineComplete:')+3
        lines[at:at]=[s for address,generation in IMMUTABLE_GENERATIONS for s in (f' lda #{generation}',f' sta.l {address}')]
        before('OnlineReject:',[
            'OnlineNoop:','.a16','.i16',f' lda.l {SNAPSHOT+144}',f' sta.l {DISPLAY_EPOCH}',
            'OnlineNoopComplete:','.a16','.i16',
            ' pld',' plb',' ply',' plx',' pla',' plp',' clc',' rtl'])
        routines=['.org $C000',
            # Pointer arithmetic is 24-bit. Source stride is row bytes, NOT
            # original pixel width; it is stepped once per output row.
            'OnlineRowPointers:','.a16','.i16',' lda $18',' and #31',' sec',' sbc $4A',' sta $5C',
            ' asl a',' clc',' adc $5C',' asl a',' asl a',' sta $5C', # chunk *12
            ' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' asl a',' asl a',' asl a',' sec',' sbc $4C',' sta $56',
            ' bpl OnlineRowPositive',' lda #0','OnlineRowPositive:','.a16','.i16',
            ' sep #$20','.a8',' sta.l $004202',' lda $48',' sta.l $004203',' nop',' nop',' nop',' nop',
            ' rep #$20','.a16',' lda.l $004216',' clc',' adc $5C',' clc',' adc $50',' sta $08',' lda $52',' adc #0',' sta $0A',
            ' lda $18',' asl a',' tax',' lda.l $E18000,x',' sta $5C',' asl a',' asl a',' clc',' adc $5C',' asl a',' asl a',' asl a',' asl a',' sta $0C', # id*80
            ' lda #$F3',' sta $0E',' lda $18',' asl a',' asl a',' asl a',' sta $54',' rts',
            'OnlineRowMask:','.a16','.i16',' lda #0',' sta $32',' lda $56',' cmp $46',' bcs OnlineMaskDone',
            ' ldx $54',' sep #$20','.a8',' lda.l $F40000,x',' rep #$20','.a16',' and #255',' eor #255',' sta $32',' xba',' ora $32',
            ' ldy #0',' and [$08],y',' sta $32','OnlineMaskDone:','.a16','.i16',' rts',
            'OnlineStepRow:','.a16','.i16',' lda $56',' bmi OnlineStepNegative',
            ' lda $08',' clc',' adc $48',' sta $08',' lda $0A',' adc #0',' sta $0A',
            'OnlineStepNegative:','.a16','.i16',' inc $56',' inc $54',' lda $0C',' clc',' adc #10',' sta $0C',' lda $0E',' adc #0',' sta $0E',' rts',
            'OnlineCoverage:','.a16','.i16',' jsr OnlineRowPointers',' lda #0',' sta $5A',' sta $58',
            'OnlineCoverageRow:','.a16','.i16',' jsr OnlineRowMask',' lda $32',' ora $5A',' sta $5A',' jsr OnlineStepRow',
            ' inc $58',' lda $58',' cmp #8',' bcc OnlineCoverageRow',' lda $5A',' rts',
            '.org $E000',*emit().assembly.splitlines()]
        before('.org $F000',routines)
        if warm:
            from m4_opaque_warm_publisher import apply as retain
            lines=retain(lines,rom,authority,sy,assets)
        if occupancy is not None:
            if not warm:raise ValueError('OCCUPANCY_REQUIRES_WARM_RESIDENCY')
            from m4_occupancy_publisher import apply as presence
            lines=presence(lines,rom,authority,phases,occupancy)
        if tile_fusion:
            if not warm or occupancy is None:raise ValueError('FUSED_TILE_REQUIRES_OCCUPANCY_WARM')
            from tile_fusion import fuse
            from assemble_sanity import audit_asm
            audit_asm()
            lines=fuse(lines)
        if direct_pair_dma:
            if not warm or occupancy is None or not tile_fusion:raise ValueError('DIRECT_PAIR_REQUIRES_OCCUPANCY_WARM_FUSION')
            from direct_pair_dma import transform as direct
            lines=direct(lines)
        if rect_map_diff:
            from rect_map_opt import transform as rectangle
            lines=rectangle(lines)
        return lines
    return apply
