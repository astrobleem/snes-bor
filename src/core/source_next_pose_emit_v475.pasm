; UNHOOKED private geometry kernel generated from verified427 emitter math.
; Live OAM, build metadata, actor/world and loader scratch are never written.
; Input is the existing selected header/pieces/lease with physical tile names.
; Palette may still be queued: this creates private bytes, not readiness.
; Caller must separately validate/pin identities and fence publication.
SourceNextEmit_Cursor = $436680
SourceNextEmit_Meta = $436690
SourceNextEmit_Scratch = $436780
SourceNextEmit_Buffer = $436400
SourceNextEmit_ExpandedHi = $436600
SourceNextEmit_X = $436682
SourceNextEmit_Y = $436683
SourceNextEmit_Tile = $436684
SourceNextEmit_Attr = $436685
SourceNextEmit_Hi = $436686
SourceNextEmit_DebugEmitPiece = $4366D0
SourceNextEmit_DebugEmitOam = $436710
SourceNextEmit_DebugSheetRow = $436750
SourceNextEmit_DebugQueueStage = $436780
SourceNextEmit_EmitBaseX = $436782
SourceNextEmit_EmitBaseY = $436784
SourceNextEmit_EmitBoundsMode = $436786
SourceNextEmit_VisiblePieces = $436788
SourceNextEmit_PieceIndex = $43678A
SourceNextEmit_Error = $43678C
SourceNextEmit_PieceOffset = $43678E
SourceNextEmit_PaletteLocalSlot = $436790
SourceNextEmit_DebugStateCompare = $436792
SourceNextEmit_EmitPieceWidth = $436794
SourceNextEmit_EmitPieceHeight = $436796
SourceNextEmit_EmitPieceX = $436798
SourceNextEmit_EmitPieceY = $43679A
SourceNextEmit_Build:
.a16
.i16
    rep #$31
    cld
    lda.l $7E46DE
    beq SourceNextEmit_BuildG5
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG5:
.a16
.i16
    lda.l Game_State
    beq SourceNextEmit_BuildG11
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG11:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceNextEmit_BuildG17
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG17:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceNextEmit_BuildG23
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG23:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceNextEmit_BuildG31
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG31:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceNextEmit_BuildG38
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG38:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceNextEmit_BuildG45
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG45:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceNextEmit_BuildG52
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG52:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceNextEmit_BuildG59
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG59:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceNextEmit_BuildG66
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG66:
.a16
.i16
    jsr SourceNextPacket_PlayerMeta
    bcs SourceNextEmit_BuildG73
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG73:
.a16
.i16
    txa
    cmp.l SourceVisual_Record
    beq SourceNextEmit_BuildG79
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG79:
.a16
.i16
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    cmp.l SourceVisual_ActorSlot
    beq SourceNextEmit_BuildG86
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG86:
.a16
.i16
    lda #0
    sta.l SourceNextEmit_Meta+16,x
    lda.l SourceNextEmit_Cursor
    cmp #513
    bcc SourceNextEmit_BuildG99
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG99:
.a16
.i16
    and #3
    beq SourceNextEmit_BuildG106
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG106:
.a16
.i16
    lda.l SourceVisual_PieceCount
    bne SourceNextEmit_BuildG112
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG112:
.a16
.i16
    cmp #66
    bcc SourceNextEmit_BuildG118
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG118:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #255
    cmp.l SourceVisual_PieceCount
    beq SourceNextEmit_BuildG124
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG124:
.a16
.i16
    lda.l SourceVisual_Key
    cmp.l SourceVisual_EntryScratch
    beq SourceNextEmit_BuildG132
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG132:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp.l SourceVisual_EntryScratch+2
    beq SourceNextEmit_BuildG139
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG139:
.a16
.i16
    lda.l SourceVisual_BaseTile
    beq SourceNextEmit_BuildG146
    brl SourceNextEmit_BuildNo
SourceNextEmit_BuildG146:
.a16
.i16
    lda #0
    ldx #0
SourceNextEmit_ClearScratch:
.a16
.i16
    sta.l SourceNextEmit_Scratch,x
    sta.l SourceNextEmit_PackedHi,x
    inx
    inx
    cpx #64
    bcc SourceNextEmit_ClearScratch
    jsr SourceNextEmit_Emit
    php
    bcc SourceNextEmit_PackDone
    jsr SourceNextEmit_PackAllHigh
    jsr SourceNextEmit_MaskHigh
SourceNextEmit_PackDone:
.a16
.i16
    plp
    rtl
SourceNextEmit_BuildNo:
.a16
.i16
    clc
    rtl
SourceNextEmit_Emit:
    rep #$31
.a16
.i16
    jsl SourceNextPacket_EmitStart
    lda #0
    sta.l SourceNextEmit_DebugEmitPiece+44
    lda #36
    sta.l SourceNextEmit_DebugQueueStage
    rep #$31
.a16
.i16
    lda CHAR_POS_X
    sec
    sbc Screen_PosX
    sta.l SourceNextEmit_X
    sta.l SourceNextEmit_EmitBaseX
    lda #0
    sta.l SourceNextEmit_EmitBoundsMode
    ; Source-sized actors bypass Character_RenderFrame. Apply pit foot depth
    ; here while retaining authored per-piece offsets from the actor's foot.
    jsl StageBoundsHost_Normal
    bcc SourceNextEmit_Emit__ground_y
    jsl StageBounds_Row
    lda.l StageBounds_State,x
    beq SourceNextEmit_Emit__ground_y
    cmp #2
    bne SourceNextEmit_Emit__not_hidden
    brl SourceNextEmit_Emit__hidden
SourceNextEmit_Emit__not_hidden:
.a16
    lda.l StageBounds_DrawY,x
    cmp #240
    bcc SourceNextEmit_Emit__height_visible
    brl SourceNextEmit_Emit__hidden
SourceNextEmit_Emit__height_visible:
.a16
    sta.l SourceNextEmit_EmitBaseY
    lda #1
    sta.l SourceNextEmit_EmitBoundsMode
    bra SourceNextEmit_Emit__y_ready
SourceNextEmit_Emit__ground_y:
.a16
.i16
    lda CHAR_POS_Y
    sta.l SourceNextEmit_EmitBaseY
    ; This path bypasses Character_RenderFrame/Jump_ApplyOamYOffset.
    ; Keep lane depth for sorting; subtract this actor's accepted Q8.8
    ; native jump height from the source-piece foot for presentation only.
    ; Bounds-owned falls use their cached DrawY above and bypass this seam.
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceNextEmit_Emit__y_ready
    lda CHAR_THROW_ZPOS
    xba
    and #$00FF
    eor #$FFFF
    inc a
    clc
    adc.l SourceNextEmit_EmitBaseY
    sta.l SourceNextEmit_EmitBaseY
SourceNextEmit_Emit__y_ready:
.a16
    ; Count only pieces intersecting the real viewport before reserving the
    ; whole visible packet. World coordinates must not wrap into screen X:
    ; old offscreen props otherwise consume OAM and can hide the player.
    lda #0
    sta.l SourceNextEmit_VisiblePieces
    sta.l SourceNextEmit_PieceIndex
SourceNextEmit_Emit__count_visible:
    lda.l SourceNextEmit_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcs SourceNextEmit_Emit__reserve_visible
    jsr SourceNextEmit_ViewportNormalPiece
    bcc SourceNextEmit_Emit__count_mirror
    lda.l SourceNextEmit_VisiblePieces
    inc a
    sta.l SourceNextEmit_VisiblePieces
SourceNextEmit_Emit__count_mirror:
    jsr SourceNextEmit_ViewportMirrorPiece
    bcc SourceNextEmit_Emit__count_next
    lda.l SourceNextEmit_VisiblePieces
    inc a
    sta.l SourceNextEmit_VisiblePieces
SourceNextEmit_Emit__count_next:
    lda.l SourceNextEmit_PieceIndex
    inc a
    sta.l SourceNextEmit_PieceIndex
    bra SourceNextEmit_Emit__count_visible
SourceNextEmit_Emit__reserve_visible:
.a16
    lda.l SourceNextEmit_VisiblePieces
    asl a
    asl a
    clc
    adc.l SourceNextEmit_Cursor
    cmp #513
    bcc SourceNextEmit_Emit__oam_capacity_ok
    sep #$20
.a8
    lda #$2B
    sta.l SourceNextEmit_Error
    rep #$31
.a16
.i16
    clc
    rts
SourceNextEmit_Emit__oam_capacity_ok:
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceNextEmit_PieceIndex
    bra SourceNextEmit_Emit__piece
SourceNextEmit_Emit__hidden:
    sec
    rts
SourceNextEmit_Emit__piece:
    lda.l SourceNextEmit_PieceIndex
    sta.l SourceNextEmit_DebugEmitPiece+46
    sta.l SourceNextEmit_DebugEmitPiece+56
    lda.l SourceVisual_PieceCount
    sta.l SourceNextEmit_DebugEmitPiece+50
    lda.l SourceNextEmit_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceNextEmit_Emit__have_piece
    brl SourceNextEmit_Emit__done
SourceNextEmit_Emit__have_piece:
    jsr SourceNextEmit_ViewportPiece
    bcs SourceNextEmit_Emit__visible_piece
    brl SourceNextEmit_Emit__next_piece
SourceNextEmit_Emit__visible_piece:
.a16
    lda.l SourceNextEmit_EmitPieceX
    sta.l SourceNextEmit_X
    lda.l SourceNextEmit_EmitPieceY
    sta.l SourceNextEmit_Y
    lda.l SourceNextEmit_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    sta.l SourceNextEmit_PieceOffset
    lda.l SourceVisual_PieceTable+14,x
    and #$01FF
    clc
    adc.l SourceVisual_BaseTile
    sep #$20
.a8
    sta.l SourceNextEmit_Tile
    lda.l SourceVisual_PieceTable+8,x
    sta.l SourceNextEmit_PaletteLocalSlot
    rep #$31
.a16
.i16
    lda.l SourceVisual_Record
    clc
    adc #16
    clc
    adc.l SourceNextEmit_PaletteLocalSlot
    tax
    sep #$20
.a8
    lda.l SourceVisual_State,x
    beq SourceNextEmit_Emit__palette_bad_near
    dec a
    sta.l SourceNextEmit_DebugEmitPiece+60
    cmp #8
    bcc SourceNextEmit_Emit__palette_ok
SourceNextEmit_Emit__palette_bad_near:
    brl SourceNextEmit_Emit__palette_fail
SourceNextEmit_Emit__palette_ok:
    rep #$20
.a16
    lda.l SourceNextEmit_PieceOffset
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_DebugEmitPiece+60
    asl a
    ora #$30
    sta.l SourceNextEmit_Attr
    ; OBJ names 0..255 address one 8-KiB name table. Include the atlas
    ; origin, not only its residency base, when selecting the second table.
    rep #$20
.a16
    lda.l SourceVisual_PieceTable+14,x
    and #$01FF
    clc
    adc.l SourceVisual_BaseTile
    and #$0100
    beq SourceNextEmit_Emit__name_table0
    sep #$20
.a8
    lda.l SourceNextEmit_Attr
    ora #$01
    sta.l SourceNextEmit_Attr
SourceNextEmit_Emit__name_table0:
    sep #$20
.a8
    lda CHAR_FACING_LEFT
    beq SourceNextEmit_Emit__right
    lda.l SourceNextEmit_Attr
    ora #$40
    sta.l SourceNextEmit_Attr
    bra SourceNextEmit_Emit__write
SourceNextEmit_Emit__right:
SourceNextEmit_Emit__write:
.a8
    lda.l SourceNextEmit_EmitBoundsMode
    beq SourceNextEmit_Emit__priority_ready
    lda.l SourceNextEmit_Attr
    and #$CF                     ; falling source pieces pass behind panels
    sta.l SourceNextEmit_Attr
SourceNextEmit_Emit__priority_ready:
.a8
    lda #37
    sta.l SourceNextEmit_DebugQueueStage
    lda #1
    sta.l SourceNextEmit_DebugEmitPiece+48
    rep #$20
.a16
    lda.l SourceVisual_PieceTable+14,x
    and #$8000
    beq SourceNextEmit_Emit__small_obj
    sep #$20
.a8
    lda #2
    bra SourceNextEmit_Emit__obj_size_ready
SourceNextEmit_Emit__small_obj:
    sep #$20
.a8
    lda #0
SourceNextEmit_Emit__obj_size_ready:
    sta.l SourceNextEmit_Hi
    rep #$20
.a16
    lda.l SourceNextEmit_EmitPieceX
    and #$0100
    beq SourceNextEmit_Emit__x_high_ready
    sep #$20
.a8
    lda.l SourceNextEmit_Hi
    ora #1
    sta.l SourceNextEmit_Hi
SourceNextEmit_Emit__x_high_ready:
    ; Negative screen X takes the A8 high-bit path above. Restore the
    ; viewport helper ABI on both paths before reading 16-bit coordinates.
    rep #$31
.a16
.i16
    jsr SourceNextEmit_ViewportNormalPiece
    bcc SourceNextEmit_Emit__mirror
    jsr SourceNextEmit_WriteCurrentPiece
SourceNextEmit_Emit__mirror:
    jsr SourceNextEmit_ViewportMirrorPiece
    bcc SourceNextEmit_Emit__next_piece
SourceNextEmit_WriteMirror:
    ; Source mirror depth is behind the floor/frontpanel. No vflip, resize,
    ; extra tile allocation, changed source pose or extra actor is involved.
    sep #$20
    .a8
    lda.l SourceNextEmit_Attr
    and #$CF
    ora #$20                    ; above clean BG1, behind foreground BG2
    sta.l SourceNextEmit_Attr
    rep #$31
    .a16
    .i16
SourceNextEmit_WriteMirror__emit:
    jsr SourceNextEmit_WriteCurrentPiece
SourceNextEmit_Emit__next_piece:
    lda.l SourceNextEmit_PieceIndex
    inc a
    sta.l SourceNextEmit_PieceIndex
    jmp SourceNextEmit_Emit__piece
SourceNextEmit_Emit__done:
.a16
.i16
    jsl SourceNextPacket_EmitFinish
    lda #38
    sta.l SourceNextEmit_DebugQueueStage
    lda.l SourceNextEmit_Buffer
    sta.l SourceNextEmit_DebugSheetRow
    lda.l SourceNextEmit_Buffer+2
    sta.l SourceNextEmit_DebugSheetRow+2
    lda.l SourceNextEmit_Cursor
    sta.l SourceNextEmit_DebugStateCompare
    ldx #0
SourceNextEmit_DebugEmitCopy:
.i16
    lda.l SourceVisual_PieceTable,x
    sta.l SourceNextEmit_DebugEmitPiece,x
    inx
    inx
    cpx #16
    bcc SourceNextEmit_DebugEmitCopy
    lda.l SourceVisual_PieceCount
    sta.l SourceNextEmit_DebugEmitPiece+32
    lda.l SourceNextEmit_Cursor
    sta.l SourceNextEmit_DebugEmitPiece+34
    lda.l SourceNextEmit_Buffer+48
    sta.l SourceNextEmit_DebugEmitPiece+36
    lda.l SourceNextEmit_Buffer+50
    sta.l SourceNextEmit_DebugEmitPiece+38
    ldx #0
SourceNextEmit_DebugEmitOamCopy:
.i16
    lda.l SourceNextEmit_Buffer,x
    sta.l SourceNextEmit_DebugEmitOam,x
    inx
    inx
    cpx #64
    bcc SourceNextEmit_DebugEmitOamCopy
    lda #35
    sta.l SourceNextEmit_DebugQueueStage
    sec
    rts
SourceNextEmit_Emit__palette_fail:
    lda.l SourceNextEmit_PieceIndex
    sta.l SourceNextEmit_DebugEmitPiece+58
    sep #$20
.a8
    lda #$2A
    sta.l SourceNextEmit_Error
    rep #$31
.a16
.i16
    clc
    rts

SourceNextEmit_WriteCurrentPiece:
    ; OAM request coordinates are bytes; A16 Y would clear adjacent Tile.
    sep #$20
    .a8
    lda.l SourceNextEmit_EmitPieceX
    sta.l SourceNextEmit_X
    lda.l SourceNextEmit_EmitPieceY
    sta.l SourceNextEmit_Y
    sep #$20
    .a8
    lda.l SourceNextEmit_Attr
    jsl StageFp_BG2OamAttr
    sta.l SourceNextEmit_Attr
    rep #$31
.a16
.i16
    lda.l SourceNextEmit_Cursor
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_X
    sta.l SourceNextEmit_Buffer,x
    lda.l SourceNextEmit_Y
    sta.l SourceNextEmit_Buffer+1,x
    lda.l SourceNextEmit_Tile
    sta.l SourceNextEmit_Buffer+2,x
    lda.l SourceNextEmit_Attr
    sta.l SourceNextEmit_Buffer+3,x
    rep #$31
.a16
.i16
    lda.l SourceNextEmit_Cursor
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_Hi
    sta.l SourceNextEmit_ExpandedHi,x
    rep #$31
.a16
.i16
    lda.l SourceNextEmit_Cursor
    clc
    adc #4
    sta.l SourceNextEmit_Cursor
    rep #$31
.a16
.i16
    rts

; A16/I16. Resolve one authored 16x32 or 32x64 piece without byte wrapping.
; C=true iff at least one of its pixels can intersect the 256x224 viewport.
; Count and emission use this same predicate, keeping OAM admission atomic.
SourceNextEmit_ViewportPiece:
    jsr SourceNextEmit_ViewportNormalPiece
    bcs SourceNextEmit_ViewportPiece__union_visible
    jsr SourceNextEmit_ViewportMirrorPiece
SourceNextEmit_ViewportPiece__union_visible:
    rts

SourceNextEmit_ViewportNormalPiece:
.a16
    lda.l SourceNextEmit_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+14,x
    and #$8000
    beq SourceNextEmit_ViewportPiece__small
    lda #32
    sta.l SourceNextEmit_EmitPieceWidth
    lda #64
    bra SourceNextEmit_ViewportPiece__height
SourceNextEmit_ViewportPiece__small:
.a16
    lda #16
    sta.l SourceNextEmit_EmitPieceWidth
    lda #32
SourceNextEmit_ViewportPiece__height:
.a16
    sta.l SourceNextEmit_EmitPieceHeight
    lda CHAR_FACING_LEFT
    and #$00FF
    beq SourceNextEmit_ViewportPiece__right
    lda.l SourceVisual_PieceTable+4,x
    clc
    adc.l SourceNextEmit_EmitBaseX
    sta.l SourceNextEmit_EmitPieceX
    lda.l SourceVisual_PieceTable+6,x
    bra SourceNextEmit_ViewportPiece__y
SourceNextEmit_ViewportPiece__right:
    lda.l SourceVisual_PieceTable,x
    clc
    adc.l SourceNextEmit_EmitBaseX
    sta.l SourceNextEmit_EmitPieceX
    lda.l SourceVisual_PieceTable+2,x
SourceNextEmit_ViewportPiece__y:
.a16
    clc
    adc.l SourceNextEmit_EmitBaseY
    sta.l SourceNextEmit_EmitPieceY
    lda.l SourceNextEmit_EmitPieceX
    bmi SourceNextEmit_ViewportPiece__x_end
    cmp #256
    bcs SourceNextEmit_ViewportPiece__outside
SourceNextEmit_ViewportPiece__x_end:
.a16
    clc
    adc.l SourceNextEmit_EmitPieceWidth
    bmi SourceNextEmit_ViewportPiece__outside
    beq SourceNextEmit_ViewportPiece__outside
    lda.l SourceNextEmit_EmitPieceY
    bmi SourceNextEmit_ViewportPiece__y_end
    cmp #224
    bcs SourceNextEmit_ViewportPiece__outside
SourceNextEmit_ViewportPiece__y_end:
    clc
    adc.l SourceNextEmit_EmitPieceHeight
    bmi SourceNextEmit_ViewportPiece__outside
    beq SourceNextEmit_ViewportPiece__outside
    sec
    rts
SourceNextEmit_ViewportPiece__outside:
    clc
    rts

SourceNextEmit_ViewportMirrorPiece:
.a16
    lda.l Stage_Mirror
    and #$00FF
    bne SourceNextEmit_ViewportMirrorPiece__active
    clc
    rts
SourceNextEmit_ViewportMirrorPiece__active:
.a16
    jsr SourceNextEmit_ViewportNormalPiece
    lda.l SourceNextEmit_EmitPieceY
    sec
    sbc.l SourceNextEmit_EmitBaseY
    clc
    adc #248
    sec
    sbc CHAR_POS_Y
    sta.l SourceNextEmit_EmitPieceY
    lda.l SourceNextEmit_EmitPieceX
    bmi SourceNextEmit_ViewportMirrorPiece__x_end
    cmp #256
    bcs SourceNextEmit_ViewportMirrorPiece__outside
SourceNextEmit_ViewportMirrorPiece__x_end:
.a16
    clc
    adc.l SourceNextEmit_EmitPieceWidth
    bmi SourceNextEmit_ViewportMirrorPiece__outside
    beq SourceNextEmit_ViewportMirrorPiece__outside
    lda.l SourceNextEmit_EmitPieceY
    bmi SourceNextEmit_ViewportMirrorPiece__y_end
    cmp #224
    bcs SourceNextEmit_ViewportMirrorPiece__outside
SourceNextEmit_ViewportMirrorPiece__y_end:
    clc
    adc.l SourceNextEmit_EmitPieceHeight
    bmi SourceNextEmit_ViewportMirrorPiece__outside
    beq SourceNextEmit_ViewportMirrorPiece__outside
    sec
    rts
SourceNextEmit_ViewportMirrorPiece__outside:
    clc
    rts

; Bank-local long-addressing form of the shared OAM shadow write.  The bank-0
; compatibility trampoline uses DB-relative legacy cells; source-sized
; publication must keep the caller's actor D/DBR context intact while writing
; the same shared OAM shadow and cursor.
SourceNextEmit_SetSprite:
    php
    rep #$31
.a16
.i16
    lda.l SourceNextEmit_DebugEmitPiece+44
    inc a
    sta.l SourceNextEmit_DebugEmitPiece+44
    lda.l SourceNextEmit_Cursor
    sta.l SourceNextEmit_DebugEmitPiece+40
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_X
    sta.l SourceNextEmit_Buffer,x
    lda.l SourceNextEmit_Y
    sta.l SourceNextEmit_Buffer+1,x
    lda.l SourceNextEmit_Tile
    sta.l SourceNextEmit_Buffer+2,x
    lda.l SourceNextEmit_Attr
    sta.l SourceNextEmit_Buffer+3,x
    rep #$31
.a16
.i16
    lda.l SourceNextEmit_Cursor
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_Hi
    sta.l SourceNextEmit_ExpandedHi,x
    rep #$31
.a16
.i16
    lda.l SourceNextEmit_Cursor
    clc
    adc #4
    sta.l SourceNextEmit_Cursor
    sta.l SourceNextEmit_DebugEmitPiece+42
    plp
    rts

; Scratch labels are explicit WRAM addresses above.

; Production main-loop poll seam. Field-paced relay waits accumulate real
; native edges separately; merge once here so a short A/Y pulse cannot vanish
; before the existing native player services get their main-loop turn.

SourceNextPacket_PlayerMeta:
.a16
.i16
    tdc
    cmp #$0A00
    bne SourceNextPacket_LongBranch0
    brl SourceNextPacket_PlayerMeta__p1
SourceNextPacket_LongBranch0:
.a16
.i16
    cmp #$0A85
    beq SourceNextPacket_LongBranch1
    brl SourceNextPacket_PlayerMeta__none
SourceNextPacket_LongBranch1:
.a16
.i16
    ldx #32
    sec
    rts
SourceNextPacket_PlayerMeta__p1:
.a16
.i16
    ldx #0
    sec
    rts
SourceNextPacket_PlayerMeta__none:
.a16
.i16
    clc
    rts

SourceNextPacket_EmitStart:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceNextPacket_EmitStart__campaign3
    brl SourceNextPacket_EmitStart__done
SourceNextPacket_EmitStart__campaign3:
.a16
.i16
    jsr SourceNextPacket_PlayerMeta
    bcs SourceNextPacket_LongBranch2
    brl SourceNextPacket_EmitStart__done
SourceNextPacket_LongBranch2:
.a16
.i16
    lda #0
    sta.l SourceNextEmit_Meta+16,x
    lda.l SourceNextEmit_Cursor
    sta.l SourceNextEmit_Meta,x
SourceNextPacket_EmitStart__done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

SourceNextPacket_EmitFinish:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceNextPacket_EmitFinish__campaign3
    brl SourceNextPacket_EmitFinish__done
SourceNextPacket_EmitFinish__campaign3:
.a16
.i16
    jsr SourceNextPacket_PlayerMeta
    bcc SourceNextPacket_LongBranch3
    brl SourceNextPacket_EmitFinish__player
SourceNextPacket_LongBranch3:
.a16
.i16
    brl SourceNextPacket_EmitFinish__done
SourceNextPacket_EmitFinish__player:
.a16
.i16
    lda.l SourceNextEmit_Cursor
    cmp.l SourceNextEmit_Meta,x
    beq SourceNextPacket_LongBranch4
    brl SourceNextPacket_EmitFinish__has_bytes
SourceNextPacket_LongBranch4:
.a16
.i16
    brl SourceNextPacket_EmitFinish__done
SourceNextPacket_EmitFinish__has_bytes:
.a16
.i16
    sta.l SourceNextEmit_Meta+2,x
    lda.l SourceNextEmit_EmitBaseX
    sta.l SourceNextEmit_Meta+4,x
    lda.l SourceNextEmit_EmitBaseY
    sta.l SourceNextEmit_Meta+6,x
    lda CHAR_ROSTER_INDEX
    and #$00FF
    sta.l SourceNextEmit_Meta+8,x
    lda.l Game_StageIndex
    sta.l SourceNextEmit_Meta+10,x
    lda.l SourceVisual_EntryScratch
    sta.l SourceNextEmit_Meta+12,x
    lda.l SourceVisual_EntryScratch+2
    sta.l SourceNextEmit_Meta+14,x
    lda CHAR_FACING_LEFT
    and #$00FF
    sta.l SourceNextEmit_Meta+18,x
    lda.l SourceVisual_EntryScratch+4
    sta.l SourceNextEmit_Meta+20,x
    lda.l SourceVisual_EntryScratch+8
    sta.l SourceNextEmit_Meta+22,x
    cpx #0
    beq SourceNextPacket_LongBranch5
    brl SourceNextPacket_EmitFinish__p2_family
SourceNextPacket_LongBranch5:
.a16
.i16
    lda.l $7E19E4
    bra SourceNextPacket_EmitFinish__family
SourceNextPacket_EmitFinish__p2_family:
.a16
.i16
    lda.l $7E1AE4
SourceNextPacket_EmitFinish__family:
.a16
.i16
    sta.l SourceNextEmit_Meta+24,x
    lda CHAR_SELECTED
    and #$00FF
    sta.l SourceNextEmit_Meta+26,x
    lda #0
    sta.l SourceNextEmit_Meta+28,x
    sta.l SourceNextEmit_Meta+30,x
    lda #1
    sta.l SourceNextEmit_Meta+16,x
SourceNextPacket_EmitFinish__done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl


SourceNextEmit_End:


; Hardware high-table bytes and per-byte ownership masks. The publisher must
; merge these masks with the visible scene; unowned neighbor bits stay intact.
SourceNextEmit_PackedHi = $4367C0
SourceNextEmit_HighMask = $4367E0
SourceNextEmit_PackSrc = $4367A0
SourceNextEmit_PackDst = $4367A2
SourceNextEmit_PackTemp = $4367A4
SourceNextEmit_MaskSprite = $4367A6
SourceNextEmit_MaskEnd = $4367A8
SourceNextEmit_MaskTemp = $4367AA
SourceNextEmit_PackAllHigh:
    php
    rep #$31
.a16
    lda #0
    sta.l SourceNextEmit_PackSrc
    sta.l SourceNextEmit_PackDst

    ; Only pack the groups Core_Oam_Play will actually DMA this frame --
    ; ceil(Oam_CurrentSlot/16) hi-table bytes, same formula as its DMA
    ; length -- instead of always walking the full 32 groups (128
    ; sprites) regardless of how many are active. This loop, unbounded,
    ; was (together with Core_Oam_ClearAll's own full-128 walk) the
    ; dominant per-frame cost pushing Core_Nmi_Play's vblank commit past
    ; real vblank -- see Core_Oam_ClearActive's header for the full story.
    lda.l SourceNextEmit_Cursor
    clc
    adc #15
    lsr a
    lsr a
    lsr a
    lsr a
    beq SourceNextEmit_PackAllHigh__done   ; nothing active -- nothing to pack
    tay
SourceNextEmit_PackAllHigh__loop:
    lda.l SourceNextEmit_PackSrc
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_ExpandedHi,x
    and #$03
    sta.l SourceNextEmit_PackTemp              ; packed = sprite0's 2 bits (bits 1-0)

    lda.l SourceNextEmit_ExpandedHi+1,x
    and #$03
    asl a
    asl a                               ; sprite1's bits -> bits 3-2
    ora.l SourceNextEmit_PackTemp
    sta.l SourceNextEmit_PackTemp

    lda.l SourceNextEmit_ExpandedHi+2,x
    and #$03
    asl a
    asl a
    asl a
    asl a                               ; sprite2's bits -> bits 5-4
    ora.l SourceNextEmit_PackTemp
    sta.l SourceNextEmit_PackTemp

    lda.l SourceNextEmit_ExpandedHi+3,x
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                               ; sprite3's bits -> bits 7-6
    ora.l SourceNextEmit_PackTemp
    sta.l SourceNextEmit_PackTemp

    rep #$31
.a16
    lda.l SourceNextEmit_PackDst
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_PackTemp
    sta.l SourceNextEmit_PackedHi,x                ; long-indexed-X: a real opcode

    rep #$31
.a16
    lda.l SourceNextEmit_PackSrc
    clc
    adc #4
    sta.l SourceNextEmit_PackSrc
    lda.l SourceNextEmit_PackDst
    inc a
    sta.l SourceNextEmit_PackDst
    dey
    bne SourceNextEmit_PackAllHigh__loop
SourceNextEmit_PackAllHigh__done:
    plp
    rts

; Internal foreground helper, after the guarded private builder.
SourceNextEmit_MaskHigh:
.a16
.i16
    rep #$31
    cld
    lda #0
    ldx #0
SourceNextEmit_MaskClear:
.a16
.i16
    sta.l SourceNextEmit_HighMask,x
    inx
    inx
    cpx #32
    bcc SourceNextEmit_MaskClear
    jsr SourceNextPacket_PlayerMeta
    bcs SourceNextEmit_MaskGuard0
    brl SourceNextEmit_MaskNo
SourceNextEmit_MaskGuard0:
.a16
.i16
    lda.l SourceNextEmit_Meta+16,x
    cmp #1
    beq SourceNextEmit_MaskGuard1
    brl SourceNextEmit_MaskNo
SourceNextEmit_MaskGuard1:
.a16
.i16
    lda.l SourceNextEmit_Meta+2,x
    cmp #513
    bcc SourceNextEmit_MaskGuard2
    brl SourceNextEmit_MaskNo
SourceNextEmit_MaskGuard2:
.a16
.i16
    and #3
    beq SourceNextEmit_MaskGuard3
    brl SourceNextEmit_MaskNo
SourceNextEmit_MaskGuard3:
.a16
.i16
    lda.l SourceNextEmit_Meta,x
    cmp.l SourceNextEmit_Meta+2,x
    bcc SourceNextEmit_MaskGuard4
    brl SourceNextEmit_MaskNo
SourceNextEmit_MaskGuard4:
.a16
.i16
    and #3
    beq SourceNextEmit_MaskGuard5
    brl SourceNextEmit_MaskNo
SourceNextEmit_MaskGuard5:
.a16
.i16
    lda.l SourceNextEmit_Meta,x
    lsr a
    lsr a
    sta.l SourceNextEmit_MaskSprite
    lda.l SourceNextEmit_Meta+2,x
    lsr a
    lsr a
    sta.l SourceNextEmit_MaskEnd
SourceNextEmit_MaskLoop:
.a16
.i16
    lda.l SourceNextEmit_MaskSprite
    cmp.l SourceNextEmit_MaskEnd
    bcs SourceNextEmit_MaskYes
    and #3
    asl a
    tax
    lda.l SourceNextEmit_HighMasks,x
    sta.l SourceNextEmit_MaskTemp
    lda.l SourceNextEmit_MaskSprite
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l SourceNextEmit_HighMask,x
    ora.l SourceNextEmit_MaskTemp
    sta.l SourceNextEmit_HighMask,x
    rep #$20
.a16
    lda.l SourceNextEmit_MaskSprite
    inc a
    sta.l SourceNextEmit_MaskSprite
    bra SourceNextEmit_MaskLoop
SourceNextEmit_MaskYes:
.a16
.i16
    sec
    rts
SourceNextEmit_MaskNo:
.a16
.i16
    clc
    rts
SourceNextEmit_HighMasks:
    .dw 3,12,48,192
SourceNextEmit_PackedEnd:
