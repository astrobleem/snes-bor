; Opt-in Normal-campaign adapter for the accepted persistent SA-1 owner.
; Combat actors bind to the source-world contexts; props, pickups, steamers
; and the special Biker driver remain on their existing typed S-CPU services.
; Spawn/respawn is a true dependency boundary: drain queued ticks, bind one
; production slot, then publish only that context and its 133-byte metadata row.
S6Normal_LastStage = $7E1778
; Spawn_Play can reassign an allocated actor row without invoking the
; behavior binder again. Track the roster represented by each live source
; context so the render-boundary ownership sweep can safely rebind it.
; $17C0..$17C5 and $17C6..$17C9 are unused; bridge scratch begins at $17E0.
S6Normal_BoundRoster = $7E17C0
S6Normal_BindLiveActors__slot_index = $7E17C6
S6Normal_BindLiveActors__worker_context = $7E17C8
; Six-byte shared target-type directory for the persistent worker's ordered
; world-attack pass. Only native breakable props are marked; HP,
; invulnerability, rewards and lifecycle remain S-CPU-owned typed state.
S6Normal_NativePropMask = $412D00
S6Normal_NativePropRecordOffset = $7E1766
S6Normal_NativePropAttackX = $7E1768
S6Normal_NativePropTargetYSlot = $7E176A

S6Normal_BeginResolve:
    jsl S6Normal_Init
    jsl Game_Campaign_ResolveNext
    rtl

S6Normal_Init:
    php
    rep #$30
    .a16
    .i16
    pha
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
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_Init__enabled
    lda #0
    sta.l S6Host_Mode
    sta.l $7E175C
    sta.l $7E175E
    sta.l $7E175A
    bra S6Normal_Init__return
S6Normal_Init__enabled:
    lda #0
    sta.l $7E175C
    sta.l $7E175E
    sta.l $7E175A
    sta.l S6Host_Error
    sta.l S6Game_Command
    sta.l S6Game_TickCommit
    sta.l S6Game_TickCommit+2
    ; Stage/bootstrap WRAM is not a zeroed worker-world image. Initialize the
    ; four source relationship pointers before the first persistent tick;
    ; stale values here are consumed by S6_SelectTarget as actor DPs.
    sta.l $7E1744
    sta.l $7E1746
    sta.l $7E174E
    sta.l $7E1750
    sta.l $411744
    sta.l $411746
    sta.l $41174E
    sta.l $411750
    ldx #0
S6Normal_Init__bound_roster_clear:
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    inx
    cpx #6
    bcc S6Normal_Init__bound_roster_clear
    ldx #0
S6Normal_Init__native_prop_clear:
    sta.l S6Normal_NativePropMask,x
    inx
    cpx #6
    bcc S6Normal_Init__native_prop_clear
    lda #$FFFF
    sta.l S6Normal_LastStage
    lda.l StageTimer_FieldCounter
    sta.l S6Game_LastField
    ; Clear the six bridge rows only. Spawn_Play remains the sole owner of
    ; actor allocation, authored instance HP, aliases and slot reuse.
    ldx #0
    lda #0
S6Normal_Init__bridge:
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_Exists,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcs S6Normal_Init__bridge_done
    lda #0
    bra S6Normal_Init__bridge
S6Normal_Init__bridge_done:
    ; The persistent worker's immutable slot table spans all six reserved
    ; source-context pages. Production OOP slots are not zero-filled, while
    ; world preflight validates E0 policy on every table pointer before it
    ; examines F6 existence. Initialize only these reserved source-world
    ; pages as valid empty contexts; Spawn_Play still owns every production
    ; allocation and S6Host_BindExisting fills each admitted actor later.
    ldx #0
S6Normal_Init__context_clear:
    lda #0
    sta.l $7E1900,x
    inx
    inx
    cpx #$0600
    bcc S6Normal_Init__context_clear
    ldx #0
S6Normal_Init__context_policy:
    lda #1
    sta.l $7E19E0,x
    txa
    clc
    adc #$0100
    tax
    cpx #$0600
    bcc S6Normal_Init__context_policy
    ; Fixed six production-slot table, same page-aligned resident ABI as the
    ; measured worker. No synthetic stage or duplicate actor list is created.
    lda #$02D2
    sta.l S6Host_World
    lda #$4996
    sta.l S6Host_World+2
    lda #S6Host_SlotTable&$FFFF
    sta.l S6Host_World+48
    lda #S6Host_SlotTable>>16
    sta.l S6Host_World+50
    lda #6
    sta.l S6Host_World+52
    lda #1
    sta.l S6Host_World+64
    ; Reset the rational 200-Hz source clock at a new Normal run boundary.
    lda #$1780
    tcd
    ldx #0
    lda #0
S6Normal_Init__clock_clear:
    sta $00,x
    inx
    inx
    cpx #32
    bcc S6Normal_Init__clock_clear
    lda #$B796
    sta $08
    lda #$0147
    sta $0A
    lda #$1700
    tcd
    lda #2
    sta.l S6Host_Mode
S6Normal_Init__return:
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; StageEnv_ResetActors runs at the authored physical-stage boundary. Flush all
; ordered events while their old bridge identities still exist, park the
; persistent owner, then retire the six fixed source contexts before the
; production rows are cleared/reused. The world/RNG epoch remains resident;
; only actors and their stage-local relationship/admission rows reset.
S6Normal_ResetStageWorld:
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
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_ResetStageWorld__campaign
    jml S6Normal_ResetStageWorld__return
S6Normal_ResetStageWorld__campaign:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_ResetStageWorld__mode
    cmp #3
    beq S6Normal_ResetStageWorld__mode
    jml S6Normal_ResetStageWorld__return
S6Normal_ResetStageWorld__mode:
    lda.l $7E175E
    cmp #2
    beq S6Normal_ResetStageWorld__owned
    jml S6Normal_ResetStageWorld__return
S6Normal_ResetStageWorld__owned:
    ; Relay_Flush drains every event through the old S-CPU mapping before the
    ; following mutation fence makes the bulk stage reset atomic to SA-1.
    jsl S7Resident_Flush
    jsl S6Normal_MutationFenceBegin
    ldx #0
    lda #0
S6Normal_ResetStageWorld__native_prop_clear:
    sta.l S6Normal_NativePropMask,x
    inx
    cpx #6
    bcc S6Normal_ResetStageWorld__native_prop_clear
    ldx #0
S6Normal_ResetStageWorld__bound_roster_clear:
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    inx
    cpx #6
    bcc S6Normal_ResetStageWorld__bound_roster_clear
    lda #0
    sta.l $7E1744
    sta.l $7E1746
    sta.l $7E174E
    sta.l $7E1750
    sta.l $411744
    sta.l $411746
    sta.l $41174E
    sta.l $411750
    lda #0
    sta.l $7E1752
    lda #$1900
    sta.l $7E1754
S6Normal_ResetStageWorld__slot:
    ; Source lifecycle references are stage-local. Clearing F6 prevents a
    ; removed stage actor from generating a later unresolvable unlink event.
    lda.l $7E1754
    tcd
    stz $44
    stz $46
    stz $4E
    stz $50
    stz $F6
    lda.l $7E1754
    sec
    sbc #$1900
    tax
    ldy #0
S6Normal_ResetStageWorld__context:
    lda.l $7E1900,x
    sta.l $411900,x
    inx
    inx
    iny
    iny
    cpy #$0100
    bcc S6Normal_ResetStageWorld__context
    ; Worker metadata is six packed 133-byte sidecar rows, not six 36-byte
    ; actor-DP strides. Clear the complete shared mirror before the S-CPU
    ; StageEnv_ResetActors loop retires the corresponding host rows.
    ldx #0
    ldy #0
    lda #0
S6Normal_ResetStageWorld__metadata:
    sta.l $412100,x
    inx
    inx
    iny
    iny
    cpy #StageEnv_ActorRowsBytes
    bcc S6Normal_ResetStageWorld__metadata
    rep #$30
    .a16
    .i16
    lda.l $7E1752
    clc
    adc #CHAR_ZP_LEN
    sta.l $7E1752
    lda.l $7E1754
    clc
    adc #$0100
    sta.l $7E1754
    cmp #$1F00
    bcc S6Normal_ResetStageWorld__slot
    jsl S6Normal_MutationFenceEnd
S6Normal_ResetStageWorld__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; Called at the real post-OOP/pre-render seam. The fixture's elapsed-time
; accumulator is reused unchanged; its synthetic command remains zero.
S6Normal_RenderHook:
    rep #$30
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #2
    bne S6Normal_RenderHook__bind_if_ready
    lda #3
    sta.l S6Host_Mode
S6Normal_RenderHook__bind_if_ready:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_RenderHook__bind_live
    cmp #3
    bne S6Normal_RenderHook__ready
S6Normal_RenderHook__bind_live:
    jsl S6Normal_RebaseStageClock
    ; Player/source entities can be created while Stage_Load is still
    ; materializing per-actor environment rows. Reconcile unowned live rows
    ; at every real post-load render seam before the next catch-up batch. Some
    ; stage-start actors are installed by the native stage bootstrap rather
    ; than ActorBehavior_Bind; the first sweep can precede their allocation.
    ; S6Normal_BindLiveActors skips existing bridge owners, so this does not
    ; reinitialize resident state or exchange whole contexts.
    jsl S6Normal_BindLiveActors
S6Normal_RenderHook__ready:
    ; A source-world player can be retired at zero HP before BOR's native
    ; stock/fall service runs. Once that service respawns a live player,
    ; restore only the missing persistent row at this existing dependency
    ; seam; never rebind an active row or an exhausted player.
    jsl S6Normal_RebindReturnedPlayers
    jml S6Game_PlayRender

; Campaign transitions can spend many physical fields in showcomplete and
; stage bootstrap while the persistent source world is intentionally parked.
; Rebase the source-field epoch exactly once when the authored physical stage
; changes, before the next catch-up pass. Do not interpret that non-gameplay
; time as a lost or oversized visual transaction.
S6Normal_RebaseStageClock:
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_RebaseStageClock__return
    lda.l Game_StageIndex
    cmp.l S6Normal_LastStage
    beq S6Normal_RebaseStageClock__return
    ; WorldMaxX is a native-coordinate stage input. Drain the previous
    ; epoch and park SA-1 while publishing its exact Normal-policy inverse;
    ; player movement then applies BOR's existing per-stage right bound.
    lda #0
    sta.l S6Host_Error
    jsl S7Resident_Flush
    jsl S6Normal_MutationFenceBegin
    lda.l WorldMaxX
    jsl S6Bridge_UnprojectRounded
    bcs S6Normal_RebaseStageClock__bad_limit
    sta.l S6Host_PlayerWorldMaxX
    bra S6Normal_RebaseStageClock__release
S6Normal_RebaseStageClock__bad_limit:
    lda #10
    sta.l S6Host_Error
S6Normal_RebaseStageClock__release:
    jsl S6Normal_MutationFenceEnd
    lda.l S6Host_Error
    bne S6Normal_RebaseStageClock__return
    lda.l Game_StageIndex
    sta.l S6Normal_LastStage
    lda.l StageTimer_FieldCounter
    sta.l S6Game_LastField
    lda #0
    sta.l S6Host_Error
S6Normal_RebaseStageClock__return:
    pla
    plp
    rtl

; ActorBehavior_Bind entry replacement. Only real players and ordinary
; source AI actors enter the SA-1 world. Every other typed entity retains its
; existing S-CPU-owned runtime and cannot poison the combat-world preflight.
S6Normal_Bind:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_Bind__normal_campaign
    jmp S6Normal_Bind__fallback
S6Normal_Bind__normal_campaign:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_Bind__active
    cmp #3
    beq S6Normal_Bind__active
    jmp S6Normal_Bind__fallback
S6Normal_Bind__active:
    sep #$20
    .a8
    ; Biker-K' uses the existing special S-CPU vehicle controller. The
    ; ordinary grounded source-world adapter must not steal that identity.
    lda CHAR_ROSTER_INDEX
    cmp #28
    bne S6Normal_Bind__ordinary_roster
    brl S6Normal_Bind__fallback
S6Normal_Bind__ordinary_roster:
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq S6Normal_Bind__source_input_ok
    cmp #2
    beq S6Normal_Bind__source_input_ok
    brl S6Normal_Bind__fallback
S6Normal_Bind__source_input_ok:
    ; Vertical source drops remain under the existing native throw/drop
    ; service until they land. Their nonzero CHAR_THROW_ZPOS is real source
    ; state, not a malformed grounded actor for S6Bridge_Import.
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_AI
    bne S6Normal_Bind__source_drop_ready
    rep #$30
    .a16
    .i16
    ; Spawn binding can run before StageBoundsHost_ResetSpawn marks a
    ; down-scroll drop. Never import an airborne AI incarnation as grounded;
    ; fallback retires any previous occupant of this physical slot, and the
    ; native drop path hands it back only once both height terms settle.
    lda CHAR_THROW_ZPOS
    ora CHAR_THROW_ZVEL
    beq S6Normal_Bind__source_height_grounded
    brl S6Normal_Bind__fallback
S6Normal_Bind__source_height_grounded:
    jsl StageBounds_Row
    lda.l StageDrop_State,x
    beq S6Normal_Bind__source_drop_ready
    brl S6Normal_Bind__fallback
S6Normal_Bind__source_drop_ready:
    rep #$30
    .a16
    .i16
    ; The production binder also sees items and typed scenery. Only combat
    ; models present in the compiler-owned worker table enter this world.
    lda CHAR_ROSTER_INDEX
    and #$00FF
    jsl S6Normal_IsRosterBound
    bcs S6Normal_Bind__combat
    brl S6Normal_Bind__fallback
S6Normal_Bind__combat:
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    beq S6Normal_Bind__bind
    ; Worker owns the old incarnation until this acknowledged release point.
    ; The spawn hook runs after native allocation has initialized the reused
    ; production slot, so preserve only those scalar birth values that the
    ; old snapshot is allowed to mirror back before the new bind.
    lda CHAR_POS_X
    pha
    lda CHAR_POS_Y
    pha
    sep #$20
    .a8
    lda CHAR_HP
    pha
    lda CHAR_FACING_LEFT
    pha
    rep #$30
    .a16
    .i16
    jsl S7Resident_Flush
    sep #$20
    .a8
    pla
    sta CHAR_FACING_LEFT
    pla
    sta CHAR_HP
    rep #$30
    .a16
    .i16
    pla
    sta CHAR_POS_Y
    pla
    sta CHAR_POS_X
S6Normal_Bind__bind:
    ; Publish the new incarnation only while the worker is parked at a
    ; source-tick boundary. The native binder remains S-CPU local.
    jsl S6Normal_MutationFenceBegin
    jsl S6Normal_UpdateNativePropFenced
    ; The host imports this bit as the source-world alive state. Publish it
    ; before the import so the first worker snapshot owns a live incarnation;
    ; the returned-player path follows the same ordering below.
    sep #$20
    .a8
    lda #1
    sta.l S6Bridge_Exists,x
    rep #$30
    .a16
    .i16
    jsl S6Host_BindExisting
    lda.l S6Host_Error
    beq S6Normal_Bind__worker_ready
    lda.l $7E1754
    sec
    sbc #$1900
    xba
    and #$00FF
    tax
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    ; S6Host_BindExisting may have published a bridge row before a later
    ; import/role validation failed. Clear that exact 133-byte production
    ; row, not the small worker-context index held in X above.
    lda.l $7E1752
    tax
    lda #0
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_Exists,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    sta.l S6Host_Action,x
    sta.l S6Host_Frame,x
    sta.l S6Host_Role,x
    sep #$20
    .a8
    bra S6Normal_Bind__fenced_done
S6Normal_Bind__worker_ready:
    lda.l $7E1754
    sec
    sbc #$1900
    xba
    and #$00FF
    tax
    sep #$20
    .a8
    lda CHAR_ROSTER_INDEX
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    beq S6Normal_Bind__fenced_done
    jsl S6Normal_SyncBoundContext
S6Normal_Bind__fenced_done:
    jsl S6Normal_MutationFenceEnd
S6Normal_Bind__handled:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    rtl
S6Normal_Bind__fallback:
    jsl S6Normal_RetireReplacedBound
    ; The old incarnation is now retired and all earlier worker events have
    ; been drained; publish the new native target kind only at this boundary.
    jsl S6Normal_UpdateNativeProp
    ply
    plx
    plp
    php
    rep #$31
    .a16
    .i16
    phx
    jml S6Normal_BindResume

; A newly allocated typed S-CPU entity can reuse a slot whose previous
; incarnation was owned by the resident source world. Fence and retire only
; that old worker row before the new entity continues through its native
; binder. The flush may project the old actor into the just-created slot, so
; preserve the four fields S6Bridge_Export can modify.
S6Normal_RetireReplacedBound:
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
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_RetireReplacedBound__campaign
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__campaign:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_RetireReplacedBound__mode
    cmp #3
    beq S6Normal_RetireReplacedBound__mode
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__mode:
    tdc
    sec
    sbc #$0A00
    tax
    cpx #CHAR_ZP_LEN*6
    bcc S6Normal_RetireReplacedBound__row
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__row:
    txa
    sta.l $7E1752
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Normal_RetireReplacedBound__owned
    cmp #2
    beq S6Normal_RetireReplacedBound__owned
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__owned:
    lda CHAR_POS_X
    pha
    lda CHAR_POS_Y
    pha
    sep #$20
    .a8
    lda CHAR_HP
    pha
    lda CHAR_FACING_LEFT
    pha
    rep #$30
    .a16
    .i16
    jsl S7Resident_Flush
    sep #$20
    .a8
    pla
    sta CHAR_FACING_LEFT
    pla
    sta CHAR_HP
    rep #$30
    .a16
    .i16
    pla
    sta CHAR_POS_Y
    pla
    sta CHAR_POS_X
    ; Resolve the paired persistent actor page from the production slot row.
    lda.l $7E1752
    tax
    ldy #$1900
S6Normal_RetireReplacedBound__context:
    cpx #0
    beq S6Normal_RetireReplacedBound__context_ready
    txa
    sec
    sbc #CHAR_ZP_LEN
    bcs S6Normal_RetireReplacedBound__context_advance
    brl S6Normal_RetireReplacedBound__fault
S6Normal_RetireReplacedBound__context_advance:
    tax
    tya
    clc
    adc #$0100
    tay
    cpy #$1F00
    bcc S6Normal_RetireReplacedBound__context
    brl S6Normal_RetireReplacedBound__fault
S6Normal_RetireReplacedBound__context_ready:
    tya
    sta.l $7E1754
    tya
    tcd
    ; A fallback/replacement ends this source actor incarnation. Park the
    ; worker before touching its canonical context; otherwise the old row can
    ; keep simulating after its S-CPU bridge mapping is cleared and later emit
    ; an unlink event that aliases a future occupant of the reused slot.
    jsl S6Normal_MutationFenceBegin
    ; The source worker may already have applied the ordered unlink and
    ; cleared F6 while the fixed context reservation and stale native bridge
    ; row remain. In that case only retire the projection; do not run
    ; KillUnlinked a second time against the detached context.
    lda $F6
    beq S6Normal_RetireReplacedBound__already_unlinked
    brl S6Normal_RetireReplacedBound__kill_live
S6Normal_RetireReplacedBound__already_unlinked:
    brl S6Normal_RetireReplacedBound__unlinked
S6Normal_RetireReplacedBound__kill_live:
    stz $FC
    jsl S6_KillUnlinked
    lda $FC
    beq S6Normal_RetireReplacedBound__unlinked
    jsl S6Normal_MutationFenceEnd
    bra S6Normal_RetireReplacedBound__fault
S6Normal_RetireReplacedBound__unlinked:
    ; KillUnlinked clears the source relationships; retire the actor itself
    ; before publishing the detached bridge row. This prevents future worker
    ; passes from running an actor whose native slot now belongs to fallback.
    stz $F6
    ; Publish the relationship fields, but not the stale S-CPU world clock.
    ; The host world stores context DPs in the $1900 window, while SA-1
    ; target traversal dereferences the corresponding $7900 BW-RAM aliases.
    ; Copying these words raw here leaves targeting pointed into the world
    ; header after any typed-slot retirement/rebind.
    lda.l $7E1744
    beq S6Normal_RetireReplacedBound__p0_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__p0_ready:
    sta.l $411744
    lda.l $7E1746
    beq S6Normal_RetireReplacedBound__p1_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__p1_ready:
    sta.l $411746
    lda.l $7E174E
    beq S6Normal_RetireReplacedBound__op0_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__op0_ready:
    sta.l $41174E
    lda.l $7E1750
    beq S6Normal_RetireReplacedBound__op1_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__op1_ready:
    sta.l $411750
    ; Remove this slot from the bridge admission table, retaining unrelated
    ; StageEnv fields (base, alias, and scene metadata) for the new entity.
    lda.l $7E1752
    tax
    lda #0
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    sta.l S6Host_Action,x
    sta.l S6Host_Frame,x
    sta.l S6Host_Role,x
    jsl S6Normal_SyncBoundContext
    lda.l $7E1754
    sec
    sbc #$1900
    xba
    and #$00FF
    tax
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    jsl S6Normal_MutationFenceEnd
    bra S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__fault:
    rep #$30
    .a16
    .i16
    lda #10
    sta.l S6Host_Error
S6Normal_RetireReplacedBound__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; A16 roster id in A. Carry is set only for a model admitted to this Normal
; worker image. Bind and tick preflight share this predicate: typed
; noncombat entities retain their S-CPU services; a missing combat binding
; remains a fail-closed worker error.
S6Normal_IsRosterBound:
    php
    rep #$30
    .a16
    .i16
    phx
    sta.l $7E1758
    ldx #0
S6Normal_IsRosterBound__scan:
    cpx #S6Host_ModelCount*32
    bcs S6Normal_IsRosterBound__no
    lda.l S6Host_ModelTable,x
    cmp.l $7E1758
    beq S6Normal_IsRosterBound__yes
    txa
    clc
    adc #32
    tax
    bra S6Normal_IsRosterBound__scan
S6Normal_IsRosterBound__yes:
    plx
    plp
    sec
    rtl
S6Normal_IsRosterBound__no:
    plx
    plp
    clc
    rtl

; First-stage handoff. The native actor contexts are the same six physical
; slots already used by Spawn_Play; do not allocate or duplicate them. Only
; live player/AI rows are considered, and S6Normal_Bind's source roster table
; keeps items/scenery on their existing typed runtime.
S6Normal_BindLiveActors:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phd
    ldx #0
    ldy #0
    lda #0
    sta.l S6Normal_BindLiveActors__slot_index
S6Normal_BindLiveActors__slot:
    txa
    clc
    adc #$0A00
    tcd
    jsl S6Normal_UpdateNativeProp
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    bne S6Normal_BindLiveActors__policy_nonzero
    brl S6Normal_BindLiveActors__check_live
S6Normal_BindLiveActors__policy_nonzero:
    cmp #2
    beq S6Normal_BindLiveActors__policy_two
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__policy_two:
    ; Bridge policy is only the S-CPU projection. Require the matching live
    ; BW-RAM sidecar before treating it as persistent ownership.
    rep #$30
    .a16
    .i16
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #2
    beq S6Normal_BindLiveActors__bridge_policy_valid
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__bridge_policy_valid:
    phx
    tya
    tax
    lda.l $412140,x
    plx
    and #$FF00
    cmp #$0100
    beq S6Normal_BindLiveActors__worker_present
    brl S6Normal_BindLiveActors__needs_bind
S6Normal_BindLiveActors__worker_present:
    phx
    tya
    tax
    lda.l $412140,x
    plx
    cmp #$0102
    beq S6Normal_BindLiveActors__worker_status_valid
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_status_valid:
    phx
    tya
    tax
    lda.l $412144,x
    sta.l S6Normal_BindLiveActors__worker_context
    plx
    lda.l S6Bridge_Context,x
    cmp.l S6Normal_BindLiveActors__worker_context
    beq S6Normal_BindLiveActors__worker_context_matches
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_context_matches:
    ; Exists=2 is an ordered removal still crossing the event ring. Leave its
    ; incarnation alone until that event is projected. Exists=0 with a
    ; matching resident slot is different: the worker has already unlinked
    ; the actor and F6 is clear, while the fixed context reservation remains
    ; $0102. Retire only the stale bridge projection, never KillUnlinked twice.
    sep #$20
    .a8
    lda.l S6Bridge_Exists,x
    cmp #1
    beq S6Normal_BindLiveActors__worker_actor_live
    cmp #2
    beq S6Normal_BindLiveActors__worker_unlink_pending
    cmp #0
    beq S6Normal_BindLiveActors__worker_unlinked
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_unlinked:
    rep #$30
    .a16
    .i16
    phx
    lda.l S6Normal_BindLiveActors__worker_context
    sec
    sbc #$1900
    tax
    sep #$20
    .a8
    lda.l $4119F6,x
    bne S6Normal_BindLiveActors__worker_context_live
    rep #$30
    .a16
    .i16
    plx
    ; Reuse the established fenced retirement path. It clears the stale bridge
    ; mapping and skips KillUnlinked when the worker context is already empty.
    ; Then the current native actor is admitted through the ordinary binder.
    lda #0
    sta.l S6Host_Error
    jsl S6Normal_RetireReplacedBound
    lda.l S6Host_Error
    beq S6Normal_BindLiveActors__worker_retired
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__worker_retired:
    ; Retirement returns in A16. Re-enter through needs_bind so its SEP sets
    ; the native actor-check width before any byte-sized direct-page reads.
    brl S6Normal_BindLiveActors__needs_bind
S6Normal_BindLiveActors__worker_context_live:
    rep #$30
    .a16
    .i16
    plx
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_unlink_pending:
    rep #$30
    .a16
    .i16
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__worker_actor_live:
    rep #$30
    .a16
    .i16
    ; A live SA-1 context can still describe the previous roster if the
    ; spawn path reused this native slot without calling ActorBehavior_Bind.
    phx
    lda.l S6Normal_BindLiveActors__slot_index
    tax
    sep #$20
    .a8
    lda.l S6Normal_BoundRoster,x
    cmp CHAR_ROSTER_INDEX
    rep #$30
    .a16
    .i16
    plx
    bne S6Normal_BindLiveActors__roster_changed
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__roster_changed:
    lda #0
    sta.l S6Host_Error
    jsl S6Normal_RetireReplacedBound
    lda.l S6Host_Error
    beq S6Normal_BindLiveActors__replacement_ready
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__replacement_ready:
    jsl S6Normal_Bind
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__ownership_fault:
    ; A different live source context must never be overwritten implicitly.
    rep #$30
    .a16
    .i16
    lda #10
    sta.l S6Host_Error
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__needs_bind:
    sep #$20
    .a8
S6Normal_BindLiveActors__check_live:
    lda CHAR_HP
    beq S6Normal_BindLiveActors__next
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq S6Normal_BindLiveActors__bind
    cmp #2
    bne S6Normal_BindLiveActors__next
    ; The source vertical-drop adapter owns this actor until landing. Do not
    ; repeatedly attempt a grounded worker bind while its native throw
    ; state is still active; StageDrop_BeforeActor performs the handoff.
    rep #$30
    .a16
    .i16
    jsl StageBounds_Row
    lda.l StageDrop_State,x
    bne S6Normal_BindLiveActors__next
    lda CHAR_THROW_ZPOS
    ora CHAR_THROW_ZVEL
    bne S6Normal_BindLiveActors__next
    sep #$20
    .a8
S6Normal_BindLiveActors__bind:
    rep #$30
    .a16
    .i16
    ; A worker-side unlink can leave only the S-CPU bridge policy behind.
    ; Rebind catalogued combat at this real boundary; typed entities such as
    ; Biker-K' instead shed only the stale bridge, without killing an empty
    ; worker context.
    sep #$20
    .a8
    lda CHAR_ROSTER_INDEX
    cmp #28
    beq S6Normal_BindLiveActors__detach_stale
    rep #$30
    .a16
    .i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    jsl S6Normal_IsRosterBound
    bcs S6Normal_BindLiveActors__try_bind
    bra S6Normal_BindLiveActors__detach_stale
S6Normal_BindLiveActors__try_bind:
    jsl S6Normal_Bind
    bra S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__detach_stale:
    rep #$30
    .a16
    .i16
    phx
    lda.l S6Normal_BindLiveActors__slot_index
    tax
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    plx
    lda #0
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    sta.l S6Host_Action,x
    sta.l S6Host_Frame,x
    sta.l S6Host_Role,x
S6Normal_BindLiveActors__next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    tya
    clc
    adc #133
    tay
    lda.l S6Normal_BindLiveActors__slot_index
    inc a
    sta.l S6Normal_BindLiveActors__slot_index
    cpx #CHAR_ZP_LEN*6
    bcs S6Normal_BindLiveActors__done
    brl S6Normal_BindLiveActors__slot
S6Normal_BindLiveActors__done:
    pld
    ply
    plx
    plp
    rtl

; Called only by the source-drop landing seam patched into the opt-in Normal
; image. D still identifies the physical actor row. Bind a grounded,
; compiler-admitted enemy here and return carry set to consume this actor pass;
; unsupported/native actors keep the base drop service's ordinary path.
S6Normal_DropHandoff:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_DropHandoff__no
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_DropHandoff__active
    cmp #3
    bne S6Normal_DropHandoff__no
S6Normal_DropHandoff__active:
    sep #$20
    .a8
    lda CHAR_HP
    beq S6Normal_DropHandoff__no
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_AI
    bne S6Normal_DropHandoff__no
    rep #$30
    .a16
    .i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    jsl S6Normal_IsRosterBound
    bcc S6Normal_DropHandoff__no
    lda CHAR_THROW_ZPOS
    ora CHAR_THROW_ZVEL
    bne S6Normal_DropHandoff__no
    lda.l S6Host_Error
    bne S6Normal_DropHandoff__owned
    jsl S6Normal_Bind
    lda.l S6Host_Error
    bne S6Normal_DropHandoff__owned
    jsl StageBounds_Row
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    cmp #2
    bne S6Normal_DropHandoff__fault
    lda.l S6Bridge_Exists,x
    cmp #1
    beq S6Normal_DropHandoff__owned
S6Normal_DropHandoff__fault:
    rep #$30
    .a16
    .i16
    lda #10
    sta.l S6Host_Error
S6Normal_DropHandoff__owned:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    sec
    rtl
S6Normal_DropHandoff__no:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    clc
    rtl

; Publish whether this existing physical actor row is a native S-CPU-owned
; combat target (currently props and the special Biker driver). A changed
; marker is written at a worker poll fence so the six-row ordered attack scan
; cannot observe a torn slot-type transition on reuse.
S6Normal_UpdateNativeProp:
    php
    rep #$30
    .a16
    .i16
    phx
    tdc
    sec
    sbc #$0A00
    ldx #0
S6Normal_UpdateNativeProp__slot:
    cmp #0
    beq S6Normal_UpdateNativeProp__found
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Normal_UpdateNativeProp__return
    inx
    cpx #6
    bcc S6Normal_UpdateNativeProp__slot
    bra S6Normal_UpdateNativeProp__return
S6Normal_UpdateNativeProp__found:
    sep #$20
    .a8
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq S6Normal_UpdateNativeProp__want_prop
    cmp #CHAR_INPUT_DRIVEN_BIKER
    beq S6Normal_UpdateNativeProp__want_prop
    lda.l S6Normal_NativePropMask,x
    beq S6Normal_UpdateNativeProp__return
    bra S6Normal_UpdateNativeProp__fence
S6Normal_UpdateNativeProp__want_prop:
    lda.l S6Normal_NativePropMask,x
    bne S6Normal_UpdateNativeProp__return
S6Normal_UpdateNativeProp__fence:
    rep #$30
    .a16
    .i16
    jsl S7Resident_Flush
    jsl S6Normal_MutationFenceBegin
    jsl S6Normal_UpdateNativeProp__write
    jsl S6Normal_MutationFenceEnd
S6Normal_UpdateNativeProp__return:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; Caller already owns the poll fence (the combat actor bind path).
S6Normal_UpdateNativePropFenced:
    php
    rep #$30
    .a16
    .i16
    phx
    tdc
    sec
    sbc #$0A00
    ldx #0
S6Normal_UpdateNativePropFenced__slot:
    cmp #0
    beq S6Normal_UpdateNativePropFenced__found
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Normal_UpdateNativePropFenced__return
    inx
    cpx #6
    bcc S6Normal_UpdateNativePropFenced__slot
    bra S6Normal_UpdateNativePropFenced__return
S6Normal_UpdateNativePropFenced__found:
    jsl S6Normal_UpdateNativeProp__write
S6Normal_UpdateNativePropFenced__return:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; X is the six-row physical entity slot. Both wrappers above call this tiny
; writer only while the worker is parked or before its epoch starts.
S6Normal_UpdateNativeProp__write:
    sep #$20
    .a8
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq S6Normal_UpdateNativeProp__write_target
    cmp #CHAR_INPUT_DRIVEN_BIKER
    bne S6Normal_UpdateNativeProp__write_clear
S6Normal_UpdateNativeProp__write_target:
    lda #1
    sta.l S6Normal_NativePropMask,x
    rtl
S6Normal_UpdateNativeProp__write_clear:
    lda #0
    sta.l S6Normal_NativePropMask,x
    rtl

; Reconcile exactly the actor whose context was just rebound. Relay_Flush
; fences the worker; this is not a per-source-tick full-context transfer.
S6Normal_SyncBoundContext:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l $7E1754
    sec
    sbc #$1900
    tax
    ldy #0
S6Normal_SyncBoundContext__context:
    lda.l $7E1900,x
    sta.l $411900,x
    inx
    inx
    iny
    iny
    cpy #$0100
    bcc S6Normal_SyncBoundContext__context
    ; New births occur after Relay_Acquire. Convert only this context's
    ; S-CPU pointers to the SA-1 $6000 window before publishing it.
    lda.l $7E1754
    sec
    sbc #$1900
    tax
    lda.l $411934,x
    beq S6Normal_SyncBoundContext__relocate_36
    clc
    adc #$6000
    sta.l $411934,x
S6Normal_SyncBoundContext__relocate_36:
    .a16
    .i16
    lda.l $411936,x
    beq S6Normal_SyncBoundContext__relocate_B0
    clc
    adc #$6000
    sta.l $411936,x
S6Normal_SyncBoundContext__relocate_B0:
    .a16
    .i16
    lda.l $4119B0,x
    beq S6Normal_SyncBoundContext__metadata_start
    clc
    adc #$6000
    sta.l $4119B0,x
S6Normal_SyncBoundContext__metadata_start:
    .a16
    .i16
    lda.l $7E1752
    tax
    ldy #0
S6Normal_SyncBoundContext__metadata:
    lda.l StageEnv_Actors,x
    sta.l $412100,x
    inx
    inx
    iny
    iny
    cpy #132
    bcc S6Normal_SyncBoundContext__metadata
    ; X now points at this row's final metadata byte (row stride is 133).
    ; Keep the full-width index produced by the word-copy loop; rebuilding
    ; it in A8 would truncate slot offsets and inherit A's stale high byte.
    sep #$20
    .a8
    lda.l StageEnv_Actors,x
    sta.l $412100,x
    rep #$30
    .a16
    .i16
    ; S6_SelectTarget reads the canonical player DPs from world $44/$46.
    ; Keep the S-CPU fallback pointers in bank-0 WRAM and the persistent
    ; worker's corresponding $6000-window pointers in shared BW-RAM.
    lda.l $7E1752
    beq S6Normal_SyncBoundContext__player0
    cmp #CHAR_ZP_LEN
    beq S6Normal_SyncBoundContext__player1
    bra S6Normal_SyncBoundContext__done
S6Normal_SyncBoundContext__player0:
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    cmp #1
    bne S6Normal_SyncBoundContext__done
    rep #$30
    .a16
    .i16
    lda #$1900
    sta.l $7E1744
    lda #$7900
    sta.l $411744
    bra S6Normal_SyncBoundContext__done
S6Normal_SyncBoundContext__player1:
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_INPUT_DRIVEN+CHAR_ZP_LEN
    cmp #1
    bne S6Normal_SyncBoundContext__done
    rep #$30
    .a16
    .i16
    lda #$1A00
    sta.l $7E1746
    lda #$7A00
    sta.l $411746
S6Normal_SyncBoundContext__done:
    ply
    plx
    plp
    rtl

; Player stock/fall remains BOR's S-CPU lifecycle, but a dead player row must
; first leave the persistent source world. Queue the normal sequenced worker
; unlink once at HP=0; the ordered unlink event clears S6Bridge_Exists, after
; which CharacterEntity_Play runs only the native player's fall/respawn path.
; Exists=2 is the pending fence and prevents duplicate remove requests while
; the worker command/event crosses the next source boundary.
S6Normal_DeathService:
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
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_DeathService__done
    lda.l S7Resident_Owner
    cmp #2
    bne S6Normal_DeathService__done
    ldx #0
    jsl S6Normal_QueueDeadPlayer
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq S6Normal_DeathService__done
    ldx #CHAR_ZP_LEN
    jsl S6Normal_QueueDeadPlayer
S6Normal_DeathService__done:
    pld
    plb
    ply
    plx
    plp
    ; Retain the native stock, OUT, and fall-animation semantics and return
    ; their exact carry result to StageTimerHost_ServiceDeaths.
    jml G13_HandleP2Death

; X=production row byte offset, P1/P2 only. A failed/full remove ring keeps
; ownership on SA-1 and retries at the next native death-service boundary.
S6Normal_QueueDeadPlayer:
    php
    rep #$30
    .a16
    .i16
    phx
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    cmp #2
    bne S6Normal_QueueDeadPlayer__done
    lda.l S6Bridge_Exists,x
    cmp #1
    bne S6Normal_QueueDeadPlayer__done
    lda.l $7E0A00+CHAR_HP,x
    bne S6Normal_QueueDeadPlayer__done
    rep #$30
    .a16
    .i16
    lda #0
    sta.l S6Host_Error
    txa
    clc
    adc #$0A00
    ; The production worker installer rewrites this call to Relay_QueueRemove.
    jsl S6Host_RemoveHandle
    lda.l S6Host_Error
    beq S6Normal_QueueDeadPlayer__accepted
    ; The one-entry sequenced removal mailbox can be occupied by the other
    ; player's simultaneous death. Relay_QueueRemove reports that retryable
    ; condition as 24 in the shared host status cell; do not leave it latched
    ; as a fatal world error, or the queued first removal can never be
    ; acknowledged and neither player can progress through native lifecycle.
    cmp #24
    bne S6Normal_QueueDeadPlayer__done
    lda #0
    sta.l S6Host_Error
    bra S6Normal_QueueDeadPlayer__done
S6Normal_QueueDeadPlayer__accepted:
    sep #$20
    .a8
    lda #2
    sta.l S6Bridge_Exists,x
S6Normal_QueueDeadPlayer__done:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; Restore a player row after the S-CPU's existing death/respawn service. A=0
; / CHAR_ZP_LEN in the helper. This is a single-slot birth transfer, not a
; per-tick ownership exchange; all live gameplay state remains on the worker.
S6Normal_RebindReturnedPlayers:
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
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_RebindReturnedPlayers__done
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_RebindReturnedPlayers__active
    cmp #3
    bne S6Normal_RebindReturnedPlayers__done
S6Normal_RebindReturnedPlayers__active:
    ldx #0
    jsl S6Normal_RebindReturnedPlayer
    ldx #CHAR_ZP_LEN
    jsl S6Normal_RebindReturnedPlayer
S6Normal_RebindReturnedPlayers__done:
    pld
    plb
    ply
    plx
    plp
    rtl

; X=production row byte offset. A row is eligible only after the native
; player service has restored HP and cleared OUT. The existing compiler-bound
; model policy is retained, and context+metadata are synchronized once after
; the bind so the SA-1 alias sees the new incarnation before its next tick.
S6Normal_RebindReturnedPlayer:
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
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Normal_RebindReturnedPlayer__owned
    cmp #2
    bne S6Normal_RebindReturnedPlayer__done
S6Normal_RebindReturnedPlayer__owned:
    lda.l S6Bridge_Exists,x
    and #$00FF
    bne S6Normal_RebindReturnedPlayer__done
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_HP,x
    beq S6Normal_RebindReturnedPlayer__done
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    cmp #1
    bne S6Normal_RebindReturnedPlayer__done
    cpx #0
    bne S6Normal_RebindReturnedPlayer__p2
    lda.l G13_P1Out
    bne S6Normal_RebindReturnedPlayer__done
    bra S6Normal_RebindReturnedPlayer__ready
S6Normal_RebindReturnedPlayer__p2:
    lda.l G13_TwoPlayerEnabled
    beq S6Normal_RebindReturnedPlayer__done
    lda.l G13_P2Out
    bne S6Normal_RebindReturnedPlayer__done
S6Normal_RebindReturnedPlayer__ready:
    rep #$30
    .a16
    .i16
    lda.l S7Resident_Owner
    cmp #2
    bne S6Normal_RebindReturnedPlayer__flush_done
    jsl S7Resident_Flush
S6Normal_RebindReturnedPlayer__flush_done:
    jsl S6Normal_MutationFenceBegin
S6Normal_RebindReturnedPlayer__bind:
    .a16
    .i16
    sep #$20
    .a8
    lda #1
    sta.l S6Bridge_Exists,x
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #$0A00
    tcd
    ; This row already passed the Normal source-model admission check when
    ; first bound. Re-entry here is a native respawn dependency boundary,
    ; not an ActorBehavior_Bind hook call: its unbound fallback tail-jumps to
    ; the generic actor continuation and would return through the wrong stack.
    ; Reinitialize this known slot directly and fail closed in the host binder.
    jsl S6Host_BindExisting
    lda.l S6Host_Error
    bne S6Normal_RebindReturnedPlayer__fenced_done
    jsl S6Normal_SyncBoundContext
S6Normal_RebindReturnedPlayer__fenced_done:
    jsl S6Normal_MutationFenceEnd
S6Normal_RebindReturnedPlayer__done:
    pld
    plb
    ply
    plx
    plp
    rtl

; Actor-context and StageEnv publication is rare and occurs only at true
; production birth/retire boundaries. Park the persistent worker at its poll
; safepoint while those shared BW-RAM rows are updated; normal source ticks
; remain asynchronous and perform no ownership transfer.
S6Normal_MutationFenceBegin:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l $7E175C
    beq S6Normal_MutationFenceBegin__return
    sep #$20
    .a8
    lda #1
    sta.l $41200C
    rep #$30
    .a16
    .i16
    ldy #$FFFF
S6Normal_MutationFenceBegin__wait:
    sep #$20
    .a8
    lda.l $41200A
    bne S6Normal_MutationFenceBegin__fault
    lda.l $41200C
    cmp #2
    beq S6Normal_MutationFenceBegin__return
    rep #$30
    .a16
    .i16
    dey
    bne S6Normal_MutationFenceBegin__wait
S6Normal_MutationFenceBegin__fault:
    rep #$30
    .a16
    .i16
    lda #21
    sta.l S6Host_Error
    stp
S6Normal_MutationFenceBegin__return:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    rtl

S6Normal_MutationFenceEnd:
    php
    rep #$30
    .a16
    .i16
    phx
    lda.l $7E175C
    beq S6Normal_MutationFenceEnd__return
    sep #$20
    .a8
    lda #0
    sta.l $41200C
S6Normal_MutationFenceEnd__return:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl
