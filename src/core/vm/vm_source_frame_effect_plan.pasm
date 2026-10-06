; Foreground B4EP cursor for the captured frame, never current-model lookup.
; Handlers must perform each operation/predicate before Ack. This cursor does
; not implicitly execute dynamic quake, child, dust or projectile services.
; B4F2 installer validates B4EP/B4FE CRCs and canonical opcode directories.
; $7FFD40..$7FFD5F completes the frame stack's 528-byte snapshot.
SourceFrameEffectPlan4086_Ready = $7FFD40
SourceFrameEffectPlan4086_State = $7FFD42
SourceFrameEffectPlan4086_Service = $7FFD44
SourceFrameEffectPlan4086_Acknowledged = $7FFD46
SourceFrameEffectPlan4086_Slot = $7FFD48
SourceFrameEffectPlan4086_Handle = $7FFD4A
SourceFrameEffectPlan4086_Frame = $7FFD4C
SourceFrameEffectPlan4086_Index = $7FFD4E
SourceFrameEffectPlan4086_Count = $7FFD50
SourceFrameEffectPlan4086_Pool = $7FFD52
SourceFrameEffectPlan4086_Directory = $7FFD54
SourceFrameEffectPlan4086_Record = $7FFD56
SourceFrameEffectPlan4086_Temp = $7FFD58
SourceFrameEffectPlan4086_Word = $7FFD5A
SourceFrameEffectPlan4086_Current = $7FFD5C
; These words are free while an operation is pending and are captured by the
; frame stack. The binding owner uses them for model/idle service tickets.
SourceFrameEffectBinding4086_State = $7FFD58
SourceFrameEffectBinding4086_Issued = $7FFD5A
SourceFrameEffectBinding4086_Target = $7FFD5C
SourceFrameEffectPlan4086_End = $7FFD5E
SourceFrameEffectPlan4086_Base = $7FFE20
SourceFrameEffectPlan4086_Bank = $7FFE22
SourceFrameEffectPlan4086_Bytes = $7FFE24
SourceFrameEffectPlan4086_Animations = $7FFE26
SourceFrameEffectPlan4086_PairedCrcLo = $7FFE28
SourceFrameEffectPlan4086_PairedCrcHi = $7FFE2A
SourceFrameEffectPlan4086_BodyCrcLo = $7FFE2C
SourceFrameEffectPlan4086_BodyCrcHi = $7FFE2E

SourceFrameEffectPlan4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceFrameEffectPlan4086_Ready
    beq SourceFrameEffectPlan4086_IdleGood
    cmp #$B4F2
    bne SourceFrameEffectPlan4086_IdleBad
    lda.l SourceFrameEffectPlan4086_State
    beq SourceFrameEffectPlan4086_IdleGood
    cmp #2
    bne SourceFrameEffectPlan4086_IdleBad
    lda.l SourceFrameEffectPlan4086_Service
    bne SourceFrameEffectPlan4086_IdleBad
SourceFrameEffectPlan4086_IdleGood:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceFrameEffectPlan4086_IdleBad:
.a16
.i16
    pla
    plp
    sec
    rtl

; Effects cannot acknowledge an unissued or stale plan for another frame.
SourceFrameEffectPlan4086_CheckComplete:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceFrameEffectPlan4086_Ready
    beq SourceFrameEffectPlan4086_CompleteGood
    cmp #$B4F2
    bne SourceFrameEffectPlan4086_CompleteBad
    lda.l SourceFrameEffectPlan4086_State
    cmp #2
    bne SourceFrameEffectPlan4086_CompleteBad
    lda.l SourceFrameEffectPlan4086_Service
    bne SourceFrameEffectPlan4086_CompleteBad
    lda.l SourceFrameEffectPlan4086_Slot
    cmp.l SourceUpdateFrame4086_Slot
    bne SourceFrameEffectPlan4086_CompleteBad
    lda.l SourceFrameEffectPlan4086_Handle
    cmp.l SourceUpdateFrame4086_Handle
    bne SourceFrameEffectPlan4086_CompleteBad
    lda.l SourceFrameEffectPlan4086_Frame
    cmp.l SourceUpdateFrame4086_Request
    bne SourceFrameEffectPlan4086_CompleteBad
SourceFrameEffectPlan4086_CompleteGood:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceFrameEffectPlan4086_CompleteBad:
.a16
.i16
    pla
    plp
    sec
    rtl

SourceFrameEffectPlan4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsl SourceFrameEffectPlan4086_CheckIdle
    bcc SourceFrameEffectPlan4086_BeginLease
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BeginLease:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Ready
    cmp #$B4F2
    beq SourceFrameEffectPlan4086_BeginPrefix
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BeginPrefix:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceFrameEffectPlan4086_BeginState
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BeginState:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceFrameEffectPlan4086_BeginPending
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BeginPending:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    cmp #2
    beq SourceFrameEffectPlan4086_BeginGeometry
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BeginGeometry:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Animations
    beq SourceFrameEffectPlan4086_GeometryBad
    cmp #513
    bcs SourceFrameEffectPlan4086_GeometryBad
    cmp.l SourceUpdateFrame4086_Animations
    bne SourceFrameEffectPlan4086_GeometryBad
    lda.l SourceUpdateFrame4086_Handle
    beq SourceFrameEffectPlan4086_GeometryBad
    cmp.l SourceFrameEffectPlan4086_Animations
    bcc SourceFrameEffectPlan4086_HandleGood
    beq SourceFrameEffectPlan4086_HandleGood
SourceFrameEffectPlan4086_GeometryBad:
.a16
.i16
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_HandleGood:
.a16
.i16
    sta.l SourceFrameEffectPlan4086_Handle
    dec a
    asl a
    asl a
    asl a
    clc
    adc #32
    sta.l SourceFrameEffectPlan4086_Directory
    lda.l SourceUpdateFrame4086_Request
    cmp.l SourceUpdateFrame4086_Count
    bcc SourceFrameEffectPlan4086_FrameGood
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_FrameGood:
.a16
.i16
    sta.l SourceFrameEffectPlan4086_Frame
    lda.l SourceUpdateFrame4086_Slot
    sta.l SourceFrameEffectPlan4086_Slot
    lda.l SourceFrameEffectPlan4086_Bank
    cmp #64
    bcc SourceFrameEffectPlan4086_BankGood
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BankGood:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Base
    cmp #$8000
    bcs SourceFrameEffectPlan4086_BaseGood
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BaseGood:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Bytes
    cmp #40
    bcs SourceFrameEffectPlan4086_BytesGood
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_BytesGood:
.a16
.i16
    dec a
    clc
    adc.l SourceFrameEffectPlan4086_Base
    bcc SourceFrameEffectPlan4086_SpanGood
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_SpanGood:
.a16
.i16
    inc a
    sta.l SourceFrameEffectPlan4086_End
    jsr SourceFrameEffectPlan4086_Header
    bcc SourceFrameEffectPlan4086_HeaderGood
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_HeaderGood:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Directory
    clc
    adc #8
    cmp.l SourceFrameEffectPlan4086_Bytes
    bcc SourceFrameEffectPlan4086_DirectoryGood
    beq SourceFrameEffectPlan4086_DirectoryGood
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_DirectoryGood:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Directory
    clc
    adc.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceFrameEffectPlan4086_Handle
    beq SourceFrameEffectPlan4086_DirectoryIdentity
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_DirectoryIdentity:
.a16
.i16
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceUpdateFrame4086_Count
    beq SourceFrameEffectPlan4086_DirectoryCount
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_DirectoryCount:
.a16
.i16
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    sta.l SourceFrameEffectPlan4086_Record
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    beq SourceFrameEffectPlan4086_RecordAddress
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_RecordAddress:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Frame
    asl a
    bcs SourceFrameEffectPlan4086_RecordBad
    asl a
    bcs SourceFrameEffectPlan4086_RecordBad
    asl a
    bcs SourceFrameEffectPlan4086_RecordBad
    clc
    adc.l SourceFrameEffectPlan4086_Record
    bcs SourceFrameEffectPlan4086_RecordBad
    sta.l SourceFrameEffectPlan4086_Record
    clc
    adc #8
    bcs SourceFrameEffectPlan4086_RecordBad
    cmp.l SourceFrameEffectPlan4086_Bytes
    bcc SourceFrameEffectPlan4086_RecordGood
    beq SourceFrameEffectPlan4086_RecordGood
SourceFrameEffectPlan4086_RecordBad:
.a16
.i16
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_RecordGood:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Record
    clc
    adc.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_Read
    sta.l SourceFrameEffectPlan4086_Pool
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    beq SourceFrameEffectPlan4086_OperationCountBad
    cmp #33
    bcs SourceFrameEffectPlan4086_OperationCountBad
    sta.l SourceFrameEffectPlan4086_Count
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceFrameEffectPlan4086_Frame
    bne SourceFrameEffectPlan4086_OperationCountBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    beq SourceFrameEffectPlan4086_PoolBounds
SourceFrameEffectPlan4086_OperationCountBad:
.a16
.i16
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_PoolBounds:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Count
    bcs SourceFrameEffectPlan4086_PoolBad
    cmp.l SourceFrameEffectPlan4086_Bytes
    bcc SourceFrameEffectPlan4086_LastOpcode
    beq SourceFrameEffectPlan4086_LastOpcode
SourceFrameEffectPlan4086_PoolBad:
.a16
.i16
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_LastOpcode:
.a16
.i16
    dec a
    clc
    adc.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_ReadByte
    cmp #23
    beq SourceFrameEffectPlan4086_Start
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_Start:
.a16
.i16
    lda #0
    sta.l SourceFrameEffectPlan4086_Index
    jmp SourceFrameEffectPlan4086_Next

SourceFrameEffectPlan4086_Ack:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceFrameEffectPlan4086_Ready
    cmp #$B4F2
    bne SourceFrameEffectPlan4086_AckBad
    lda.l SourceFrameEffectPlan4086_State
    cmp #1
    bne SourceFrameEffectPlan4086_AckBad
    lda.l SourceFrameEffectPlan4086_Service
    cmp.l SourceFrameEffectPlan4086_Acknowledged
    bne SourceFrameEffectPlan4086_AckBad
    lda.l SourceFrameEffectPlan4086_Index
    inc a
    cmp.l SourceFrameEffectPlan4086_Count
    bcc SourceFrameEffectPlan4086_AckMore
    beq SourceFrameEffectPlan4086_AckEnd
SourceFrameEffectPlan4086_AckBad:
.a16
.i16
    jmp SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_AckEnd:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Service
    cmp #23
    bne SourceFrameEffectPlan4086_AckBad
    lda #0
    sta.l SourceFrameEffectPlan4086_Service
    sta.l SourceFrameEffectPlan4086_Acknowledged
    lda #2
    sta.l SourceFrameEffectPlan4086_State
    bra SourceFrameEffectPlan4086_Good
SourceFrameEffectPlan4086_AckMore:
.a16
.i16
    sta.l SourceFrameEffectPlan4086_Index
SourceFrameEffectPlan4086_Next:
.a16
.i16
    clc
    adc.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_ReadByte
    cmp #2
    bcc SourceFrameEffectPlan4086_Bad
    cmp #5
    bcc SourceFrameEffectPlan4086_OpcodeGood
    cmp #7
    bcc SourceFrameEffectPlan4086_Bad
    cmp #12
    bcc SourceFrameEffectPlan4086_OpcodeGood
    cmp #15
    bcc SourceFrameEffectPlan4086_Bad
    cmp #24
    bcs SourceFrameEffectPlan4086_Bad
SourceFrameEffectPlan4086_OpcodeGood:
.a16
.i16
    sta.l SourceFrameEffectPlan4086_Service
    lda #0
    sta.l SourceFrameEffectPlan4086_Acknowledged
    sta.l SourceFrameEffectBinding4086_State
    sta.l SourceFrameEffectBinding4086_Issued
    sta.l SourceFrameEffectBinding4086_Target
    lda #1
    sta.l SourceFrameEffectPlan4086_State
SourceFrameEffectPlan4086_Good:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
SourceFrameEffectPlan4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceFrameEffectPlan4086_State
    ply
    plx
    plp
    sec
    rtl

SourceFrameEffectPlan4086_Header:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_Read
    cmp #$3442
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp #$5045
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp #1
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceFrameEffectPlan4086_Animations
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp #8
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp #8
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp #1
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    beq SourceFrameEffectPlan4086_HeaderSize
SourceFrameEffectPlan4086_HeaderBad:
.a16
.i16
    sec
    rts
SourceFrameEffectPlan4086_HeaderSize:
.a16
.i16
    ; Canonical directory/pool shape and body CRC were checked by installer.
    lda.l SourceFrameEffectPlan4086_Base
    clc
    adc #20
    tax
    jsr SourceFrameEffectPlan4086_Read
    clc
    adc #32
    bcs SourceFrameEffectPlan4086_HeaderBad
    cmp.l SourceFrameEffectPlan4086_Bytes
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceFrameEffectPlan4086_PairedCrcLo
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceFrameEffectPlan4086_PairedCrcHi
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceFrameEffectPlan4086_BodyCrcLo
    bne SourceFrameEffectPlan4086_HeaderBad
    inx
    inx
    jsr SourceFrameEffectPlan4086_Read
    cmp.l SourceFrameEffectPlan4086_BodyCrcHi
    bne SourceFrameEffectPlan4086_HeaderBad
    clc
    rts

SourceFrameEffectPlan4086_Read:
.a16
.i16
    phb
    sep #$20
.a8
    lda.l SourceFrameEffectPlan4086_Bank
    pha
    plb
    rep #$20
.a16
    lda.w $0000,x
    plb
    ora #0
    rts
SourceFrameEffectPlan4086_ReadByte:
.a16
.i16
    phb
    sep #$20
.a8
    lda.l SourceFrameEffectPlan4086_Bank
    pha
    plb
    lda.w $0000,x
    plb
    rep #$20
.a16
    and #$00FF
    rts
