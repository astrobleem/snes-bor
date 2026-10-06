; S8 source timer and reset effect. Include in a bank with verified free space.
; Not connected to main/jump/spawn by this file. No implicit Easy activation.
; Source: BOR.C eba02fe6, SHA256 68c54a19...1735f41; timer_contract.py pins it.
;
; WRAM ownership: $7E5900..$7E591F (32 bytes), after Spawn_B2Hp=$7E58FF,
; before opponent HUD $7E5A00..$7E5ACF and VmCode_Wram=$7E6000.
; WramBuffer ends $7E4FFF; StageEnv's six
; 133-byte rows end $7E582C. No actor/queue/HUD arena is resized or overlaid.
; Public calls preserve P/X/Y/D/DBR, clobber A, except Display returns X.
; Input operands are A16/I16. Carry result explicitly documented per entry.
; Not reentrant; main thread only. All accesses long, independent of D/DBR.
;
; REQUIRED host labels (no default implementations):
; PlayerState -> A bits0/1=present P1/P2, Y bits0/1=has takedamage callback.
; DamagePlayer: X=player, A=1000, Y=drop1, type0, other=self. The source
; callback halves self-player force to 500 and owns unlink/toss/fall/death.
; EndGame: set source endgame, do NOT bypass damage/sound/reset below.
; Sound: A=1 get2, A=2 timeover, pitch100 and source effect volume.
; Collect: X=item slot,Y=collector; opponent=item,z=100000 equivalent
; exclusion/hide, getting=1, ANI_GET. Retain slot; no HP-zero/free shortcut.
; Retire: X=item slot; source suicide/kill including opponent cleanup.
; All hosts return A16/I16 and preserve X/Y/D/DBR (PlayerState returns Y).
; Host callbacks may call Reset100/PlayersAbsent; timeout resets LAST.
;
; Integration:
; 1. Stage_Load after stage/actor reset -> StartLevel (campaign id already set).
; 2. NmiField once EVERY NMI, including skipped commits. ClockService once
;    per main boundary, A=1 running/A=0 paused or non-gameplay. Service old
;    elapsed time BEFORE this boundary's input/collection/wait-reset events.
;    On pause/resume transitions sample with the OLD running state first;
;    keep sampling A=0 while paused. No paused backlog is replayed.
;    Explicit ACCEPTED_COMPAT adapter: nominal60 fields/sec, 10/3 timer
;    ticks/field, 5/3 gravity ticks/field. This is not PC PIT/NTSC exact time.
;    Missed main services are accounted using the unconditional counter.
;    Never use Nmi_FrameCounter (it excludes busy/skipped visual commits).
;    BeginTick/EndTick pair inside timer catch-up ONLY, no world reexecution.
;    TakeGravityTicks returns/drains 100Hz credit for bounds/gravity service.
; 3. Reset100 on wait-release, successful reentry, join start/confirmation.
;    PlayersAbsent(A=credits) ONLY on last-player removal transition.
; 4. Strict linked model-effect table -> ApplyEffect(A=id,X=slot,Y=collector).
;    id=6 is the new Normal pickup kind. Roster46 is a compiler binding, not
;    a runtime identity check. Legacy ApplyPickup A6 alone has no item slot:
;    capture slot at __vsN_dy_ok before TriggerGet/Audio_EmitPickup, or pass it
;    through an explicit context. Bypass that branch's immediate HP=0 tail.
;    Selected Normal Time requires the collector's attack edge, mapped from
;    source playkeys ATTACK; recognized denial returns handled, not fallback.
;    It must replace, not accompany, legacy overlap/free for this effect.
;    Reserve pending slots in spawn allocation. CancelSlot before external
;    kill/reuse. StartLevel clears the table after the old actors are gone.
; 5. Display -> A=00..99,X=show TIME OVER (snapshot before flag clear).
; Existing all-OUT grace/timeout handling must delegate in campaign3, else
; two independent countdowns can consume stock or end the game twice.

STAGE_TIMER_CAMPAIGN = 3
STAGE_TIMER_RESET = 40000
STAGE_TIMER_COUNTER_SPEED = 400
STAGE_TIMER_PICKUP_TICKS = 600
STAGE_TIMER_EFFECT_RESET = 6
StageTimer_Left = $7E5900             ; u16 source timeleft
StageTimer_ShowTimeOver = $7E5902     ; u16 boolean
StageTimer_InTick = $7E5904           ; u16 pair guard
StageTimer_Fault = $7E5906            ; u16 sticky:1 tick pair,2 slot/collector
StageTimer_Pending = $7E5908          ; six u16 suicide countdowns
StageTimer_FieldCounter = $7E5914    ; u16 unconditional NMI field count
StageTimer_LastField = $7E5916       ; u16 last clock sample, pause included
StageTimer_ClockPhase = $7E5918      ; u16 thirds of 200Hz tick (0..2 at rest)
StageTimer_GravityDue = $7E591A      ; u16 unconsumed 100Hz gravity credits
StageTimer_GravityPhase = $7E591C    ; u16 one half of 100Hz tick (0..1)
StageTimer_ClockWork = $7E591E       ; u16 outstanding fields in this service

StageTimer_StartLevel:
    php
    rep #$30
.a16
.i16
    phx
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_StartLevel__done
    lda #0
    ldx #30
StageTimer_StartLevel__clear:
.a16
.i16
    ; NMI owns FieldCounter. Never clear it from the main thread: an NMI
    ; between clear and snapshot must not lose a field or rewind the clock.
    cpx #20
    beq StageTimer_StartLevel__next
    sta.l StageTimer_Left,x
StageTimer_StartLevel__next:
.a16
.i16
    dex
    dex
    bpl StageTimer_StartLevel__clear
    lda #STAGE_TIMER_RESET
    sta.l StageTimer_Left
    lda.l StageTimer_FieldCounter
    sta.l StageTimer_LastField
StageTimer_StartLevel__done:
.a16
.i16
    plx
    plp
    rtl

; Source resets timeleft alone, not source time or display flag.
StageTimer_Reset100:
    php
    rep #$20
.a16
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_Reset100__done
    lda #STAGE_TIMER_RESET
    sta.l StageTimer_Left
StageTimer_Reset100__done:
.a16
    plp
    rtl

; A=remaining credits, last-player removal only; no recurring reset.
StageTimer_PlayersAbsent:
    php
    rep #$20
.a16
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_PlayersAbsent__skip
    pla
    beq StageTimer_PlayersAbsent__no_credit
    lda #4000
    bra StageTimer_PlayersAbsent__store
StageTimer_PlayersAbsent__no_credit:
.a16
    lda #200
StageTimer_PlayersAbsent__store:
.a16
    sta.l StageTimer_Left
    plp
    rtl
StageTimer_PlayersAbsent__skip:
.a16
    pla
    plp
    rtl

; C=1 consumed; C=0 delegate/reject. Repeat collection cannot refresh timer.
StageTimer_ApplyEffect:
    php
    rep #$30
.a16
.i16
    phx
    phy
    cmp #STAGE_TIMER_EFFECT_RESET
    bne StageTimer_ApplyEffect__no
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_ApplyEffect__no
    cpx #6
    bcs StageTimer_ApplyEffect__fault
    cpy #2
    bcs StageTimer_ApplyEffect__fault
    txa
    asl a
    tax
    lda.l StageTimer_Pending,x
    bne StageTimer_ApplyEffect__no
    lda #STAGE_TIMER_PICKUP_TICKS
    sta.l StageTimer_Pending,x
    txa
    lsr a
    tax
    jsl StageTimer_Reset100
    lda #1
    jsl StageTimerHost_Sound
    jsl StageTimerHost_Collect
    ply
    plx
    plp
    sec
    rtl
StageTimer_ApplyEffect__fault:
.a16
.i16
    lda #2
    sta.l StageTimer_Fault
StageTimer_ApplyEffect__no:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl

; X=slot; cancel only after kill cleanup or before deliberate slot reuse.
StageTimer_CancelSlot:
    php
    rep #$30
.a16
.i16
    phx
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_CancelSlot__done
    cpx #6
    bcs StageTimer_CancelSlot__fault
    txa
    asl a
    tax
    lda #0
    sta.l StageTimer_Pending,x
    bra StageTimer_CancelSlot__done
StageTimer_CancelSlot__fault:
.a16
.i16
    lda #2
    sta.l StageTimer_Fault
StageTimer_CancelSlot__done:
.a16
.i16
    plx
    plp
    rtl

; C=1 pair error; C=0 successful or inactive. Retire before actor thinkers.
StageTimer_BeginTick:
    php
    rep #$30
.a16
.i16
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_BeginTick__done
    lda.l StageTimer_InTick
    bne StageTimer_BeginTick__fault
    lda #1
    sta.l StageTimer_InTick
    ldx #0
StageTimer_BeginTick__slot:
.a16
.i16
    lda.l StageTimer_Pending,x
    beq StageTimer_BeginTick__next
    dec a
    sta.l StageTimer_Pending,x
    bne StageTimer_BeginTick__next
    phx
    txa
    lsr a
    tax
    jsl StageTimerHost_Retire
    plx
StageTimer_BeginTick__next:
.a16
.i16
    inx
    inx
    cpx #12
    bcc StageTimer_BeginTick__slot
StageTimer_BeginTick__done:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
StageTimer_BeginTick__fault:
.a16
.i16
    lda #1
    sta.l StageTimer_Fault
    ply
    plx
    plp
    sec
    rtl

; A=ingame. A tick reducing 1->0 does NOT time out; the next tick does.
StageTimer_EndTick:
    php
    rep #$30
.a16
.i16
    phx
    phy
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    beq StageTimer_EndTick__active
    pla
    jmp StageTimer_EndTick__done
StageTimer_EndTick__active:
.a16
.i16
    pla
    tay
    lda.l StageTimer_InTick
    cmp #1
    beq StageTimer_EndTick__paired
    lda #1
    sta.l StageTimer_Fault
    ply
    plx
    plp
    sec
    rtl
StageTimer_EndTick__paired:
.a16
.i16
    lda #0
    sta.l StageTimer_InTick
    tya
    bne StageTimer_EndTick__ingame
    jmp StageTimer_EndTick__done
StageTimer_EndTick__ingame:
.a16
.i16
    lda.l StageTimer_Left
    beq StageTimer_EndTick__timeout
    dec a
    sta.l StageTimer_Left
    jmp StageTimer_EndTick__done
StageTimer_EndTick__timeout:
.a16
.i16
    jsl StageTimerHost_PlayerState
    pha
    and #1
    bne StageTimer_EndTick__p1
    ; BOR.C: if(!player[0].ent && !player[0].ent) endgame=1;
    jsl StageTimerHost_EndGame
StageTimer_EndTick__p1:
.a16
.i16
    pla
    phy
    and 1,s
    ply
    and #1
    beq StageTimer_EndTick__p2
    ldx #0
    ldy #1
    lda #1000
    jsl StageTimerHost_DamagePlayer
StageTimer_EndTick__p2:
.a16
.i16
    ; Re-read after P1 callback, matching the sequential source ifs.
    jsl StageTimerHost_PlayerState
    phy
    and 1,s
    ply
    and #2
    beq StageTimer_EndTick__sound
    ldx #1
    ldy #1
    lda #1000
    jsl StageTimerHost_DamagePlayer
StageTimer_EndTick__sound:
.a16
.i16
    lda #2
    jsl StageTimerHost_Sound
    jsl StageTimer_Reset100
    lda #1
    sta.l StageTimer_ShowTimeOver
StageTimer_EndTick__done:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl

; A=displayed 00..99, X=message flag BEFORE source clears it for dt<99.
; C=1 active, C=0 inactive (A=0,X=0). Caller draws the snapshot once.
StageTimer_Display:
    php
    rep #$30
    cld
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_Display__inactive
    lda.l StageTimer_ShowTimeOver
    tax
    lda.l StageTimer_Left
    cmp #39600
    bcs StageTimer_Display__99
    lda #0
    sta.l StageTimer_ShowTimeOver
    phy
    ldy #0
    lda.l StageTimer_Left
StageTimer_Display__divide:
.a16
.i16
    cmp #STAGE_TIMER_COUNTER_SPEED
    bcc StageTimer_Display__value
    sec
    sbc #STAGE_TIMER_COUNTER_SPEED
    iny
    bra StageTimer_Display__divide
StageTimer_Display__value:
.a16
.i16
    tya
    ply
    bra StageTimer_Display__done
StageTimer_Display__99:
.a16
.i16
    lda #99
StageTimer_Display__done:
.a16
.i16
    plp
    sec
    rtl
StageTimer_Display__inactive:
.a16
.i16
    lda #0
    tax
    plp
    clc
    rtl

; Tiny mandatory NMI hook: after registers saved, outside visual-commit gate.
; Private counter only; no callbacks. Does not rely on DBR=0.
StageTimer_NmiField:
    php
    rep #$20
.a16
    pha
StageTimer_NmiField__after_save:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_NmiField__done
    lda.l StageTimer_FieldCounter
    inc a
    sta.l StageTimer_FieldCounter
StageTimer_NmiField__done:
.a16
    pla
    plp
    rtl

; A=running boolean. No world/AI reexecution, no discarded busy-field debt.
; C=1 fault (3=ambiguous >=32768 field gap,4=undrained gravity overflow).
; Clock must be initialized by StartLevel. Sample at least once per 32768
; fields (~9 minutes); unsigned counter wrap is supported within that bound.
StageTimer_ClockService:
    php
    rep #$30
.a16
.i16
    cld
    phx
    phy
    tay
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    beq StageTimer_ClockService__active
    jmp StageTimer_ClockService__done
StageTimer_ClockService__active:
.a16
.i16
    lda.l StageTimer_FieldCounter
    pha
    sec
    sbc.l StageTimer_LastField
    sta.l StageTimer_ClockWork
    pla
    sta.l StageTimer_LastField
    tya
    bne StageTimer_ClockService__running
    lda #0
    sta.l StageTimer_ClockWork
    jmp StageTimer_ClockService__done
StageTimer_ClockService__running:
.a16
.i16
    lda.l StageTimer_ClockWork
    bpl StageTimer_ClockService__field
    lda #3
    jmp StageTimer_ClockService__fault
StageTimer_ClockService__field:
.a16
.i16
    lda.l StageTimer_ClockWork
    bne StageTimer_ClockService__have_field
    jmp StageTimer_ClockService__done
StageTimer_ClockService__have_field:
.a16
.i16
    dec a
    sta.l StageTimer_ClockWork
    lda.l StageTimer_ClockPhase
    clc
    adc #10
    sta.l StageTimer_ClockPhase
StageTimer_ClockService__tick:
.a16
.i16
    lda.l StageTimer_ClockPhase
    cmp #3
    bcc StageTimer_ClockService__field
    sec
    sbc #3
    sta.l StageTimer_ClockPhase
    jsl StageTimer_BeginTick
    bcs StageTimer_ClockService__existing_fault
    lda #1
    jsl StageTimer_EndTick
    bcs StageTimer_ClockService__existing_fault
    lda.l StageTimer_GravityPhase
    eor #1
    sta.l StageTimer_GravityPhase
    bne StageTimer_ClockService__tick
    lda.l StageTimer_GravityDue
    cmp #$FFFF
    beq StageTimer_ClockService__overflow
    inc a
    sta.l StageTimer_GravityDue
    bra StageTimer_ClockService__tick
StageTimer_ClockService__overflow:
.a16
.i16
    lda #4
StageTimer_ClockService__fault:
.a16
.i16
    sta.l StageTimer_Fault
StageTimer_ClockService__existing_fault:
.a16
.i16
    ply
    plx
    plp
    sec
    rtl
StageTimer_ClockService__done:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl

; A=100Hz ticks since last drain, including main-service stalls; preserve X/Y.
StageTimer_TakeGravityTicks:
    php
    rep #$20
.a16
    lda.l Game_CampaignId
    and #$00FF
    cmp #STAGE_TIMER_CAMPAIGN
    bne StageTimer_TakeGravityTicks__inactive
    lda.l StageTimer_GravityDue
    pha
    lda #0
    sta.l StageTimer_GravityDue
    pla
    plp
    rtl
StageTimer_TakeGravityTicks__inactive:
.a16
    lda #0
    plp
    rtl
