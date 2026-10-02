; ============================================================================
; G15 L3A -- bounded BOR scene-video frame loader.
;
; This is deliberately a single-frame test seam, not the eventual movie
; player. It consumes the generated BORVID1 metadata and the relocatable
; Rugal payload, stages one validated frame in the borrowed VM-tail WRAM
; region, and queues three ordinary BOR DMA transfers. Gameplay is bypassed
; while the test frame is active. No timing, audio, skip, or campaign logic
; belongs here yet.
; ============================================================================

SCENE_VIDEO_REQUEST_START = 1
SCENE_VIDEO_REQUEST_STOP  = 2
SCENE_VIDEO_ACTIVE_MARKER = $A5
SCENE_VIDEO_RUGAL_ID      = 1
SCENE_VIDEO_BG1SC         = $60       ; 32x32 map at VRAM word $6000
SCENE_VIDEO_BG12NBA       = $20       ; BG1 4bpp tiles at VRAM word $0000
SCENE_VIDEO_MAP_DMA_BYTES = $0800     ; complete 32x32 map, not packed 32x24
SCENE_VIDEO_BLANK_TILE_BYTES = 32
SCENE_VIDEO_TILE_VRAM_BYTE = $0000
SCENE_VIDEO_MAP_VRAM_BYTE  = $C000
SCENE_VIDEO_CGRAM_BYTE     = $0000
SCENE_VIDEO_TILE_VRAM_BYTE_B = $4000
SCENE_VIDEO_MAP_VRAM_BYTE_B  = $C800
SCENE_VIDEO_BG1SC_B           = $64
SCENE_VIDEO_BG12NBA_B         = $22
SCENE_VIDEO_PLAY_LOADING      = 1
SCENE_VIDEO_PLAY_READY        = 2
SCENE_CONTINUE_TITLE          = 0
SCENE_CONTINUE_CAMPAIGN       = 1

; A is a generated scene ID and X is the continuation selector. This request
; deliberately leaves Game_StatePrev to the normal state machinery.
SceneVideo_Request:
    php
    rep #$31
.a16
.i16
    sep #$20
.a8
    sta.l SceneVideo_RequestedSceneId
    txa
    sta.l SceneVideo_Continuation
    sep #$20
.a8
    lda #SCENE_VIDEO_REQUEST_START
    sta.l SceneVideo_TestRequest
    rep #$31
.a16
.i16
    lda #0
    sta.l SceneVideo_TestRequest+1
    rep #$31
.a16
.i16
    lda #GAME_STATE_SCENE_FRAME
    sta.l Game_State
    plp
    rtl

; Resolve one generated authored-scene record and its first clip. Scene IDs
; and clip IDs are data-driven; the playback loop never names a particular
; scene or animation.
SceneVideo_ResolveSequence:
    php
    rep #$31
.a16
.i16
    lda.l SceneVideo_RequestedSceneId
    and #$00FF
    beq SceneVideo_ResolveSequence__bad
    dec a
    tax
    cpx #SceneSequence_Count
    bcs SceneVideo_ResolveSequence__bad
    sep #$20
.a8
    lda.l SceneVideo_RequestedSceneId
    sta.l SceneVideo_SequenceSceneId
    lda.l SceneSequence_ClipCounts,x
    sta.l SceneVideo_SequenceClipCount
    rep #$31
.a16
.i16
    and #$00FF
    sta.l SceneVideo_SequenceClipCount16
    sep #$20
.a8
    rep #$31
.a16
.i16
    txa
    asl a
    tax
    lda.l SceneSequence_ClipOffsets,x
    sta.l SceneVideo_SequenceClipOffset
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_SequenceClipOrdinal
    rep #$31
.a16
.i16
    lda.l SceneVideo_SequenceClipOffset
    tax
    sep #$20
.a8
    lda.l SceneSequence_ClipIds,x
    sta.l SceneVideo_SequenceClipId
    plp
    sec
    rts
SceneVideo_ResolveSequence__bad:
    plp
    clc
    rts

; ----------------------------------------------------------------------
; Test request service. Carry set means the caller must bypass ordinary game
; state dispatch for this iteration. The request is intentionally external
; test control; no campaign path writes it.
; ----------------------------------------------------------------------
SceneVideo_TestService:
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda.l SceneVideo_TestActive
    cmp #SCENE_VIDEO_ACTIVE_MARKER
    bne SceneVideo_TestService__clear_inactive
    brl SceneVideo_TestService__active
SceneVideo_TestService__clear_inactive:
    nop
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_TestActive
SceneVideo_TestService__not_active:
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestRequest
    cmp #SCENE_VIDEO_REQUEST_START
    beq SceneVideo_TestService__start
    brl SceneVideo_TestService__idle
SceneVideo_TestService__start:
    nop
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestRequestSeen
    inc a
    sta.l SceneVideo_TestRequestSeen
    lda.l SceneVideo_TestRequestConsumed
    inc a
    sta.l SceneVideo_TestRequestConsumed
    lda #0
    sta.l SceneVideo_TestRequest
    sta.l SceneVideo_TestFrameIndex
    sta.l SceneVideo_TestBuffer
    lda #1
    sta.l SceneVideo_TestQueuePalette
    sep #$20
.a8
    lda.l SceneVideo_RequestedSceneId
    bne SceneVideo_TestService__scene_selected
    lda #SceneVideo_Rugal
    sta.l SceneVideo_RequestedSceneId
SceneVideo_TestService__scene_selected:
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_SkipPending
    jsr SceneVideo_ResolveSequence
    bcs SceneVideo_TestService__sequence_ok
    brl SceneVideo_TestService__load_failed
SceneVideo_TestService__sequence_ok:
    jsr SceneVideo_LoadFrame
    bcs SceneVideo_TestService__initial_load_ok
    brl SceneVideo_TestService__load_failed
SceneVideo_TestService__initial_load_ok:
    nop
    ; LoadFrame brackets its MSU read with NMI/auto-joypad disabled.  The
    ; scene owns that protection only for the read; restore the normal BOR
    ; frame/input service before entering the active playback state.
    sep #$20
.a8
    lda #$81
    sta $4200
    sep #$20
.a8
    lda #SCENE_VIDEO_ACTIVE_MARKER
    sta.l SceneVideo_TestActive
    lda #1
    sta.l SceneVideo_SequenceActive
    ; Frame zero is visible after the first NMI commit. Start the playback
    ; clock here, after the proven L3A load has been queued.
    rep #$31
.a16
.i16
    lda #0
    sta.l SceneVideo_TestFrameIndex
    sta.l SceneVideo_PlayPresented
    sta.l SceneVideo_PlaySwaps
    sta.l SceneVideo_PlayReadyCount
    sta.l SceneVideo_PlayLateCount
    sta.l SceneVideo_PlayDmaRetries
    sta.l SceneVideo_PlayMaxDmaBytes
    sta.l SceneVideo_PlayElapsedTicks
    sta.l SceneVideo_PlayCompletion
    sta.l SceneVideo_PlayDmaBytes
    sta.l SceneVideo_PlayAudioEnded
    sta.l SceneVideo_PlayAudioStops
    sta.l SceneVideo_PlaySkipCount
    sta.l SceneVideo_PlayAudioRepeat
    sta.l SceneVideo_PlayAudioStartCount
    sta.l SceneVideo_SequenceTransitions
    sta.l SceneVideo_SequenceAudioStarts
    sta.l SceneVideo_SequenceCompletion
    sta.l SceneVideo_SequenceSkipCount
    sta.l SceneVideo_InputPollCount
    sta.l SceneVideo_LoadCount
    sta.l SceneVideo_LoadStartNmi
    sta.l SceneVideo_LoadEndNmi
    sta.l SceneVideo_LoadCheckpoints
    sta.l SceneVideo_InputRawAtSkip
    sta.l SceneVideo_InputPressAtSkip
    sta.l SceneVideo_InputTriggerAtSkip
    sta.l SceneVideo_PlaySkipSwaps
    lda.l Nmi_FrameCounter
    sta.l SceneVideo_PlayLastNmi
    ; Source music begins on the same scene-start transition as frame zero.
    rep #$31
.a16
.i16
    lda.l SceneVideo_SequenceSceneId
    and #$00FF
    jsl Music_SelectSceneTrack_Long
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_PlayAccumulator
    sta.l SceneVideo_PlayDue
    sta.l SceneVideo_TestBuffer
    sta.l SceneVideo_SequenceTimingAccum
    rep #$31
.a16
.i16
    sta.l SceneVideo_PlayVisible
    sta.l SceneVideo_PlayNext
    sta.l SceneVideo_PlayLastFrame
    sta.l SceneVideo_PlayTimingPhase
    sta.l SceneVideo_PlayTimingPhase+2
    sep #$20
.a8
    lda #1
    rep #$31
.a16
.i16
    sta.l SceneVideo_PlayNext
    sep #$20
.a8
    lda #0
    rep #$31
.a16
.i16
    sta.l SceneVideo_PlayLastFrame
    sep #$20
.a8
    sta.l SceneVideo_SkipPending
    sta.l SceneVideo_LoadCheckpointCounter
    ; Frame 0 is already queued in buffer A. The first frame handler iteration
    ; begins the hidden frame-1 load after that queue has crossed an NMI.
    lda #0
    sta.l SceneVideo_TestFrameIndex
    sta.l SceneVideo_TestBuffer
    lda #1
    sta.l SceneVideo_TestQueuePalette
    ; The first frame's queue is drained by the next NMI. The frame handler
    ; then starts the first hidden load, avoiding two frame-sized staging
    ; batches competing for the initial DMA queue.
    lda #0
    sta.l SceneVideo_PlayState
    rep #$31
.a16
.i16
    lda #1
    sta.l SceneVideo_PlayPresented
    rep #$31
.a16
.i16
    lda #GAME_STATE_SCENE_FRAME
    sta.l Game_State
    sec
    rtl
SceneVideo_TestService__active:
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestRequest
    cmp #SCENE_VIDEO_REQUEST_STOP
    bne SceneVideo_TestService__hold
    jsr SceneVideo_StopFrameTest
    clc
    rtl
SceneVideo_TestService__hold:
    sec
    rtl
SceneVideo_TestService__load_failed:
    clc
    rtl
SceneVideo_TestService__idle:
    clc
    rtl

; ----------------------------------------------------------------------
; MSU-1 absolute seek. Scene offsets are 32-bit in metadata, but the MSU
; address port consumes the low 24 bits; the source payload is far below the
; 16MB MSU address limit. Entry/exit is .a16/.i16.
; ----------------------------------------------------------------------
SceneVideo_FrameTestHandler:
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda.l SceneVideo_TestActive
    cmp #SCENE_VIDEO_ACTIVE_MARKER
    beq SceneVideo_FrameTestHandler__service_done
    jsl SceneVideo_TestService
SceneVideo_FrameTestHandler__service_done:
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestHandlerEntries
    inc a
    sta.l SceneVideo_TestHandlerEntries
    sep #$20
.a8
    lda.l SceneVideo_TestActive
    cmp #SCENE_VIDEO_ACTIVE_MARKER
    beq SceneVideo_FrameTestHandler__active
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__active:
    nop
    ; Consume an edge already produced by the ordinary global poll before the
    ; hidden load begins; ServiceInput covers edges arriving inside the load.
    jsr SceneVideo_LatchInputEdge
    ; The handler owns the one shared cleanup path.
    sep #$20
.a8
    lda.l SceneVideo_SkipPending
    beq SceneVideo_FrameTestHandler__no_skip
    lda.l SceneVideo_PlaySkipCount
    inc a
    sta.l SceneVideo_PlaySkipCount
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlaySwaps
    sta.l SceneVideo_PlaySkipSwaps
    jsl Music_StopSceneTrack_Long
    jsr SceneVideo_StopFrameTest
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__no_skip:
    ; MSU-1 status bit 7 reports audio playback.  Video completion remains
    ; independent when this non-looping scene track ends first.
    sep #$20
.a8
    lda.l Music_PlayState
    beq SceneVideo_FrameTestHandler__audio_checked
    lda $2000
    bmi SceneVideo_FrameTestHandler__audio_checked
    lda #0
    sta.l Music_PlayState
    lda #1
    sta.l SceneVideo_PlayAudioEnded
SceneVideo_FrameTestHandler__audio_checked:
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayElapsedTicks
    inc a
    sta.l SceneVideo_PlayElapsedTicks

    ; A hidden map/tile upload owns the single WRAM staging buffer until every
    ; queued DMA has been drained by NMI. Only then may it be reused.
    sep #$20
.a8
    lda.l SceneVideo_PlayState
    cmp #SCENE_VIDEO_PLAY_LOADING
    bne SceneVideo_FrameTestHandler__not_loading
    ; Core_Nmi_Play drains this isolated scene's queued transfers before the
    ; next main-loop iteration. The scene handler is reached only after that
    ; NMI boundary, so this is the explicit commit-after-confirm point.
    sec
    bcs SceneVideo_FrameTestHandler__loading_ready
SceneVideo_FrameTestHandler__loading_ready:
    nop
    sep #$20
.a8
    lda #SCENE_VIDEO_PLAY_READY
    sta.l SceneVideo_PlayState
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayReadyCount
    inc a
    sta.l SceneVideo_PlayReadyCount
SceneVideo_FrameTestHandler__not_loading:
    ; Reuse the old visible buffer for the next hidden frame immediately
    ; after a successful commit. This keeps preparation independent of the
    ; next presentation deadline.
    sep #$20
.a8
    lda.l SceneVideo_MsuDmaProbe
    bne SceneVideo_FrameTestHandler__scheduler
    lda.l SceneVideo_PlayState
    bne SceneVideo_FrameTestHandler__scheduler
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayNext
    cmp.l SceneVideo_SequenceFrameCount
    bcs SceneVideo_FrameTestHandler__scheduler
    sta.l SceneVideo_TestFrameIndex
    sep #$20
.a8
    lda.l SceneVideo_TestBuffer
    eor #1
    sta.l SceneVideo_TestBuffer
    lda #0
    sta.l SceneVideo_TestQueuePalette
    jsr SceneVideo_LoadFrame
    bcc SceneVideo_FrameTestHandler__scheduler
    lda #SCENE_VIDEO_PLAY_LOADING
    sta.l SceneVideo_PlayState
SceneVideo_FrameTestHandler__scheduler:
    ; Source-time accumulator. Each NTSC display tick contributes 1000 ms
    ; in a millisecond phase domain; fixed and per-frame timing metadata both
    ; feed the same exact integer path.
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayTimingPhase
    clc
    adc #1000
    sta.l SceneVideo_PlayTimingPhase
    lda.l SceneVideo_PlayTimingPhase+2
    adc #0
    sta.l SceneVideo_PlayTimingPhase+2
    lda.l SceneVideo_PlayTimingPhase+2
    cmp.l SceneVideo_PlayFrameBudget+2
    bcc SceneVideo_FrameTestHandler__phase_not_due
    bne SceneVideo_FrameTestHandler__phase_due
    lda.l SceneVideo_PlayTimingPhase
    cmp.l SceneVideo_PlayFrameBudget
    bcc SceneVideo_FrameTestHandler__phase_not_due
SceneVideo_FrameTestHandler__phase_due:
    lda.l SceneVideo_PlayTimingPhase
    sec
    sbc.l SceneVideo_PlayFrameBudget
    sta.l SceneVideo_PlayTimingPhase
    lda.l SceneVideo_PlayTimingPhase+2
    sbc.l SceneVideo_PlayFrameBudget+2
    sta.l SceneVideo_PlayTimingPhase+2
    sep #$20
.a8
    lda #1
    sta.l SceneVideo_PlayDue
    bra SceneVideo_FrameTestHandler__phase_ready
SceneVideo_FrameTestHandler__phase_not_due:
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_PlayDue
SceneVideo_FrameTestHandler__phase_ready:
    sep #$20
.a8
    lda.l SceneVideo_PlayDue
    bne SceneVideo_FrameTestHandler__due_latched
    brl SceneVideo_FrameTestHandler__not_due
SceneVideo_FrameTestHandler__due_latched:
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayNext
    cmp.l SceneVideo_SequenceFrameCount
    bcc SceneVideo_FrameTestHandler__not_final_due
    lda.l SceneVideo_SequenceClipOrdinal
    and #$00FF
    inc a
    cmp.l SceneVideo_SequenceClipCount16
    bcc SceneVideo_FrameTestHandler__next_clip
    brl SceneVideo_FrameTestHandler__finish
SceneVideo_FrameTestHandler__next_clip:
    ; The current clip's final frame has just received its full duration.
    ; Retain the scene-owned buffers/audio and prepare clip zero in the
    ; hidden buffer; no cleanup or audio restart occurs here.
    sep #$20
.a8
    lda.l SceneVideo_SequenceClipOrdinal
    inc a
    sta.l SceneVideo_SequenceClipOrdinal
    rep #$31
.a16
.i16
    lda.l SceneVideo_SequenceClipOrdinal
    and #$00FF
    clc
    adc.l SceneVideo_SequenceClipOffset
    tax
    sep #$20
.a8
    lda.l SceneSequence_ClipIds,x
    sta.l SceneVideo_SequenceClipId
    rep #$31
.a16
.i16
    lda #0
    sta.l SceneVideo_PlayNext
    sta.l SceneVideo_TestFrameIndex
    sep #$20
.a8
    lda.l SceneVideo_TestBuffer
    eor #1
    sta.l SceneVideo_TestBuffer
    lda #0
    sta.l SceneVideo_TestQueuePalette
    jsr SceneVideo_LoadFrame
    bcs SceneVideo_FrameTestHandler__next_clip_load_ok
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__next_clip_load_ok:
    sep #$20
.a8
    lda #SCENE_VIDEO_PLAY_LOADING
    sta.l SceneVideo_PlayState
    lda.l SceneVideo_SequenceTransitions
    inc a
    sta.l SceneVideo_SequenceTransitions
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__not_final_due:
    nop
    sep #$20
.a8
    lda.l SceneVideo_PlayState
    cmp #SCENE_VIDEO_PLAY_READY
    beq SceneVideo_FrameTestHandler__present
    ; The visible frame remains intact. This is intentionally telemetry-only;
    ; source frames are never dropped.
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayLateCount
    inc a
    sta.l SceneVideo_PlayLateCount
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__not_due:
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__present:
    ; A ready hidden buffer is committed only at the due boundary. Palette,
    ; tile base, and map base are selected for the same NMI commit.
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayNext
    sta.l SceneVideo_PlayVisible
    sta.l SceneVideo_PlayLastFrame
    sep #$20
.a8
    lda.l SceneVideo_PlayNext
    sta.l SceneVideo_PlayLastPresented
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayPresented
    inc a
    sta.l SceneVideo_PlayPresented
    lda.l SceneVideo_PlayNext
    inc a
    sta.l SceneVideo_PlayNext
    sep #$20
.a8
    lda.l SceneVideo_TestBuffer
    beq SceneVideo_FrameTestHandler__present_a
    lda #SCENE_VIDEO_BG1SC_B
    sta.l Nmi_Bg1TilemapVram
    lda #SCENE_VIDEO_BG12NBA_B
    sta.l Nmi_BgTilesVram12
    bra SceneVideo_FrameTestHandler__queue_palette
SceneVideo_FrameTestHandler__present_a:
    nop
    sep #$20
.a8
    lda #SCENE_VIDEO_BG1SC
    sta.l Nmi_Bg1TilemapVram
    lda #SCENE_VIDEO_BG12NBA
    sta.l Nmi_BgTilesVram12
SceneVideo_FrameTestHandler__queue_palette:
    nop
    rep #$31
.a16
.i16
    lda #SceneVideo_PaletteStage
    sta.l DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #SCENE_VIDEO_CGRAM_BYTE
    sta.l DmaRequest_TargetAddr
    rep #$31
.a16
.i16
    lda #64
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #DMA_TYPE_CGRAM
    sta.l DmaRequest_TypeFlags
    jsl Core_Dma_Enqueue_Long
    bcc SceneVideo_FrameTestHandler__palette_retry
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayNext
    dec a
    sta.l SceneVideo_PlayVisible
    sta.l SceneVideo_PlayLastFrame
    sep #$20
.a8
    lda.l SceneVideo_PlayNext
    dec a
    sta.l SceneVideo_PlayLastPresented
    lda.l SceneVideo_PlaySwaps
    inc a
    sta.l SceneVideo_PlaySwaps
    lda #0
    sta.l SceneVideo_PlayState
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__palette_retry:
    nop
    rep #$31
.a16
.i16
    lda.l SceneVideo_PlayDmaRetries
    inc a
    sta.l SceneVideo_PlayDmaRetries
    brl SceneVideo_FrameTestHandler__done
SceneVideo_FrameTestHandler__finish:
    nop
    ; Frame 125 has already received its normal due interval. Completion is
    ; recorded exactly once; the existing test service owns teardown.
    lda.l SceneVideo_PlayCompletion
    bne SceneVideo_FrameTestHandler__done
    inc a
    sta.l SceneVideo_PlayCompletion
    rep #$31
.a16
.i16
    lda.l SceneVideo_SequenceCompletion
    inc a
    sta.l SceneVideo_SequenceCompletion
    jsr SceneVideo_StopFrameTest
    rep #$31
.a16
.i16
SceneVideo_FrameTestHandler__done:
    nop
    rtl

; Carry set iff all eight queue slots are inactive. This is deliberately a
; non-destructive check; the NMI remains the sole queue consumer.
SceneVideo_DmaQueueEmpty:
    php
    sei
    sep #$20
.a8
    ldx #0
SceneVideo_DmaQueueEmpty__scan:
    nop
    sep #$20
.a8
    lda.l DmaQueue+4,x
    bit #DMA_OPT_ACTIVE
    bne SceneVideo_DmaQueueEmpty__busy
    rep #$31
.a16
.i16
    txa
    clc
    adc #DMA_QUEUE_SLOT_SIZE
    tax
    cmp #DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE
    bcc SceneVideo_DmaQueueEmpty__scan
    plp
    sec
    rts
SceneVideo_DmaQueueEmpty__busy:
    nop
    plp
    clc
    rts

SceneVideo_SeekAbsolute:
    sep #$20
.a8
    lda.l SceneVideo_TestSeekOffset
    sta $2000
    lda.l SceneVideo_TestSeekOffset+1
    sta $2001
    lda.l SceneVideo_TestSeekOffset+2
    sta $2002
    lda.l SceneVideo_TestSeekOffset+3
    sta $2003                 ; project MSU-1 extension: seek bits 24..31
SceneVideo_SeekAbsolute__busy:
    lda $2000
    bmi SceneVideo_SeekAbsolute__busy
    rep #$31
.a16
.i16
    rts

; Immediate scene-owned MSU_DATA -> WRAM transfer.  DMA channel 7 is used
; directly because the normal NMI queue is reserved for PPU work.  DMAP bit 3
; keeps A-bus source $2001 fixed while the MSU stream advances internally;
; WMDATA increments the WRAM address after each byte.
SceneVideo_DmaMsuToWram:
    php
    sei
    rep #$31
.a16
.i16
    lda.l SceneVideo_MsuDmaTarget
    sta $2181
    sep #$20
.a8
    lda #$7E
    sta $2183
    rep #$31
.a16
.i16
    lda #$2001
    sta $4372
    sep #$20
.a8
    lda #$00
    sta $4374
    lda #$08                 ; DMAP7: mode 0 + fixed A-bus source
    sta $4370
    lda #$80                 ; BBAD7: WMDATA
    sta $4371
    rep #$31
.a16
.i16
    lda.l SceneVideo_MsuDmaLength
    sta $4375
    sep #$20
.a8
    lda #$80                 ; MDMAEN channel 7
    sta $420B
    rep #$31
.a16
.i16
    plp
    rts

; ----------------------------------------------------------------------
; Fail closed. A nonzero error is verifier-visible and no DMA is queued.
; ----------------------------------------------------------------------
SceneVideo_Fail:
    sep #$20
.a8
    lda #1
    sta.l SceneVideo_TestError
    lda #0
    sta.l SceneVideo_TestActive
    sta.l SceneVideo_SequenceActive
    rep #$31
.a16
.i16
    clc
    rts

SceneVideo_SetErrorCode:
    sep #$20
.a8
    sta.l SceneVideo_TestErrorCode
    rep #$31
.a16
.i16
    rts

; ----------------------------------------------------------------------
; Load frame 0 of the generated Rugal record.
; ----------------------------------------------------------------------
; Convert the current source-frame duration in milliseconds to display-phase
; units. NTSC contributes 1000 phase units per NMI, while a frame budget is
; duration_ms * 60; the remainder is retained between frames.
SceneVideo_SetTimingBudget:
    rep #$31
.a16
.i16
    lda #0
    sta.l SceneVideo_PlayFrameBudget
    sta.l SceneVideo_PlayFrameBudget+2
    ldx #60
SceneVideo_SetTimingBudget__loop:
    lda.l SceneVideo_PlayFrameBudget
    clc
    adc.l SceneVideo_PlayFrameDuration
    sta.l SceneVideo_PlayFrameBudget
    lda.l SceneVideo_PlayFrameBudget+2
    adc.l SceneVideo_PlayFrameDurationHi
    sta.l SceneVideo_PlayFrameBudget+2
    dex
    bne SceneVideo_SetTimingBudget__loop
    rts

SceneVideo_LoadFrame:
    php
    sei
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_TestError
    sta.l SceneVideo_TestErrorCode
    sta.l SceneVideo_LoadCheckpointCounter
    rep #$31
.a16
.i16
    lda.l SceneVideo_LoadCount
    inc a
    sta.l SceneVideo_LoadCount
    lda.l Nmi_FrameCounter
    sta.l SceneVideo_LoadStartNmi
    sep #$20
.a8
    lda #$01
    sta $4200                 ; keep NMI out, preserve auto-joypad bit 0
    lda #$80
    sta $2100                 ; forced blank while staging/queueing
    rep #$31
.a16
.i16

    ; Resolve the generated BORVID record by video clip ID. The sequence
    ; resolver supplies this ID; authored scene IDs are never used as a
    ; physical video-record shortcut.
    rep #$31
.a16
.i16
    lda.l SceneVideo_SequenceClipId
    and #$00FF
    bne SceneVideo_LoadFrame__clip_nonzero
    lda #1
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__record_bad
SceneVideo_LoadFrame__clip_nonzero:
    dec a
    tax
    sep #$20
.a8
SceneVideo_LoadFrame__index_ok:
SceneVideo_LoadFrame__record_match:
    rep #$31
.a16
.i16
    txa
    asl a
    tax
    lda.l SceneVideo_RecordPayloadOffsetsLo,x
    sta.l SceneVideo_TestPayloadBase
    lda.l SceneVideo_RecordPayloadOffsetsHi,x
    sta.l SceneVideo_TestPayloadBase+2
    lda.l SceneVideo_RecordPayloadSizesLo,x
    sta.l SceneVideo_TestPayloadSize
    lda.l SceneVideo_RecordPayloadSizesHi,x
    sta.l SceneVideo_TestPayloadSize+2
SceneVideo_LoadFrame__record_ok:
    lda.l SceneVideo_RecordWidths,x
    sta.l SceneVideo_TestWidth
    lda.l SceneVideo_RecordHeights,x
    sta.l SceneVideo_TestHeight
    lda.l SceneVideo_RecordFrameCountsLo,x
    sta.l SceneVideo_SequenceFrameCount
    lda.l SceneVideo_RecordFrameCountsHi,x
    sta.l SceneVideo_SequenceFrameCount+2
    lda.l SceneVideo_RecordFrameDurationMs,x
    sta.l SceneVideo_PlayFrameDuration
    lda.l SceneVideo_RecordFlags,x
    sta.l SceneVideo_SequenceVariable
    ; This is a 16-bit half-word, not an 8-bit flag. Clear the complete
    ; duration high word so a prior scene cannot leak into the fixed-rate
    ; frame budget.
    rep #$31
.a16
.i16
    lda #0
    sta.l SceneVideo_PlayFrameDurationHi

    ; Seek to payload start and validate its frame count.
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestPayloadBase
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestPayloadBase+2
    sta.l SceneVideo_TestSeekOffset+2
    jsr SceneVideo_SeekAbsolute
    sep #$20
.a8
    lda $2001
    sta.l SceneVideo_TestFrameCount
    lda $2001
    sta.l SceneVideo_TestFrameCount+1
    lda $2001
    sta.l SceneVideo_TestFrameCount+2
    lda $2001
    sta.l SceneVideo_TestFrameCount+3
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestFrameCount
    cmp.l SceneVideo_SequenceFrameCount
    beq SceneVideo_LoadFrame__count_ok
    lda #2
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__count_ok:
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestFrameCount+2
    beq SceneVideo_LoadFrame__count_high_ok
    lda #3
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__record_bad:
    jsr SceneVideo_Fail
    plp
    rts
SceneVideo_LoadFrame__count_high_ok:
.a16
.i16

    ; The packed count is u32; the current runtime index is deliberately
    ; widened to u16 and is rejected before any pointer-table seek.
    lda.l SceneVideo_TestFrameIndex
    cmp.l SceneVideo_SequenceFrameCount
    bcc SceneVideo_LoadFrame__frame_index_ok
SceneVideo_LoadFrame__frame_index_bad:
    lda #6
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__frame_index_ok:

    ; Variable-timing clips store one u16 millisecond duration immediately
    ; after the pointer table. Read the requested frame's duration directly;
    ; fixed clips retain the generated rational-FPS duration above.
    sep #$20
.a8
    lda.l SceneVideo_SequenceVariable
    and #1
    beq SceneVideo_LoadFrame__timing_ready
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestPayloadBase
    clc
    adc #4
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestPayloadBase+2
    adc #0
    sta.l SceneVideo_TestSeekOffset+2
    lda.l SceneVideo_SequenceFrameCount
    asl a
    asl a
    clc
    adc.l SceneVideo_TestSeekOffset
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestSeekOffset+2
    adc #0
    sta.l SceneVideo_TestSeekOffset+2
    lda.l SceneVideo_TestFrameIndex
    asl a
    clc
    adc.l SceneVideo_TestSeekOffset
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestSeekOffset+2
    adc #0
    sta.l SceneVideo_TestSeekOffset+2
    jsr SceneVideo_SeekAbsolute
    sep #$20
.a8
    lda $2001
    sta.l SceneVideo_PlayFrameDuration
    lda $2001
    sta.l SceneVideo_PlayFrameDuration+1
    rep #$31
.a16
.i16
    lda #0
    sta.l SceneVideo_PlayFrameDurationHi
SceneVideo_LoadFrame__timing_ready:
    rep #$31
.a16
.i16
    jsr SceneVideo_SetTimingBudget

    ; The pointer table is u32-relative. Frame index is multiplied by four;
    ; the same path therefore serves L3A frame zero and every L3B frame.
    lda.l SceneVideo_TestPayloadBase
    clc
    adc #4
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestPayloadBase+2
    adc #0
    sta.l SceneVideo_TestSeekOffset+2
    lda.l SceneVideo_TestFrameIndex
    asl a
    asl a
    clc
    adc.l SceneVideo_TestSeekOffset
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestSeekOffset+2
    adc #0
    sta.l SceneVideo_TestSeekOffset+2
    jsr SceneVideo_SeekAbsolute
    sep #$20
.a8
    lda $2001
    sta.l SceneVideo_TestFramePointer
    lda $2001
    sta.l SceneVideo_TestFramePointer+1
    lda $2001
    sta.l SceneVideo_TestFramePointer+2
    lda $2001
    sta.l SceneVideo_TestFramePointer+3
    rep #$31
.a16
.i16
    ; pointer < payload_size, unsigned 32-bit compare
    lda.l SceneVideo_TestFramePointer+2
    cmp.l SceneVideo_TestPayloadSize+2
    bcc SceneVideo_LoadFrame__pointer_ok
    beq SceneVideo_LoadFrame__pointer_high_equal
    lda #7
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__pointer_high_equal:
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestFramePointer
    cmp.l SceneVideo_TestPayloadSize
    bcc SceneVideo_LoadFrame__pointer_ok
    lda #7
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__pointer_ok:
    ; absolute frame offset = payload base + relative pointer
    lda.l SceneVideo_TestPayloadBase
    clc
    adc.l SceneVideo_TestFramePointer
    sta.l SceneVideo_TestFrameOffset
    lda.l SceneVideo_TestPayloadBase+2
    adc.l SceneVideo_TestFramePointer+2
    sta.l SceneVideo_TestFrameOffset+2
    lda.l SceneVideo_TestFrameOffset
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestFrameOffset+2
    sta.l SceneVideo_TestSeekOffset+2
    jsr SceneVideo_SeekAbsolute

    ; Parse frame_id and the packed length header.
    sep #$20
.a8
    lda $2001
    sta.l SceneVideo_TestFrameId
    lda $2001
    sta.l SceneVideo_TestFrameId+1
    lda $2001
    sta.l SceneVideo_TestLengthLo
    lda $2001
    sta.l SceneVideo_TestLengthLo+1
    lda $2001
    sta.l SceneVideo_TestLengthHi
    lda $2001
    sta.l SceneVideo_TestLengthHi+1
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestFrameId
    cmp.l SceneVideo_TestFrameIndex
    beq SceneVideo_LoadFrame__frame_id_ok
    lda #10
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__frame_id_ok:
.a16
.i16

    ; Decode the BOR packed lengths: map words in bits 0..10, tile words in
    ; bits 11..21, palette words in bits 22..29.
    lda.l SceneVideo_TestLengthLo
    and #$07FF
    asl a
    sta.l SceneVideo_TestMapBytes
    lda.l SceneVideo_TestLengthLo
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestLengthHi
    and #$003F
    asl a
    asl a
    asl a
    asl a
    asl a
    ora.l SceneVideo_TestSeekOffset
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SceneVideo_TestTileBytes
    lda.l SceneVideo_TestLengthHi
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    and #$00FF
    asl a
    sta.l SceneVideo_TestPaletteBytes

    lda.l SceneVideo_TestMapBytes
    cmp #1536
    beq SceneVideo_LoadFrame__map_ok
    lda #12
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__map_ok:
.a16
.i16
    lda.l SceneVideo_TestTileBytes
    cmp #12289
    bcc SceneVideo_LoadFrame__tile_max_ok
    lda #13
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__tile_max_ok:
.a16
.i16
    and #$001F
    beq SceneVideo_LoadFrame__tile_alignment_ok
    lda #14
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__tile_alignment_ok:
.a16
.i16
    lda.l SceneVideo_TestPaletteBytes
    cmp #64
    beq SceneVideo_LoadFrame__palette_ok
    lda #15
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__palette_ok:
.a16
.i16

    ; Telemetry records the complete scene batch drained by one NMI: map,
    ; tiles (including the blank border tile), and palette when this is the
    ; visible-frame load. Hidden loads intentionally omit the palette.
    lda.l SceneVideo_TestMapBytes
    clc
    adc.l SceneVideo_TestTileBytes
    adc #SCENE_VIDEO_BLANK_TILE_BYTES
    sep #$20
.a8
    lda.l SceneVideo_TestQueuePalette
    beq SceneVideo_LoadFrame__dma_bytes_no_palette
    rep #$31
.a16
.i16
    adc #64
SceneVideo_LoadFrame__dma_bytes_no_palette:
    nop
    rep #$31
.a16
.i16
    cmp.l SceneVideo_PlayMaxDmaBytes
    bcc SceneVideo_LoadFrame__max_dma_done
    sta.l SceneVideo_PlayMaxDmaBytes
SceneVideo_LoadFrame__max_dma_done:
    rep #$31
.a16
.i16

    ; Verify relative frame end <= payload size before reading data.
    lda.l SceneVideo_TestFramePointer
    clc
    adc #6
    adc.l SceneVideo_TestMapBytes
    adc.l SceneVideo_TestTileBytes
    adc.l SceneVideo_TestPaletteBytes
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestFramePointer+2
    adc #0
    sta.l SceneVideo_TestSeekOffset+2
    lda.l SceneVideo_TestSeekOffset+2
    cmp.l SceneVideo_TestPayloadSize+2
    bcc SceneVideo_LoadFrame__end_ok
    beq SceneVideo_LoadFrame__end_high_equal
    lda #18
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__end_high_equal:
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestSeekOffset
    cmp.l SceneVideo_TestPayloadSize
    bcc SceneVideo_LoadFrame__end_ok
    beq SceneVideo_LoadFrame__end_ok
    lda #18
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__end_ok:
.a16
.i16

    ; Border map uses one blank tile appended after the frame's actual tiles.
    ; This keeps all 32x32 cells initialized without corrupting video tile 0.
    lda.l SceneVideo_TestTileBytes
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SceneVideo_BlankTileIndex
    lda.l SceneVideo_BlankTileIndex
    cmp #385
    bcc SceneVideo_LoadFrame__blank_index_ok
    lda #19
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__bad
SceneVideo_LoadFrame__blank_index_ok:
.a16
.i16
    lda.l SceneVideo_BlankTileIndex
    ldx #0
SceneVideo_LoadFrame__clear_map:
.a16
.i16
    sta.l SceneVideo_MapStage,x
    inx
    inx
    cpx #SCENE_VIDEO_MAP_DMA_BYTES
    bcc SceneVideo_LoadFrame__clear_map

    ; Read packed tilemap into rows 2..25 of the full 32x32 map.
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestFrameOffset
    clc
    adc #6
    sta.l SceneVideo_TestSeekOffset
    lda.l SceneVideo_TestFrameOffset+2
    adc #0
    sta.l SceneVideo_TestSeekOffset+2
    jsr SceneVideo_SeekAbsolute
    rep #$31
.a16
.i16
    lda #SceneVideo_MapVideoStage
    sta.l SceneVideo_MsuDmaTarget
    lda.l SceneVideo_TestMapBytes
    clc
    adc.l SceneVideo_TestTileBytes
    adc.l SceneVideo_TestPaletteBytes
    sta.l SceneVideo_MsuDmaLength
    jsr SceneVideo_DmaMsuToWram
    brl SceneVideo_LoadFrame__queue_loaded_body
    sep #$20
.a8
    ldx #0
SceneVideo_LoadFrame__read_map:
.a8
.i16
    lda $2001
    sta.l SceneVideo_MapVideoStage,x
    inx
    txa
    bne SceneVideo_LoadFrame__map_no_checkpoint
    jsr SceneVideo_LoadCheckpoint
    bcc SceneVideo_LoadFrame__map_checkpoint_ok
    brl SceneVideo_LoadFrame__aborted
SceneVideo_LoadFrame__map_checkpoint_ok:
SceneVideo_LoadFrame__map_no_checkpoint:
    sep #$20
.a8
    cpx #1536
    bcc SceneVideo_LoadFrame__read_map

    ; Read tiles and append the all-zero border tile.
    ldx #0
SceneVideo_LoadFrame__read_tiles:
    lda $2001
    sta.l SceneVideo_TileStage,x
    inx
    txa
    bne SceneVideo_LoadFrame__tiles_no_checkpoint
    jsr SceneVideo_LoadCheckpoint
    bcc SceneVideo_LoadFrame__tiles_checkpoint_ok
    brl SceneVideo_LoadFrame__aborted
SceneVideo_LoadFrame__tiles_checkpoint_ok:
SceneVideo_LoadFrame__tiles_no_checkpoint:
    sep #$20
.a8
    rep #$20
.a16
    txa
    cmp.l SceneVideo_TestTileBytes
    sep #$20
.a8
    bcc SceneVideo_LoadFrame__read_tiles
    ldy #0
SceneVideo_LoadFrame__blank_tile:
.a8
.i16
    lda #0
    sta.l SceneVideo_TileStage,x
    inx
    iny
    cpy #SCENE_VIDEO_BLANK_TILE_BYTES
    bcc SceneVideo_LoadFrame__blank_tile

    ; Palette follows the fixed tile staging capacity, so its source never
    ; overlaps even when a future frame uses all 384 source tiles.
    ldx #0
SceneVideo_LoadFrame__read_palette:
.a8
.i16
    lda $2001
    sta.l SceneVideo_PaletteStage,x
    inx
    cpx #64
    bcc SceneVideo_LoadFrame__read_palette

SceneVideo_LoadFrame__queue_loaded_body:

    ; Append the blank border tile after the contiguous DMA body.
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestMapBytes
    clc
    adc.l SceneVideo_TestTileBytes
    tax
    sep #$20
.a8
    ldy #0
SceneVideo_LoadFrame__dma_blank_tile:
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_MapVideoStage,x
    inx
    iny
    cpy #SCENE_VIDEO_BLANK_TILE_BYTES
    bcc SceneVideo_LoadFrame__dma_blank_tile

    ; Queue map, tile graphics + blank tile, and CGRAM palette through the
    ; existing BOR DMA abstraction. The next NMI drains these three requests.
    rep #$31
.a16
.i16
    lda #SceneVideo_MapStage
    sta.l DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda.l SceneVideo_TestBuffer
    beq SceneVideo_LoadFrame__map_target_a
    rep #$31
.a16
.i16
    lda #SCENE_VIDEO_MAP_VRAM_BYTE_B
    sta.l DmaRequest_TargetAddr
    bra SceneVideo_LoadFrame__map_target_done
SceneVideo_LoadFrame__map_target_a:
    nop
    rep #$31
.a16
.i16
    lda #SCENE_VIDEO_MAP_VRAM_BYTE
    sta.l DmaRequest_TargetAddr
SceneVideo_LoadFrame__map_target_done:
    nop
    rep #$31
.a16
.i16
    lda #SCENE_VIDEO_MAP_DMA_BYTES
    sta.l DmaRequest_Length
    jsl Core_Dma_Enqueue_Long
    bcs SceneVideo_LoadFrame__map_dma_ok
    lda #16
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__dma_bad
SceneVideo_LoadFrame__map_dma_ok:
.a16
.i16

    lda #SceneVideo_MapVideoStage
    clc
    adc.l SceneVideo_TestMapBytes
    sta.l DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda.l SceneVideo_TestBuffer
    beq SceneVideo_LoadFrame__tile_target_a
    rep #$31
.a16
.i16
    lda #SCENE_VIDEO_TILE_VRAM_BYTE_B
    sta.l DmaRequest_TargetAddr
    bra SceneVideo_LoadFrame__tile_target_done
SceneVideo_LoadFrame__tile_target_a:
    nop
    rep #$31
.a16
.i16
    lda #SCENE_VIDEO_TILE_VRAM_BYTE
    sta.l DmaRequest_TargetAddr
SceneVideo_LoadFrame__tile_target_done:
    nop
    rep #$31
.a16
.i16
    lda.l SceneVideo_TestTileBytes
    clc
    adc #SCENE_VIDEO_BLANK_TILE_BYTES
    sta.l DmaRequest_Length
    jsl Core_Dma_Enqueue_Long
    bcs SceneVideo_LoadFrame__tile_dma_ok
    lda #17
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__dma_bad
SceneVideo_LoadFrame__tile_dma_ok:
.a16
.i16

    lda.l SceneVideo_TestQueuePalette
    beq SceneVideo_LoadFrame__skip_palette_dma
    lda #SceneVideo_MapVideoStage
    clc
    adc.l SceneVideo_TestMapBytes
    adc.l SceneVideo_TestTileBytes
    sta.l DmaRequest_SourceAddrLow
    lda #SCENE_VIDEO_CGRAM_BYTE
    sta.l DmaRequest_TargetAddr
    lda #64
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #DMA_TYPE_CGRAM
    sta.l DmaRequest_TypeFlags
    jsl Core_Dma_Enqueue_Long
    bcs SceneVideo_LoadFrame__palette_dma_ok
    lda #17
    jsr SceneVideo_SetErrorCode
    brl SceneVideo_LoadFrame__dma_bad
SceneVideo_LoadFrame__palette_dma_ok:
.a8

SceneVideo_LoadFrame__skip_palette_dma:
    sep #$20
.a8

    ; BG1 only while the test frame is active; NMI commits these shadows after
    ; the queued transfers, so no half-loaded frame is exposed.
    lda.l SceneVideo_TestQueuePalette
    beq SceneVideo_LoadFrame__bg_target_done
    lda #$09
    sta.l Nmi_ScreenMode
    lda.l SceneVideo_TestBuffer
    beq SceneVideo_LoadFrame__bg_target_a
    lda #SCENE_VIDEO_BG1SC_B
    sta.l Nmi_Bg1TilemapVram
    lda #SCENE_VIDEO_BG12NBA_B
    sta.l Nmi_BgTilesVram12
    bra SceneVideo_LoadFrame__bg_target_done
SceneVideo_LoadFrame__bg_target_a:
    nop
    sep #$20
.a8
    lda #SCENE_VIDEO_BG1SC
    sta.l Nmi_Bg1TilemapVram
    lda #SCENE_VIDEO_BG12NBA
    sta.l Nmi_BgTilesVram12
SceneVideo_LoadFrame__bg_target_done:
    nop
    sep #$20
.a8
    lda #$01
    sta.l Nmi_MainScreen
    rep #$31
.a16
.i16
    lda #0
    sta.l Nmi_Bg1ScrollX
    sta.l Nmi_Bg1ScrollY
    sta.l Nmi_Bg2ScrollX
    sta.l Nmi_Bg2ScrollY
    sta.l Nmi_Bg3ScrollX
    sta.l Nmi_Bg3ScrollY
    sep #$20
.a8
    lda #$0F
    sta.l Nmi_ScreenBrightness
    lda #$81
    sta $4200
    rep #$31
.a16
.i16
    lda.l Nmi_FrameCounter
    sta.l SceneVideo_LoadEndNmi
    plp
    sec
    rts

; Called only when the low byte of a read index wraps, i.e. once per 256
; MSU bytes. The actual hardware poll is every eighth boundary (2048 bytes),
; keeping the service bounded without paying a full poll on every boundary.
SceneVideo_LoadCheckpoint:
    sep #$20
.a8
    lda.l SceneVideo_LoadCheckpointCounter
    inc a
    sta.l SceneVideo_LoadCheckpointCounter
    and #$07
    bne SceneVideo_LoadCheckpoint__done
    lda.l SceneVideo_TestActive
    beq SceneVideo_LoadCheckpoint__done
    rep #$31
.a16
.i16
    lda.l SceneVideo_LoadCheckpoints
    inc a
    sta.l SceneVideo_LoadCheckpoints
    jsr SceneVideo_ServiceInput
    sep #$20
.a8
    lda.l SceneVideo_SkipPending
    beq SceneVideo_LoadCheckpoint__done
    sec
    rts
SceneVideo_LoadCheckpoint__done:
    clc
    rts

; Cooperative service during the synchronous MSU read.  It calls the same
; hardware-latched Core_Input_Poll used by the ordinary main loop and only
; latches an edge for the scene handler; cleanup remains outside this loop.
SceneVideo_ServiceInput:
    phx
    phy
    jsl Core_Input_Poll
    jsr SceneVideo_LatchInputEdge
    ply
    plx
    rts

; Latch the edge currently held by the normal global input path.  This only
; consumes Input_trigger/Input2_trigger; it never manufactures controller
; state or treats a held Input_press as a new press.
SceneVideo_LatchInputEdge:
    rep #$31
.a16
.i16
    lda.l SceneVideo_InputPollCount
    inc a
    sta.l SceneVideo_InputPollCount
    lda.l Input_trigger
    ora.l Input_trigger+1
    ora.l Input2_trigger
    ora.l Input2_trigger+1
    beq SceneVideo_LatchInputEdge__none
    lda.l Input_last_raw_Addr
    sta.l SceneVideo_InputRawAtSkip
    lda.l Input_press
    sta.l SceneVideo_InputPressAtSkip
    lda.l Input_trigger
    sta.l SceneVideo_InputTriggerAtSkip
    lda.l Input2_trigger
    sta.l SceneVideo_Input2TriggerAtSkip
    sep #$20
.a8
    lda #1
    sta.l SceneVideo_SkipPending
    sec
    rts
SceneVideo_LatchInputEdge__none:
    clc
    rts

SceneVideo_LoadFrame__aborted:
    sep #$20
.a8
    lda #$81
    sta $4200
    clc
    plp
    rts

SceneVideo_LoadFrame__dma_bad:
    rep #$31
.a16
.i16
    jsr SceneVideo_Fail
    plp
    clc
    rts
SceneVideo_LoadFrame__bad:
    jsr SceneVideo_Fail
    plp
    clc
    rts

; ----------------------------------------------------------------------
; One cleanup path for the L3A test. Restore the normal BOR shadow setup and
; return to the already-supported title renderer; no campaign transition is
; owned by this slice.
; ----------------------------------------------------------------------
SceneVideo_StopFrameTest:
    php
    sei
    sep #$20
.a8
    lda #0
    sta $4200
    lda #$80
    sta $2100
    lda #0
    sta.l SceneVideo_TestActive
    lda #0
    sta.l SceneVideo_TestRequest
    sta.l SceneVideo_TestError
    sta.l SceneVideo_SkipPending
    ; Natural completion and skip share one audio stop operation.
    sta $2007
    sta.l Music_PlayState
    lda.l SceneVideo_PlayAudioStops
    inc a
    sta.l SceneVideo_PlayAudioStops
    lda #$09
    sta.l Nmi_ScreenMode
    lda #$60
    sta.l Nmi_Bg1TilemapVram
    lda #$68
    sta.l Nmi_Bg3TilemapVram
    lda #$20
    sta.l Nmi_BgTilesVram12
    lda #$05
    sta.l Nmi_BgTilesVram34
    lda #$15
    sta.l Nmi_MainScreen
    lda #$0F
    sta.l Nmi_ScreenBrightness
    rep #$31
.a16
.i16
    lda #0
    sta.l Nmi_Bg1ScrollX
    sta.l Nmi_Bg1ScrollY
    sta.l Nmi_Bg2ScrollX
    sta.l Nmi_Bg2ScrollY
    sta.l Nmi_Bg3ScrollX
    sta.l Nmi_Bg3ScrollY
    sep #$20
.a8
    lda.l SceneVideo_Continuation
    beq SceneVideo_StopFrameTest__title
    jsl Game_Campaign_AdvanceAfterScene
    bra SceneVideo_StopFrameTest__done
SceneVideo_StopFrameTest__title:
    rep #$31
.a16
.i16
    lda #GAME_STATE_TITLE
    sta.l Game_State
    sta.l $7E2752
    sep #$20
.a8
    lda #0
    sta.l $7E2760
SceneVideo_StopFrameTest__done:
    sep #$20
.a8
    stz $506E
    lda #$81
    sta $4200
    plp
    rts
