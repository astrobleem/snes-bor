; Synchronous no-event/no-minion kill leaf. B4F8 is NOT gameplay admission.
; Installer proves no initialized onkill or script clear entry for the complete
; registry, validates/publishes the relation/role/variable/core/flag leases.
; Dynamic minion branches are rejected BEFORE live mutation. They require the
; separate damage/recursive-kill service capability; never discard a minion.
; All normal source relation, role, script-instance and self cleanup is real.
; Scratch is synchronous, outside frame snapshot, not live across callbacks.
SourceRetirement4086_Ready = $7FFE40
SourceRetirement4086_Slot = $7FFE42
SourceRetirement4086_Status = $7FFE44 ; 0 idle,1 running,2 done,3 fault
SourceRetirement4086_Victim = $7FFE46 ; physical low token
SourceRetirement4086_Relation = $7FFE48
SourceRetirement4086_View = $7FFE4A
SourceRetirement4086_Core = $7FFE4C
SourceRetirement4086_Flags = $7FFE4E
SourceRetirement4086_OldSelfLo = $7FFE50
SourceRetirement4086_OldSelfHi = $7FFE52
SourceRetirement4086_Row = $7FFE54
SourceRetirement4086_Field = $7FFE56
SourceRetirement4086_AliveCount = $7FFE58
SourceRetirement4086_Temporary = $7FFE5A
SourceRetirement4086_ArgLo = $7FFE5C
SourceRetirement4086_ArgHi = $7FFE5E
SourceRetirement4086_PreflightView = $7FFE60
SOURCE_RETIREMENT_RELATIONS = $409000
SOURCE_RETIREMENT_ROLES = $43FD80

; Public physical-pointer resolver for the typed script API. Dead pool rows
; remain valid pointers. Do not route killentity through an alive-only lookup.
SourceRetirement4086_ResolvePointer:
.a16
.i16
    php
    rep #$38
    phy
    lda.l SourceRetirement4086_Ready
    cmp #$B4F8
    bne SourceRetirement4086_ResolveBad
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne SourceRetirement4086_ResolveBad
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    bne SourceRetirement4086_ResolveBad
    lda.l VmSourceWorld_Count
    beq SourceRetirement4086_ResolveBad
    cmp #129
    bcs SourceRetirement4086_ResolveBad
    lda.l SourceRetirement4086_ArgHi
    tay
    lda.l SourceRetirement4086_ArgLo
    jsr SourceRetirement4086_Pointer
    bcs SourceRetirement4086_ResolveBad
    ply
    plp
    clc
    rtl
SourceRetirement4086_ResolveBad:
.a16
.i16
    lda #3
    sta.l SourceRetirement4086_Status
    ply
    plp
    sec
    rtl

SourceRetirement4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceRetirement4086_Ready
    bne SourceRetirement4086_Branch_1
    jmp SourceRetirement4086_IdleGood
SourceRetirement4086_Branch_1:
.a16
.i16
    cmp #$B4F8
    beq SourceRetirement4086_Branch_2
    jmp SourceRetirement4086_IdleBad
SourceRetirement4086_Branch_2:
.a16
.i16
    lda.l SourceRetirement4086_Status
    bne SourceRetirement4086_Branch_3
    jmp SourceRetirement4086_IdleGood
SourceRetirement4086_Branch_3:
.a16
.i16
    cmp #2
    beq SourceRetirement4086_Branch_4
    jmp SourceRetirement4086_IdleBad
SourceRetirement4086_Branch_4:
.a16
.i16
SourceRetirement4086_IdleGood:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceRetirement4086_IdleBad:
.a16
.i16
    pla
    plp
    sec
    rtl

SourceRetirement4086_ApplyNoEvents:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsl SourceRetirement4086_PreflightNoEvents
    bcc SourceRetirement4086_ApplyChecked
    jmp SourceRetirement4086_Bad
SourceRetirement4086_ApplyChecked:
.a16
.i16
    ora #0
    bne SourceRetirement4086_ApplyLive
    jmp SourceRetirement4086_Done
SourceRetirement4086_ApplyLive:
.a16
.i16
    jmp SourceRetirement4086_Mutate
SourceRetirement4086_PreflightNoEvents:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceRetirement4086_Ready
    cmp #$B4F8
    beq SourceRetirement4086_Branch_5
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_5:
.a16
.i16
    lda.l SourceRetirement4086_Status
    bne SourceRetirement4086_Branch_6
    jmp SourceRetirement4086_World
SourceRetirement4086_Branch_6:
.a16
.i16
    cmp #2
    beq SourceRetirement4086_Branch_7
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_7:
.a16
.i16
SourceRetirement4086_World:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceRetirement4086_Branch_8
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_8:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq SourceRetirement4086_Branch_9
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_9:
.a16
.i16
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    beq SourceRetirement4086_Branch_10
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_10:
.a16
.i16
    lda.l VmSourceWorld_Count
    bne SourceRetirement4086_Branch_11
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_11:
.a16
.i16
    cmp #129
    bcc SourceRetirement4086_Branch_12
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_12:
.a16
.i16
    cmp.l SourceRetirement4086_Slot
    bcs SourceRetirement4086_Branch_13
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_13:
.a16
.i16
    bne SourceRetirement4086_Branch_14
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_14:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Ready
    cmp #$B4EB
    beq SourceRetirement4086_Branch_15
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_15:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Entities
    cmp.l VmSourceWorld_Count
    beq SourceRetirement4086_Branch_16
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_16:
.a16
.i16
    lda.l SourceIdle4086_Ready
    cmp #$B4F3
    beq SourceRetirement4086_Branch_17
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_17:
.a16
.i16
    lda.l VmSourceVars_Ready
    cmp #$B4A4
    beq SourceRetirement4086_Branch_18
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_18:
.a16
.i16
    lda.l VmSourceVars_Base
    cmp #$8800
    beq SourceRetirement4086_Branch_19
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_19:
.a16
.i16
    lda.l VmSourceVars_Bank
    and #$00FF
    cmp #$0041
    beq SourceRetirement4086_Branch_20
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_20:
.a16
.i16
    lda.l VmSourceVars_Count
    bne SourceRetirement4086_Branch_21
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_21:
.a16
.i16
    cmp #385
    bcc SourceRetirement4086_Branch_22
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_22:
.a16
.i16
    lda.l SourceSelf4086_Ready
    cmp #$B4F6
    beq SourceRetirement4086_Branch_23
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_23:
.a16
.i16
    lda.l SourceSelf4086_Fault
    beq SourceRetirement4086_Branch_24
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_24:
.a16
.i16
    lda.l SourceSelf4086_GlobalHigh
    tay
    lda.l SourceSelf4086_GlobalLow
    jsr SourceRetirement4086_Pointer
    bcc SourceRetirement4086_Branch_25
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_25:
.a16
.i16
    lda.l SourceSelf4086_GlobalLow
    sta.l SourceRetirement4086_OldSelfLo
    lda.l SourceSelf4086_GlobalHigh
    sta.l SourceRetirement4086_OldSelfHi
    lda.l SourceRetirement4086_Slot
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_Row
    sta.l SourceRetirement4086_Relation
    lda.l SourceRetirement4086_Temporary
    sta.l SourceRetirement4086_Victim
    ; Validate victim/live rows and count before any live write. Empty inactive
    ; rows are not traversed by source kill and need no repeated pointer scan.
    lda #0
    sta.l SourceRetirement4086_AliveCount
    sta.l SourceRetirement4086_PreflightView
    ldx #0
    ldy #0
SourceRetirement4086_PreflightRow:
.a16
.i16
    lda.l $414004,x
    cmp #2
    bcc SourceRetirement4086_Branch_26
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_26:
.a16
.i16
    clc
    adc.l SourceRetirement4086_AliveCount
    sta.l SourceRetirement4086_AliveCount
    lda.l $414004,x
    bne SourceRetirement4086_PreflightRequired
    tya
    cmp.l SourceRetirement4086_Slot
    beq SourceRetirement4086_PreflightRequired
    jmp SourceRetirement4086_PreflightNext
SourceRetirement4086_PreflightRequired:
.a16
.i16
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+48,x
    ora.l SOURCE_RETIREMENT_RELATIONS+50,x
    ora.l SOURCE_RETIREMENT_RELATIONS+52,x
    ora.l SOURCE_RETIREMENT_RELATIONS+54,x
    ora.l SOURCE_RETIREMENT_RELATIONS+56,x
    ora.l SOURCE_RETIREMENT_RELATIONS+58,x
    ora.l SOURCE_RETIREMENT_RELATIONS+60,x
    ora.l SOURCE_RETIREMENT_RELATIONS+62,x
    beq SourceRetirement4086_Branch_27
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_27:
.a16
.i16
    phy
    lda #8
    sta.l SourceRetirement4086_Field
SourceRetirement4086_PreflightPointer:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS+2,x
    tay
    lda.l SOURCE_RETIREMENT_RELATIONS,x
    jsr SourceRetirement4086_Pointer
    bcc SourceRetirement4086_Branch_28
    jmp SourceRetirement4086_PointerFailed
SourceRetirement4086_Branch_28:
.a16
.i16
    inx
    inx
    inx
    inx
    lda.l SourceRetirement4086_Field
    dec a
    sta.l SourceRetirement4086_Field
    beq SourceRetirement4086_Branch_29
    jmp SourceRetirement4086_PreflightPointer
SourceRetirement4086_Branch_29:
.a16
.i16
    ply
SourceRetirement4086_PreflightNext:
.a16
.i16
    lda.l SourceRetirement4086_PreflightView
    clc
    adc #80
    sta.l SourceRetirement4086_PreflightView
    tax
    iny
    tya
    cmp.l VmSourceWorld_Count
    bcs SourceRetirement4086_Branch_30
    jmp SourceRetirement4086_PreflightRow
SourceRetirement4086_Branch_30:
.a16
.i16
    lda.l SOURCE_RETIREMENT_ROLES+2
    beq SourceRetirement4086_Branch_31
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_31:
.a16
.i16
    lda.l SOURCE_RETIREMENT_ROLES
    cmp.l SourceRetirement4086_AliveCount
    beq SourceRetirement4086_Branch_32
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_32:
.a16
.i16
    ldx #4
SourceRetirement4086_PreflightRoles:
.a16
.i16
    lda.l SOURCE_RETIREMENT_ROLES+2,x
    tay
    lda.l SOURCE_RETIREMENT_ROLES,x
    jsr SourceRetirement4086_Pointer
    bcc SourceRetirement4086_Branch_33
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_33:
.a16
.i16
    inx
    inx
    inx
    inx
    cpx #28
    bcs SourceRetirement4086_Branch_34
    jmp SourceRetirement4086_PreflightRoles
SourceRetirement4086_Branch_34:
.a16
.i16
    lda.l SourceRetirement4086_Slot
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_View
    tax
    lda.l $414004,x
    bne SourceRetirement4086_Branch_35
    jmp SourceRetirement4086_PreflightDead
SourceRetirement4086_Branch_35:
.a16
.i16
    lda.l SourceRetirement4086_Relation
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+38,x
    beq SourceRetirement4086_Branch_36
    jmp SourceRetirement4086_NoSingleMinion
SourceRetirement4086_Branch_36:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS+36,x
    cmp #1
    beq SourceRetirement4086_Branch_37
    jmp SourceRetirement4086_NoSingleMinion
SourceRetirement4086_Branch_37:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS+4,x
    ora.l SOURCE_RETIREMENT_RELATIONS+6,x
    beq SourceRetirement4086_Branch_38
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_38:
.a16
.i16
SourceRetirement4086_NoSingleMinion:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS+38,x
    beq SourceRetirement4086_Branch_39
    jmp SourceRetirement4086_PreflightLive
SourceRetirement4086_Branch_39:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS+36,x
    cmp #2
    beq SourceRetirement4086_Branch_40
    jmp SourceRetirement4086_PreflightLive
SourceRetirement4086_Branch_40:
.a16
.i16
    ldy #0
SourceRetirement4086_CheckAllMinions:
.a16
.i16
    tya
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_View
    tax
    lda.l $414004,x
    bne SourceRetirement4086_Branch_41
    jmp SourceRetirement4086_NoChild
SourceRetirement4086_Branch_41:
.a16
.i16
    lda.l SourceRetirement4086_Row
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS,x
    cmp.l SourceRetirement4086_Victim
    bne SourceRetirement4086_Branch_42
    jmp SourceRetirement4086_Bad
SourceRetirement4086_Branch_42:
.a16
.i16
SourceRetirement4086_NoChild:
.a16
.i16
    iny
    tya
    cmp.l VmSourceWorld_Count
    bcs SourceRetirement4086_Branch_43
    jmp SourceRetirement4086_CheckAllMinions
SourceRetirement4086_Branch_43:
.a16
.i16
SourceRetirement4086_PreflightLive:
.a16
.i16
    lda #1
    bra SourceRetirement4086_PreflightGood
SourceRetirement4086_PreflightDead:
.a16
.i16
    lda #0
SourceRetirement4086_PreflightGood:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
SourceRetirement4086_Mutate:
.a16
.i16
    lda #1
    sta.l SourceRetirement4086_Status
    lda.l SourceRetirement4086_Slot
    jsr SourceRetirement4086_Offsets
    ; TYPE_SHOT owner/player cantfire release.
    lda.l SourceRetirement4086_Core
    tax
    lda.l $40C048,x
    and #32
    bne SourceRetirement4086_Branch_44
    jmp SourceRetirement4086_Unlink
SourceRetirement4086_Branch_44:
.a16
.i16
    lda.l SourceRetirement4086_Relation
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+10,x
    tay
    lda.l SOURCE_RETIREMENT_RELATIONS+8,x
    jsr SourceRetirement4086_Pointer
    cmp #$FFFF
    bne SourceRetirement4086_Branch_45
    jmp SourceRetirement4086_Unlink
SourceRetirement4086_Branch_45:
.a16
.i16
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_Core
    tax
    lda.l $40C048,x
    and #1
    bne SourceRetirement4086_Branch_46
    jmp SourceRetirement4086_Unlink
SourceRetirement4086_Branch_46:
.a16
.i16
    lda.l SourceRetirement4086_Row
    tax
    lda #0
    sta.l SOURCE_RETIREMENT_RELATIONS+32,x
    sta.l SOURCE_RETIREMENT_RELATIONS+34,x
SourceRetirement4086_Unlink:
.a16
.i16
    lda.l SourceRetirement4086_Relation
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+30,x
    tay
    lda.l SOURCE_RETIREMENT_RELATIONS+28,x
    jsr SourceRetirement4086_Pointer
    cmp #$FFFF
    bne SourceRetirement4086_Branch_47
    jmp SourceRetirement4086_UnlinkVictim
SourceRetirement4086_Branch_47:
.a16
.i16
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_Row
    tax
    lda #0
    sta.l SOURCE_RETIREMENT_RELATIONS+28,x
    sta.l SOURCE_RETIREMENT_RELATIONS+30,x
    lda.l SourceRetirement4086_Core
    tax
    lda #0
    sta.l $40C050,x
    sta.l $40C052,x
SourceRetirement4086_UnlinkVictim:
.a16
.i16
    lda.l SourceRetirement4086_Slot
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_Row
    tax
    lda #0
    sta.l SOURCE_RETIREMENT_RELATIONS+28,x
    sta.l SOURCE_RETIREMENT_RELATIONS+30,x
    sta.l SOURCE_RETIREMENT_RELATIONS+44,x
    sta.l SOURCE_RETIREMENT_RELATIONS+46,x
    lda.l SourceRetirement4086_Core
    tax
    lda #0
    sta.l $40C050,x
    sta.l $40C052,x
    lda.l SourceRetirement4086_Flags
    tax
    lda #0
    sta.l $43EB1C,x
    sta.l $43EB1E,x
    lda.l SourceRetirement4086_View
    tax
    lda #0
    sta.l $414024,x
    sta.l $414026,x
    sta.l $414004,x
    lda.l SOURCE_RETIREMENT_ROLES
    dec a
    sta.l SOURCE_RETIREMENT_ROLES
    ; Script_Clear(method=1) with no clear entry keeps names but empties values.
    ldx #0
    ldy #0
SourceRetirement4086_ClearVariables:
.a16
.i16
    lda.l $418800,x
    cmp.l SourceRetirement4086_Victim
    beq SourceRetirement4086_Branch_48
    jmp SourceRetirement4086_VariableNext
SourceRetirement4086_Branch_48:
.a16
.i16
    lda.l $418802,x
    cmp #$0041
    beq SourceRetirement4086_Branch_49
    jmp SourceRetirement4086_VariableNext
SourceRetirement4086_Branch_49:
.a16
.i16
    lda #0
    sta.l $418808,x
    sta.l $41880A,x
    sta.l $41880C,x
    sta.l $41880E,x
SourceRetirement4086_VariableNext:
.a16
.i16
    txa
    clc
    adc #64
    tax
    iny
    tya
    cmp.l VmSourceVars_Count
    bcs SourceRetirement4086_Branch_50
    jmp SourceRetirement4086_ClearVariables
SourceRetirement4086_Branch_50:
.a16
.i16
    ; Parent's subentity is cleared only when it actually names this victim.
    lda.l SourceRetirement4086_Relation
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+2,x
    tay
    lda.l SOURCE_RETIREMENT_RELATIONS,x
    jsr SourceRetirement4086_Pointer
    cmp #$FFFF
    bne SourceRetirement4086_Branch_51
    jmp SourceRetirement4086_ClearParent
SourceRetirement4086_Branch_51:
.a16
.i16
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_Row
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+6,x
    cmp #$0041
    beq SourceRetirement4086_ParentSubMapped
    jmp SourceRetirement4086_ClearParent
SourceRetirement4086_ParentSubMapped:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS+4,x
    cmp.l SourceRetirement4086_Victim
    beq SourceRetirement4086_Branch_52
    jmp SourceRetirement4086_ClearParent
SourceRetirement4086_Branch_52:
.a16
.i16
    lda #0
    sta.l SOURCE_RETIREMENT_RELATIONS+4,x
    sta.l SOURCE_RETIREMENT_RELATIONS+6,x
SourceRetirement4086_ClearParent:
.a16
.i16
    lda.l SourceRetirement4086_Relation
    tax
    lda #0
    sta.l SOURCE_RETIREMENT_RELATIONS,x
    sta.l SOURCE_RETIREMENT_RELATIONS+2,x
    sta.l SOURCE_RETIREMENT_RELATIONS+4,x
    sta.l SOURCE_RETIREMENT_RELATIONS+6,x
    ; Preserve the source else-if ordering: only the first player match clears.
    ldx #4
SourceRetirement4086_Player:
.a16
.i16
    lda.l SOURCE_RETIREMENT_ROLES,x
    cmp.l SourceRetirement4086_Victim
    bne SourceRetirement4086_Branch_53
    jmp SourceRetirement4086_PlayerClear
SourceRetirement4086_Branch_53:
.a16
.i16
    inx
    inx
    inx
    inx
    cpx #20
    bcs SourceRetirement4086_Branch_54
    jmp SourceRetirement4086_Player
SourceRetirement4086_Branch_54:
.a16
.i16
    bra SourceRetirement4086_GlobalRoles
SourceRetirement4086_PlayerClear:
.a16
.i16
    lda #0
    sta.l SOURCE_RETIREMENT_ROLES,x
    sta.l SOURCE_RETIREMENT_ROLES+2,x
SourceRetirement4086_GlobalRoles:
.a16
.i16
    ldx #20
SourceRetirement4086_GlobalRole:
.a16
.i16
    lda.l SOURCE_RETIREMENT_ROLES,x
    cmp.l SourceRetirement4086_Victim
    beq SourceRetirement4086_Branch_55
    jmp SourceRetirement4086_GlobalNext
SourceRetirement4086_Branch_55:
.a16
.i16
    lda #0
    sta.l SOURCE_RETIREMENT_ROLES,x
    sta.l SOURCE_RETIREMENT_ROLES+2,x
SourceRetirement4086_GlobalNext:
.a16
.i16
    inx
    inx
    inx
    inx
    cpx #28
    bcs SourceRetirement4086_Branch_56
    jmp SourceRetirement4086_GlobalRole
SourceRetirement4086_Branch_56:
.a16
.i16
    ldy #0
SourceRetirement4086_Scan:
.a16
.i16
    tya
    jsr SourceRetirement4086_Offsets
    lda.l SourceRetirement4086_View
    tax
    lda.l $414004,x
    bne SourceRetirement4086_Branch_57
    jmp SourceRetirement4086_ScanNext
SourceRetirement4086_Branch_57:
.a16
.i16
    lda.l SourceRetirement4086_Temporary
    sta.l SourceSelf4086_GlobalLow
    lda #$0041
    sta.l SourceSelf4086_GlobalHigh
    lda.l SourceRetirement4086_Row
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS,x
    cmp.l SourceRetirement4086_Victim
    beq SourceRetirement4086_Branch_58
    jmp SourceRetirement4086_OwnerRepair
SourceRetirement4086_Branch_58:
.a16
.i16
    lda #0
    sta.l SOURCE_RETIREMENT_RELATIONS,x
    sta.l SOURCE_RETIREMENT_RELATIONS+2,x
SourceRetirement4086_OwnerRepair:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS+8,x
    cmp.l SourceRetirement4086_Victim
    beq SourceRetirement4086_Branch_59
    jmp SourceRetirement4086_RepairRelations
SourceRetirement4086_Branch_59:
.a16
.i16
    phx
    lda.l SourceRetirement4086_Relation
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+8,x
    plx
    sta.l SOURCE_RETIREMENT_RELATIONS+8,x
    phx
    lda.l SourceRetirement4086_Relation
    tax
    lda.l SOURCE_RETIREMENT_RELATIONS+10,x
    plx
    sta.l SOURCE_RETIREMENT_RELATIONS+10,x
SourceRetirement4086_RepairRelations:
.a16
.i16
    ; opponent/binding/landed/hithead occupy four consecutive pointer fields.
    lda #4
    sta.l SourceRetirement4086_Field
    txa
    clc
    adc #12
    tax
SourceRetirement4086_RepairPointer:
.a16
.i16
    lda.l SOURCE_RETIREMENT_RELATIONS,x
    cmp.l SourceRetirement4086_Victim
    beq SourceRetirement4086_Branch_60
    jmp SourceRetirement4086_RepairNext
SourceRetirement4086_Branch_60:
.a16
.i16
    lda #0
    sta.l SOURCE_RETIREMENT_RELATIONS,x
    sta.l SOURCE_RETIREMENT_RELATIONS+2,x
SourceRetirement4086_RepairNext:
.a16
.i16
    inx
    inx
    inx
    inx
    lda.l SourceRetirement4086_Field
    dec a
    sta.l SourceRetirement4086_Field
    beq SourceRetirement4086_Branch_61
    jmp SourceRetirement4086_RepairPointer
SourceRetirement4086_Branch_61:
.a16
.i16
    lda.l SourceRetirement4086_Core
    tax
    lda.l $40C054,x
    cmp.l SourceRetirement4086_Victim
    beq SourceRetirement4086_Branch_62
    jmp SourceRetirement4086_Textbox
SourceRetirement4086_Branch_62:
.a16
.i16
    lda.l $40C056,x
    cmp #$0041
    beq SourceRetirement4086_Branch_63
    jmp SourceRetirement4086_Textbox
SourceRetirement4086_Branch_63:
.a16
.i16
    lda #0
    sta.l $40C054,x
    sta.l $40C056,x
SourceRetirement4086_Textbox:
.a16
.i16
    lda.l SOURCE_RETIREMENT_ROLES+24
    ora.l SOURCE_RETIREMENT_ROLES+26
    beq SourceRetirement4086_Branch_64
    jmp SourceRetirement4086_ScanNext
SourceRetirement4086_Branch_64:
.a16
.i16
    lda.l $40C048,x
    and #128
    bne SourceRetirement4086_Branch_65
    jmp SourceRetirement4086_ScanNext
SourceRetirement4086_Branch_65:
.a16
.i16
    lda.l SourceRetirement4086_Temporary
    sta.l SOURCE_RETIREMENT_ROLES+24
    lda #$0041
    sta.l SOURCE_RETIREMENT_ROLES+26
SourceRetirement4086_ScanNext:
.a16
.i16
    iny
    tya
    cmp.l VmSourceWorld_Count
    bcs SourceRetirement4086_Branch_66
    jmp SourceRetirement4086_Scan
SourceRetirement4086_Branch_66:
.a16
.i16
    lda.l SourceRetirement4086_OldSelfLo
    sta.l SourceSelf4086_GlobalLow
    lda.l SourceRetirement4086_OldSelfHi
    sta.l SourceSelf4086_GlobalHigh
SourceRetirement4086_Done:
.a16
.i16
    lda #2
    sta.l SourceRetirement4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceRetirement4086_PointerFailed:
.a16
.i16
    ply
SourceRetirement4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceRetirement4086_Status
    ply
    plx
    plp
    sec
    rtl

; A=slot. Synchronous conversion preserves X/Y, updates only scratch.
SourceRetirement4086_Offsets:
.a16
.i16
    pha
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceRetirement4086_Flags
    asl a
    sta.l SourceRetirement4086_Row
    clc
    adc.l SourceRetirement4086_Flags
    sta.l SourceRetirement4086_Core
    lda 1,s
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceRetirement4086_Row
    sta.l SourceRetirement4086_View
    clc
    adc #$4000
    sta.l SourceRetirement4086_Temporary
    pla
    rts

; A=low,Y=high. Return A=slot or FFFF for NULL. Preserve X/Y except carry.
SourceRetirement4086_Pointer:
.a16
.i16
    phx
    pha
    tya
    cmp #$0041
    bne SourceRetirement4086_Branch_67
    jmp SourceRetirement4086_PointerMapped
SourceRetirement4086_Branch_67:
.a16
.i16
    ora 1,s
    beq SourceRetirement4086_Branch_68
    jmp SourceRetirement4086_PointerBad
SourceRetirement4086_Branch_68:
.a16
.i16
    pla
    lda #$FFFF
    plx
    clc
    rts
SourceRetirement4086_PointerMapped:
.a16
.i16
    pla
    cmp #$4000
    bcs SourceRetirement4086_Branch_69
    jmp SourceRetirement4086_PointerReject
SourceRetirement4086_Branch_69:
.a16
.i16
    cmp #$6800
    bcc SourceRetirement4086_Branch_70
    jmp SourceRetirement4086_PointerReject
SourceRetirement4086_Branch_70:
.a16
.i16
    sec
    sbc #$4000
    tax
    and #15
    bne SourceRetirement4086_PointerReject
    txa
    lsr a
    lsr a
    lsr a
    lsr a
    asl a
    tax
    lda.l SourceRetirement4086_SlotIndex,x
    cmp.l VmSourceWorld_Count
    bcs SourceRetirement4086_PointerReject
    plx
    clc
    rts
SourceRetirement4086_PointerBad:
.a16
.i16
    pla
SourceRetirement4086_PointerReject:
.a16
.i16
    plx
    sec
    rts

; Physical 80-byte pool stride: aligned 16-byte offsets map every fifth
; element to a slot. The other four entries reject rather than round.
SourceRetirement4086_SlotIndex:
    .dw 0,65535,65535,65535,65535
    .dw 1,65535,65535,65535,65535
    .dw 2,65535,65535,65535,65535
    .dw 3,65535,65535,65535,65535
    .dw 4,65535,65535,65535,65535
    .dw 5,65535,65535,65535,65535
    .dw 6,65535,65535,65535,65535
    .dw 7,65535,65535,65535,65535
    .dw 8,65535,65535,65535,65535
    .dw 9,65535,65535,65535,65535
    .dw 10,65535,65535,65535,65535
    .dw 11,65535,65535,65535,65535
    .dw 12,65535,65535,65535,65535
    .dw 13,65535,65535,65535,65535
    .dw 14,65535,65535,65535,65535
    .dw 15,65535,65535,65535,65535
    .dw 16,65535,65535,65535,65535
    .dw 17,65535,65535,65535,65535
    .dw 18,65535,65535,65535,65535
    .dw 19,65535,65535,65535,65535
    .dw 20,65535,65535,65535,65535
    .dw 21,65535,65535,65535,65535
    .dw 22,65535,65535,65535,65535
    .dw 23,65535,65535,65535,65535
    .dw 24,65535,65535,65535,65535
    .dw 25,65535,65535,65535,65535
    .dw 26,65535,65535,65535,65535
    .dw 27,65535,65535,65535,65535
    .dw 28,65535,65535,65535,65535
    .dw 29,65535,65535,65535,65535
    .dw 30,65535,65535,65535,65535
    .dw 31,65535,65535,65535,65535
    .dw 32,65535,65535,65535,65535
    .dw 33,65535,65535,65535,65535
    .dw 34,65535,65535,65535,65535
    .dw 35,65535,65535,65535,65535
    .dw 36,65535,65535,65535,65535
    .dw 37,65535,65535,65535,65535
    .dw 38,65535,65535,65535,65535
    .dw 39,65535,65535,65535,65535
    .dw 40,65535,65535,65535,65535
    .dw 41,65535,65535,65535,65535
    .dw 42,65535,65535,65535,65535
    .dw 43,65535,65535,65535,65535
    .dw 44,65535,65535,65535,65535
    .dw 45,65535,65535,65535,65535
    .dw 46,65535,65535,65535,65535
    .dw 47,65535,65535,65535,65535
    .dw 48,65535,65535,65535,65535
    .dw 49,65535,65535,65535,65535
    .dw 50,65535,65535,65535,65535
    .dw 51,65535,65535,65535,65535
    .dw 52,65535,65535,65535,65535
    .dw 53,65535,65535,65535,65535
    .dw 54,65535,65535,65535,65535
    .dw 55,65535,65535,65535,65535
    .dw 56,65535,65535,65535,65535
    .dw 57,65535,65535,65535,65535
    .dw 58,65535,65535,65535,65535
    .dw 59,65535,65535,65535,65535
    .dw 60,65535,65535,65535,65535
    .dw 61,65535,65535,65535,65535
    .dw 62,65535,65535,65535,65535
    .dw 63,65535,65535,65535,65535
    .dw 64,65535,65535,65535,65535
    .dw 65,65535,65535,65535,65535
    .dw 66,65535,65535,65535,65535
    .dw 67,65535,65535,65535,65535
    .dw 68,65535,65535,65535,65535
    .dw 69,65535,65535,65535,65535
    .dw 70,65535,65535,65535,65535
    .dw 71,65535,65535,65535,65535
    .dw 72,65535,65535,65535,65535
    .dw 73,65535,65535,65535,65535
    .dw 74,65535,65535,65535,65535
    .dw 75,65535,65535,65535,65535
    .dw 76,65535,65535,65535,65535
    .dw 77,65535,65535,65535,65535
    .dw 78,65535,65535,65535,65535
    .dw 79,65535,65535,65535,65535
    .dw 80,65535,65535,65535,65535
    .dw 81,65535,65535,65535,65535
    .dw 82,65535,65535,65535,65535
    .dw 83,65535,65535,65535,65535
    .dw 84,65535,65535,65535,65535
    .dw 85,65535,65535,65535,65535
    .dw 86,65535,65535,65535,65535
    .dw 87,65535,65535,65535,65535
    .dw 88,65535,65535,65535,65535
    .dw 89,65535,65535,65535,65535
    .dw 90,65535,65535,65535,65535
    .dw 91,65535,65535,65535,65535
    .dw 92,65535,65535,65535,65535
    .dw 93,65535,65535,65535,65535
    .dw 94,65535,65535,65535,65535
    .dw 95,65535,65535,65535,65535
    .dw 96,65535,65535,65535,65535
    .dw 97,65535,65535,65535,65535
    .dw 98,65535,65535,65535,65535
    .dw 99,65535,65535,65535,65535
    .dw 100,65535,65535,65535,65535
    .dw 101,65535,65535,65535,65535
    .dw 102,65535,65535,65535,65535
    .dw 103,65535,65535,65535,65535
    .dw 104,65535,65535,65535,65535
    .dw 105,65535,65535,65535,65535
    .dw 106,65535,65535,65535,65535
    .dw 107,65535,65535,65535,65535
    .dw 108,65535,65535,65535,65535
    .dw 109,65535,65535,65535,65535
    .dw 110,65535,65535,65535,65535
    .dw 111,65535,65535,65535,65535
    .dw 112,65535,65535,65535,65535
    .dw 113,65535,65535,65535,65535
    .dw 114,65535,65535,65535,65535
    .dw 115,65535,65535,65535,65535
    .dw 116,65535,65535,65535,65535
    .dw 117,65535,65535,65535,65535
    .dw 118,65535,65535,65535,65535
    .dw 119,65535,65535,65535,65535
    .dw 120,65535,65535,65535,65535
    .dw 121,65535,65535,65535,65535
    .dw 122,65535,65535,65535,65535
    .dw 123,65535,65535,65535,65535
    .dw 124,65535,65535,65535,65535
    .dw 125,65535,65535,65535,65535
    .dw 126,65535,65535,65535,65535
    .dw 127,65535,65535,65535,65535
