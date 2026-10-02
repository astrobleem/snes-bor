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
; Normal's stage-boundary command, projected into source coordinates once per
; physical stage. This follows the six-byte native-target mask at $412D00.
S6Host_PlayerWorldMaxX = $412D06
; Persistent production input record for the source tick currently executing.
; Relay publishes these words from the sequenced 8-byte-per-tick input ring.
S6Host_InputP1Press = $412020
S6Host_InputP1Trigger = $412022
S6Host_InputP2Press = $412024
S6Host_InputP2Trigger = $412026
; Private opt-in catch-up transaction: 0=production owner, 1=acquire on tick,
; 2=resident source owner. World $5E is reserved; not an actor-context offset.
; Caller must flush before any outside-world consumer or mutation.
S7Resident_Owner = $7E175E

; Bind an EXISTING production slot. Caller owns normal spawn/respawn and must
; have a compiler-approved source spawn record (in particular no random drop).
; ModelTable records32: roster,type,health,flags,roleptr low/high,count,
; idle,pain,rise,attack1,walk,range low/high,unsupported features,speed20.
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
    and #$FFFB
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
    and #$FFFB
    cmp #2
    beq S6Host_BindExisting__player_policy_valid
    jmp S6Host_BindExisting__bad_slot
S6Host_BindExisting__player_policy_valid:
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
    ; Model flag bit 2 selects the Normal compiler's rounded 4/5 XY bridge.
    ; Existing measured/reference model records retain exact policy 1.
    lda.l $7E1756
    tax
    lda.l S6Host_ModelTable+6,x
    and #4
    beq S6Host_BindExisting__exact_bridge
    lda #$0102
    bra S6Host_BindExisting__bridge_policy
S6Host_BindExisting__exact_bridge:
    lda #$0101
S6Host_BindExisting__bridge_policy:
    ldx $7A
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
    ; Normal's sequenced worker ring owns a zero-based 32-bit tick epoch.
    ; S6Host_Mode changes from the bind barrier (3) to active owner (1), so
    ; it cannot select the clock domain. Use the ring producer's committed
    ; timestamp for every Normal bind; the legacy fallback uses caller time.
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Host_BindExisting__clock_legacy
    lda.l S6Game_TickCommit
    sta $D0
    lda.l S6Game_TickCommit+2
    sta $D2
    bra S6Host_BindExisting__clock_ready
S6Host_BindExisting__clock_legacy:
    .a16
    .i16
    lda.l $7E173C
    sta $D0
    lda.l $7E173E
    sta $D2
S6Host_BindExisting__clock_ready:
    .a16
    .i16
    ldx $7A
    jsl S6Bridge_Import
    lda $FC
    beq S6Host_BindExisting__bridge_ok
    jmp S6Host_BindExisting__error
S6Host_BindExisting__bridge_ok:
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
    lda.l S6Host_ModelTable+30,x
    sta $C6
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
    bne S6Host_BindExisting__error
    ; S5_LoadFrame uses E8/EA as scratch while S6_SetRole enters the initial
    ; authored frame. Set the first think deadline after that transaction so
    ; the scheduler fields cannot be clobbered by frame preparation.
    lda $D0
    clc
    adc #1
    sta $E8
    lda $D2
    adc #0
    sta $EA
S6Host_BindExisting__scheduled:
    bra S6Host_BindExisting__return
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
    cmp #2
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
    beq S6Host_Tick__player1_slot
    jmp S6Host_Tick__unbound
S6Host_Tick__player1_slot:
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    bne S6Host_Tick__player1_enabled
    jmp S6Host_Tick__unbound
S6Host_Tick__player1_enabled:
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
    ; In the persistent SA-1 runtime, S6Host_Tick__resident_execute has
    ; already queued the tick and deliberately did not mutate the S-CPU
    ; world error/context mirrors.  Return to the source clock here: the
    ; coherent snapshot is exported once at the presentation boundary by
    ; S7Resident_Flush.  Running the synchronous error/export tail against
    ; stale S-CPU contexts both consumed per-tick CPU and could mistake the
    ; untouched $3A scratch for a world callback failure.
    lda $5E
    cmp #2
    beq S6Host_Tick__return
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
    beq S6Host_Tick__export_bound
    cmp #2
    bne S6Host_Tick__next_export
S6Host_Tick__export_bound:
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
; Player life stock and OUT remain owned by G13_SourcePlayerDeathP1/P2 after
; this bridge publishes HP=0. Worker absence is not equivalent to exhausted
; stock and must not short-circuit BOR's native fall/decrement/respawn path.
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
    txa
    sta.l SourceVisual_RetireEntityOffset
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
    ; $FC is actor scratch as well as this transaction's status word. The
    ; resident worker intentionally does not import/export the whole context
    ; for unlink, so initialize the return status before either path.
    stz $FC
    lda.l S7Resident_Owner
    cmp #2
    beq S6Host_RemoveHandle__resident
    jsl S6Bridge_Import
    lda $FC
    bne S6Host_RemoveHandle__error
    bra S6Host_RemoveHandle__temporary
S6Host_RemoveHandle__resident:
    .a16
    .i16
    ; The ordered unlink came from SA-1 after it already ran
    ; S6_KillUnlinked against canonical state. The S-CPU actor page is only
    ; a sampled mirror and can have an older environment base; replaying
    ; kill/export here duplicates lifecycle and can reject a valid unlink on
    ; that stale projection. Publish only the native-slot consequences.
    ldx $7A
    lda #0
    sta.l S6Bridge_DisplayedHealth,x
    sep #$20
    .a8
    sta.l S6Bridge_Exists,x
    sta.l $7E0A00+CHAR_HP,x
    rep #$30
    .a16
    .i16
    jsl S6Host_ClearRemovedReferences
    lda.l SourceVisual_RetireEntityOffset
    tax
    jsl SourceVisual_QueueRetireEntityOffset
    bra S6Host_RemoveHandle__return
S6Host_RemoveHandle__temporary:
    .a16
    .i16
    jsl S6_KillUnlinked
    jsl S6Bridge_Export
    lda $FC
    bne S6Host_RemoveHandle__error
    jsl S6Host_ClearRemovedReferences
    lda.l SourceVisual_RetireEntityOffset
    tax
    jsl SourceVisual_QueueRetireEntityOffset
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

; Normal's persistent player controller consumes only the current worker-tick
; input words. Held directions advance the canonical source position at the
; model's authored speed20, using the same twentieth-pixel accumulator as the
; source enemy driver. Attack remains an edge from that same tick record.
S6Host_PlayerAction:
    sep #$20
    .a8
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    bne S6Host_PlayerAction__grounded
    ; BOR's Jump_PlayerTick remains the sole owner of the existing 60-Hz
    ; airborne X/Z transition. Do not apply the persistent 200-Hz grounded
    ; controller while that native substate is active.
    jml S6Host_PlayerAction__done
S6Host_PlayerAction__grounded:
    rep #$30
    .a16
    .i16
    jsl S6Host_PlayerMove
    jsl S6Host_PlayerInputTrigger
    and #$4000
    bne S6Host_PlayerAction__attack
S6Host_PlayerAction__ordinary:
    .a16
    .i16
    ldx $7A
    lda.l S6Host_Action,x
    cmp #$FFFF
    beq S6Host_PlayerAction__locomotion
    cmp $A0
    beq S6Host_PlayerAction__attack
    jml S6Host_PlayerAction__unsupported
S6Host_PlayerAction__attack:
    ldx $7A
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
    rtl
S6Host_PlayerAction__locomotion:
    jsl S6Host_PlayerInputHeld
    and #$0F00
    beq S6Host_PlayerAction__idle
    lda $A6
    bra S6Host_PlayerAction__set_locomotion
S6Host_PlayerAction__idle:
    lda $38
S6Host_PlayerAction__set_locomotion:
    stz $FA
    jsl S6_SetRole
    lda #8
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
    jsl S6Host_PlayerMove
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

; Return the per-tick held or edge word for the currently bound player.
; Production P1/P2 occupy physical context rows 0 and CHAR_ZP_LEN.
S6Host_PlayerInputHeld:
    .a16
    .i16
    lda $7A
    cmp #CHAR_ZP_LEN
    beq S6Host_PlayerInputHeld__p2
    lda.l S6Host_InputP1Press
    rtl
S6Host_PlayerInputHeld__p2:
    lda.l S6Host_InputP2Press
    rtl

S6Host_PlayerInputTrigger:
    .a16
    .i16
    lda $7A
    cmp #CHAR_ZP_LEN
    beq S6Host_PlayerInputTrigger__p2
    lda.l S6Host_InputP1Trigger
    rtl
S6Host_PlayerInputTrigger__p2:
    lda.l S6Host_InputP2Trigger
    rtl

; Move the player in SOURCE_EXACT coordinates. The PAK-derived model speed is
; stored in twentieths; S6_EnemyApplyAxis retains signed twentieth-pixel
; remainders in this actor context, so 0.9/1.2 authored speeds do not drift.
; Left wins over right and up wins over down, matching Character_PlayFrame.
; B doubles speed. Direction/role and coordinates all belong to this one SA-1
; pass; the S-CPU consumes only the next coherent snapshot.
S6Host_PlayerMove:
    .a16
    .i16
    jsl S6Host_PlayerInputHeld
    sta $B4
    and #$0300
    beq S6Host_PlayerMove__x_stop
    and #$0200
    beq S6Host_PlayerMove__x_right
    lda $C6
    eor #$FFFF
    inc a
    bra S6Host_PlayerMove__x_speed
S6Host_PlayerMove__x_right:
    lda $C6
S6Host_PlayerMove__x_speed:
    sta $B6
    lda $B4
    and #$8000
    beq S6Host_PlayerMove__x_load
    lda $B6
    asl a
    sta $B6
S6Host_PlayerMove__x_load:
    lda $B6
    bra S6Host_PlayerMove__x_store
S6Host_PlayerMove__x_stop:
    lda #0
    sta $B6
S6Host_PlayerMove__x_store:
    ldx $B0
    sta.l $7E0000,x
    stz $90
    stz $92
    stz $94
    jsl S6_EnemyApplyAxis
    ; The S-CPU's Character_PlayFrame clamps player X to WorldMaxX after a
    ; horizontal step. Persistent ownership must preserve that stage-local
    ; rule too; otherwise an actor carried from a wider previous stage can
    ; walk past the new stage and eventually exceed the snapshot bridge's
    ; admitted source-coordinate domain. Left wins over right, and only the
    ; selected direction's native clamp is applied.
    lda.l S6Host_Mode
    cmp #1
    bne S6Host_PlayerMove__x_bound_done
    lda.l S7Resident_Owner
    cmp #2
    bne S6Host_PlayerMove__x_bound_done
    lda $B4
    and #$0300
    beq S6Host_PlayerMove__x_bound_done
    and #$0200
    beq S6Host_PlayerMove__x_bound_right
    lda $14
    bpl S6Host_PlayerMove__x_bound_done
    stz $14
    bra S6Host_PlayerMove__x_bound_done
S6Host_PlayerMove__x_bound_right:
    lda $14
    cmp.l S6Host_PlayerWorldMaxX
    bcc S6Host_PlayerMove__x_bound_done
    beq S6Host_PlayerMove__x_bound_done
    lda.l S6Host_PlayerWorldMaxX
    sta $14
S6Host_PlayerMove__x_bound_done:

    lda $B4
    and #$0C00
    beq S6Host_PlayerMove__y_stop
    and #$0800
    beq S6Host_PlayerMove__y_down
    lda $C6
    eor #$FFFF
    inc a
    bra S6Host_PlayerMove__y_speed
S6Host_PlayerMove__y_down:
    lda $C6
S6Host_PlayerMove__y_speed:
    sta $B6
    lda $B4
    and #$8000
    beq S6Host_PlayerMove__y_load
    lda $B6
    asl a
    sta $B6
S6Host_PlayerMove__y_load:
    lda $B6
    bra S6Host_PlayerMove__y_store
S6Host_PlayerMove__y_stop:
    lda #0
    sta $B6
S6Host_PlayerMove__y_store:
    sta $B6
    ldx $B0
    txa
    clc
    adc #4
    tax
    lda $B6
    sta.l $7E0000,x
    lda #2
    sta $90
    sta $92
    lda #4
    sta $94
    jsl S6_EnemyApplyAxis

    lda $B4
    and #$0300
    beq S6Host_PlayerMove__done
    and #$0200
    bne S6Host_PlayerMove__left
    lda #1
    sta $1A
    rtl
S6Host_PlayerMove__left:
    lda #0
    sta $1A
S6Host_PlayerMove__done:
    rtl

S6_FrameChanged:
    rep #$30
    .a16
    .i16
    ldx $7A
    lda $06
    sta.l S6Host_Frame,x
    lda $E4
    cmp $38
    beq S6_FrameChanged__idle
    cmp $A6
    beq S6_FrameChanged__walk
    cmp $A0
    beq S6_FrameChanged__attack
    cmp $3A
    beq S6_FrameChanged__pain
    cmp $3C
    beq S6_FrameChanged__rise
    lda $A8
    and #$00FF
    cmp $E4
    beq S6_FrameChanged__jump
    lda #$00FF
    bra S6_FrameChanged__store_role
S6_FrameChanged__idle:
    lda #0
    bra S6_FrameChanged__store_role
S6_FrameChanged__walk:
    lda #1
    bra S6_FrameChanged__store_role
S6_FrameChanged__attack:
    lda #2
    bra S6_FrameChanged__store_role
S6_FrameChanged__rise:
    lda #5
    bra S6_FrameChanged__store_role
S6_FrameChanged__jump:
    lda #7
    bra S6_FrameChanged__store_role
S6_FrameChanged__pain:
    lda #8
S6_FrameChanged__store_role:
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
    ; The display camera need not land on the exact 4-pixel source lattice.
    ; Use each bound actor's compiler-selected inverse policy, just like
    ; bridge import; Normal's 5/4 projection is intentionally rounded.
    jsl S6Bridge_UnprojectPolicy
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
S6Host_EnvironmentBlocked:
    ; Projection failure from S6_WorldLost is still fail-closed. Gravity no
    ; longer branches here because its former $C2 test read actor scratch.
    .a16
    .i16
    lda #10
    sta $FC
    rtl

S6_WorldGravity:
    rep #$30
    .a16
    .i16
    ; This pass has no source actor-local gravity state to apply. $C2 is
    ; scratch beyond CharacterEntity's 133-byte contract (e.g. DriftTick's
    ; signed-bound temporary), not a gravity/hole certificate; treating a
    ; stale nonzero value as fatal faulted ordinary Normal actors. Authored
    ; stage hazards are serviced by StageBoundsHost_Physics/Enter on the
    ; gameplay path before the resident-world tick.
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
