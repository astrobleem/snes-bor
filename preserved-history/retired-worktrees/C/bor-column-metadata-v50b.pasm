; Immutable BG1 source columns only. Cache rows never contain physical
; tile slots or tilemap words; original ResolveRows validates/touches every
; live tile and retains all enqueue, retirement and camera-clamp fences.
; Existing six actor raw-metadata leases end exactly at $434E00.
SVBG_Columns = $434E00
SVBG_ColumnsEnd = $436600 ; 64 rows * 96 bytes, within existing bank 43
SVBG_Offset = $4325B4
SVBG_Column = $4325B6
SVBG_Hits = $4325B8
SVBG_Misses = $4325BA

SVBG_InitColumns:
    rep #$30
.a16
.i16
    phx
    ldx #0
    lda #0
SVBG_InitColumns__row:
.a16
.i16
    sta.l SVBG_Columns+10,x
    txa
    clc
    adc #96
    tax
    lda #0
    cpx #6144
    bcc SVBG_InitColumns__row
    plx
    rtl

SVBG_Scope:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVBG_Scope__no
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVBG_Scope__no
    lda.l Game_State
    cmp #GAME_STATE_PLAYING
    bne SVBG_Scope__no
    lda.l StreamStage_ColStrideLo
    beq SVBG_Scope__no
    cmp #85
    bcs SVBG_Scope__no
    sec
    rts
SVBG_Scope__no:
.a16
.i16
    clc
    rts

; Caller X is the complete source world-column ID. Preserve X, Y and DBR
; even on a hit so the surrounding original routine keeps its register ABI.
SVBG_LoadColumn:
    rep #$31
.a16
.i16
    phx
    phy
    phb
    jsr SVBG_Scope
    bcs SVBG_LoadColumn__scope
    brl SVBG_LoadColumn__miss_return
SVBG_LoadColumn__scope:
.a16
.i16
    txa
    sta.l SVBG_Column
    and #63
    ; slot * 96 = (slot * 2 + slot) * 32
    sta.l SVBG_Offset
    asl a
    clc
    adc.l SVBG_Offset
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SVBG_Offset
    tax
    lda.l SVBG_Columns+10,x
    cmp #$D7B6
    bne SVBG_LoadColumn__miss
    lda.l SVBG_Columns,x
    cmp.l SVBG_Column
    bne SVBG_LoadColumn__miss
    lda.l SVBG_Columns+2,x
    cmp.l Game_StageIndex
    bne SVBG_LoadColumn__miss
    lda.l SVBG_Columns+4,x
    cmp.l StreamScroll_TilemapOffLo
    bne SVBG_LoadColumn__miss
    lda.l StreamScroll_TilemapOffHi
    and #$00FF
    cmp.l SVBG_Columns+6,x
    bne SVBG_LoadColumn__miss
    lda.l SVBG_Columns+8,x
    cmp.l StreamStage_ColStrideLo
    bne SVBG_LoadColumn__miss
    txa
    clc
    adc #$4E0C
    tax
    ldy #StreamStage_Entries
    lda.l StreamStage_ColStrideLo
    dec a
    ; Poppy operands are emitted destination-bank, source-bank.
    mvn $7E,$43
    lda.l SVBG_Hits
    inc a
    sta.l SVBG_Hits
    plb
    ply
    plx
    sec
    rtl
SVBG_LoadColumn__miss:
.a16
.i16
    lda.l SVBG_Misses
    inc a
    sta.l SVBG_Misses
SVBG_LoadColumn__miss_return:
.a16
.i16
    plb
    ply
    plx
    clc
    rtl

; Called only after the original complete MSU read. The full source keys
; and exact payload are published before the final valid word. Foreign or
; oversized columns continue through the original path without cache writes.
SVBG_StoreColumn:
    rep #$31
.a16
.i16
    phx
    phy
    phb
    jsr SVBG_Scope
    bcc SVBG_StoreColumn__done
    lda.l SVBG_Offset
    tax
    lda #0
    sta.l SVBG_Columns+10,x
    txa
    clc
    adc #$4E0C
    tay
    ldx #StreamStage_Entries
    lda.l StreamStage_ColStrideLo
    dec a
    ; Poppy operands are emitted destination-bank, source-bank.
    mvn $43,$7E
    lda.l SVBG_Offset
    tax
    lda.l SVBG_Column
    sta.l SVBG_Columns,x
    lda.l Game_StageIndex
    sta.l SVBG_Columns+2,x
    lda.l StreamScroll_TilemapOffLo
    sta.l SVBG_Columns+4,x
    lda.l StreamScroll_TilemapOffHi
    and #$00FF
    sta.l SVBG_Columns+6,x
    lda.l StreamStage_ColStrideLo
    sta.l SVBG_Columns+8,x
    lda #$D7B6
    sta.l SVBG_Columns+10,x
SVBG_StoreColumn__done:
.a16
.i16
    plb
    ply
    plx
    rtl
