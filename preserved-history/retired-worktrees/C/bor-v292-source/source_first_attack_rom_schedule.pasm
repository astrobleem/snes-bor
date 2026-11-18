; Only the exact ROM admission JSR may bypass the first-NPC priority.
; Every scheduler, palette, preemption and public caller retains the original
; predicate. Reuse original RTS tails so the existing short-call ABI stays.
SourceCoexist_PendingFirstTail:
.a16
.i16
    php
    rep #$30
    pha
    lda 4,s
    cmp #((SourceCoexist_AdmissionReturn-1)&$FFFF)
    bne SourceCoexist_KeepPriority
    lda.l SourceVisual_Key
    cmp #$0216
    bne SourceCoexist_KeepPriority
    lda.l SourceRom_PlayerMode
    cmp #1
    bne SourceCoexist_KeepPriority
    pla
    plp
    jsl SourceCoexist_UrgentGuard
    bcc SourceCoexist_PendingAllow
    jml SVActor_LoadEnter__yes
SourceCoexist_PendingAllow:
.a16
.i16
    jml SVActor_LoadOwnerNeedsFirstPicture__no
SourceCoexist_KeepPriority:
.a16
.i16
    pla
    plp
    jml SVActor_LoadEnter__yes

; Tail-entered after first-NPC priority or an ordinary missing-attack miss.
; Return through the original bank10 RTS. No actor, request or owner writes.
SourceCoexist_SchedulerFallback:
.a16
.i16
    php
    rep #$30
    cld
    phx
    phy
    phb
    phd
    lda.l SourceVisual_State+30
    and #255
    cmp #2
    beq SourceCoexist_SchedulerScope
    lda.l SourceVisual_State+62
    and #255
    cmp #2
    bne SourceCoexist_SchedulerNone
SourceCoexist_SchedulerScope:
.a16
.i16
    lda.l $7E46DE
    bne SourceCoexist_SchedulerNone
    jsr SourceNpc_Scope
    bcc SourceCoexist_SchedulerNone
    lda.l Game_StageIndex
    bne SourceCoexist_SchedulerNone
    jsr SourceCoexist_PhysicalJump
    bcs SourceCoexist_SchedulerNone
    jsr SourceCoexist_SchedulerP1
    bcs SourceCoexist_SchedulerSelected
    jsr SourceCoexist_SchedulerP2
    bcs SourceCoexist_SchedulerSelected
SourceCoexist_SchedulerNone:
.a16
.i16
    lda #0
SourceCoexist_SchedulerSelected:
.a16
.i16
    pld
    plb
    ply
    plx
    plp
    ora #0 ; original selector reports NZ from its returned DP/zero
    beq SourceCoexist_SchedulerReturn
    sec ; selected DP retains the public selector carry contract
SourceCoexist_SchedulerReturn:
.a16
.i16
    jml SourceVisual_FirstMissingPlayerAttack__done

SourceCoexist_UrgentGuard:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    tdc
    cmp #$0A00
    beq SourceCoexist_P1
    cmp #$0A85
    beq SourceCoexist_P2
    brl SourceCoexist_No
SourceCoexist_P1:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #0
    beq SourceCoexist_G101
    brl SourceCoexist_No
SourceCoexist_G101:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #0
    beq SourceCoexist_G102
    brl SourceCoexist_No
SourceCoexist_G102:
.a16
.i16
    ldx #0
    bra SourceCoexist_Common
SourceCoexist_P2:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceCoexist_G103
    brl SourceCoexist_No
SourceCoexist_G103:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceCoexist_G104
    brl SourceCoexist_No
SourceCoexist_G104:
.a16
.i16
    ldx #133
SourceCoexist_Common:
.a16
.i16
    lda.l SourceRom_PlayerMode
    cmp #1
    beq SourceCoexist_G105
    brl SourceCoexist_No
SourceCoexist_G105:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #534
    beq SourceCoexist_G1
    brl SourceCoexist_No
SourceCoexist_G1:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    cmp #6
    bcc SourceCoexist_G2
    brl SourceCoexist_No
SourceCoexist_G2:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    cmp #0
    beq SourceCoexist_G3
    brl SourceCoexist_No
SourceCoexist_G3:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceCoexist_G4
    brl SourceCoexist_No
SourceCoexist_G4:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceCoexist_Scope
    brl SourceCoexist_No
SourceCoexist_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceCoexist_G5
    brl SourceCoexist_No
SourceCoexist_G5:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceCoexist_G6
    brl SourceCoexist_No
SourceCoexist_G6:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceCoexist_G7
    brl SourceCoexist_No
SourceCoexist_G7:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceCoexist_G8
    brl SourceCoexist_No
SourceCoexist_G8:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceCoexist_G9
    brl SourceCoexist_No
SourceCoexist_G9:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceCoexist_G10
    brl SourceCoexist_No
SourceCoexist_G10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceCoexist_G11
    brl SourceCoexist_No
SourceCoexist_G11:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp #0
    bne SourceCoexist_Nonempty
    brl SourceCoexist_No
SourceCoexist_Nonempty:
.a16
.i16
    cmp #66
    bcc SourceCoexist_BoundedCount
    brl SourceCoexist_No
SourceCoexist_BoundedCount:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp #3
    bcc SourceCoexist_G106
    brl SourceCoexist_No
SourceCoexist_G106:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    cmp.l SourceVisual_Key
    beq SourceCoexist_HeaderKey
    brl SourceCoexist_No
SourceCoexist_HeaderKey:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceVisual_Key+2
    beq SourceCoexist_HeaderFrame
    brl SourceCoexist_No
SourceCoexist_HeaderFrame:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #255
    cmp.l SourceVisual_PieceCount
    beq SourceCoexist_Count
    brl SourceCoexist_No
SourceCoexist_Count:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    asl a
    clc
    adc #781
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceCoexist_Index
    brl SourceCoexist_No
SourceCoexist_Index:
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceCoexist_G107
    brl SourceCoexist_No
SourceCoexist_G107:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    cmp #0
    beq SourceCoexist_G108
    brl SourceCoexist_No
SourceCoexist_G108:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp #534
    beq SourceCoexist_G109
    brl SourceCoexist_No
SourceCoexist_G109:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceCoexist_Request
    brl SourceCoexist_No
SourceCoexist_Request:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceCoexist_RestoreP1
    ldx #133
    bra SourceCoexist_Restored
SourceCoexist_RestoreP1:
.a16
.i16
    ldx #0
SourceCoexist_Restored:
.a16
.i16
    cpx #0
    beq SourceCoexist_P1Picture
    brl SourceCoexist_P2Picture
SourceCoexist_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceCoexist_G12
    brl SourceCoexist_No
SourceCoexist_G12:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceCoexist_G13
    brl SourceCoexist_No
SourceCoexist_G13:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceCoexist_G14
    brl SourceCoexist_No
SourceCoexist_G14:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceCoexist_G15
    brl SourceCoexist_No
SourceCoexist_G15:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #3
    bcc SourceCoexist_G16
    brl SourceCoexist_No
SourceCoexist_G16:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceCoexist_G17
    brl SourceCoexist_No
SourceCoexist_G17:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceCoexist_G18
    brl SourceCoexist_No
SourceCoexist_G18:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceCoexist_G19
    brl SourceCoexist_No
SourceCoexist_G19:
.a16
.i16
    brl SourceCoexist_Change
SourceCoexist_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceCoexist_G20
    brl SourceCoexist_No
SourceCoexist_G20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceCoexist_G21
    brl SourceCoexist_No
SourceCoexist_G21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceCoexist_G22
    brl SourceCoexist_No
SourceCoexist_G22:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceCoexist_G23
    brl SourceCoexist_No
SourceCoexist_G23:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #3
    bcc SourceCoexist_G24
    brl SourceCoexist_No
SourceCoexist_G24:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceCoexist_G25
    brl SourceCoexist_No
SourceCoexist_G25:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceCoexist_G26
    brl SourceCoexist_No
SourceCoexist_G26:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceCoexist_G27
    brl SourceCoexist_No
SourceCoexist_G27:
.a16
.i16
SourceCoexist_Change:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceCoexist_DistinctP1
    ldx #133
    bra SourceCoexist_DistinctCurrent
SourceCoexist_DistinctP1:
.a16
.i16
    ldx #0
SourceCoexist_DistinctCurrent:
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    jsr SourceCoexist_DistinctFrame
    bcs SourceCoexist_Allowed
    brl SourceCoexist_No
SourceCoexist_Allowed:
    ply
    plx
    pla
    plp
    clc
    rtl
SourceCoexist_No:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl

SourceCoexist_SchedulerP1:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #255
    cmp #0
    bne SourceCoexist_SchedG201
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG201:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceCoexist_SchedG202
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG202:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceCoexist_SchedG203
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG203:
.a16
.i16
    lda.l $7E0A00+0+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceCoexist_SchedG204
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG204:
.a16
.i16
    lda.l $7E0A00+0+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceCoexist_SchedG205
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG205:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #255
    cmp #2
    beq SourceCoexist_SchedG206
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG206:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+0
    and #255
    cmp #3
    bcc SourceCoexist_SchedG207
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG207:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #1
    beq SourceCoexist_SchedG208
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG208:
.a16
.i16
    lda.l SourceVisual_State+28
    and #255
    cmp #0
    beq SourceCoexist_SchedG209
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG209:
.a16
.i16
    lda.l SourceVisual_State+29
    cmp #534
    beq SourceCoexist_SchedG210
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG210:
.a16
.i16
    lda.l SourceVisual_State+0
    cmp #781
    bcs SourceCoexist_SchedG211
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG211:
.a16
.i16
    lda.l SourceVisual_State+0
    cmp #793
    bcc SourceCoexist_SchedG212
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG212:
.a16
.i16
    lda.l SourceVisual_State+0
    and #1
    cmp #1
    beq SourceCoexist_SchedG213
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG213:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceCoexist_SchedG214
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG214:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceCoexist_SchedG215
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG215:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceCoexist_SchedG216
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG216:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceCoexist_SchedG217
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG217:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #3
    bcc SourceCoexist_SchedG218
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG218:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceCoexist_SchedG219
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG219:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceCoexist_SchedG220
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG220:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceCoexist_SchedG221
    brl SourceCoexist_SchedulerP1No
SourceCoexist_SchedG221:
.a16
.i16
    ldx #0
    lda.l SourceVisual_State+0
    jsr SourceCoexist_DistinctFrame
    bcc SourceCoexist_SchedulerP1No
    lda #2560
    sec
    rts
SourceCoexist_SchedulerP1No:
.a16
.i16
    clc
    rts
SourceCoexist_SchedulerP2:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #255
    cmp #0
    bne SourceCoexist_SchedG222
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG222:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceCoexist_SchedG223
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG223:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceCoexist_SchedG224
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG224:
.a16
.i16
    lda.l $7E0A00+133+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceCoexist_SchedG225
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG225:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceCoexist_SchedG226
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG226:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #255
    cmp #2
    beq SourceCoexist_SchedG227
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG227:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #255
    cmp #3
    bcc SourceCoexist_SchedG228
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG228:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceCoexist_SchedG229
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG229:
.a16
.i16
    lda.l SourceVisual_State+60
    and #255
    cmp #0
    beq SourceCoexist_SchedG230
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG230:
.a16
.i16
    lda.l SourceVisual_State+61
    cmp #534
    beq SourceCoexist_SchedG231
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG231:
.a16
.i16
    lda.l SourceVisual_State+32
    cmp #781
    bcs SourceCoexist_SchedG232
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG232:
.a16
.i16
    lda.l SourceVisual_State+32
    cmp #793
    bcc SourceCoexist_SchedG233
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG233:
.a16
.i16
    lda.l SourceVisual_State+32
    and #1
    cmp #1
    beq SourceCoexist_SchedG234
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG234:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceCoexist_SchedG235
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG235:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceCoexist_SchedG236
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG236:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceCoexist_SchedG237
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG237:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceCoexist_SchedG238
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG238:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #3
    bcc SourceCoexist_SchedG239
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG239:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceCoexist_SchedG240
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG240:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceCoexist_SchedG241
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG241:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceCoexist_SchedG242
    brl SourceCoexist_SchedulerP2No
SourceCoexist_SchedG242:
.a16
.i16
    ldx #133
    lda.l SourceVisual_State+32
    jsr SourceCoexist_DistinctFrame
    bcc SourceCoexist_SchedulerP2No
    lda #2693
    sec
    rts
SourceCoexist_SchedulerP2No:
.a16
.i16
    clc
    rts
 ; Read-only: A=validated desired catalog index, X=0/133. Refuse
; redundant work for an already displayed identical attack frame.
SourceCoexist_DistinctFrame:
.a16
.i16
    php
    rep #$30
    cld
    pha
    cpx #0
    beq SourceCoexist_DistinctReadP1
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bne SourceCoexist_DistinctYes
    lda.l SVActor_Data+2
    bra SourceCoexist_DistinctReadFrame
SourceCoexist_DistinctReadP1:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #2
    bne SourceCoexist_DistinctYes
    lda.l SourceVisual_CompletedEntry+2
SourceCoexist_DistinctReadFrame:
.a16
.i16
    and #255
    cmp #6
    bcs SourceCoexist_DistinctNo
    asl a
    clc
    adc #781
    cmp 1,s
    beq SourceCoexist_DistinctNo
SourceCoexist_DistinctYes:
.a16
.i16
    pla
    plp
    sec
    rts
SourceCoexist_DistinctNo:
.a16
.i16
    pla
    plp
    clc
    rts

; Both-player jump priority also applies to the ordinary none tail.
SourceCoexist_PhysicalJump:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #255
    beq SourceCoexist_JumpNext0
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    bne SourceCoexist_JumpNext0
    lda.l $7E0000+2560+CHAR_SELECTED
    and #255
    cmp #CHAR_SELECTED_JUMP
    beq SourceCoexist_JumpYes
SourceCoexist_JumpNext0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #255
    beq SourceCoexist_JumpNext1
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    bne SourceCoexist_JumpNext1
    lda.l $7E0000+2693+CHAR_SELECTED
    and #255
    cmp #CHAR_SELECTED_JUMP
    beq SourceCoexist_JumpYes
SourceCoexist_JumpNext1:
.a16
.i16
    clc
    rts
SourceCoexist_JumpYes:
.a16
.i16
    sec
    rts
SourceCoexist_End:
