; S8 concrete ACCEPTED_COMPAT host for stage_timer.pasm, campaign3 only.
; Include in ONE verified free ROM bank. No private WRAM beyond timer's
; reserved $7E5900..$7E591F, plus row ownership word $7E5920..$7E5921.
; HUD owns $7E5A00..$7E5ACF. Ownership survives timer/stage/campaign resets.
;
; Required NEW audio data binding (not a callback stub):
; STAGE_TIMER_TIMEOVER_SFX_ID = actual resident DATA/SOUNDS/TIMEOVER.WAV ID
; AUDIO_SEMANTIC_TIMEOVER = new generated semantic ID. MONEY is existing get2.
; Main/audio owner must encode/link that sample; no substitute/no-op is used.
;
; Normal Time requires the collector's attack edge (source playkeys ATTACK).
; Other pickups retain accepted overlap eligibility. Physical input ports
; are used outside actor ContextEnter; one edge can collect only one Time.
; source z=100000 exclusion becomes off-world coordinates plus pending mask.
; Render/collision/slot admission MUST consult IsPendingOffset until Retire.
; Fatal source self-damage 1000/2 exceeds target max64, so HP=0 enters the
; existing G13 fall/death/life-stock path. No direct life decrement/respawn.
; This is a semantic lethal-damage adapter, not source float physics.
;
; Main integration (no shared edits in this file):
; - Include timer and host in a free bank (all external calls are JSL).
; - NMI, before busy/visual-commit branch: JSL StageTimer_NmiField.
; - ClockService A=old running state before input/event processing, also on
;   paused/all-OUT boundaries. Pause entry/resume sample before changing mode.
; - ApplyPickup kind6: X MUST be physical item slot, then call
;   CollectFromOverlap. Better intercept __vsN_dy_ok before generic GET/audio
;   and HP-zero tail; set X=N, call, return immediately on handled carry.
;   Do not call the old reward/audio/free tail a second time.
; - All five spawn/reveal slot searches, render-alive and collision filters:
;   IsPendingOffset(X=physical byte offset), C=1 means occupied/hidden/inert.
; - On unrelated actual removal/reuse call CancelSlot before new ownership.
; - Last-player OUT transition: PlayersAbsent(A=Game_Credits), not per frame.
; - Existing all-out grace returns without its own decrement in campaign3.
; - Reset100 after successful respawn/join and wait release. Stage load uses
;   StartLevel after old actors are removed. Bounds drains TakeGravityTicks.

; Main integration: depth_sort.pasm's JSL Character_RenderFrame becomes
; JSL StageTimerHost_RenderFrame (same four bytes). Physical actor D retained.
; Pending Time must emit neither normal nor mirrored OAM. Non-source policies
; and other campaigns tail-call the unchanged renderer. Source-policy fall
; frames remain on the source-sized path even at zero HP. Entry A8, exit A16/I16.
StageTimerHost_RenderFrame:
    php
    rep #$30
    cld
.a16
.i16
    lda.l SourceVisual_HostCallCount
    inc a
    sta.l SourceVisual_HostCallCount
    pha
    phx
    tdc
    sta.l SourceVisual_HostLastD
    sep #$20
.a8
    lda CHAR_ROSTER_INDEX
    sta.l SourceVisual_HostLastRoster
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_HostLastPolicy
    ; Resolve the physical actor offset from the captured direct page. The
    ; policy diagnostic above is deliberately independent of this value.
    lda.l SourceVisual_HostLastD
    sec
    sbc #$0A00
    tax
    jsl StageTimerHost_IsPendingOffset
    bcs StageTimerHost_RenderFrame__skip
    ; Normal's production runtime is source-sized only.  Keep the accepted
    ; compatibility renderer for other campaigns, but never feed a missing
    ; or out-of-range Normal identity to the legacy animation loader (which
    ; can read arbitrary animation metadata and hang on the invalid roster).
    ; CampaignId is a byte immediately followed by CampaignOrdinal.  This
    ; routine is A16 here, so mask the loaded word before comparing; otherwise
    ; any nonzero ordinal silently selects the compatibility renderer.
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq StageTimerHost_RenderFrame__normal_campaign
    brl StageTimerHost_RenderFrame__compat
StageTimerHost_RenderFrame__normal_campaign:
    sep #$20
.a8
    lda #SOURCE_VISUAL_BUILD_ENABLED
    beq StageTimerHost_RenderFrame__normal_invalid
    lda CHAR_ROSTER_INDEX
    cmp #SOURCE_VISUAL_ROSTER_COUNT
    bcs StageTimerHost_RenderFrame__normal_invalid
    tax
    lda.l SourceVisual_RosterPolicy,x
    sta.l SourceVisual_HostLastPolicy
    cmp #VISUAL_POLICY_SOURCE_SIZED
    bne StageTimerHost_RenderFrame__normal_invalid
    rep #$31
.a16
.i16
    jsl SourceVisual_RenderCurrent
    bcs StageTimerHost_RenderFrame__source_done
    ; SOURCE_SIZED is fail-closed.  Never fall back to the fixed 32x48 ABI.
    jsl Core_Oam_HideRequest
    bra StageTimerHost_RenderFrame__source_done
StageTimerHost_RenderFrame__normal_invalid:
    sep #$20
.a8
    lda #$21
    sta.l SourceVisual_Error
    sta.l SourceVisual_DebugLastError
    rep #$31
.a16
.i16
    jsl Core_Oam_HideRequest
    bra StageTimerHost_RenderFrame__source_done
StageTimerHost_RenderFrame__compat:
    plx
    pla
    plp
    jml Character_RenderFrame
StageTimerHost_RenderFrame__source_done:
    plx
    pla
    plp
    rep #$31
.a16
.i16
    rtl
StageTimerHost_RenderFrame__skip:
.a16
.i16
    plx
    pla
    plp
    rep #$30
.a16
.i16
    rtl

StageTimerHost_Offsets:
    .dw 0, CHAR_ZP_LEN, CHAR_ZP_LEN*2, CHAR_ZP_LEN*3, CHAR_ZP_LEN*4, CHAR_ZP_LEN*5

; Internal: X=validated physical slot -> byte offset; A/X clobbered.
StageTimerHost_Offset:
.a16
.i16
    txa
    asl a
    tax
    lda.l StageTimerHost_Offsets,x
    tax
    rts

; C=enabled, preserve input A/X/Y/P except carry. Main thread, A16/I16.
StageTimerHost_Enabled:
    php
    rep #$20
.a16
    pha
    lda.l Game_CampaignId
    and #$FF
    cmp #3
    bne StageTimerHost_Enabled__no
    pla
    plp
    sec
    rtl
StageTimerHost_Enabled__no:
.a16
    pla
    plp
    clc
    rtl

; Presence follows entity existence/OUT, not HP; dying entities still exist.
StageTimerHost_PlayerState:
    php
    rep #$30
.a16
.i16
    phx
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_PlayerState__empty
    ldx #0
    lda.l G13_P1Out
    and #$FF
    bne StageTimerHost_PlayerState__p2
    inx
StageTimerHost_PlayerState__p2:
.a16
.i16
    lda.l G13_TwoPlayerEnabled
    and #$FF
    beq StageTimerHost_PlayerState__result
    lda.l G13_P2Out
    and #$FF
    bne StageTimerHost_PlayerState__result
    inx
    inx
StageTimerHost_PlayerState__result:
.a16
.i16
    txa
    tay
    plx
    plp
    rtl
StageTimerHost_PlayerState__empty:
.a16
.i16
    lda #0
    tay
    plx
    plp
    rtl

; Unlink both directions for a physical slot. Scans bounded six-slot ABI.
StageTimerHost_UnlinkSlot:
    php
    rep #$30
.a16
.i16
    phx
    phy
    txa
    pha
    ldx #0
StageTimerHost_UnlinkSlot__scan:
.a16
.i16
    lda.l $7E0A00+CHAR_GRAB_TARGET,x
    and #$FF
    cmp 1,s
    bne StageTimerHost_UnlinkSlot__grabbed
    sep #$20
.a8
    lda #$FF
    sta.l $7E0A00+CHAR_GRAB_TARGET,x
    rep #$20
.a16
StageTimerHost_UnlinkSlot__grabbed:
.a16
.i16
    lda.l $7E0A00+CHAR_GRABBED_BY,x
    and #$FF
    cmp 1,s
    bne StageTimerHost_UnlinkSlot__next
    sep #$20
.a8
    lda #$FF
    sta.l $7E0A00+CHAR_GRABBED_BY,x
    lda #0
    sta.l $7E0A00+CHAR_GRAB_TIMER,x
    rep #$20
.a16
StageTimerHost_UnlinkSlot__next:
.a16
.i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc StageTimerHost_UnlinkSlot__scan
    pla
    tax
    jsr StageTimerHost_Offset
    sep #$20
.a8
    lda #$FF
    sta.l $7E0A00+CHAR_GRAB_TARGET,x
    sta.l $7E0A00+CHAR_GRABBED_BY,x
    lda #0
    sta.l $7E0A00+CHAR_GRAB_TIMER,x
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

StageTimerHost_DamagePlayer:
    php
    rep #$30
.a16
.i16
    cld
    phx
    phy
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_DamagePlayer__done
    cpx #2
    bcs StageTimerHost_DamagePlayer__done
    jsl StageTimerHost_UnlinkSlot
    cpx #0
    bne StageTimerHost_DamagePlayer__p2
    sep #$20
.a8
    lda.l PlayerEntity_Hp
    beq StageTimerHost_DamagePlayer__done
    lda #0
    sta.l PlayerEntity_Hp
    sta.l PlayerEntity_Selected
    ; Force existing handler's fresh-fall entry, never consume stock inside
    ; timer catch-up because a prior nonlethal fall had a terminal marker.
    jsl G13_SourcePlayerDeathP1
    bra StageTimerHost_DamagePlayer__done
StageTimerHost_DamagePlayer__p2:
.a16
.i16
    sep #$20
.a8
    lda.l Entity1_Hp
    beq StageTimerHost_DamagePlayer__done
    lda #0
    sta.l Entity1_Hp
    sta.l Entity1_Selected
    jsl G13_SourcePlayerDeathP2
StageTimerHost_DamagePlayer__done:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

StageTimerHost_EndGame:
    php
    rep #$30
.a16
.i16
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_EndGame__done
    lda #BOR_GAME_OVER_DISPLAY_FRAMES
    sta.l GameOver_ContinueTimer
    lda #GAME_STATE_GAMEOVER
    sta.l Game_State
StageTimerHost_EndGame__done:
.a16
.i16
    plp
    rtl

StageTimerHost_Sound:
    php
    rep #$30
.a16
.i16
    phx
    phy
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_Sound__done
    cmp #1
    bne StageTimerHost_Sound__timeout
    sep #$20
.a8
    lda #AUDIO_SEMANTIC_MONEY
    ldx #SFX_MONEY_ID
    jsl Audio_QueueResidentSemantic
    bra StageTimerHost_Sound__done
StageTimerHost_Sound__timeout:
.a16
.i16
    cmp #2
    bne StageTimerHost_Sound__done
    sep #$20
.a8
    lda #AUDIO_SEMANTIC_TIMEOVER
    ldx #STAGE_TIMER_TIMEOVER_SFX_ID
    jsl Audio_QueueResidentSemantic
StageTimerHost_Sound__done:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

StageTimerHost_Collect:
    php
    rep #$30
.a16
.i16
    phx
    phy
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_Collect__done
    jsr StageTimerHost_Offset
    txa
    pha
    tya
    tax
    jsr StageTimerHost_Offset
    pla
    tay
    jsl HudOpponent_Target
    phy
    ; Collection has priority over the attack selected earlier this compat
    ; world pass. Source chooses ANI_GET inside its attack-input branch.
    sep #$20
.a8
    lda.l $7E0A00+CHAR_GET_FCOUNT,x
    beq StageTimerHost_Collect__hide
    lda #GET_MOVE_VARIANT
    sta.l $7E0A00+CHAR_ATTACK_VARIANT,x
    lda #2
    sta.l $7E0A00+CHAR_SELECTED,x
    lda #$FF
    sta.l $7E0A00+CHAR_FRAME_INDEX,x
    lda #1
    sta.l $7E0A00+CHAR_TICK_COUNTER,x
StageTimerHost_Collect__hide:
    rep #$30
.a16
.i16
    ply
    tyx
    lda #$7FFF
    sta.l $7E0A00+CHAR_POS_X,x
    sta.l $7E0A00+CHAR_POS_Y,x
    sep #$20
.a8
    lda #0
    sta.l $7E0A00+CHAR_PICKUP_TYPE,x
    ; HP stays live/occupied. Pending mask handles all semantic exclusion.
StageTimerHost_Collect__done:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

StageTimerHost_Retire:
    php
    rep #$30
.a16
.i16
    cld
    phx
    phy
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_Retire__done
    jsl StageTimer_CancelSlot
    jsl StageTimerHost_UnlinkSlot
    jsr StageTimerHost_Offset
    jsl HudOpponent_Remove
    sep #$20
.a8
    lda #0
    sta.l $7E0A00+CHAR_HP,x
    sta.l $7E0A00+CHAR_PICKUP_TYPE,x
    sta.l $7E0A00+CHAR_INPUT_DRIVEN,x
StageTimerHost_Retire__done:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

; X=physical slot from __vsN_dy_ok; ownership from existing pickup context.
; C=1 recognized/handled, NOT necessarily consumed. Ineligible Time and
; pending duplicates must NEVER delegate to legacy auto-GET/HP-zero tails.
; C=0 only for other campaigns/slots/items. Source BOR.C3460 consumes the
; attack playkey before pickup; compat maps that to the physical Y edge.
StageTimerHost_CollectFromOverlap:
    php
    rep #$30
.a16
.i16
    phx
    phy
    jsl StageTimerHost_Enabled
    bcs StageTimerHost_CollectFromOverlap__enabled
    jmp StageTimerHost_CollectFromOverlap__no
StageTimerHost_CollectFromOverlap__enabled:
.a16
.i16
    cpx #1
    bcs StageTimerHost_CollectFromOverlap__low_valid
    jmp StageTimerHost_CollectFromOverlap__no
StageTimerHost_CollectFromOverlap__low_valid:
.a16
.i16
    cpx #6
    bcc StageTimerHost_CollectFromOverlap__slot_valid
    jmp StageTimerHost_CollectFromOverlap__no
StageTimerHost_CollectFromOverlap__slot_valid:
.a16
.i16
    phx
    jsr StageTimerHost_Offset
    jsl StageTimerHost_IsPendingOffset
    bcc StageTimerHost_CollectFromOverlap__not_pending
    jmp StageTimerHost_CollectFromOverlap__handled_offset
StageTimerHost_CollectFromOverlap__not_pending:
.a16
.i16
    lda.l $7E0A00+CHAR_PICKUP_TYPE,x
    and #$FF
    cmp #6
    beq StageTimerHost_CollectFromOverlap__kind_valid
    jmp StageTimerHost_CollectFromOverlap__not_item
StageTimerHost_CollectFromOverlap__kind_valid:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$FF
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq StageTimerHost_CollectFromOverlap__prop_valid
    jmp StageTimerHost_CollectFromOverlap__not_item
StageTimerHost_CollectFromOverlap__prop_valid:
.a16
.i16
    plx
    lda.l G13_PickupForP2
    and #$FF
    tay
    beq StageTimerHost_CollectFromOverlap__p1_input
    cmp #1
    bne StageTimerHost_CollectFromOverlap__handled
    lda.l Input2_trigger_Addr
    bra StageTimerHost_CollectFromOverlap__input
StageTimerHost_CollectFromOverlap__p1_input:
.a16
.i16
    lda.l Input_trigger_Addr
StageTimerHost_CollectFromOverlap__input:
.a16
.i16
    and #ANIM_ATTACK_BUTTON_MASK << 8
    beq StageTimerHost_CollectFromOverlap__handled
    lda #6
    jsl StageTimer_ApplyEffect
    bcc StageTimerHost_CollectFromOverlap__handled
    ; Consume only the collector's attack edge, preserving other input bits.
    cpy #0
    beq StageTimerHost_CollectFromOverlap__consume_p1
    lda.l Input2_trigger_Addr
    and #$FFFF ^ (ANIM_ATTACK_BUTTON_MASK << 8)
    sta.l Input2_trigger_Addr
    bra StageTimerHost_CollectFromOverlap__handled
StageTimerHost_CollectFromOverlap__consume_p1:
.a16
.i16
    lda.l Input_trigger_Addr
    and #$FFFF ^ (ANIM_ATTACK_BUTTON_MASK << 8)
    sta.l Input_trigger_Addr
StageTimerHost_CollectFromOverlap__handled:
.a16
.i16
    ply
    plx
    plp
    sec
    rtl
StageTimerHost_CollectFromOverlap__handled_offset:
.a16
.i16
    plx
    bra StageTimerHost_CollectFromOverlap__handled
StageTimerHost_CollectFromOverlap__not_item:
.a16
.i16
    plx
StageTimerHost_CollectFromOverlap__no:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl

; X=physical actor byte offset (NOT slot index). C1=A1 pending; C0=A0 not.
; Preserve X/Y/P except carry, accepts either accumulator width.
StageTimerHost_IsPendingOffset:
    php
    rep #$30
.a16
.i16
    phx
    phy
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_IsPendingOffset__no
    txy
    ldx #0
StageTimerHost_IsPendingOffset__find:
.a16
.i16
    tya
    cmp.l StageTimerHost_Offsets,x
    beq StageTimerHost_IsPendingOffset__found
    inx
    inx
    cpx #12
    bcc StageTimerHost_IsPendingOffset__find
    bra StageTimerHost_IsPendingOffset__no
StageTimerHost_IsPendingOffset__found:
.a16
.i16
    lda.l StageTimer_Pending,x
    beq StageTimerHost_IsPendingOffset__no
    lda #1
    ply
    plx
    plp
    sec
    rtl
StageTimerHost_IsPendingOffset__no:
.a16
.i16
    lda #0
    ply
    plx
    plp
    clc
    rtl

; Same-size replacements for Spawn_Play's five occupancy queries. A8/Z
; result and X preservation match ActorBehavior_SlotNBusy exactly.
StageTimerHost_Slot1Busy:
.a8
.i16
    phx
    ldx #CHAR_ZP_LEN
    bra StageTimerHost_SlotBusy
StageTimerHost_Slot2Busy:
.a8
.i16
    phx
    ldx #CHAR_ZP_LEN*2
    bra StageTimerHost_SlotBusy
StageTimerHost_Slot3Busy:
.a8
.i16
    phx
    ldx #CHAR_ZP_LEN*3
    bra StageTimerHost_SlotBusy
StageTimerHost_Slot4Busy:
.a8
.i16
    phx
    ldx #CHAR_ZP_LEN*4
    bra StageTimerHost_SlotBusy
StageTimerHost_Slot5Busy:
.a8
.i16
    phx
    ldx #CHAR_ZP_LEN*5
StageTimerHost_SlotBusy:
.a8
.i16
    jsl StageTimerHost_IsPendingOffset
    bcc StageTimerHost_SlotBusy__legacy
    plx
    lda #1
    rtl
StageTimerHost_SlotBusy__legacy:
.a8
.i16
    ; Original common tail consumes the PHX above and returns A8/Z.
    jml ActorBehavior_SlotBusy

; Overlap hooks preserve entry width; returning C1 skips old GET/audio/free.
StageTimerHost_CollectSlot1:
    php
    rep #$30
.a16
.i16
    ldx #1
    bra StageTimerHost_CollectSlot
StageTimerHost_CollectSlot2:
    php
    rep #$30
.a16
.i16
    ldx #2
    bra StageTimerHost_CollectSlot
StageTimerHost_CollectSlot3:
    php
    rep #$30
.a16
.i16
    ldx #3
    bra StageTimerHost_CollectSlot
StageTimerHost_CollectSlot4:
    php
    rep #$30
.a16
.i16
    ldx #4
    bra StageTimerHost_CollectSlot
StageTimerHost_CollectSlot5:
    php
    rep #$30
.a16
.i16
    ldx #5
StageTimerHost_CollectSlot:
.a16
.i16
    jsl StageTimerHost_CollectFromOverlap
    bcc StageTimerHost_CollectSlot__no
    plp
    sec
    rtl
StageTimerHost_CollectSlot__no:
.a16
.i16
    plp
    clc
    rtl

; Main state boundary: gameplay, including all-OUT credit grace, runs clock.
; Paused/scenes/menus consume elapsed fields without advancing simulation.
StageTimerHost_FrameService:
    php
    rep #$30
.a16
.i16
    phx
    phy
    lda.l Game_State
    cmp #GAME_STATE_PLAYING
    beq StageTimerHost_FrameService__running
    lda #0
    bra StageTimerHost_FrameService__service
StageTimerHost_FrameService__running:
.a16
.i16
    lda #1
StageTimerHost_FrameService__service:
.a16
.i16
    jsl StageTimer_ClockService
    bcc StageTimerHost_FrameService__done
    ; Sticky fault is visible and gameplay stops. Never silently lose debt.
    lda #GAME_STATE_PAUSED
    sta.l Game_State
StageTimerHost_FrameService__done:
.a16
.i16
    jsl StageTimerHost_DrawTimer
    ply
    plx
    plp
    rtl

StageTimerHost_HandleContinue:
    php
    rep #$30
.a16
.i16
    jsl G13_HandleOutContinue
    bcc StageTimerHost_HandleContinue__no
    jsl StageTimer_Reset100
    plp
    sec
    rtl
StageTimerHost_HandleContinue__no:
.a16
.i16
    plp
    clc
    rtl

; Snapshot lifecycle around existing handler, without editing its shared file.
; Reset only a player's actual stock-consuming reentry, not partner OUT.
StageTimerHost_ServiceDeaths:
    php
    rep #$30
.a16
.i16
    phx
    phy
    jsl StageTimerHost_Enabled
    bcs StageTimerHost_ServiceDeaths__normal
    ply
    plx
    plp
    jml G13_HandleP2Death
StageTimerHost_ServiceDeaths__normal:
.a16
.i16
    lda.l Game_Lives
    pha
    lda.l G13_P2Lives
    pha
    jsl StageTimerHost_PlayerState
    pha
    jsl G13_HandleP2Death
    php
    rep #$30
.a16
.i16
    jsl StageTimerHost_PlayerState
    tax
    bne StageTimerHost_ServiceDeaths__present
    lda 2,s
    beq StageTimerHost_ServiceDeaths__restore
    lda.l Game_Credits
    and #$FF
    jsl StageTimer_PlayersAbsent
    bra StageTimerHost_ServiceDeaths__restore
StageTimerHost_ServiceDeaths__present:
.a16
.i16
    txa
    and #1
    beq StageTimerHost_ServiceDeaths__p2
    lda.l Game_Lives
    cmp 6,s
    bne StageTimerHost_ServiceDeaths__reset
StageTimerHost_ServiceDeaths__p2:
.a16
.i16
    txa
    and #2
    beq StageTimerHost_ServiceDeaths__restore
    lda.l G13_P2Lives
    cmp 4,s
    beq StageTimerHost_ServiceDeaths__restore
StageTimerHost_ServiceDeaths__reset:
.a16
.i16
    jsl StageTimer_Reset100
StageTimerHost_ServiceDeaths__restore:
.a16
.i16
    plp
    pla
    pla
    pla
    bcs StageTimerHost_ServiceDeaths__handled
    ply
    plx
    plp
    clc
    rtl
StageTimerHost_ServiceDeaths__handled:
.a16
.i16
    ply
    plx
    plp
    sec
    rtl

StageTimerHost_CheckAllOut:
    jsl StageTimerHost_Enabled
    bcc StageTimerHost_CheckAllOut__legacy
    clc
    rtl
StageTimerHost_CheckAllOut__legacy:
    jml Game_State_Play__check_all_out

; Same target walk/score tail as accepted caller, with selected-Normal Time
; and pending consumed items excluded BEFORE damage/grab/score side effects.
StageTimerHost_VsAllGeneric:
    php
    rep #$31
.a16
.i16
    jsl StageTimerHost_Enabled
    bcs StageTimerHost_VsAllGeneric__normal
    plp
    jml Character_HitApply_VsAllGeneric
StageTimerHost_VsAllGeneric__normal:
.a16
.i16
    lda #0
    sta.l VmNativeEng_ScanIndex
StageTimerHost_VsAllGeneric__loop:
.a16
.i16
    lda.l G13_TwoPlayerEnabled
    beq StageTimerHost_VsAllGeneric__target
    lda.l VmNativeEng_ScanIndex
    bne StageTimerHost_VsAllGeneric__target
    jmp StageTimerHost_VsAllGeneric__next
StageTimerHost_VsAllGeneric__target:
.a16
.i16
    lda.l VmNativeEng_ScanIndex
    tax
    lsr a
    inc a
    sta.l HitApply_TargetIndex
    lda.l Character_ActorTargetOffsets,x
    tax
    jsl StageTimerHost_IsPendingOffset
    bcs StageTimerHost_VsAllGeneric__next
    lda.l $7E0A00+CHAR_PICKUP_TYPE,x
    and #$FF
    cmp #6
    beq StageTimerHost_VsAllGeneric__next
    jsl Character_HitApply_VsEntityGeneric
.a8
    bcc StageTimerHost_VsAllGeneric__next
    jsl Character_HitApply__ScoreAndFinish_Long
    rep #$31
.a16
.i16
    lda.l HitApply_EntityBase
    tax
    sep #$20
.a8
    lda.l $7E0A00+CHAR_HP,x
    bne StageTimerHost_VsAllGeneric__next
    jsl Character_HitApply__RevealOrPickup
StageTimerHost_VsAllGeneric__next:
    rep #$31
.a16
.i16
    lda.l VmNativeEng_ScanIndex
    inc a
    inc a
    sta.l VmNativeEng_ScanIndex
    cmp #(CHARACTER_ACTOR_COUNT-1)*2
    bcs StageTimerHost_VsAllGeneric__done
    jmp StageTimerHost_VsAllGeneric__loop
StageTimerHost_VsAllGeneric__done:
.a16
.i16
    plp
    rtl


; Normal countdown presentation. Row11 cols11..19 is outside player rows
; 0..3/7..9, demo4..5, opponent6/10, frontpanel21..27.
; Dedicated ownership word in audited gap after timer32B, before HUD5A00.
; Cold INTRO (only entered by boot, whose BG3 is cleared) initializes it.
; StageTimer_StartLevel never clears it. Successful cleanup enqueue releases
; ownership; rejection retains it even if campaign changes to Easy.
StageTimerHost_RowOwned = $7E5920 ; u16: 0 never owned/cleanup queued,1 owned
; Immutable ROM rows avoid TextStaging aliasing and pending-source mutation.
; One 18-byte queue request per playing boundary; full queue retries next
; boundary. Source Display supplies the timeout snapshot before flag clear.
; Font uses the existing initialized BG3 font and palette. Bank16 owner.
StageTimerHost_DrawTimer:
    php
    rep #$30
    cld
.a16
.i16
    pha
    phx
    phy
    lda.l Game_State
    cmp #GAME_STATE_INTRO
    bne StageTimerHost_DrawTimer__initialized
    lda #0
    sta.l StageTimerHost_RowOwned
    jmp StageTimerHost_DrawTimer__done
StageTimerHost_DrawTimer__initialized:
.a16
.i16
    ; Drain earlier timer/blank transfers before replacing this destination.
    ; Queue is not a FIFO when slots wrap: never allow stale draw after clear.
    ldx #0
StageTimerHost_DrawTimer__pending:
.a16
.i16
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    beq StageTimerHost_DrawTimer__next_dma
    lda.l DmaQueue+2,x
    cmp #(BG3_TILEMAP_VRAM_WORD + 11*TEXT_ROW_ENTRIES + 11)*2
    bne StageTimerHost_DrawTimer__next_dma
    jmp StageTimerHost_DrawTimer__done
StageTimerHost_DrawTimer__next_dma:
.a16
.i16
    txa
    clc
    adc #DMA_QUEUE_SLOT_SIZE
    tax
    cpx #DMA_QUEUE_SLOTS*DMA_QUEUE_SLOT_SIZE
    bcc StageTimerHost_DrawTimer__pending
    lda.l Game_CampaignId
    and #$FF
    cmp #3
    beq StageTimerHost_DrawTimer__normal
    jmp StageTimerHost_DrawTimer__cleanup
StageTimerHost_DrawTimer__normal:
.a16
.i16
    lda.l Game_State
    cmp #GAME_STATE_PLAYING
    beq StageTimerHost_DrawTimer__playing
    jmp StageTimerHost_DrawTimer__cleanup
StageTimerHost_DrawTimer__playing:
.a16
.i16
    lda.l StageTimer_ShowTimeOver
    pha
    jsl StageTimer_Display
    cpx #0
    bne StageTimerHost_DrawTimer__timeout
    ; A=count 0..99; row stride18 = count*16 + count*2.
    asl a
    pha
    asl a
    asl a
    asl a
    clc
    adc 1,s
    plx
    clc
    adc #StageTimerHost_TimerRows
    bra StageTimerHost_DrawTimer__queue
StageTimerHost_DrawTimer__timeout:
.a16
.i16
    lda #StageTimerHost_TimeOverRow
StageTimerHost_DrawTimer__queue:
.a16
.i16
    jsr StageTimerHost_QueueRow
    bcs StageTimerHost_DrawTimer__accepted
    ; Display clears the flag after its snapshot. A rejected DMA must not
    ; consume the last visible TIME OVER presentation; retry next boundary.
    pla
    sta.l StageTimer_ShowTimeOver
    bra StageTimerHost_DrawTimer__done
StageTimerHost_DrawTimer__accepted:
.a16
.i16
    pla
    lda #1
    sta.l StageTimerHost_RowOwned
StageTimerHost_DrawTimer__done:
    rep #$30
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

StageTimerHost_DrawTimer__cleanup:
.a16
.i16
    lda.l StageTimerHost_RowOwned
    beq StageTimerHost_DrawTimer__done
    lda #StageTimerHost_BlankRow
    jsr StageTimerHost_QueueRow
    bcc StageTimerHost_DrawTimer__done
    lda #0
    sta.l StageTimerHost_RowOwned
    bra StageTimerHost_DrawTimer__done

; Private A16/I16, A=immutable bank16 source low address; returns enqueue C.
StageTimerHost_QueueRow:
.a16
.i16
    sta.l DmaRequest_SourceAddrLow
    lda #(BG3_TILEMAP_VRAM_WORD + 11*TEXT_ROW_ENTRIES + 11)*2
    sta.l DmaRequest_TargetAddr
    lda #18
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #$10
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$30
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    rts

StageTimerHost_BlankRow:
    .dw 0,0,0,0,0,0,0,0,0

; Nine glyphs each, including trailing blanks to erase TIME OVER.
; Existing font tile index = FONT_TILE_INDEX_BASE + ASCII - 32;
; Match the FULL Text_EmitGlyph owner expression: HUD priority plus font
; palette1. Current combined flags are $2400, not priority-only $2000.
StageTimerHost_TimerRows:
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+16+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+17+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+18+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+19+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+20+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+21+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+22+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+23+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+24+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+25+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
StageTimerHost_TimeOverRow:
    .dw FONT_TILE_INDEX_BASE+52+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+41+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+45+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+0+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+47+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+54+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+37+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400)),FONT_TILE_INDEX_BASE+50+((HUD_ENTRY_HIGH*$100)|(FONT_CGRAM_PAL_ID*$0400))
