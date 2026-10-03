; Bounded production-world field interface, not a second entity allocator.
; Not yet included in main: tick/spawn consumers must be connected before use.
; D=source scheduler page, DBR0,A16/I16,decimal clear. X/Y clobbered.
; Linker provides CHAR_* and StageEnv_* from the actual production symbols.
; Per actual133-byte StageEnv row: +64 policy(1 exact,2 Normal rounded),+65 exists,
; +66 displayed HP word,+68 bound scheduler DP word,+70 target entity DP word.
; Scheduler7A=row byte offset; working fields14/16/18,F0,F6 are imported
; from the SAME production slot on every world pass, never allocated here.
; Bridge temporaries live in reserved globals $17E0-$17EF, not in the caller's
; direct page: Normal's 133-byte native entity stride means a scheduler D at
; $0A00 would otherwise make scratch $80-$8A overwrite the next OOP header.
; Policy 1 requires the exact integral lattice. Normal policy 2 mirrors its
; compiler's nearest 4/5 spawn-coordinate rounding.
; Both policies admit source-world coordinates through +/-8191 and native
; coordinates through +/-6553, matching the world target-selection proof.
; General fractional movement and health outside0..255 fail closed.
; FC:1 policy/binding,10 unsupported coordinate/base,12 health/existence width.
S6Bridge_Policy = StageEnv_Actors+64
S6Bridge_Exists = StageEnv_Actors+65
S6Bridge_DisplayedHealth = StageEnv_Actors+66
S6Bridge_Context = StageEnv_Actors+68
S6Bridge_TargetHandle = StageEnv_Actors+70
S6Bridge_Temp78 = $7E17E0
S6Bridge_Temp7C = $7E17E2
S6Bridge_Temp80 = $7E17E4
S6Bridge_Temp82 = $7E17E6
S6Bridge_Temp84 = $7E17E8
S6Bridge_Temp86 = $7E17EA
S6Bridge_Temp88 = $7E17EC
S6Bridge_Temp8A = $7E17EE

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
    beq S6Bridge_Resolve__policy_valid
    cmp #2
    bne S6Bridge_Resolve__bad
S6Bridge_Resolve__policy_valid:
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

; Policy dispatchers preserve the public exact-only projection routines.
; $7A is the current StageEnv row byte offset for both bind and tick paths.
S6Bridge_UnprojectPolicy:
    .a16
    .i16
    phx
    pha
    ldx $7A
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #2
    beq S6Bridge_UnprojectPolicy__rounded
    pla
    plx
    jml S6Bridge_Unproject
S6Bridge_UnprojectPolicy__rounded:
    pla
    plx
    jml S6Bridge_UnprojectRounded

S6Bridge_ProjectPolicy:
    .a16
    .i16
    phx
    pha
    ldx $7A
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #2
    beq S6Bridge_ProjectPolicy__rounded
    pla
    plx
    jml S6Bridge_Project
S6Bridge_ProjectPolicy__rounded:
    pla
    plx
    jml S6Bridge_ProjectRounded

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
    beq S6Bridge_Import__grab_target_clear
    brl S6Bridge_Import__linked
S6Bridge_Import__grab_target_clear:
    lda.l $7E0A00+CHAR_GRABBED_BY,x
    and #$00FF
    cmp #$FF
    beq S6Bridge_Import__grabbed_by_clear
    brl S6Bridge_Import__linked
S6Bridge_Import__grabbed_by_clear:
    stz $C4                  ; proven unlinked in the actual world, not guessed
    ; A child may inherit a fixed fractional environment base. BOR's admitted
    ; combat coordinates and renderer consume BaseInteger only; BaseFraction
    ; changes only on the typed steam-emitter callback, which is not admitted
    ; as a combat actor. Preserve the fractional metadata for that S-CPU
    ; service without rejecting the child's otherwise exact source state.
    lda.l $7E0A00+CHAR_THROW_ZPOS,x
    ora.l $7E0A00+CHAR_THROW_ZVEL,x
    bne S6Bridge_Import__height_check
    brl S6Bridge_Import__height_ok
    ; Normal's real player jump remains the existing S-CPU player-action
    ; substate: Jump_PlayerTick owns its Z integration and the renderer reads
    ; these same per-entity fields. The persistent world owns ground X/Y and
    ; deliberately neither imports nor exports player height. Do not extend
    ; this exception to thrown, hole, or other airborne entities; those still
    ; require a source-world capability and fail closed here.
S6Bridge_Import__height_check:
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    cmp #1
    beq S6Bridge_Import__height_input_ok
    brl S6Bridge_Import__height_bad
S6Bridge_Import__height_input_ok:
    lda.l $7E0A00+CHAR_SELECTED,x
    cmp #CHAR_SELECTED_JUMP
    beq S6Bridge_Import__height_check_valid
    brl S6Bridge_Import__height_bad
S6Bridge_Import__height_check_valid:
    rep #$30
    .a16
    .i16
S6Bridge_Import__height_ok:
    ; A real player jump remains native BOR state. Mirror only its active
    ; discriminator into the worker so grounded source movement pauses during
    ; the jump; native CHAR_SELECTED/Z fields are never snapshot-overwritten.
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_SELECTED,x
    cmp #CHAR_SELECTED_JUMP
    bne S6Bridge_Import__height_not_jump
    sta CHAR_SELECTED
    rep #$30
    .a16
    .i16
    bra S6Bridge_Import__height_synced
S6Bridge_Import__height_not_jump:
    .a8
    .i16
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    beq S6Bridge_Import__worker_jump_active
    brl S6Bridge_Import__height_synced
S6Bridge_Import__worker_jump_active:
    rep #$30
    .a16
    .i16
    lda.l $7E0A00+CHAR_THROW_ZPOS,x
    ora.l $7E0A00+CHAR_THROW_ZVEL,x
    bne S6Bridge_Import__height_synced
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_SELECTED,x
    sta CHAR_SELECTED
    rep #$30
    .a16
    .i16
S6Bridge_Import__height_synced:
    ; Both branches from the byte-sized jump discriminator converge here.
    ; The coordinate projection and all following source-world fields are
    ; 16-bit, so restore the caller's normal A16/I16 mode before importing.
    rep #$30
    .a16
    .i16
    lda.l $7E0A00+CHAR_POS_X,x
    jsl S6Bridge_UnprojectPolicy
    bcs S6Bridge_Import__numeric
    sta.l S6Bridge_Temp78
    lda.l $7E0A00+CHAR_POS_Y,x
    jsl S6Bridge_UnprojectPolicy
    bcs S6Bridge_Import__numeric
    sta.l S6Bridge_Temp7C
    lda.l S6Bridge_Temp78
    sta $14
    lda.l S6Bridge_Temp7C
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
S6Bridge_Import__height_bad:
    rep #$30
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
    jsl S6Bridge_ProjectPolicy
    bcs S6Bridge_Export__numeric
    sta.l S6Bridge_Temp88
    lda $16
    jsl S6Bridge_ProjectPolicy
    bcs S6Bridge_Export__numeric
    sta.l S6Bridge_Temp8A
    ldx $7A
    lda.l S6Bridge_Temp88
    sta.l $7E0A00+CHAR_POS_X,x
    lda.l S6Bridge_Temp8A
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

; Normal policy 2: nearest signed 5/4 inverse. The half case rounds away from
; zero so the paired 4/5 projection maps every native integer back to itself.
S6Bridge_UnprojectRounded:
    .a16
    .i16
    sta.l S6Bridge_Temp80
    clc
    adc #6553
    cmp #13107
    bcs S6Bridge_Unproject__bad
    lda #0
    sta.l S6Bridge_Temp86
    lda.l S6Bridge_Temp80
    bpl S6Bridge_UnprojectRounded__magnitude
    pha
    lda.l S6Bridge_Temp86
    inc a
    sta.l S6Bridge_Temp86
    pla
    eor #$FFFF
    inc a
S6Bridge_UnprojectRounded__magnitude:
    sta.l S6Bridge_Temp80
    asl a
    asl a
    clc
    adc.l S6Bridge_Temp80
    clc
    adc #2
    lsr a
    lsr a
    pha
    lda.l S6Bridge_Temp86
    tay
    pla
    cpy #0
    beq S6Bridge_UnprojectRounded__done
    eor #$FFFF
    inc a
S6Bridge_UnprojectRounded__done:
    clc
    rtl

; Signed target integer -> source integer; carry set rejects non-lattice
; values on policy 1 or values beyond the target selection proof's bound.
S6Bridge_Unproject:
    .a16
    .i16
    sta.l S6Bridge_Temp80
    and #3
    bne S6Bridge_Unproject__bad
    lda.l S6Bridge_Temp80
    clc
    adc #6553
    cmp #13107
    bcs S6Bridge_Unproject__bad
    lda.l S6Bridge_Temp80
    cmp #$8000
    ror a
    cmp #$8000
    ror a
    sta.l S6Bridge_Temp82
    asl a
    asl a
    clc
    adc.l S6Bridge_Temp82
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
; h<=31 and h+l<=286. Tables reject every nonzero remainder. No hardware
; divider ownership/NMI dependency. X preserved; Y/scratch clobbered as before.
S6Bridge_Project:
    .a16
    .i16
    phx
    sta.l S6Bridge_Temp80
    clc
    adc #8191
    cmp #16383
    bcs S6Bridge_Project__bad
    lda #0
    sta.l S6Bridge_Temp86
    lda.l S6Bridge_Temp80
    bpl S6Bridge_Project__positive
    pha
    lda.l S6Bridge_Temp86
    inc a
    sta.l S6Bridge_Temp86
    pla
    eor #$FFFF
    inc a
S6Bridge_Project__positive:
    .a16
    .i16
    sta.l S6Bridge_Temp80
    xba
    and #$001F
    sta.l S6Bridge_Temp82
    asl a
    tax
    lda.l S6Bridge_ProjectHigh,x
    sta.l S6Bridge_Temp84
    lda.l S6Bridge_Temp80
    and #$00FF
    clc
    adc.l S6Bridge_Temp82
    asl a
    tax
    lda.l S6Bridge_ProjectLow,x
    bmi S6Bridge_Project__bad
    clc
    adc.l S6Bridge_Temp84
    pha
    lda.l S6Bridge_Temp86
    tay
    pla
    cpy #0
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

; Normal policy 2: nearest 4/5 projection. abs(n)=256*h+l and
; 4*n/5=204*h+4*(h+l)/5. The compact second table avoids a divider in the
; per-tick export path. Policy 1 continues to use the exact-only table below.
S6Bridge_ProjectRounded:
    .a16
    .i16
    phx
    sta.l S6Bridge_Temp80
    clc
    adc #8191
    cmp #16383
    bcs S6Bridge_ProjectRounded__bad
    lda #0
    sta.l S6Bridge_Temp86
    lda.l S6Bridge_Temp80
    bpl S6Bridge_ProjectRounded__positive
    pha
    lda.l S6Bridge_Temp86
    inc a
    sta.l S6Bridge_Temp86
    pla
    eor #$FFFF
    inc a
S6Bridge_ProjectRounded__positive:
    sta.l S6Bridge_Temp80
    xba
    and #$001F
    sta.l S6Bridge_Temp82
    asl a
    tax
    lda.l S6Bridge_ProjectHigh,x
    sta.l S6Bridge_Temp84
    lda.l S6Bridge_Temp80
    and #$00FF
    clc
    adc.l S6Bridge_Temp82
    asl a
    tax
    lda.l S6Bridge_ProjectRoundedLow,x
    clc
    adc.l S6Bridge_Temp84
    pha
    lda.l S6Bridge_Temp86
    tay
    pla
    cpy #0
    beq S6Bridge_ProjectRounded__done
    eor #$FFFF
    inc a
S6Bridge_ProjectRounded__done:
    plx
    clc
    rtl
S6Bridge_ProjectRounded__bad:
    plx
    sec
    rtl

S6Bridge_ProjectHigh:
    .dw $0000,$00CC,$0198,$0264,$0330,$03FC,$04C8,$0594,$0660,$072C,$07F8,$08C4
    .dw $0990,$0A5C,$0B28,$0BF4
    .dw $0CC0,$0D8C,$0E58,$0F24,$0FF0,$10BC,$1188,$1254
    .dw $1320,$13EC,$14B8,$1584,$1650,$171C,$17E8,$18B4
S6Bridge_ProjectRoundedLow:
    .dw $0000,$0001,$0002,$0002,$0003,$0004,$0005,$0006,$0006,$0007,$0008,$0009,$000a,$000a,$000b,$000c
    .dw $000d,$000e,$000e,$000f,$0010,$0011,$0012,$0012,$0013,$0014,$0015,$0016,$0016,$0017,$0018,$0019
    .dw $001a,$001a,$001b,$001c,$001d,$001e,$001e,$001f,$0020,$0021,$0022,$0022,$0023,$0024,$0025,$0026
    .dw $0026,$0027,$0028,$0029,$002a,$002a,$002b,$002c,$002d,$002e,$002e,$002f,$0030,$0031,$0032,$0032
    .dw $0033,$0034,$0035,$0036,$0036,$0037,$0038,$0039,$003a,$003a,$003b,$003c,$003d,$003e,$003e,$003f
    .dw $0040,$0041,$0042,$0042,$0043,$0044,$0045,$0046,$0046,$0047,$0048,$0049,$004a,$004a,$004b,$004c
    .dw $004d,$004e,$004e,$004f,$0050,$0051,$0052,$0052,$0053,$0054,$0055,$0056,$0056,$0057,$0058,$0059
    .dw $005a,$005a,$005b,$005c,$005d,$005e,$005e,$005f,$0060,$0061,$0062,$0062,$0063,$0064,$0065,$0066
    .dw $0066,$0067,$0068,$0069,$006a,$006a,$006b,$006c,$006d,$006e,$006e,$006f,$0070,$0071,$0072,$0072
    .dw $0073,$0074,$0075,$0076,$0076,$0077,$0078,$0079,$007a,$007a,$007b,$007c,$007d,$007e,$007e,$007f
    .dw $0080,$0081,$0082,$0082,$0083,$0084,$0085,$0086,$0086,$0087,$0088,$0089,$008a,$008a,$008b,$008c
    .dw $008d,$008e,$008e,$008f,$0090,$0091,$0092,$0092,$0093,$0094,$0095,$0096,$0096,$0097,$0098,$0099
    .dw $009a,$009a,$009b,$009c,$009d,$009e,$009e,$009f,$00a0,$00a1,$00a2,$00a2,$00a3,$00a4,$00a5,$00a6
    .dw $00a6,$00a7,$00a8,$00a9,$00aa,$00aa,$00ab,$00ac,$00ad,$00ae,$00ae,$00af,$00b0,$00b1,$00b2,$00b2
    .dw $00b3,$00b4,$00b5,$00b6,$00b6,$00b7,$00b8,$00b9,$00ba,$00ba,$00bb,$00bc,$00bd,$00be,$00be,$00bf
    .dw $00c0,$00c1,$00c2,$00c2,$00c3,$00c4,$00c5,$00c6,$00c6,$00c7,$00c8,$00c9,$00ca,$00ca,$00cb,$00cc
    .dw $00cd,$00ce,$00ce,$00cf,$00d0,$00d1,$00d2,$00d2,$00d3,$00d4,$00d5,$00d6,$00d6,$00d7,$00d8
    .dw $00d9,$00da,$00da,$00db,$00dc,$00dd,$00de,$00de
    .dw $00df,$00e0,$00e1,$00e2,$00e2,$00e3,$00e4,$00e5
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
    .dw $8000,$8000,$8000,$8000,$00DC,$8000,$8000,$8000
    .dw $8000,$00E0,$8000,$8000,$8000,$8000,$00E4,$8000
