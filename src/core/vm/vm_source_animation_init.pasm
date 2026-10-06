; ent_set_anim policy owner. Pending state 1 requires actual update_frame(0),
; never an implicit acknowledgement. B4EC leases shared animhits $43E000..E1FF
; and entity-core reserved fields +80 grabbing/+84 lasthit. Nonrecursive owner;
; nested update_frame service stack is the caller's separate responsibility.
SourceAnimationInit4086_Ready = $7FFC90
SourceAnimationInit4086_State = $7FFC92 ; 0 idle,1 frame-zero pending,2 done,3 fault
SourceAnimationInit4086_Slot = $7FFC94
SourceAnimationInit4086_Number = $7FFC96
SourceAnimationInit4086_Reset = $7FFC98
SourceAnimationInit4086_Base = $7FFC9A
SourceAnimationInit4086_Bank = $7FFC9C
SourceAnimationInit4086_Bytes = $7FFC9E
SourceAnimationInit4086_Handles = $7FFCA0
SourceAnimationInit4086_View = $7FFCA2
SourceAnimationInit4086_Side = $7FFCA4
SourceAnimationInit4086_Core = $7FFCA6
SourceAnimationInit4086_Aux = $7FFCA8
SourceAnimationInit4086_Handle = $7FFCAA
SourceAnimationInit4086_Count = $7FFCAC
SourceAnimationInit4086_Sync = $7FFCAE
SourceAnimationInit4086_Old = $7FFCB0
SourceAnimationInit4086_Offset = $7FFCB2
SourceAnimationInit4086_RowBytes = $7FFCB4
SourceAnimationInit4086_Model = $7FFCB6
SourceAnimationInit4086_Issued = $7FFCB8

SourceAnimationInit4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceAnimationInit4086_Ready
    beq SourceAnimationInit4086_CheckIdle_Good
    cmp #$B4EC
    bne SourceAnimationInit4086_CheckIdle_Bad
    lda.l SourceAnimationInit4086_State
    beq SourceAnimationInit4086_CheckIdle_Good
    cmp #2
    bne SourceAnimationInit4086_CheckIdle_Bad
SourceAnimationInit4086_CheckIdle_Good:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceAnimationInit4086_CheckIdle_Bad:
.a16
.i16
    pla
    plp
    sec
    rtl

SourceAnimationInit4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceAnimationInit4086_Ready
    cmp #$B4EC
    beq SourceAnimationInit4086_Relaxed_1
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_1:
.a16
.i16
    lda.l SourceAnimationInit4086_State
    cmp #1
    bne SourceAnimationInit4086_Relaxed_2
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_2:
.a16
.i16
    cmp #3
    bne SourceAnimationInit4086_Relaxed_3
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_3:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceAnimationInit4086_Relaxed_4
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_4:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq SourceAnimationInit4086_Relaxed_5
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_5:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Ready
    cmp #$B4EB
    beq SourceAnimationInit4086_Relaxed_6
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_6:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_Ready
    cmp #$B4E9
    beq SourceAnimationInit4086_Relaxed_7
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_7:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceAnimationInit4086_Relaxed_8
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_8:
.a16
.i16
    lda.l VmSourceWorld_Count
    bne SourceAnimationInit4086_Relaxed_9
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_9:
.a16
.i16
    cmp #129
    bcc SourceAnimationInit4086_Relaxed_10
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_10:
.a16
.i16
    lda.l SourceAnimationInit4086_Slot
    cmp.l VmSourceWorld_Count
    bcc SourceAnimationInit4086_Relaxed_11
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_11:
.a16
.i16
    ; Invalid source animation numbers are source no-ops, not table faults.
    lda.l SourceModelAnimationCopy4086_Maximum
    bne SourceAnimationInit4086_Relaxed_12
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_12:
.a16
.i16
    cmp #1025
    bcc SourceAnimationInit4086_Relaxed_13
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_13:
.a16
.i16
    asl a
    sta.l SourceAnimationInit4086_RowBytes
    lda.l SourceModelAnimationCopy4086_Models
    bne SourceAnimationInit4086_Relaxed_14
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_14:
.a16
.i16
    cmp #129
    bcc SourceAnimationInit4086_Relaxed_15
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_15:
.a16
.i16
    tax
    lda #0
SourceAnimationInit4086_Capacity:
.a16
.i16
    clc
    adc.l SourceAnimationInit4086_RowBytes
    bcc SourceAnimationInit4086_Relaxed_16
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_16:
.a16
.i16
    dex
    bne SourceAnimationInit4086_Capacity
    cmp #8193
    bcc SourceAnimationInit4086_Relaxed_17
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_17:
.a16
.i16
    cmp.l SourceModelAnimationCopy4086_Bytes
    beq SourceAnimationInit4086_Relaxed_18
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_18:
.a16
.i16
    lda.l SourceAnimationInit4086_Number
    cmp.l SourceModelAnimationCopy4086_Maximum
    bcc SourceAnimationInit4086_Relaxed_19
    jmp SourceAnimationInit4086_Done
SourceAnimationInit4086_Relaxed_19:
.a16
.i16
    ; B4AI table is an immutable paired descriptor verified by installation.
    lda.l SourceAnimationInit4086_Bank
    cmp #64
    bcc SourceAnimationInit4086_Relaxed_20
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_20:
.a16
.i16
    lda.l SourceAnimationInit4086_Base
    cmp #$8000
    bcs SourceAnimationInit4086_Relaxed_21
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_21:
.a16
.i16
    lda.l SourceAnimationInit4086_Bytes
    cmp #16
    bcs SourceAnimationInit4086_Relaxed_22
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_22:
.a16
.i16
    dec a
    clc
    adc.l SourceAnimationInit4086_Base
    bcc SourceAnimationInit4086_Relaxed_23
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_23:
.a16
.i16
    ldx #0
    jsr SourceAnimationInit4086_Read
    cmp #$3442
    beq SourceAnimationInit4086_Relaxed_24
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_24:
.a16
.i16
    ldx #2
    jsr SourceAnimationInit4086_Read
    cmp #$4941
    beq SourceAnimationInit4086_Relaxed_25
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_25:
.a16
.i16
    ldx #4
    jsr SourceAnimationInit4086_Read
    cmp #1
    beq SourceAnimationInit4086_Relaxed_26
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_26:
.a16
.i16
    ldx #6
    jsr SourceAnimationInit4086_Read
    bne SourceAnimationInit4086_Relaxed_27
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_27:
.a16
.i16
    cmp #129
    bcc SourceAnimationInit4086_Relaxed_28
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_28:
.a16
.i16
    sta.l SourceAnimationInit4086_Handles
    cmp.l SourceUpdateFrame4086_Animations
    beq SourceAnimationInit4086_Relaxed_29
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_29:
.a16
.i16
    asl a
    asl a
    asl a
    clc
    adc #16
    cmp.l SourceAnimationInit4086_Bytes
    beq SourceAnimationInit4086_Relaxed_30
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_30:
.a16
.i16
    ldx #8
    jsr SourceAnimationInit4086_Read
    cmp.l SourceModelAnimationCopy4086_Maximum
    beq SourceAnimationInit4086_Relaxed_31
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_31:
.a16
.i16
    ldx #10
    jsr SourceAnimationInit4086_Read
    cmp #8
    beq SourceAnimationInit4086_Relaxed_32
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_32:
.a16
.i16
    ldx #12
    jsr SourceAnimationInit4086_Read
    cmp #16
    beq SourceAnimationInit4086_Relaxed_33
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_33:
.a16
.i16
    ldx #14
    jsr SourceAnimationInit4086_Read
    beq SourceAnimationInit4086_Relaxed_34
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_34:
.a16
.i16
    lda.l SourceAnimationInit4086_Slot
    asl a
    asl a
    asl a
    asl a
    sta.l SourceAnimationInit4086_Offset ; slot*16
    asl a
    asl a
    sta.l SourceAnimationInit4086_Side ; slot*64
    clc
    adc #$6800
    sta.l SourceAnimationInit4086_Side
    tax
    lda.l $410000,x
    cmp.l SourceModelAnimationCopy4086_Models
    bcc SourceAnimationInit4086_Relaxed_35
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_35:
.a16
.i16
    sta.l SourceAnimationInit4086_Model
    lda.l $410004,x
    sta.l SourceAnimationInit4086_Old
    lda.l SourceAnimationInit4086_Offset
    asl a ; slot*32
    clc
    adc.l SourceAnimationInit4086_Offset ; slot*48
    asl a ; slot*96
    clc
    adc #$C000
    sta.l SourceAnimationInit4086_Core
    lda.l SourceAnimationInit4086_Offset
    clc
    adc.l SourceAnimationInit4086_Slot
    adc.l SourceAnimationInit4086_Slot
    adc.l SourceAnimationInit4086_Slot
    adc.l SourceAnimationInit4086_Slot ; slot*20, no overflow for slot<128
    clc
    adc #$F500
    sta.l SourceAnimationInit4086_Aux
    lda.l SourceAnimationInit4086_Offset
    asl a
    asl a ; slot*64
    clc
    adc.l SourceAnimationInit4086_Offset ; slot*80
    clc
    adc #$4000
    sta.l SourceAnimationInit4086_View
    tax
    lda.l $410010,x ; animation ID variant tag
    cmp #BOR_VT_INTEGER
    beq SourceAnimationInit4086_Relaxed_36
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_36:
.a16
.i16
    lda.l $410012,x
    ora.l $410016,x ; reserved/high ID (native IDs nonnegative <=1024)
    beq SourceAnimationInit4086_Relaxed_37
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_37:
.a16
.i16
    lda.l SourceAnimationInit4086_Model
    tax
    lda #0
    cpx #0
    beq SourceAnimationInit4086_ModelOffset
SourceAnimationInit4086_ModelLoop:
.a16
.i16
    clc
    adc.l SourceAnimationInit4086_RowBytes
    dex
    bne SourceAnimationInit4086_ModelLoop
SourceAnimationInit4086_ModelOffset:
.a16
.i16
    sta.l SourceAnimationInit4086_Offset
    lda.l SourceAnimationInit4086_Number
    asl a
    clc
    adc.l SourceAnimationInit4086_Offset
    tax
    lda.l SOURCE_MODEL_ANIMATION_CACHE,x
    bne SourceAnimationInit4086_Relaxed_38
    jmp SourceAnimationInit4086_Done
SourceAnimationInit4086_Relaxed_38:
.a16
.i16
    sta.l SourceAnimationInit4086_Handle
    jsr SourceAnimationInit4086_CheckHandle
    bcc SourceAnimationInit4086_Relaxed_39
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_39:
.a16
.i16
    sta.l SourceAnimationInit4086_Offset
    tax
    inx
    inx
    jsr SourceAnimationInit4086_Read
    sta.l SourceAnimationInit4086_Count
    ; Frame count must agree with the immutable frame-effect directory.
    lda.l SourceAnimationInit4086_Handle
    jsr SourceModelAnimationCopy4086_FrameCount
    cmp.l SourceAnimationInit4086_Count
    beq SourceAnimationInit4086_Relaxed_40
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_40:
.a16
.i16
    beq SourceAnimationInit4086_CountChecked
SourceAnimationInit4086_CountChecked:
.a16
.i16
    lda.l SourceAnimationInit4086_Count
    bne SourceAnimationInit4086_Relaxed_41
    jmp SourceAnimationInit4086_Done
SourceAnimationInit4086_Relaxed_41:
.a16
.i16
    lda.l SourceAnimationInit4086_Offset
    tax
    inx
    inx
    inx
    inx
    jsr SourceAnimationInit4086_Read
    sta.l SourceAnimationInit4086_Sync
    cmp #$FFFF
    beq SourceAnimationInit4086_SyncChecked
    cmp.l SourceModelAnimationCopy4086_Maximum
    bcc SourceAnimationInit4086_Relaxed_42
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_42:
.a16
.i16
SourceAnimationInit4086_SyncChecked:
.a16
.i16
    lda.l SourceAnimationInit4086_Reset
    bne SourceAnimationInit4086_CheckOld
    lda.l SourceAnimationInit4086_Old
    cmp.l SourceAnimationInit4086_Handle
    bne SourceAnimationInit4086_Relaxed_43
    jmp SourceAnimationInit4086_Done
SourceAnimationInit4086_Relaxed_43:
.a16
.i16
SourceAnimationInit4086_CheckOld:
.a16
.i16
    lda.l SourceAnimationInit4086_Old
    bne SourceAnimationInit4086_Relaxed_44
    jmp SourceAnimationInit4086_Initialize
SourceAnimationInit4086_Relaxed_44:
.a16
.i16
    jsr SourceAnimationInit4086_CheckHandle
    bcc SourceAnimationInit4086_Relaxed_45
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_45:
.a16
.i16
    clc
    adc #4
    tax
    jsr SourceAnimationInit4086_Read
    cmp.l SourceAnimationInit4086_Sync
    bne SourceAnimationInit4086_CheckReset
    lda.l SourceAnimationInit4086_Sync
    cmp #$FFFF
    beq SourceAnimationInit4086_Relaxed_46
    jmp SourceAnimationInit4086_Synchronized
SourceAnimationInit4086_Relaxed_46:
.a16
.i16
SourceAnimationInit4086_CheckReset:
.a16
.i16
    lda.l SourceAnimationInit4086_Reset
    bit #2
    bne SourceAnimationInit4086_Relaxed_47
    jmp SourceAnimationInit4086_Initialize
SourceAnimationInit4086_Relaxed_47:
.a16
.i16
SourceAnimationInit4086_Synchronized:
.a16
.i16
    lda.l SourceAnimationInit4086_Side
    tax
    lda.l $410006,x
    cmp.l SourceAnimationInit4086_Count
    bcc SourceAnimationInit4086_KeepFrame
    lda #0
SourceAnimationInit4086_KeepFrame:
.a16
.i16
    sta.l $410006,x
    jsr SourceAnimationInit4086_Install
    jmp SourceAnimationInit4086_Done
SourceAnimationInit4086_Initialize:
.a16
.i16
    jsr SourceAnimationInit4086_Install
    lda.l SourceAnimationInit4086_Handle
    dec a
    asl a
    asl a
    tax
    lda #0
    sta.l $43E000,x
    sta.l $43E002,x
    lda.l SourceAnimationInit4086_Core
    tax
    lda.l $400050,x
    sta.l $400054,x
    lda.l $400052,x
    sta.l $400056,x
    lda.l SourceAnimationInit4086_Aux
    tax
    lda #0
    sta.l $410008,x
    sta.l $41000A,x
    lda #1
    sta.l $410010,x
    sta.l SourceAnimationInit4086_State
    lda #0
    sta.l SourceAnimationInit4086_Issued
    ply
    plx
    plp
    clc
    rtl
SourceAnimationInit4086_Done:
.a16
.i16
    lda #2
    sta.l SourceAnimationInit4086_State
    ply
    plx
    plp
    clc
    rtl
SourceAnimationInit4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceAnimationInit4086_State
    ply
    plx
    plp
    sec
    rtl

SourceAnimationInit4086_Install:
.a16
.i16
    lda.l SourceAnimationInit4086_Side
    tax
    lda.l SourceAnimationInit4086_Handle
    sta.l $410004,x
    lda.l SourceAnimationInit4086_View
    tax
    lda.l SourceAnimationInit4086_Number
    sta.l $410014,x
    lda #0
    sta.l $410016,x
    rts

; Return checked B4AI row relative offset. Preserve source handle identity.
SourceAnimationInit4086_CheckHandle:
.a16
.i16
    beq SourceAnimationInit4086_HandleBad
    cmp.l SourceAnimationInit4086_Handles
    beq SourceAnimationInit4086_HandleBounded
    bcs SourceAnimationInit4086_HandleBad
SourceAnimationInit4086_HandleBounded:
.a16
.i16
    pha
    dec a
    asl a
    asl a
    asl a
    clc
    adc #16
    tax
    jsr SourceAnimationInit4086_Read
    sta.l SourceAnimationInit4086_Model ; no longer needed model ID
    pla
    cmp.l SourceAnimationInit4086_Model
    bne SourceAnimationInit4086_HandleBad
    txa
    clc
    rts
SourceAnimationInit4086_HandleBad:
.a16
.i16
    sec
    rts

SourceAnimationInit4086_Read:
.a16
.i16
    phb
    txa
    pha
    lda.l SourceAnimationInit4086_Bank
    sep #$20
.a8
    pha
    plb
    rep #$20
.a16
    pla
    clc
    adc.l SourceAnimationInit4086_Base
    tax
    lda.w $0000,x
    plb
    ora #0
    ; X is normalized back to table-relative offset for callers.
    pha
    txa
    sec
    sbc.l SourceAnimationInit4086_Base
    tax
    pla
    ora #0
    rts

SourceAnimationInit4086_Ack:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceAnimationInit4086_Ready
    cmp #$B4EC
    beq SourceAnimationInit4086_Relaxed_48
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_48:
.a16
.i16
    lda.l SourceAnimationInit4086_State
    cmp #1
    beq SourceAnimationInit4086_Relaxed_49
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_49:
.a16
.i16
    lda.l SourceAnimationInit4086_Issued
    cmp #1
    beq SourceAnimationInit4086_Relaxed_50
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_50:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #2
    beq SourceAnimationInit4086_Relaxed_51
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_51:
.a16
.i16
    lda.l SourceUpdateFrame4086_Slot
    cmp.l SourceAnimationInit4086_Slot
    beq SourceAnimationInit4086_Relaxed_52
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_52:
.a16
.i16
    lda.l SourceUpdateFrame4086_Request
    beq SourceAnimationInit4086_Relaxed_53
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_53:
.a16
.i16
    jmp SourceAnimationInit4086_Done

; Issue exactly one fresh frame-zero continuation. Caller must first save any
; parent frame owner, then run every nested script/effect service to completion.
SourceAnimationInit4086_StartFrame:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceAnimationInit4086_Ready
    cmp #$B4EC
    beq SourceAnimationInit4086_Relaxed_54
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_54:
.a16
.i16
    lda.l SourceAnimationInit4086_State
    cmp #1
    beq SourceAnimationInit4086_Relaxed_55
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_55:
.a16
.i16
    lda.l SourceAnimationInit4086_Issued
    beq SourceAnimationInit4086_Relaxed_56
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_56:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    bne SourceAnimationInit4086_Relaxed_57
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_57:
.a16
.i16
    cmp #3
    bne SourceAnimationInit4086_Relaxed_58
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_58:
.a16
.i16
    lda.l SourceAnimationInit4086_Slot
    sta.l SourceUpdateFrame4086_Slot
    lda #0
    sta.l SourceUpdateFrame4086_Request
    jsl SourceUpdateFrame4086_Begin
    bcc SourceAnimationInit4086_Relaxed_59
    jmp SourceAnimationInit4086_Bad
SourceAnimationInit4086_Relaxed_59:
.a16
.i16
    lda #1
    sta.l SourceAnimationInit4086_Issued
    ply
    plx
    plp
    clc
    rtl
