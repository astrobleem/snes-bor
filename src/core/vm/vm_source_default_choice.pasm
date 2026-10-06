; Synchronous ent_default_init first-animation preparation. B4FA is a private
; capability, not complete initialization. Uses the real animation resolver.
; Returned Service=1 requires actual ent_set_anim + nested frame-zero work.
; No candidate is a source no-call, not an implicit idle substitution.
SourceDefaultChoice4086_Ready = $7FFE84
SourceDefaultChoice4086_Slot = $7FFE86
SourceDefaultChoice4086_Status = $7FFE88
SourceDefaultChoice4086_Select = $7FFE8A
SourceDefaultChoice4086_TimeLo = $7FFE8C
SourceDefaultChoice4086_TimeHi = $7FFE8E
SourceDefaultChoice4086_Spawn = $7FFE90
SourceDefaultChoice4086_Respawn = $7FFE92
SourceDefaultChoice4086_Selection = $7FFE94
SourceDefaultChoice4086_Chosen = $7FFE96
SourceDefaultChoice4086_Service = $7FFE98
SourceDefaultChoice4086_Core = $7FFE9A

SourceDefaultChoice4086_Prepare:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceDefaultChoice4086_Ready
    cmp #$B4FA
    beq SourceDefaultChoice4086_Guard_1
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_1:
.a16
.i16
    lda.l SourceDefaultChoice4086_Status
    cmp #3
    bne SourceDefaultChoice4086_Guard_2
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_2:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceDefaultChoice4086_Guard_3
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_3:
.a16
.i16
    lda.l VmSourceWorld_Count
    bne SourceDefaultChoice4086_Guard_4
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_4:
.a16
.i16
    cmp #129
    bcc SourceDefaultChoice4086_Guard_5
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_5:
.a16
.i16
    cmp.l SourceDefaultChoice4086_Slot
    bcs SourceDefaultChoice4086_Guard_6
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_6:
.a16
.i16
    bne SourceDefaultChoice4086_Guard_7
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_7:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Ready
    cmp #$B4EB
    beq SourceDefaultChoice4086_Guard_8
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_8:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Entities
    cmp.l VmSourceWorld_Count
    beq SourceDefaultChoice4086_Guard_9
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_9:
.a16
.i16
    lda.l SourceDefaultChoice4086_Slot
    sta.l SourceAnimationInit4086_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    pha
    asl a
    clc
    adc 1,s
    ply
    sta.l SourceDefaultChoice4086_Core
    tax
    lda #0
    sta.l SourceDefaultChoice4086_Service
    sta.l SourceAnimationInit4086_Reset
    lda #$FFFF
    sta.l SourceDefaultChoice4086_Chosen
    lda.l $40C04A,x
    beq SourceDefaultChoice4086_Guard_10
    jmp SourceDefaultChoice4086_SpawnFirst
SourceDefaultChoice4086_Guard_10:
.a16
.i16
    lda.l $40C048,x
    cmp #1
    beq SourceDefaultChoice4086_Guard_11
    jmp SourceDefaultChoice4086_SpawnFirst
SourceDefaultChoice4086_Guard_11:
.a16
.i16
    lda.l SourceDefaultChoice4086_Select
    beq SourceDefaultChoice4086_Guard_12
    jmp SourceDefaultChoice4086_SelectFirst
SourceDefaultChoice4086_Guard_12:
.a16
.i16
    lda.l SourceDefaultChoice4086_TimeLo
    ora.l SourceDefaultChoice4086_TimeHi
    bne SourceDefaultChoice4086_Guard_13
    jmp SourceDefaultChoice4086_SpawnFirst
SourceDefaultChoice4086_Guard_13:
.a16
.i16
    lda.l SourceDefaultChoice4086_Respawn
    jsr SourceDefaultChoice4086_Try
    bcc SourceDefaultChoice4086_Guard_14
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_14:
.a16
.i16
    lda.l SourceDefaultChoice4086_Service
    beq SourceDefaultChoice4086_Guard_15
    jmp SourceDefaultChoice4086_Done
SourceDefaultChoice4086_Guard_15:
.a16
.i16
    lda.l SourceDefaultChoice4086_Spawn
    jsr SourceDefaultChoice4086_Try
    bcc SourceDefaultChoice4086_Guard_16
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_16:
.a16
.i16
    bra SourceDefaultChoice4086_Done
SourceDefaultChoice4086_SpawnFirst:
.a16
.i16
    lda.l SourceDefaultChoice4086_Spawn
    jsr SourceDefaultChoice4086_Try
    bcc SourceDefaultChoice4086_Guard_17
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_17:
.a16
.i16
    lda.l SourceDefaultChoice4086_Service
    beq SourceDefaultChoice4086_Guard_18
    jmp SourceDefaultChoice4086_Done
SourceDefaultChoice4086_Guard_18:
.a16
.i16
    lda.l SourceDefaultChoice4086_Respawn
    jsr SourceDefaultChoice4086_Try
    bcc SourceDefaultChoice4086_Guard_19
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_19:
.a16
.i16
    bra SourceDefaultChoice4086_Done
SourceDefaultChoice4086_SelectFirst:
.a16
.i16
    lda.l SourceDefaultChoice4086_Selection
    jsr SourceDefaultChoice4086_Try
    bcc SourceDefaultChoice4086_Guard_20
    jmp SourceDefaultChoice4086_Bad
SourceDefaultChoice4086_Guard_20:
.a16
.i16
SourceDefaultChoice4086_Done:
.a16
.i16
    lda #2
    sta.l SourceDefaultChoice4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceDefaultChoice4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceDefaultChoice4086_Status
    ply
    plx
    plp
    sec
    rtl
SourceDefaultChoice4086_Try:
.a16
.i16
    sta.l SourceAnimationInit4086_Number
    jsl SourceAnimationInit4086_Resolve
    bcs SourceDefaultChoice4086_TryBad
    lda.l SourceAnimationInit4086_Handle
    beq SourceDefaultChoice4086_TryGood
    lda.l SourceAnimationInit4086_Count
    beq SourceDefaultChoice4086_TryGood
    lda.l SourceAnimationInit4086_Number
    sta.l SourceDefaultChoice4086_Chosen
    lda #1
    sta.l SourceDefaultChoice4086_Service
SourceDefaultChoice4086_TryGood:
.a16
.i16
    clc
    rts
SourceDefaultChoice4086_TryBad:
.a16
.i16
    sec
    rts
