; DEFAULT_IDLE_ONLY is admitted from the complete cached-model registry:
; max_idles=1, subtype NONE, no FAINT/SLEEP animation in any inheritable model.
; This leaf performs set_idle flags and common_idle movement policy, then
; prepares ent_set_anim(ANI_IDLE,0). Caller must execute the existing native
; animation initializer and any nested frame-zero effects before effect Ack.
; Entity flags lease $43EB00..$43FAFF, 128*32 bytes, all int32:
; idling, inpain, jumping, blocking, reactive, idlemode, sleeptime, weapent token.
; attacking remains in entity core +88. Cached type governs movement, not the
; retained entity type after a weapon/model switch. No bank-0 code or globals.
; Scratch is a synchronous leaf and is never live across a yielded service.
SourceIdle4086_Ready = $7FFDD0
SourceIdle4086_Slot = $7FFDD2
SourceIdle4086_Status = $7FFDD4
SourceIdle4086_Flags = $7FFDD6
SourceIdle4086_Side = $7FFDD8
SourceIdle4086_Core = $7FFDDA
SourceIdle4086_Model = $7FFDDC
SourceIdle4086_Cache = $7FFDDE

SourceIdle4086_Prepare:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceIdle4086_Ready
    cmp #$B4F3
    beq SourceIdle4086_World
    jmp SourceIdle4086_Bad
SourceIdle4086_World:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceIdle4086_Pool
    jmp SourceIdle4086_Bad
SourceIdle4086_Pool:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq SourceIdle4086_SideLease
    jmp SourceIdle4086_Bad
SourceIdle4086_SideLease:
.a16
.i16
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    beq SourceIdle4086_CoreLease
    jmp SourceIdle4086_Bad
SourceIdle4086_CoreLease:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Ready
    cmp #$B4EB
    beq SourceIdle4086_Entities
    jmp SourceIdle4086_Bad
SourceIdle4086_Entities:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Entities
    beq SourceIdle4086_Reject
    cmp #129
    bcs SourceIdle4086_Reject
    cmp.l VmSourceWorld_Count
    bne SourceIdle4086_Reject
    cmp.l SourceIdle4086_Slot
    bcc SourceIdle4086_Reject
    beq SourceIdle4086_Reject
    lda.l SourceModelEntityCopy4086_Models
    beq SourceIdle4086_Reject
    cmp #17
    bcc SourceIdle4086_Offsets
SourceIdle4086_Reject:
.a16
.i16
    jmp SourceIdle4086_Bad
SourceIdle4086_Offsets:
.a16
.i16
    lda.l SourceIdle4086_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceIdle4086_Flags
    asl a
    sta.l SourceIdle4086_Side
    clc
    adc.l SourceIdle4086_Flags
    sta.l SourceIdle4086_Core
    lda.l SourceIdle4086_Flags
    tax
    lda.l $43EB16,x
    bne SourceIdle4086_Reject
    lda.l $43EB14,x
    cmp #2
    bcs SourceIdle4086_Reject
    lda.l SourceIdle4086_Side
    tax
    lda.l $416800,x
    cmp.l SourceModelEntityCopy4086_Models
    bcs SourceIdle4086_Reject
    sta.l SourceIdle4086_Model
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceIdle4086_Cache
    asl a
    asl a
    clc
    adc.l SourceIdle4086_Cache
    sta.l SourceIdle4086_Cache
    lda.l SourceIdle4086_Slot
    sta.l SourceAnimationInit4086_Slot
    lda #0
    sta.l SourceAnimationInit4086_Number
    sta.l SourceAnimationInit4086_Reset
    jsl SourceAnimationInit4086_Resolve
    bcc SourceIdle4086_Apply
    jmp SourceIdle4086_Bad
SourceIdle4086_Apply:
.a16
.i16
    lda.l SourceIdle4086_Flags
    tax
    lda #3
    sta.l $43EB00,x
    lda #0
    sta.l $43EB02,x
    sta.l $43EB04,x
    sta.l $43EB06,x
    sta.l $43EB08,x
    sta.l $43EB0A,x
    sta.l $43EB0C,x
    sta.l $43EB0E,x
    lda.l SourceIdle4086_Core
    tax
    lda #0
    sta.l $40C058,x
    sta.l $40C05A,x
    lda.l SourceIdle4086_Cache
    tax
    lda.l $40B09C,x
    ora.l $40B09E,x
    beq SourceIdle4086_Done
    lda.l SourceIdle4086_Side
    tax
    lda #0
    sta.l $416824,x
    sta.l $416826,x
    sta.l $416828,x
    sta.l $41682A,x
SourceIdle4086_Done:
.a16
.i16
    lda #1
    sta.l SourceIdle4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceIdle4086_Bad:
.a16
.i16
    lda #2
    sta.l SourceIdle4086_Status
    ply
    plx
    plp
    sec
    rtl
