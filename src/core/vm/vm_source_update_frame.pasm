; Foreground update_frame prefix and resumable owner, outside bank 0.
; B4E3 leases the frame auxiliary array and checked immutable B4FE table.
; Aux rows at $41F500 are 20 bytes: movex,movez,altbase,pausetime (Q16/uint32),
; signed animating at +16, gameplay flags at +18. Never infer reverse playback
; from the legacy side's one-bit animating flag. Table installation owns CRC/
; SHA validation; Begin checks the selected directory and frame bounds again.
; Pending 1=execute_animation_script; 2=remaining update_frame effects using
; captured AnimationData/FrameData. Caller MUST finish each service before Ack.
; This prefix does not implement the effect services or nested interpreter calls.
SourceUpdateFrame4086_Ready = $7FFB50
SourceUpdateFrame4086_State = $7FFB52 ; 0 idle,1 pending,2 complete,3 fault
SourceUpdateFrame4086_Pending = $7FFB54
SourceUpdateFrame4086_Slot = $7FFB56
SourceUpdateFrame4086_Request = $7FFB58
SourceUpdateFrame4086_View = $7FFB5A
SourceUpdateFrame4086_Side = $7FFB5C
SourceUpdateFrame4086_Aux = $7FFB5E
SourceUpdateFrame4086_Handle = $7FFB60
SourceUpdateFrame4086_Base = $7FFB62
SourceUpdateFrame4086_Bank = $7FFB64
SourceUpdateFrame4086_Bytes = $7FFB66
SourceUpdateFrame4086_Animations = $7FFB68
SourceUpdateFrame4086_Count = $7FFB6A
SourceUpdateFrame4086_AnimationData = $7FFB6C
SourceUpdateFrame4086_FrameData = $7FFB6E
SourceUpdateFrame4086_FirstFrame = $7FFB70
SourceUpdateFrame4086_Fault = $7FFB72
SourceUpdateFrame4086_TableEnd = $7FFB74
SourceUpdateFrame4086_Delay = $7FFB76
SourceUpdateFrame4086_TimeLo = $7FFB78
SourceUpdateFrame4086_TimeHi = $7FFB7A
SourceUpdateFrame4086_AnimIdLo = $7FFB7C
SourceUpdateFrame4086_AnimIdHi = $7FFB7E
SourceUpdateFrame4086_ScratchEnd = $7FFB80
SOURCE_UPDATE_FRAME_AUX = $41F500
SOURCE_UPDATE_FRAME_QUAKE = $41FF00

; Initialize the admitted NONE idle row before alive publication. Other birth
; policies must supply their actual source state; this does not admit them.
SourceUpdateFrame4086_InitializeBirth:
.a16
.i16
    php
    rep #$38
    pha
    phx
    phy
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    bne SourceUpdateFrame4086_InitializeBirth__done
    lda.l VmSourceWorld_SideOffset
    lsr a
    lsr a
    lsr a
    lsr a                         ; physical slot*4
    pha
    asl a
    asl a                         ; physical slot*16
    clc
    adc 1,s
    tax
    pla
    ldy #0
    lda #0
SourceUpdateFrame4086_InitializeBirth__clear:
.a16
.i16
    sta.l SOURCE_UPDATE_FRAME_AUX,x
    inx
    inx
    iny
    iny
    cpy #20
    bcc SourceUpdateFrame4086_InitializeBirth__clear
    lda #1
    sta.l SOURCE_UPDATE_FRAME_AUX-4,x ; source admitted idle has animating=1
SourceUpdateFrame4086_InitializeBirth__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; C=1 unfinished/faulted frame owner. Preserve A/X/Y/P except C.
SourceUpdateFrame4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceUpdateFrame4086_Ready
    bne SourceUpdateFrame4086_Branch_1
    jmp SourceUpdateFrame4086_CheckIdle__ok
SourceUpdateFrame4086_Branch_1:
.a16
.i16
    cmp #$B4E3
    beq SourceUpdateFrame4086_Branch_2
    jmp SourceUpdateFrame4086_CheckIdle__bad
SourceUpdateFrame4086_Branch_2:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    beq SourceUpdateFrame4086_Branch_3
    jmp SourceUpdateFrame4086_CheckIdle__bad
SourceUpdateFrame4086_Branch_3:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    bne SourceUpdateFrame4086_Branch_4
    jmp SourceUpdateFrame4086_CheckIdle__ok
SourceUpdateFrame4086_Branch_4:
.a16
.i16
    cmp #2
    bne SourceUpdateFrame4086_Branch_5
    jmp SourceUpdateFrame4086_CheckIdle__ok
SourceUpdateFrame4086_Branch_5:
.a16
.i16
SourceUpdateFrame4086_CheckIdle__bad:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceUpdateFrame4086_CheckIdle__ok:
.a16
.i16
    pla
    plp
    clc
    rtl

; Input Slot/Request plus table lease. Return C=0 and Pending in A.
SourceUpdateFrame4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceUpdateFrame4086_Branch_6
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_6:
.a16
.i16
    jsl SourceUpdateFrame4086_CheckIdle
    bcc SourceUpdateFrame4086_Branch_7
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_7:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    bne SourceUpdateFrame4086_Branch_8
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_8:
.a16
.i16
    cmp #VMSTAT_YIELDED
    bne SourceUpdateFrame4086_Branch_9
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_9:
.a16
.i16
    cmp #VMSTAT_FAULT
    bne SourceUpdateFrame4086_Branch_10
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_10:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceUpdateFrame4086_Branch_11
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_11:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq SourceUpdateFrame4086_Branch_12
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_12:
.a16
.i16
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    beq SourceUpdateFrame4086_Branch_13
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_13:
.a16
.i16
    lda.l VmSourceWorld_Count
    bne SourceUpdateFrame4086_Branch_14
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_14:
.a16
.i16
    cmp #129
    bcc SourceUpdateFrame4086_Branch_15
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_15:
.a16
.i16
    cmp.l SourceUpdateFrame4086_Slot
    bne SourceUpdateFrame4086_Branch_16
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_16:
.a16
.i16
    bcs SourceUpdateFrame4086_Branch_17
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_17:
.a16
.i16
    lda.l SourceUpdateFrame4086_Request
    bpl SourceUpdateFrame4086_Branch_18
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_18:
.a16
.i16
    lda.l SourceUpdateFrame4086_Slot
    asl a
    asl a
    pha
    asl a
    asl a
    sta.l SourceUpdateFrame4086_Side ; slot*16
    pla
    clc
    adc.l SourceUpdateFrame4086_Side ; slot*20
    clc
    adc #$F500
    sta.l SourceUpdateFrame4086_Aux
    lda.l SourceUpdateFrame4086_Side
    asl a
    asl a                         ; slot*64
    sta.l SourceUpdateFrame4086_View
    clc
    adc #$6800
    sta.l SourceUpdateFrame4086_Side
    lda.l SourceUpdateFrame4086_View
    lsr a
    lsr a                         ; slot*16
    clc
    adc.l SourceUpdateFrame4086_View
    clc
    adc #$4000
    sta.l SourceUpdateFrame4086_View
    tax
    lda.l $410004,x
    bne SourceUpdateFrame4086_Branch_19
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_19:
.a16
.i16
    lda.l $410010,x                ; complete INTEGER animation id
    cmp #BOR_VT_INTEGER
    beq SourceUpdateFrame4086_Branch_20
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_20:
.a16
.i16
    lda.l $410012,x
    beq SourceUpdateFrame4086_Branch_21
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_21:
.a16
.i16
    lda.l $410014,x
    sta.l SourceUpdateFrame4086_AnimIdLo
    lda.l $410016,x
    sta.l SourceUpdateFrame4086_AnimIdHi
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410004,x
    sta.l SourceUpdateFrame4086_Handle
    lda.l SourceUpdateFrame4086_Base
    cmp #$8000
    bcs SourceUpdateFrame4086_Branch_22
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_22:
.a16
.i16
    lda.l SourceUpdateFrame4086_Bytes
    cmp #24
    bcs SourceUpdateFrame4086_Branch_23
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_23:
.a16
.i16
    clc
    adc.l SourceUpdateFrame4086_Base
    bcc SourceUpdateFrame4086_Branch_24
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_24:
.a16
.i16
    sta.l SourceUpdateFrame4086_TableEnd
    lda.l SourceUpdateFrame4086_Bank
    cmp #64
    bcc SourceUpdateFrame4086_Branch_25
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_25:
.a16
.i16
    lda.l SourceUpdateFrame4086_Base
    tax
    jsr SourceUpdateFrame4086_Read
    cmp #$3442                    ; B4FE
    beq SourceUpdateFrame4086_Branch_26
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_26:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    cmp #$4546
    beq SourceUpdateFrame4086_Branch_27
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_27:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    cmp #1
    beq SourceUpdateFrame4086_Branch_28
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_28:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    bne SourceUpdateFrame4086_Branch_29
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_29:
.a16
.i16
    cmp #129
    bcc SourceUpdateFrame4086_Branch_30
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_30:
.a16
.i16
    sta.l SourceUpdateFrame4086_Animations
    lda.l SourceUpdateFrame4086_Handle
    bne SourceUpdateFrame4086_Branch_31
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_31:
.a16
.i16
    cmp.l SourceUpdateFrame4086_Animations
    bcs SourceUpdateFrame4086_Branch_32
    jmp SourceUpdateFrame4086_Begin__handle_ok
SourceUpdateFrame4086_Branch_32:
.a16
.i16
    beq SourceUpdateFrame4086_Branch_33
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_33:
.a16
.i16
SourceUpdateFrame4086_Begin__handle_ok:
.a16
.i16
    dec a
    asl a
    asl a
    asl a
    clc
    adc #16
    clc
    adc.l SourceUpdateFrame4086_Base
    tax
    clc
    adc #8
    bcc SourceUpdateFrame4086_Branch_34
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_34:
.a16
.i16
    cmp.l SourceUpdateFrame4086_TableEnd
    bcs SourceUpdateFrame4086_Branch_35
    jmp SourceUpdateFrame4086_Begin__directory_ok
SourceUpdateFrame4086_Branch_35:
.a16
.i16
    beq SourceUpdateFrame4086_Branch_36
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_36:
.a16
.i16
SourceUpdateFrame4086_Begin__directory_ok:
.a16
.i16
    jsr SourceUpdateFrame4086_Read
    cmp.l SourceUpdateFrame4086_Handle
    beq SourceUpdateFrame4086_Branch_37
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_37:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    bne SourceUpdateFrame4086_Branch_38
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_38:
.a16
.i16
    bpl SourceUpdateFrame4086_Branch_39
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_39:
.a16
.i16
    cmp #1366                     ; prevent count*24 uint16 overflow
    bcc SourceUpdateFrame4086_Branch_40
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_40:
.a16
.i16
    sta.l SourceUpdateFrame4086_Count
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    clc
    adc.l SourceUpdateFrame4086_Base
    bcc SourceUpdateFrame4086_Branch_41
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_41:
.a16
.i16
    sta.l SourceUpdateFrame4086_AnimationData
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    clc
    adc.l SourceUpdateFrame4086_Base
    bcc SourceUpdateFrame4086_Branch_42
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_42:
.a16
.i16
    sta.l SourceUpdateFrame4086_FirstFrame
    sec
    sbc.l SourceUpdateFrame4086_AnimationData
    cmp #128
    beq SourceUpdateFrame4086_Branch_43
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_43:
.a16
.i16
    lda.l SourceUpdateFrame4086_Animations
    asl a
    asl a
    asl a
    clc
    adc #16
    clc
    adc.l SourceUpdateFrame4086_Base
    cmp.l SourceUpdateFrame4086_AnimationData
    bne SourceUpdateFrame4086_Branch_44
    jmp SourceUpdateFrame4086_Begin__animation_ok
SourceUpdateFrame4086_Branch_44:
.a16
.i16
    bcc SourceUpdateFrame4086_Branch_45
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_45:
.a16
.i16
SourceUpdateFrame4086_Begin__animation_ok:
.a16
.i16
    lda.l SourceUpdateFrame4086_Count
    asl a
    asl a
    asl a                         ; count*8
    pha
    asl a                         ; count*16
    bcc SourceUpdateFrame4086_Branch_46
    jmp SourceUpdateFrame4086_Begin__drop_bad
SourceUpdateFrame4086_Branch_46:
.a16
.i16
    clc
    adc 1,s                       ; count*24
    bcc SourceUpdateFrame4086_Branch_47
    jmp SourceUpdateFrame4086_Begin__drop_bad
SourceUpdateFrame4086_Branch_47:
.a16
.i16
    clc
    adc.l SourceUpdateFrame4086_FirstFrame
    bcc SourceUpdateFrame4086_Branch_48
    jmp SourceUpdateFrame4086_Begin__drop_bad
SourceUpdateFrame4086_Branch_48:
.a16
.i16
    cmp.l SourceUpdateFrame4086_TableEnd
    bcs SourceUpdateFrame4086_Branch_49
    jmp SourceUpdateFrame4086_Begin__frame_range_ok
SourceUpdateFrame4086_Branch_49:
.a16
.i16
    beq SourceUpdateFrame4086_Branch_50
    jmp SourceUpdateFrame4086_Begin__drop_bad
SourceUpdateFrame4086_Branch_50:
.a16
.i16
SourceUpdateFrame4086_Begin__frame_range_ok:
.a16
.i16
    pla
    lda.l SourceUpdateFrame4086_Request
    cmp.l SourceUpdateFrame4086_Count
    bcc SourceUpdateFrame4086_Branch_51
    jmp SourceUpdateFrame4086_Complete
SourceUpdateFrame4086_Branch_51:
.a16
.i16
    asl a
    asl a
    asl a
    pha
    asl a
    clc
    adc 1,s
    clc
    adc.l SourceUpdateFrame4086_FirstFrame
    sta.l SourceUpdateFrame4086_FrameData
    pla
    lda.l SourceUpdateFrame4086_FrameData
    clc
    adc #20
    tax
    jsr SourceUpdateFrame4086_Read
    sta.l SourceUpdateFrame4086_Delay
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    beq SourceUpdateFrame4086_Branch_52
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_52:
.a16
.i16
    lda.l VmSourceWorld_Time
    sta.l SourceUpdateFrame4086_TimeLo
    lda.l VmSourceWorld_Time+2
    sta.l SourceUpdateFrame4086_TimeHi
    lda #0
    sta.l SourceUpdateFrame4086_Fault
    ; The opt-in motion backend is once per admitted frame invocation.
    sta.l SourceFrameMotion4086_Status
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l SourceUpdateFrame4086_Request
    sta.l $410006,x
    lda.l SourceUpdateFrame4086_Aux
    tax
    lda.l $410010,x
    bne SourceUpdateFrame4086_Branch_53
    jmp SourceUpdateFrame4086_Begin__effects
SourceUpdateFrame4086_Branch_53:
.a16
.i16
    lda #0
    sta.l $41000C,x
    sta.l $41000E,x
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l SourceUpdateFrame4086_Delay
    clc
    adc.l SourceUpdateFrame4086_TimeLo
    sta.l $410008,x
    lda.l SourceUpdateFrame4086_TimeHi
    adc #0
    sta.l $41000A,x
    lda #1
    bra SourceUpdateFrame4086_Issue
SourceUpdateFrame4086_Begin__drop_bad:
.a16
.i16
    pla
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Begin__effects:
.a16
.i16
    lda #2
SourceUpdateFrame4086_Issue:
.a16
.i16
    sta.l SourceUpdateFrame4086_Pending
    lda #1
    sta.l SourceUpdateFrame4086_State
    jmp SourceUpdateFrame4086_Ok

SourceUpdateFrame4086_Ack:
.a16
.i16
    php
    rep #$38
    phx
    phy
    cmp.l SourceUpdateFrame4086_Pending
    beq SourceUpdateFrame4086_Branch_54
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_54:
.a16
.i16
    cmp #1
    bne SourceUpdateFrame4086_Branch_55
    jmp SourceUpdateFrame4086_Ack__script
SourceUpdateFrame4086_Branch_55:
.a16
.i16
    cmp #2
    beq SourceUpdateFrame4086_Branch_56
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_56:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceUpdateFrame4086_Branch_57
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_57:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceUpdateFrame4086_Branch_58
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_58:
.a16
.i16
    lda.l SourceFrameMotion4086_Ready
    beq SourceUpdateFrame4086_Ack__motion_disabled
    cmp #$B4E8
    beq SourceUpdateFrame4086_Ack__motion_leased
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Ack__motion_leased:
.a16
.i16
    lda.l SourceFrameMotion4086_Status
    cmp #1
    beq SourceUpdateFrame4086_Ack__motion_disabled
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Ack__motion_disabled:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    bne SourceUpdateFrame4086_Branch_59
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_59:
.a16
.i16
    cmp #VMSTAT_YIELDED
    bne SourceUpdateFrame4086_Branch_60
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_60:
.a16
.i16
    cmp #VMSTAT_FAULT
    bne SourceUpdateFrame4086_Branch_61
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_61:
.a16
.i16
    jmp SourceUpdateFrame4086_Complete
SourceUpdateFrame4086_Ack__script:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceUpdateFrame4086_Branch_62
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_62:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceUpdateFrame4086_Branch_63
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_63:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_DONE
    beq SourceUpdateFrame4086_Branch_64
    jmp SourceUpdateFrame4086_Bad
SourceUpdateFrame4086_Branch_64:
.a16
.i16
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410004,x
    cmp.l SourceUpdateFrame4086_Handle
    beq SourceUpdateFrame4086_Branch_65
    jmp SourceUpdateFrame4086_Complete
SourceUpdateFrame4086_Branch_65:
.a16
.i16
    lda.l $410006,x
    cmp.l SourceUpdateFrame4086_Request
    beq SourceUpdateFrame4086_Branch_66
    jmp SourceUpdateFrame4086_Complete
SourceUpdateFrame4086_Branch_66:
.a16
.i16
    lda #2
    jmp SourceUpdateFrame4086_Issue
SourceUpdateFrame4086_Complete:
.a16
.i16
    lda #0
    sta.l SourceUpdateFrame4086_Pending
    sta.l SourceUpdateFrame4086_Fault
    lda #2
    sta.l SourceUpdateFrame4086_State
    jmp SourceUpdateFrame4086_Ok
SourceUpdateFrame4086_Bad:
.a16
.i16
    lda #1
    sta.l SourceUpdateFrame4086_Fault
    lda #3
    sta.l SourceUpdateFrame4086_State
    ply
    plx
    plp
    sec
    rtl
SourceUpdateFrame4086_Ok:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    ply
    plx
    plp
    clc
    rtl

; Caller proved both bytes lie within the mapped immutable table. Preserve C.
SourceUpdateFrame4086_Read:
.a16
.i16
    phb
    sep #$20
.a8
    lda.l SourceUpdateFrame4086_Bank
    pha
    plb
    rep #$20
.a16
    lda.w $0000,x
    plb
    ora #0                        ; PLB changed N/Z; expose the loaded word
    rts
