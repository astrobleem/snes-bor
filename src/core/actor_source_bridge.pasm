; Bounded production-world field interface, not a second entity allocator.
; Not yet included in main: tick/spawn consumers must be connected before use.
; D=source scheduler page, DBR0,A16/I16,decimal clear. X/Y clobbered.
; Linker provides CHAR_* and StageEnv_* from the actual production symbols.
; Per actual133-byte StageEnv row: +64 policy(1 exact),+65 exists,
; +66 displayed HP word,+68 bound scheduler DP word,+70 target entity DP word.
; Scheduler7A=row byte offset; working fields14/16/18,F0,F6 are imported
; from the SAME production slot on every world pass, never allocated here.
; Scratch78,7C,80..8A. Source position is production position*5/4, only
; admitted on the exact integral lattice; no recovery from rounded spawn data.
; Source spawn provenance must independently establish the initial lattice.
; General fractional movement and health outside0..255 fail closed.
; FC:1 policy/binding,10 unsupported coordinate/base,12 health/existence width.
S6Bridge_Policy = StageEnv_Actors+64
S6Bridge_Exists = StageEnv_Actors+65
S6Bridge_DisplayedHealth = StageEnv_Actors+66
S6Bridge_Context = StageEnv_Actors+68
S6Bridge_TargetHandle = StageEnv_Actors+70

S6Bridge_Resolve:
    rep #$30
    .a16
    .i16
    ldx $7A
    ldy #6
    txa
S6Bridge_Resolve__row:
    .a16
    .i16
    cmp #0
    beq S6Bridge_Resolve__valid_row
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Bridge_Resolve__bad
    dey
    bne S6Bridge_Resolve__row
    bra S6Bridge_Resolve__bad
S6Bridge_Resolve__valid_row:
    .a16
    .i16
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    bne S6Bridge_Resolve__bad
    tdc
    cmp.l S6Bridge_Context,x
    bne S6Bridge_Resolve__bad
    clc
    rtl
S6Bridge_Resolve__bad:
    .a16
    .i16
    lda #1
    sta $FC
    sec
    rtl

S6Bridge_Import:
    rep #$30
    .a16
    .i16
    jsl S6Bridge_Resolve
    bcc S6Bridge_Import__bound
    rtl
S6Bridge_Import__bound:
    .a16
    .i16
    lda.l $7E0A00+CHAR_GRAB_TARGET,x
    and #$00FF
    cmp #$FF
    bne S6Bridge_Import__linked
    lda.l $7E0A00+CHAR_GRABBED_BY,x
    and #$00FF
    cmp #$FF
    bne S6Bridge_Import__linked
    stz $C4                  ; proven unlinked in the actual world, not guessed
    lda.l StageEnv_BaseFraction,x
    bne S6Bridge_Import__numeric
    lda.l $7E0A00+CHAR_THROW_ZPOS,x
    ora.l $7E0A00+CHAR_THROW_ZVEL,x
    bne S6Bridge_Import__numeric
    lda.l $7E0A00+CHAR_POS_X,x
    jsl S6Bridge_Unproject
    bcs S6Bridge_Import__numeric
    sta $78
    lda.l $7E0A00+CHAR_POS_Y,x
    jsl S6Bridge_Unproject
    bcs S6Bridge_Import__numeric
    sta $7C
    lda $78
    sta $14
    lda $7C
    sta $16
    lda.l StageEnv_BaseInteger,x
    sta $18
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    sta $F0
    lda.l S6Bridge_Exists,x
    and #$00FF
    sta $F6
    lda.l S6Bridge_DisplayedHealth,x
    sta $70
    lda.l $7E0A00+CHAR_FACING_LEFT,x
    and #$00FF
    beq S6Bridge_Import__right
    stz $1A
    rtl
S6Bridge_Import__right:
    .a16
    .i16
    lda #1
    sta $1A
    rtl
S6Bridge_Import__numeric:
    .a16
    .i16
    lda #10
    sta $FC
    rtl
S6Bridge_Import__linked:
    .a16
    .i16
    lda #4
    sta $FC
    rtl

; Validate all outgoing scalar fields before mutating production world state.
S6Bridge_Export:
    rep #$30
    .a16
    .i16
    lda $FC
    beq S6Bridge_Export__resolve
    rtl
S6Bridge_Export__resolve:
    .a16
    .i16
    jsl S6Bridge_Resolve
    bcs S6Bridge_Export__done
    lda $F0
    cmp #256
    bcs S6Bridge_Export__width
    lda $F6
    cmp #2
    bcs S6Bridge_Export__width
    lda $1A
    cmp #2
    bcs S6Bridge_Export__width
    lda $18
    cmp.l StageEnv_BaseInteger,x
    bne S6Bridge_Export__numeric
    lda $14
    jsl S6Bridge_Project
    bcs S6Bridge_Export__numeric
    sta $88
    lda $16
    jsl S6Bridge_Project
    bcs S6Bridge_Export__numeric
    sta $8A
    ldx $7A
    lda $88
    sta.l $7E0A00+CHAR_POS_X,x
    lda $8A
    sta.l $7E0A00+CHAR_POS_Y,x
    lda $70
    sta.l S6Bridge_DisplayedHealth,x
    sep #$20
    .a8
    lda $F0
    sta.l $7E0A00+CHAR_HP,x
    lda $F6
    sta.l S6Bridge_Exists,x
    lda $1A
    beq S6Bridge_Export__left
    lda #0
    bra S6Bridge_Export__facing
S6Bridge_Export__left:
    .a8
    .i16
    lda #1
S6Bridge_Export__facing:
    .a8
    .i16
    sta.l $7E0A00+CHAR_FACING_LEFT,x
    rep #$30
    .a16
    .i16
S6Bridge_Export__done:
    .a16
    .i16
    rtl
S6Bridge_Export__width:
    .a16
    .i16
    lda #12
    sta $FC
    rtl
S6Bridge_Export__numeric:
    .a16
    .i16
    lda #10
    sta $FC
    rtl

; Signed target integer -> source integer; carry set rejects non-lattice
; values or values beyond the target selection proof's source-coordinate bound.
S6Bridge_Unproject:
    .a16
    .i16
    sta $80
    and #3
    bne S6Bridge_Unproject__bad
    lda $80
    clc
    adc #3276
    cmp #6553
    bcs S6Bridge_Unproject__bad
    lda $80
    cmp #$8000
    ror a
    cmp #$8000
    ror a
    sta $82
    asl a
    asl a
    clc
    adc $82
    clc
    rtl
S6Bridge_Unproject__bad:
    .a16
    .i16
    sec
    rtl

; Signed source integer -> production integer on the admitted5-pixel lattice.
; Exact bounded integer conversion, not floating evaluation or approximation.
; abs(n)=256*h+l, 256=51*5+1, hence n/5=51*h+(h+l)/5.
; h<=15 and h+l<=270. Tables reject every nonzero remainder. No hardware
; divider ownership/NMI dependency. X preserved; Y/scratch clobbered as before.
S6Bridge_Project:
    .a16
    .i16
    phx
    sta $80
    clc
    adc #4095
    cmp #8191
    bcs S6Bridge_Project__bad
    stz $86
    lda $80
    bpl S6Bridge_Project__positive
    inc $86
    eor #$FFFF
    inc a
S6Bridge_Project__positive:
    .a16
    .i16
    sta $80
    xba
    and #$000F
    sta $82
    asl a
    tax
    lda.l S6Bridge_ProjectHigh,x
    sta $84
    lda $80
    and #$00FF
    clc
    adc $82
    asl a
    tax
    lda.l S6Bridge_ProjectLow,x
    bmi S6Bridge_Project__bad
    clc
    adc $84
    ldy $86
    beq S6Bridge_Project__done
    eor #$FFFF
    inc a
S6Bridge_Project__done:
    .a16
    .i16
    plx
    clc
    rtl
S6Bridge_Project__bad:
    .a16
    .i16
    plx
    sec
    rtl

S6Bridge_ProjectHigh:
    .dw $0000,$00CC,$0198,$0264,$0330,$03FC,$04C8,$0594,$0660,$072C,$07F8,$08C4
    .dw $0990,$0A5C,$0B28,$0BF4
S6Bridge_ProjectLow:
    .dw $0000,$8000,$8000,$8000,$8000,$0004,$8000,$8000,$8000,$8000,$0008,$8000
    .dw $8000,$8000,$8000,$000C,$8000,$8000,$8000,$8000,$0010,$8000,$8000,$8000
    .dw $8000,$0014,$8000,$8000,$8000,$8000,$0018,$8000,$8000,$8000,$8000,$001C
    .dw $8000,$8000,$8000,$8000,$0020,$8000,$8000,$8000,$8000,$0024,$8000,$8000
    .dw $8000,$8000,$0028,$8000,$8000,$8000,$8000,$002C,$8000,$8000,$8000,$8000
    .dw $0030,$8000,$8000,$8000,$8000,$0034,$8000,$8000,$8000,$8000,$0038,$8000
    .dw $8000,$8000,$8000,$003C,$8000,$8000,$8000,$8000,$0040,$8000,$8000,$8000
    .dw $8000,$0044,$8000,$8000,$8000,$8000,$0048,$8000,$8000,$8000,$8000,$004C
    .dw $8000,$8000,$8000,$8000,$0050,$8000,$8000,$8000,$8000,$0054,$8000,$8000
    .dw $8000,$8000,$0058,$8000,$8000,$8000,$8000,$005C,$8000,$8000,$8000,$8000
    .dw $0060,$8000,$8000,$8000,$8000,$0064,$8000,$8000,$8000,$8000,$0068,$8000
    .dw $8000,$8000,$8000,$006C,$8000,$8000,$8000,$8000,$0070,$8000,$8000,$8000
    .dw $8000,$0074,$8000,$8000,$8000,$8000,$0078,$8000,$8000,$8000,$8000,$007C
    .dw $8000,$8000,$8000,$8000,$0080,$8000,$8000,$8000,$8000,$0084,$8000,$8000
    .dw $8000,$8000,$0088,$8000,$8000,$8000,$8000,$008C,$8000,$8000,$8000,$8000
    .dw $0090,$8000,$8000,$8000,$8000,$0094,$8000,$8000,$8000,$8000,$0098,$8000
    .dw $8000,$8000,$8000,$009C,$8000,$8000,$8000,$8000,$00A0,$8000,$8000,$8000
    .dw $8000,$00A4,$8000,$8000,$8000,$8000,$00A8,$8000,$8000,$8000,$8000,$00AC
    .dw $8000,$8000,$8000,$8000,$00B0,$8000,$8000,$8000,$8000,$00B4,$8000,$8000
    .dw $8000,$8000,$00B8,$8000,$8000,$8000,$8000,$00BC,$8000,$8000,$8000,$8000
    .dw $00C0,$8000,$8000,$8000,$8000,$00C4,$8000,$8000,$8000,$8000,$00C8,$8000
    .dw $8000,$8000,$8000,$00CC,$8000,$8000,$8000,$8000,$00D0,$8000,$8000,$8000
    .dw $8000,$00D4,$8000,$8000,$8000,$8000,$00D8
