; SOURCE_EXACT production-slot host. Opt-in build integration only.
; Six working contexts are views of the six existing production slots.
; No allocator, second entity list or independent world-coordinate owner.
; World page1700; contexts1900..1E00; clock1780; zero-velocity blocks17B0..17DF.
; Callers/linker must reserve those ranges and provide immutable SlotTable.
; All required live actors must be bound; mixed unbound interactions fault14.
; Rendering/media publication is a separate consumer, not inferred from frames.
S6Host_World = $1700
S6Host_Mode = $7E1760
S6Host_Error = $7E1764
S6Host_FrameEvents = $7E176C
S6Host_HitEvents = $7E176E
S6Host_Action = StageEnv_Actors+74
S6Host_Frame = StageEnv_Actors+84
S6Host_Role = StageEnv_Actors+86
; Private opt-in catch-up transaction: 0=production owner, 1=acquire on tick,
; 2=resident source owner. World $5E is reserved; not an actor-context offset.
; Caller must flush before any outside-world consumer or mutation.
S7Resident_Owner = $7E175E

; Bind an EXISTING production slot. Caller owns normal spawn/respawn and must
; have a compiler-approved source spawn record (in particular no random drop).
; ModelTable records32: roster,type,health,flags,roleptr low/high,count,
; idle,pain,rise,attack1,walk,range low/high,unsupported features,reserved.
; flags1=grounded single-attack opponent,2=controlled source player action.
; No model-name selection, no slot allocation. Failure never delegates.
S6Host_BindExisting:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    tdc
    sec
    sbc #$0A00
    sta.l $7E1752
    ldy #$1900
S6Host_BindExisting__slot:
    .a16
    .i16
    cmp #0
    beq S6Host_BindExisting__slot_found
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Host_BindExisting__bad_slot
    pha
    tya
    clc
    adc #$100
    tay
    pla
    cpy #$1F00
    bcc S6Host_BindExisting__slot
S6Host_BindExisting__bad_slot:
    .a16
    .i16
    lda #14
    jmp S6Host_BindExisting__error
S6Host_BindExisting__slot_found:
    .a16
    .i16
    tya
    sta.l $7E1754
    lda CHAR_ROSTER_INDEX
    and #$00FF
    sta.l $7E1758
    ldx #0
S6Host_BindExisting__model:
    .a16
    .i16
    cpx #S6Host_ModelCount*32
    bcs S6Host_BindExisting__bad_slot
    lda.l S6Host_ModelTable,x
    cmp.l $7E1758
    beq S6Host_BindExisting__model_found
    txa
    clc
    adc #32
    tax
    bra S6Host_BindExisting__model
S6Host_BindExisting__model_found:
    .a16
    .i16
    txa
    sta.l $7E1756
    lda.l S6Host_ModelTable+4,x
    cmp #256
    bcs S6Host_BindExisting__bad_slot
    lda.l S6Host_ModelTable+2,x
    cmp #1
    beq S6Host_BindExisting__player_policy
    cmp #2
    bne S6Host_BindExisting__bad_slot
    lda.l S6Host_ModelTable+6,x
    cmp #1
    bne S6Host_BindExisting__bad_slot
    lda.l S6Host_ModelTable+4,x
    sep #$20
    .a8
    sta CHAR_HP
    rep #$30
    .a16
    .i16
    bra S6Host_BindExisting__player
S6Host_BindExisting__player_policy:
    .a16
    .i16
    lda.l S6Host_ModelTable+6,x
    cmp #2
    bne S6Host_BindExisting__bad_slot
S6Host_BindExisting__player:
    .a16
    .i16
    lda.l $7E1754
    tcd
    ldx #254
    lda #0
S6Host_BindExisting__clear:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl S6Host_BindExisting__clear
    lda.l $7E1752
    sta $7A
    tax
    lda.l $7E1754
    sta.l S6Bridge_Context,x
    lda #$0101
    sta.l S6Bridge_Policy,x
    lda #$FFFF
    sta.l S6Host_Action,x
    lda #0
    sta.l S6Bridge_TargetHandle,x
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    sta.l S6Bridge_DisplayedHealth,x
    lda #1
    sta $E0
    lda #S6Host_World
    sta $36
    lda.l $7E1754
    sec
    sbc #$1900
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc #$17B0
    sta $B0
    jsl S6_StopMovement
    lda.l $7E173C
    sta $D0
    clc
    adc #1
    sta $E8
    lda.l $7E173E
    sta $D2
    adc #0
    sta $EA
    ldx $7A
    jsl S6Bridge_Import
    lda $FC
    bne S6Host_BindExisting__error
    lda.l $7E1756
    tax
    lda.l S6Host_ModelTable+8,x
    sta $C8
    lda.l S6Host_ModelTable+10,x
    sta $CA
    lda.l S6Host_ModelTable+12,x
    sta $CC
    lda.l S6Host_ModelTable+14,x
    sta $38
    lda.l S6Host_ModelTable+16,x
    sta $3A
    lda.l S6Host_ModelTable+18,x
    sta $3C
    lda.l S6Host_ModelTable+20,x
    sta $A0
    lda.l S6Host_ModelTable+22,x
    sta $A6
    lda.l S6Host_ModelTable+24,x
    sta $A2
    lda.l S6Host_ModelTable+26,x
    sta $A4
    lda.l S6Host_ModelTable+28,x
    sta $A8
    lda.l S6Host_ModelTable+2,x
    sta $F2
    cmp #1
    beq S6Host_BindExisting__player_driver
    lda #6
    bra S6Host_BindExisting__driver
S6Host_BindExisting__player_driver:
    .a16
    .i16
    lda #8
S6Host_BindExisting__driver:
    .a16
    .i16
    sta $E6
    lda #$FFFF
    sta $E4
    sta $F4
    lda $38
    jsl S6_SetRole
    lda $FC
    beq S6Host_BindExisting__return
S6Host_BindExisting__error:
    .a16
    .i16
    sta.l S6Host_Error
S6Host_BindExisting__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; Public tick. D/DBR/P/X/Y preserved. World3C is supplied source time.
; Default: each tick imports production fields then exports the transaction.
; Opt-in resident window: acquire once; shared contexts own mutable state until
; flush. No outside simulation consumer may execute while that owner is held.
S6Host_Tick:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda #S6Host_World
    tcd
    lda $60
    cmp #1
    beq S6Host_Tick__enabled
    jmp S6Host_Tick__return
S6Host_Tick__enabled:
    .a16
    .i16
    lda $64
    beq S6Host_Tick__ready
    jmp S6Host_Tick__return
S6Host_Tick__ready:
    .a16
    .i16
    lda $5E
    cmp #2
    bne S6Host_Tick__acquire
    jmp S6Host_Tick__resident_execute
S6Host_Tick__acquire:
    .a16
    .i16
    stz $44
    stz $46
    stz $52                  ; production row byte offset
    lda #$1900
    sta $54                  ; paired scheduler working page
S6Host_Tick__import:
    .a16
    .i16
    ldx $52
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Host_Tick__bound
    cpx #CHAR_ZP_LEN
    bne S6Host_Tick__unbound_health
    lda.l G13_TwoPlayerEnabled
    and #255
    beq S6Host_Tick__empty
S6Host_Tick__unbound_health:
    .a16
    .i16
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    beq S6Host_Tick__empty
    jmp S6Host_Tick__unbound
S6Host_Tick__empty:
    .a16
    .i16
    ldx $54
    lda #1
    sta.l $7E00E0,x
    lda #0
    sta.l $7E00F6,x
    bra S6Host_Tick__next_import
S6Host_Tick__bound:
    .a16
    .i16
    phd
    lda $54
    tcd
    jsl S6Bridge_Import
    lda $FC
    pld
    cmp #0
    beq S6Host_Tick__imported
    jmp S6Host_Tick__fault
S6Host_Tick__imported:
    .a16
    .i16
    ldx $54
    lda.l $7E00F6,x
    beq S6Host_Tick__next_import
    lda.l $7E00F2,x
    cmp #1
    bne S6Host_Tick__next_import
    lda $52
    beq S6Host_Tick__player0
    cmp #CHAR_ZP_LEN
    bne S6Host_Tick__unbound
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq S6Host_Tick__unbound
    lda $54
    sta $46
    bra S6Host_Tick__next_import
S6Host_Tick__player0:
    .a16
    .i16
    lda $54
    sta $44
S6Host_Tick__next_import:
    .a16
    .i16
    jsl S6Host_NextRow
    bcc S6Host_Tick__import
    lda $5E
    beq S6Host_Tick__execute
    lda #2
    sta $5E
S6Host_Tick__execute:
    .a16
    .i16
    jsl S6_UpdateWorld
    bra S6Host_Tick__world_done
S6Host_Tick__resident_execute:
    .a16
    .i16
    ; Source slot layout/policies were validated by this batch's first pass.
    ; No external bind or layout mutation is allowed while contexts own state.
    ; Mutable same-pass checks remain in the generated traversal.
    jsl S6_UpdateWorldBound
S6Host_Tick__world_done:
    .a16
    .i16
    lda $3A
    bne S6Host_Tick__fault
S6Host_Tick__export_all:
    .a16
    .i16
    stz $52
    lda #$1900
    sta $54
S6Host_Tick__export:
    .a16
    .i16
    ldx $52
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    bne S6Host_Tick__next_export
    phd
    lda $54
    tcd
    ; Native autokill/removal must perform the source cleanup, not just hide.
    lda $F6
    beq S6Host_Tick__remove_actor
    lda.l S7Resident_Owner
    cmp #2
    bne S6Host_Tick__commit_actor
    bra S6Host_Tick__actor_committed
S6Host_Tick__remove_actor:
    .a16
    .i16
    jsl S6_KillUnlinked
S6Host_Tick__commit_actor:
    .a16
    .i16
    jsl S6Bridge_Export
    lda $FC
    bne S6Host_Tick__actor_committed
    lda $F6
    bne S6Host_Tick__actor_committed
    jsl S6Host_ClearRemovedReferences
S6Host_Tick__actor_committed:
    .a16
    .i16
    lda $FC
    pld
    cmp #0
    bne S6Host_Tick__fault
S6Host_Tick__next_export:
    .a16
    .i16
    jsl S6Host_NextRow
    bcc S6Host_Tick__export
    bra S6Host_Tick__return
S6Host_Tick__unbound:
    .a16
    .i16
    lda #14
S6Host_Tick__fault:
    .a16
    .i16
    sta $64
S6Host_Tick__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

S6Host_NextRow:
    .a16
    .i16
    lda $54
    clc
    adc #$100
    sta $54
    lda $52
    clc
    adc #CHAR_ZP_LEN
    sta $52
    cmp #CHAR_ZP_LEN*6
    rtl

; Release resident ownership, publishing all scalar fields before returning.
; No source tick, no re-import. Preserve the host tick's caller ABI exactly.
S7Resident_Flush:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda #S6Host_World
    tcd
    lda $5E
    stz $5E
    cmp #2
    beq S7Resident_Flush__publish
    jmp S6Host_Tick__return
S7Resident_Flush__publish:
    .a16
    .i16
    jmp S6Host_Tick__export_all

; Remove an actual production handle (A=entity DP). Source kill owns this
; operation; it does not free/move the persistent OOP character allocation.
; The existing player OUT bit mirrors absence, not a fabricated death/credit.
S6Host_RemoveHandle:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sec
    sbc #$0A00
    tax
    ldy #6
S6Host_RemoveHandle__validate:
    .a16
    .i16
    cmp #0
    beq S6Host_RemoveHandle__valid
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Host_RemoveHandle__bad
    dey
    bne S6Host_RemoveHandle__validate
    bra S6Host_RemoveHandle__bad
S6Host_RemoveHandle__valid:
    .a16
    .i16
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l S6Bridge_Context,x
    beq S6Host_RemoveHandle__bad
    tcd
    lda.l S7Resident_Owner
    cmp #2
    beq S6Host_RemoveHandle__resident
    jsl S6Bridge_Import
    lda $FC
    bne S6Host_RemoveHandle__error
S6Host_RemoveHandle__resident:
    .a16
    .i16
    jsl S6_KillUnlinked
    jsl S6Bridge_Export
    lda $FC
    bne S6Host_RemoveHandle__error
    jsl S6Host_ClearRemovedReferences
    lda $F2
    cmp #1
    bne S6Host_RemoveHandle__return
    ldx $7A
    beq S6Host_RemoveHandle__p1
    cpx #CHAR_ZP_LEN
    bne S6Host_RemoveHandle__bad
    sep #$20
    .a8
    lda #1
    sta.l G13_P2Out
    bra S6Host_RemoveHandle__return
S6Host_RemoveHandle__p1:
    .a16
    .i16
    sep #$20
    .a8
    lda #1
    sta.l G13_P1Out
    bra S6Host_RemoveHandle__return
S6Host_RemoveHandle__bad:
    rep #$30
    .a16
    .i16
    lda #14
S6Host_RemoveHandle__error:
    .a16
    .i16
    sta.l S6Host_Error
S6Host_RemoveHandle__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; Source host callbacks. No accepted-compat execution fallback.
S6_Think:
    rep #$30
    .a16
    .i16
    lda $E6
    cmp #2
    beq S6Host_Recovery
    cmp #3
    beq S6Host_Recovery
    cmp #4
    beq S6Host_Lifecycle
    cmp #5
    beq S6Host_Lifecycle
    cmp #6
    beq S6Host_Lifecycle
    cmp #7
    bne S6_Think__not_pain
    jml S6Host_PlayerPain
S6_Think__not_pain:
    .a16
    .i16
    cmp #8
    beq S6Host_PlayerAction
    cmp #9
    bne S6_Think__enemy
    jml S6Host_PlayerAttack
S6_Think__enemy:
    .a16
    .i16
    jsl S6_EnemyDecision
    jsl S6Host_PublishTarget
    rtl
S6Host_Recovery:
    .a16
    .i16
    jml S6_RecoveryThink
S6Host_Lifecycle:
    .a16
    .i16
    jml S6_GroundLifecycle

; Target publication is a real production-slot handle, not a context address.
; Selection itself remains the already-proven S6_SelectTarget implementation.
S6Host_PublishTarget:
    .a16
    .i16
    lda $34
    beq S6Host_PublishTarget__none
    tax
    lda.l $7E00F6,x
    beq S6Host_PublishTarget__none
    lda.l $7E007A,x
    clc
    adc #$0A00
    bra S6Host_PublishTarget__store
S6Host_PublishTarget__none:
    .a16
    .i16
    lda #0
S6Host_PublishTarget__store:
    .a16
    .i16
    ldx $7A
    sta.l S6Bridge_TargetHandle,x
    rtl

S6Host_ClearRemovedReferences:
    .a16
    .i16
    lda $7A
    clc
    adc #$0A00
    sta $AA
    ldx #0
S6Host_ClearRemovedReferences__slot:
    .a16
    .i16
    lda.l S6Bridge_TargetHandle,x
    cmp $AA
    bne S6Host_ClearRemovedReferences__next
    lda #0
    sta.l S6Bridge_TargetHandle,x
S6Host_ClearRemovedReferences__next:
    .a16
    .i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc S6Host_ClearRemovedReferences__slot
    rtl

; Explicit source action fixture adapter, not a complete player controller.
; ActionFFFF means no request. Only metadata-selected attack1 is admitted.
S6Host_PlayerAction:
    .a16
    .i16
    ldx $7A
    lda.l S6Host_Action,x
    cmp #$FFFF
    beq S6Host_PlayerAction__done
    cmp $A0
    bne S6Host_PlayerAction__unsupported
    lda #$FFFF
    sta.l S6Host_Action,x
    stz $FA
    lda $A0
    jsl S6_SetRole
    lda $08
    ora #1
    sta $08
    lda #9
    sta $E6
S6Host_PlayerAction__done:
    .a16
    .i16
    rtl
S6Host_PlayerAction__unsupported:
    .a16
    .i16
    lda #15
    sta $FC
    rtl
S6Host_PlayerAttack:
    .a16
    .i16
    lda $10
    bne S6Host_PlayerAction__done
    lda $08
    and #$FFFE
    sta $08
    bra S6Host_PlayerIdle
S6Host_PlayerPain:
    .a16
    .i16
    ; No special-input/grab fallback. Controlled fixture supplies no input.
    lda $C4
    bne S6Host_PlayerAction__unsupported
    lda $10
    bne S6Host_PlayerAction__done
S6Host_PlayerIdle:
    .a16
    .i16
    stz $FA
    lda $38
    jsl S6_SetRole
    lda #8
    sta $E6
    rtl

S6_FrameChanged:
    rep #$30
    .a16
    .i16
    ldx $7A
    lda $06
    sta.l S6Host_Frame,x
    lda $E4
    sta.l S6Host_Role,x
    lda.l S6Host_FrameEvents
    inc a
    sta.l S6Host_FrameEvents
    rtl

S6_WorldHealth:
    rep #$30
    .a16
    .i16
    jml S6_DisplayHealth

S6_WorldLost:
    rep #$30
    .a16
    .i16
    lda.l Screen_PosX
    jsl S6Bridge_Unproject
    bcs S6Host_EnvironmentBlocked
    sec
    sbc #1000
    sta $AA
    lda $14
    sec
    sbc $AA
    bmi S6Host_LostRemove
    lda $18
    eor #$8000
    cmp #$7E0C                ; source a < PIT_DEPTH*2 (-500)
    bcc S6Host_LostRemove
    rtl
S6Host_LostRemove:
    .a16
    .i16
    jml S6_KillUnlinked

S6_WorldGravity:
    rep #$30
    .a16
    .i16
    ; Bounded ground-only certificate. Compiler also excludes authored
    ; endholes/water/rocking before linking this host to a selected stage.
    lda $C2
    bne S6Host_EnvironmentBlocked
    lda.l Spawn_HoleCount
    and #$00FF
    bne S6Host_EnvironmentBlocked
    rtl
S6Host_EnvironmentBlocked:
    .a16
    .i16
    lda #10
    sta $FC
    rtl

S6_WorldAttack:
    rep #$30
    .a16
    .i16
    ; BOR.C gates the entire target scan on this source frame's attack.
    ; An inactive frame resets attack_id once, even with no live targets.
    ; Do not repeatedly decode the identical inactive frame for each target.
    jsl S6_CheckPolicy
    bcs S6_WorldAttack__done
    jsl S5_ActivateAttack
    lda $0A
    bne S6_WorldAttack__active
    stz $DC
    stz $DE
    rtl
S6_WorldAttack__active:
    .a16
    .i16
    ; Scan stable source slot order, not just the selected AI target.
    stz $AC
S6_WorldAttack__slot:
    .a16
    .i16
    lda $AC
    asl a
    tax
    lda.l S6Host_SlotTable,x
    sta $34
    tax
    lda.l $7E00F6,x
    beq S6_WorldAttack__next
    jsl S6_TryHitOne
    lda $FC
    bne S6_WorldAttack__done
S6_WorldAttack__next:
    .a16
    .i16
    inc $AC
    lda $AC
    cmp #6
    bcc S6_WorldAttack__slot
S6_WorldAttack__done:
    .a16
    .i16
    rtl

S6_HitEffects:
    rep #$30
    .a16
    .i16
    ; This publication is NOT a complete flash/audio/combo/effects binding.
    ; Keep the full effect category un-certified until its consumers exist.
    lda.l S6Host_HitEvents
    inc a
    sta.l S6Host_HitEvents
    rtl
