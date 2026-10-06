; set_weapon selection/bookkeeping component. Resolve does not switch models:
; caller must pass Selected/Sync to the ordered model-transition owner.
; B4F1 exclusive entity weapon metadata $43E200..$43E9FF (128*16):
; owner/count words, source weaploss[0]/[1] int32, reserved uint32=0.
; Player weapnum[4] int32 at $43EA00..$43EA0F. These are entity shallow-copy
; values, never a fresh lookup of a subsequently mutated cached weapon list.
SourceWeapon4086_Ready = $7FFD20
SourceWeapon4086_Status = $7FFD22
SourceWeapon4086_Slot = $7FFD24
SourceWeapon4086_NumberLo = $7FFD26
SourceWeapon4086_NumberHi = $7FFD28
SourceWeapon4086_AnimFlagLo = $7FFD2A
SourceWeapon4086_AnimFlagHi = $7FFD2C
SourceWeapon4086_Selected = $7FFD2E
SourceWeapon4086_Sync = $7FFD30
SourceWeapon4086_Row = $7FFD32
SourceWeapon4086_Owner = $7FFD34
SourceWeapon4086_Count = $7FFD36
SourceWeapon4086_Offset = $7FFD38
SourceWeapon4086_Value = $7FFD3A
SourceWeapon4086_Temp = $7FFD3C
SourceWeapon4086_Player = $7FFD3E
; Immutable installed descriptor, outside nested snapshots.
SourceWeapon4086_Base = $7FFE00
SourceWeapon4086_Bank = $7FFE02
SourceWeapon4086_Bytes = $7FFE04
SourceWeapon4086_Models = $7FFE06
SourceWeapon4086_Entities = $7FFE08
SourceWeapon4086_LevelWeaponLo = $7FFE0A
SourceWeapon4086_LevelWeaponHi = $7FFE0C
SourceWeapon4086_Players = $7FFE0E

SourceWeapon4086_Resolve:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsr SourceWeapon4086_CheckLease
    bcc SourceWeapon4086_ResolveCore
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ResolveCore:
.a16
.i16
    lda.l SourceWeapon4086_Slot
    asl a
    asl a
    asl a
    asl a
    sta.l SourceWeapon4086_Row ; slot*16
    asl a
    sta.l SourceWeapon4086_Temp ; slot*32
    asl a
    clc
    adc.l SourceWeapon4086_Temp ; slot*96
    tax
    lda.l $40C048,x
    bit #1
    bne SourceWeapon4086_PlayerIndex
    jmp SourceWeapon4086_Select
SourceWeapon4086_PlayerIndex:
.a16
.i16
    lda.l SourceWeapon4086_Row
    asl a
    asl a
    clc
    adc.l SourceWeapon4086_Row ; slot*80
    tax
    lda.l $414028,x
    cmp #BOR_VT_INTEGER
    beq SourceWeapon4086_PlayerTag
    jmp SourceWeapon4086_Bad
SourceWeapon4086_PlayerTag:
.a16
.i16
    lda.l $41402A,x
    ora.l $41402E,x
    beq SourceWeapon4086_PlayerValue
    jmp SourceWeapon4086_Bad
SourceWeapon4086_PlayerValue:
.a16
.i16
    lda.l $41402C,x
    cmp.l SourceWeapon4086_Players
    bcc SourceWeapon4086_PlayerSave
    jmp SourceWeapon4086_Bad
SourceWeapon4086_PlayerSave:
.a16
.i16
    asl a
    asl a
    sta.l SourceWeapon4086_Player
    lda.l SourceWeapon4086_Row
    tax
    lda.l $43E204,x
    cmp #3
    bne SourceWeapon4086_PlayerLevel
    lda.l $43E206,x
    bne SourceWeapon4086_PlayerLevel
    lda.l SourceWeapon4086_Player
    tax
    lda.l SourceWeapon4086_NumberLo
    sta.l $43EA00,x
    lda.l SourceWeapon4086_NumberHi
    sta.l $43EA02,x
    bra SourceWeapon4086_Select
SourceWeapon4086_PlayerLevel:
.a16
.i16
    lda.l SourceWeapon4086_Player
    tax
    lda.l SourceWeapon4086_LevelWeaponLo
    sta.l $43EA00,x
    lda.l SourceWeapon4086_LevelWeaponHi
    sta.l $43EA02,x
SourceWeapon4086_Select:
.a16
.i16
    lda.l SourceWeapon4086_Row
    tax
    lda.l $43E200,x
    cmp #$FFFF
    bne SourceWeapon4086_HasList
    jmp SourceWeapon4086_Default
SourceWeapon4086_HasList:
.a16
.i16
    sta.l SourceWeapon4086_Owner
    cmp.l SourceWeapon4086_Models
    bcc SourceWeapon4086_ListOwnerGood
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListOwnerGood:
.a16
.i16
    lda.l SourceWeapon4086_NumberHi
    beq SourceWeapon4086_NumberLow
    jmp SourceWeapon4086_Default ; negative or positive >65535
SourceWeapon4086_NumberLow:
.a16
.i16
    lda.l SourceWeapon4086_NumberLo
    bne SourceWeapon4086_NumberPositive
    jmp SourceWeapon4086_Default
SourceWeapon4086_NumberPositive:
.a16
.i16
    lda.l $43E202,x
    sta.l SourceWeapon4086_Count
    cmp #129
    bcc SourceWeapon4086_ListCountGood
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListCountGood:
.a16
.i16
    cmp.l SourceWeapon4086_NumberLo
    bcs SourceWeapon4086_NumberInRange
    jmp SourceWeapon4086_Default
SourceWeapon4086_NumberInRange:
.a16
.i16
    lda.l SourceWeapon4086_Owner
    asl a
    asl a
    asl a
    clc
    adc #16
    sta.l SourceWeapon4086_Offset
    clc
    adc.l SourceWeapon4086_Base
    tax
    jsr SourceWeapon4086_Read
    cmp.l SourceWeapon4086_Owner
    beq SourceWeapon4086_ListIdentity
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListIdentity:
.a16
.i16
    inx
    inx
    jsr SourceWeapon4086_Read
    cmp.l SourceWeapon4086_Count
    beq SourceWeapon4086_ListSize
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListSize:
.a16
.i16
    inx
    inx
    jsr SourceWeapon4086_Read
    sta.l SourceWeapon4086_Offset
    inx
    inx
    jsr SourceWeapon4086_Read
    beq SourceWeapon4086_ListReserved
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListReserved:
.a16
.i16
    lda.l SourceWeapon4086_Models
    asl a
    asl a
    asl a
    clc
    adc #16
    cmp.l SourceWeapon4086_Offset
    bcc SourceWeapon4086_ListPool
    beq SourceWeapon4086_ListPool
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListPool:
.a16
.i16
    lda.l SourceWeapon4086_Count
    asl a
    clc
    adc.l SourceWeapon4086_Offset
    bcc SourceWeapon4086_ListEnd
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListEnd:
.a16
.i16
    cmp.l SourceWeapon4086_Bytes
    bcc SourceWeapon4086_ListIndex
    beq SourceWeapon4086_ListIndex
    jmp SourceWeapon4086_Bad
SourceWeapon4086_ListIndex:
.a16
.i16
    lda.l SourceWeapon4086_NumberLo
    dec a
    asl a
    clc
    adc.l SourceWeapon4086_Offset
    clc
    adc.l SourceWeapon4086_Base
    tax
    jsr SourceWeapon4086_Read
    bne SourceWeapon4086_SelectedNonzero
    jmp SourceWeapon4086_Default ; source list entry zero is false
SourceWeapon4086_SelectedNonzero:
.a16
.i16
    cmp.l SourceWeapon4086_Models
    bcc SourceWeapon4086_SelectedGood
    jmp SourceWeapon4086_Bad ; FFFF/source -1 is not a Python negative index
SourceWeapon4086_SelectedGood:
.a16
.i16
    sta.l SourceWeapon4086_Selected
    lda.l SourceWeapon4086_AnimFlagLo
    ora.l SourceWeapon4086_AnimFlagHi
    beq SourceWeapon4086_SetSync
    lda #0
    bra SourceWeapon4086_StoreSync
SourceWeapon4086_Default:
.a16
.i16
    lda.l SourceWeapon4086_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $416802,x
    cmp.l SourceWeapon4086_Models
    bcc SourceWeapon4086_DefaultGood
    jmp SourceWeapon4086_Bad
SourceWeapon4086_DefaultGood:
.a16
.i16
    sta.l SourceWeapon4086_Selected
SourceWeapon4086_SetSync:
.a16
.i16
    lda #1
SourceWeapon4086_StoreSync:
.a16
.i16
    sta.l SourceWeapon4086_Sync
SourceWeapon4086_Good:
.a16
.i16
    lda #1
    sta.l SourceWeapon4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceWeapon4086_Bad:
.a16
.i16
    lda #2
    sta.l SourceWeapon4086_Status
    ply
    plx
    plp
    sec
    rtl

SourceWeapon4086_CheckLease:
.a16
.i16
    lda.l SourceWeapon4086_Ready
    cmp #$B4F1
    bne SourceWeapon4086_LeaseBad
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne SourceWeapon4086_LeaseBad
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    bne SourceWeapon4086_LeaseBad
    lda.l SourceWeapon4086_Models
    beq SourceWeapon4086_LeaseBad
    cmp #17
    bcs SourceWeapon4086_LeaseBad
    lda.l SourceWeapon4086_Entities
    beq SourceWeapon4086_LeaseBad
    cmp #129
    bcs SourceWeapon4086_LeaseBad
    cmp.l VmSourceWorld_Count
    bne SourceWeapon4086_LeaseBad
    lda.l SourceWeapon4086_Slot
    cmp.l SourceWeapon4086_Entities
    bcs SourceWeapon4086_LeaseBad
    lda.l SourceWeapon4086_Players
    beq SourceWeapon4086_LeaseBad
    cmp #5
    bcs SourceWeapon4086_LeaseBad
    lda.l SourceWeapon4086_Bank
    cmp #64
    bcs SourceWeapon4086_LeaseBad
    lda.l SourceWeapon4086_Base
    cmp #$8000
    bcc SourceWeapon4086_LeaseBad
    lda.l SourceWeapon4086_Bytes
    cmp #16
    bcc SourceWeapon4086_LeaseBad
    dec a
    clc
    adc.l SourceWeapon4086_Base
    bcs SourceWeapon4086_LeaseBad
    bra SourceWeapon4086_Header
SourceWeapon4086_LeaseBad:
.a16
.i16
    sec
    rts
SourceWeapon4086_Header:
.a16
.i16
    lda.l SourceWeapon4086_Models
    asl a
    asl a
    asl a
    clc
    adc #16
    cmp.l SourceWeapon4086_Bytes
    bcc SourceWeapon4086_HeaderRead
    beq SourceWeapon4086_HeaderRead
    bra SourceWeapon4086_LeaseBad
SourceWeapon4086_HeaderRead:
.a16
.i16
    lda.l SourceWeapon4086_Base
    tax
    jsr SourceWeapon4086_Read
    cmp #$3442
    bne SourceWeapon4086_LeaseBad
    inx
    inx
    jsr SourceWeapon4086_Read
    cmp #$574D
    bne SourceWeapon4086_LeaseBad
    inx
    inx
    jsr SourceWeapon4086_Read
    cmp #1
    bne SourceWeapon4086_LeaseBad
    inx
    inx
    jsr SourceWeapon4086_Read
    cmp.l SourceWeapon4086_Models
    bne SourceWeapon4086_LeaseBad
    inx
    inx
    jsr SourceWeapon4086_Read
    cmp #8
    bne SourceWeapon4086_LeaseBad
    inx
    inx
    jsr SourceWeapon4086_Read
    cmp #16
    bne SourceWeapon4086_LeaseBad
    inx
    inx
    jsr SourceWeapon4086_Read
    cmp #32
    bne SourceWeapon4086_LeaseBad
    inx
    inx
    jsr SourceWeapon4086_Read
    bne SourceWeapon4086_LeaseBad
    clc
    rts

SourceWeapon4086_Read:
.a16
.i16
    phb
    sep #$20
.a8
    lda.l SourceWeapon4086_Bank
    pha
    plb
    rep #$20
.a16
    lda.w $0000,x
    plb
    ora #0
    rts
