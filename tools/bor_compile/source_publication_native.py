"""Compiler-owned native source publication backend.

Inputs are explicit model/frame/map admission and the audited runtime symbol ABI.
This module emits native transfer, snapshot and compositor code; it performs no
emulator execution, fixture model selection, or certificate promotion.
"""
import json
import re
import struct
from pathlib import Path
from model_ir import parse_model
from actor_lowering import lower_model
from source_publication_set import compile_set, PublicationResourceBlocked
from source_publication_codegen import capture_code
from source_palette_packet import link_packet_palettes
from frame_publication import pack_descriptor

ROOT=Path(__file__).resolve().parents[2]


def db(data):
    return '\n'.join('    .db '+','.join(str(v) for v in data[i:i+16])
                     for i in range(0,len(data),16))+'\n'


def hook_render_live(depth):
    """Route exactly one accepted production render call through publication."""
    start='Character_RenderPass__render_live:\n'
    end='Character_RenderPass__render_done:\n'
    if depth.count(start)!=1 or depth.count(end)!=1:
        raise ValueError('PUBLICATION_RENDER_HOOK: missing/duplicate live block')
    before,body=depth.split(start)
    live,after=body.split(end)
    accepted=('Character_RenderFrame','StageTimerHost_RenderFrame')
    calls=list(re.finditer(r'(?m)^[ \t]*jsl[ \t]+(\w+)[ \t]*(?:;[^\n]*)?$',live))
    accepted_calls=[call for call in calls if call[1] in accepted]
    if len(accepted_calls)!=1:
        raise ValueError('PUBLICATION_RENDER_HOOK: expected exactly one accepted live call')
    target=accepted_calls[0][1]
    all_calls=re.findall(r'(?m)^[ \t]*jsl[ \t]+(Character_RenderFrame|StageTimerHost_RenderFrame)\b',depth)
    if all_calls!=[target]:
        raise ValueError('PUBLICATION_RENDER_HOOK: duplicate accepted render call')
    # Replace the accepted renderer call itself.  The live block also owns
    # hide/set-sprite calls before and after it; selecting calls[0] routes
    # empty actors into the publisher and leaves live actors on the legacy
    # renderer.
    call=accepted_calls[0]
    live=live[:call.start(1)]+'S7Publisher_RenderOrCompat'+live[call.end(1):]
    return before+start+live+end+after,target


def bind_compat_renderer(code,target):
    """Late binding: owner-admission insertion must see the legacy template first."""
    legacy='    plp\n    jml Character_RenderFrame\n'
    if target not in ('Character_RenderFrame','StageTimerHost_RenderFrame') or code.count(legacy)!=1:
        raise ValueError('PUBLICATION_COMPAT_HOOK: unexpected compatibility template')
    return code.replace(legacy,f'    plp\n    jml {target}\n')


def emit_code(sym,roster,role,chunks,transfers,payload,*,stream=False,_defer_compat=False):
    """Native template from linked data; no fixture model or image lookup."""
    code=f'.bank 31\n.org $8000\nS7Pub_State = $7F8C00\nS7Pub_Transfers = $1FB000\nS7Pub_TransferCount = 9\n'
    native=(ROOT/'src/core/actor_source_publisher.pasm').read_text()
    code+=native+'\n'
    code+='S7Publisher_Capture:\n    rep #$30\n    .a16\n    .i16\n    jsl Depth_Sort_ComputeOrder\n    phd\n'
    for slot in range(6):
        ctx=0x1900+256*slot;row=133*slot;dest=0x7f8c20+32*slot
        nxt=f'S7Publisher_Capture_S{slot}_done'
        code+=f'''    lda #0
    sta.l ${dest+6:06X}
    lda.l S7Pub_State+6
    beq {nxt}
    lda.l S6Bridge_Policy+{row}
    and #255
    cmp #3
    bcs {nxt}
    lda #${ctx:04X}
    tcd
    lda $F6
    beq {nxt}
    lda $FC
    bne {nxt}
    lda.l $7E0A00+CHAR_ROSTER_INDEX+{row}
    and #255
    cmp #{roster}
    bne {nxt}
    lda $E4
    cmp #{role}
    bne {nxt}
    lda $06
{('    cmp #6' + chr(10) + '    bcs ' + nxt) if stream else ('    bne '+nxt)}
    lda.l $7E0A00+CHAR_MAP_INDEX+{row}
    and #255
    bne {nxt}
    lda #{row}
    sta $7A
    lda $14
    jsl S6Bridge_ProjectPolicy
    sec
    sbc.l Screen_PosX
    sta.l ${dest:06X}
    lda $16
    jsl S6Bridge_ProjectPolicy
    sec
    sbc $18
    sta.l ${dest+2:06X}
    lda $1A
    sta.l ${dest+4:06X}
    lda $E4
    sta.l ${dest+8:06X}
    lda $06
    sta.l ${dest+10:06X}
    lda.l $7E0A00+CHAR_MAP_INDEX+{row}
    and #255
    sta.l ${dest+14:06X}
    lda.l $7E0A00+CHAR_ROSTER_INDEX+{row}
    and #255
    sta.l ${dest+16:06X}
    lda.l Screen_PosX
    sta.l ${dest+18:06X}
    lda $18
    sta.l ${dest+20:06X}
    lda.l $7E173C
    sta.l ${dest+12:06X}
    lda #1
    sta.l ${dest+6:06X}
{nxt}:
    .a16
    .i16
'''
        if stream:
            metadata=f'''    lda $06
    asl a
    asl a
    asl a
    tax
    lda.l $20A080,x
    sta.l ${dest+22:06X}
    lda.l $20A082,x
    sta.l ${dest+24:06X}
'''
            code=code.replace(nxt+':',metadata+nxt+':')
    code+='    pld\n    rtl\n'
    serial=[0]
    def long_skip(match):
        serial[0]+=1
        label=f'S7Capture_Branch{serial[0]}'
        inverse={'beq':'bne','bne':'beq','bcs':'bcc'}[match[1]]
        return f'    {inverse} {label}\n    brl {match[2]}\n{label}:\n    .a16\n    .i16'
    code=re.sub(r'    (beq|bne|bcs) (S7Publisher_Capture_S\d+_done)',long_skip,code)
    code+='''S7Publisher_EmitPieces:
    .a16
    .i16
    lda.l S7Pub_State+32,x
    sta.l S7Pub_State+14
    lda.l S7Pub_State+34,x
    sta.l S7Pub_State+16
    ; Normal source actors bypass Character_RenderFrame and emit a whole source
    ; metasprite here. Apply the native pit-foot projection before any source
    ; piece reaches the OAM shadow.
    stz.l S7Pub_State+8
    tdc
    sec
    sbc #$0A00
    tax
    lda.l StageBounds_State,x
    beq S7Publisher_EmitPieces__bounds_ready
    cmp #2
    beq S7Publisher_EmitPieces__bounds_hidden
    lda.l StageBounds_DrawY,x
    cmp #240
    bcs S7Publisher_EmitPieces__bounds_hidden
    sta.l S7Pub_State+16
    lda #1
    sta.l S7Pub_State+8
    bra S7Publisher_EmitPieces__bounds_ready
S7Publisher_EmitPieces__bounds_hidden:
    .a16
    .i16
    lda #2
    sta.l S7Pub_State+8
    rts
S7Publisher_EmitPieces__bounds_ready:
    .a16
    .i16
    lda.l S7Pub_State+12
    tax
    lda.l S7Pub_State+36,x
    sta.l S7Pub_State+18
    lda.l S7Pub_State+44,x
    sta.l S7Pub_State+22
    lda #0
    sta.l S7Pub_State+20
S7Publisher_EmitPieces__loop:
    .a16
    .i16
    lda.l S7Pub_State+20
    tax
    lda.l S7Pub_State+18
    beq S7Publisher_EmitPieces__left
    lda.l $20A100,x
    bra S7Publisher_EmitPieces__x
S7Publisher_EmitPieces__left:
    .a16
    .i16
    lda.l $20A102,x
S7Publisher_EmitPieces__x:
    .a16
    .i16
    clc
    adc.l S7Pub_State+14
    cmp #256
    bcs S7Publisher_EmitPieces__next
    sep #$20
    .a8
    sta.l OamSetSprite_X
    rep #$30
    .a16
    .i16
    lda.l $20A104,x
    clc
    adc.l S7Pub_State+16
    cmp #224
    bcs S7Publisher_EmitPieces__next
    sep #$20
    .a8
    sta.l OamSetSprite_Y
    lda.l $20A106,x
    sta.l OamSetSprite_Tile
    lda #0
    sta.l OamSetSprite_Hi
    lda.l S7Pub_State+18
    bne S7Publisher_EmitPieces__right_attr
    lda #$7C
    bra S7Publisher_EmitPieces__attr
S7Publisher_EmitPieces__right_attr:
    .a8
    .i16
    lda #$3C
S7Publisher_EmitPieces__attr:
    .a8
    .i16
    sta.l OamSetSprite_Attr
    lda.l S7Pub_State+8
    cmp #1
    bne S7Publisher_EmitPieces__priority_ready
    lda.l OamSetSprite_Attr
    and #$CF                     ; source-sized pit pieces pass behind panels
    sta.l OamSetSprite_Attr
S7Publisher_EmitPieces__priority_ready:
    .a8
    .i16
    jsl Core_Oam_SetSprite_Long
S7Publisher_EmitPieces__next:
    rep #$30
    .a16
    .i16
    lda.l S7Pub_State+20
    clc
    adc #8
    sta.l S7Pub_State+20
'''+f'    cmp #{len(chunks)*8}\n    bcc S7Publisher_EmitPieces__loop\n    rts\n'
    depth=(ROOT/'src/core/depth_sort.pasm').read_text().split('Character_RenderPass:\n',1)[1]
    depth=depth.replace('    jsl Depth_Sort_ComputeOrder','    ; Order captured with the pre-catch-up snapshot.')
    depth=depth.replace('    jsl G13_PlayerLifecycleIsOut',
        '    tdc\n    sec\n    sbc #$0A00\n    tax\n    lda.l S6Bridge_Policy,x\n    and #255\n    cmp #1\n    beq Character_RenderPass__render_live\n    jsl G13_PlayerLifecycleIsOut')
    depth,compat_renderer=hook_render_live(depth)
    # The isolated template test intentionally supplies no runtime symbol
    # table.  Keep the generated template self-contained in that mode; a
    # real linked build still has the accepted StageTimerHost hook and is
    # checked below through the normal import path.
    if compat_renderer not in sym:
        if sym:
            raise ValueError('PUBLICATION_COMPAT_HOOK: renderer missing from runtime symbols: '+compat_renderer)
        compat_renderer='Character_RenderFrame'
    code+='Character_RenderPass:\n'+depth
    if stream:
        code=code.replace('    lda #0\n    sta.l S7Pub_State+20\nS7Publisher_EmitPieces__loop:',
            '    lda.l S7Pub_State+54,x\n    sta.l S7Pub_State+20\n    lda.l S7Pub_State+56,x\n    asl a\n    asl a\n    asl a\n    clc\n    adc.l S7Pub_State+20\n    sta.l S7Pub_State+28\nS7Publisher_EmitPieces__loop:')
        code=code.replace(f'    cmp #{len(chunks)*8}\n    bcc S7Publisher_EmitPieces__loop',
                          '    cmp.l S7Pub_State+28\n    bcc S7Publisher_EmitPieces__loop')
    code+='\n.org $B000\n'+db(transfers)+'\n.bank 32\n.org $8000\n'+db(payload)
    if not _defer_compat:
        code=bind_compat_renderer(code,compat_renderer)
    tokens=set(re.findall(r'\b[A-Za-z_][A-Za-z_0-9]*\b',code))
    imports={k:v for k,v in sym.items() if k in tokens and not k.startswith('Character_RenderPass')}
    if compat_renderer in sym:
        imports[compat_renderer]=sym[compat_renderer]
    return dict(assembly=code,imports=imports,compat_renderer=compat_renderer)


def prepare(folder,source,sym,requests):
    def resource_block(resource,required,available):
        details=dict(capability='RESOURCE_BLOCKED',resource=resource,
                     required=required,available=available,
                     scope='CURRENT_COMPILER_PUBLICATION_ABI_NOT_GLOBAL_TARGET_IMPOSSIBILITY')
        (folder/'resource-blocked.json').write_text(json.dumps(details,indent=2))
        raise PublicationResourceBlocked(resource,details)
    packet_palettes=any(r.get('packet_palettes',False) for r in requests)
    if packet_palettes and any(r['action_slot'] not in (0,1) for r in requests):
        resource_block('PACKET_PALETTE_INSTANCE_SLOTS',sorted({r['action_slot'] for r in requests}),[0,1])
    linked=[]
    for r in requests:
        model=parse_model(source,r['path'],r['name'],'s7-multi','historical-bor')
        actor=lower_model(model)
        role_id=sorted(a['role'] for a in actor['animations']).index(r['role'])
        linked.append(dict(r,model=model,role_id=role_id))
    try:
        compat_slots=sorted({slot for r in requests for slot in r.get('compat_slots',[])})
        # Production columns 0..3,32,33 each own four SMALL footprints.
        columns=(0,1,2,3,32,33)
        reserved=sorted({(columns[slot]//32)*16+(columns[slot]%32)*2+offset
                         for slot in compat_slots for offset in (0,1,8,9)})
        plan=compile_set(source,linked,packet_palettes=packet_palettes,reserved_slots=reserved)
    except PublicationResourceBlocked as error:
        (folder/'resource-blocked.json').write_text(json.dumps(error.details,indent=2))
        raise
    metadata=bytearray();pieces=bytearray()
    for f in plan['frames']:
        _,blob=pack_descriptor(dict(chunks=f['pieces']),role=f['role'],index=f['frame'],
                              map_selector=f['map'],piece_address=0x20A100+len(pieces))
        f['piece_offset']=len(pieces);f['piece_bytes']=len(blob)
        metadata+=struct.pack('<8H',f['model'],f['role'],f['frame'],f['map'],len(pieces),len(f['pieces']),f['palette_slot'],0)
        pieces+=blob
    if len(metadata)>256:resource_block('PINNED_DESCRIPTOR_TABLE_BYTES',len(metadata),256)
    payload=plan['tiles']+metadata.ljust(256,b'\0')+pieces
    palette_base=len(payload);paldata=bytearray();transfers=bytearray()
    if reserved:
        occupied=set()
        for block in plan['blocks'].values():
            slot=block['slot'];tile=(slot//8)*64+(slot%8)*2
            for row in range(4):occupied.update(range((tile+16*row)*32,(tile+16*row)*32+64))
        spans=[]
        for offset in sorted(occupied):
            if spans and spans[-1][0]+spans[-1][1]==offset and spans[-1][1]<1024:
                spans[-1][1]+=1
            else:spans.append([offset,1])
    else:spans=[[i,1024] for i in range(0,16384,1024)]
    for i,length in spans:transfers+=struct.pack('<HHHBB',0x8000+i,0x8000+i,length,32,0)
    for key,slot in sorted(plan['palette_slots'].items(),key=lambda p:p[1]):
        transfers+=struct.pack('<HHHBB',0x8000+palette_base+len(paldata),256+slot*32,32,32,2)
        paldata+=plan['palettes'][key]
    payload+=paldata
    if packet_palettes:
        palette_addresses={}
        for key,data in sorted(plan['palettes'].items()):
            palette_addresses[key]=0x8000+len(payload)
            payload+=data
        for i,f in enumerate(plan['frames']):
            f['palette_source']=palette_addresses[f['palette']]
            struct.pack_into('<H',metadata,i*16+14,f['palette_source'])
        payload=payload[:16384]+metadata.ljust(256,b'\0')+payload[16640:]
    if len(payload)>32768:resource_block('PUBLICATION_ROM_BANK_BYTES',len(payload),32768)
    result=emit_code(sym,linked[0]['runtime_id'],linked[0]['role_id'],plan['frames'][0]['pieces'],transfers,payload,stream=True,_defer_compat=True)
    code=result['assembly'].split('\n.org $B000\n',1)[0]
    a,b=code.split('S7Publisher_Capture:\n',1)
    _,b=b.split('S7Publisher_EmitPieces:\n',1)
    slot_mask=0
    for r in requests:slot_mask|=1<<r['action_slot']
    code=a+capture_code(len(plan['frames']),[f['model'] for f in plan['frames']],slot_mask)+'S7Publisher_EmitPieces:\n'+b
    if packet_palettes:
        for slot in (0,1):
            dest=0x7F8C20+slot*32
            code=code.replace(f'    lda.l $20C00C,x\n    sta.l ${dest+26:06X}',
                f'    lda.l $20A00E,x\n    sta.l ${dest+28:06X}\n    lda #{6+slot}\n    sta.l ${dest+26:06X}')
    code=code.replace('S7Pub_TransferCount = 9',f'S7Pub_TransferCount = {len(spans)+len(plan["palette_slots"])}')
    code=code.replace('    lda.l S7Pub_State+32,x\n',
        '    lda.l S7Pub_State+58,x\n    asl a\n    ora #$30\n    sta.l S7Pub_State+30\n    lda.l S7Pub_State+32,x\n')
    code=code.replace('    lda #$7C','    lda.l S7Pub_State+30\n    ora #$40')
    code=code.replace('    lda #$3C','    lda.l S7Pub_State+30')
    code=code.replace('    cmp #256\n    bcs S7Publisher_EmitPieces__next',
        '    cmp #256\n    bcc S7Multi_XVisible\n    cmp #$FFF1\n    bcc S7Publisher_EmitPieces__next\nS7Multi_XVisible:\n.a16\n.i16\n    sta.l S7Pub_State+$E6')
    code=code.replace('    cmp #224\n    bcs S7Publisher_EmitPieces__next',
        '    cmp #224\n    bcc S7Multi_YVisible\n    cmp #$FFE1\n    bcc S7Publisher_EmitPieces__next\nS7Multi_YVisible:\n.a16\n.i16')
    code=code.replace('    lda #0\n    sta.l OamSetSprite_Hi',
        '    lda.l S7Pub_State+$E7\n    and #1\n    sta.l OamSetSprite_Hi')
    code=code.replace('    bcc S7Publisher_EmitPieces__loop',
        '    bcs S7Multi_PiecesDone\n    brl S7Publisher_EmitPieces__loop\nS7Multi_PiecesDone:\n.a16\n.i16')
    # Existing immutable full OAM packet implementation, unchanged fences.
    code=code.replace('    rtl\n\nS7Publisher_Entry:', '    jsl S7Multi_Reset\n    rtl\n\nS7Publisher_Entry:')
    code=code.replace('Character_RenderPass:\n','Character_RenderPass:\n    jsl S7Packet_Begin\n')
    if any(not f['pieces'] for f in plan['frames']):
        code=code.replace('    jsr S7Publisher_EmitPieces',
            '    lda.l S7Pub_State+56,x\n    beq S7Publisher_RenderOrCompat__done\n    jsr S7Publisher_EmitPieces')
    code=code.replace('    lda.l Depth_RenderOrder,x','    lda.l S7Pub_State+$F4,x')
    code=code.replace('S7Publisher_EmitPieces:\n','S7Publisher_EmitPieces:\n    lda.l S7Pub_State+$F2\n    beq S7Multi_EmitActive\n    rts\nS7Multi_EmitActive:\n.a16\n.i16\n')
    oam=(ROOT/'src/core/oam.pasm').read_text()
    clear=oam[oam.index('Core_Oam_ClearActive:\n'):oam.index('; Call once per frame after all sprites')]
    for label,width in (('main_loop','a16'),('main_skip','a16'),('hi_loop','a8')):
        clear=clear.replace(f'Core_Oam_ClearActive__{label}:\n',f'Core_Oam_ClearActive__{label}:\n.{width}\n.i16\n')
    native=(ROOT/'src/core/actor_source_oam_packet.pasm').read_text()+'\n'+clear+oam[oam.index('Core_Oam_TransformHiOam:\n'):]
    native=native.replace('Core_Oam_ClearActive','S7Packet_ClearActive').replace('Core_Oam_TransformHiOam','S7Packet_TransformHiOam')
    # Separate immutable packet in the gap after FP Tile2Slot and before
    # Slot2Tile. Keep the accepted streaming packet and its lease ABI unchanged.
    assert sym['StreamCacheFp_Tile2Slot']+2*sym['STREAM_FP_MAX_TILE_IDS']<=0x7FA600
    assert 0x7FA840<=sym['StreamCacheFp_Slot2Tile']
    second=(ROOT/'src/core/actor_source_oam_packet.pasm').read_text()
    second=second.replace('S7Packet_','S7Packet2_')
    second=re.sub(r'\$7F8([D-F][0-9A-F]{2})',
        lambda m:f'${int(m[0][1:],16)+0x1900:06X}',second)
    second=second.replace('Core_Oam_ClearActive','S7Packet_ClearActive').replace('Core_Oam_TransformHiOam','S7Packet_TransformHiOam')
    second=second.replace('S7Packet2_ClearActive','S7Packet_ClearActive').replace('S7Packet2_TransformHiOam','S7Packet_TransformHiOam')
    second=second.replace('#$8D00','#$A600')
    code+='\n'+native+'\n'+second+'''\nS7Multi_Reset:
    jsl S7Packet_Init
    jsl S7Packet2_Init
    rep #$30
.a16
.i16
    lda #0
    sta.l S7Pub_State+$F2
    ldx #0
S7Multi_Reset__loop:
.a16
.i16
    sta.l $7F8F24,x
    sta.l $7FA824,x
    inx
    inx
    cpx #28
    bcc S7Multi_Reset__loop
    rtl
S7Multi_OamTail:
    php
    rep #$30
.a16
.i16
    lda.l S7Pub_State+$F2
    beq S7Multi_OamTail__active
    jsl S7Multi_Teardown
    plp
    rtl
S7Multi_OamTail__active:
.a16
.i16
    lda.l S7Pub_State+6
    cmp #1
    bne S7Multi_OamTail__legacy
    lda.l S7Pub_State+$E8
    beq S7Multi_OamTail__ready
S7Multi_OamTail__missing:
.a16
.i16
    lda #$D705
    sta.l S7Pub_State+$FE
    lda.l S7Pub_State+$F0
    inc a
    sta.l S7Pub_State+$F0
    plp
    rtl
S7Multi_OamTail__ready:
.a16
.i16
    jsl S7Packet_Poll
    jsl S7Packet2_Poll
    lda.l DmaQueue_BudgetTotal
    clc
    adc #544
    cmp #$0B00
    bcs S7Multi_OamTail__budget
    lda.l $7F8F20
    beq S7Multi_OamTail__first
    lda.l $7FA820
    bne S7Multi_OamTail__busy
    jsl S7Packet2_Submit
    plp
    rtl
S7Multi_OamTail__first:
.a16
.i16
    jsl S7Packet_Submit
    plp
    rtl
S7Multi_OamTail__budget:
.a16
.i16
    lda #$D706
    sta.l S7Pub_State+$FE
    plp
    rtl
S7Multi_OamTail__busy:
.a16
.i16
    lda #$D704
    sta.l S7Pub_State+$FE
    plp
    rtl
S7Multi_OamTail__legacy:
.a16
.i16
    jsl Core_Oam_Play_Long
    plp
    rtl
; Epoch-close request: all previous packets and a replacement hidden packet
; must finish before the pinned tile/palette lease can be released.
S7Multi_Teardown:
    rep #$30
.a16
.i16
    jsl S7Packet_Poll
    jsl S7Packet2_Poll
    lda.l $7F8F20
    ora.l $7FA820
    bne S7Multi_Teardown__done
    lda.l S7Pub_State+$F2
    cmp #3
    beq S7Multi_Teardown__legacy
    cmp #1
    beq S7Multi_Teardown__hide
    cmp #2
    bne S7Multi_Teardown__done
    lda #0
    sta.l S7Pub_State+6
    lda #3
    sta.l S7Pub_State+$F2
    rtl
S7Multi_Teardown__hide:
.a16
.i16
    ; A close may be requested AFTER this field's render. Retire source tiles
    ; only with a picture captured/rendered under the source-excluded phase.
    lda.l S7Pub_State+$FA
    beq S7Multi_Teardown__done
    lda.l DmaQueue_BudgetTotal
    clc
    adc #544
    cmp #$0B00
    bcs S7Multi_Teardown__done
    jsl S7Packet_Submit
    bcc S7Multi_Teardown__done
    lda #2
    sta.l S7Pub_State+$F2
S7Multi_Teardown__done:
.a16
.i16
    rtl
S7Multi_Teardown__legacy:
.a16
.i16
    jml S7Shared_Oam
S7Shared_Oam:
    php
    rep #$30
.a16
.i16
    jmp S7Multi_OamTail__ready
'''
    code+='\n.org $B000\n'+db(transfers)+'\n.bank 32\n.org $8000\n'+db(payload)
    palette_overlays=[]
    if packet_palettes:
        code,palette_overlays=link_packet_palettes(code,sym,
            (ROOT/'src/core/actor_source_palette_packet.pasm').read_text(),
            staging_cache=any(r.get('palette_staging_cache') for r in requests))
    # Source-excluded pictures still use immutable shared packets. Reverting
    # to legacy mutable OAM during close/reload would re-arm its NMI clear and
    # could erase the next source picture while it is being prepared.
    code=code.replace('    jsl S7Packet_Submit\n','    jsl S7Packet_Submit__source\n')
    code=code.replace('    jsl S7Packet2_Submit\n','    jsl S7Packet2_Submit__source\n')
    code=code.replace('    bne S7Packet_Begin__done\n    jsr S7Packet_ClearActive',
        '    beq S7Shared_Clear\n    lda.l S7Pub_State+$F2\n    beq S7Packet_Begin__done\nS7Shared_Clear:\n.a16\n.i16\n    jsr S7Packet_ClearActive')
    # Lifecycle service is an unconditional publisher capability. In
    # particular a resource-rejected picture must not strand a close request.
    assert 0x7FA8D0<=sym['StreamCacheFp_Slot2Tile']
    code=code.replace('    sta.l S7Pub_State+$F2\n',
        '    sta.l S7Pub_State+$F2\n    sta.l $7FA8C0\n    sta.l $7FA8C2\n    sta.l $7FA8C4\n',1)
    code=code.replace('S7Multi_OamTail:\n    php\n    rep #$30\n.a16\n.i16\n',
        'S7Multi_OamTail:\n    php\n    rep #$30\n.a16\n.i16\n    jsl S7Epoch_Service\n'
        '    lda.l S7Pub_State+$F2\n    cmp #4\n    bne S7Epoch_NotOpening\n    jsl S7Epoch_Reopen\n    jsl S7Shared_Oam\n    plp\n    rtl\nS7Epoch_NotOpening:\n.a16\n.i16\n')
    code=code.replace('    lda #3\n    sta.l S7Pub_State+$F2\n    rtl',
        '    lda #3\n    sta.l S7Pub_State+$F2\n    lda #1\n    sta.l $7FA8C2\n    rtl')
    code+='\n.bank 31\n.org $C400\n'+(ROOT/'src/core/actor_source_publication_epoch.pasm').read_text()
    # Publication ordering is independent of the interruptible DMA ring's
    # physical placement. Both buffers receive one monotonic producer ticket.
    assert 0x7FA8D0<=sym['StreamCacheFp_Slot2Tile']
    code=code.replace('S7Multi_Reset:\n',
        'S7Multi_Reset:\n    rep #$30\n.a16\n.i16\n    lda #0\n    sta.l $7FA8C8\n    sta.l $7FAA02\n',1)
    for prefix,control,buffer in (('S7Packet',0x7F8F20,0x8D00),('S7Packet2',0x7FA820,0xA600)):
        marker=f'    sta.l ${control+20:06X}\n'
        assert code.count(marker)==1
        code=code.replace(marker,marker+f'    lda.l $7FA8C8\n    inc a\n    sta.l $7FA8C8\n    sta.l ${control+24:06X}\n')
        metadata=['    lda #0',f'    sta.l ${control+30:06X}']
        metadata += [f'    ora.l ${0x7F8C26+slot*32:06X}' for slot in range(6)]
        metadata += [f'    sta.l ${control+28:06X}']
        for slot in range(6):
            label=f'{prefix}_Camera{slot}'
            metadata += [f'    lda.l ${0x7F8C26+slot*32:06X}',f'    beq {label}',
                         f'    lda.l ${0x7F8C32+slot*32:06X}',f'    sta.l ${control+26:06X}',
                         f'    brl {prefix}_CameraDone',label+':','.a16','.i16']
        metadata += [prefix+'_CameraDone:','.a16','.i16']
        code=code.replace(marker,marker+'\n'.join(metadata)+'\n')
        start=code.index(prefix+'_Poll:\n')
        end=code.index('    rtl\n',code.index(prefix+'_Poll__done:\n',start))+len('    rtl\n')
        poll=f'''{prefix}_Poll:
    rep #$30
.a16
.i16
    lda.l ${control:06X}
    bne {prefix}_Poll__scan_start
    rtl
{prefix}_Poll__scan_start:
.a16
.i16
    phy
{prefix}_Poll__retry:
.a16
.i16
    lda.l Nmi_FrameCounter
    pha
    ldx #0
{prefix}_Poll__scan:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$43
    cmp #$41
    bne {prefix}_Poll__next
    lda.l DmaQueue+7,x
    and #255
    cmp #$7F
    bne {prefix}_Poll__next
    lda.l DmaQueue+5,x
    cmp #${buffer:04X}
    bne {prefix}_Poll__next
    pla
    txa
    sta.l ${control+2:06X}
    ply
    rtl
{prefix}_Poll__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc {prefix}_Poll__scan
    pla
    cmp.l Nmi_FrameCounter
    bne {prefix}_Poll__retry
    lda.l ${control+6:06X}
    sta.l ${control+4:06X}
    lda #0
    sta.l ${control:06X}
    ply
{prefix}_Poll__done:
.a16
.i16
    rtl
'''
        code=code[:start]+poll+code[end:]
        start=code.index(prefix+'_Submit__source:\n')
        end=code.index(prefix+'_Submit__free:\n',start)
        code=code[:start]+f'''{prefix}_Submit__source:
.a16
.i16
    jsl {prefix}_Poll
    lda.l ${control:06X}
    beq {prefix}_Submit__free
    jmp {prefix}_Submit__fault
'''+code[end:]
    if not packet_palettes:
        address=sym['Core_Dma_TransferOam']
        code+='\n.bank 31\n.org $C000\n'+(ROOT/'src/core/actor_source_palette_packet.pasm').read_text()
        code+=f'\n.bank 0\n.org ${address:04X}\n    jsl S7Palette_Transfer\n    rts\n'
        palette_overlays.append((address,bytes.fromhex('c231bf8504')))
    code=code.replace('S7Palette_Transfer:\n','S7Palette_Transfer:\n    jsl S7Oam_Order\n    jsl S7Framing_Admit\n    bcs S7Palette_Transfer__admitted\nS7Palette_Transfer__rejected:\n.a16\n.i16\n    rtl\nS7Palette_Transfer__admitted:\n.a16\n.i16\n')
    code+='\n.bank 31\n.org $CA00\n'+(ROOT/'src/core/actor_source_oam_order.pasm').read_text()
    assert 0x7FAE00<=sym['StreamCacheFp_Slot2Tile']
    # Reservations belong to the admitted epoch, not to actor names. Validate
    # actual allocation owners before any entry transfer and each publication.
    guard=['S7Admission_Owners:','    rep #$30','.a16','.i16',
           '    lda #0','    sta.l $7FAA08']
    for slot in range(6):
        nxt=f'S7Admission_Owners_{slot}'
        base=0x7E0A00+slot*sym['CHAR_ZP_LEN']
        guard += [f'    lda.l S6Bridge_Policy+{slot}*CHAR_ZP_LEN','    and #255',
                  '    cmp #1',f'    beq {nxt}',f'    lda.l ${base+sym["CHAR_HP"]:06X}',
                  '    and #255',f'    bne {nxt}_allocated',
                  f'    lda.l ${base+sym["CHAR_SELECTED"]:06X}','    and #255',
                  '    cmp #CHAR_SELECTED_FALL',f'    bne {nxt}',
                  nxt+'_allocated:','.a16','.i16']
        if slot in compat_slots:
            guard += [f'    lda.l ${base+sym["CHAR_TILE_COLUMN"]:06X}','    and #255',
                      f'    cmp #{columns[slot]}',f'    beq {nxt}_palette',
                      f'    bra {nxt}_invalid',nxt+'_palette:','.a16','.i16',
                      f'    lda.l ${base+sym["CHAR_PALETTE_SLOT"]:06X}','    and #255',
                      f'    cmp #{slot}',f'    beq {nxt}']
        guard += [nxt+'_invalid:','.a16','.i16','    lda.l $7FAA08',
                  f'    ora #{1<<slot}','    sta.l $7FAA08',nxt+':','.a16','.i16']
    guard += ['    lda.l $7FAA08','    bne S7Admission_Owners__blocked',
              '    sec','    rtl','S7Admission_Owners__blocked:','.a16','.i16',
              '    lda #$D708','    sta.l S7Pub_State+$FE','    clc','    rtl']
    upper=['S7Admission_Upper:','    jsl S7Admission_Owners','    bcs S7Admission_Upper__owned',
           '    lda.l S7Pub_State+$F2','    bne S7Admission_Upper__owned','    clc','    rtl',
           'S7Admission_Upper__owned:','.a16','.i16','    lda #0','    sta.l S7Pub_State+22']
    for slot in range(6):
        row=0x7F8C20+slot*32;label=f'S7Admission_Upper_{slot}'
        upper += [f'    lda.l S6Bridge_Policy+{slot}*CHAR_ZP_LEN','    and #255',
                  '    cmp #1',f'    beq {label}_source','    lda #2',f'    bra {label}_add',
                  label+'_source:','.a16','.i16',f'    lda.l ${row+6:06X}',f'    beq {label}_done',
                  f'    lda.l ${row+24:06X}',label+'_add:','.a16','.i16',
                  '    clc','    adc.l S7Pub_State+22','    sta.l S7Pub_State+22',label+'_done:','.a16','.i16']
    upper += ['    lda.l S7Pub_State+22','    sta.l $7FA8DA','    cmp #129','    bcc S7Admission_Upper__pass',
              '    lda #$D70A','    sta.l S7Pub_State+$FE','    clc','    rtl',
              'S7Admission_Upper__pass:','.a16','.i16','    sec','    rtl']
    code+='\n.bank 31\n.org $CC00\n'+'\n'.join(guard+upper)+'\n'
    code+=(ROOT/'src/core/actor_source_oam_admission.pasm').read_text()
    code+=f'\nS7Framing_PacketBytes = {608 if packet_palettes else 544}\n'+(ROOT/'src/core/actor_source_publication_framing.pasm').read_text()
    # NMI owns one source-excluded copy of the last hardware picture. It is
    # never a simulated world or an expected-image fixture. The copy is used
    # only to fail closed if that displayed picture loses its camera contract.
    code=code.replace('    sta.l $7FAA02\n','    sta.l $7FAA02\n    sta.l $7FAD22\n',1)
    end='    rep #$31\n.a16\n.i16\n    rtl\n'
    start=code.index('S7Palette_Transfer:\n')
    finish=code.index(end,code.index('S7Palette_Transfer__length:',start))
    code=code[:finish]+code[finish:].replace(end,
        '    rep #$31\n.a16\n.i16\n    jsl S7Framing_Remember\n    rtl\n',1)
    # A malformed accepted allocation is never rendered into the shared
    # picture. A close can still publish the valid accepted owners and retire
    # source leases through the normal hardware-consumption fence.
    legacy='    plp\n    jml Character_RenderFrame\n'
    assert code.count(legacy)==1
    owner_checks=[]
    for slot in range(6):
        label=f'S7Admission_Compat_{slot}'
        owner_checks += [f'    cpx #{slot}*CHAR_ZP_LEN',f'    bne {label}',
                         '    lda.l $7FAA08',f'    and #{1<<slot}',
                         '    bne S7Admission_CompatHidden',label+':','.a16','.i16']
    code=code.replace(legacy,'\n'.join(owner_checks)+'\n'+legacy+
        'S7Admission_CompatHidden:\n.a16\n.i16\n    plp\n    rtl\n')
    code=bind_compat_renderer(code,result['compat_renderer'])
    code=code.replace('S7Publisher_Entry:\n',
        'S7Publisher_Entry:\n    jsl S7Admission_Owners\n    bcs S7Admission_EntryOwned\n    rtl\nS7Admission_EntryOwned:\n.a16\n.i16\n')
    code=code.replace('S7Admission_EntryOwned:\n.a16\n.i16\n',
        'S7Admission_EntryOwned:\n.a16\n.i16\n    lda #1\n    sta.l $7FAD28\n')
    code=code.replace('    sta.l $7FAD22\n','    sta.l $7FAD22\n    sta.l $7FAD28\n',1)
    code=code.replace('    sta.l S7Pub_State+6\n    lda #3\n',
        '    sta.l S7Pub_State+6\n    sta.l $7FAD28\n    lda #3\n')
    # Lease segments are 64-byte units across the full $8000-$BFFF
    # source-OBJ span: 256 units, not the former single-page 128.
    segments=bytes(int(((i&7)+(i//32)*8) in {b['slot'] for b in plan['blocks'].values()}) for i in range(256))
    vram=(ROOT/'src/core/dma.pasm').read_text().split('Core_Dma_TransferVram:\n',1)[1].split('Core_Dma_TransferOam:',1)[0]
    assert vram.count('\trts')==1
    vram=vram.replace('\trts','\trtl')
    code+='\n.bank 31\n.org $D800\n'+(ROOT/'src/core/actor_source_vram_lease.pasm').read_text()
    code+='\nS7Lease_TransferVram:\n    jsl S7Lease_Admit\n    bcs S7Lease_TransferVram__allowed\n    rtl\nS7Lease_TransferVram__allowed:\n.a16\n.i16\n'+vram
    code+='\nS7Lease_Segments:\n'+db(segments+b'\0')+'\n'
    address=sym['Core_Dma_TransferVram']
    code+=f'\n.bank 0\n.org ${address:04X}\n    jsl S7Lease_TransferVram\n    rts\n'
    palette_overlays.append((address,bytes.fromhex('c231bf8504')))
    cgram=(ROOT/'src/core/dma.pasm').read_text().split('Core_Dma_TransferCgram:\n',1)[1]
    assert cgram.count('\trts')==1
    code+='\n.bank 31\n.org $DC00\nS7Lease_TransferCgram:\n    jsl S7Lease_AdmitCgram\n    bcs S7Lease_TransferCgram__allowed\n    rtl\nS7Lease_TransferCgram__allowed:\n.a16\n.i16\n'+cgram.replace('\trts','\trtl')
    address=sym['Core_Dma_TransferCgram']
    code+=f'\n.bank 0\n.org ${address:04X}\n    jsl S7Lease_TransferCgram\n    rts\n'
    palette_overlays.append((address,bytes.fromhex('c231bf8504')))
    call=sym['Game_State_Play__done']-3;gate=0xFFA8
    # A completed source render snapshot is independent of the catch-up it
    # precedes. Submit its immutable picture before running those source ticks.
    # The late gameplay hook remains for initialization/error paths only.
    code+='''
.bank 31
.org $C800
S7Multi_PublishSnapshot:
    php
    rep #$30
.a16
.i16
    phx
    phy
    phb
    phd
    sep #$20
.a8
    lda #$7E
    pha
    plb
    rep #$30
.a16
.i16
    jsl S7Admission_Upper
    bcc S7Multi_PublishSnapshot__handled
    jsl Character_RenderPass
    jsl S7Admission_Scanlines
    bcc S7Multi_PublishSnapshot__handled
    jsl S7Multi_OamTail
S7Multi_PublishSnapshot__handled:
.a16
.i16
    lda #1
    sta.l $7FA8C6
    pld
    plb
    ply
    plx
    plp
S7Multi_PublishSnapshot__completed:
.a16
.i16
    rtl
S7Multi_ServiceTail:
    php
    rep #$30
.a16
.i16
    lda.l $7FA8C6
    bne S7Multi_ServiceTail__done
    jsl S7Multi_OamTail
S7Multi_ServiceTail__done:
.a16
.i16
    plp
    rtl
'''
    code+=f'\n.bank 0\n.org ${call:04X}\n    jsr ${gate:04X}\n.org ${gate:04X}\n    jsl S7Multi_ServiceTail\n    rts\n'
    # Keep the small production-bank overlays together. Interleaving a
    # returning bank's high native cursor with a low overlay .org makes the
    # assembler's section-overlap accounting span unrelated bank addresses.
    overlays=[]
    def collect_overlay(match):
        overlays.append(match.group(0))
        return '\n'
    code=re.sub(r'\n\.bank 0\n.*?(?=\n\.bank |\Z)',collect_overlay,code,flags=re.S)
    code+=''.join(overlays)
    tokens=set(re.findall(r'\b[A-Za-z_][A-Za-z_0-9]*\b',native))
    result['imports'].update({k:v for k,v in sym.items() if k in tokens})
    result['imports'].update({k:v for k,v in sym.items() if k.startswith('CHAR_') and k in code})
    result['imports'].update({k:v for k,v in sym.items() if k.startswith('Nmi_') and k in code})
    result['imports']['Core_Oam_Play_Long']=sym['Core_Oam_Play_Long']
    result['assembly']=code
    result['overlays']=[(call,bytes([0x20])+sym['Core_Oam_Play'].to_bytes(2,'little')),(gate,bytes(5)),*palette_overlays]
    (folder/'publisher-assets.bin').write_bytes(payload)
    report={k:v for k,v in plan.items() if k not in ('tiles','palettes')}
    report['palettes']={k:v.hex() for k,v in plan['palettes'].items()}
    report['transfers']=[list(t) for t in struct.iter_unpack('<HHHBB',transfers)]
    report['fixture_publication_slot_mask']=slot_mask
    report['packet_palettes']=packet_palettes
    (folder/'publisher-multi.json').write_text(json.dumps(report,indent=2))
    return result
