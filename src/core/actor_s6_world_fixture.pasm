; Private production-image hooks. No production include/default policy change.
; Command1 loads the selected real stage; its one retained authored queue record
; remains owned by normal Spawn_Play. Player positions are fixture preconditions.
S6Game_Command = $7E1770
S6Game_LastField = $7E1772
S6Game_TickCommit = $7E1774
S6Game_BirthCount = $7E177E ; fixture-owned, cleared by whole world-context reset

S6Game_Entity:
    php
    rep #$30
    .a16
    .i16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Game_Entity__exact
    plx
    plp
    rep #$31
    .a16
    .i16
    phd
    jsl G13_PlayerLifecycleIsOut
    jml S6Game_EntityResume
S6Game_Entity__exact:
    .a16
    .i16
    plx
    plp
    jml CharacterEntity_Play__no_context_exit

S6Game_Bind:
    php
    rep #$30
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #2
    beq S6Game_Bind__exact
    plp
    php
    rep #$31
    .a16
    .i16
    phx
    jml S6Game_BindResume
S6Game_Bind__exact:
    .a16
    .i16
    lda #S6Game_Profile
    beq S6Game_Bind__placed
    jsl S6Host_BindExisting
    lda.l S6Host_Error
    bne S6Game_Bind__done
S6Game_Bind__placed:
    .a16
    .i16
    lda #S6Game_ControlPlacement
    beq S6Game_Bind__ready
    ; Same bounded Kula control geometry under both explicit policies.
    ; These are post-birth fixture preconditions, NOT source movement proof.
    lda #124
    sta CHAR_POS_X
    lda #100
    sta.l $7E0A00+CHAR_POS_X
    sep #$20
    .a8
    lda #100
    sta CHAR_HP
    rep #$30
    .a16
    .i16
S6Game_Bind__ready:
    .a16
    .i16
    lda.l S6Game_BirthCount
    inc a
    sta.l S6Game_BirthCount
    cmp #S6Game_ExpectedBirths
    bcc S6Game_Bind__done
    lda #3                   ; bound, await first complete world-pass boundary
    sta.l S6Host_Mode
    lda #S6Game_InitialAction
    sta.l S6Host_Action
    lda.l Nmi_FrameCounter
    sta.l S6Game_LastField
S6Game_Bind__done:
    .a16
    .i16
    plp
    rtl

; Called at the existing post-OOP/pre-render seam. Preserve all renderer inputs.
S6Game_PlayRender:
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
    lda #0
    tcd
    lda.l S6Game_Command
    cmp #1
    beq S6Game_PlayRender__load
    jmp S6Game_PlayRender__tick
S6Game_PlayRender__load:
    .a16
    .i16
    lda #0
    sta.l S6Game_Command
    sta.l S6Host_Mode
    ; Controlled teardown of the startup stage. Stage_Load normally assumes
    ; its preceding stage has cleared; do not carry its NPCs into this fixture.
    sep #$20
    .a8
    lda #VMSTAT_DONE          ; bounded stage fixture has no startup VM script
    sta.l VmState_Status
    ldx #CHAR_ZP_LEN*2
S6Game_PlayRender__clear_old:
    .a8
    .i16
    lda #0
    sta.l $7E0A00+CHAR_HP,x
    rep #$20
    .a16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    sep #$20
    .a8
    cpx #CHAR_ZP_LEN*6
    bcc S6Game_PlayRender__clear_old
    rep #$30
    .a16
    .i16
    lda #S6Game_Stage
    sta.l Game_StageIndex
    sep #$20
    .a8
    sta.l Bg_LoadScene_StageIndex
    rep #$30
    .a16
    .i16
    jsl Stage_LoadAndRespawn_Long
    sep #$20
    .a8
    lda #0
    ldx #5
S6Game_PlayRender__clear_grace:
    .a8
    .i16
    sta.l Actor_InvulnFrames,x
    dex
    bpl S6Game_PlayRender__clear_grace
    rep #$30
    .a16
    .i16
    lda #$1700
    tcd
    lda #0
    ldx #$FE
S6Game_PlayRender__clear:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl S6Game_PlayRender__clear
    lda #$02D2
    sta $00
    lda #$4996
    sta $02
    lda #S6Host_SlotTable&$FFFF
    sta $30
    lda #S6Host_SlotTable>>16
    sta $32
    lda #6
    sta $34
    rep #$30
    .a16
    .i16
    lda #1
    sta $40
    ; S6Clock_ClockAdvance uses the dedicated D=$1780 context.  Initialize
    ; its 32-bit NTSC rate there, not in the actor context that is about to be
    ; selected below.  21,477,270 = $0147B796 master clocks/second.
    lda #$1780
    tcd
    lda #$B796
    sta $08
    lda #$0147
    sta $0A
    lda #$0A00
    tcd
    lda #16
    sta CHAR_POS_X
    lda #176
    sta CHAR_POS_Y
    sep #$20
    .a8
    lda #S6Game_PlayerFacing
    sta CHAR_FACING_LEFT
    rep #$30
    .a16
    .i16
    lda #S6Game_Profile
    beq S6Game_PlayRender__p2
    jsl S6Host_BindExisting
S6Game_PlayRender__p2:
    .a16
    .i16
    lda.l G13_TwoPlayerEnabled
    and #255
    beq S6Game_PlayRender__await_spawn
    lda #$0A00+CHAR_ZP_LEN
    tcd
    lda #S6Game_Player2X
    sta CHAR_POS_X
    lda #176
    sta CHAR_POS_Y
    lda #S6Game_Profile
    beq S6Game_PlayRender__await_spawn
    jsl S6Host_BindExisting
S6Game_PlayRender__await_spawn:
    .a16
    .i16
    lda #S6Game_ExpectedBirths
    cmp #1
    beq S6Game_PlayRender__catalog_ready
    ; CPU-only concurrency fixture: choose the preloaded catalog identity
    ; for inactive slots. HP/existence and birth remain Spawn_Play-owned.
    ; This is NOT a media/residency or original stage-order certificate.
    ldx #CHAR_ZP_LEN*2
    sep #$20
    .a8
    lda #S6Game_EnemyRoster
S6Game_PlayRender__catalog_slot:
    .a8
    .i16
    sta.l $7E0A00+CHAR_ROSTER_INDEX,x
    rep #$20
    .a16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    sep #$20
    .a8
    lda #S6Game_EnemyRoster
    cpx #CHAR_ZP_LEN*6
    bcc S6Game_PlayRender__catalog_slot
    rep #$20
    .a16
S6Game_PlayRender__catalog_ready:
    ; The bounded actor fixture uses the source-valid zero-base environment.
    ; Clear per-slot base fractions left by the real stage loader so the
    ; bridge does not reject those slots as unsupported fractional altitude.
    rep #$30
    .a16
    .i16
    ldx #0
S6Game_PlayRender__clear_base_fraction:
    lda #0
    sta.l StageEnv_BaseFraction,x
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc S6Game_PlayRender__clear_base_fraction
    .a16
    .i16
    lda #2
    sta.l S6Host_Mode
    jmp S6Game_PlayRender__return
S6Game_PlayRender__tick:
    .a16
    .i16
    lda.l S6Game_Command
    cmp #2
    bne S6Game_PlayRender__no_remove
    lda #0
    sta.l S6Game_Command
    lda.l $7E1776
    jsl S6Host_RemoveHandle
S6Game_PlayRender__no_remove:
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #3
    bne S6Game_PlayRender__running
    lda.l Nmi_FrameCounter
    sta.l S6Game_LastField
    lda #S6Game_Profile
    bne S6Game_PlayRender__exact_start
    lda #5                   ; compatibility control: no source actor ticking
    bra S6Game_PlayRender__start_mode
S6Game_PlayRender__exact_start:
    .a16
    .i16
    lda #1
S6Game_PlayRender__start_mode:
    .a16
    .i16
    sta.l S6Host_Mode
    jmp S6Game_PlayRender__return
S6Game_PlayRender__running:
    .a16
    .i16
    cmp #1
    beq S6Game_PlayRender__check_error
    jmp S6Game_PlayRender__return
S6Game_PlayRender__check_error:
    .a16
    .i16
    lda.l S6Host_Error
    beq S6Game_PlayRender__measure
    jmp S6Game_PlayRender__return
S6Game_PlayRender__measure:
    ; Render-loop passes may repeat within one physical field. Advance source
    ; time only for newly committed NMI fields, and catch up every elapsed
    ; field if a busy pass crossed more than one boundary.
    .a16
    .i16
    lda.l Nmi_FrameCounter
    sec
    sbc.l S6Game_LastField
    ; Nmi_FrameCounter is an 8-bit monotonic field counter in production;
    ; discard the adjacent byte before using the elapsed-field count.
    and #$00FF
    bne S6Game_PlayRender__has_elapsed
    jmp S6Game_PlayRender__return
S6Game_PlayRender__has_elapsed:
    .a16
    .i16
    cmp #30
    bcc S6Game_PlayRender__field
    lda #16                  ; bounded catch-up domain, never silently skip time
    sta.l S6Host_Error
    bra S6Game_PlayRender__return
S6Game_PlayRender__field:
    .a16
    .i16
    sta.l $7E177A
    lda #S7Resident_Enabled
    sta.l S7Resident_Owner
    lda.l Nmi_FrameCounter
    sta.l S6Game_LastField
    ; Reconstruct preceding alternating NTSC fields, oldest first. This is
    ; elapsed clock batching, not permission to drop source scheduler ticks.
    lda.l $7E177A
    dec a
    and #1
    xba
    lsr a
    sta.l $7E177C
    sep #$20
    .a8
    lda $213F
    and #$80
    eor.l $7E177C
    sta.l $7E177C
    rep #$30
    .a16
    .i16
S6Game_PlayRender__elapsed_field:
    .a16
    .i16
    lda #$1780
    tcd
    lda #$99C0
    sta $00
    lda #$0442
    sta $02
    sep #$20
    .a8
    lda.l $7E177C
    and #$80
    beq S6Game_PlayRender__clock
    rep #$20
    .a16
    lda $00
    sec
    sbc #800
    sta $00
    lda $02
    sbc #0
    sta $02
S6Game_PlayRender__clock:
    rep #$30
    .a16
    .i16
    jsl S6Clock_ClockAdvance
    lda.l $7E177C
    eor #$80
    sta.l $7E177C
    lda.l $7E177A
    dec a
    sta.l $7E177A
    bne S6Game_PlayRender__elapsed_field
    jsl S7Resident_Flush
S6Game_PlayRender__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    jml Character_RenderPass

S6Clock_HostSourceTick:
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #1
    beq S6Clock_HostSourceTick__running
    brl S6Clock_HostSourceTick__done
S6Clock_HostSourceTick__running:
    lda $0C
    sta.l $7E173C
    lda $0E
    sta.l $7E173E
    jsl S6Host_Tick
    lda $0C
    sta.l S6Game_TickCommit
    ; Observer-only bounded stop, after the complete shared world pass.
    ; The source transition executes first; no actor state is manufactured.
    lda.l S6Host_HitEvents
    beq S6Clock_HostSourceTick__done
    lda.l $7E19E6+S6Game_StopSlot*256
    cmp #S6Game_StopDriver
    bne S6Clock_HostSourceTick__done
    lda #4
    sta.l S6Host_Mode
S6Clock_HostSourceTick__done:
    .a16
    .i16
    rtl

; Deterministic existence consumer, same real row as scheduler bridge.
S6Game_Alive:
    .a8
    .i16
    pha
    rep #$20
    .a16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    cmp #1
    beq S6Game_Alive__exact
    plx
    pla
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    beq S6Game_Alive__legacy_source
    jml S6Game_AliveResume
S6Game_Alive__legacy_source:
    .a8
    .i16
    jml ActorBehavior_EntityAlive__source
S6Game_Alive__exact:
    .a8
    .i16
    plx
    pla
    rep #$20
    .a16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    sep #$20
    .a8
    lda.l S6Bridge_Exists,x
    plx
    ora #0
    rtl

; X already selects an actual production row; original callers saved X.
S6Game_SlotBusy:
    .a8
    .i16
    lda.l S6Bridge_Policy,x
    cmp #1
    beq S6Game_SlotBusy__exact
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    jml S6Game_SlotBusyResume
S6Game_SlotBusy__exact:
    .a8
    .i16
    lda.l S6Bridge_Exists,x
    plx
    ora #0
    rtl

S6Game_CountSlot1:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN
    bra S6Game_CountSlot
S6Game_CountSlot2:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*2
    bra S6Game_CountSlot
S6Game_CountSlot3:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*3
    bra S6Game_CountSlot
S6Game_CountSlot4:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*4
    bra S6Game_CountSlot
S6Game_CountSlot5:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*5
S6Game_CountSlot:
    .a8
    .i16
    lda.l S6Bridge_Policy,x
    cmp #1
    beq S6Game_SlotBusy__exact
    lda.l $7E0A00+CHAR_HP,x
    plx
    ora #0
    rtl

S6Game_HudHealth:
    .a8
    .i16
    lda.l S6Bridge_Policy
    cmp #1
    bne S6Game_HudHealth__compat
    lda.l S6Bridge_Exists
    beq S6Game_HudHealth__done
    lda.l S6Bridge_DisplayedHealth
S6Game_HudHealth__done:
    .a8
    .i16
    rtl
S6Game_HudHealth__compat:
    .a8
    .i16
    lda.l PlayerEntity_Hp
    rtl

; Exact actors own their lifecycle in the shared source pass. Running the
; compatibility death service as well would stop the entire world when one
; player is OUT, or revive an exact absent slot before retargeting.
S6Game_DeathService:
    php
    rep #$30
    .a16
    .i16
    lda.l S6Bridge_Policy
    and #$00FF
    cmp #1
    bne S6Game_DeathService__compat
    lda.l S6Bridge_Policy+CHAR_ZP_LEN
    and #$00FF
    cmp #1
    bne S6Game_DeathService__compat
    plp
    clc
    rtl
S6Game_DeathService__compat:
    .a16
    .i16
    plp
    jml G13_HandleP2Death
