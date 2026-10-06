; set_model_ex ordered continuation. Services must be bound by the admitted
; source profile; this owner never acknowledges them implicitly. Service 1
; snapshots old entity/combat factors when onmodelcopy is initialized. Service
; 2 installs the remaining shallow modeldata (including immutable palette,
; scripts, weapon metadata, animation parameters); 3/6 apply colourmap; 4
; completes nested frame-zero initialization; 5 copies scripts/factors; 7 runs
; onmodelcopy and releases its snapshot. Even a no-op service needs explicit Ack.
; Included in the frame stack's $7FFB50..$7FFD3F continuation snapshot.
SourceModelTransition4086_Ready = $7FFD00
SourceModelTransition4086_State = $7FFD02
SourceModelTransition4086_Service = $7FFD04
SourceModelTransition4086_Acknowledged = $7FFD06
SourceModelTransition4086_Slot = $7FFD08
SourceModelTransition4086_New = $7FFD0A
SourceModelTransition4086_Old = $7FFD0C
SourceModelTransition4086_Side = $7FFD0E
SourceModelTransition4086_Core = $7FFD10
SourceModelTransition4086_OldTypeLo = $7FFD12
SourceModelTransition4086_OldTypeHi = $7FFD14
SourceModelTransition4086_Flags = $7FFD16
SourceModelTransition4086_Temp = $7FFD18

SourceModelTransition4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceModelTransition4086_Ready
    beq SourceModelTransition4086_IdleGood
    cmp #$B4F0
    bne SourceModelTransition4086_IdleBad
    lda.l SourceModelTransition4086_State
    beq SourceModelTransition4086_IdleGood
    cmp #2
    bne SourceModelTransition4086_IdleBad
    lda.l SourceModelTransition4086_Service
    bne SourceModelTransition4086_IdleBad
SourceModelTransition4086_IdleGood:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceModelTransition4086_IdleBad:
.a16
.i16
    pla
    plp
    sec
    rtl

SourceModelTransition4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsl SourceModelTransition4086_CheckIdle
    bcc SourceModelTransition4086_BeginLease
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginLease:
.a16
.i16
    lda.l SourceModelTransition4086_Ready
    cmp #$B4F0
    beq SourceModelTransition4086_BeginWorld
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginWorld:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceModelTransition4086_BeginPool
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginPool:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq SourceModelTransition4086_BeginCount
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginCount:
.a16
.i16
    lda.l VmSourceWorld_Count
    beq SourceModelTransition4086_BeginReject
    cmp #129
    bcs SourceModelTransition4086_BeginReject
    lda.l SourceModelTransition4086_Slot
    cmp.l VmSourceWorld_Count
    bcc SourceModelTransition4086_BeginSide
SourceModelTransition4086_BeginReject:
.a16
.i16
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginSide:
.a16
.i16
    ; physical entity slot, not presentation order
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceModelTransition4086_Temp
    asl a
    clc
    adc #$6800
    sta.l SourceModelTransition4086_Side
    tax
    lda.l $410000,x
    sta.l SourceModelTransition4086_Old
    lda.l SourceModelTransition4086_New
    cmp.l SourceModelEntityCopy4086_Models
    bcc SourceModelTransition4086_BeginOld
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginOld:
.a16
.i16
    lda.l SourceModelTransition4086_Old
    cmp.l SourceModelEntityCopy4086_Models
    bcc SourceModelTransition4086_BeginSame
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginSame:
.a16
.i16
    cmp.l SourceModelTransition4086_New
    bne SourceModelTransition4086_BeginComponents
    jmp SourceModelTransition4086_Done ; source early return
SourceModelTransition4086_BeginComponents:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Ready
    cmp #$B4EB
    beq SourceModelTransition4086_BeginCache
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginCache:
.a16
.i16
    lda.l SourceModelCachedCopy4086_Ready
    cmp #$B4EE
    beq SourceModelTransition4086_BeginAnimationCache
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginAnimationCache:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_Ready
    cmp #$B4E9
    beq SourceModelTransition4086_BeginModelAnimation
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginModelAnimation:
.a16
.i16
    lda.l SourceModelAnimation4086_Ready
    cmp #$B4EF
    beq SourceModelTransition4086_BeginGeometry
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginGeometry:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Models
    beq SourceModelTransition4086_BeginGeometryBad
    cmp #17
    bcs SourceModelTransition4086_BeginGeometryBad
    cmp.l SourceModelCachedCopy4086_Models
    bne SourceModelTransition4086_BeginGeometryBad
    cmp.l SourceModelAnimationCopy4086_Models
    bne SourceModelTransition4086_BeginGeometryBad
    lda.l SourceModelEntityCopy4086_Entities
    cmp.l VmSourceWorld_Count
    beq SourceModelTransition4086_BeginCore
SourceModelTransition4086_BeginGeometryBad:
.a16
.i16
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginCore:
.a16
.i16
    lda.l SourceModelTransition4086_Side
    sec
    sbc #$6800 ; slot*64
    clc
    adc.l SourceModelTransition4086_Temp ; slot*32
    clc
    adc #$C000
    sta.l SourceModelTransition4086_Core
    tax
    lda.l $400048,x
    sta.l SourceModelTransition4086_OldTypeLo
    lda.l $40004A,x
    sta.l SourceModelTransition4086_OldTypeHi
    lda.l SourceModelTransition4086_New
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$BA00
    tax
    lda.l $400004,x
    sta.l SourceModelTransition4086_Flags
    and #$FFF8
    beq SourceModelTransition4086_BeginSnapshot
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_BeginSnapshot:
.a16
.i16
    lda #1
    jmp SourceModelTransition4086_Pending

SourceModelTransition4086_Ack:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceModelTransition4086_Ready
    cmp #$B4F0
    beq SourceModelTransition4086_AckState
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_AckState:
.a16
.i16
    lda.l SourceModelTransition4086_State
    cmp #1
    beq SourceModelTransition4086_AckService
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_AckService:
.a16
.i16
    lda.l SourceModelTransition4086_Service
    cmp.l SourceModelTransition4086_Acknowledged
    beq SourceModelTransition4086_AckDispatch
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_AckDispatch:
.a16
.i16
    cmp #1
    bne SourceModelTransition4086_AckNotSnapshot
    jmp SourceModelTransition4086_Inherit
SourceModelTransition4086_AckNotSnapshot:
.a16
.i16
    cmp #2
    bne SourceModelTransition4086_AckNotInstall
    lda #3
    jmp SourceModelTransition4086_Pending
SourceModelTransition4086_AckNotInstall:
.a16
.i16
    cmp #3
    bne SourceModelTransition4086_AckNotColour
    jmp SourceModelTransition4086_Animation
SourceModelTransition4086_AckNotColour:
.a16
.i16
    cmp #4
    bne SourceModelTransition4086_AckNotFrame
    jsl SourceModelAnimation4086_Ack
    bcc SourceModelTransition4086_AckFrameGood
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_AckFrameGood:
.a16
.i16
    jmp SourceModelTransition4086_RestoreType
SourceModelTransition4086_AckNotFrame:
.a16
.i16
    cmp #5
    bne SourceModelTransition4086_AckNotScripts
    lda #6
    jmp SourceModelTransition4086_Pending
SourceModelTransition4086_AckNotScripts:
.a16
.i16
    cmp #6
    bne SourceModelTransition4086_AckNotColourAfter
    lda #7
    jmp SourceModelTransition4086_Pending
SourceModelTransition4086_AckNotColourAfter:
.a16
.i16
    cmp #7
    beq SourceModelTransition4086_AckDone
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_AckDone:
.a16
.i16
    jmp SourceModelTransition4086_Done

SourceModelTransition4086_Inherit:
.a16
.i16
    lda.l SourceModelTransition4086_Old
    sta.l SourceModelCachedCopy4086_Old
    sta.l SourceModelAnimationCopy4086_OldModel
    lda.l SourceModelTransition4086_New
    sta.l SourceModelCachedCopy4086_New
    sta.l SourceModelAnimationCopy4086_NewModel
    sta.l SourceModelEntityCopy4086_Model
    lda.l SourceModelTransition4086_Flags
    sta.l SourceModelCachedCopy4086_Flags
    sta.l SourceModelAnimationCopy4086_Flags
    jsl SourceModelCachedCopy4086_Apply
    bcc SourceModelTransition4086_InheritAnimations
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_InheritAnimations:
.a16
.i16
    jsl SourceModelAnimationCopy4086_Apply
    bcc SourceModelTransition4086_InstallCore
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_InstallCore:
.a16
.i16
    lda.l SourceModelTransition4086_Slot
    sta.l SourceModelEntityCopy4086_Slot
    jsl SourceModelEntityCopy4086_Apply
    bcc SourceModelTransition4086_InstallSide
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_InstallSide:
.a16
.i16
    lda.l SourceWeapon4086_Ready
    beq SourceModelTransition4086_InstallSideIdentity
    cmp #$B4F1
    beq SourceModelTransition4086_InstallWeaponMetadata
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_InstallWeaponMetadata:
.a16
.i16
    lda.l SourceModelTransition4086_Slot
    sta.l SourceWeapon4086_Slot
    lda.l SourceModelTransition4086_New
    sta.l SourceWeapon4086_Selected
    jsl SourceWeapon4086_InstallMetadata
    bcc SourceModelTransition4086_InstallSideIdentity
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_InstallSideIdentity:
.a16
.i16
    lda.l SourceModelTransition4086_Side
    tax
    lda.l SourceModelTransition4086_New
    sta.l $410000,x
    lda #2
    jmp SourceModelTransition4086_Pending

SourceModelTransition4086_Animation:
.a16
.i16
    lda.l SourceModelTransition4086_Slot
    sta.l SourceModelAnimation4086_Slot
    jsl SourceModelAnimation4086_Begin
    bcc SourceModelTransition4086_AnimationGood
    jmp SourceModelTransition4086_Bad
SourceModelTransition4086_AnimationGood:
.a16
.i16
    lda.l SourceModelAnimation4086_State
    cmp #2
    beq SourceModelTransition4086_RestoreType
    lda #4
    jmp SourceModelTransition4086_Pending
SourceModelTransition4086_RestoreType:
.a16
.i16
    lda.l SourceModelTransition4086_Core
    tax
    lda.l SourceModelTransition4086_OldTypeLo
    sta.l $400048,x
    lda.l SourceModelTransition4086_OldTypeHi
    sta.l $40004A,x
    lda #5
SourceModelTransition4086_Pending:
.a16
.i16
    sta.l SourceModelTransition4086_Service
    lda #0
    sta.l SourceModelTransition4086_Acknowledged
    lda #1
    sta.l SourceModelTransition4086_State
    bra SourceModelTransition4086_Good
SourceModelTransition4086_Done:
.a16
.i16
    lda #0
    sta.l SourceModelTransition4086_Service
    sta.l SourceModelTransition4086_Acknowledged
    lda #2
    sta.l SourceModelTransition4086_State
SourceModelTransition4086_Good:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
SourceModelTransition4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceModelTransition4086_State
    ply
    plx
    plp
    sec
    rtl
